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
from PySide6.QtWidgets import QComboBox, QFrame, QGroupBox, QLabel, QTableWidgetItem, QWidget

from mangame.domain.models import IconState
from mangame.i18n.catalog import Translator
from mangame.store.config import SeriesConfig, Settings
from mangame.ui import artwork, emblems
from mangame.ui.settings_dialog import (
    DARK_PANEL,
    LIGHT_PANEL,
    MIN_PARTIAL_MATCH,
    PAGE_MARGIN,
    PREVIEW_HEIGHT,
    PREVIEW_WIDTH,
    SHARED_EMBLEM,
    NameMatch,
    SettingsDialog,
    classify,
    emblem_choices,
    file_filter,
    heading,
    match_series,
    split_preview,
    squash,
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
        assert dialog._one_icon.isChecked() is False
        assert dialog._per_manga.isChecked() is True

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
        dialog._one_icon.setChecked(True)

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


class TestTrayMode:
    """Choosing between one icon for everything and one icon per manga.

    This is a choice between two pictures of your library, not a feature to
    switch on, so it is a pair of radios rather than a checkbox -- and the
    emblem the aggregate icon wears hangs off the option it belongs to.
    """

    def test_the_emblem_picker_only_applies_to_the_aggregate_icon(
        self, dialog: SettingsDialog
    ) -> None:
        # A control that cannot apply says so by being unavailable, rather
        # than by being explained in a sentence nobody reads.
        assert dialog._per_manga.isChecked() is True
        assert dialog._tray_emblem.isEnabled() is False

        dialog._one_icon.setChecked(True)
        assert dialog._tray_emblem.isEnabled() is True

        dialog._per_manga.setChecked(True)
        assert dialog._tray_emblem.isEnabled() is False

    def test_choosing_one_icon_for_everything_is_reported_once(
        self, dialog: SettingsDialog
    ) -> None:
        # Both radios move on every click; reacting to both would save twice.
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        dialog._one_icon.setChecked(True)

        assert len(seen.calls) == 1
        assert isinstance(seen.last, Settings)
        assert seen.last.single_tray_icon is True

    def test_choosing_one_icon_per_manga_is_reported_once(self, dialog: SettingsDialog) -> None:
        dialog.set_settings(settings().model_copy(update={"single_tray_icon": True}))
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        dialog._per_manga.setChecked(True)

        assert len(seen.calls) == 1
        assert isinstance(seen.last, Settings)
        assert seen.last.single_tray_icon is False

    def test_choosing_an_emblem_for_it_is_reported(self, dialog: SettingsDialog) -> None:
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        dialog._tray_emblem.setCurrentIndex(dialog._tray_emblem.findData("book"))

        assert isinstance(seen.last, Settings)
        assert seen.last.tray_emblem == "book"

    def test_the_picker_shows_what_each_emblem_looks_like(self, dialog: SettingsDialog) -> None:
        for row in range(dialog._tray_emblem.count()):
            assert not dialog._tray_emblem.itemIcon(row).isNull()

    def test_it_offers_the_app_mark_and_the_installed_artwork(self, dialog: SettingsDialog) -> None:
        offered = {dialog._tray_emblem.itemData(i) for i in range(dialog._tray_emblem.count())}
        assert {"mangame", "onepiece", "book"} <= offered

    def test_it_does_not_offer_the_monogram(self, dialog: SettingsDialog) -> None:
        # A monogram takes its letter and its hue from one series' title, and
        # the aggregate icon stands for all of them.
        offered = {dialog._tray_emblem.itemData(i) for i in range(dialog._tray_emblem.count())}
        assert emblems.MONOGRAM_EMBLEM not in offered

    def test_but_it_keeps_a_stored_choice_it_would_not_have_offered(
        self, dialog: SettingsDialog
    ) -> None:
        # Never silently rewrite what someone already chose.
        stored = emblems.MONOGRAM_EMBLEM
        dialog.set_settings(settings().model_copy(update={"tray_emblem": stored}))

        assert dialog._tray_emblem.currentData() == stored

    def test_imported_artwork_can_be_chosen_for_it(
        self, dialog: SettingsDialog, emblem_home: Path, tmp_path: Path
    ) -> None:
        artwork.install(picture(tmp_path / "crest.png"), "crest")
        dialog.set_settings(settings())

        offered = {dialog._tray_emblem.itemData(i) for i in range(dialog._tray_emblem.count())}
        assert "crest" in offered

    def test_being_handed_new_settings_is_not_an_edit(self, dialog: SettingsDialog) -> None:
        seen = Recorder()
        dialog.settings_changed.connect(seen)

        dialog.set_settings(
            settings().model_copy(update={"single_tray_icon": True, "tray_emblem": "book"})
        )

        assert dialog._one_icon.isChecked() is True
        assert dialog._tray_emblem.currentData() == "book"
        assert dialog._tray_emblem.isEnabled() is True
        assert seen.calls == []


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

    def test_a_picture_named_after_a_manga_is_offered_to_it(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "One Piece.png"))

        assert dialog.match() is NameMatch.MATCHED
        assert dialog.target() == "one-piece"
        assert dialog._import.isEnabled() is True

    def test_the_button_names_the_manga_it_is_about_to_change(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        # The confirmation that the name landed somewhere is the action label,
        # not a message beside it: a label cannot be read past.
        dialog.set_source(picture(tmp_path / "one-piece.png"))

        assert dialog._import.text() == "Use for One Piece"

    def test_a_picture_matching_nothing_cannot_be_imported(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        # This is the whole point: an unmatched name used to look exactly like
        # a matched one, and the import went somewhere nobody was looking.
        dialog.set_source(picture(tmp_path / "bleach-logo.png"))

        assert dialog.match() is NameMatch.NONE
        assert dialog.target() is None
        assert dialog._import.isEnabled() is False
        assert "bleach-logo" in dialog._verdict.text()

    def test_only_the_no_match_line_is_set_in_bold(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "bleach-logo.png"))
        assert dialog._verdict.font().bold() is True

        dialog.set_source(picture(tmp_path / "one-piece.png"))
        assert dialog._verdict.font().bold() is False

    def test_picking_a_manga_by_hand_unblocks_an_unmatched_picture(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "bleach-logo.png"))
        dialog._target.setCurrentIndex(dialog._target.findData("kagurabachi"))

        assert dialog.match() is NameMatch.CHOSEN
        assert dialog._import.isEnabled() is True
        assert dialog._import.text() == "Use for Kagurabachi"

    def test_a_shared_emblem_asks_for_a_name_instead(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "Straw Hat.png"))
        assert dialog._form.isRowVisible(dialog._name_row) is False

        dialog._target.setCurrentIndex(dialog._target.findData(SHARED_EMBLEM))

        assert dialog.match() is NameMatch.SHARED
        assert dialog._form.isRowVisible(dialog._name_row) is True
        assert dialog._name.text() == "straw-hat"
        assert dialog._import.isEnabled() is True

    def test_clearing_a_shared_name_blocks_the_import(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "a.png"))
        dialog._target.setCurrentIndex(dialog._target.findData(SHARED_EMBLEM))
        dialog._name.setText("   ")

        assert dialog._import.isEnabled() is False

    def test_the_suggested_name_follows_the_picture(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        # Otherwise a second import is filed under the first picture's name.
        dialog.set_source(picture(tmp_path / "Straw Hat.png"))
        dialog.set_source(picture(tmp_path / "Cursed Blade.png"))

        assert dialog._name.text() == "cursed-blade"

    def test_a_name_the_user_typed_is_left_alone(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "Straw Hat.png"))
        dialog._name.setText("mine")
        dialog._on_name_typed("mine")

        dialog.set_source(picture(tmp_path / "Cursed Blade.png"))

        assert dialog._name.text() == "mine"

    def test_the_empty_tab_shows_no_verdict_and_no_preview(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        # Captions under blank squares read as breakage, not as an example.
        assert dialog.match() is NameMatch.IDLE
        assert dialog._form.isRowVisible(dialog._verdict_row) is False
        assert dialog._preview_box.isHidden() is True

        dialog.set_source(picture(tmp_path / "a.png"))

        assert dialog._form.isRowVisible(dialog._verdict_row) is True
        assert dialog._preview_box.isHidden() is False

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

    def test_importing_writes_the_emblem_and_hands_it_to_the_manga(
        self, dialog: SettingsDialog, tmp_path: Path, emblem_home: Path
    ) -> None:
        # Installing and assigning are one action because they were always one
        # intention; separately, an import could appear to work and change
        # nothing anyone could see.
        drawn = Recorder()
        saved = Recorder()
        dialog.artwork_changed.connect(drawn)
        dialog.settings_changed.connect(saved)

        dialog.set_source(picture(tmp_path / "One Piece.png"))
        dialog._import.click()

        assert (emblem_home / "one-piece" / "ready" / "64.png").exists()
        assert (emblem_home / "one-piece" / "break" / "64.png").exists()
        assert len(drawn.calls) == 1
        assert isinstance(saved.last, Settings)
        assert saved.last.series[0].emblem == "one-piece"
        assert "One Piece" in dialog._status.text()

    def test_a_shared_emblem_is_installed_without_touching_any_manga(
        self, dialog: SettingsDialog, tmp_path: Path, emblem_home: Path
    ) -> None:
        saved = Recorder()
        dialog.settings_changed.connect(saved)

        dialog.set_source(picture(tmp_path / "Straw Hat.png"))
        dialog._target.setCurrentIndex(dialog._target.findData(SHARED_EMBLEM))
        dialog._import.click()

        assert (emblem_home / "straw-hat" / "ready" / "64.png").exists()
        assert saved.calls == []

    def test_an_imported_emblem_can_be_picked_straight_away(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "Straw Hat.png"))
        dialog._target.setCurrentIndex(dialog._target.findData(SHARED_EMBLEM))
        dialog._import.click()

        combo = emblem_combo(dialog, 0)
        assert combo.findData("straw-hat") >= 0

    def test_the_list_says_which_manga_wears_each_emblem(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        # An emblem nobody wears looks identical to one that is working, which
        # is how an import could appear to succeed while changing nothing.
        assert dialog._installed.isEnabled() is False

        dialog.set_source(picture(tmp_path / "Straw Hat.png"))
        dialog._target.setCurrentIndex(dialog._target.findData(SHARED_EMBLEM))
        dialog._import.click()

        assert dialog._installed.isEnabled() is True
        assert dialog._installed.item(0).text() == "straw-hat — not used by any manga"

        dialog.set_source(picture(tmp_path / "One Piece.png"))
        dialog._import.click()

        listed = {dialog._installed.item(i).text() for i in range(dialog._installed.count())}
        assert "one-piece — One Piece" in listed

    def test_an_imported_emblem_can_be_removed_again(
        self, dialog: SettingsDialog, tmp_path: Path, emblem_home: Path
    ) -> None:
        dialog.set_source(picture(tmp_path / "Straw Hat.png"))
        dialog._target.setCurrentIndex(dialog._target.findData(SHARED_EMBLEM))
        dialog._import.click()
        dialog._installed.setCurrentRow(0)

        assert dialog._discard.isEnabled() is True
        dialog._discard.click()

        # The row reads "straw-hat — not used by any manga"; the name it
        # removes has to come from the item's data, not its label.
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


class TestFlatLayout:
    def test_a_control_sits_one_margin_from_the_window_edge(self, dialog: SettingsDialog) -> None:
        # Three insets used to stack here: the dialog's layout, the tab pane's
        # frame and the page's own layout, putting 24px around everything.
        dialog.resize(560, 520)
        dialog.show()

        for index in range(dialog._tabs.count()):
            dialog._tabs.setCurrentIndex(index)
            page = dialog._tabs.currentWidget()
            controls = [w for w in page.findChildren(QWidget) if w.isVisible()]
            leftmost = min(w.mapTo(dialog, w.rect().topLeft()).x() for w in controls)
            assert leftmost == PAGE_MARGIN, dialog._tabs.tabText(index)

    def test_the_tab_pane_draws_no_frame(self, dialog: SettingsDialog) -> None:
        # Document mode is what removes the pane; without it the pages are
        # inset again and the margin above is measured from the wrong place.
        assert dialog._tabs.documentMode() is True

    def test_the_views_have_no_sunken_border(self, dialog: SettingsDialog) -> None:
        assert dialog._series.frameShape() == QFrame.Shape.NoFrame
        assert dialog._installed.frameShape() == QFrame.Shape.NoFrame

    def test_sections_are_titled_by_weight_rather_than_a_box(self, dialog: SettingsDialog) -> None:
        # Fusion keeps drawing a group box's frame even when asked for a flat
        # one, so the artwork tab uses labels and must not grow boxes again.
        assert dialog.findChildren(QGroupBox) == []
        titles = {label.text() for label in dialog.findChildren(QLabel) if label.font().bold()}
        assert titles == {
            dialog._t("dialog.settings.tray.heading"),
            dialog._t("dialog.settings.art.preview"),
            dialog._t("dialog.settings.art.yours"),
        }

    def test_a_heading_is_the_only_thing_the_helper_changes(self) -> None:
        parent = QWidget()
        label = heading("Preview", parent)

        assert label.text() == "Preview"
        assert label.font().bold() is True
        assert label.parent() is parent

    def test_the_preview_row_keeps_its_shape_before_and_after_a_picture(
        self, dialog: SettingsDialog, tmp_path: Path
    ) -> None:
        # Every caption is a different length, and one of them wraps in German;
        # without a reserved cell the row is ragged and jumps when it fills in.
        dialog.show()
        empty = [(w.width(), w.height()) for w in dialog._previews.values()]

        dialog.set_source(picture(tmp_path / "a.png"))

        assert {w.width() for w in dialog._previews.values()} == {PREVIEW_WIDTH}
        assert all(w.height() >= PREVIEW_HEIGHT for w in dialog._previews.values())
        assert [(w.width(), w.height()) for w in dialog._previews.values()] == empty


class TestNameMatching:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Hunter x Hunter", "hunterxhunter"),
            ("hunter-x-hunter", "hunterxhunter"),
            ("hunterxhunter", "hunterxhunter"),
            ("Spy × Family", "spyfamily"),  # noqa: RUF001
            ("", ""),
        ],
    )
    def test_titles_keys_and_file_names_reduce_to_one_form(self, text: str, expected: str) -> None:
        assert squash(text) == expected

    def test_a_title_always_recognises_itself(self) -> None:
        # The looser match has to be at least as permissive as the identity
        # rule, or a file named exactly after a series would still miss it.
        for entry in settings().series:
            assert match_series(entry.title, settings().series) == entry.key
            assert match_series(entry.key, settings().series) == entry.key

    def test_punctuation_is_not_a_reason_to_miss(self) -> None:
        # The failure that prompted all this: artwork saved as
        # "hunterxhunter.png" landed nowhere, because the key is
        # "hunter-x-hunter" and nothing said the two were the same manga.
        series = [SeriesConfig(key="hunter-x-hunter", title="Hunter x Hunter")]

        assert match_series("hunterxhunter", series) == "hunter-x-hunter"
        assert match_series("HUNTER X HUNTER", series) == "hunter-x-hunter"

    def test_a_file_name_that_carries_the_title_still_matches(self) -> None:
        assert match_series("onepiece-hat", settings().series) == "one-piece"
        assert match_series("one-piece-logo-final", settings().series) == "one-piece"

    def test_a_stub_too_short_to_mean_anything_matches_nothing(self) -> None:
        short = "one"
        assert len(short) < MIN_PARTIAL_MATCH
        assert match_series(short, settings().series) is None

    def test_two_candidates_are_not_a_match(self) -> None:
        # Guessing between them would attach artwork to the wrong manga, and
        # nothing afterwards would look wrong enough to notice.
        series = [
            SeriesConfig(key="one-piece", title="One Piece"),
            SeriesConfig(key="one-punch-man", title="One Punch Man"),
        ]
        assert match_series("onep", series) is None

    def test_an_exact_match_beats_a_longer_neighbour(self) -> None:
        series = [
            SeriesConfig(key="bleach", title="Bleach"),
            SeriesConfig(key="bleach-remix", title="Bleach Remix"),
        ]
        assert match_series("bleach", series) == "bleach"

    @pytest.mark.parametrize("stem", ["", "   ", "!!!"])
    def test_a_name_with_no_letters_matches_nothing(self, stem: str) -> None:
        assert match_series(stem, settings().series) is None

    def test_nothing_is_matched_against_an_empty_library(self) -> None:
        assert match_series("one-piece", []) is None

    @pytest.mark.parametrize(
        ("source", "chosen", "matched", "expected"),
        [
            (None, None, None, NameMatch.IDLE),
            (None, "one-piece", "one-piece", NameMatch.IDLE),
            (Path("a.png"), SHARED_EMBLEM, None, NameMatch.SHARED),
            (Path("a.png"), None, None, NameMatch.NONE),
            (Path("a.png"), "one-piece", "one-piece", NameMatch.MATCHED),
            (Path("a.png"), "one-piece", "kagurabachi", NameMatch.CHOSEN),
            (Path("a.png"), "one-piece", None, NameMatch.CHOSEN),
        ],
    )
    def test_where_the_chosen_manga_came_from(
        self, source: Path | None, chosen: str | None, matched: str | None, expected: NameMatch
    ) -> None:
        assert classify(source, chosen, matched) is expected
