"""The adaptive polling ladder: check harder as the due date approaches."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mangame.domain import schedule
from mangame.domain.models import Cadence, PublicationStatus, SeriesPhase
from mangame.domain.schedule import DAY, HOUR, MINUTE, PollInputs

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
WEEKLY = Cadence(period=timedelta(days=7), sample_size=8)


def inputs(**overrides: object) -> PollInputs:
    base: dict[str, object] = {
        "series_key": "one-piece",
        "now": NOW,
        "phase": SeriesPhase.WAITING,
        "status": PublicationStatus.ONGOING,
        "cadence": WEEKLY,
    }
    base.update(overrides)
    return PollInputs.model_validate(base)


def tier(**overrides: object) -> str:
    return schedule.decide(inputs(**overrides)).tier


class TestApproachingTheDueDate:
    """The core requirement: polling tightens as the release nears."""

    @pytest.mark.parametrize(
        ("distance", "expected"),
        [
            (timedelta(days=6), "far"),
            (timedelta(days=2), "approaching"),
            (timedelta(hours=6), "near"),
            (timedelta(hours=1), "imminent"),
            (timedelta(hours=-3), "hot"),
            (timedelta(days=-2), "late"),
            (timedelta(days=-7), "stalled"),
            (timedelta(days=-30), "dormant"),
        ],
    )
    def test_each_distance_selects_its_tier(self, distance: timedelta, expected: str) -> None:
        assert tier(expected_next_at=NOW + distance) == expected

    def test_intervals_shorten_monotonically_towards_the_release(self) -> None:
        distances = [
            timedelta(days=6),
            timedelta(days=2),
            timedelta(hours=6),
            timedelta(hours=1),
        ]
        intervals = [schedule.decide(inputs(expected_next_at=NOW + d)).interval for d in distances]
        assert intervals == sorted(intervals, reverse=True)

    def test_intervals_relax_again_once_a_series_goes_quiet(self) -> None:
        overdue = [timedelta(hours=-3), timedelta(days=-2), timedelta(days=-7), timedelta(days=-30)]
        intervals = [schedule.decide(inputs(expected_next_at=NOW + d)).interval for d in overdue]
        assert intervals == sorted(intervals)


class TestSpecialCases:
    def test_a_finished_series_is_barely_checked(self) -> None:
        decision = schedule.decide(inputs(status=PublicationStatus.COMPLETED))
        assert decision.tier == "ended"
        assert decision.interval >= 5 * DAY

    def test_an_unread_chapter_removes_the_urgency(self) -> None:
        assert tier(phase=SeriesPhase.UNREAD, expected_next_at=NOW + MINUTE) == "unread"

    def test_no_learned_rhythm_falls_back_to_twice_a_day(self) -> None:
        assert tier(cadence=Cadence(), expected_next_at=NOW + timedelta(hours=1)) == (
            "unknown-cadence"
        )

    def test_a_single_sample_is_not_a_rhythm(self) -> None:
        lone = Cadence(period=timedelta(days=11), sample_size=1)
        assert tier(cadence=lone, expected_next_at=NOW + timedelta(hours=1)) == "unknown-cadence"

    def test_a_release_with_no_projection_is_not_chased(self) -> None:
        assert tier(expected_next_at=None) == "unknown-cadence"


class TestBreaks:
    def test_an_indefinite_hiatus_is_checked_daily(self) -> None:
        assert tier(phase=SeriesPhase.ANNOUNCED_BREAK, break_ends_at=None) == "break-openended"

    def test_a_distant_break_is_checked_daily(self) -> None:
        assert (
            tier(
                phase=SeriesPhase.ANNOUNCED_BREAK,
                break_ends_at=NOW + timedelta(days=10),
            )
            == "break"
        )

    def test_polling_tightens_as_the_break_ends(self) -> None:
        assert (
            tier(phase=SeriesPhase.ANNOUNCED_BREAK, break_ends_at=NOW + timedelta(days=1))
            == "break-closing"
        )
        assert (
            tier(phase=SeriesPhase.ANNOUNCED_BREAK, break_ends_at=NOW + timedelta(hours=2))
            == "break-ending"
        )


class TestBackoff:
    def test_failures_slow_things_down(self) -> None:
        calm = schedule.decide(inputs(expected_next_at=NOW + timedelta(hours=1)))
        angry = schedule.decide(
            inputs(expected_next_at=NOW + timedelta(hours=1), consecutive_errors=5)
        )
        assert angry.interval > calm.interval

    def test_backoff_never_speeds_anything_up(self) -> None:
        slow = schedule.decide(inputs(status=PublicationStatus.COMPLETED, consecutive_errors=3))
        assert slow.interval >= 5 * DAY

    def test_backoff_is_capped(self) -> None:
        assert schedule._backoff(10 * MINUTE, 40) <= 4 * HOUR


class TestBoundsAndJitter:
    def test_nothing_is_ever_polled_faster_than_the_floor(self) -> None:
        for errors in range(4):
            for phase in SeriesPhase:
                decision = schedule.decide(
                    inputs(phase=phase, expected_next_at=NOW, consecutive_errors=errors)
                )
                assert decision.interval >= schedule.MIN_INTERVAL
                assert decision.interval <= schedule.MAX_INTERVAL

    def test_a_source_can_ask_to_be_left_alone_for_longer(self) -> None:
        decision = schedule.decide(
            inputs(expected_next_at=NOW, source_min_interval=timedelta(hours=2))
        )
        assert decision.interval >= timedelta(hours=2)

    def test_jitter_is_deterministic_so_restarts_do_not_stampede(self) -> None:
        first = schedule.decide(inputs(expected_next_at=NOW + timedelta(hours=1)))
        second = schedule.decide(inputs(expected_next_at=NOW + timedelta(hours=1)))
        assert first.interval == second.interval

    def test_different_series_are_spread_out(self) -> None:
        intervals = {
            schedule.decide(
                inputs(series_key=f"series-{i}", expected_next_at=NOW + timedelta(hours=1))
            ).interval
            for i in range(12)
        }
        assert len(intervals) > 8, "most series should land on distinct moments"

    def test_jitter_stays_inside_its_band(self) -> None:
        for i in range(50):
            spread = schedule._jitter(HOUR, f"s{i}", "near")
            assert abs(spread - HOUR) <= HOUR * schedule.JITTER_RATIO

    def test_the_decision_carries_an_absolute_due_time(self) -> None:
        # Wall-clock, not a sleep: a laptop that suspends for a day must notice
        # what it owes the moment it wakes.
        decision = schedule.decide(inputs(expected_next_at=NOW + timedelta(hours=1)))
        assert decision.due_at == NOW + decision.interval

    def test_every_decision_explains_itself(self) -> None:
        decision = schedule.decide(inputs(expected_next_at=NOW + timedelta(hours=1)))
        assert decision.reason
