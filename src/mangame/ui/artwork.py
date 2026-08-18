"""Turning one picture into a three-state emblem set.

The tray says three things with one shape: full colour means ready, grey means
the week is due, near-black means a break was announced. Bundled emblems get
that for free — they are drawn three times from three palettes. Anything a user
brings is a single picture, so the other two states have to be derived.

Two transforms do it:

**Greyscale** takes each pixel's luminance and squeezes the result into a mid
band. Plain luminance would be honest and useless: artwork that is mostly dark
comes out nearly black, which is exactly what the *break* state looks like, and
the entire point is that the three states are told apart at 16 pixels.

**Silhouette** flattens everything opaque to one tone and rings it in the
opposite one. A dark silhouette vanishes on a dark panel and a light one
vanishes on a light panel, so whichever is chosen, the rim is what keeps the
icon visible on the other. The rim is grown outwards from the alpha channel,
and the artwork is inset by exactly that much so the halo is never clipped.

Every operation is a Qt composition on :class:`QImage`, which — unlike
``QPixmap`` — needs no display, no ``QApplication`` and no window system. That
is what keeps this fast enough for a live preview and testable headlessly.
"""

import math
from enum import StrEnum
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from mangame.domain.models import IconState
from mangame.store import paths
from mangame.ui.emblems import SIZES, forget_artwork

#: Extensions a user may hand us. SVG is rendered at each target size rather
#: than scaled up from one bitmap, so small tray sizes stay crisp.
VECTOR_SUFFIXES = frozenset({".svg", ".svgz"})
RASTER_SUFFIXES = frozenset({".png", ".webp", ".jpg", ".jpeg", ".bmp", ".gif"})
SUPPORTED_SUFFIXES = VECTOR_SUFFIXES | RASTER_SUFFIXES

#: Where black and white land in the grey state. Pulling the range off both
#: ends is what keeps "grey" distinguishable from "near-black" at 16px.
GREY_FLOOR = 0.34
GREY_CEILING = 0.86


class SilhouetteTone(StrEnum):
    """Which way round a silhouette is drawn."""

    DARK = "dark"
    """Near-black shape, light rim. Reads best on a light panel."""

    LIGHT = "light"
    """Near-white shape, dark rim. Reads best on a dark panel."""


#: Fill and rim per tone, matching the palettes ``tools/gen_icons.py`` uses for
#: the bundled artwork.
TONES: dict[SilhouetteTone, tuple[str, str]] = {
    SilhouetteTone.DARK: ("#232323", "#D2D2D2"),
    SilhouetteTone.LIGHT: ("#EDEDED", "#2B2B2B"),
}


class UnsupportedArtworkError(Exception):
    """The file is not an image mangame can read."""


def rim_width(size: int) -> int:
    """How thick the silhouette rim is at a given icon size.

    One pixel at tray sizes, growing with the icon so the halo stays visible
    rather than disappearing into a 256px render.
    """
    return max(1, round(size / 32))


def load(source: Path, size: int) -> QImage:
    """Render ``source`` into a square ``size`` image with alpha.

    Vectors are rendered at the requested size; rasters are scaled smoothly.
    Either way the picture keeps its proportions and is centred, so a wide
    cover crop does not get squashed into the tray.
    """
    suffix = source.suffix.lower()
    if suffix in VECTOR_SUFFIXES:
        return _render_vector(source, size)
    if suffix in RASTER_SUFFIXES:
        return _render_raster(source, size)
    raise UnsupportedArtworkError(f"{source.name}: expected one of {sorted(SUPPORTED_SUFFIXES)}")


def _blank(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    return image


def _render_vector(source: Path, size: int) -> QImage:
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise UnsupportedArtworkError(f"{source.name}: not a readable SVG")

    native = renderer.defaultSize()
    image = _blank(size)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, _fitted(native.width(), native.height(), size))
    painter.end()
    return image


def _render_raster(source: Path, size: int) -> QImage:
    loaded = QImage(str(source))
    if loaded.isNull():
        raise UnsupportedArtworkError(f"{source.name}: not a readable image")

    scaled = loaded.convertToFormat(QImage.Format.Format_ARGB32).scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    image = _blank(size)
    painter = QPainter(image)
    painter.drawImage((size - scaled.width()) // 2, (size - scaled.height()) // 2, scaled)
    painter.end()
    return image


def _fitted(width: int, height: int, size: int) -> QRectF:
    """Centre a ``width`` by ``height`` box inside a ``size`` square."""
    if width <= 0 or height <= 0:
        return QRectF(0, 0, size, size)
    scale = min(size / width, size / height)
    drawn_width, drawn_height = width * scale, height * scale
    return QRectF((size - drawn_width) / 2, (size - drawn_height) / 2, drawn_width, drawn_height)


def grayscale(image: QImage) -> QImage:
    """Desaturate into the mid band, keeping the original alpha.

    Qt's ``Grayscale8`` conversion is a gamma-correct Rec. 709 luminance — it
    linearises, weights, then re-encodes — which is why we lean on it instead
    of weighting sRGB bytes ourselves. It drops alpha, so the alpha is masked
    back on afterwards.
    """
    source = image.convertToFormat(QImage.Format.Format_ARGB32)
    grey = source.convertToFormat(QImage.Format.Format_Grayscale8)

    floor = round(GREY_FLOOR * 255)
    span = GREY_CEILING - GREY_FLOOR
    table = bytes(min(255, floor + round(level * span)) for level in range(256))
    remapped = QImage(
        bytes(grey.constBits()).translate(table),
        grey.width(),
        grey.height(),
        grey.bytesPerLine(),
        QImage.Format.Format_Grayscale8,
    ).convertToFormat(QImage.Format.Format_ARGB32)

    painter = QPainter(remapped)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, source)
    painter.end()
    return remapped


