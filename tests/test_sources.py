"""Source adapters against recorded API shapes. No network."""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import respx

from mangame.domain.models import PublicationStatus
from mangame.sources import anilist, mangadex, mangaupdates, registry
from mangame.sources.base import FetchRequest, SourceError
from mangame.sources.http import CacheValidators, HttpClient

MANGA_ID = "a1c7c817-4e59-43b7-9365-09675a149a6f"


@pytest.fixture
async def client() -> AsyncIterator[HttpClient]:
    async with HttpClient(rate_per_second=1000.0, burst=64) as http:
        yield http


def manga_detail(status: str = "ongoing") -> dict[str, Any]:
    return {
        "result": "ok",
        "data": {
            "id": MANGA_ID,
            "type": "manga",
            "attributes": {
                "title": {"en": "One Piece"},
                "status": status,
                "lastChapter": None,
            },
        },
    }


def feed_entry(number: str, published: str, external: bool = True) -> dict[str, Any]:
    return {
        "id": f"chapter-{number}",
        "type": "chapter",
        "attributes": {
            "chapter": number,
            "volume": None,
            "title": f"Chapter {number}",
            "translatedLanguage": "en",
            "externalUrl": "https://mangaplus.shueisha.co.jp/viewer/1" if external else None,
            "publishAt": published,
            "readableAt": published,
            "createdAt": published,
        },
        "relationships": [],
    }


class TestMangaDexFetch:
    async def test_chapters_and_status_come_back_normalised(self, client: HttpClient) -> None:
        source = mangadex.MangaDexSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}").respond(json=manga_detail())
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}/feed").respond(
                json={
                    "result": "ok",
                    "data": [
                        feed_entry("1190", "2026-08-09T15:07:05+00:00"),
                        feed_entry("1189", "2026-07-29T14:25:10+00:00"),
                    ],
                }
            )
            signal = await source.fetch(client, FetchRequest(series_key="one-piece", ref=MANGA_ID))

        assert signal.status is PublicationStatus.ONGOING
        assert [c.number for c in signal.chapters] == ["1190", "1189"]
        url = signal.chapters[0].url
        assert url is not None and url.startswith("https://mangaplus")

    async def test_the_2037_sentinel_is_not_mistaken_for_a_release_date(
        self, client: HttpClient
    ) -> None:
        # MangaDex stamps MANGA Plus-linked chapters with a far-future
        # publishAt to hide official schedules. Treating that as an announced
        # next-release would put every simulpub series on a 12-year break.
        source = mangadex.MangaDexSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}").respond(json=manga_detail())
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}/feed").respond(
                json={
                    "result": "ok",
                    "data": [
                        feed_entry("1191", "2037-12-31T15:00:00+00:00"),
                        feed_entry("1190", "2026-08-09T15:07:05+00:00"),
                    ],
                }
            )
            signal = await source.fetch(client, FetchRequest(series_key="one-piece", ref=MANGA_ID))

        assert signal.announced_next_at is None
        assert [c.number for c in signal.chapters] == ["1190"]

    async def test_a_believable_future_date_is_kept_as_an_announcement(
        self, client: HttpClient
    ) -> None:
        soon = (datetime.now(UTC) + timedelta(days=6)).isoformat()
        source = mangadex.MangaDexSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}").respond(json=manga_detail())
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}/feed").respond(
                json={
                    "result": "ok",
                    "data": [
                        feed_entry("1191", soon),
                        feed_entry("1190", "2026-08-09T15:07:05+00:00"),
                    ],
                }
            )
            signal = await source.fetch(client, FetchRequest(series_key="one-piece", ref=MANGA_ID))

        assert signal.announced_next_at is not None
        assert [c.number for c in signal.chapters] == ["1190"]

    async def test_a_hiatus_status_is_carried_through(self, client: HttpClient) -> None:
        source = mangadex.MangaDexSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}").respond(json=manga_detail("hiatus"))
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}/feed").respond(
                json={"result": "ok", "data": []}
            )
            signal = await source.fetch(client, FetchRequest(series_key="x", ref=MANGA_ID))
        assert signal.status is PublicationStatus.HIATUS

    async def test_a_304_costs_nothing_and_changes_nothing(self, client: HttpClient) -> None:
        source = mangadex.MangaDexSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}").respond(json=manga_detail())
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}/feed").respond(304)
            signal = await source.fetch(
                client,
                FetchRequest(
                    series_key="x",
                    ref=MANGA_ID,
                    validators=CacheValidators(etag='W/"abc"'),
                    watermark="chapter-1190",
                ),
            )
        assert signal.unchanged
        assert signal.chapters == []
        assert signal.watermark == "chapter-1190"

    async def test_an_api_level_error_is_raised_not_swallowed(self, client: HttpClient) -> None:
        source = mangadex.MangaDexSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}").respond(json=manga_detail())
            mock.get(f"{mangadex.API}/manga/{MANGA_ID}/feed").respond(
                json={"result": "error", "errors": []}
            )
            with pytest.raises(SourceError):
                await source.fetch(client, FetchRequest(series_key="x", ref=MANGA_ID))


