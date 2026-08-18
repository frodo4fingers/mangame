"""Library + poller: signals in, icon state and a re-armed schedule out."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from mangame.domain.models import (
    Chapter,
    IconState,
    PublicationStatus,
    SeriesPhase,
    SourceSignal,
)
from mangame.service.library import Library
from mangame.service.poller import Poller
from mangame.sources.base import Capabilities, FetchRequest
from mangame.sources.http import HttpClient
from mangame.store.config import SeriesConfig, Settings
from mangame.store.db import Database

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def chapter(number: str, published_at: datetime, source_id: str = "fake") -> Chapter:
    return Chapter(
        source_id=source_id,
        external_id=f"{source_id}-{number}",
        number=number,
        published_at=published_at,
    )


def weekly_history(count: int, *, ending: datetime) -> list[Chapter]:
    return [chapter(str(1190 - i), ending - timedelta(days=7 * i)) for i in reversed(range(count))]


class FakeSource:
    """A source that returns whatever the test hands it."""

    display_name = "Fake"
    capabilities = Capabilities(
        chapter_timestamps=True,
        announced_next_date=True,
        hiatus_flag=True,
        search=False,
        batch_feed=False,
    )
    min_interval = timedelta(minutes=5)

    def __init__(self, source_id: str = "fake") -> None:
        self.source_id = source_id
        self.signal = SourceSignal(source_id=source_id, fetched_at=NOW)
        self.calls: list[FetchRequest] = []
        self.fail: Exception | None = None

    async def search(self, client: HttpClient, query: str, *, limit: int = 10) -> list[Any]:
        return []

    async def fetch(self, client: HttpClient, request: FetchRequest) -> SourceSignal:
        self.calls.append(request)
        if self.fail is not None:
            raise self.fail
        return self.signal


class FakeRegistry:
    def __init__(self, *sources: FakeSource) -> None:
        self._sources = {s.source_id: s for s in sources}

    def __contains__(self, source_id: str) -> bool:
        return source_id in self._sources

    def get(self, source_id: str) -> FakeSource | None:
        return self._sources.get(source_id)

    def client(self, source_id: str) -> Any:
        return None


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    with Database(tmp_path / "mangame.db") as database:
        yield database


def settings_with(**overrides: object) -> Settings:
    series: dict[str, object] = {
        "key": "one-piece",
        "title": "One Piece",
        "emblem": "strawhat",
        "sources": {"fake": "ref-1"},
    }
    series.update(overrides)
    return Settings(series=[SeriesConfig.model_validate(series)])


class TestLibrary:
    def test_a_new_series_starts_out_unknown(self, db: Database) -> None:
        library = Library(settings_with(), db)
        snapshot = library.snapshot_for("one-piece", NOW)
        assert snapshot is not None
        assert snapshot.phase is SeriesPhase.UNKNOWN
        assert snapshot.icon_state is IconState.DUE

    def test_applying_chapters_makes_a_series_ready(self, db: Database) -> None:
        library = Library(settings_with(), db)
        signal = SourceSignal(
            source_id="fake",
            fetched_at=NOW,
            chapters=weekly_history(10, ending=NOW - timedelta(days=1)),
            status=PublicationStatus.ONGOING,
        )
        assert library.apply(library.configs()[0], [signal], NOW) == 10

        snapshot = library.snapshot_for("one-piece", NOW)
        assert snapshot is not None
        assert snapshot.icon_state is IconState.READY
        assert snapshot.latest_chapter is not None
        assert snapshot.latest_chapter.number == "1190"

    def test_a_learned_rhythm_survives_a_restart(self, tmp_path: Path) -> None:
        signal = SourceSignal(
            source_id="fake",
            fetched_at=NOW,
            chapters=weekly_history(10, ending=NOW - timedelta(days=1)),
            status=PublicationStatus.ONGOING,
        )
        path = tmp_path / "mangame.db"
        with Database(path) as first:
            Library(settings_with(), first).apply(settings_with().series[0], [signal], NOW)
        with Database(path) as second:
            series = Library(settings_with(), second).hydrate(settings_with().series[0])
            assert series.cadence.period == timedelta(days=7)
            assert series.status is PublicationStatus.ONGOING

    def test_marking_read_turns_the_icon_off(self, db: Database) -> None:
        library = Library(settings_with(), db)
        signal = SourceSignal(
            source_id="fake",
            fetched_at=NOW,
            chapters=weekly_history(10, ending=NOW - timedelta(days=1)),
        )
        library.apply(library.configs()[0], [signal], NOW)
        before = library.snapshot_for("one-piece", NOW)
        assert before is not None and before.icon_state is IconState.READY

        library.mark_read("one-piece")
        after = library.snapshot_for("one-piece", NOW)
        assert after is not None and after.icon_state is not IconState.READY

    def test_a_hiatus_flag_blackens_the_icon_once_caught_up(self, db: Database) -> None:
        library = Library(settings_with(), db)
        library.apply(
            library.configs()[0],
            [
                SourceSignal(
                    source_id="fake",
                    fetched_at=NOW,
                    chapters=weekly_history(10, ending=NOW - timedelta(days=1)),
                    status=PublicationStatus.HIATUS,
                )
            ],
            NOW,
        )
        library.mark_read("one-piece")

        snapshot = library.snapshot_for("one-piece", NOW)
        assert snapshot is not None
        assert snapshot.phase is SeriesPhase.ANNOUNCED_BREAK
        assert snapshot.icon_state is IconState.BREAK

    def test_an_elapsed_break_stops_blackening_the_icon(self, db: Database) -> None:
        library = Library(settings_with(), db)
        config = library.configs()[0]
        library.apply(
            config,
            [
                SourceSignal(
                    source_id="fake",
                    fetched_at=NOW,
                    chapters=weekly_history(10, ending=NOW - timedelta(days=1)),
                    status=PublicationStatus.HIATUS,
                )
            ],
            NOW,
        )
        library.apply(
            config,
            [
                SourceSignal(
                    source_id="fake",
                    fetched_at=NOW,
                    chapters=weekly_history(10, ending=NOW - timedelta(days=1)),
                    status=PublicationStatus.ONGOING,
                )
            ],
            NOW + timedelta(days=40),
        )
        library.mark_read("one-piece")

        snapshot = library.snapshot_for("one-piece", NOW + timedelta(days=40))
        assert snapshot is not None
        assert snapshot.icon_state is not IconState.BREAK

    def test_the_strongest_status_across_sources_wins(self, db: Database) -> None:
        settings = settings_with(sources={"fake": "a", "other": "b"})
        library = Library(settings, db)
        library.apply(
            library.configs()[0],
            [
                SourceSignal(source_id="fake", fetched_at=NOW, status=PublicationStatus.UNKNOWN),
                SourceSignal(source_id="other", fetched_at=NOW, status=PublicationStatus.COMPLETED),
            ],
            NOW,
        )
        assert library.hydrate(library.configs()[0]).status is PublicationStatus.COMPLETED

    def test_a_source_that_says_nothing_does_not_erase_what_we_knew(self, db: Database) -> None:
        library = Library(settings_with(), db)
        config = library.configs()[0]
        library.apply(
            config,
            [SourceSignal(source_id="fake", fetched_at=NOW, status=PublicationStatus.HIATUS)],
            NOW,
        )
        library.apply(
            config,
            [SourceSignal(source_id="fake", fetched_at=NOW, unchanged=True)],
            NOW + timedelta(hours=12),
        )
        assert library.hydrate(config).status is PublicationStatus.HIATUS

    def test_a_series_can_come_back_off_hiatus(self, db: Database) -> None:
        library = Library(settings_with(), db)
        config = library.configs()[0]
        library.apply(
            config,
            [SourceSignal(source_id="fake", fetched_at=NOW, status=PublicationStatus.HIATUS)],
            NOW,
        )
        library.apply(
            config,
            [SourceSignal(source_id="fake", fetched_at=NOW, status=PublicationStatus.ONGOING)],
            NOW + timedelta(days=40),
        )
        assert library.hydrate(config).status is PublicationStatus.ONGOING


class TestPoller:
    async def test_a_new_series_is_polled_on_the_first_tick(self, db: Database) -> None:
        source = FakeSource()
        source.signal = SourceSignal(
            source_id="fake",
            fetched_at=NOW,
            chapters=weekly_history(10, ending=NOW - timedelta(days=1)),
            status=PublicationStatus.ONGOING,
        )
        poller = Poller(Library(settings_with(), db), db, FakeRegistry(source))

        outcomes = await poller.tick(NOW)
        assert len(outcomes) == 1
        assert outcomes[0].new_chapters == 10
        assert outcomes[0].snapshot is not None
        assert outcomes[0].snapshot.icon_state is IconState.READY

    async def test_a_series_is_not_polled_again_until_it_is_due(self, db: Database) -> None:
        source = FakeSource()
        source.signal = SourceSignal(
            source_id="fake",
            fetched_at=NOW,
            chapters=weekly_history(10, ending=NOW - timedelta(days=1)),
            status=PublicationStatus.ONGOING,
        )
        poller = Poller(Library(settings_with(), db), db, FakeRegistry(source))

        await poller.tick(NOW)
        assert await poller.tick(NOW + timedelta(minutes=1)) == []
        assert len(source.calls) == 1

    async def test_polling_re_arms_with_an_absolute_wall_clock_time(self, db: Database) -> None:
        # Not a sleep: a laptop that suspends for a day must immediately notice
        # what it owes when it wakes up.
        source = FakeSource()
        source.signal = SourceSignal(
            source_id="fake",
            fetched_at=NOW,
            chapters=weekly_history(10, ending=NOW - timedelta(days=1)),
            status=PublicationStatus.ONGOING,
        )
        poller = Poller(Library(settings_with(), db), db, FakeRegistry(source))
        await poller.tick(NOW)

        state = db.poll_state("one-piece", "fake")
        assert state.next_due_at is not None
        assert state.next_due_at > NOW
        assert state.tier

        assert len(await poller.tick(NOW + timedelta(days=1))) == 1

    async def test_a_failing_source_backs_off_instead_of_hammering(self, db: Database) -> None:
        source = FakeSource()
        source.fail = RuntimeError("boom")
        poller = Poller(Library(settings_with(), db), db, FakeRegistry(source))

        first = await poller.tick(NOW)
        assert first[0].errors

        state = db.poll_state("one-piece", "fake")
        assert state.consecutive_errors == 1
        assert state.next_due_at is not None and state.next_due_at > NOW

    async def test_recovering_from_failure_clears_the_error_count(self, db: Database) -> None:
        source = FakeSource()
        source.fail = RuntimeError("boom")
        poller = Poller(Library(settings_with(), db), db, FakeRegistry(source))
        await poller.tick(NOW)

        source.fail = None
        source.signal = SourceSignal(
            source_id="fake",
            fetched_at=NOW,
            chapters=weekly_history(3, ending=NOW - timedelta(days=1)),
            status=PublicationStatus.ONGOING,
        )
        db.clear_due()
        await poller.tick(NOW + timedelta(hours=1))

        assert db.poll_state("one-piece", "fake").consecutive_errors == 0

    async def test_cache_validators_are_replayed_on_the_next_poll(self, db: Database) -> None:
        source = FakeSource()
        source.signal = SourceSignal(
            source_id="fake",
            fetched_at=NOW,
            chapters=weekly_history(3, ending=NOW - timedelta(days=1)),
            etag='W/"abc"',
            watermark="chapter-1190",
        )
        poller = Poller(Library(settings_with(), db), db, FakeRegistry(source))

        await poller.tick(NOW)
        db.clear_due()
        await poller.tick(NOW + timedelta(hours=13))

        assert source.calls[-1].validators.etag == 'W/"abc"'
        assert source.calls[-1].watermark == "chapter-1190"

    async def test_an_unchanged_response_keeps_what_we_already_learned(self, db: Database) -> None:
        source = FakeSource()
        source.signal = SourceSignal(
            source_id="fake",
            fetched_at=NOW,
            chapters=weekly_history(10, ending=NOW - timedelta(days=1)),
            status=PublicationStatus.ONGOING,
        )
        poller = Poller(Library(settings_with(), db), db, FakeRegistry(source))
        await poller.tick(NOW)

        source.signal = SourceSignal(
            source_id="fake", fetched_at=NOW, unchanged=True, watermark="w"
        )
        db.clear_due()
        outcomes = await poller.tick(NOW + timedelta(hours=13))

        assert outcomes[0].new_chapters == 0
        assert outcomes[0].snapshot is not None
        assert outcomes[0].snapshot.latest_chapter is not None

    async def test_unknown_sources_are_ignored_rather_than_crashing(self, db: Database) -> None:
        poller = Poller(
            Library(settings_with(sources={"nope": "x"}), db), db, FakeRegistry(FakeSource())
        )
        assert await poller.tick(NOW) == []

    async def test_several_sources_for_one_series_are_merged(self, db: Database) -> None:
        chapters = FakeSource("chapters")
        chapters.signal = SourceSignal(
            source_id="chapters",
            fetched_at=NOW,
            chapters=weekly_history(10, ending=NOW - timedelta(days=1)),
        )
        status = FakeSource("status")
        status.signal = SourceSignal(
            source_id="status", fetched_at=NOW, status=PublicationStatus.HIATUS
        )

        settings = settings_with(sources={"chapters": "a", "status": "b"})
        poller = Poller(Library(settings, db), db, FakeRegistry(chapters, status))
        outcomes = await poller.tick(NOW)

        assert outcomes[0].new_chapters == 10
        assert outcomes[0].snapshot is not None
        # Unread still wins over the hiatus flag.
        assert outcomes[0].snapshot.icon_state is IconState.READY
