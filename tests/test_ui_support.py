"""Menu translations, emblem resolution and menu placement — the pure UI bits."""

import re
from pathlib import Path
from statistics import mean, median
from typing import ClassVar

import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QColor, QImage

from mangame.domain.models import IconState
from mangame.i18n.catalog import _CATALOGS, _EN, LANGUAGES, Translator, available
from mangame.ui import emblems
from mangame.ui.menu import fitted_position, menu_anchor


class TestTranslator:
    def test_english_is_the_baseline(self) -> None:
        assert Translator("en")("menu.quit") == "Quit mangame"

    def test_a_translated_language_is_used(self) -> None:
        assert Translator("de")("dialog.settings.language") == "Lesesprache"

    def test_an_unknown_language_falls_back_to_english(self) -> None:
        assert Translator("kl")("menu.quit") == Translator("en")("menu.quit")

    def test_language_codes_are_matched_case_insensitively(self) -> None:
        assert Translator("DE")("dialog.settings.language") == "Lesesprache"

    def test_conventional_region_casing_is_understood(self) -> None:
        assert Translator("es-MX").language == "es"

    def test_an_os_locale_degrades_to_its_base_language(self) -> None:
        assert Translator("de_DE.UTF-8").language == "de"
        assert Translator("en-GB").language == "en"

    def test_a_language_we_cannot_poll_for_is_not_offered(self) -> None:
        # Reading language and menu language are the same setting, so a
        # catalog we cannot fetch chapters for would be a promise we break.
        assert Translator("ja").language == "en"
        assert "ja" not in available()

    def test_an_unknown_key_returns_something_showable(self) -> None:
        # Better a visible key than a blank menu entry.
        assert Translator("en")("menu.nonexistent")

    @pytest.mark.parametrize("code", sorted(LANGUAGES))
    def test_every_offered_language_covers_every_label(self, code: str) -> None:
        translate = Translator(code)
        for key in _EN:
            assert translate(key), f"{code} has nothing for {key}"

    @pytest.mark.parametrize("code", sorted(_CATALOGS))
    def test_no_catalog_invents_keys_english_does_not_have(self, code: str) -> None:
        assert set(_CATALOGS[code]) <= set(_EN)

    @pytest.mark.parametrize("code", sorted(_CATALOGS))
    def test_every_catalog_uses_the_same_placeholders(self, code: str) -> None:
        # A translation that renames {count} would raise KeyError at the moment
        # the dialog tries to show its result count.
        placeholders = re.compile(r"\{(\w+)\}")
        for key, text in _CATALOGS[code].items():
            assert set(placeholders.findall(text)) == set(placeholders.findall(_EN[key])), key

    def test_every_catalog_is_offered_in_the_menu(self) -> None:
        assert set(_CATALOGS) <= set(LANGUAGES)

    def test_available_lists_languages_in_their_own_language(self) -> None:
        assert available()["es"] == "Español"
        assert available()["de"] == "Deutsch"

    @pytest.mark.parametrize("tag", ["", "zz-ZZ", "ja"])
    def test_an_unrecognisable_tag_still_yields_a_usable_menu(self, tag: str) -> None:
        # Folding happens in i18n.languages; what matters here is that the
        # menu never comes back blank.
        assert Translator(tag)("menu.quit") == _EN["menu.quit"]


#: Every emblem shipped in the package. "mangame" is the app's own mark, worn
#: by the aggregate icon; the other two are series artwork.
BUNDLED = ["onepiece", "book", "mangame"]


