"""The tray, driven for real.

These tests build a ``MangameTray`` against a throwaway config and data
directory and then look at the icons it produced — not at what it intended to
produce. An icon that is set but never shown, or shown wearing the wrong
artwork, is exactly the kind of bug that only pixels catch.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from mangame.domain.models import IconState
from mangame.store import config
from mangame.store.config import SeriesConfig, Settings
from mangame.ui.emblems import icon_for
from mangame.ui.tray import MangameTray

SERIES = [
    SeriesConfig(key="one-piece", title="One Piece", emblem="onepiece"),
    SeriesConfig(key="berserk", title="Berserk", emblem="book"),
]


def pixels(icon: QIcon, size: int = 22) -> bytes:
    """The actual rasterised icon, so two icons can be compared as pictures."""
    image = icon.pixmap(size, size).toImage()
    return bytes(image.constBits())


@pytest.fixture
def tray(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qapp: QApplication
) -> Iterator[MangameTray]:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    config.save(Settings(series=SERIES))
    built = MangameTray(qapp)
    yield built
    built.shutdown()


def rebuild(tray: MangameTray, **changes: object) -> None:
    """Save a settings change the way the settings dialog does, then redraw."""
    config.save(config.load().model_copy(update=changes))
    tray._reload_settings()
    tray.refresh()


class TestAggregateIcon:
    """One icon standing for the whole library wears the app's own mark.

    It used to wear One Piece's straw hat, hardcoded, so a library of thirty
    titles looked like one of them.
    """

    def test_it_wears_the_app_mark_by_default(self, tray: MangameTray) -> None:
        rebuild(tray, single_tray_icon=True)
        icon = tray._icons["__all__"]
        assert pixels(icon.icon()) == pixels(icon_for("mangame", IconState.DUE, "mangame"))

    def test_it_does_not_wear_any_series_emblem(self, tray: MangameTray) -> None:
        rebuild(tray, single_tray_icon=True)
        shown = pixels(tray._icons["__all__"].icon())
        for series in SERIES:
            assert shown != pixels(icon_for(series.emblem, IconState.DUE, series.title))

    def test_choosing_another_emblem_changes_the_picture(self, tray: MangameTray) -> None:
        rebuild(tray, single_tray_icon=True)
        before = pixels(tray._icons["__all__"].icon())
        rebuild(tray, tray_emblem="book")
        after = pixels(tray._icons["__all__"].icon())
        assert before != after
        assert after == pixels(icon_for("book", IconState.DUE, "mangame"))

    def test_an_emblem_that_went_missing_falls_back_rather_than_blanking(
        self, tray: MangameTray
    ) -> None:
        rebuild(tray, single_tray_icon=True, tray_emblem="deleted-by-hand")
        assert not tray._icons["__all__"].icon().isNull()


class TestOneIconPerManga:
    def test_every_tracked_series_gets_its_own_icon(self, tray: MangameTray) -> None:
        rebuild(tray, single_tray_icon=False)
        assert set(tray._icons) == {"one-piece", "berserk"}

    def test_each_icon_wears_that_series_own_emblem(self, tray: MangameTray) -> None:
        rebuild(tray, single_tray_icon=False)
        for series in SERIES:
            shown = pixels(tray._icons[series.key].icon())
            assert shown == pixels(icon_for(series.emblem, IconState.DUE, series.title))

    def test_switching_modes_clears_up_after_itself(self, tray: MangameTray) -> None:
        # Both directions: a stale icon left behind is a duplicate in the panel.
        rebuild(tray, single_tray_icon=True)
        assert set(tray._icons) == {"__all__"}
        rebuild(tray, single_tray_icon=False)
        assert "__all__" not in tray._icons
        rebuild(tray, single_tray_icon=True)
        assert set(tray._icons) == {"__all__"}

    def test_a_series_hidden_from_the_tray_has_no_icon(self, tray: MangameTray) -> None:
        hidden = [SERIES[0], SERIES[1].model_copy(update={"show_in_tray": False})]
        rebuild(tray, single_tray_icon=False, series=hidden)
        assert set(tray._icons) == {"one-piece"}

    def test_hiding_every_series_falls_back_to_the_aggregate(self, tray: MangameTray) -> None:
        # Otherwise the app vanishes from the panel with no way back to it.
        hidden = [s.model_copy(update={"show_in_tray": False}) for s in SERIES]
        rebuild(tray, single_tray_icon=False, series=hidden)
        assert set(tray._icons) == {"__all__"}


class TestClickingTheIcon:
    """A tray icon has no affordance but the picture, so the first click has
    to lead somewhere — and the menu is the only somewhere there is."""

    @staticmethod
    def click(tray: MangameTray, key: str, reason: QSystemTrayIcon.ActivationReason) -> QMenu:
        tray._icons[key].activated.emit(reason)
        menu = tray._icons[key].contextMenu()
        assert menu is not None
        return menu

    @pytest.mark.parametrize(
        "reason",
        [
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ],
    )
    def test_a_left_click_opens_the_menu(
        self, tray: MangameTray, reason: QSystemTrayIcon.ActivationReason
    ) -> None:
        rebuild(tray, single_tray_icon=True)
        assert self.click(tray, "__all__", reason).isVisible()

    @pytest.mark.parametrize(
        "reason",
        [
            QSystemTrayIcon.ActivationReason.Context,
            QSystemTrayIcon.ActivationReason.MiddleClick,
            QSystemTrayIcon.ActivationReason.Unknown,
        ],
    )
    def test_nothing_else_raises_it_a_second_time(
        self, tray: MangameTray, reason: QSystemTrayIcon.ActivationReason
    ) -> None:
        # The right button already has a menu, from the platform. Popping our
        # own on top of that fights it; middle-click never asked for one.
        rebuild(tray, single_tray_icon=True)
        assert not self.click(tray, "__all__", reason).isVisible()

    def test_the_menu_is_the_one_belonging_to_the_icon_clicked(self, tray: MangameTray) -> None:
        rebuild(tray, single_tray_icon=False)
        self.click(tray, "berserk", QSystemTrayIcon.ActivationReason.Trigger)

        assert tray._icons["berserk"].contextMenu().isVisible()
        assert not tray._icons["one-piece"].contextMenu().isVisible()

    def test_a_click_does_not_open_a_chapter_behind_your_back(
        self, tray: MangameTray, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # It used to, whenever the series happened to be READY -- silently
        # marking it read as it went. Nothing on an icon says it is clickable,
        # let alone that it is clickable only sometimes.
        opened: list[str] = []
        monkeypatch.setattr(tray, "_open", opened.append)
        rebuild(tray, single_tray_icon=False)
        tray._last_state["one-piece"] = IconState.READY

        self.click(tray, "one-piece", QSystemTrayIcon.ActivationReason.Trigger)

        assert opened == []

    def test_a_refresh_does_not_pull_an_open_menu_out_from_under_you(
        self, tray: MangameTray
    ) -> None:
        # The tray re-derives state every minute, and rebuilding the menu drops
        # the last reference to the one on screen. A menu that vanishes -- or
        # takes the process with it -- mid-click is worse than a stale one.
        rebuild(tray, single_tray_icon=True)
        menu = self.click(tray, "__all__", QSystemTrayIcon.ActivationReason.Trigger)

        tray.refresh()

        assert menu.isVisible()
        assert tray._icons["__all__"].contextMenu() is menu
