"""Where mangame keeps its things, per platform."""

import os
from pathlib import Path

from platformdirs import PlatformDirs

_DIRS = PlatformDirs(appname="mangame", appauthor=False, roaming=True)

APP_ID = "mangame"

HOME_VAR = "MANGAME_HOME"


def home_override() -> Path | None:
    """One directory holding everything, when ``MANGAME_HOME`` names one.

    Two uses. A portable install keeps its settings, database and artwork
    beside the executable instead of in the user profile. And the test suite
    needs isolation that behaves the same everywhere: ``platformdirs`` reads
    the XDG variables on Linux and macOS but not on Windows, where redirecting
    them would silently write into the real profile instead.
    """
    named = os.environ.get(HOME_VAR)
    return Path(named).expanduser() if named else None


def config_dir() -> Path:
    path = home_override() or Path(_DIRS.user_config_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    path = home_override() or Path(_DIRS.user_data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_file() -> Path:
    return config_dir() / "config.json"


def database_file() -> Path:
    return data_dir() / "state.sqlite3"


def user_emblem_dir() -> Path:
    """Drop-in folder so users can add their own emblems without a rebuild."""
    path = data_dir() / "emblems"
    path.mkdir(parents=True, exist_ok=True)
    return path