class TestEmblems:
    @pytest.mark.parametrize("emblem", BUNDLED)
    def test_the_bundled_artwork_is_shipped(self, emblem: str) -> None:
        assert emblem in emblems.available_emblems()

    @pytest.mark.parametrize("emblem", BUNDLED)
    @pytest.mark.parametrize("state", list(IconState))
    def test_every_emblem_has_artwork_for_every_state(self, emblem: str, state: IconState) -> None:
        found = emblems._find(emblem, state)
        assert found is not None, f"{emblem}/{state.value} has no artwork"
        assert found.is_dir() or found.is_file()

    @pytest.mark.parametrize("emblem", BUNDLED)
    def test_bundled_artwork_covers_the_sizes_a_panel_may_ask_for(self, emblem: str) -> None:
        for state in IconState:
            directory = emblems.BUNDLED_DIR / emblem / state.value
            present = {int(p.stem) for p in directory.glob("*.png") if p.stem.isdigit()}
            assert set(emblems.SIZES) <= present

    def test_user_artwork_takes_priority_over_bundled(self, tmp_path: Path) -> None:
        assert emblems.emblem_roots()[0] != emblems.BUNDLED_DIR
        assert emblems.BUNDLED_DIR in emblems.emblem_roots()

    def test_the_monogram_is_not_offered_as_artwork(self) -> None:
        assert emblems.MONOGRAM_EMBLEM not in emblems.available_emblems()
        assert emblems.selectable_emblems()[0] == emblems.MONOGRAM_EMBLEM


class TestAppMark:
    """The app's own icon has to carry the same three states a series does.

    That is the whole point of it: the tray says "something is ready" the same
    way whether it is showing one manga or standing in for thirty. So rather
    than pin the mark to invented numbers, every assertion here measures it
    against the series artwork that has always been on the panel.
    """

    #: The artwork the app mark has to hold its own next to.
    SERIES: ClassVar[list[str]] = ["onepiece", "book"]

    @staticmethod
    def _pixels(emblem: str, state: IconState, size: int = 22) -> list[QColor]:
        image = QImage(str(emblems.BUNDLED_DIR / emblem / state.value / f"{size}.png"))
        found = [
            image.pixelColor(x, y)
            for y in range(image.height())
            for x in range(image.width())
            if image.pixelColor(x, y).alpha() > 200
        ]
        assert found, f"{emblem}/{state.value} rendered nothing"
        return found

    @classmethod
    def _colour(cls, emblem: str, state: IconState) -> float:
        pixels = cls._pixels(emblem, state)
        return mean(c.saturationF() for c in pixels)

    @classmethod
    def _body(cls, emblem: str, state: IconState) -> float:
        """Median lightness — the mark's body, not its outline.

        The break state is a dark silhouette wearing a light rim, so its *mean*
        lightness says nothing: on a thin shape the rim outweighs the body and
        the average lands in the middle.
        """
        return median(c.lightnessF() for c in cls._pixels(emblem, state))

    def test_ready_is_the_only_state_with_colour(self) -> None:
        ready = self._colour("mangame", IconState.READY)
        assert ready >= min(self._colour(e, IconState.READY) for e in self.SERIES)
        assert self._colour("mangame", IconState.DUE) == 0.0
        assert self._colour("mangame", IconState.BREAK) == 0.0

    def test_the_states_get_darker_as_the_news_gets_worse(self) -> None:
        due = self._body("mangame", IconState.DUE)
        assert self._body("mangame", IconState.READY) < due
        assert self._body("mangame", IconState.BREAK) < due

    @pytest.mark.parametrize("state", list(IconState))
    def test_its_body_is_as_dark_as_the_series_artwork(self, state: IconState) -> None:
        # A letter has far less area per unit of outline than a hat or a book,
        # so an outline sized for those turns the mark into a line drawing
        # instead of a silhouette. This is what catches that.
        series = [self._body(e, state) for e in self.SERIES]
        assert self._body("mangame", state) <= max(series) + 0.05

    def test_the_break_silhouette_keeps_a_light_rim(self) -> None:
        # Without it a near-black mark disappears on a dark panel.
        lightest = max(c.lightnessF() for c in self._pixels("mangame", IconState.BREAK, 64))
        assert lightest > 0.7

    def test_it_is_not_the_same_picture_as_a_series_emblem(self) -> None:
        mark = QImage(str(emblems.BUNDLED_DIR / "mangame" / "ready" / "64.png"))
        for other in self.SERIES:
            assert mark != QImage(str(emblems.BUNDLED_DIR / other / "ready" / "64.png"))


