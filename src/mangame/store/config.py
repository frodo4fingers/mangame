"""User settings.

Stored as JSON rather than TOML on purpose: reading *and* writing JSON is in
the standard library and round-trips Pydantic models exactly, so there is no
hand-rolled serialiser to get subtly wrong. The file stays perfectly readable
and hand-editable either way.
"""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, ValidationError

from mangame.i18n import languages
from mangame.store import paths

ReadingLanguage = Annotated[str, AfterValidator(languages.normalize)]
"""A language code folded onto one mangame can actually read in.

Applied at the settings boundary so every layer below — sources, store,
snapshots — only ever sees a canonical code. A hand-edited ``"pt-BR"`` or a
language dropped from a later release therefore degrades to something the
sources can serve instead of silently matching no chapters at all.
"""


def series_key(title: str) -> str:
    """The identity a tracked series is stored under.

    Lives with the model that owns ``key`` rather than in the tray, because
    "do we already track this?" has to be asked the same way in both the add
    dialog and the code that writes the entry — otherwise Add looks available
    and then quietly does nothing.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "series"


class SeriesConfig(BaseModel):
    """One tracked series, as the user configured it."""

    key: str
    title: str
    emblem: str = "monogram"
    language: ReadingLanguage | None = None
    """Overrides the global reading language for this series only."""

    show_in_tray: bool = True
    enabled: bool = True
    sources: dict[str, str] = Field(default_factory=dict)
    """``{source_id: reference}``; several sources may back one series."""


class Settings(BaseModel):
    """Everything the tiny menu can change, plus a few file-only escape hatches."""

    language: ReadingLanguage = languages.DEFAULT
    """The language you read manga in.

    This decides which sources are polled and which chapters count as "ready",
    so it is a content setting rather than a cosmetic one. The menu is shown in
    the same language, which is what keeps it to a single entry.
    """

    autostart: bool = False
    notifications: bool = True
    single_tray_icon: bool = False
    """Collapse every series into one aggregate icon instead of one each."""

    tray_emblem: str = "mangame"
    """Which emblem the aggregate icon wears.

    Only consulted in single-icon mode: with one icon per manga, each series
    already names its own. It defaults to the app's own mark rather than to a
    series' artwork, because an icon that speaks for the whole library should
    not look like one of the things in it.
    """

    max_tray_icons: int = 8
    series: list[SeriesConfig] = Field(default_factory=list)

    def tray_series(self) -> list[SeriesConfig]:
        visible = [s for s in self.series if s.enabled and s.show_in_tray]
        return visible[: self.max_tray_icons]

    def language_for(self, series: SeriesConfig) -> str:
        return series.language or self.language

    def with_series_change(self, key: str, **changes: object) -> "Settings":
        """A copy in which one tracked series has been edited in place.

        Order is preserved, because the series list is also the tray order.
        """
        series = [s.model_copy(update=changes) if s.key == key else s for s in self.series]
        return self.model_copy(update={"series": series})

    def without_series(self, key: str) -> "Settings":
        """A copy with one series dropped."""
        return self.model_copy(update={"series": [s for s in self.series if s.key != key]})


#: The series mangame ships already following.
#:
#: An empty tracker is a chicken-and-egg problem: the icon has nothing to say,
#: the three states cannot be told apart, and the first thing a new user sees
#: is an empty list asking them to know what to type. So the first run comes up
#: following the series this app ships artwork for.
#:
#: It is a starting point, not a fixture. Dropping it is saved like any other
#: change and it does not come back; everything else is found through search.
DEFAULT_SERIES_TITLE = "One Piece"


def default_series() -> list[SeriesConfig]:
    """The library a brand-new installation starts with.

    Built fresh on every call because a mutable default shared between two
    ``Settings`` objects would let one library edit the other.

    Sources are listed for every reading language and filtered later by what
    each one can actually serve, so a Spanish reader gets the same entry with
    the German scanlation simply never asked.
    """
    return [
        SeriesConfig(
            key=series_key(DEFAULT_SERIES_TITLE),
            title=DEFAULT_SERIES_TITLE,
            emblem="onepiece",
            sources={
                "mangadex": "a1c7c817-4e59-43b7-9365-09675a149a6f",
                "anilist": "30013",
                "onepiecetube": "https://onepiece.tube/manga/kapitel-mangaliste",
            },
        )
    ]


def load(path: Path | None = None) -> Settings:
    """Read settings, falling back to a first-run library.

    A missing file and an unreadable one are the same situation: there is no
    usable record of what the user follows. Both start from the default
    library rather than from an empty one, so the tray always has something to
    draw and a broken file never presents itself as "you track nothing".
    """
    target = path or paths.config_file()
    if not target.exists():
        return Settings(series=default_series())
    try:
        return Settings.model_validate_json(target.read_text(encoding="utf-8"))
    except (ValidationError, json.JSONDecodeError, OSError):
        # A corrupted config must never stop the tray from coming up.
        return Settings(series=default_series())


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
