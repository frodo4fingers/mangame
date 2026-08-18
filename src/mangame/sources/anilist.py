"""AniList adapter — the hiatus oracle.

AniList carries no chapter-level release times, so it is useless for cadence.
What it does carry is a curated ``status`` field with an explicit ``HIATUS``
value, which is one of the few places a break is stated as data rather than
prose. It is therefore registered as a *status-only* source: cheap, batched,
and consulted purely to blacken the icon.

Batching is free here — GraphQL aliases let one request cover the entire
library, so this source costs a single call per sweep no matter how many
series the user tracks.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from mangame.domain.models import PublicationStatus, SourceSignal
from mangame.sources.base import Capabilities, FetchRequest, SourceError, SourceMatch
from mangame.sources.http import HttpClient

API = "https://graphql.anilist.co"

#: AniList allows 90 requests/minute and has been observed degraded to 30.
RATE_PER_SECOND = 0.4

#: Aliased queries per request. Kept modest to stay inside query-complexity limits.
MAX_ALIASES = 40

_STATUS = {
    "RELEASING": PublicationStatus.ONGOING,
    "HIATUS": PublicationStatus.HIATUS,
    "FINISHED": PublicationStatus.COMPLETED,
    "CANCELLED": PublicationStatus.CANCELLED,
    "NOT_YET_RELEASED": PublicationStatus.UNKNOWN,
}

_SEARCH_QUERY = """
query ($q: String, $n: Int) {
  Page(perPage: $n) {
    media(search: $q, type: MANGA) {
      id
      status
      siteUrl
      startDate { year }
      title { romaji english native }
    }
  }
}
"""


def _title_of(media: dict[str, Any]) -> str:
    titles = media.get("title") or {}
    for key in ("english", "romaji", "native"):
        if titles.get(key):
            return str(titles[key])
    return "Untitled"


class AniListSource:
    """Status-only source used to detect declared hiatuses."""

    source_id = "anilist"
    display_name = "AniList"
    capabilities = Capabilities(
        chapter_timestamps=False,
        announced_next_date=False,
        hiatus_flag=True,
        search=True,
        batch_feed=True,
    )
    min_interval = timedelta(hours=6)

    async def _post(self, client: HttpClient, query: str, variables: dict[str, Any]) -> Any:
        response = await client.post_json(
            API,
            json_body={"query": query, "variables": variables},
            headers={"Content-Type": "application/json"},
        )
        payload = response.payload or {}
        if payload.get("errors"):
            raise SourceError(f"anilist: {payload['errors'][0].get('message', 'error')}")
        return payload.get("data") or {}

    async def search(self, client: HttpClient, query: str, *, limit: int = 10) -> list[SourceMatch]:
        data = await self._post(client, _SEARCH_QUERY, {"q": query, "n": limit})
        media_list = (data.get("Page") or {}).get("media") or []
        return [
            SourceMatch(
                source_id=self.source_id,
                ref=str(media["id"]),
                title=_title_of(media),
                url=media.get("siteUrl"),
                year=(media.get("startDate") or {}).get("year"),
                hint=str(media.get("status") or ""),
            )
            for media in media_list
        ]

    async def fetch(self, client: HttpClient, request: FetchRequest) -> SourceSignal:
        signals = await self.fetch_batch(client, [request])
        return signals[request.series_key]

    async def fetch_batch(
        self, client: HttpClient, requests: list[FetchRequest]
    ) -> dict[str, SourceSignal]:
        """One aliased GraphQL document covers up to :data:`MAX_ALIASES` series."""
        now = datetime.now(UTC)
        signals: dict[str, SourceSignal] = {}

        for start in range(0, len(requests), MAX_ALIASES):
            chunk = requests[start : start + MAX_ALIASES]
            aliases = {f"m{index}": request for index, request in enumerate(chunk)}
            body = "\n".join(
                f"{alias}: Media(id: {int(request.ref)}, type: MANGA) {{ id status }}"
                for alias, request in aliases.items()
            )
            data = await self._post(client, f"query {{\n{body}\n}}", {})

            for alias, request in aliases.items():
                media = data.get(alias) or {}
                signals[request.series_key] = SourceSignal(
                    source_id=self.source_id,
                    fetched_at=now,
                    status=_STATUS.get(str(media.get("status")), PublicationStatus.UNKNOWN),
                    watermark=str(media.get("status") or ""),
                )
        return signals
