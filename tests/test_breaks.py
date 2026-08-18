"""Break detection — the logic behind the black icon."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mangame.domain import breaks
from mangame.domain.models import BreakWindow, Cadence, Confidence, PublicationStatus

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
WEEKLY = Cadence(period=timedelta(days=7), sample_size=8, jitter=timedelta(hours=2))
LAST = datetime(2026, 8, 9, 15, 0, tzinfo=UTC)


def window(
    start: datetime,
    end: datetime | None,
    confidence: Confidence = Confidence.HIGH,
    reason: str = "",
) -> BreakWindow:
    return BreakWindow(starts_at=start, ends_at=end, confidence=confidence, reason=reason)


class TestFromAnnouncedNext:
    def test_a_stated_date_a_week_late_is_a_break(self) -> None:
        result = breaks.from_announced_next(
            announced_next_at=LAST + timedelta(days=14),
            last_release_at=LAST,
            cadence=WEEKLY,
            source_id="mangadex",
        )
        assert result is not None
        assert result.confidence is Confidence.HIGH
        assert result.ends_at == LAST + timedelta(days=14)
        assert "1 slot" in result.reason

    def test_ordinary_slippage_is_not_a_break(self) -> None:
        assert (
            breaks.from_announced_next(
                announced_next_at=LAST + timedelta(days=7, hours=20),
                last_release_at=LAST,
                cadence=WEEKLY,
                source_id="mangadex",
            )
            is None
        )

    def test_a_long_gap_counts_the_skipped_slots(self) -> None:
        result = breaks.from_announced_next(
            announced_next_at=LAST + timedelta(days=28),
            last_release_at=LAST,
            cadence=WEEKLY,
            source_id="mangadex",
        )
        assert result is not None
        assert "3 slot" in result.reason

    @pytest.mark.parametrize(
        ("announced", "last", "cadence"),
        [
            (None, LAST, WEEKLY),
            (LAST + timedelta(days=14), None, WEEKLY),
            (LAST + timedelta(days=14), LAST, Cadence()),
        ],
    )
    def test_missing_inputs_produce_nothing(
        self, announced: datetime | None, last: datetime | None, cadence: Cadence
    ) -> None:
        assert (
            breaks.from_announced_next(
                announced_next_at=announced,
                last_release_at=last,
                cadence=cadence,
                source_id="x",
            )
            is None
        )


class TestFromStatus:
    def test_a_hiatus_flag_opens_an_indefinite_break(self) -> None:
        result = breaks.from_status(status=PublicationStatus.HIATUS, now=NOW, source_id="anilist")
        assert result is not None
        assert result.ends_at is None
        assert result.confidence is Confidence.HIGH

    @pytest.mark.parametrize(
        "status",
        [
            PublicationStatus.ONGOING,
            PublicationStatus.COMPLETED,
            PublicationStatus.CANCELLED,
            PublicationStatus.UNKNOWN,
        ],
    )
    def test_every_other_status_is_not_a_break(self, status: PublicationStatus) -> None:
        assert breaks.from_status(status=status, now=NOW, source_id="x") is None


class TestIsSuspected:
    def test_silence_past_the_tolerance_is_suspicious(self) -> None:
        assert breaks.is_suspected(
            now=NOW, expected_next_at=NOW - timedelta(days=5), cadence=WEEKLY
        )

    def test_being_slightly_late_is_not(self) -> None:
        assert not breaks.is_suspected(
            now=NOW, expected_next_at=NOW - timedelta(days=3), cadence=WEEKLY
        )

    def test_nothing_to_compare_against_is_never_suspicious(self) -> None:
        assert not breaks.is_suspected(now=NOW, expected_next_at=None, cadence=WEEKLY)
        assert not breaks.is_suspected(
            now=NOW, expected_next_at=NOW - timedelta(days=90), cadence=Cadence()
        )


class TestMerge:
    def test_overlapping_windows_become_one(self) -> None:
        merged = breaks.merge(
            [
                window(NOW, NOW + timedelta(days=7)),
                window(NOW + timedelta(days=3), NOW + timedelta(days=10)),
            ]
        )
        assert len(merged) == 1
        assert merged[0].starts_at == NOW
        assert merged[0].ends_at == NOW + timedelta(days=10)

    def test_the_most_trusted_reason_wins(self) -> None:
        merged = breaks.merge(
            [
                window(NOW, NOW + timedelta(days=7), Confidence.LOW, "guessed"),
                window(NOW + timedelta(days=1), NOW + timedelta(days=5), Confidence.HIGH, "stated"),
            ]
        )
        assert merged[0].reason == "stated"
        assert merged[0].confidence is Confidence.HIGH

    def test_disjoint_windows_are_kept_apart(self) -> None:
        merged = breaks.merge(
            [
                window(NOW, NOW + timedelta(days=2)),
                window(NOW + timedelta(days=20), NOW + timedelta(days=25)),
            ]
        )
        assert len(merged) == 2

    def test_an_open_ended_window_swallows_what_follows(self) -> None:
        merged = breaks.merge(
            [window(NOW, None), window(NOW + timedelta(days=30), NOW + timedelta(days=40))]
        )
        assert len(merged) == 1
        assert merged[0].ends_at is None

    def test_merging_nothing_is_fine(self) -> None:
        assert breaks.merge([]) == []


class TestActive:
    def test_a_window_covering_now_is_active(self) -> None:
        active = breaks.active([window(NOW - timedelta(days=1), NOW + timedelta(days=3))], NOW)
        assert active is not None

    def test_a_break_starting_tomorrow_already_counts(self) -> None:
        # This is the "no chapter this week" heads-up the black icon is for.
        active = breaks.active([window(NOW + timedelta(hours=20), NOW + timedelta(days=8))], NOW)
        assert active is not None

    def test_a_break_starting_next_month_does_not(self) -> None:
        assert (
            breaks.active([window(NOW + timedelta(days=30), NOW + timedelta(days=37))], NOW) is None
        )

    def test_a_finished_break_does_not(self) -> None:
        assert (
            breaks.active([window(NOW - timedelta(days=10), NOW - timedelta(days=3))], NOW) is None
        )

    def test_inferred_breaks_never_blacken_the_icon(self) -> None:
        assert (
            breaks.active(
                [window(NOW - timedelta(days=1), NOW + timedelta(days=3), Confidence.LOW)], NOW
            )
            is None
        )

    def test_the_earliest_candidate_wins(self) -> None:
        early = window(NOW - timedelta(days=1), NOW + timedelta(days=2), reason="early")
        late = window(NOW, NOW + timedelta(days=9), reason="late")
        active = breaks.active([late, early], NOW)
        assert active is not None
        assert active.reason == "early"
