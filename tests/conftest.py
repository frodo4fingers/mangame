"""Shared fixtures. Every test works off explicit clocks — no ``utcnow`` anywhere."""

from datetime import UTC, datetime, timedelta

import pytest

from mangame.domain.models import Chapter

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def chapter(
    number: str | None,
    published_at: datetime,
    *,
    source_id: str = "test",
    external_id: str | None = None,
) -> Chapter:
    return Chapter(
        source_id=source_id,
        external_id=external_id or f"{source_id}-{number}-{published_at.isoformat()}",
        number=number,
        published_at=published_at,
    )


def weekly(count: int, *, start: datetime, step: timedelta = timedelta(days=7)) -> list[Chapter]:
    """``count`` chapters numbered 1..count, one every ``step``."""
    return [chapter(str(i + 1), start + step * i) for i in range(count)]


@pytest.fixture
def now() -> datetime:
    return NOW
