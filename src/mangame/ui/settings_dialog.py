"""One window for everything that used to live in the context menu.

The tray menu had grown three levels deep — Manga ▸ Stop tracking ▸ a series,
Language ▸ a language — which is both awkward to reach and, on a panel at the
edge of a screen, awkward to even display. A menu is a good place for *verbs*
and a bad place for settings, so the verbs stayed (open, mark read, check now)
and everything with a value moved here.

Three tabs, matching the three things there are to configure:

* **General** — the reading language, and the switches that used to sit at the
  top level.
* **Manga** — which series get their own tray icon, which emblem each wears,
  and adding or dropping one.
* **Artwork** — turn any picture into an emblem. See :mod:`mangame.ui.artwork`
  for the transforms; this tab is the preview and the file picker around them.

Changes apply as they are made rather than on an OK button. A tray app has no
document to save, and an Apply step would only add a way to lose a change.

Like :mod:`mangame.ui.add_dialog`, the dialog owns no services: it emits what
the user asked for and is handed new settings back, which is what keeps it
testable without a poller, a database or a display.
"""

from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mangame.domain.models import IconState
from mangame.i18n.catalog import Translator, available
from mangame.store.config import SeriesConfig, Settings
from mangame.ui import artwork, emblems

#: Preview swatch geometry. Every state is shown on a light *and* a dark
#: background, because "which tone survives on my panel" is the only question
#: the artwork tab exists to answer.
PREVIEW_ICON = 36
PREVIEW_PAD = 8
LIGHT_PANEL = "#F2F2F2"
DARK_PANEL = "#1B1B1B"

#: Width of one swatch, and so of the column under it. Without the group box
#: that used to hold the previews, the captions decided how wide each cell was
#: and the row came out ragged. The height is reserved for the same reason:
#: so picking a picture fills the row in rather than pushing the page down.
PREVIEW_WIDTH = 2 * (PREVIEW_ICON + 2 * PREVIEW_PAD)
PREVIEW_HEIGHT = PREVIEW_ICON + 2 * PREVIEW_PAD

#: Slack around an emblem picker so its longest entry is never clipped.
COMBO_MARGIN = 16

#: Content insets. Three of them used to stack — the dialog's own layout, the
#: tab pane's frame and each page's layout — putting 24px between a control and
#: the window edge. The pages now sit flush inside a frameless tab widget, so
#: this is the only margin left, and it is the one the tab labels align to.
PAGE_MARGIN = 12
PAGE_SPACING = 8

#: Stands in for "not for one particular manga" in the target picker. No series
#: key can collide with it: keys are ``[a-z0-9-]+``.
SHARED_EMBLEM = "*shared*"

#: How much of a title a file name has to carry before a partial match counts.
#: Without a floor, a file called "one.png" would claim One Piece.
MIN_PARTIAL_MATCH = 4


class NameMatch(StrEnum):
    """What the chosen file name found among the tracked manga.

    Importing artwork exists to give a manga a picture, so the only question
    worth answering while it happens is *which* manga is about to get it.
    Naming that outcome keeps the sentence shown, the button's label and
    whether the button works at all derived from one decision instead of three.
    """

    IDLE = "idle"
    """No picture chosen yet; there is nothing to say."""

    MATCHED = "matched"
    """The file name picked out exactly one tracked manga."""

    CHOSEN = "chosen"
    """The user pointed at a manga themselves."""

    NONE = "none"
    """The file name matches nothing, or matches two things equally."""

    SHARED = "shared"
    """Deliberately not for one manga: a named emblem any of them can wear."""


def squash(text: str) -> str:
    """Reduce a title, a key or a file name to comparable letters.

    :func:`~mangame.store.config.series_key` turns punctuation into separators,
    which is right for an identity and too strict for recognising a file:
    someone who saves "hunterxhunter.png" plainly means "Hunter x Hunter", and
    a hyphen should not be the reason their import lands nowhere.
    """
    return "".join(char for char in text.lower() if char.isalnum())


