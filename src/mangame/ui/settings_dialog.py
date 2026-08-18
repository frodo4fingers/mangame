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
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mangame.domain.models import IconState
from mangame.i18n.catalog import Translator, available
from mangame.store.config import Settings
from mangame.ui import artwork, emblems

#: Preview swatch geometry. Every state is shown on a light *and* a dark
#: background, because "which tone survives on my panel" is the only question
#: the artwork tab exists to answer.
PREVIEW_ICON = 36
PREVIEW_PAD = 8
LIGHT_PANEL = "#F2F2F2"
DARK_PANEL = "#1B1B1B"

#: Slack around an emblem picker so its longest entry is never clipped.
COMBO_MARGIN = 16


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
    width = 2 * (PREVIEW_ICON + 2 * PREVIEW_PAD)
    height = PREVIEW_ICON + 2 * PREVIEW_PAD
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
        # Set while widgets are being repopulated, so echoing new settings
        # back into the dialog cannot bounce out as another change.
        self._loading = False

        self.setWindowTitle(self._t("dialog.settings.title"))
        self.setMinimumWidth(480)

        self._tabs = QTabWidget(self)
        self._tabs.addTab(self._build_general(), self._t("dialog.settings.tab.general"))
        self._tabs.addTab(self._build_manga(), self._t("dialog.settings.tab.manga"))
        self._tabs.addTab(self._build_artwork(), self._t("dialog.settings.tab.artwork"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
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
        self._series.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
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

        self._name = QLineEdit(page)
        self._name.textChanged.connect(self._on_name_changed)

        self._tone = QComboBox(page)
        self._tone.addItem(
            self._t("dialog.settings.art.tone.dark"), artwork.SilhouetteTone.DARK.value
        )
        self._tone.addItem(
            self._t("dialog.settings.art.tone.light"), artwork.SilhouetteTone.LIGHT.value
        )
        self._tone.currentIndexChanged.connect(self.update_preview)

        self._previews: dict[IconState, QLabel] = {}
        preview_box = QGroupBox(self._t("dialog.settings.art.preview"), page)
        preview_row = QHBoxLayout(preview_box)
        for state in IconState:
            cell = QVBoxLayout()
            swatch = QLabel(preview_box)
            swatch.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption = QLabel(self._t(f"state.{state.value}"), preview_box)
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setEnabled(False)
            cell.addWidget(swatch)
            cell.addWidget(caption)
            preview_row.addLayout(cell)
            self._previews[state] = swatch

        self._import = QPushButton(self._t("dialog.settings.art.import"), page)
        self._import.setEnabled(False)
        self._import.clicked.connect(self.import_artwork)

        self._status = QLabel("", page)
        self._status.setWordWrap(True)

        self._installed = QListWidget(page)
        self._installed.setMaximumHeight(90)
        self._installed.itemSelectionChanged.connect(self._on_installed_selection)

        self._discard = QPushButton(self._t("dialog.settings.art.remove"), page)
        self._discard.setEnabled(False)
        self._discard.clicked.connect(self._on_discard)

        installed_box = QGroupBox(self._t("dialog.settings.art.yours"), page)
        installed_layout = QHBoxLayout(installed_box)
        installed_layout.addWidget(self._installed, 1)
        installed_layout.addWidget(self._discard, 0, Qt.AlignmentFlag.AlignTop)

        form = QFormLayout()
        form.addRow(self._t("dialog.settings.art.image"), picker)
        form.addRow(self._t("dialog.settings.art.name"), self._name)
        form.addRow(self._t("dialog.settings.art.tone"), self._tone)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self._import)

        layout = QVBoxLayout(page)
        layout.addLayout(form)
        layout.addWidget(preview_box)
        layout.addLayout(actions)
        layout.addWidget(self._status)
        layout.addWidget(installed_box)
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
        finally:
            self._loading = False

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
        """Re-read the imported emblem list and the preview."""
        installed = artwork.user_emblems()
        self._installed.clear()
        self._installed.addItems(installed)
        self._installed.setEnabled(bool(installed))
        self._discard.setEnabled(False)
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
        """Adopt a picture, filling in a name if the field is still untouched."""
        self._source = path
        self._path.setText(str(path) if path else "")
        if path is not None and not self._name.text().strip():
            self._name.setText(suggested_name(path))
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
        """Render the three states from the chosen picture, or clear them."""
        ready = bool(self._source and self._name.text().strip())
        self._import.setEnabled(ready)

        for state, swatch in self._previews.items():
            if self._source is None:
                swatch.clear()
                continue
            try:
                image = artwork.state_image(self._source, state, 64, self.tone())
            except artwork.UnsupportedArtworkError:
                swatch.clear()
                self._status.setText(self._t("dialog.settings.art.failed"))
                self._import.setEnabled(False)
                continue
            swatch.setPixmap(QPixmap.fromImage(split_preview(image)))

    def import_artwork(self) -> None:
        """Write the three states to disk under the chosen name."""
        if self._source is None:
            return
        try:
            name = artwork.install(self._source, self._name.text(), self.tone())
        except artwork.UnsupportedArtworkError:
            self._status.setText(self._t("dialog.settings.art.failed"))
            return

        self._status.setText(self._t("dialog.settings.art.installed").format(name=name))
        self.artwork_changed.emit()
        self.refresh_artwork()
        self.set_settings(self._settings)

    def _on_discard(self) -> None:
        item = self._installed.currentItem()
        if item is None or not self._installed.isEnabled():
            return
        name = item.text()
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
        self._import.setEnabled(bool(self._source and self._name.text().strip()))

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
