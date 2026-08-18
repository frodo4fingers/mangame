"""Domain vocabulary for mangame.

Everything in :mod:`mangame.domain` is pure: no I/O, no network, no clock
reads that are not passed in explicitly. That keeps the interesting logic
(cadence estimation, break detection, icon state, adaptive polling) fully
unit-testable and makes the tray layer a thin shell.
"""

from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IconState(StrEnum):
    """The three visual states the tray emblem can take.

    Exactly three, by design — the icon is a glanceable signal, not a report.
    Richer nuance lives in :class:`SeriesPhase` and the tooltip.
    """

    READY = "ready"
    """Full colour: an unread chapter is available right now."""

    DUE = "due"
    """Greyscale: we are waiting for the next chapter."""

    BREAK = "break"
    """Black silhouette: a break has been *announced* for the current slot."""


class SeriesPhase(StrEnum):
    """Internal, finer-grained lifecycle used for tooltips and poll pacing."""

    UNREAD = "unread"
    WAITING = "waiting"
    """Inside the normal wait, next chapter is not expected yet."""

    IMMINENT = "imminent"
    """Expected release is within the hot window."""

    OVERDUE = "overdue"
    """Past the expected slot with nothing published and no announcement."""

    ANNOUNCED_BREAK = "announced_break"
    SUSPECTED_BREAK = "suspected_break"
    """Overdue for long enough that a break is likely, but nobody said so."""

    ENDED = "ended"
    """Completed or cancelled series."""

    UNKNOWN = "unknown"


class PublicationStatus(StrEnum):
    """Normalised publication status across all sources."""

    ONGOING = "ongoing"
    HIATUS = "hiatus"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class Confidence(StrEnum):
    """How much we trust a derived signal."""

    HIGH = "high"
    """Stated outright by an authoritative source (publisher next-date, hiatus flag)."""

    MEDIUM = "medium"
    """Derived from a reliable secondary signal (magazine calendar)."""

    LOW = "low"
    """Inferred purely from silence."""


class Chapter(BaseModel):
    """One published chapter, normalised across sources."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    external_id: str
    number: str | None = None
    volume: str | None = None
    title: str | None = None
    language: str = "en"
    published_at: datetime
    url: str | None = None

    @property
    def sort_key(self) -> tuple[float, datetime]:
        """Numeric chapter order when parseable, falling back to publish time."""
        try:
            numeric = float(self.number) if self.number is not None else float("-inf")
        except ValueError:
            numeric = float("-inf")
        return (numeric, self.published_at)


class Release(BaseModel):
    """One distinct release moment, after batching and backfill filtering."""

    model_config = ConfigDict(frozen=True)

    at: datetime
    number: float | None = None
    """Highest chapter number in the batch, when the source numbers chapters."""


class BreakWindow(BaseModel):
    """A period during which no chapter is expected."""

    model_config = ConfigDict(frozen=True)

    starts_at: datetime
    ends_at: datetime | None = None
    """``None`` means open-ended (e.g. an indefinite hiatus flag)."""

    reason: str = ""
    source_id: str = ""
    confidence: Confidence = Confidence.MEDIUM

    def covers(self, moment: datetime) -> bool:
        if moment < self.starts_at:
            return False
        return self.ends_at is None or moment < self.ends_at


class Cadence(BaseModel):
    """Learned release rhythm of a series.

    This is what lets mangame support a huge variety of sources cheaply: even a
    source that only lists publication timestamps yields a usable "next chapter
    is expected around X", with no per-series configuration.
    """

    model_config = ConfigDict(frozen=True)

    period: timedelta | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    """0 = Monday. Only meaningful for weekly/biweekly rhythms."""

    hour: int | None = Field(default=None, ge=0, le=23)
    """Typical publish hour in UTC."""

    sample_size: int = 0
    jitter: timedelta = timedelta(0)
    """Median absolute deviation of the observed intervals."""

    @property
    def is_known(self) -> bool:
        return self.period is not None and self.sample_size >= 2

    @property
    def score(self) -> float:
        """0.0-1.0 trust in this cadence, from sample size and regularity."""
        if not self.is_known or self.period is None:
            return 0.0
        sample_term = min(self.sample_size, 8) / 8.0
        regularity = 1.0 - min(
            self.jitter.total_seconds() / max(self.period.total_seconds(), 1.0), 1.0
        )
        return round(sample_term * 0.4 + regularity * 0.6, 3)


class SourceSignal(BaseModel):
    """What a single source reports about a single series at one point in time.

    Adapters produce this and nothing else, which is why adding a source never
    touches the scheduling or icon logic.
    """

    source_id: str
    fetched_at: datetime
    chapters: list[Chapter] = Field(default_factory=list)
    status: PublicationStatus = PublicationStatus.UNKNOWN
    announced_next_at: datetime | None = None
    """Publisher-stated date of the next chapter. The single best break signal."""

    breaks: list[BreakWindow] = Field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    watermark: str | None = None
    """Opaque cheap change token (e.g. MangaDex ``latestUploadedChapter``).

    Compared against the stored value to skip an expensive fetch entirely.
    """

    unchanged: bool = False
    """True when the source confirmed nothing moved; ``chapters`` is then empty
    on purpose and the caller must keep whatever it already had."""


class TrackedSeries(BaseModel):
    """A series the user follows, plus everything mangame has learned about it."""

    key: str
    """Stable local identifier, e.g. ``one-piece``."""

    title: str
    emblem: str = "monogram"
    language: str = "en"
    enabled: bool = True
    show_in_tray: bool = True

    source_refs: dict[str, str] = Field(default_factory=dict)
    """``{source_id: id-within-that-source}``. Multiple sources per series."""

    status: PublicationStatus = PublicationStatus.UNKNOWN
    cadence: Cadence = Field(default_factory=Cadence)
    latest_chapter: Chapter | None = None
    last_read_at: datetime | None = None
    last_read_external_id: str | None = None
    announced_next_at: datetime | None = None
    breaks: list[BreakWindow] = Field(default_factory=list)

    @field_validator("key")
    @classmethod
    def _key_is_slug(cls, value: str) -> str:
        if not value or any(c.isspace() for c in value):
            raise ValueError("series key must be a non-empty slug without whitespace")
        return value.lower()

    @property
    def has_unread(self) -> bool:
        if self.latest_chapter is None:
            return False
        if self.last_read_external_id == self.latest_chapter.external_id:
            return False
        if self.last_read_at is None:
            return True
        return self.latest_chapter.published_at > self.last_read_at


class SeriesSnapshot(BaseModel):
    """Fully resolved view of one series at a given instant."""

    model_config = ConfigDict(frozen=True)

    key: str
    title: str
    emblem: str
    icon_state: IconState
    phase: SeriesPhase
    expected_next_at: datetime | None
    active_break: BreakWindow | None
    latest_chapter: Chapter | None
    tooltip: str
