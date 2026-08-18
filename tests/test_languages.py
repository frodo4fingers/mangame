"""The reading-language registry.

The language setting decides which sources are polled and which chapters count
as readable, so folding tags onto a canonical code is load-bearing rather than
cosmetic: a code no source can serve means an icon that never turns colour.
"""

import pytest

from mangame.i18n import languages


class TestSupportedLanguages:
    def test_the_three_supported_languages_are_offered(self) -> None:
        assert languages.codes() == ("en", "es", "de")

    def test_labels_are_written_in_their_own_language(self) -> None:
        assert languages.labels() == {"en": "English", "es": "Español", "de": "Deutsch"}

    def test_the_default_is_one_we_support(self) -> None:
        assert languages.DEFAULT in languages.codes()


class TestNormalisation:
    @pytest.mark.parametrize(
        ("tag", "expected"),
        [
            ("en", "en"),
            ("de", "de"),
            ("es", "es"),
            ("ES", "es"),
            ("es-la", "es"),  # MangaDex's Latin-American Spanish
            ("es-419", "es"),  # the UN region code some sites use
            ("es_MX.UTF-8", "es"),  # an OS locale
            ("de-AT", "de"),
            ("en-GB", "en"),
            ("  DE  ", "de"),
        ],
    )
    def test_a_tag_folds_onto_the_language_it_belongs_to(self, tag: str, expected: str) -> None:
        assert languages.normalize(tag) == expected

    @pytest.mark.parametrize("tag", ["ja", "pt-br", "fr", "it", "zz-ZZ", "", "   "])
    def test_a_language_we_cannot_serve_degrades_to_the_default(self, tag: str) -> None:
        assert languages.normalize(tag) == languages.DEFAULT


class TestSourceCodes:
    def test_spanish_asks_for_both_regional_codes(self) -> None:
        # MangaDex splits Spanish into "es" and "es-la"; a reader who chose
        # Spanish is waiting for whichever arrives first.
        assert languages.source_codes("es") == ("es", "es-la")

    def test_a_single_code_language_asks_for_exactly_one(self) -> None:
        assert languages.source_codes("de") == ("de",)
        assert languages.source_codes("en") == ("en",)

    def test_the_canonical_code_is_asked_for_first(self) -> None:
        for language in languages.SUPPORTED:
            assert language.source_codes[0] == language.code

    def test_every_code_we_ask_for_folds_back_onto_its_language(self) -> None:
        # Without this round trip a chapter could be fetched under one code and
        # then stored under a language nobody ever queries.
        for language in languages.SUPPORTED:
            for code in language.source_codes:
                assert languages.canonical(code) == language.code

    def test_no_code_is_claimed_by_two_languages(self) -> None:
        claimed = [code for language in languages.SUPPORTED for code in language.source_codes]
        assert len(claimed) == len(set(claimed))


class TestLookup:
    def test_a_known_code_returns_its_record(self) -> None:
        assert languages.get("es").label == "Español"

    def test_an_unknown_code_returns_the_default_rather_than_raising(self) -> None:
        assert languages.get("ja").code == languages.DEFAULT
