"""Shared fixtures. Every test works off explicit clocks — no ``utcnow`` anywhere."""

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mangame.domain.models import Chapter
from mangame.store import paths
from mangame.ui import emblems

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

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


@pytest.fixture(scope="session")
def qapp() -> Iterator["QApplication"]:
    """A real Qt application on the offscreen platform.

    Widgets need one to exist, but nothing here needs a display, so the tests
    that drive the dialogs run the same way in CI as they do on a desktop.
    Session-scoped because Qt allows exactly one application per process.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app


@pytest.fixture
def emblem_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point imported artwork at a throwaway directory.

    ``platformdirs`` honours the XDG variables, so redirecting the data home
    is enough to keep a test from writing into the developer's own emblems.
    """
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    emblems.forget_artwork()
    yield paths.user_emblem_dir()
    emblems.forget_artwork()
