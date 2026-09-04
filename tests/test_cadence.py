"""Cadence learning: the layer that lets any source get away with timestamps only."""

from datetime import UTC, datetime, timedelta

from mangame.domain import cadence as cadence_rules
from tests.conftest import chapter, weekly

START = datetime(2026, 1, 4, 15, 0, tzinfo=UTC)  # a Sunday


class TestReleaseEvents:
    def test_batches_within_the_window_collapse_to_one_release(self) -> None:
        dump = [
            chapter("1", START),
            chapter("2", START + timedelta(hours=1)),
            chapter("3", START + timedelta(hours=2)),
        ]
        events = cadence_rules.release_events(dump)
        assert len(events) == 1
        assert events[0].at == START
        assert events[0].number == 3.0, "a batch carries its highest chapter number"

    def test_releases_further_apart_than_the_window_stay_separate(self) -> None:
        events = cadence_rules.release_events(
            [chapter("1", START), chapter("2", START + timedelta(hours=19))]
        )
        assert len(events) == 2

    def test_late_backfill_of_old_chapters_is_discarded(self) -> None:
        # Exactly the MangaDex One Piece shape: chapters 1-3 uploaded long
        # after chapter 1148, which naive time ordering reads as a new release.
        history = [
            chapter("1148", datetime(2025, 5, 21, tzinfo=UTC)),
            chapter("1", datetime(2025, 10, 22, 1, 9, tzinfo=UTC)),
            chapter("2", datetime(2025, 10, 22, 1, 10, tzinfo=UTC)),
            chapter("3", datetime(2025, 10, 22, 1, 11, tzinfo=UTC)),
            chapter("1189", datetime(2026, 7, 29, tzinfo=UTC)),
            chapter("1190", datetime(2026, 8, 9, tzinfo=UTC)),
        ]
        assert [c.number for c in cadence_rules._forward_run(history)] == ["1148", "1189", "1190"]

    def test_unnumbered_chapters_fall_back_to_time_order(self) -> None:
        history = [chapter(None, START), chapter(None, START + timedelta(days=7))]
        assert len(cadence_rules.release_events(history)) == 2

    def test_the_same_chapter_from_two_sources_is_one_release(self) -> None:
        # The real One Piece shape: MANGA Plus publishes, MangaDex relists the
        # very same chapter three days later. Two sightings, one release.
        history = [
            chapter("1189", START, source_id="mangaplus"),
            chapter("1189", START + timedelta(days=3), source_id="mangadex"),
        ]
        events = cadence_rules.release_events(history)

        assert len(events) == 1
        assert events[0].at == START, "a chapter is released when it first appears anywhere"

    def test_a_lagging_mirror_does_not_shorten_the_next_gap(self) -> None:
        # The subtler half of the same bug: the late copy also sits between
        # its own chapter and the next one, making that interval look short.
        history = [
            chapter("1189", START, source_id="mangaplus"),
            chapter("1189", START + timedelta(days=3), source_id="mangadex"),
            chapter("1190", START + timedelta(days=14), source_id="mangaplus"),
        ]
        events = cadence_rules.release_events(history)

        assert cadence_rules._intervals(events) == [timedelta(days=14)]

    def test_release_times_returns_plain_moments(self) -> None:
        assert cadence_rules.release_times(weekly(3, start=START)) == [
            START,
            START + timedelta(days=7),
            START + timedelta(days=14),
        ]


class TestIntervals:
    def test_a_skipped_chapter_is_normalised_not_doubled(self) -> None:
        events = cadence_rules.release_events(
            [chapter("10", START), chapter("12", START + timedelta(days=14))]
        )
        assert cadence_rules._intervals(events) == [timedelta(days=7)]

    def test_a_coverage_hole_is_dropped_rather_than_guessed(self) -> None:
        # 41 chapters missing is a gap in the source, not a 14-month break.
        events = cadence_rules.release_events(
            [chapter("1148", START), chapter("1189", START + timedelta(days=434))]
        )
        assert cadence_rules._intervals(events) == []

    def test_consecutive_chapters_keep_their_real_gap(self) -> None:
        events = cadence_rules.release_events(
            [chapter("1189", START), chapter("1190", START + timedelta(days=11))]
        )
        assert cadence_rules._intervals(events) == [timedelta(days=11)]


