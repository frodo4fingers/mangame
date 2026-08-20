"""Persistent logs and a copyable support report for the windowed app."""

import logging
import platform
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import qVersion

from mangame import __version__
from mangame.store import paths

LOG_BYTES = 1_000_000
LOG_BACKUPS = 3
LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure_logging() -> Path:
    """Log to disk because packaged GUI builds may have no standard streams."""
    target = paths.log_file()
    handlers: list[logging.Handler] = [
        RotatingFileHandler(
            target,
            maxBytes=LOG_BYTES,
            backupCount=LOG_BACKUPS,
            encoding="utf-8",
        )
    ]
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler(sys.stderr))

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=handlers,
        force=True,
    )
    return target


def report() -> str:
    """The facts a useful bug report needs, without library contents."""
    return "\n".join(
        (
            f"mangame {__version__}",
            f"Python {platform.python_version()}",
            f"Qt {qVersion()}",
            f"Platform {platform.platform()}",
            f"Settings: {paths.config_file()}",
            f"Database: {paths.database_file()}",
            f"Log: {paths.log_file()}",
        )
    )
