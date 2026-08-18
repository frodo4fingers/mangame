"""One dialog for finding a series and adding it.

Adding used to be a chain of modal boxes: type a query, wait blind while the
network happened, then pick from a list — and when nothing was found, a combo
box containing a single empty string stood in for an error message. Refining a
search meant starting again from the menu.

This is that whole flow in one window: the field, the results and the outcome
all stay on screen, so a search that found the wrong thing is one edit away
from the right one.

Results are grouped by title rather than listed per source. Three rows reading
"One Piece · mangadex", "One Piece · anilist", "One Piece · mangaupdates" are
one series, and picking any of them already produced the same tracked entry —
:meth:`MangameTray._track` cross-links same-titled matches. Showing the group
makes what Add will do visible instead of surprising.

The dialog knows nothing about threads or networking: it emits
``search_requested`` and waits to be handed results, which is what lets its
logic be tested without a display or a socket.
"""

from collections.abc import Iterable, Sequence

from pydantic import BaseModel, ConfigDict
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mangame.i18n.catalog import Translator
from mangame.sources.base import SourceMatch
from mangame.store.config import series_key

#: Source order used to pick which match represents a group. MangaDex first
#: because it is the one that reports chapter times; a status-only source can
#: describe a series but never say that a chapter landed.
SOURCE_PRIORITY = ("mangadex", "mangaupdates", "anilist", "feed")


def title_key(title: str) -> str:
    """The identity two matches must share to be the same series.

    Deliberately the same normalisation ``_track`` uses when it decides which
    matches to cross-link, so the grouping shown is the grouping applied. It is
    stricter than the series key: "One Piece" and "One Piece!" are two rows,
    but they would be stored under the same key.
    """
    return title.strip().lower()


def _priority(source_id: str) -> int:
    if source_id in SOURCE_PRIORITY:
        return SOURCE_PRIORITY.index(source_id)
    return len(SOURCE_PRIORITY)


class SeriesCandidate(BaseModel):
    """One series in the results list, with every source that offered it."""

    model_config = ConfigDict(frozen=True)

    title: str
    year: int | None = None
    matches: tuple[SourceMatch, ...]
    tracked: bool = False

    @property
    def primary(self) -> SourceMatch:
        """The match that represents the group.

        Ranked rather than "whichever source answered first", so a series is
        anchored to a source that can report chapters whenever one is on offer.
        """
        return min(self.matches, key=lambda match: _priority(match.source_id))

    @property
    def source_ids(self) -> tuple[str, ...]:
        seen: list[str] = []
        for match in self.matches:
            if match.source_id not in seen:
                seen.append(match.source_id)
        return tuple(seen)

    def label(self) -> str:
        year = f" ({self.year})" if self.year else ""
        return f"{self.title}{year}"

    def detail(self, tracked_label: str) -> str:
        sources = " · ".join(self.source_ids)
        return f"{sources} — {tracked_label}" if self.tracked else sources


def group_matches(
    matches: Iterable[SourceMatch], tracked_keys: Iterable[str] = ()
) -> list[SeriesCandidate]:
    """Collapse per-source matches into one candidate per series.

    First-appearance order is kept, so each source's own relevance ranking
    survives instead of being replaced by an ordering of our own invention.

    ``tracked_keys`` are compared the way the store compares them — by series
    key, not by title — so a row marked addable really is addable.
    """
    already = set(tracked_keys)
    grouped: dict[str, list[SourceMatch]] = {}
    for match in matches:
        grouped.setdefault(title_key(match.title), []).append(match)

    candidates = []
    for group in grouped.values():
        years = [match.year for match in group if match.year]
        title = min(group, key=lambda match: _priority(match.source_id)).title
        candidates.append(
            SeriesCandidate(
                title=title,
                year=years[0] if years else None,
                matches=tuple(group),
                tracked=series_key(title) in already,
            )
        )
    return candidates


