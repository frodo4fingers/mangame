"""Turn raw source signals into announced-break windows.

Break detection is ranked by how much the signal can be trusted:

1. **Publisher next-chapter date** — MANGA Plus/Viz style "next chapter on X".
   If that date is meaningfully later than the learned rhythm predicts, the gap
   *is* the break. This is the single strongest signal and it is stated
   outright, so it earns :attr:`Confidence.HIGH`.
2. **Explicit hiatus flags** — AniList ``HIATUS``, MangaUpdates hiatus.
3. **Magazine skip calendars** — combined/double issues, Golden Week and New
   Year gaps. Known in advance for a whole magazine, so one calendar entry
   covers every series it carries.
4. **Silence** — only ever :attr:`Confidence.LOW`, and deliberately *not*
   enough to blacken the icon.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from mangame.domain.cadence import expected_next
from mangame.domain.models import BreakWindow, Cadence, Confidence, PublicationStatus

#: A stated next-release later than the prediction by more than this fraction
#: of one period counts as a skipped slot rather than ordinary slippage.
SLIP_TOLERANCE = 0.45

#: How long silence must last, relative to one period, before we *suspect*
#: (but never announce) a break.
SUSPICION_FACTOR = 0.6


def from_announced_next(
    *,
    announced_next_at: datetime | None,
    last_release_at: datetime | None,
    cadence: Cadence,
    source_id: str,
) -> BreakWindow | None:
    """Derive a break from a publisher-stated next-chapter date."""
    if announced_next_at is None or last_release_at is None or cadence.period is None:
        return None

    predicted = expected_next(cadence, last_release_at)
    if predicted is None:
        return None

    slip = announced_next_at - predicted
    if slip <= cadence.period * SLIP_TOLERANCE:
        return None

    skipped = max(1, round(slip / cadence.period))
    return BreakWindow(
        starts_at=predicted,
        ends_at=announced_next_at,
        reason=f"no chapter for {skipped} slot(s); next announced for {announced_next_at:%Y-%m-%d}",
        source_id=source_id,
        confidence=Confidence.HIGH,
    )


def from_status(*, status: PublicationStatus, now: datetime, source_id: str) -> BreakWindow | None:
    """Derive an open-ended break from an explicit hiatus flag."""
    if status is not PublicationStatus.HIATUS:
        return None
    return BreakWindow(
        starts_at=now,
        ends_at=None,
        reason="series flagged as on hiatus",
        source_id=source_id,
        confidence=Confidence.HIGH,
    )


def is_suspected(*, now: datetime, expected_next_at: datetime | None, cadence: Cadence) -> bool:
    """Silence long enough to look like an unannounced break.

    Intentionally never produces a :class:`BreakWindow`: the black icon means
    *announced*, so an inference only shows up in the tooltip.
    """
    if expected_next_at is None or cadence.period is None:
        return False
    overdue = now - expected_next_at
    return overdue > cadence.period * SUSPICION_FACTOR


def merge(windows: Iterable[BreakWindow]) -> list[BreakWindow]:
    """Collapse overlapping windows, keeping the most trusted reason."""
    rank = {Confidence.HIGH: 2, Confidence.MEDIUM: 1, Confidence.LOW: 0}
    ordered = sorted(windows, key=lambda w: w.starts_at)
    merged: list[BreakWindow] = []

    for window in ordered:
        if not merged:
            merged.append(window)
            continue

        last = merged[-1]
        last_end = last.ends_at
        if last_end is not None and window.starts_at > last_end:
            merged.append(window)
            continue

        winner = window if rank[window.confidence] > rank[last.confidence] else last
        end = None if last_end is None or window.ends_at is None else max(last_end, window.ends_at)
        merged[-1] = winner.model_copy(update={"starts_at": last.starts_at, "ends_at": end})

    return merged


def active(windows: Iterable[BreakWindow], now: datetime) -> BreakWindow | None:
    """The announced break covering ``now``, or the next one starting soon.

    A break that starts within one day is already worth showing: that is
    precisely the "no chapter this week" heads-up the black icon exists for.
    """
    horizon = now + timedelta(days=1)
    candidates = [
        w
        for w in windows
        if w.confidence in (Confidence.HIGH, Confidence.MEDIUM)
        and (w.covers(now) or w.starts_at <= horizon)
        and (w.ends_at is None or w.ends_at > now)
    ]
    return min(candidates, key=lambda w: w.starts_at) if candidates else None


def utcnow() -> datetime:
    return datetime.now(UTC)
