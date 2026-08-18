"""Entry point. ``mangame`` or ``python -m mangame``."""

import logging
import sys

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from mangame import __version__
from mangame.store import env
from mangame.store.paths import EMBLEM_VAR, HOME_VAR
from mangame.ui.tray import MangameTray

USAGE = f"""\
mangame {__version__} — a manga release radar that lives in the system tray.

usage: mangame [--version] [--help]

There are no other options: everything is configured from the tray menu, which
either mouse button opens. Settings are stored as JSON and may be hand-edited.

environment:
  {HOME_VAR}
      Keep settings, database and artwork in this directory instead of the
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


def main() -> int:
    if "--version" in sys.argv or "-V" in sys.argv:
        # Frozen builds have no package metadata to interrogate, so the
        # question has to be answerable from the app itself.
        sys.stdout.write(f"mangame {__version__}\n")
        return 0

    if "--help" in sys.argv or "-h" in sys.argv:
        sys.stdout.write(USAGE)
        return 0

    # Before anything resolves a path, or the app would read one directory and
    # then be told to use another.
    env_file = env.load()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    )

    if env_file:
        logging.getLogger("mangame").info("read environment from %s", env_file)

    app = QApplication(sys.argv)
    app.setApplicationName("mangame")
    app.setApplicationDisplayName("mangame")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("mangame")

    # Without this the process exits the moment a transient dialog closes,
    # because a tray-only app never owns a window.
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        sys.stderr.write(
            "mangame: no system tray found.\n"
            "On GNOME install the 'AppIndicator and KStatusNotifierItem' "
            "extension; KDE, XFCE, Windows and macOS work out of the box.\n"
        )
        return 1

    tray = MangameTray(app)
    tray.start()
    app.aboutToQuit.connect(tray.shutdown)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
