"""The settings dialog: what it shows, and what it asks the tray to do.

The dialog is driven for real here — on Qt's offscreen platform, so no display
is involved — because the interesting failures are wiring failures. A checkbox
connected to nothing, or an echo of saved settings bouncing back out as a fresh
edit, both look perfectly fine in a screenshot.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QComboBox, QTableWidgetItem

from mangame.domain.models import IconState
from mangame.i18n.catalog import Translator
from mangame.store.config import SeriesConfig, Settings
from mangame.ui import artwork, emblems
from mangame.ui.settings_dialog import (
    DARK_PANEL,
    LIGHT_PANEL,
    SettingsDialog,
    emblem_choices,
    file_filter,
    split_preview,
    suggested_name,
)

pytestmark = pytest.mark.usefixtures("qapp")


def picture(path: Path, fill: str = "#E8352C") -> Path:
    image = QImage(64, 64, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(fill))
    painter.drawEllipse(8, 8, 48, 48)
    painter.end()
    image.save(str(path))
    return path


def settings() -> Settings:
    return Settings(
        language="en",
        notifications=True,
        single_tray_icon=False,
        series=[
            SeriesConfig(key="one-piece", title="One Piece", emblem="onepiece"),
            SeriesConfig(
                key="kagurabachi", title="Kagurabachi", emblem="monogram", show_in_tray=False
            ),
        ],
    )


@pytest.fixture
def dialog(emblem_home: Path) -> Iterator[SettingsDialog]:
    widget = SettingsDialog(Translator("en"), settings())
    yield widget
    widget.deleteLater()


def row(dialog: SettingsDialog, index: int) -> QTableWidgetItem:
    """The series cell in one row of the Manga tab."""
    item = dialog._series.item(index, 0)
    assert item is not None
    return item


def emblem_combo(dialog: SettingsDialog, index: int) -> QComboBox:
    """The emblem picker in one row of the Manga tab."""
    combo = dialog._series.cellWidget(index, 1)
    assert isinstance(combo, QComboBox)
    return combo


class Recorder:
    """Collects whatever a signal carried, so a test can assert on it."""

    def __init__(self) -> None:
        self.calls: list[object] = []

    def __call__(self, value: object = None) -> None:
        self.calls.append(value)

    @property
    def last(self) -> object:
        return self.calls[-1]


class TestPureHelpers:
    def test_the_file_filter_covers_every_readable_format(self) -> None:
        pattern = file_filter("Images")
        assert pattern.startswith("Images (")
        for suffix in artwork.SUPPORTED_SUFFIXES:
            assert f"*{suffix}" in pattern

    @pytest.mark.parametrize(
        ("filename", "expected"),
        [("Straw Hat.png", "straw-hat"), ("one_piece.svg", "one-piece"), ("HAT.PNG", "hat")],
    )
    def test_a_name_is_suggested_from_the_filename(self, filename: str, expected: str) -> None:
        assert suggested_name(Path("/tmp") / filename) == expected

    def test_the_generated_badge_is_always_offered(self, emblem_home: Path) -> None:
        assert emblem_choices("onepiece")[0] == emblems.MONOGRAM_EMBLEM

    def test_an_emblem_whose_artwork_vanished_is_still_listed(self, emblem_home: Path) -> None:
        # Dropping it would silently rewrite the config to whatever sorted
        # first, losing the user's choice behind their back.
        assert "ghost" in emblem_choices("ghost")

    def test_the_preview_shows_the_icon_on_both_panel_colours(self, tmp_path: Path) -> None:
        image = artwork.load(picture(tmp_path / "a.png"), 64)
        swatch = split_preview(image)

        half = swatch.width() // 2
        assert swatch.pixelColor(1, 1).name() == QColor(LIGHT_PANEL).name()
        assert swatch.pixelColor(half + 1, 1).name() == QColor(DARK_PANEL).name()
        # ...and the artwork itself is drawn on each half.
        assert swatch.pixelColor(half // 2, swatch.height() // 2).name() == "#e8352c"
        assert swatch.pixelColor(half + half // 2, swatch.height() // 2).name() == "#e8352c"


class TestGeneralTab:
    def test_it_opens_showing_the_current_settings(self, dialog: SettingsDialog) -> None:
        assert dialog._language.currentData() == "en"
        assert dialog._notifications.isChecked() is True
        assert dialog._single_icon.isChecked() is False

    def test_turning_notifications_off_is_reported(self, dialog: SettingsDialog) -> None:
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        dialog._notifications.setChecked(False)

        assert isinstance(seen.last, Settings)
        assert seen.last.notifications is False
        # Everything else is carried over untouched.
        assert [s.key for s in seen.last.series] == ["one-piece", "kagurabachi"]

    def test_choosing_a_language_is_reported(self, dialog: SettingsDialog) -> None:
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        dialog._language.setCurrentIndex(dialog._language.findData("de"))

        assert isinstance(seen.last, Settings)
        assert seen.last.language == "de"

    def test_being_handed_new_settings_is_not_an_edit(self, dialog: SettingsDialog) -> None:
        # The tray echoes saved settings back into the open dialog. Without
        # the guard that echo re-enters as a change and loops.
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        dialog.set_settings(settings().model_copy(update={"notifications": False}))

        assert dialog._notifications.isChecked() is False
        assert seen.calls == []

    def test_a_second_edit_keeps_the_first(self, dialog: SettingsDialog) -> None:
        # Each change is built on the last, not on whatever the dialog opened
        # with, so switching two things in a row cannot revert either.
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        dialog._notifications.setChecked(False)
        dialog._single_icon.setChecked(True)

        assert isinstance(seen.last, Settings)
        assert seen.last.single_tray_icon is True
        assert seen.last.notifications is False

    def test_a_series_edit_keeps_an_earlier_general_edit(self, dialog: SettingsDialog) -> None:
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        dialog._notifications.setChecked(False)
        row(dialog, 0).setCheckState(Qt.CheckState.Unchecked)

        assert isinstance(seen.last, Settings)
        assert seen.last.series[0].show_in_tray is False
        assert seen.last.notifications is False

    def test_autostart_is_reported_separately(self, dialog: SettingsDialog) -> None:
        # Separate because switching it on writes a file and can fail, which
        # is the service layer's business rather than the dialog's.
        seen = Recorder()
        dialog.autostart_changed.connect(seen)

        dialog._autostart.setChecked(True)

        assert seen.calls == [True]

    def test_autostart_is_greyed_out_where_it_cannot_work(self, emblem_home: Path) -> None:
        widget = SettingsDialog(Translator("en"), settings(), autostart_supported=False)
        assert widget._autostart.isEnabled() is False
        assert widget._autostart.toolTip()

    def test_the_dialog_speaks_the_reading_language(self, emblem_home: Path) -> None:
        widget = SettingsDialog(Translator("de"), settings().model_copy(update={"language": "de"}))
        assert widget.windowTitle() == "mangame-Einstellungen"
        assert widget._language.currentData() == "de"


class TestMangaTab:
    def test_every_tracked_series_gets_a_row(self, dialog: SettingsDialog) -> None:
        assert dialog._series.rowCount() == 2
        assert row(dialog, 0).text() == "One Piece"
        assert row(dialog, 1).text() == "Kagurabachi"

    def test_the_tick_reflects_whether_it_has_its_own_icon(self, dialog: SettingsDialog) -> None:
        assert row(dialog, 0).checkState() is Qt.CheckState.Checked
        assert row(dialog, 1).checkState() is Qt.CheckState.Unchecked

    def test_unticking_a_series_hides_only_that_one(self, dialog: SettingsDialog) -> None:
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        row(dialog, 0).setCheckState(Qt.CheckState.Unchecked)

        assert isinstance(seen.last, Settings)
        assert seen.last.series[0].show_in_tray is False
        assert seen.last.series[1].show_in_tray is False  # unchanged
        assert seen.last.series[0].key == "one-piece"

    def test_the_emblem_combo_starts_on_the_configured_artwork(
        self, dialog: SettingsDialog
    ) -> None:
        assert emblem_combo(dialog, 0).currentData() == "onepiece"
        assert emblem_combo(dialog, 1).currentData() == emblems.MONOGRAM_EMBLEM

    def test_picking_another_emblem_is_reported(self, dialog: SettingsDialog) -> None:
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        combo = emblem_combo(dialog, 1)
        combo.setCurrentIndex(combo.findData("book"))

        assert isinstance(seen.last, Settings)
        assert seen.last.series[1].emblem == "book"
        assert seen.last.series[0].emblem == "onepiece"

    def test_picking_an_emblem_repaints_that_row_only(self, dialog: SettingsDialog) -> None:
        seen = Recorder()
        dialog.settings_changed.connect(seen)
        before = [row(dialog, i).icon().pixmap(24, 24).toImage() for i in (0, 1)]

        combo = emblem_combo(dialog, 1)
        combo.setCurrentIndex(combo.findData("book"))

        after = [row(dialog, i).icon().pixmap(24, 24).toImage() for i in (0, 1)]
        assert after[1] != before[1]
        assert after[0] == before[0]
        # Repainting the row must not read as a second edit.
        assert len(seen.calls) == 1

    def test_stop_tracking_waits_for_a_selection(self, dialog: SettingsDialog) -> None:
        assert dialog._remove.isEnabled() is False

        dialog._series.setCurrentCell(1, 0)

        assert dialog._remove.isEnabled() is True

    def test_stop_tracking_names_the_selected_series(self, dialog: SettingsDialog) -> None:
        seen = Recorder()
        dialog.remove_requested.connect(seen)

        dialog._series.setCurrentCell(1, 0)
        dialog._remove.click()

        assert seen.calls == ["kagurabachi"]

    def test_a_dropped_series_disappears_when_the_tray_says_so(
        self, dialog: SettingsDialog
    ) -> None:
        dialog.set_settings(settings().without_series("kagurabachi"))

        assert dialog._series.rowCount() == 1
        assert row(dialog, 0).text() == "One Piece"


class TestArtworkTab:
    def test_nothing_can_be_imported_before_a_picture_is_chosen(
        self, dialog: SettingsDialog
    ) -> None:
        assert dialog._import.isEnabled() is False

    def test_choosing_a_picture_fills_in_a_name(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "Straw Hat.png"))

        assert dialog._name.text() == "straw-hat"
        assert dialog._import.isEnabled() is True

    def test_a_name_the_user_typed_is_left_alone(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog._name.setText("mine")
        dialog.set_source(picture(tmp_path / "Straw Hat.png"))

        assert dialog._name.text() == "mine"

    def test_clearing_the_name_blocks_the_import(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "a.png"))
        dialog._name.setText("   ")

        assert dialog._import.isEnabled() is False

    def test_all_three_states_are_previewed(self, dialog: SettingsDialog, tmp_path: Path) -> None:
        dialog.set_source(picture(tmp_path / "a.png"))

        for state in IconState:
            assert not dialog._previews[state].pixmap().isNull()

    def test_switching_tone_redraws_the_break_preview(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "a.png"))

        def break_body() -> str:
            swatch = dialog._previews[IconState.BREAK].pixmap().toImage()
            return swatch.pixelColor(swatch.width() // 4, swatch.height() // 2).name()

        dark = break_body()
        dialog._tone.setCurrentIndex(dialog._tone.findData(artwork.SilhouetteTone.LIGHT.value))
        assert QColor(break_body()).lightness() > QColor(dark).lightness()

    def test_an_unreadable_file_says_so_instead_of_importing_it(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        broken = tmp_path / "broken.png"
        broken.write_bytes(b"not a png")
        dialog.set_source(broken)

        assert dialog._import.isEnabled() is False
        assert dialog._status.text() == Translator("en")("dialog.settings.art.failed")

    def test_importing_writes_the_emblem_and_announces_it(
        self, dialog: SettingsDialog, tmp_path: Path, emblem_home: Path
    ) -> None:
        seen = Recorder()
        dialog.artwork_changed.connect(seen)

        dialog.set_source(picture(tmp_path / "Straw Hat.png"))
        dialog._import.click()

        assert (emblem_home / "straw-hat" / "ready" / "64.png").exists()
        assert (emblem_home / "straw-hat" / "break" / "64.png").exists()
        assert len(seen.calls) == 1
        assert "straw-hat" in dialog._status.text()

    def test_an_imported_emblem_can_be_picked_straight_away(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "Straw Hat.png"))
        dialog._import.click()

        combo = emblem_combo(dialog, 0)
        assert combo.findData("straw-hat") >= 0

    def test_imported_emblems_are_listed(self, dialog: SettingsDialog, tmp_path: Path) -> None:
        assert dialog._installed.isEnabled() is False

        dialog.set_source(picture(tmp_path / "Straw Hat.png"))
        dialog._import.click()

        assert dialog._installed.isEnabled() is True
        assert dialog._installed.item(0).text() == "straw-hat"

    def test_an_imported_emblem_can_be_removed_again(
        self, dialog: SettingsDialog, tmp_path: Path, emblem_home: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "Straw Hat.png"))
        dialog._import.click()
        dialog._installed.setCurrentRow(0)

        assert dialog._discard.isEnabled() is True
        dialog._discard.click()

        assert not (emblem_home / "straw-hat").exists()
        assert dialog._installed.isEnabled() is False

    def test_importing_does_not_look_like_a_settings_edit(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        # Rebuilding the series table to show the new emblem must not be
        # mistaken for the user having changed a series.
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        dialog.set_source(picture(tmp_path / "a.png"))
        dialog._import.click()

        assert seen.calls == []