class TestMangaDexSweep:
    async def test_one_request_answers_for_a_hundred_series(self, client: HttpClient) -> None:
        # The cheap daily pass: status plus a change watermark for the whole
        # library, so only series that actually moved get a real fetch.
        refs = [f"id-{i}" for i in range(100)]
        source = mangadex.MangaDexSource()
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(f"{mangadex.API}/manga").respond(
                json={
                    "result": "ok",
                    "data": [
                        {
                            "id": ref,
                            "attributes": {
                                "status": "ongoing",
                                "latestUploadedChapter": f"chap-{ref}",
                            },
                        }
                        for ref in refs
                    ],
                }
            )
            result = await source.sweep(client, refs)

        assert route.call_count == 1
        assert len(result) == 100
        assert result["id-7"] == (PublicationStatus.ONGOING, "chap-id-7")

    async def test_more_than_a_hundred_series_are_split_into_pages(
        self, client: HttpClient
    ) -> None:
        refs = [f"id-{i}" for i in range(150)]
        source = mangadex.MangaDexSource()
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(f"{mangadex.API}/manga").respond(json={"result": "ok", "data": []})
            await source.sweep(client, refs)
        assert route.call_count == 2


class TestAniList:
    async def test_many_series_are_asked_for_in_one_query(self, client: HttpClient) -> None:
        source = anilist.AniListSource()
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "data": {
                        "m0": {"id": 30013, "status": "RELEASING"},
                        "m1": {"id": 105778, "status": "HIATUS"},
                    }
                },
            )

        with respx.mock(assert_all_called=False) as mock:
            route = mock.post(anilist.API).mock(side_effect=handler)
            signals = await source.fetch_batch(
                client,
                [
                    FetchRequest(series_key="one-piece", ref="30013"),
                    FetchRequest(series_key="hxh", ref="105778"),
                ],
            )

        assert route.call_count == 1, "batching is the whole point of the AniList tier"
        assert "m0" in captured["query"] and "m1" in captured["query"]
        assert signals["one-piece"].status is PublicationStatus.ONGOING
        assert signals["hxh"].status is PublicationStatus.HIATUS

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("RELEASING", PublicationStatus.ONGOING),
            ("HIATUS", PublicationStatus.HIATUS),
            ("FINISHED", PublicationStatus.COMPLETED),
            ("CANCELLED", PublicationStatus.CANCELLED),
            ("NOT_YET_RELEASED", PublicationStatus.UNKNOWN),
        ],
    )
    async def test_status_mapping(
        self, client: HttpClient, raw: str, expected: PublicationStatus
    ) -> None:
        source = anilist.AniListSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.post(anilist.API).respond(json={"data": {"m0": {"id": 1, "status": raw}}})
            signals = await source.fetch_batch(client, [FetchRequest(series_key="x", ref="1")])
        assert signals["x"].status is expected

    async def test_anilist_never_claims_to_know_chapters(self) -> None:
        # It tracks status, not releases; pretending otherwise would let a
        # stale chapter count drive the icon.
        assert anilist.AniListSource().capabilities.chapter_timestamps is False


