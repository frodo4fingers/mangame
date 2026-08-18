"""MangaUpdates adapter — the release historian.

MangaUpdates records dated *release* rows going back years, which is the
richest history available for learning a rhythm — far better than aggregators
that only keep the last handful of chapters.

It deliberately does **not** advertise a batch feed. The obvious candidate,
``GET /v1/releases/days``, reports roughly nine thousand releases site-wide per
day; paging through that to find a handful of tracked titles would cost far
more than asking about each title directly. Instead ``GET /v1/series/{id}``
returns ``latest_chapter`` in one cheap call, and that value is used as a
watermark so the expensive history query only runs when something moved.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from mangame.domain.models import Chapter, PublicationStatus, SourceSignal
from mangame.sources.base import Capabilities, FetchRequest, SourceMatch
from mangame.sources.http import HttpClient

API = "https://api.mangaupdates.com/v1"

#: Undocumented limits, so we stay deliberately gentle.
RATE_PER_SECOND = 1.0

HISTORY_PAGE_SIZE = 50


def _release_time(record: dict[str, Any]) -> datetime | None:
    """Prefer the timestamped ``time_added``, fall back to the plain date."""
    added = (record.get("time_added") or {}).get("as_rfc3339")
    if added:
        try:
            return datetime.fromisoformat(added).astimezone(UTC)
        except ValueError:
            pass
    raw = record.get("release_date")
    if not raw:
        return None
    try:
        return datetime.combine(date.fromisoformat(str(raw)), time(12, 0), tzinfo=UTC)
    except ValueError:
        return None


def _chapter_from(record: dict[str, Any], language: str) -> Chapter | None:
    published = _release_time(record)
    if published is None:
        return None
    groups = ", ".join(g.get("name", "") for g in record.get("groups") or [])
    return Chapter(
        source_id=MangaUpdatesSource.source_id,
        external_id=str(record.get("id")),
        number=str(record["chapter"]) if record.get("chapter") else None,
        volume=str(record["volume"]) if record.get("volume") else None,
        title=groups or None,
        language=language,
        published_at=published,
    )


class MangaUpdatesSource:
    """Dated release records, plus a site-wide newest-releases firehose."""

    source_id = "mangaupdates"
    display_name = "MangaUpdates"
    capabilities = Capabilities(
        chapter_timestamps=True,
        announced_next_date=False,
        hiatus_flag=True,
        search=True,
        batch_feed=False,
    )
    min_interval = timedelta(minutes=15)

    async def search(self, client: HttpClient, query: str, *, limit: int = 10) -> list[SourceMatch]:
        response = await client.post_json(
            f"{API}/series/search",
            json_body={"search": query, "perpage": limit},
            headers={"Content-Type": "application/json"},
        )
        matches: list[SourceMatch] = []
        for entry in (response.payload or {}).get("results", []):
            record = entry.get("record", {})
            year = record.get("year")
            matches.append(
                SourceMatch(
                    source_id=self.source_id,
                    ref=str(record.get("series_id")),
                    title=str(record.get("title", "Untitled")),
                    url=record.get("url"),
                    year=int(year) if str(year).isdigit() else None,
                )
            )
        return matches

    async def _series_detail(self, client: HttpClient, ref: str) -> dict[str, Any]:
        response = await client.get_json(f"{API}/series/{ref}")
        return dict(response.payload or {})

    async def fetch(self, client: HttpClient, request: FetchRequest) -> SourceSignal:
        now = datetime.now(UTC)
        detail = await self._series_detail(client, request.ref)
        title = str(detail.get("title") or "")
        latest = detail.get("latest_chapter")
        watermark = str(latest) if latest is not None else None

        status = (
            PublicationStatus.COMPLETED if detail.get("completed") else PublicationStatus.ONGOING
        )
        if "hiatus" in str(detail.get("status") or "").lower():
            status = PublicationStatus.HIATUS

        # The cheap watermark already says nothing moved; skip the history call.
        if watermark is not None and watermark == request.watermark:
            return SourceSignal(
                source_id=self.source_id,
                fetched_at=now,
                status=status,
                watermark=watermark,
                unchanged=True,
            )

        chapters = await self._history(
            client, ref=request.ref, title=title, language=request.language
        )
        return SourceSignal(
            source_id=self.source_id,
            fetched_at=now,
            chapters=chapters,
            status=status,
            watermark=watermark,
        )

    async def _history(
        self, client: HttpClient, *, ref: str, title: str, language: str
    ) -> list[Chapter]:
        """Dated releases for one series, used to learn its rhythm."""
        if not title:
            return []
        response = await client.post_json(
            f"{API}/releases/search",
            json_body={
                "search": title,
                "asc": "desc",
                "perpage": HISTORY_PAGE_SIZE,
                "include_metadata": True,
            },
            headers={"Content-Type": "application/json"},
        )
        chapters: list[Chapter] = []
        for entry in (response.payload or {}).get("results", []):
            series = (entry.get("metadata") or {}).get("series") or {}
            if str(series.get("series_id")) != str(ref):
                continue
            chapter = _chapter_from(entry.get("record", {}), language)
            if chapter is not None:
                chapters.append(chapter)
        return chapters

    async def fetch_batch(
        self, client: HttpClient, requests: list[FetchRequest]
    ) -> dict[str, SourceSignal]:
        """No real batch endpoint exists, so this is just a paced loop.

        Each iteration is one cheap ``/series/{id}`` call; the watermark keeps
        the expensive release-history query from running unless it must.
        """
        return {r.series_key: await self.fetch(client, r) for r in requests}