def match_series(stem: str, series: Sequence[SeriesConfig]) -> str | None:
    """The key of the one manga a file name names, or ``None``.

    Ambiguity is not a match. Two candidates mean the file name decided
    nothing, and guessing between them would hand the artwork to the wrong
    manga — worse than asking, because nothing would look wrong afterwards.
    """
    target = squash(stem)
    if not target:
        return None

    exact = {s.key for s in series if target in {squash(s.title), squash(s.key)}}
    if exact:
        return exact.pop() if len(exact) == 1 else None

    partial = {
        s.key
        for s in series
        for form in (squash(s.title), squash(s.key))
        if min(len(form), len(target)) >= MIN_PARTIAL_MATCH
        and (target.startswith(form) or form.startswith(target))
    }
    return partial.pop() if len(partial) == 1 else None


def classify(source: Path | None, chosen: str | None, matched: str | None) -> NameMatch:
    """Where the manga about to receive this picture came from."""
    if source is None:
        return NameMatch.IDLE
    if chosen == SHARED_EMBLEM:
        return NameMatch.SHARED
    if chosen is None:
        return NameMatch.NONE
    return NameMatch.MATCHED if chosen == matched else NameMatch.CHOSEN


def heading(text: str, parent: QWidget) -> QLabel:
    """A section label: weight instead of a box.

    Qt's group boxes draw a frame that Fusion keeps even when the box is asked
    to be flat, and another frame is precisely what this window was trying to
    lose. A bold line reads as a group perfectly well without one.
    """
    label = QLabel(text, parent)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label


def flatten(view: QAbstractItemView) -> None:
    """Strip a view's sunken frame so it sits on the page, not in a well."""
    view.setFrameShape(QFrame.Shape.NoFrame)


def file_filter(label: str) -> str:
    """A Qt file dialog filter covering every image we can import."""
    patterns = " ".join(f"*{suffix}" for suffix in sorted(artwork.SUPPORTED_SUFFIXES))
    return f"{label} ({patterns})"


def suggested_name(source: Path) -> str:
    """The emblem name a file implies, so the field is rarely typed in."""
    return artwork.emblem_name(source.stem)


def emblem_choices(current: str) -> list[str]:
    """Emblem names to offer, keeping one a config already names.

    Artwork can be deleted out from under a series; dropping the name from the
    list would silently rewrite the config to whatever sorted first.
    """
    choices = emblems.selectable_emblems()
    return choices if current in choices else [*choices, current]


