"""User settings.

Stored as JSON rather than TOML on purpose: reading *and* writing JSON is in
the standard library and round-trips Pydantic models exactly, so there is no
hand-rolled serialiser to get subtly wrong. The file stays perfectly readable
and hand-editable either way.
"""

import json
import os
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from mangame.store import paths


class SeriesConfig(BaseModel):
    """One tracked series, as the user configured it."""

    key: str
    title: str
    emblem: str = "book"
    language: str | None = None
    """Preferred chapter language; ``None`` inherits :attr:`Settings.language`."""

    show_in_tray: bool = True
    enabled: bool = True
    sources: dict[str, str] = Field(default_factory=dict)
    """``{source_id: reference}``; several sources may back one series."""


class Settings(BaseModel):
    """Everything the tiny menu can change, plus a few file-only escape hatches."""

    language: str = "en"
    """UI language, and the default chapter language."""

    autostart: bool = False
    notifications: bool = True
    single_tray_icon: bool = False
    """Collapse every series into one aggregate icon instead of one each."""

    max_tray_icons: int = 8
    series: list[SeriesConfig] = Field(default_factory=list)

    def tray_series(self) -> list[SeriesConfig]:
        visible = [s for s in self.series if s.enabled and s.show_in_tray]
        return visible[: self.max_tray_icons]

    def language_for(self, series: SeriesConfig) -> str:
        return series.language or self.language


def load(path: Path | None = None) -> Settings:
    """Read settings, falling back to defaults on a missing or broken file."""
    target = path or paths.config_file()
    if not target.exists():
        return Settings()
    try:
        return Settings.model_validate_json(target.read_text(encoding="utf-8"))
    except (ValidationError, json.JSONDecodeError, OSError):
        # A corrupted config must never stop the tray from coming up.
        return Settings()


def save(settings: Settings, path: Path | None = None) -> None:
    """Write settings atomically so a crash cannot truncate the file."""
    target = path or paths.config_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = settings.model_dump_json(indent=2)

    handle, temp_name = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