class AddSeriesDialog(QDialog):
    """Search and add, in one window."""

    search_requested = Signal(str)
    """Emitted with the query whenever the user asks for a search."""

    def __init__(
        self,
        translator: Translator,
        tracked_keys: Sequence[str] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._t = translator
        self._tracked = tuple(tracked_keys)
        self._candidates: list[SeriesCandidate] = []
        self._searching = False
        self.chosen: SeriesCandidate | None = None

        self.setWindowTitle(self._t("dialog.add.title"))
        self.setMinimumWidth(440)

        self._query = QLineEdit(self)
        self._query.setPlaceholderText(self._t("dialog.add.placeholder"))
        self._query.setClearButtonEnabled(True)
        self._query.returnPressed.connect(self.start_search)
        self._query.textChanged.connect(self._on_query_changed)

        self._search_button = QPushButton(self._t("dialog.add.search"), self)
        self._search_button.setEnabled(False)
        self._search_button.setDefault(True)
        self._search_button.clicked.connect(self.start_search)

        self._results = QListWidget(self)
        self._results.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._results.setAlternatingRowColors(True)
        self._results.setMinimumHeight(180)
        self._results.itemSelectionChanged.connect(self._on_selection_changed)
        self._results.itemDoubleClicked.connect(self._on_double_click)

        self._status = QLabel(self._t("dialog.add.prompt"), self)
        self._status.setWordWrap(True)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self._add_button = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._add_button.setText(self._t("dialog.add.add"))
        self._add_button.setEnabled(False)
        # Enter belongs to the search field until there is something to add.
        self._add_button.setAutoDefault(False)
        self._buttons.accepted.connect(self._accept_selection)
        self._buttons.rejected.connect(self.reject)

        top = QHBoxLayout()
        top.addWidget(self._query, 1)
        top.addWidget(self._search_button)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self._results, 1)
        layout.addWidget(self._status)
        layout.addWidget(self._buttons)

        self._query.setFocus()

    # ------------------------------------------------------------- searching

    def query(self) -> str:
        return self._query.text().strip()

    def searching(self) -> bool:
        """True between asking for a search and being handed its outcome."""
        return self._searching

    def start_search(self) -> None:
        query = self.query()
        if not query or self._searching:
            return
        self._searching = True
        self._results.clear()
        self._candidates = []
        self._add_button.setEnabled(False)
        self._search_button.setEnabled(False)
        self._status.setText(self._t("dialog.add.searching"))
        self.search_requested.emit(query)

    def show_results(self, matches: Sequence[SourceMatch]) -> None:
        """Fill the list with what the search found."""
        self._searching = False
        self._candidates = group_matches(matches, self._tracked)
        self._results.clear()
        self._search_button.setEnabled(bool(self.query()))

        if not self._candidates:
            self._status.setText(self._t("dialog.add.none").format(query=self.query()))
            self._query.setFocus()
            self._query.selectAll()
            return

        tracked_label = self._t("dialog.add.tracked")
        for index, candidate in enumerate(self._candidates):
            item = QListWidgetItem(f"{candidate.label()}\n{candidate.detail(tracked_label)}")
            item.setData(Qt.ItemDataRole.UserRole, index)
            if candidate.tracked:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._results.addItem(item)

        self._status.setText(self._t("dialog.add.results").format(count=len(self._candidates)))
        self._select_first_addable()

    def search_failed(self) -> None:
        self._searching = False
        self._search_button.setEnabled(bool(self.query()))
        self._status.setText(self._t("dialog.add.failed"))

    # -------------------------------------------------------------- choosing

    def _select_first_addable(self) -> None:
        for row in range(self._results.count()):
            item = self._results.item(row)
            if item is not None and item.flags() & Qt.ItemFlag.ItemIsSelectable:
                self._results.setCurrentRow(row)
                return

    def _selected_candidate(self) -> SeriesCandidate | None:
        item = self._results.currentItem()
        if item is None or not item.flags() & Qt.ItemFlag.ItemIsSelectable:
            return None
        index = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(index, int) or index >= len(self._candidates):
            return None
        return self._candidates[index]

    def _on_query_changed(self, text: str) -> None:
        self._search_button.setEnabled(bool(text.strip()) and not self._searching)

    def _on_selection_changed(self) -> None:
        self._add_button.setEnabled(self._selected_candidate() is not None)

    def _on_double_click(self, _item: QListWidgetItem) -> None:
        self._accept_selection()

    def _accept_selection(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            return
        self.chosen = candidate
        self.accept()