class TestEstimate:
    def test_learns_a_weekly_rhythm_with_weekday_and_hour(self) -> None:
        cadence = cadence_rules.estimate(weekly(10, start=START))
        assert cadence.period == timedelta(days=7)
        assert cadence.weekday == START.weekday()
        assert cadence.hour == 15
        assert cadence.is_known
        assert cadence.score > 0.8

    def test_learns_a_fortnightly_rhythm(self) -> None:
        chapters = weekly(8, start=START, step=timedelta(days=14))
        assert cadence_rules.estimate(chapters).period == timedelta(days=14)

    def test_a_single_skipped_week_does_not_move_the_period(self) -> None:
        chapters = weekly(8, start=START)
        chapters.append(chapter("9", START + timedelta(days=63)))  # a fortnight gap
        chapters += [chapter("10", START + timedelta(days=70))]
        assert cadence_rules.estimate(chapters).period == timedelta(days=7)

    def test_near_weekly_timing_snaps_to_exactly_a_week(self) -> None:
        drifting = [
            chapter(str(i + 1), START + timedelta(days=7 * i, hours=i * 3)) for i in range(8)
        ]
        assert cadence_rules.estimate(drifting).period == timedelta(days=7)

    def test_a_lone_interval_is_measured_but_not_trusted(self) -> None:
        cadence = cadence_rules.estimate(
            [chapter("1189", START), chapter("1190", START + timedelta(days=11))]
        )
        assert cadence.period == timedelta(days=11)
        assert not cadence.is_known, "one sample must not drive tight polling"
        assert cadence.score == 0.0

    def test_a_mirror_that_always_lags_does_not_move_the_rhythm(self) -> None:
        # Adding a second source must not change what the series' rhythm *is*.
        # Before duplicate chapters were collapsed, this mirror pulled the
        # fortnightly period down to 11 days, and because 11 is not a multiple
        # of a week the weekday and hour stopped being learned at all — so the
        # tray predicted the wrong day as well as the wrong date.
        official = weekly(6, start=START, step=timedelta(days=14), source_id="mangaplus")
        mirror = [
            chapter(c.number, c.published_at + timedelta(days=3), source_id="mangadex")
            for c in official
        ]

        cadence = cadence_rules.estimate(official + mirror)

        assert cadence.period == timedelta(days=14)
        assert cadence.weekday == START.weekday()
        assert cadence.hour == 15

    def test_a_second_source_only_makes_the_estimate_more_confident(self) -> None:
        official = weekly(6, start=START, source_id="mangaplus")
        mirror = [
            chapter(c.number, c.published_at + timedelta(minutes=20), source_id="mangadex")
            for c in official
        ]

        alone = cadence_rules.estimate(official)
        mirrored = cadence_rules.estimate(official + mirror)

        assert mirrored.period == alone.period
        assert mirrored.jitter == alone.jitter, "a duplicate must not look like irregularity"
        assert mirrored.sample_size == alone.sample_size

    def test_omake_only_coverage_yields_no_cadence(self) -> None:
        # MangaDex carries only the ".5" side chapters for some licensed series.
        omake = [
            chapter("124.5", datetime(2025, 4, 9, tzinfo=UTC)),
            chapter("136.5", datetime(2025, 8, 6, tzinfo=UTC)),
            chapter("149.5", datetime(2025, 9, 8, tzinfo=UTC)),
            chapter("156.5", datetime(2025, 12, 8, tzinfo=UTC)),
        ]
        cadence = cadence_rules.estimate(omake)
        assert cadence.period is None
        assert not cadence.is_known

    def test_no_history_is_not_an_error(self) -> None:
        assert cadence_rules.estimate([]).period is None
        assert cadence_rules.estimate(weekly(1, start=START)).sample_size == 0

    def test_non_weekly_periods_do_not_claim_a_weekday(self) -> None:
        cadence = cadence_rules.estimate(weekly(8, start=START, step=timedelta(days=3)))
        assert cadence.period == timedelta(days=3)
        assert cadence.weekday is None


class TestExpectedNext:
    def test_projects_one_period_ahead(self) -> None:
        cadence = cadence_rules.estimate(weekly(8, start=START, step=timedelta(days=3)))
        last = START + timedelta(days=21)
        assert cadence_rules.expected_next(cadence, last) == last + timedelta(days=3)

    def test_weekly_rhythms_snap_back_onto_the_learned_slot(self) -> None:
        cadence = cadence_rules.estimate(weekly(10, start=START))
        late = START + timedelta(days=63, hours=5)  # a chapter that slipped 5h
        projected = cadence_rules.expected_next(cadence, late)
        assert projected is not None
        assert projected.weekday() == START.weekday()
        assert projected.hour == 15
        assert timedelta(days=6) < projected - late < timedelta(days=8)

    def test_without_a_period_there_is_no_projection(self) -> None:
        from mangame.domain.models import Cadence

        assert cadence_rules.expected_next(Cadence(), START) is None
        assert (
            cadence_rules.expected_next(cadence_rules.estimate(weekly(10, start=START)), None)
            is None
        )
