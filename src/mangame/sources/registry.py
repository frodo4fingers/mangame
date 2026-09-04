"""Source registry: one place that knows which adapters exist.

Adapters are looked up by id, so a series' ``source_refs`` mapping
(``{"mangadex": "<uuid>", "feed": "https://..."}``) is enough to route it.
Each source gets its own rate-limited :class:`HttpClient`, which keeps one
misbehaving site from starving the others.
"""

from collections.abc import Iterator
from types import TracebackType
from typing import Self

from mangame.sources import anilist, mangadex, mangaupdates
from mangame.sources.base import Capabilities, Source
from mangame.sources.feed import FeedSource
from mangame.sources.http import HttpClient
from mangame.sources.onepiecetube import OnePieceTubeSource

#: Adapter id -> (adapter, requests per second, burst).
_BUILTINS: tuple[tuple[Source, float, int], ...] = (
    (mangadex.MangaDexSource(), mangadex.RATE_PER_SECOND, 4),
    (mangaupdates.MangaUpdatesSource(), mangaupdates.RATE_PER_SECOND, 2),
    (anilist.AniListSource(), anilist.RATE_PER_SECOND, 2),
    (OnePieceTubeSource(), 0.5, 1),
    (FeedSource(), 1.0, 4),
)

_CAPABILITIES: dict[str, Capabilities] = {
    source.source_id: source.capabilities for source, _rate, _burst in _BUILTINS
}


def serves(source_id: str, language: str) -> bool:
    """Can the built-in adapter answer for ``language``?

    Available without building a registry, so the UI can decide which sources
    are worth linking to a new series without opening any HTTP clients.
    """
    capabilities = _CAPABILITIES.get(source_id)
    return capabilities is not None and capabilities.serves(language)


class SourceRegistry:
    """Owns every adapter and its dedicated HTTP client."""

    def __init__(self, sources: tuple[tuple[Source, float, int], ...] = _BUILTINS) -> None:
        self._sources: dict[str, Source] = {}
        self._clients: dict[str, HttpClient] = {}
        for source, rate, burst in sources:
            self._sources[source.source_id] = source
            self._clients[source.source_id] = HttpClient(rate_per_second=rate, burst=burst)

    def __contains__(self, source_id: str) -> bool:
        return source_id in self._sources

    def __iter__(self) -> Iterator[Source]:
        return iter(self._sources.values())

    def get(self, source_id: str) -> Source | None:
        return self._sources.get(source_id)

    def client(self, source_id: str) -> HttpClient:
        return self._clients[source_id]

    def searchable(self) -> list[Source]:
        return [s for s in self._sources.values() if s.capabilities.search]

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        for client in self._clients.values():
            await client.aclose()