class TestMonogramFallback:
    """A series without artwork must still look like itself.

    ``emblem_for`` hands every series but One Piece the name ``monogram``, and
    that used to resolve through a "book" fallback — so every one of them wore
    the identical stand-in and the generated badge was unreachable.
    """

    @staticmethod
    def rendered(emblem: str, title: str, state: IconState = IconState.READY) -> bytes:
        image = emblems.icon_for(emblem, state, title).pixmap(64, 64).toImage()
        return bytes(image.constBits())

    def test_asking_for_a_monogram_does_not_give_the_book(self, qapp: object) -> None:
        assert self.rendered("monogram", "Kagurabachi") != self.rendered("book", "Kagurabachi")

    def test_two_series_without_artwork_look_different(self, qapp: object) -> None:
        assert self.rendered("monogram", "Kagurabachi") != self.rendered("monogram", "Sakamoto")

    def test_artwork_that_was_deleted_falls_back_to_the_monogram(self, qapp: object) -> None:
        assert self.rendered("no-such-emblem", "Kagurabachi") == self.rendered(
            "monogram", "Kagurabachi"
        )

    @pytest.mark.parametrize("state", list(IconState))
    def test_each_state_still_looks_different(self, state: IconState, qapp: object) -> None:
        others = [s for s in IconState if s is not state]
        mine = self.rendered("monogram", "Kagurabachi", state)
        assert all(mine != self.rendered("monogram", "Kagurabachi", other) for other in others)

    def test_real_artwork_is_still_preferred(self, qapp: object) -> None:
        assert self.rendered("onepiece", "One Piece") != self.rendered("monogram", "One Piece")


class TestMenuAnchor:
    """Where a tray menu is asked to appear when its icon is clicked."""

    CURSOR = QPoint(1720, 1420)

    def test_it_follows_the_icon_where_the_desktop_reports_one(self) -> None:
        assert menu_anchor(QRect(1700, 1400, 24, 24), self.CURSOR) == QPoint(1700, 1400)

    def test_it_falls_back_to_the_pointer_where_the_desktop_does_not(self) -> None:
        # StatusNotifierItem hosts draw the icon themselves and hand Qt an
        # empty rectangle, so on KDE and GNOME this is the only branch taken.
        assert menu_anchor(QRect(), self.CURSOR) == self.CURSOR
        assert menu_anchor(QRect(0, 0, 0, 0), self.CURSOR) == self.CURSOR


class TestMenuFitting:
    """The work area of this developer's KDE box: a 44px panel at the bottom."""

    AREA = QRect(0, 0, 3440, 1396)
    SCREEN = QRect(0, 0, 3440, 1440)

    def test_a_menu_already_inside_the_work_area_is_left_alone(self) -> None:
        frame = QRect(3139, 1200, 301, 114)
        assert fitted_position(frame, self.AREA) == frame.topLeft()

    def test_a_menu_hanging_behind_the_panel_is_lifted_clear_of_it(self) -> None:
        # What Qt actually produced: bottom flush with the screen, not the
        # work area, so the last 44px sat underneath the panel.
        frame = QRect(3139, 1326, 301, 114)
        assert frame.bottom() == self.SCREEN.bottom()

        moved = fitted_position(frame, self.AREA)
        assert moved.x() == frame.x()
        assert moved.y() + frame.height() - 1 == self.AREA.bottom()

    def test_a_submenu_running_off_the_right_edge_is_pulled_back(self) -> None:
        frame = QRect(3400, 500, 137, 90)
        moved = fitted_position(frame, self.AREA)
        assert moved.x() + frame.width() - 1 == self.AREA.right()
        assert moved.y() == frame.y()

    def test_a_menu_off_the_top_left_is_pushed_into_view(self) -> None:
        assert fitted_position(QRect(-40, -20, 137, 90), self.AREA) == QPoint(0, 0)

    def test_a_menu_taller_than_the_work_area_stays_reachable_from_the_top(self) -> None:
        # Qt adds scroll arrows in this case; the top must remain visible.
        moved = fitted_position(QRect(100, 300, 137, 2000), self.AREA)
        assert moved == QPoint(100, self.AREA.top())

    def test_an_offset_work_area_is_respected(self) -> None:
        # A panel on the left and on the top, e.g. Unity-style.
        area = QRect(64, 32, 3376, 1408)
        assert fitted_position(QRect(0, 0, 137, 90), area) == QPoint(64, 32)
