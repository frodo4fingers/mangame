"""Start on boot/login, on all three platforms.

Deliberately dependency-free: each platform's mechanism is a handful of
standard-library calls, and owning them outright avoids betting the feature on
a third-party package that may go unmaintained.

* **Linux** — an XDG autostart ``.desktop`` file in ``~/.config/autostart``.
* **Windows** — a value under ``HKCU\\...\\CurrentVersion\\Run`` (per-user, so
  it never needs administrator rights).
* **macOS** — a ``LaunchAgent`` plist in ``~/Library/LaunchAgents`` with
  ``RunAtLoad``.
"""

import contextlib
import os
import plistlib
import subprocess
import sys
from pathlib import Path

APP_NAME = "mangame"
APP_DISPLAY_NAME = "mangame"
MACOS_LABEL = "io.mangame.agent"


def launch_command() -> list[str]:
    """How to start mangame again later.

    A frozen build is its own executable; a source checkout has to go back
    through the interpreter that is running right now.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", APP_NAME]


def _quote(parts: list[str]) -> str:
    return " ".join(f'"{part}"' if " " in part else part for part in parts)


# ------------------------------------------------------------------ Linux (XDG)


def _linux_desktop_file() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "autostart" / f"{APP_NAME}.desktop"


def _linux_set(enabled: bool) -> bool:
    target = _linux_desktop_file()
    if not enabled:
        target.unlink(missing_ok=True)
        return True
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_DISPLAY_NAME}\n"
        "Comment=Manga release radar in the system tray\n"
        f"Exec={_quote(launch_command())}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )
    return True


def _linux_enabled() -> bool:
    return _linux_desktop_file().exists()


# --------------------------------------------------------------- Windows (Run)

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _windows_set(enabled: bool) -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _quote(launch_command()))
        else:
            with contextlib.suppress(FileNotFoundError):
                winreg.DeleteValue(key, APP_NAME)
    return True


def _windows_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
    except OSError:
        return False
    return True


# ------------------------------------------------------------ macOS (LaunchAgent)


def _macos_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{MACOS_LABEL}.plist"


def _macos_set(enabled: bool) -> bool:
    target = _macos_plist()
    if not enabled:
        if target.exists():
            subprocess.run(
                ["/bin/launchctl", "unload", str(target)],
                check=False,
                capture_output=True,
            )
            target.unlink(missing_ok=True)
        return True

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        plistlib.dump(
            {
                "Label": MACOS_LABEL,
                "ProgramArguments": launch_command(),
                "RunAtLoad": True,
                "KeepAlive": False,
                "ProcessType": "Interactive",
            },
            handle,
        )
    subprocess.run(["/bin/launchctl", "load", str(target)], check=False, capture_output=True)
    return True


def _macos_enabled() -> bool:
    return _macos_plist().exists()


# --------------------------------------------------------------------- public


def is_supported() -> bool:
    return sys.platform in ("linux", "win32", "darwin")


def is_enabled() -> bool:
    """Whether mangame is currently registered to start at login."""
    try:
        if sys.platform == "win32":
            return _windows_enabled()
        if sys.platform == "darwin":
            return _macos_enabled()
        return _linux_enabled()
    except OSError:
        return False


def set_enabled(enabled: bool) -> bool:
    """Register or unregister start-at-login. Returns success."""
    try:
        if sys.platform == "win32":
            return _windows_set(enabled)
        if sys.platform == "darwin":
            return _macos_set(enabled)
        return _linux_set(enabled)
    except OSError:
        return False
