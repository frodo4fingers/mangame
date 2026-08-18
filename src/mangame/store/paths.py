"""Where mangame keeps its things, per platform."""

import os
from pathlib import Path

from platformdirs import PlatformDirs

_DIRS = PlatformDirs(appname="mangame", appauthor=False, roaming=True)

APP_ID = "mangame"

HOME_VAR = "MANGAME_HOME"

EMBLEM_VAR = "MANGAME_EMBLEM_DIR"


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


def default_config_dir() -> Path:
    """The platform's own location, ignoring any override.

    Needed to find a ``.env``, which is what decides where the override points
    in the first place. Creates nothing: this is a question, not a claim.
    """
    return Path(_DIRS.user_config_dir)


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
    """Drop-in folder so users can add their own emblems without a rebuild.

    ``MANGAME_EMBLEM_DIR`` moves it anywhere, independently of the rest.
    Artwork is the one thing worth keeping apart: it is bulky, it is the part
    a user is most likely to have collected by hand, and it survives a
    reinstall that throws the database away.
    """
    named = os.environ.get(EMBLEM_VAR)
    path = Path(named).expanduser() if named else data_dir() / "emblems"
    path.mkdir(parents=True, exist_ok=True)
    return path
