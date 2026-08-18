"""Adaptive polling policy: cheap when nothing can happen, hot when it can.

The baseline is one scan a day. As the learned due-date approaches, the
interval for *that series on that source* collapses towards minutes; once the
chapter lands (or an announced break removes the slot entirely) it relaxes
straight back to daily. Announced breaks are the biggest saving of all — a
series on hiatus is checked once a day purely to notice when it returns.

Everything here is a pure function of ``(now, snapshot-ish inputs)`` so the
whole ladder is unit-testable without a clock or a network.
"""

import hashlib
from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from mangame.domain.models import Cadence, PublicationStatus, SeriesPhase

MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)

#: Hard ceiling — even a finished series gets looked at now and then.
MAX_INTERVAL = timedelta(days=7)

#: Never hammer a source faster than this, whatever the ladder says.
MIN_INTERVAL = 5 * MINUTE

#: ± this fraction, derived deterministically from the series key, so a user
#: tracking thirty titles does not fire thirty requests in the same second.
JITTER_RATIO = 0.12


class PollDecision(BaseModel):
    """Why we chose an interval — surfaced in logs and the diagnostics view."""

    model_config = ConfigDict(frozen=True)

    interval: timedelta
    tier: str
    due_at: datetime
    reason: str = ""


class PollInputs(BaseModel):
    """Everything the ladder needs, and nothing else."""

    series_key: str
    now: datetime
    phase: SeriesPhase
    status: PublicationStatus = PublicationStatus.UNKNOWN
    cadence: Cadence = Field(default_factory=Cadence)
    expected_next_at: datetime | None = None
    break_ends_at: datetime | None = None
    consecutive_errors: int = Field(default=0, ge=0)
    source_min_interval: timedelta = MIN_INTERVAL


def _ladder(inp: PollInputs) -> tuple[timedelta, str, str]:
    """The interval ladder. Ordered most-specific first; first match wins."""
    now = inp.now

    if inp.status in (PublicationStatus.COMPLETED, PublicationStatus.CANCELLED):
        return MAX_INTERVAL, "ended", "series finished; only checking for revivals"

    if inp.phase is SeriesPhase.UNREAD:
        return 12 * HOUR, "unread", "chapter already waiting; nothing urgent to find"

    if inp.phase is SeriesPhase.ANNOUNCED_BREAK:
        if inp.break_ends_at is None:
            return DAY, "break-openended", "indefinite hiatus; daily check for a return"
        remaining = inp.break_ends_at - now
        if remaining <= 6 * HOUR:
            return 15 * MINUTE, "break-ending", "announced break is about to end"
        if remaining <= 2 * DAY:
            return 3 * HOUR, "break-closing", "announced break ends within two days"
        return DAY, "break", "announced break; slot is cancelled"

    if inp.expected_next_at is None or not inp.cadence.is_known:
        return 12 * HOUR, "unknown-cadence", "no rhythm learned yet; sampling twice a day"

    distance = inp.expected_next_at - now

    if distance > 3 * DAY:
        return DAY, "far", "release is days away"
    if distance > 12 * HOUR:
        return 6 * HOUR, "approaching", "release is within three days"
    if distance > 2 * HOUR:
        return HOUR, "near", "release is within twelve hours"
    if distance > timedelta(0):
        return 10 * MINUTE, "imminent", "release is due within two hours"

    overdue = -distance
    if overdue <= 12 * HOUR:
        return 10 * MINUTE, "hot", "due now; watching closely"
    if overdue <= 3 * DAY:
        return 45 * MINUTE, "late", "overdue but still plausible"
    if overdue <= 14 * DAY:
        return 6 * HOUR, "stalled", "long overdue; probably an unannounced break"
    return DAY, "dormant", "no release for a fortnight past schedule"


def _backoff(interval: timedelta, errors: int) -> timedelta:
    """Exponential backoff that can only ever slow us down, never speed us up."""
    if errors <= 0:
        return interval
    steps = min(errors - 1, 8)
    penalty = min(MINUTE * (5 * (1 << steps)), 4 * HOUR)
    return max(interval, penalty)


def _jitter(interval: timedelta, series_key: str, tier: str) -> timedelta:
    digest = hashlib.blake2s(f"{series_key}:{tier}".encode(), digest_size=4).digest()
    unit = int.from_bytes(digest, "big") / 0xFFFFFFFF  # 0.0 - 1.0
    factor = 1.0 + (unit * 2.0 - 1.0) * JITTER_RATIO
    return timedelta(seconds=interval.total_seconds() * factor)


def decide(inp: PollInputs) -> PollDecision:
    """Choose when this series should next be polled on this source."""
    interval, tier, reason = _ladder(inp)
    interval = _backoff(interval, inp.consecutive_errors)
    interval = _jitter(interval, inp.series_key, tier)
    interval = max(interval, inp.source_min_interval, MIN_INTERVAL)
    interval = min(interval, MAX_INTERVAL)
    return PollDecision(interval=interval, tier=tier, due_at=inp.now + interval, reason=reason)
