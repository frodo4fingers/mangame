"""Menu translations and emblem resolution — the two UI-adjacent pure bits."""

from pathlib import Path

import pytest

from mangame.domain.models import IconState
from mangame.i18n.catalog import _CATALOGS, _EN, LANGUAGES, Translator, available, normalize
from mangame.ui import emblems


class TestTranslator:
    def test_english_is_the_baseline(self) -> None:
        assert Translator("en")("menu.quit") == "Quit mangame"

    def test_a_translated_language_is_used(self) -> None:
        assert Translator("de")("menu.language") == "Sprache"

    def test_an_unknown_language_falls_back_to_english(self) -> None:
        assert Translator("kl")("menu.quit") == Translator("en")("menu.quit")

    def test_language_codes_are_matched_case_insensitively(self) -> None:
        assert Translator("DE")("menu.language") == "Sprache"

    def test_conventional_region_casing_is_understood(self) -> None:
        assert Translator("pt-BR").language == "pt-br"

    def test_an_os_locale_degrades_to_its_base_language(self) -> None:
        assert Translator("de_DE.UTF-8").language == "de"
        assert Translator("fr-CA").language == "fr"

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

    def test_every_catalog_is_offered_in_the_menu(self) -> None:
        assert set(_CATALOGS) <= set(LANGUAGES)

    def test_available_lists_languages_in_their_own_language(self) -> None:
        assert available()["ja"] == "日本語"

    def test_an_unrecognisable_tag_still_yields_english(self) -> None:
        assert normalize("") == "en"
        assert normalize("zz-ZZ") == "en"


class TestEmblems:
    def test_the_bundled_artwork_is_shipped(self) -> None:
        assert "strawhat" in emblems.available_emblems()
        assert "book" in emblems.available_emblems()

    @pytest.mark.parametrize("emblem", ["strawhat", "book"])
    @pytest.mark.parametrize("state", list(IconState))
    def test_every_emblem_has_artwork_for_every_state(self, emblem: str, state: IconState) -> None:
        found = emblems._find(emblem, state)
        assert found is not None, f"{emblem}/{state.value} has no artwork"
        assert found.is_dir() or found.is_file()

    def test_bundled_artwork_covers_the_sizes_a_panel_may_ask_for(self) -> None:
        for state in IconState:
            directory = emblems.BUNDLED_DIR / "strawhat" / state.value
            present = {int(p.stem) for p in directory.glob("*.png") if p.stem.isdigit()}
            assert set(emblems.SIZES) <= present

    def test_user_artwork_takes_priority_over_bundled(self, tmp_path: Path) -> None:
        assert emblems.emblem_roots()[0] != emblems.BUNDLED_DIR
        assert emblems.BUNDLED_DIR in emblems.emblem_roots()