def split_preview(image: QImage) -> QImage:
    """One swatch showing an icon on a light panel and on a dark one.

    Returns an image rather than a pixmap so the composition can be checked
    without a running application; the widget wraps it at the last moment.
    """
    width = PREVIEW_WIDTH
    height = PREVIEW_HEIGHT
    canvas = QImage(width, height, QImage.Format.Format_ARGB32)

    painter = QPainter(canvas)
    painter.fillRect(0, 0, width // 2, height, QColor(LIGHT_PANEL))
    painter.fillRect(width // 2, 0, width - width // 2, height, QColor(DARK_PANEL))
    scaled = image.scaled(
        PREVIEW_ICON,
        PREVIEW_ICON,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    painter.drawImage(PREVIEW_PAD, PREVIEW_PAD, scaled)
    painter.drawImage(width // 2 + PREVIEW_PAD, PREVIEW_PAD, scaled)
    painter.end()
    return canvas


class SettingsDialog(QDialog):
    """Everything configurable, in one window."""

    settings_changed = Signal(object)
    """A new :class:`Settings` the caller should persist."""

    autostart_changed = Signal(bool)
    """Separate because enabling it writes a file and may fail."""

    add_requested = Signal()
    """The user wants the add-a-series dialog."""

    remove_requested = Signal(str)
    """Stop tracking the series with this key, forgetting its history."""

    artwork_changed = Signal()
    """Emblems on disk changed; cached icons are already invalidated."""

    def __init__(
        self,
        translator: Translator,
        settings: Settings,
        *,
        autostart_enabled: bool = False,
        autostart_supported: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._t = translator
        self._settings = settings
        self._source: Path | None = None
        # The manga the current file name picked out, kept so the dialog can
        # tell "we guessed this" from "you chose this".
        self._matched: str | None = None
        # Whether the emblem name is the user's words or ours.
        self._name_typed = False
        # Set while widgets are being repopulated, so echoing new settings
        # back into the dialog cannot bounce out as another change.
        self._loading = False

        self.setWindowTitle(self._t("dialog.settings.title"))
        self.setMinimumWidth(480)

        self._tabs = QTabWidget(self)
        self._tabs.setDocumentMode(True)
        self._tabs.addTab(self._build_general(), self._t("dialog.settings.tab.general"))
        self._tabs.addTab(self._build_manga(), self._t("dialog.settings.tab.manga"))
        self._tabs.addTab(self._build_artwork(), self._t("dialog.settings.tab.artwork"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
        layout.setSpacing(PAGE_SPACING)
        layout.addWidget(self._tabs, 1)
        layout.addWidget(buttons)

        self._autostart.setChecked(autostart_enabled)
        self._autostart.setEnabled(autostart_supported)
        if not autostart_supported:
            self._autostart.setToolTip(self._t("dialog.settings.autostart_unsupported"))
        self._autostart.toggled.connect(self._on_autostart)

        self.set_settings(settings)
        self.refresh_artwork()

    # ------------------------------------------------------------------ tabs

    def _build_general(self) -> QWidget:
        page = QWidget(self)

        self._language = QComboBox(page)
        for code, label in available().items():
            self._language.addItem(label, code)
        self._language.currentIndexChanged.connect(self._on_language)

        self._notifications = QCheckBox(self._t("dialog.settings.notifications"), page)
        self._notifications.toggled.connect(lambda checked: self._change(notifications=checked))

        self._single_icon = QCheckBox(self._t("dialog.settings.single_icon"), page)
        self._single_icon.toggled.connect(lambda checked: self._change(single_tray_icon=checked))

        self._autostart = QCheckBox(self._t("menu.autostart"), page)

        hint = QLabel(self._t("dialog.settings.language_hint"), page)
        hint.setWordWrap(True)
        hint.setEnabled(False)

        form = QFormLayout(page)
        form.setContentsMargins(0, PAGE_SPACING, 0, 0)
        form.setSpacing(PAGE_SPACING)
        form.addRow(self._t("dialog.settings.language"), self._language)
        form.addRow("", hint)
        form.addRow(self._notifications)
        form.addRow(self._single_icon)
        form.addRow(self._autostart)
        return page

    def _build_manga(self) -> QWidget:
        page = QWidget(self)

        self._series = QTableWidget(0, 2, page)
        self._series.setHorizontalHeaderLabels(
            [self._t("dialog.settings.column.series"), self._t("dialog.settings.column.emblem")]
        )
        self._series.verticalHeader().setVisible(False)
        self._series.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._series.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._series.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._series.setIconSize(QSize(20, 20))
        self._series.setShowGrid(False)
        flatten(self._series)
        self._series.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._series.horizontalHeader().setHighlightSections(False)
        self._series.itemChanged.connect(self._on_series_item_changed)
        self._series.itemSelectionChanged.connect(self._on_series_selection)

        hint = QLabel(self._t("dialog.settings.tray_hint"), page)
        hint.setWordWrap(True)
        hint.setEnabled(False)

        add = QPushButton(self._t("menu.add"), page)
        add.clicked.connect(self.add_requested.emit)

        self._remove = QPushButton(self._t("menu.remove"), page)
        self._remove.setEnabled(False)
        self._remove.clicked.connect(self._on_remove)

        row = QHBoxLayout()
        row.addWidget(add)
        row.addStretch(1)
        row.addWidget(self._remove)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, PAGE_SPACING, 0, 0)
        layout.setSpacing(PAGE_SPACING)
        layout.addWidget(self._series, 1)
        layout.addWidget(hint)
        layout.addLayout(row)
        return page

    def _build_artwork(self) -> QWidget:
        page = QWidget(self)

        self._path = QLineEdit(page)
        self._path.setReadOnly(True)
        self._path.setPlaceholderText(self._t("dialog.settings.art.prompt"))

        choose = QPushButton(self._t("dialog.settings.art.choose"), page)
        choose.clicked.connect(self.choose_source)

        picker = QHBoxLayout()
        picker.addWidget(self._path, 1)
        picker.addWidget(choose)

        self._target = QComboBox(page)
        self._target.setIconSize(QSize(20, 20))
        self._target.currentIndexChanged.connect(self._on_target)

        self._verdict = QLabel("", page)
        self._verdict.setWordWrap(True)

        self._name = QLineEdit(page)
        self._name.textChanged.connect(self._on_name_changed)
        # textEdited fires only for typing, so adopting a suggestion cannot
        # be mistaken for the user having named the emblem themselves.
        self._name.textEdited.connect(self._on_name_typed)

        self._tone = QComboBox(page)
        self._tone.addItem(
            self._t("dialog.settings.art.tone.dark"), artwork.SilhouetteTone.DARK.value
        )
        self._tone.addItem(
            self._t("dialog.settings.art.tone.light"), artwork.SilhouetteTone.LIGHT.value
        )
        self._tone.currentIndexChanged.connect(self.update_preview)

        self._previews: dict[IconState, QLabel] = {}
        # The preview and its heading live in one box so the whole block can
        # be hidden until there is a picture: captions under empty squares
        # read as breakage, not as an explanation of what import produces.
        self._preview_box = QWidget(page)
        preview_column = QVBoxLayout(self._preview_box)
        preview_column.setContentsMargins(0, 0, 0, 0)
        preview_column.setSpacing(2)
        preview_column.addWidget(heading(self._t("dialog.settings.art.preview"), self._preview_box))
        preview_row = QHBoxLayout()
        preview_row.setSpacing(PAGE_SPACING)
        for state in IconState:
            cell = QVBoxLayout()
            cell.setSpacing(2)
            swatch = QLabel(self._preview_box)
            swatch.setAlignment(Qt.AlignmentFlag.AlignCenter)
            swatch.setFixedWidth(PREVIEW_WIDTH)
            swatch.setMinimumHeight(PREVIEW_HEIGHT)
            caption = QLabel(self._t(f"state.{state.value}"), self._preview_box)
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setFixedWidth(PREVIEW_WIDTH)
            caption.setWordWrap(True)
            caption.setEnabled(False)
            cell.addWidget(swatch)
            cell.addWidget(caption)
            preview_row.addLayout(cell)
            self._previews[state] = swatch
        preview_row.addStretch(1)
        preview_column.addLayout(preview_row)

        self._import = QPushButton(self._t("dialog.settings.art.import"), page)
        self._import.setEnabled(False)
        self._import.clicked.connect(self.import_artwork)

        self._status = QLabel("", page)
        self._status.setWordWrap(True)

        self._installed = QListWidget(page)
        self._installed.setMaximumHeight(90)
        flatten(self._installed)
        self._installed.itemSelectionChanged.connect(self._on_installed_selection)

        self._discard = QPushButton(self._t("dialog.settings.art.remove"), page)
        self._discard.setEnabled(False)
        self._discard.clicked.connect(self._on_discard)

        installed_row = QHBoxLayout()
        installed_row.setSpacing(PAGE_SPACING)
        installed_row.addWidget(self._installed, 1)
        installed_row.addWidget(self._discard, 0, Qt.AlignmentFlag.AlignTop)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(PAGE_SPACING)
        form.addRow(self._t("dialog.settings.art.image"), picker)
        form.addRow(self._t("dialog.settings.art.for"), self._target)
        self._verdict_row = form.rowCount()
        form.addRow("", self._verdict)
        self._name_row = form.rowCount()
        form.addRow(self._t("dialog.settings.art.name"), self._name)
        form.addRow(self._t("dialog.settings.art.tone"), self._tone)
        # Only a shared emblem needs naming; for a manga the key is the name.
        form.setRowVisible(self._name_row, False)
        self._form = form

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self._import)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, PAGE_SPACING, 0, 0)
        layout.setSpacing(PAGE_SPACING)
        layout.addLayout(form)
        layout.addWidget(self._preview_box)
        layout.addLayout(actions)
        layout.addWidget(self._status)
        layout.addWidget(heading(self._t("dialog.settings.art.yours"), page))
        layout.addLayout(installed_row)
        layout.addStretch(1)
        return page

    # ----------------------------------------------------------- populating

    def set_settings(self, settings: Settings) -> None:
        """Show these settings without treating the update as a user edit."""
        self._settings = settings
        self._loading = True
        try:
            index = self._language.findData(settings.language)
            if index >= 0:
                self._language.setCurrentIndex(index)
            self._notifications.setChecked(settings.notifications)
            self._single_icon.setChecked(settings.single_tray_icon)
            self._fill_series()
            self._fill_targets(self._target.currentData())
        finally:
            self._loading = False
        self.update_preview()

    def _fill_series(self) -> None:
        self._series.setRowCount(len(self._settings.series))
        widest = 0

        for row, series in enumerate(self._settings.series):
            item = QTableWidgetItem(series.title)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(
                Qt.CheckState.Checked if series.show_in_tray else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, series.key)
            item.setIcon(emblems.icon_for(series.emblem, IconState.READY, series.title))
            self._series.setItem(row, 0, item)

            combo = QComboBox(self._series)
            for name in emblem_choices(series.emblem):
                combo.addItem(self._emblem_label(name), name)
            combo.setCurrentIndex(max(0, combo.findData(series.emblem)))
            combo.currentIndexChanged.connect(
                lambda _index, key=series.key, box=combo: self._on_emblem(key, box)
            )
            self._series.setCellWidget(row, 1, combo)
            widest = max(widest, combo.sizeHint().width())

        # Sized from the widest picker rather than left to the header, which
        # would clip a translated label or a long emblem name.
        if widest:
            self._series.setColumnWidth(1, widest + COMBO_MARGIN)
        self._remove.setEnabled(False)

    def _emblem_label(self, name: str) -> str:
        if name == emblems.MONOGRAM_EMBLEM:
            return self._t("dialog.settings.emblem.monogram")
        return name

    def refresh_artwork(self) -> None:
        """Re-read the imported emblem list and the preview.

        Each entry says which manga wears it, because an emblem nobody wears
        looks identical to one that is working — and that was exactly how an
        import could appear to succeed while changing nothing.
        """
        installed = artwork.user_emblems()
        self._installed.clear()
        self._installed.setEnabled(bool(installed))
        self._discard.setEnabled(False)
        for name in installed:
            worn_by = [s.title for s in self._settings.series if s.emblem == name]
            wearer = ", ".join(worn_by) if worn_by else self._t("dialog.settings.art.unused")
            item = QListWidgetItem(f"{name} — {wearer}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self._installed.addItem(item)
        if not installed:
            self._installed.addItem(self._t("dialog.settings.art.none"))
            self._installed.setEnabled(False)
        self.update_preview()

    # -------------------------------------------------------------- artwork

    def tone(self) -> artwork.SilhouetteTone:
        return artwork.SilhouetteTone(self._tone.currentData())

    def source(self) -> Path | None:
        return self._source

    def set_source(self, path: Path | None) -> None:
        """Adopt a picture and say which manga, if any, its name names."""
        self._source = path
        self._path.setText(str(path) if path else "")
        self._matched = match_series(path.stem, self._settings.series) if path else None
        # The suggestion follows the picture; a name the user typed does not,
        # or a second import would quietly be filed under the first one's name.
        if path is not None and not self._name_typed:
            self._name.setText(suggested_name(path))
        self._status.clear()
        # A new file re-asks the question, so an earlier answer is not kept.
        self._fill_targets(self._matched)
        self.update_preview()

    def target(self) -> str | None:
        """The key of the manga this picture is destined for, if one."""
        data = self._target.currentData()
        return data if isinstance(data, str) and data != SHARED_EMBLEM else None

    def match(self) -> NameMatch:
        """What the current file name found among the tracked manga."""
        return classify(self._source, self._target.currentData(), self._matched)

    def _title_of(self, key: str | None) -> str:
        return next((s.title for s in self._settings.series if s.key == key), "")

    def _fill_targets(self, preselect: str | None) -> None:
        """Offer every tracked manga, preselecting the one the name found."""
        was_loading = self._loading
        self._loading = True
        try:
            self._target.clear()
            self._target.addItem(self._t("dialog.settings.art.for.none"), None)
            for entry in self._settings.series:
                icon = emblems.icon_for(entry.emblem, IconState.READY, entry.title)
                self._target.addItem(icon, entry.title, entry.key)
            self._target.addItem(self._t("dialog.settings.art.for.shared"), SHARED_EMBLEM)
            index = self._target.findData(preselect) if preselect else 0
            self._target.setCurrentIndex(max(0, index))
        finally:
            self._loading = was_loading

    def _on_target(self, _index: int) -> None:
        if self._loading:
            return
        self._status.clear()
        self.update_preview()

    def choose_source(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(
            self,
            self._t("dialog.settings.art.choose"),
            str(self._source.parent) if self._source else "",
            file_filter(self._t("dialog.settings.art.images")),
        )
        if chosen:
            self.set_source(Path(chosen))

    def update_preview(self) -> None:
        """Recompute everything the chosen picture and manga imply.

        The sentence, the button's label and whether it works at all are all
        derived here from one :class:`NameMatch`, so they cannot disagree —
        which is the failure this tab had: a name that matched nothing looked
        exactly like a name that matched, and the import quietly went nowhere.
        """
        state = self.match()
        title = self._title_of(self.target())
        stem = self._source.stem if self._source else ""

        self._verdict.setText(self._verdict_text(state, stem, title))
        # Nothing matched is the one case that needs weight: it is the only
        # one where the user has to act before anything can happen.
        font = self._verdict.font()
        font.setBold(state is NameMatch.NONE)
        self._verdict.setFont(font)

        self._form.setRowVisible(self._name_row, state is NameMatch.SHARED)
        # An empty verdict and empty swatches are holes in the form; both only
        # have something to say once a picture has been chosen.
        self._form.setRowVisible(self._verdict_row, state is not NameMatch.IDLE)
        self._preview_box.setVisible(state is not NameMatch.IDLE)
        self._import.setText(
            self._t("dialog.settings.art.import.for").format(title=title)
            if title
            else self._t("dialog.settings.art.import")
        )
        self._import.setEnabled(self._can_import(state))

        for state_key, swatch in self._previews.items():
            if self._source is None:
                swatch.clear()
                continue
            try:
                image = artwork.state_image(self._source, state_key, 64, self.tone())
            except artwork.UnsupportedArtworkError:
                swatch.clear()
                self._status.setText(self._t("dialog.settings.art.failed"))
                self._import.setEnabled(False)
                continue
            swatch.setPixmap(QPixmap.fromImage(split_preview(image)))

    def _verdict_text(self, state: NameMatch, stem: str, title: str) -> str:
        key = {
            NameMatch.IDLE: "",
            NameMatch.MATCHED: "dialog.settings.art.verdict.matched",
            NameMatch.CHOSEN: "dialog.settings.art.verdict.chosen",
            NameMatch.NONE: "dialog.settings.art.verdict.none",
            NameMatch.SHARED: "dialog.settings.art.verdict.shared",
        }[state]
        return self._t(key).format(name=stem, title=title) if key else ""

    def _can_import(self, state: NameMatch) -> bool:
        if self._source is None:
            return False
        if state is NameMatch.SHARED:
            return bool(self._name.text().strip())
        return state in {NameMatch.MATCHED, NameMatch.CHOSEN}

    def import_artwork(self) -> None:
        """Write the three states to disk, and hand them to the chosen manga.

        Installing and assigning are one action because they were always one
        intention. Splitting them is what let a picture be imported under a
        name no series wore, leaving the manga looking untouched.
        """
        if self._source is None:
            return
        key = self.target()
        raw = key or self._name.text()
        if not raw.strip():
            return
        try:
            name = artwork.install(self._source, raw, self.tone())
        except artwork.UnsupportedArtworkError:
            self._status.setText(self._t("dialog.settings.art.failed"))
            return

        self.artwork_changed.emit()
        if key is None:
            self._status.setText(self._t("dialog.settings.art.installed").format(name=name))
        else:
            title = self._title_of(key)
            self._status.setText(self._t("dialog.settings.art.assigned").format(title=title))
            self._apply(self._settings.with_series_change(key, emblem=name))
        self.refresh_artwork()
        self.set_settings(self._settings)

    def _on_discard(self) -> None:
        item = self._installed.currentItem()
        if item is None or not self._installed.isEnabled():
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if not artwork.uninstall(name):
            return
        self._status.setText(self._t("dialog.settings.art.removed").format(name=name))
        self.artwork_changed.emit()
        self.refresh_artwork()
        self.set_settings(self._settings)

    def _on_installed_selection(self) -> None:
        self._discard.setEnabled(
            self._installed.isEnabled() and self._installed.currentItem() is not None
        )

    def _on_name_changed(self, _text: str) -> None:
        self.update_preview()

    def _on_name_typed(self, _text: str) -> None:
        self._name_typed = True

    # --------------------------------------------------------------- edits

    def _change(self, **changes: object) -> None:
        self._apply(self._settings.model_copy(update=changes))

    def _apply(self, updated: Settings) -> None:
        """Adopt an edit, then hand it to the caller to persist.

        The dialog keeps its own copy in step rather than waiting to be told,
        because the next edit is built on top of this one. Emitting from a
        stale copy would quietly undo whatever was changed just before.
        """
        if self._loading:
            return
        self._settings = updated
        self.settings_changed.emit(updated)

    def _on_language(self, _index: int) -> None:
        code = self._language.currentData()
        if isinstance(code, str):
            self._change(language=code)

    def _on_autostart(self, enabled: bool) -> None:
        if not self._loading:
            self.autostart_changed.emit(enabled)

    def _on_series_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(key, str):
            visible = item.checkState() is Qt.CheckState.Checked
            self._apply(self._settings.with_series_change(key, show_in_tray=visible))

    def _on_emblem(self, key: str, combo: QComboBox) -> None:
        if self._loading:
            return
        emblem = combo.currentData()
        if not isinstance(emblem, str):
            return
        self._show_emblem(key, emblem)
        self._apply(self._settings.with_series_change(key, emblem=emblem))

    def _show_emblem(self, key: str, emblem: str) -> None:
        """Repaint one row's icon, so picking an emblem shows straight away."""
        self._loading = True
        try:
            for row in range(self._series.rowCount()):
                item = self._series.item(row, 0)
                if item is not None and item.data(Qt.ItemDataRole.UserRole) == key:
                    item.setIcon(emblems.icon_for(emblem, IconState.READY, item.text()))
        finally:
            self._loading = False

    def _on_series_selection(self) -> None:
        self._remove.setEnabled(self._selected_key() is not None)

    def _selected_key(self) -> str | None:
        row = self._series.currentRow()
        item = self._series.item(row, 0) if row >= 0 else None
        if item is None:
            return None
        key = item.data(Qt.ItemDataRole.UserRole)
        return key if isinstance(key, str) else None

    def _on_remove(self) -> None:
        key = self._selected_key()
        if key is not None:
            self.remove_requested.emit(key)
