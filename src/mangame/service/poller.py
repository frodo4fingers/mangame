"""The poller: decides what to ask, asks it, and re-arms the schedule.

Two properties worth calling out:

* **Batching first.** Sources that can answer for many series in one request
  (MangaDex's 100-id sweep, AniList's aliased GraphQL) are grouped, so the
  routine daily scan usually costs a couple of requests in total rather than a
  couple per series.
* **Absolute due-times, not sleeps.** Every pair stores a wall-clock
  ``next_due_at``. A laptop that suspends for six hours therefore wakes up and
  immediately notices what it owes, instead of resuming a stale timer.
"""

import asyncio
import contextlib
import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from mangame.domain import schedule
from mangame.domain.models import SeriesPhase, SeriesSnapshot, SourceSignal
from mangame.domain.schedule import PollInputs
from mangame.service.library import Library
from mangame.sources.base import BatchSource, FetchRequest, Registry
from mangame.sources.http import CacheValidators
from mangame.store.config import SeriesConfig
from mangame.store.db import Database

LOG = logging.getLogger(__name__)

#: How often the loop wakes to re-check due times. Cheap: it is one SQL query.
TICK = 60.0


class PollOutcome(BaseModel):
    """Result of one tick, for notifications and logging."""

    series_key: str
    title: str
    new_chapters: int = 0
    errors: list[str] = Field(default_factory=list)
    snapshot: SeriesSnapshot | None = None


class Poller:
    """Owns the polling loop for the whole library."""

    def __init__(
        self,
        library: Library,
        database: Database,
        registry: Registry,
    ) -> None:
        self._library = library
        self._db = database
        self._registry = registry

    # ----------------------------------------------------------------- driving

    async def run(
        self,
        stop: asyncio.Event,
        on_outcomes: Callable[[list[PollOutcome]], None] | None = None,
    ) -> None:
        """Poll until ``stop`` is set, reporting each tick's outcomes."""
        while not stop.is_set():
            try:
                outcomes = await self.tick(datetime.now(UTC))
                if outcomes and on_outcomes is not None:
                    on_outcomes(outcomes)
            except Exception:  # a bad tick must never kill the loop
                LOG.exception("poll tick failed")
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=TICK)

    async def tick(self, now: datetime) -> list[PollOutcome]:
        """Poll everything that is due, then re-arm each pair."""
        due = self._due_work(now)
        if not due:
            return []

        signals: dict[str, list[SourceSignal]] = defaultdict(list)
        errors: dict[str, list[str]] = defaultdict(list)

        for source_id, requests in due.items():
            source = self._registry.get(source_id)
            if source is None:
                continue
            client = self._registry.client(source_id)
            try:
                if isinstance(source, BatchSource) and len(requests) > 1:
                    produced = await source.fetch_batch(client, requests)
                else:
                    produced = {
                        request.series_key: await source.fetch(client, request)
                        for request in requests
                    }
            except Exception as exc:
                LOG.warning("source %s failed: %s", source_id, exc)
                for request in requests:
                    errors[request.series_key].append(f"{source_id}: {exc}")
                continue

            for series_key, signal in produced.items():
                signals[series_key].append(signal)

        return self._commit(due, signals, errors, now)

    # ----------------------------------------------------------------- planning

    def _due_work(self, now: datetime) -> dict[str, list[FetchRequest]]:
        """Group everything owed right now by source, ready for batching."""
        grouped: dict[str, list[FetchRequest]] = defaultdict(list)

        for config in self._library.configs():
            for source_id, ref in config.sources.items():
                if source_id not in self._registry:
                    continue
                poll = self._db.poll_state(config.key, source_id)
                if poll.next_due_at is not None and poll.next_due_at > now:
                    continue
                grouped[source_id].append(
                    FetchRequest(
                        series_key=config.key,
                        ref=ref,
                        language=self._library.settings.language_for(config),
                        validators=CacheValidators(
                            etag=poll.etag, last_modified=poll.last_modified
                        ),
                        watermark=poll.watermark,
                    )
                )
        return grouped

    # ---------------------------------------------------------------- recording

    def _commit(
        self,
        due: dict[str, list[FetchRequest]],
        signals: dict[str, list[SourceSignal]],
        errors: dict[str, list[str]],
        now: datetime,
    ) -> list[PollOutcome]:
        polled_keys = {request.series_key for requests in due.values() for request in requests}
        configs = {c.key: c for c in self._library.configs()}
        outcomes: list[PollOutcome] = []

        for key in sorted(polled_keys):
            config = configs.get(key)
            if config is None:
                continue

            found = self._library.apply(config, signals.get(key, []), now)
            snapshot = self._library.snapshot_for(key, now)
            self._rearm(config, due, signals, errors, snapshot, now)

            outcomes.append(
                PollOutcome(
                    series_key=key,
                    title=config.title,
                    new_chapters=found,
                    errors=errors.get(key, []),
                    snapshot=snapshot,
                )
            )

        self._db.prune_chapters()
        return outcomes

    def _rearm(
        self,
        config: SeriesConfig,
        due: dict[str, list[FetchRequest]],
        signals: dict[str, list[SourceSignal]],
        errors: dict[str, list[str]],
        snapshot: SeriesSnapshot | None,
        now: datetime,
    ) -> None:
        """Store the next due-time for every source we just asked."""
        series = self._library.hydrate(config)
        produced = {s.source_id: s for s in signals.get(config.key, [])}
        failed = bool(errors.get(config.key))

        for source_id, requests in due.items():
            if not any(r.series_key == config.key for r in requests):
                continue
            source = self._registry.get(source_id)
            if source is None:
                continue

            poll = self._db.poll_state(config.key, source_id)
            signal = produced.get(source_id)

            decision = schedule.decide(
                PollInputs(
                    series_key=config.key,
                    now=now,
                    phase=snapshot.phase if snapshot else SeriesPhase.UNKNOWN,
                    status=series.status,
                    cadence=series.cadence,
                    expected_next_at=snapshot.expected_next_at if snapshot else None,
                    break_ends_at=(
                        snapshot.active_break.ends_at
                        if snapshot and snapshot.active_break
                        else None
                    ),
                    consecutive_errors=poll.consecutive_errors + 1 if failed else 0,
                    source_min_interval=source.min_interval,
                )
            )

            poll.next_due_at = decision.due_at
            poll.last_polled_at = now
            poll.tier = decision.tier
            poll.consecutive_errors = poll.consecutive_errors + 1 if failed else 0
            if signal is not None:
                poll.etag = signal.etag
                poll.last_modified = signal.last_modified
                poll.watermark = signal.watermark or poll.watermark
            self._db.save_poll_state(poll)
