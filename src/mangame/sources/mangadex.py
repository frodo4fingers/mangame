"""MangaDex adapter — the primary source.

Why it leads the tier list: no auth for reads, per-language chapter feeds with
exact publication timestamps, an explicit ``hiatus`` status, and — crucially —
a bulk endpoint.

The bulk endpoint is what makes the daily scan almost free. ``GET /manga?ids[]``
accepts up to 100 ids in one request and returns each series' ``status`` and
``latestUploadedChapter``. One call therefore answers "did anything change?"
for the user's whole library; only the series whose latest-chapter id actually
moved get a follow-up per-series feed request.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from mangame.domain.models import Chapter, PublicationStatus, SourceSignal
from mangame.i18n import languages
from mangame.sources.base import Capabilities, FetchRequest, SourceError, SourceMatch
from mangame.sources.http import HttpClient

API = "https://api.mangadex.org"

#: MangaDex publishes a 5 req/s global budget; we stay well under it.
RATE_PER_SECOND = 2.0

MAX_IDS_PER_SWEEP = 100

#: MangaDex parks licensed/MANGA Plus chapters on a sentinel far-future
#: ``publishAt`` (observed: 2037-12-31) so as not to leak official dates. Any
#: "announced next release" beyond this horizon is that sentinel, not news.
MAX_ANNOUNCE_HORIZON = timedelta(days=180)

_STATUS = {
    "ongoing": PublicationStatus.ONGOING,
    "hiatus": PublicationStatus.HIATUS,
    "completed": PublicationStatus.COMPLETED,
    "cancelled": PublicationStatus.CANCELLED,
}


def _parse_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).astimezone(UTC)
    except ValueError:
        return None


def _pick_title(attributes: dict[str, Any]) -> str:
    titles = attributes.get("title") or {}
    for key in ("en", "ja-ro", "ja"):
        if key in titles:
            return str(titles[key])
    if titles:
        return str(next(iter(titles.values())))
    for alt in attributes.get("altTitles") or []:
        if alt:
            return str(next(iter(alt.values())))
    return "Untitled"


class MangaDexSource:
    """Chapter feeds, hiatus flags and a 100-series bulk sweep."""

    source_id = "mangadex"
    display_name = "MangaDex"
    capabilities = Capabilities(
        chapter_timestamps=True,
        announced_next_date=True,
        hiatus_flag=True,
        search=True,
        batch_feed=True,
        languages=frozenset(languages.codes()),
    )
    min_interval = timedelta(minutes=5)

    def __init__(self, *, feed_limit: int = 24) -> None:
        self._feed_limit = feed_limit

    async def search(self, client: HttpClient, query: str, *, limit: int = 10) -> list[SourceMatch]:
        response = await client.get_json(f"{API}/manga", params={"title": query, "limit": limit})
        payload = response.payload or {}
        matches: list[SourceMatch] = []
        for entry in payload.get("data", []):
            attributes = entry.get("attributes", {})
            matches.append(
                SourceMatch(
                    source_id=self.source_id,
                    ref=str(entry["id"]),
                    title=_pick_title(attributes),
                    url=f"https://mangadex.org/title/{entry['id']}",
                    year=attributes.get("year"),
                    hint=str(attributes.get("status") or ""),
                )
            )
        return matches

    async def fetch(self, client: HttpClient, request: FetchRequest) -> SourceSignal:
        now = datetime.now(UTC)

        detail = await client.get_json(f"{API}/manga/{request.ref}")
        attributes = (detail.payload or {}).get("data", {}).get("attributes", {})
        status = _STATUS.get(str(attributes.get("status")), PublicationStatus.UNKNOWN)

        feed = await client.get_json(
            f"{API}/manga/{request.ref}/feed",
            params={
                # Every code for the wanted language, because MangaDex splits
                # some languages by region (Spanish is "es" and "es-la") and a
                # reader who asked for Spanish wants both.
                "translatedLanguage[]": list(languages.source_codes(request.language)),
                "order[publishAt]": "desc",
                "limit": self._feed_limit,
            },
            validators=request.validators,
        )
        if feed.not_modified:
            return SourceSignal(
                source_id=self.source_id,
                fetched_at=now,
                status=status,
                etag=request.validators.etag,
                last_modified=request.validators.last_modified,
                watermark=request.watermark,
                unchanged=True,
            )

        payload = feed.payload or {}
        if payload.get("result") == "error":
            raise SourceError(f"mangadex feed error for {request.ref}")

        chapters: list[Chapter] = []
        future: list[datetime] = []
        for entry in payload.get("data", []):
            chapter_attrs = entry.get("attributes", {})
            published = _parse_time(
                chapter_attrs.get("readableAt") or chapter_attrs.get("publishAt")
            )
            if published is None:
                continue
            if published > now:
                # MangaDex schedules licensed/simulpub chapters ahead of time,
                # which is a publisher-stated next-release date for free — but
                # only when it is a real date rather than the far-future
                # sentinel used to hide official release schedules.
                if published - now <= MAX_ANNOUNCE_HORIZON:
                    future.append(published)
                continue
            chapters.append(
                Chapter(
                    source_id=self.source_id,
                    external_id=str(entry["id"]),
                    number=chapter_attrs.get("chapter"),
                    volume=chapter_attrs.get("volume"),
                    title=chapter_attrs.get("title"),
                    # Folded onto the canonical code so that an "es-la" chapter
                    # is stored as Spanish and found by a Spanish reader.
                    language=languages.canonical(
                        str(chapter_attrs.get("translatedLanguage") or request.language)
                    ),
                    published_at=published,
                    url=chapter_attrs.get("externalUrl")
                    or f"https://mangadex.org/chapter/{entry['id']}",
                )
            )

        return SourceSignal(
            source_id=self.source_id,
            fetched_at=now,
            chapters=chapters,
            status=status,
            announced_next_at=min(future) if future else None,
            etag=feed.validators.etag,
            last_modified=feed.validators.last_modified,
        )

    async def sweep(
        self, client: HttpClient, refs: list[str]
    ) -> dict[str, tuple[PublicationStatus, str | None]]:
        """One request per 100 series: ``{ref: (status, latest_chapter_id)}``.

        The caller compares ``latest_chapter_id`` with what it stored last time
        and only drills into the series that actually moved.

        The watermark is language-blind: it moves when *any* translation is
        uploaded. That errs on the side of looking, which is the safe
        direction — a missed upload would mean a missed chapter, whereas an
        extra look merely costs one request.
        """
        results: dict[str, tuple[PublicationStatus, str | None]] = {}
        for start in range(0, len(refs), MAX_IDS_PER_SWEEP):
            chunk = refs[start : start + MAX_IDS_PER_SWEEP]
            response = await client.get_json(
                f"{API}/manga",
                params={"ids[]": chunk, "limit": len(chunk)},
            )
            for entry in (response.payload or {}).get("data", []):
                attributes = entry.get("attributes", {})
                results[str(entry["id"])] = (
                    _STATUS.get(str(attributes.get("status")), PublicationStatus.UNKNOWN),
                    attributes.get("latestUploadedChapter"),
                )
        return results

    async def fetch_batch(
        self, client: HttpClient, requests: list[FetchRequest]
    ) -> dict[str, SourceSignal]:
        """Sweep first, then drill only into series whose latest chapter moved."""
        now = datetime.now(UTC)
        by_ref = {r.ref: r for r in requests}
        swept = await self.sweep(client, list(by_ref))

        signals: dict[str, SourceSignal] = {}
        for ref, request in by_ref.items():
            status, watermark = swept.get(ref, (PublicationStatus.UNKNOWN, None))
            if watermark is not None and watermark == request.watermark:
                signals[request.series_key] = SourceSignal(
                    source_id=self.source_id,
                    fetched_at=now,
                    status=status,
                    watermark=watermark,
                    unchanged=True,
                )
                continue
            signal = await self.fetch(client, request)
            signals[request.series_key] = signal.model_copy(
                update={"watermark": watermark or signal.watermark, "status": status}
            )
        return signals
