"""The add-manga dialog: grouping, ranking and the language-filtered search.

Everything here runs without a display. The dialog's own logic lives in
``group_matches``/``SeriesCandidate`` precisely so the interesting decisions —
which rows appear, which source represents a row, what Add will link — can be
asserted directly instead of driven through widgets.
"""

import asyncio

import httpx
import pytest
import respx

from mangame.sources import anilist, mangadex, mangaupdates
from mangame.sources.base import SourceMatch
from mangame.store.config import series_key
from mangame.ui.add_dialog import SeriesCandidate, group_matches, title_key
from mangame.ui.worker import SearchWorker


def match(source_id: str, title: str, ref: str = "r", year: int | None = None) -> SourceMatch:
    return SourceMatch(source_id=source_id, ref=ref, title=title, year=year)


class TestGrouping:
    def test_one_series_found_by_three_sources_is_one_row(self) -> None:
        # The old dialog listed these as three separate entries even though
        # picking any of them produced the identical tracked series.
        candidates = group_matches(
            [
                match("mangadex", "One Piece", "md", 1997),
                match("mangaupdates", "One Piece", "mu"),
                match("anilist", "One Piece", "al", 1997),
            ]
        )
        assert len(candidates) == 1
        assert candidates[0].source_ids == ("mangadex", "mangaupdates", "anilist")

    def test_different_series_stay_separate(self) -> None:
        candidates = group_matches(
            [match("mangadex", "One Piece"), match("mangadex", "One Piece Party")]
        )
        assert [c.title for c in candidates] == ["One Piece", "One Piece Party"]

    def test_titles_are_matched_the_way_tracking_matches_them(self) -> None:
        candidates = group_matches(
            [match("mangadex", "One Piece"), match("anilist", "  ONE PIECE  ")]
        )
        assert len(candidates) == 1, "grouping must agree with _track's cross-linking"

    def test_source_order_is_preserved(self) -> None:
        # Each source ranks its own results by relevance; re-sorting here would
        # replace that with an ordering of our own invention.
        candidates = group_matches(
            [match("mangadex", "B"), match("mangadex", "A"), match("anilist", "C")]
        )
        assert [c.title for c in candidates] == ["B", "A", "C"]

    def test_a_year_from_any_source_is_used(self) -> None:
        candidates = group_matches(
            [match("mangaupdates", "Berserk"), match("anilist", "Berserk", year=1989)]
        )
        assert candidates[0].year == 1989

    def test_nothing_found_is_no_rows(self) -> None:
        assert group_matches([]) == []


class TestTracked:
    """Flagged exactly when adding would be refused, never merely when it looks alike."""

    def test_a_series_already_tracked_is_flagged(self) -> None:
        # Adding it again silently did nothing; saying so is the whole point.
        candidates = group_matches([match("mangadex", "One Piece")], ["one-piece"])
        assert candidates[0].tracked

    def test_the_flag_ignores_case_and_punctuation(self) -> None:
        # "One Piece!" is stored under the same key, so Add would be refused —
        # comparing titles would have shown it as addable.
        candidates = group_matches([match("mangadex", "One Piece!")], ["one-piece"])
        assert candidates[0].tracked

    def test_the_flag_uses_the_key_the_store_uses(self) -> None:
        title = "One Piece: Ace's Story"
        candidates = group_matches([match("mangadex", title)], [series_key(title)])
        assert candidates[0].tracked

    def test_an_untracked_series_is_not_flagged(self) -> None:
        candidates = group_matches([match("mangadex", "One Piece")], ["berserk"])
        assert not candidates[0].tracked

    @pytest.mark.parametrize(
        "title", ["One Piece", "One Piece!", "ONE PIECE", "one   piece", "  One Piece  "]
    )
    def test_every_spelling_the_store_would_refuse_is_flagged(self, title: str) -> None:
        assert group_matches([match("mangadex", title)], ["one-piece"])[0].tracked

    def test_the_detail_line_says_so(self) -> None:
        candidate = group_matches([match("mangadex", "One Piece")], ["one-piece"])[0]
        assert candidate.detail("already tracked") == "mangadex — already tracked"

    def test_the_detail_line_is_just_sources_otherwise(self) -> None:
        matches = [match("mangadex", "One Piece"), match("anilist", "One Piece")]
        assert group_matches(matches)[0].detail("already tracked") == "mangadex · anilist"


