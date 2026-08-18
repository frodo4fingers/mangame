"""Resolve a tracked series into the icon state the user actually sees.

Precedence is deliberate and is the whole product in one rule:

    READY  >  BREAK  >  DUE

"Is there something to read?" always wins — an announced break does not make a
freshly published chapter less readable. Only once you are caught up does the
icon switch to black to tell you the next slot is cancelled.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from mangame.domain import breaks
from mangame.domain.cadence import expected_next
from mangame.domain.models import (
    BreakWindow,
    IconState,
    PublicationStatus,
    SeriesPhase,
    SeriesSnapshot,
    TrackedSeries,
)

#: How close to the expected moment counts as "any minute now".
IMMINENT_WINDOW = timedelta(hours=12)


def _phase(series: TrackedSeries, now: datetime, expected_next_at: datetime | None) -> SeriesPhase:
    if series.has_unread:
        return SeriesPhase.UNREAD
    if series.status in (PublicationStatus.COMPLETED, PublicationStatus.CANCELLED):
        return SeriesPhase.ENDED
    if breaks.active(series.breaks, now) is not None:
        return SeriesPhase.ANNOUNCED_BREAK
    if expected_next_at is None:
        return SeriesPhase.UNKNOWN
    if now < expected_next_at - IMMINENT_WINDOW:
        return SeriesPhase.WAITING
    if now <= expected_next_at:
        return SeriesPhase.IMMINENT
    if breaks.is_suspected(now=now, expected_next_at=expected_next_at, cadence=series.cadence):
        return SeriesPhase.SUSPECTED_BREAK
    return SeriesPhase.OVERDUE


def icon_state_for(phase: SeriesPhase) -> IconState:
    if phase is SeriesPhase.UNREAD:
        return IconState.READY
    if phase is SeriesPhase.ANNOUNCED_BREAK:
        return IconState.BREAK
    return IconState.DUE


def _tooltip(
    series: TrackedSeries,
    phase: SeriesPhase,
    expected_next_at: datetime | None,
    active_break: BreakWindow | None,
) -> str:
    latest = series.latest_chapter
    chapter = f"ch. {latest.number}" if latest and latest.number else "latest chapter"

    if phase is SeriesPhase.UNREAD:
        return f"{series.title} — {chapter} is ready to read"
    if phase is SeriesPhase.ANNOUNCED_BREAK:
        reason = (active_break.reason if active_break else "") or "on break"
        return f"{series.title} — on break ({reason})"
    if phase is SeriesPhase.ENDED:
        return f"{series.title} — {series.status.value}"
    if phase is SeriesPhase.SUSPECTED_BREAK:
        return f"{series.title} — overdue, possibly on an unannounced break"
    if expected_next_at is not None:
        return f"{series.title} — next chapter expected {expected_next_at:%a %d %b %H:%M} UTC"
    return f"{series.title} — release schedule unknown"


def resolve(series: TrackedSeries, now: datetime) -> SeriesSnapshot:
    """Compute everything the tray needs to draw one series."""
    last_release_at = series.latest_chapter.published_at if series.latest_chapter else None
    expected_next_at = expected_next(series.cadence, last_release_at)
    phase = _phase(series, now, expected_next_at)
    active_break = breaks.active(series.breaks, now)

    return SeriesSnapshot(
        key=series.key,
        title=series.title,
        emblem=series.emblem,
        icon_state=icon_state_for(phase),
        phase=phase,
        expected_next_at=expected_next_at,
        active_break=active_break,
        latest_chapter=series.latest_chapter,
        tooltip=_tooltip(series, phase, expected_next_at, active_break),
    )


def aggregate(states: list[IconState]) -> IconState:
    """Fold several series into one icon, for the summary tray entry."""
    if IconState.READY in states:
        return IconState.READY
    if states and all(s is IconState.BREAK for s in states):
        return IconState.BREAK
    return IconState.DUE
