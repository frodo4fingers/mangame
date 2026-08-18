"""Where mangame keeps its things, per platform."""

from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs

_DIRS = PlatformDirs(appname="mangame", appauthor=False, roaming=True)

APP_ID = "mangame"


def config_dir() -> Path:
    path = Path(_DIRS.user_config_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    path = Path(_DIRS.user_data_dir)
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
