"""OnePiece-Tube adapter against the site's real page shape. No network."""

import json
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import respx

from mangame.domain import state
from mangame.domain.models import Cadence, Chapter, IconState, TrackedSeries
from mangame.sources import onepiecetube, registry
from mangame.sources.base import FetchRequest, SourceError
from mangame.sources.http import CacheValidators, HttpClient


@pytest.fixture
async def client() -> AsyncIterator[HttpClient]:
    async with HttpClient(rate_per_second=1000.0, burst=64) as http:
        yield http


def entry(
    number: int | float,
    date: str,
    *,
    name: str = "Ein Kapitel",
    available: bool = True,
    pages: int = 14,
    lang: str = "ger",
) -> dict[str, Any]:
    """One catalogue row, in the site's own field shape."""
    return {
        "id": 1000 + int(number),
        "name": name,
        "number": number,
        "category_id": 3,
        "arc_id": 80,
        "specials_id": 0,
        "lang": lang,
        "pages": pages,
        "is_available": available,
        "date": date,
        "href": f"https://onepiece.tube/manga/kapitel/{number}/1",
    }


def list_page(*entries: dict[str, Any]) -> str:
    """The catalogue page: JSON assigned to a global, wrapped in real markup."""
    payload = {
        "options": {"livesearch": True, "isChapter": True},
        "category": {"id": 3, "type": "manga", "name": "Manga Kapitel"},
        "arcs": [],
        "entries": list(entries),
    }
    return (
        "<!doctype html><html><head><title>Manga Kapitel</title></head><body>"
        "<div id='app'></div>"
        f"<script>window.__data = {json.dumps(payload)};window.__env = 'prod';</script>"
        "</body></html>"
    )


#: A Friday, after the fan release of 1192 and before the official Sunday.
NOW = datetime(2026, 9, 4, 9, 0, tzinfo=UTC)

NEWEST = entry(1192, "04.09.2026", name="Das lassen wir uns nicht gefallen!")
HISTORY = (
    NEWEST,
    entry(1191, "20.08.2026", name="Loki ist hier"),
    entry(1190, "07.08.2026"),
    entry(1189, "24.07.2026"),
)


class TestParseChapterList:
    def test_reads_the_fields_the_domain_needs(self) -> None:
        [chapter] = onepiecetube.parse_chapter_list(list_page(NEWEST))

        assert chapter.number == "1192"
        assert chapter.title == "Das lassen wir uns nicht gefallen!"
        assert chapter.language == "de"
        assert chapter.url == "https://onepiece.tube/manga/kapitel/1192/1"
        assert chapter.source_id == "onepiecetube"

    def test_a_german_date_becomes_the_start_of_that_day_in_utc(self) -> None:
        [chapter] = onepiecetube.parse_chapter_list(list_page(NEWEST))
        assert chapter.published_at == datetime(2026, 9, 4, tzinfo=UTC)

    def test_chapters_the_site_cannot_serve_are_not_releases(self) -> None:
        # The catalogue lists every chapter ever published but hosts only some.
        # Reporting the rest would turn the icon "ready" for a chapter that
        # opens on nothing.
        page = list_page(
            NEWEST,
            entry(419, "15.07.2006", available=False, pages=0),
            entry(418, "10.07.2006", available=False, pages=0),
        )
        assert [c.number for c in onepiecetube.parse_chapter_list(page)] == ["1192"]

    def test_an_available_flag_without_pages_is_not_trusted(self) -> None:
        page = list_page(entry(1192, "04.09.2026", available=True, pages=0))
        assert onepiecetube.parse_chapter_list(page) == []

    def test_another_language_is_ignored(self) -> None:
        page = list_page(NEWEST, entry(1192, "04.09.2026", lang="eng"))
        assert len(onepiecetube.parse_chapter_list(page)) == 1

    def test_newest_first_and_capped(self) -> None:
        chapters = onepiecetube.parse_chapter_list(list_page(*HISTORY), limit=2)
        assert [c.number for c in chapters] == ["1192", "1191"]

    def test_a_half_chapter_keeps_its_fraction(self) -> None:
        [chapter] = onepiecetube.parse_chapter_list(list_page(entry(1192.5, "04.09.2026")))
        assert chapter.number == "1192.5"

    def test_unusable_rows_are_skipped_rather_than_fatal(self) -> None:
        page = list_page(
            NEWEST,
            entry(1191, "not a date"),
            {"id": 7, "is_available": True, "pages": 3, "lang": "ger", "date": "01.01.2026"},
        )
        assert [c.number for c in onepiecetube.parse_chapter_list(page)] == ["1192"]

    def test_a_page_without_the_payload_is_an_error(self) -> None:
        # A 404 still returns a full styled page, so "no payload" is the only
        # honest way to tell a moved URL from an empty catalogue.
        with pytest.raises(SourceError, match=re.escape("no window.__data")):
            onepiecetube.parse_chapter_list("<html><body>Seite nicht gefunden</body></html>")

    def test_a_broken_payload_is_an_error(self) -> None:
        with pytest.raises(SourceError, match="unparseable"):
            onepiecetube.parse_chapter_list("<script>window.__data = {oops;</script>")

    def test_a_payload_without_entries_is_an_error(self) -> None:
        with pytest.raises(SourceError, match="no entries"):
            onepiecetube.parse_chapter_list('<script>window.__data = {"category": {}};</script>')


