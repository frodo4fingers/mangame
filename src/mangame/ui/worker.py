"""Background threads that bridge asyncio networking to the Qt GUI thread.

Qt owns the main thread; the poller wants an asyncio loop. Rather than pull in
an event-loop integration package, each background job runs a plain
``asyncio.run`` inside its own :class:`QThread` and reports back with a Qt
signal, which Qt delivers to the GUI thread as a queued call.

Each thread also opens its **own** SQLite connection. ``sqlite3`` objects are
not shareable across threads, and WAL mode makes two connections to the same
file cheap and safe.
"""

import asyncio
import logging
import threading
from datetime import UTC, datetime

from PySide6.QtCore import QThread, Signal

from mangame.service.library import Library
from mangame.service.poller import Poller, PollOutcome
from mangame.sources.base import SourceMatch
from mangame.sources.registry import SourceRegistry
from mangame.store import config
from mangame.store.db import Database

LOG = logging.getLogger(__name__)

#: Seconds between due-time re-evaluations. The tick itself is one SQL query,
#: so this is not the polling rate — it is only the resolution of the schedule.
TICK_SECONDS = 60

#: Granularity at which the sleep checks for stop/refresh requests.
WAKE_SECONDS = 1.0


class PollWorker(QThread):
    """Runs the polling loop for the lifetime of the app."""

    outcomes = Signal(object)
    """Emitted with ``list[PollOutcome]`` after any tick that did work."""

    def __init__(self) -> None:
        super().__init__()
        self._stop = threading.Event()
        self._force = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def request_check_now(self) -> None:
        """Clear every due-time so the next tick polls everything."""
        self._force.set()

    def run(self) -> None:
        try:
            asyncio.run(self._main())
        except Exception:
            LOG.exception("poll worker crashed")

    async def _main(self) -> None:
        database = Database()
        registry = SourceRegistry()
        library = Library(config.load(), database)
        poller = Poller(library, database, registry)

        try:
            while not self._stop.is_set():
                # Re-read settings each tick so anything the menu changed (or
                # the user hand-edited) is picked up without any cross-thread
                # state sharing.
                library.replace_settings(config.load())

                if self._force.is_set():
                    self._force.clear()
                    database.clear_due()

                try:
                    produced = await poller.tick(datetime.now(UTC))
                    if produced:
                        self.outcomes.emit(produced)
                except Exception:
                    LOG.exception("poll tick failed")

                await self._sleep(TICK_SECONDS)
        finally:
            await registry.aclose()
            database.close()

    async def _sleep(self, seconds: float) -> None:
        """Sleep in small steps so stop/refresh are honoured promptly."""
        waited = 0.0
        while waited < seconds and not self._stop.is_set() and not self._force.is_set():
            await asyncio.sleep(WAKE_SECONDS)
            waited += WAKE_SECONDS


class SearchWorker(QThread):
    """One-shot series lookup across every searchable source."""

    found = Signal(object)
    """Emitted with ``list[SourceMatch]``."""

    def __init__(self, query: str, limit: int = 12) -> None:
        super().__init__()
        self._query = query
        self._limit = limit

    def run(self) -> None:
        try:
            matches = asyncio.run(self._search())
        except Exception:
            LOG.exception("search failed")
            matches = []
        self.found.emit(matches)

    async def _search(self) -> list[SourceMatch]:
        registry = SourceRegistry()
        try:
            results: list[SourceMatch] = []
            for source in registry.searchable():
                try:
                    results.extend(
                        await source.search(
                            registry.client(source.source_id),
                            self._query,
                            limit=self._limit,
                        )
                    )
                except Exception as exc:
                    LOG.warning("search on %s failed: %s", source.source_id, exc)
            return results
        finally:
            await registry.aclose()


__all__ = ["PollOutcome", "PollWorker", "SearchWorker"]
