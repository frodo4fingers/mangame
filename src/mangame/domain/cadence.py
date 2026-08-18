"""Learn a series' release rhythm from nothing but publication timestamps.

This is the trick that makes "support a huge variety of sources with minimal
effort" tractable. A source only has to answer *"which chapters exist and when
were they published"* — the cheapest thing any API, RSS feed or HTML page can
offer. Everything else (when the next one is due, how hard to poll, whether a
break is under way) is derived here.
"""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta
from itertools import pairwise

from mangame.domain.models import Cadence, Chapter, Release

#: Chapters published within this window are one "drop", not two releases.
BATCH_WINDOW = timedelta(hours=18)

#: Only the recent past is predictive; older history biases towards dead rhythms.
MAX_INTERVALS = 12

#: Beyond this many chapters between two known releases, the source has a
#: coverage hole rather than a rhythm worth measuring.
MAX_NUMBER_STEP = 4.0


def _numeric(chapter: Chapter) -> float | None:
    if chapter.number is None:
        return None
    try:
        return float(chapter.number)
    except ValueError:
        return None


def _forward_run(chapters: Sequence[Chapter]) -> list[Chapter]:
    """Keep the trailing run where publish time rises with chapter number.

    Aggregators routinely backfill old chapters long after the fact: MangaDex
    carries One Piece 1-3 stamped months *after* chapter 1148. Ordered purely
    by time that backfill looks like a brand-new release and poisons every
    interval. Walking back from the newest chapter and stopping at the first
    out-of-order timestamp keeps exactly the stretch of history that actually
    describes the current rhythm.
    """
    keyed = [(number, c) for c in chapters if (number := _numeric(c)) is not None]
    if len(keyed) < 2:
        return list(chapters)

    keyed.sort(key=lambda pair: (pair[0], pair[1].published_at))
    run = [keyed[-1][1]]
    for _, chapter in reversed(keyed[:-1]):
        if chapter.published_at > run[0].published_at:
            break
        run.insert(0, chapter)
    return run


#: Cadences publishers actually use, snapped to when we are close enough.
CANONICAL_PERIODS: tuple[timedelta, ...] = (
    timedelta(days=1),
    timedelta(days=2),
    timedelta(days=3),
    timedelta(days=7),
    timedelta(days=14),
    timedelta(days=21),
    timedelta(days=28),
    timedelta(days=30),
    timedelta(days=60),
    timedelta(days=90),
)
SNAP_TOLERANCE = 0.15


def _as_utc(moment: datetime) -> datetime:
    return moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC)


def release_events(chapters: Iterable[Chapter]) -> list[Release]:
    """Collapse chapters into distinct release moments, oldest first.

    Two kinds of noise are removed here, because everything downstream
    (cadence, expected-next, break detection, poll pacing) reads this list:

    * multi-chapter dumps, common on aggregators and catch-up scanlations,
      would otherwise look like a several-times-a-day cadence;
    * late backfills of old chapters would otherwise look like fresh releases.

    Each event carries the highest chapter number in its batch, so callers can
    tell "one chapter later" from "forty-one chapters later".
    """
    ordered = _forward_run(list(chapters))
    stamped = sorted((_as_utc(c.published_at), _numeric(c)) for c in ordered)

    events: list[Release] = []
    for moment, number in stamped:
        if events and moment - events[-1].at <= BATCH_WINDOW:
            last = events[-1]
            if number is not None and (last.number is None or number > last.number):
                events[-1] = Release(at=last.at, number=number)
            continue
        events.append(Release(at=moment, number=number))
    return events


def release_times(chapters: Iterable[Chapter]) -> list[datetime]:
    """Just the moments from :func:`release_events`."""
    return [event.at for event in release_events(chapters)]


def _intervals(events: Sequence[Release]) -> list[timedelta]:
    """Turn consecutive releases into per-chapter intervals.

    A source that carries chapters 1148 and 1189 but nothing between them is
    not telling us a series took fourteen months off — it is telling us it has
    a hole. Small skips are normalised by the number of chapters they span;
    large ones are dropped rather than guessed at.
    """
    spans: list[timedelta] = []
    for earlier, later in pairwise(events):
        span = later.at - earlier.at
        if span <= timedelta(0):
            continue
        if earlier.number is not None and later.number is not None:
            step = later.number - earlier.number
            if step > MAX_NUMBER_STEP:
                continue
            if step > 1.0:
                span /= step
        spans.append(span)
    return spans


def _robust_period(intervals: Sequence[timedelta]) -> tuple[timedelta, timedelta] | None:
    """Return ``(period, jitter)`` using a median that ignores break-inflated gaps."""
    if not intervals:
        return None

    seconds = [i.total_seconds() for i in intervals]
    rough = statistics.median(seconds)
    if rough <= 0:
        return None

    # Second pass: a skipped week doubles the gap and would drag a plain mean
    # far off. Keep only intervals close to the rough median, then re-measure.
    kept = [s for s in seconds if 0.5 * rough <= s <= 1.75 * rough] or seconds
    period_seconds = statistics.median(kept)
    deviations = [abs(s - period_seconds) for s in kept]
    jitter_seconds = statistics.median(deviations) if deviations else 0.0
    return timedelta(seconds=period_seconds), timedelta(seconds=jitter_seconds)


def _snap(period: timedelta) -> timedelta:
    for canonical in CANONICAL_PERIODS:
        delta = abs(period.total_seconds() - canonical.total_seconds())
        if delta / canonical.total_seconds() <= SNAP_TOLERANCE:
            return canonical
    return period


def _is_weekly_multiple(period: timedelta) -> bool:
    weeks = period.total_seconds() / timedelta(days=7).total_seconds()
    return weeks >= 0.9 and abs(weeks - round(weeks)) <= 0.12


def estimate(chapters: Iterable[Chapter]) -> Cadence:
    """Derive a :class:`Cadence` from a series' publication history."""
    events = release_events(chapters)
    if len(events) < 2:
        return Cadence(sample_size=0)

    recent = events[-(MAX_INTERVALS + 1) :]
    intervals = _intervals(recent)
    measured = _robust_period(intervals)
    if measured is None:
        return Cadence(sample_size=0)

    period, jitter = measured
    period = _snap(period)

    weekday: int | None = None
    hour: int | None = None
    if _is_weekly_multiple(period):
        weekday = Counter(e.at.weekday() for e in recent).most_common(1)[0][0]
        hour = Counter(e.at.hour for e in recent).most_common(1)[0][0]

    return Cadence(
        period=period,
        weekday=weekday,
        hour=hour,
        sample_size=len(intervals),
        jitter=jitter,
    )


def expected_next(cadence: Cadence, last_release_at: datetime | None) -> datetime | None:
    """Project the next release moment.

    For weekly rhythms the projection is snapped onto the learned weekday and
    hour, so a chapter that slipped by a few hours does not permanently drag
    the whole schedule.
    """
    if last_release_at is None or cadence.period is None:
        return None

    base = _as_utc(last_release_at) + cadence.period
    if cadence.weekday is None or not _is_weekly_multiple(cadence.period):
        return base

    if cadence.hour is not None:
        base = base.replace(hour=cadence.hour, minute=0, second=0, microsecond=0)

    offset = (cadence.weekday - base.weekday()) % 7
    if offset > 3:
        offset -= 7
    return base + timedelta(days=offset)
