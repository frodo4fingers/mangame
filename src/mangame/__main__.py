"""Entry point. ``mangame`` or ``python -m mangame``."""

import logging
import sys

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from mangame.ui.tray import MangameTray


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    )

    app = QApplication(sys.argv)
    app.setApplicationName("mangame")
    app.setApplicationDisplayName("mangame")
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