def silhouette(image: QImage, tone: SilhouetteTone = SilhouetteTone.DARK) -> QImage:
    """Flatten to one tone and ring the shape in the opposite one."""
    fill, rim = TONES[tone]
    source = image.convertToFormat(QImage.Format.Format_ARGB32)

    result = _ring(source, QColor(rim), rim_width(max(source.width(), source.height())))
    painter = QPainter(result)
    painter.drawImage(0, 0, _tinted(source, QColor(fill)))
    painter.end()
    return result


def _tinted(image: QImage, colour: QColor) -> QImage:
    """The image's shape, painted flat in one colour, alpha intact."""
    result = image.copy()
    painter = QPainter(result)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(result.rect(), colour)
    painter.end()
    return result


def _ring(source: QImage, colour: QColor, width: int) -> QImage:
    """A halo of ``width`` pixels hugging the outside of the shape.

    Dilating the alpha by stamping the mask across a disc of offsets, then
    punching the original shape back out, leaves only the grown edge. Doing
    that with draw calls instead of a pixel loop keeps a 256px render instant.
    """
    stamp = _tinted(source, colour)
    result = QImage(source.size(), QImage.Format.Format_ARGB32)
    result.fill(Qt.GlobalColor.transparent)

    painter = QPainter(result)
    for offset_x in range(-width, width + 1):
        for offset_y in range(-width, width + 1):
            if math.hypot(offset_x, offset_y) <= width:
                painter.drawImage(offset_x, offset_y, stamp)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
    painter.drawImage(0, 0, source)
    painter.end()
    return result


def _inset(image: QImage, margin: int) -> QImage:
    """Shrink the drawing inside its canvas to leave room for a rim."""
    size = image.width()
    inner = size - 2 * margin
    if inner <= 0:
        return image
    scaled = image.scaled(
        inner,
        inner,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    result = QImage(image.size(), QImage.Format.Format_ARGB32)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.drawImage(margin, margin, scaled)
    painter.end()
    return result


def state_image(
    source: Path,
    state: IconState,
    size: int,
    tone: SilhouetteTone = SilhouetteTone.DARK,
) -> QImage:
    """The imported artwork as it should look in one icon state."""
    if state is IconState.READY:
        return load(source, size)
    if state is IconState.DUE:
        return grayscale(load(source, size))
    # The rim grows outwards, so the art is inset by exactly the ring it needs.
    return silhouette(_inset(load(source, size), rim_width(size)), tone)


def emblem_name(raw: str) -> str:
    """Fold a user-typed name into something usable as a directory name."""
    cleaned = "".join(char if char.isalnum() else "-" for char in raw.strip().lower())
    return "-".join(part for part in cleaned.split("-") if part)


def install(source: Path, name: str, tone: SilhouetteTone = SilhouetteTone.DARK) -> str:
    """Write ``source`` into the user emblem directory as a full state set.

    Returns the folded name the emblem was stored under, which is what a series
    config then refers to. User artwork shadows bundled artwork of the same
    name, so importing "onepiece" replaces the shipped hat.
    """
    folder = emblem_name(name)
    if not folder:
        raise UnsupportedArtworkError("an emblem needs a name")

    root = paths.user_emblem_dir() / folder
    for state in IconState:
        out_dir = root / state.value
        out_dir.mkdir(parents=True, exist_ok=True)
        for size in SIZES:
            state_image(source, state, size, tone).save(str(out_dir / f"{size}.png"))
    forget_artwork()
    return folder


def uninstall(name: str) -> bool:
    """Remove a user-installed emblem. Bundled artwork is never touched."""
    root = paths.user_emblem_dir() / emblem_name(name)
    if not root.is_dir():
        return False
    for child in sorted(root.rglob("*"), reverse=True):
        child.rmdir() if child.is_dir() else child.unlink()
    root.rmdir()
    forget_artwork()
    return True


def user_emblems() -> list[str]:
    """Emblem names the user installed, as opposed to the bundled ones."""
    root = paths.user_emblem_dir()
    if not root.is_dir():
        return []
    return sorted(child.name for child in root.iterdir() if child.is_dir())
