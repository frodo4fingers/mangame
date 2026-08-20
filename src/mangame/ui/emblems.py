"""Emblem resolution: series + state -> a tray-ready :class:`QIcon`.

Two mechanisms, in order:

1. **Bundled or user-supplied artwork.** ``<emblems>/<name>/<state>.png``.
   The user directory is searched first. A root-level ``<title>.png`` is
   transformed into that layout automatically; the old per-size layout
   remains readable for existing installations.
2. **Procedural monogram.** Any series without artwork gets a generated badge:
   the initial on a colour derived from the title. This means every series has
   a distinct, recognisable icon from the moment it is added, and it sidesteps
   reproducing anyone's character art or logo.

Missing artwork therefore falls back to the monogram and never to some other
series' picture: a generated badge still says *which* series it is, whereas a
shared stand-in would make every untouched series look identical.

The three states are visually separated so they survive both light and dark
panels: full colour, desaturated grey, and a near-black silhouette with a light
rim (which stays visible on a dark panel, where plain black would vanish).
"""

import hashlib
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap

from mangame.domain.models import IconState
from mangame.store import paths

BUNDLED_DIR = Path(__file__).resolve().parent.parent / "assets" / "emblems"

#: Not a directory but a request: draw the badge instead of loading a picture.
MONOGRAM_EMBLEM = "monogram"

#: Per-state styling for the procedural monogram.
_MONOGRAM_STYLE: dict[IconState, tuple[float, float, str, str]] = {
    # (saturation, value, text colour, rim colour)
    IconState.READY: (0.72, 0.92, "#FFFFFF", "#00000055"),
    IconState.DUE: (0.0, 0.66, "#FFFFFF", "#00000055"),
    IconState.BREAK: (0.0, 0.14, "#8C8C8C", "#D2D2D2D9"),
}


def emblem_name(raw: str) -> str:
    """Fold a title or user name into something usable as a directory name."""
    cleaned = "".join(char if char.isalnum() else "-" for char in raw.strip().lower())
    return "-".join(part for part in cleaned.split("-") if part)


def emblem_roots() -> tuple[Path, ...]:
    """User artwork wins over bundled artwork."""
    return (paths.user_emblem_dir(), BUNDLED_DIR)


def available_emblems() -> list[str]:
    """Artwork names on disk, user and bundled, without the monogram."""
    names: set[str] = set()
    for root in emblem_roots():
        if root.is_dir():
            names.update(child.name for child in root.iterdir() if child.is_dir())
    names.discard(MONOGRAM_EMBLEM)
    return sorted(names)


def selectable_emblems() -> list[str]:
    """What the settings dialog may offer, monogram first as the safe default."""
    return [MONOGRAM_EMBLEM, *available_emblems()]


def _find(emblem: str, state: IconState) -> Path | None:
    for root in emblem_roots():
        state_file = root / emblem / f"{state.value}.png"
        if state_file.is_file():
            return state_file
        legacy_directory = root / emblem / state.value
        if legacy_directory.is_dir():
            return legacy_directory
    return None


def _user_title_artwork(title: str, state: IconState) -> Path | None:
    """A dropped ``<title>.png`` intentionally overrides configured artwork."""
    name = emblem_name(title)
    state_file = paths.user_emblem_dir() / name / f"{state.value}.png"
    return state_file if state_file.is_file() else None


def _icon(path: Path) -> QIcon:
    if path.is_file():
        return QIcon(str(path))
    icon = QIcon()
    candidates = [candidate for candidate in path.glob("*.png") if candidate.stem.isdigit()]
    for candidate in sorted(candidates, key=lambda item: int(item.stem)):
        icon.addFile(str(candidate))
    return icon


def _hue_for(seed: str) -> int:
    digest = hashlib.blake2s(seed.encode("utf-8"), digest_size=2).digest()
    return int.from_bytes(digest, "big") % 360


def _initial(title: str) -> str:
    for char in title:
        if char.isalnum():
            return char.upper()
    return "?"


def monogram(title: str, state: IconState, size: int = 64) -> QPixmap:
    """Generate a badge icon for a series that has no artwork."""
    saturation, value, text_color, rim_color = _MONOGRAM_STYLE[state]
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    inset = size * 0.06
    body = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)
    radius = size * 0.24

    fill = QColor.fromHsvF(_hue_for(title) / 360.0, saturation, value)
    painter.setBrush(fill)
    painter.setPen(QPen(QColor(rim_color), max(1.0, size * 0.05)))
    painter.drawRoundedRect(body, radius, radius)

    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(size * 0.62))
    painter.setFont(font)
    painter.setPen(QColor(text_color))
    painter.drawText(body, Qt.AlignmentFlag.AlignCenter, _initial(title))
    painter.end()
    return pixmap


@lru_cache(maxsize=256)
def icon_for(emblem: str, state: IconState, title: str) -> QIcon:
    """The icon to show for one series in one state.

    Cached because the tray asks for these on every state change and the
    answer only depends on the three arguments. :func:`forget_artwork` drops
    the cache after artwork is imported or removed.
    """
    dropped = _user_title_artwork(title, state)
    if dropped is not None:
        icon = _icon(dropped)
        if not icon.isNull():
            return icon

    if emblem != MONOGRAM_EMBLEM:
        found = _find(emblem, state)
        if found is not None:
            icon = _icon(found)
            if not icon.isNull():
                return icon

    icon = QIcon()
    for size in (16, 24, 32, 64):
        icon.addPixmap(monogram(title, state, size))
    return icon


def forget_artwork() -> None:
    """Drop cached icons so newly imported artwork is picked up at once."""
    icon_for.cache_clear()
