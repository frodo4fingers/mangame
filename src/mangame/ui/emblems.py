"""Emblem resolution: series + state -> a tray-ready :class:`QIcon`.

Two mechanisms, in order:

1. **Bundled or user-supplied artwork.** ``<emblems>/<name>/<state>/<size>.png``.
   The user directory is searched first, so anyone can drop in their own hat
   without rebuilding the app.
2. **Procedural monogram.** Any series without artwork gets a generated badge:
   the initial on a colour derived from the title. This means every series has
   a distinct, recognisable icon from the moment it is added, and it sidesteps
   reproducing anyone's character art or logo.

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

#: Sizes rasterised by ``tools/gen_icons.py``; a QIcon gets all of them so the
#: platform can pick the right one for the panel and DPI.
SIZES = (16, 18, 20, 22, 24, 32, 36, 44, 48, 64)

FALLBACK_EMBLEM = "book"

#: Per-state styling for the procedural monogram.
_MONOGRAM_STYLE: dict[IconState, tuple[float, float, str, str]] = {
    # (saturation, value, text colour, rim colour)
    IconState.READY: (0.72, 0.92, "#FFFFFF", "#00000055"),
    IconState.DUE: (0.0, 0.66, "#FFFFFF", "#00000055"),
    IconState.BREAK: (0.0, 0.14, "#8C8C8C", "#D2D2D2D9"),
}


def emblem_roots() -> tuple[Path, ...]:
    """User artwork wins over bundled artwork."""
    return (paths.user_emblem_dir(), BUNDLED_DIR)


def available_emblems() -> list[str]:
    names: set[str] = set()
    for root in emblem_roots():
        if root.is_dir():
            names.update(child.name for child in root.iterdir() if child.is_dir())
    return sorted(names)


def _find(emblem: str, state: IconState) -> Path | None:
    for root in emblem_roots():
        candidate = root / emblem / state.value
        if candidate.is_dir():
            return candidate
    return None


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
    answer only depends on the three arguments.
    """
    directory = _find(emblem, state) or _find(FALLBACK_EMBLEM, state)
    if directory is not None:
        icon = QIcon()
        for size in SIZES:
            candidate = directory / f"{size}.png"
            if candidate.exists():
                icon.addFile(str(candidate))
        if not icon.isNull():
            return icon

    icon = QIcon()
    for size in (16, 24, 32, 64):
        icon.addPixmap(monogram(title, state, size))
    return icon