class TestPrimarySource:
    def test_a_chapter_source_represents_the_group(self) -> None:
        # AniList answered first here, but it never reports chapters, so
        # anchoring the series to it would give an icon that cannot turn.
        candidate = group_matches(
            [match("anilist", "One Piece", "al"), match("mangadex", "One Piece", "md")]
        )[0]
        assert candidate.primary.source_id == "mangadex"
        assert candidate.primary.ref == "md"

    def test_the_only_source_represents_the_group(self) -> None:
        candidate = group_matches([match("anilist", "Obscure", "al")])[0]
        assert candidate.primary.source_id == "anilist"

    def test_an_unranked_source_still_works(self) -> None:
        candidate = group_matches([match("somethingelse", "Obscure", "x")])[0]
        assert candidate.primary.source_id == "somethingelse"

    def test_the_title_shown_is_the_primary_source_title(self) -> None:
        candidate = group_matches(
            [match("anilist", "ONE PIECE", "al"), match("mangadex", "One Piece", "md")]
        )[0]
        assert candidate.title == "One Piece"


class TestLabels:
    def test_a_year_is_shown_when_known(self) -> None:
        assert (
            SeriesCandidate(
                title="One Piece", year=1997, matches=(match("mangadex", "One Piece"),)
            ).label()
            == "One Piece (1997)"
        )

    def test_no_year_means_no_empty_brackets(self) -> None:
        assert (
            SeriesCandidate(title="One Piece", matches=(match("mangadex", "One Piece"),)).label()
            == "One Piece"
        )

    @pytest.mark.parametrize(
        ("title", "expected"), [("One Piece", "one piece"), ("  Berserk ", "berserk")]
    )
    def test_title_key_normalises(self, title: str, expected: str) -> None:
        assert title_key(title) == expected


class TestLanguageFilteredSearch:
    """Search and poll have to agree about which sources are worth asking."""

    @staticmethod
    def _routes() -> dict[str, respx.Route]:
        return {
            "mangadex": respx.get(f"{mangadex.API}/manga").mock(
                return_value=httpx.Response(200, json={"result": "ok", "data": []})
            ),
            "mangaupdates": respx.post(f"{mangaupdates.API}/series/search").mock(
                return_value=httpx.Response(200, json={"results": []})
            ),
            "anilist": respx.post(anilist.API).mock(
                return_value=httpx.Response(200, json={"data": {"Page": {"media": []}}})
            ),
        }

    @respx.mock
    def test_english_asks_everyone(self) -> None:
        routes = self._routes()
        asyncio.run(SearchWorker("one piece", "en")._search())
        assert all(route.called for route in routes.values())

    @respx.mock
    def test_german_skips_the_english_only_index(self) -> None:
        # Offering a MangaUpdates hit to a German reader would add a series
        # whose only chapter source reports somebody else's releases.
        routes = self._routes()
        asyncio.run(SearchWorker("one piece", "de")._search())
        assert routes["mangadex"].called
        assert routes["anilist"].called
        assert not routes["mangaupdates"].called

    @respx.mock
    def test_a_failing_source_does_not_lose_the_others(self) -> None:
        # 404 rather than 500 on purpose: a server error is retried with real
        # backoff, and the behaviour under test — one source raising must not
        # discard the rest — is the same either way.
        respx.get(f"{mangadex.API}/manga").mock(return_value=httpx.Response(404))
        respx.post(f"{mangaupdates.API}/series/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        respx.post(anilist.API).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "Page": {
                            "media": [
                                {
                                    "id": 30013,
                                    "title": {"romaji": "One Piece"},
                                    "startDate": {"year": 1997},
                                }
                            ]
                        }
                    }
                },
            )
        )

        matches = asyncio.run(SearchWorker("one piece", "en")._search())

        assert [m.source_id for m in matches] == ["anilist"]
