"""Entry point. ``mangame`` or ``python -m mangame``."""

import logging
import sys
from typing import TextIO

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from mangame import __version__, diagnostics
from mangame.domain.models import IconState
from mangame.store import env
from mangame.store.config import load
from mangame.store.db import Database
from mangame.store.paths import EMBLEM_VAR, HOME_VAR
from mangame.ui import emblems
from mangame.ui.tray import MangameTray

LOG = logging.getLogger(__name__)

SMOKE_FLAG = "--smoke-test"

USAGE = f"""\
mangame {__version__} — a manga release radar that lives in the system tray.

usage: mangame [--version] [--help]

There are no other options: everything is configured from the tray menu, which
either mouse button opens. Settings are stored as JSON and may be hand-edited.

environment:
  {HOME_VAR}
      Keep settings, database, logs and artwork in this directory instead of the
      platform's usual location. Useful for a portable copy, or a second
      instance that leaves the first alone.

  {EMBLEM_VAR}
      Keep imported artwork in this directory, wherever the rest lives.

  {env.ENV_FILE_VAR}
      Read these variables from this file. Otherwise the first '{env.FILENAME}'
      found in the working directory, beside the executable, or in the
      configuration directory is used.

https://github.com/frodo4fingers/mangame
"""


def _write(stream: TextIO | None, text: str) -> None:
    """Windowed Windows builds deliberately have no stdout or stderr."""
    if stream is not None:
        stream.write(text)


def _application() -> QApplication:
    existing = QApplication.instance()
    return existing if isinstance(existing, QApplication) else QApplication(sys.argv)


def _prepare_application(app: QApplication) -> None:
    app.setApplicationName("mangame")
    app.setApplicationDisplayName("mangame")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("mangame")

    # Without this the process exits the moment a transient dialog closes,
    # because a tray-only app never owns a window.
    app.setQuitOnLastWindowClosed(False)


def _smoke_test(app: QApplication) -> int:
    """Exercise the packaged runtime without opening a tray or using a stream."""
    load()
    with Database():
        pass
    icon = emblems.icon_for("mangame", IconState.READY, "mangame")
    if icon.isNull():
        LOG.error("smoke test could not load the bundled app icon")
        return 1
    LOG.info("smoke test passed for mangame %s", app.applicationVersion())
    return 0


def main() -> int:
    if "--version" in sys.argv or "-V" in sys.argv:
        # Frozen builds have no package metadata to interrogate, so the
        # question has to be answerable from the app itself.
        _write(sys.stdout, f"mangame {__version__}\n")
        return 0

    if "--help" in sys.argv or "-h" in sys.argv:
        _write(sys.stdout, USAGE)
        return 0

    # Before anything resolves a path, or the app would read one directory and
    # then be told to use another.
    env_file = env.load()
    log_file = diagnostics.configure_logging()

    if env_file:
        logging.getLogger("mangame").info("read environment from %s", env_file)
    LOG.info("logging to %s", log_file)

    app = _application()
    _prepare_application(app)

    if SMOKE_FLAG in sys.argv:
        return _smoke_test(app)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        LOG.error(
            "mangame: no system tray found.\n"
            "On GNOME install the 'AppIndicator and KStatusNotifierItem' "
            "extension; KDE, XFCE, Windows and macOS work out of the box."
        )
        return 1

    tray = MangameTray(app)
    tray.start()
    app.aboutToQuit.connect(tray.shutdown)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
