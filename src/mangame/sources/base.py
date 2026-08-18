"""The contract every source adapter implements.

Deliberately tiny. A source has to answer only two questions:

* *"which chapters of this series exist, and when were they published?"*
* *"can you find this series by name?"*

Everything downstream — cadence, expected next release, break detection, poll
pacing, icon state — is derived from that in :mod:`mangame.domain`. Adding a
new source therefore never touches the scheduler or the UI, which is what keeps
"support a huge variety of sources" from turning into a maintenance sink.
"""

from datetime import timedelta
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from mangame.domain.models import SourceSignal
from mangame.sources.http import CacheValidators, HttpClient


class SourceMatch(BaseModel):
    """A candidate series returned by a search, shown in the add-series flow."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    ref: str
    title: str
    url: str | None = None
    year: int | None = None
    hint: str = ""


class Capabilities(BaseModel):
    """What a source can actually tell us, used to pick the best signal."""

    model_config = ConfigDict(frozen=True)

    chapter_timestamps: bool = True
    """Per-chapter publication times — the basis for cadence learning."""

    announced_next_date: bool = False
    """Publisher-stated next-chapter date: the strongest break signal."""

    hiatus_flag: bool = False
    search: bool = True
    batch_feed: bool = False
    """Can answer for many series in one request (see :meth:`Source.fetch_batch`)."""


class FetchRequest(BaseModel):
    """One series, on one source."""

    model_config = ConfigDict(frozen=True)

    series_key: str
    ref: str
    language: str = "en"
    validators: CacheValidators = Field(default_factory=CacheValidators)
    watermark: str | None = None
    """Change token from the previous fetch, if the source supports one."""


@runtime_checkable
class Source(Protocol):
    """Structural interface for adapters. No base class to inherit."""

    source_id: str
    display_name: str
    capabilities: Capabilities
    min_interval: timedelta

    async def fetch(self, client: HttpClient, request: FetchRequest) -> SourceSignal: ...

    async def search(
        self, client: HttpClient, query: str, *, limit: int = 10
    ) -> list[SourceMatch]: ...


@runtime_checkable
class BatchSource(Source, Protocol):
    """A source that can cover every tracked series in a single request.

    This is the cheapest possible daily scan: one call, N series answered. Used
    for the baseline sweep; per-series :meth:`Source.fetch` is reserved for the
    hot window around a due date.
    """

    async def fetch_batch(
        self, client: HttpClient, requests: list[FetchRequest]
    ) -> dict[str, SourceSignal]: ...


@runtime_checkable
class Registry(Protocol):
    """What the poller needs from a source registry, and nothing more."""

    def __contains__(self, source_id: str) -> bool: ...

    def get(self, source_id: str) -> Source | None: ...

    def client(self, source_id: str) -> HttpClient: ...


class SourceError(RuntimeError):
    """Raised by adapters for anything the poller should count as a failure."""