class TestSearch:
    @pytest.mark.parametrize("query", ["One Piece", "one-piece", "ONEPIECE", "one  piece", ""])
    async def test_recognises_the_only_series_it_carries(
        self, client: HttpClient, query: str
    ) -> None:
        [match] = await onepiecetube.OnePieceTubeSource().search(client, query, language="de")
        assert match.title == "One Piece"
        assert match.ref == onepiecetube.LIST_URL
        assert match.source_id == "onepiecetube"

    async def test_does_not_answer_for_another_series(self, client: HttpClient) -> None:
        found = await onepiecetube.OnePieceTubeSource().search(client, "Naruto", language="de")
        assert found == []

    async def test_does_not_answer_for_another_language(self, client: HttpClient) -> None:
        found = await onepiecetube.OnePieceTubeSource().search(client, "One Piece", language="en")
        assert found == []


class TestFetch:
    @respx.mock
    async def test_returns_chapters_and_a_change_token(self, client: HttpClient) -> None:
        respx.get(onepiecetube.LIST_URL).mock(
            return_value=httpx.Response(200, text=list_page(*HISTORY))
        )
        signal = await onepiecetube.OnePieceTubeSource().fetch(
            client,
            FetchRequest(series_key="one-piece", ref=onepiecetube.LIST_URL, language="de"),
        )

        assert [c.number for c in signal.chapters] == ["1192", "1191", "1190", "1189"]
        assert signal.watermark == str(NEWEST["id"])
        assert not signal.unchanged

    @respx.mock
    async def test_a_chapter_dated_ahead_of_today_is_not_out_yet(self, client: HttpClient) -> None:
        # The site fills the date in when it schedules an entry, so a future
        # date is a plan, not a release.
        tomorrow = datetime.now(UTC) + timedelta(days=2)
        respx.get(onepiecetube.LIST_URL).mock(
            return_value=httpx.Response(
                200, text=list_page(entry(1193, tomorrow.strftime("%d.%m.%Y")), NEWEST)
            )
        )
        signal = await onepiecetube.OnePieceTubeSource().fetch(
            client,
            FetchRequest(series_key="one-piece", ref=onepiecetube.LIST_URL, language="de"),
        )

        assert [c.number for c in signal.chapters] == ["1192"]

    @respx.mock
    async def test_an_unchanged_page_costs_nothing(self, client: HttpClient) -> None:
        respx.get(onepiecetube.LIST_URL).mock(return_value=httpx.Response(304))
        signal = await onepiecetube.OnePieceTubeSource().fetch(
            client,
            FetchRequest(
                series_key="one-piece",
                ref=onepiecetube.LIST_URL,
                language="de",
                validators=CacheValidators(etag='"abc"'),
                watermark="1386",
            ),
        )

        assert signal.unchanged
        assert signal.chapters == []
        assert signal.watermark == "1386", "a no-op must not forget what we knew"

    @respx.mock
    async def test_falls_back_to_the_catalogue_url(self, client: HttpClient) -> None:
        route = respx.get(onepiecetube.LIST_URL).mock(
            return_value=httpx.Response(200, text=list_page(NEWEST))
        )
        await onepiecetube.OnePieceTubeSource().fetch(
            client, FetchRequest(series_key="one-piece", ref="", language="de")
        )
        assert route.called


class TestRegistration:
    def test_the_adapter_is_wired_in(self) -> None:
        ids = [source.source_id for source in registry.SourceRegistry()]
        assert "onepiecetube" in ids

    def test_it_is_only_offered_to_german_readers(self) -> None:
        assert registry.serves("onepiecetube", "de")
        assert not registry.serves("onepiecetube", "en")

    def test_the_registry_can_build_it(self) -> None:
        source = registry.SourceRegistry().get("onepiecetube")
        assert source is not None
        assert source.min_interval >= timedelta(minutes=10), "a fan site is not a CDN"


class TestWhatThisChangesForTheReader:
    """The reason this adapter exists, expressed as the user's own case."""

    #: The newest chapter the official simulpub has, and the one just read.
    OFFICIAL = Chapter(
        source_id="mangaplus",
        external_id="1191",
        number="1191",
        language="de",
        published_at=datetime(2026, 8, 23, 15, tzinfo=UTC),
    )

    def _series(self, latest: Chapter | None) -> TrackedSeries:
        """A reader caught up on 1191, as marking it read would leave them."""
        return TrackedSeries(
            key="one-piece",
            title="One Piece",
            language="de",
            source_refs={"mangaplus": "100020", "onepiecetube": onepiecetube.LIST_URL},
            latest_chapter=latest,
            last_read_number=self.OFFICIAL.number,
            last_read_external_id=self.OFFICIAL.external_id,
            last_read_at=self.OFFICIAL.published_at,
            # A fortnightly Sunday rhythm, which is what both the learned
            # cadence and the MANGA Plus announcement point at: 6 September.
            cadence=Cadence(period=timedelta(days=14), weekday=6, hour=15, sample_size=5),
            announced_next_at=datetime(2026, 9, 6, 15, tzinfo=UTC),
        )

    def test_without_this_source_the_reader_waits_for_the_official_date(self) -> None:
        snapshot = state.resolve(self._series(self.OFFICIAL), NOW)

        assert snapshot.icon_state is IconState.DUE
        # Weekday and month names follow the process locale, which Qt changes
        # the moment it starts, so only the locale-stable parts are asserted.
        assert "next chapter expected" in snapshot.tooltip
        assert "15:00 UTC" in snapshot.tooltip

    def test_a_scanlation_ahead_of_the_publisher_turns_the_icon_on(self) -> None:
        [fan_release] = onepiecetube.parse_chapter_list(list_page(NEWEST))
        snapshot = state.resolve(self._series(fan_release), NOW)

        assert snapshot.icon_state is IconState.READY
        assert "ch. 1192 is ready to read" in snapshot.tooltip, (
            "a chapter in hand outranks a date the publisher announced"
        )
