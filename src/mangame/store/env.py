"""Reading a ``.env`` file, so a machine's own paths never reach the repository.

The published project has to be empty: no tracked series, no imported artwork,
nothing naming a person. Everything that differs between one machine and the
next is therefore expressed as an environment variable, and a ``.env`` file is
simply a convenient, git-ignored place to keep those variables.

The file only ever fills in blanks. A variable already present in the real
environment always wins, so a launcher, a systemd unit or a one-off
``MANGAME_HOME=/tmp/x mangame`` cannot be quietly overridden by a file left in
a directory the app happens to have been started from.
"""

import os
import re
import sys
from pathlib import Path

from mangame.store import paths

ENV_FILE_VAR = "MANGAME_ENV_FILE"

FILENAME = ".env"

PREFIX = "MANGAME_"
"""Only mangame's own variables are set.

A ``.env`` is a tempting place to park unrelated secrets, and this app has no
business exporting someone's database password into its process.
"""


def candidates() -> list[Path]:
    """Where a ``.env`` may live, best first.

    Four places, for four ways of running mangame. An explicit path wins for
    anyone scripting it. The working directory serves development from a
    clone. Beside the executable serves a portable install, where the whole
    point is that the stick carries its own configuration. The platform's own
    config directory serves the ordinary case: a tray app started at login has
    no meaningful working directory, so nothing else would ever be found.
    """
    named = os.environ.get(ENV_FILE_VAR)
    found = [Path(named).expanduser()] if named else []

    found.append(Path.cwd() / FILENAME)

    if getattr(sys, "frozen", False):
        found.append(Path(sys.executable).resolve().parent / FILENAME)

    # Deliberately the platform default rather than the configured directory,
    # which cannot be known until this file has been read.
    found.append(paths.default_config_dir() / FILENAME)

    return found


def parse(text: str) -> dict[str, str]:
    """The subset of ``.env`` syntax this project promises to understand.

    Deliberately small: comments, blank lines, an optional ``export``, and
    values that may be quoted to protect leading or trailing spaces. There is
    no interpolation and no multi-line value, because a path never needs one
    and every additional rule is another way for a file to mean something
    other than it appears to.
    """
    values: dict[str, str] = {}

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        name, _, value = stripped.partition("=")
        name = name.removeprefix("export ").strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            # A trailing note is a comment, not part of the path. Quote the
            # value if you genuinely have a '#' in a directory name.
            value = re.split(r"\s#", value, maxsplit=1)[0].rstrip()

        if name:
            values[name] = value

    return values


def read(path: Path) -> dict[str, str]:
    """The mangame variables in one file, or nothing if it is not there."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # An unreadable or binary .env must not stop the app from starting;
        # it only ever supplies optional overrides.
        return {}

    return {k: v for k, v in parse(text).items() if k.startswith(PREFIX)}


def load() -> Path | None:
    """Fill in unset mangame variables from the first ``.env`` that exists.

    Returns the file used, so startup can say where its configuration came
    from. Call it before anything resolves a path.
    """
    for path in candidates():
        if not path.is_file():
            continue

        for name, value in read(path).items():
            os.environ.setdefault(name, value)

        return path

    return None