class TestMangaUpdates:
    async def test_the_latest_chapter_becomes_a_cheap_watermark(self, client: HttpClient) -> None:
        source = mangaupdates.MangaUpdatesSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(f"{mangaupdates.API}/series/55099564912").respond(
                json={
                    "series_id": 55099564912,
                    "title": "One Piece",
                    "latest_chapter": 1190,
                    "completed": False,
                    "status": "1190 Chapters (Ongoing)",
                }
            )
            mock.post(f"{mangaupdates.API}/releases/search").respond(json={"results": []})
            signal = await source.fetch(
                client, FetchRequest(series_key="one-piece", ref="55099564912")
            )

        assert signal.watermark == "1190"
        assert signal.status is PublicationStatus.ONGOING

    async def test_a_completed_series_is_reported_as_completed(self, client: HttpClient) -> None:
        source = mangaupdates.MangaUpdatesSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(f"{mangaupdates.API}/series/1").respond(
                json={"series_id": 1, "title": "Done", "latest_chapter": 50, "completed": True}
            )
            mock.post(f"{mangaupdates.API}/releases/search").respond(json={"results": []})
            signal = await source.fetch(client, FetchRequest(series_key="x", ref="1"))
        assert signal.status is PublicationStatus.COMPLETED

    async def test_it_does_not_offer_a_batch_feed(self) -> None:
        # /releases/days returns roughly nine thousand releases a day, so a
        # firehose costs far more than polling the handful of tracked series.
        assert mangaupdates.MangaUpdatesSource().capabilities.batch_feed is False


class TestLanguageRouting:
    """Which language a source is asked for, and what it may claim in return."""

    @respx.mock
    async def test_spanish_asks_mangadex_for_both_regional_codes(self, client: HttpClient) -> None:
        respx.get(f"{mangadex.API}/manga/{MANGA_ID}").mock(
            return_value=httpx.Response(200, json=manga_detail())
        )
        route = respx.get(f"{mangadex.API}/manga/{MANGA_ID}/feed").mock(
            return_value=httpx.Response(200, json={"result": "ok", "data": []})
        )
        source = mangadex.MangaDexSource()

        await source.fetch(
            client, FetchRequest(series_key="one-piece", ref=MANGA_ID, language="es")
        )

        asked = route.calls.last.request.url.params.get_list("translatedLanguage[]")
        assert asked == ["es", "es-la"]

    @respx.mock
    async def test_a_latin_american_chapter_counts_as_spanish(self, client: HttpClient) -> None:
        # Stored under the canonical code, otherwise a reader who chose
        # "es" would never see a chapter MangaDex filed under "es-la".
        entry = feed_entry("1190", "2026-08-09T15:07:05+00:00")
        entry["attributes"]["translatedLanguage"] = "es-la"
        respx.get(f"{mangadex.API}/manga/{MANGA_ID}").mock(
            return_value=httpx.Response(200, json=manga_detail())
        )
        respx.get(f"{mangadex.API}/manga/{MANGA_ID}/feed").mock(
            return_value=httpx.Response(200, json={"result": "ok", "data": [entry]})
        )
        source = mangadex.MangaDexSource()

        signal = await source.fetch(
            client, FetchRequest(series_key="one-piece", ref=MANGA_ID, language="es")
        )

        assert [chapter.language for chapter in signal.chapters] == ["es"]

    def test_mangadex_serves_every_language_mangame_offers(self) -> None:
        capabilities = mangadex.MangaDexSource.capabilities
        assert all(capabilities.serves(code) for code in ("en", "es", "de"))

    def test_mangaupdates_only_speaks_for_english(self) -> None:
        # Its release records carry no language and its lang filter is ignored,
        # so anything else would be a guess presented as fact.
        capabilities = mangaupdates.MangaUpdatesSource.capabilities
        assert capabilities.serves("en")
        assert not capabilities.serves("de")
        assert not capabilities.serves("es")

    def test_a_mangaupdates_release_is_labelled_english_not_what_was_asked_for(self) -> None:
        chapter = mangaupdates._chapter_from(
            {
                "id": 36642,
                "chapter": "1190",
                "volume": "108",
                "groups": [{"name": "Some Group"}],
                "release_date": "2026-08-09",
            }
        )
        assert chapter is not None
        assert chapter.language == "en"

    def test_a_status_only_source_is_worth_asking_in_any_language(self) -> None:
        # AniList carries no chapters, so its hiatus flag is equally true
        # whichever language the reader picked.
        capabilities = anilist.AniListSource.capabilities
        assert not capabilities.chapter_timestamps
        assert all(capabilities.serves(code) for code in ("en", "es", "de"))

    @pytest.mark.parametrize(
        ("source_id", "language", "expected"),
        [
            ("mangadex", "es", True),
            ("mangadex", "de", True),
            ("mangaupdates", "en", True),
            ("mangaupdates", "de", False),
            ("anilist", "de", True),  # status only, so language-independent
            ("feed", "de", True),  # the URL is the reader's own choice
            ("nope", "en", False),
        ],
    )
    def test_the_registry_answers_without_opening_a_client(
        self, source_id: str, language: str, expected: bool
    ) -> None:
        assert registry.serves(source_id, language) is expected
