"""Icon-state resolution — READY > BREAK > DUE, the product in one rule."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mangame.domain import state
from mangame.domain.models import (
    BreakWindow,
    Cadence,
    Chapter,
    Confidence,
    IconState,
    PublicationStatus,
    SeriesPhase,
    TrackedSeries,
)

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
WEEKLY = Cadence(period=timedelta(days=7), weekday=6, hour=15, sample_size=8)


def series(**overrides: object) -> TrackedSeries:
    base: dict[str, object] = {
        "key": "one-piece",
        "title": "One Piece",
        "emblem": "strawhat",
        "cadence": WEEKLY,
        "status": PublicationStatus.ONGOING,
    }
    base.update(overrides)
    return TrackedSeries.model_validate(base)


def latest(published_at: datetime, number: str = "1190") -> Chapter:
    return Chapter(
        source_id="mangadex",
        external_id=f"ch-{number}",
        number=number,
        published_at=published_at,
    )


def announced_break(start: datetime, end: datetime | None = None) -> BreakWindow:
    return BreakWindow(
        starts_at=start, ends_at=end, confidence=Confidence.HIGH, reason="golden week"
    )


class TestPrecedence:
    def test_an_unread_chapter_is_ready(self) -> None:
        snapshot = state.resolve(series(latest_chapter=latest(NOW - timedelta(days=1))), NOW)
        assert snapshot.phase is SeriesPhase.UNREAD
        assert snapshot.icon_state is IconState.READY

    def test_unread_beats_an_announced_break(self) -> None:
        # A break does not make a freshly published chapter less readable.
        snapshot = state.resolve(
            series(
                latest_chapter=latest(NOW - timedelta(days=1)),
                breaks=[announced_break(NOW, NOW + timedelta(days=7))],
            ),
            NOW,
        )
        assert snapshot.icon_state is IconState.READY

    def test_a_break_beats_waiting_once_caught_up(self) -> None:
        chapter = latest(NOW - timedelta(days=1))
        snapshot = state.resolve(
            series(
                latest_chapter=chapter,
                last_read_external_id=chapter.external_id,
                breaks=[announced_break(NOW, NOW + timedelta(days=7))],
            ),
            NOW,
        )
        assert snapshot.phase is SeriesPhase.ANNOUNCED_BREAK
        assert snapshot.icon_state is IconState.BREAK

    def test_caught_up_and_waiting_is_due(self) -> None:
        chapter = latest(NOW - timedelta(days=1))
        snapshot = state.resolve(
            series(latest_chapter=chapter, last_read_external_id=chapter.external_id), NOW
        )
        assert snapshot.icon_state is IconState.DUE


class TestPhases:
    def test_a_finished_series_is_ended(self) -> None:
        chapter = latest(NOW - timedelta(days=400))
        snapshot = state.resolve(
            series(
                status=PublicationStatus.COMPLETED,
                latest_chapter=chapter,
                last_read_external_id=chapter.external_id,
            ),
            NOW,
        )
        assert snapshot.phase is SeriesPhase.ENDED
        assert snapshot.icon_state is IconState.DUE

    def test_a_release_days_out_is_waiting(self) -> None:
        chapter = latest(NOW - timedelta(days=1))
        snapshot = state.resolve(
            series(latest_chapter=chapter, last_read_external_id=chapter.external_id), NOW
        )
        assert snapshot.phase is SeriesPhase.WAITING

    def test_a_release_within_hours_is_imminent(self) -> None:
        # Deliberately a cadence with no weekday, so the projection is not
        # snapped onto a fixed slot and lands exactly six hours out.
        chapter = latest(NOW - timedelta(days=7) + timedelta(hours=6))
        snapshot = state.resolve(
            series(
                cadence=Cadence(period=timedelta(days=7), sample_size=8),
                latest_chapter=chapter,
                last_read_external_id=chapter.external_id,
            ),
            NOW,
        )
        assert snapshot.expected_next_at == NOW + timedelta(hours=6)
        assert snapshot.phase is SeriesPhase.IMMINENT

    def test_a_little_late_is_overdue(self) -> None:
        chapter = latest(NOW - timedelta(days=9))
        snapshot = state.resolve(
            series(latest_chapter=chapter, last_read_external_id=chapter.external_id), NOW
        )
        assert snapshot.phase is SeriesPhase.OVERDUE

    def test_long_silence_is_a_suspected_break(self) -> None:
        chapter = latest(NOW - timedelta(days=20))
        snapshot = state.resolve(
            series(latest_chapter=chapter, last_read_external_id=chapter.external_id), NOW
        )
        assert snapshot.phase is SeriesPhase.SUSPECTED_BREAK
        assert snapshot.icon_state is IconState.DUE, "a guess must never blacken the icon"
        assert "unannounced" in snapshot.tooltip

    def test_no_rhythm_and_nothing_unread_is_unknown(self) -> None:
        chapter = latest(NOW - timedelta(days=3))
        snapshot = state.resolve(
            series(
                cadence=Cadence(),
                latest_chapter=chapter,
                last_read_external_id=chapter.external_id,
            ),
            NOW,
        )
        assert snapshot.phase is SeriesPhase.UNKNOWN
        assert snapshot.expected_next_at is None

    def test_a_series_with_no_chapters_yet_is_unknown(self) -> None:
        assert state.resolve(series(), NOW).phase is SeriesPhase.UNKNOWN


class TestReadTracking:
    def test_reading_the_latest_chapter_clears_ready(self) -> None:
        chapter = latest(NOW - timedelta(days=1))
        assert state.resolve(series(latest_chapter=chapter), NOW).icon_state is IconState.READY
        caught_up = series(latest_chapter=chapter, last_read_external_id=chapter.external_id)
        assert state.resolve(caught_up, NOW).icon_state is not IconState.READY

    def test_a_newer_chapter_makes_it_ready_again(self) -> None:
        old = latest(NOW - timedelta(days=8), "1189")
        new = latest(NOW - timedelta(days=1), "1190")
        tracked = series(latest_chapter=new, last_read_external_id=old.external_id)
        assert state.resolve(tracked, NOW).icon_state is IconState.READY


class TestTooltip:
    def test_ready_names_the_chapter(self) -> None:
        snapshot = state.resolve(series(latest_chapter=latest(NOW - timedelta(days=1))), NOW)
        assert "ch. 1190" in snapshot.tooltip

    def test_a_break_explains_itself(self) -> None:
        chapter = latest(NOW - timedelta(days=1))
        snapshot = state.resolve(
            series(
                latest_chapter=chapter,
                last_read_external_id=chapter.external_id,
                breaks=[announced_break(NOW, NOW + timedelta(days=7))],
            ),
            NOW,
        )
        assert "golden week" in snapshot.tooltip


class TestAggregate:
    @pytest.mark.parametrize(
        ("states", "expected"),
        [
            ([IconState.DUE, IconState.READY, IconState.BREAK], IconState.READY),
            ([IconState.BREAK, IconState.BREAK], IconState.BREAK),
            ([IconState.BREAK, IconState.DUE], IconState.DUE),
            ([], IconState.DUE),
        ],
    )
    def test_folding_many_series_into_one_icon(
        self, states: list[IconState], expected: IconState
    ) -> None:
        assert state.aggregate(states) is expected
