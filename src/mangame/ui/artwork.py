"""Turning one picture into a three-state emblem set.

The tray says three things with one shape: full colour means ready, grey means
the week is due, near-black means a break was announced. Every emblem begins as
one picture, and the other two states are derived.

Two transforms do it:

**Greyscale** takes each pixel's luminance and squeezes the result into a mid
band. Plain luminance would be honest and useless: artwork that is mostly dark
comes out nearly black, which is exactly what the *break* state looks like, and
the entire point is that the three states are told apart at 16 pixels.

**Silhouette** flattens everything opaque to near-black and rings it in
near-white. The rim is what keeps the icon visible on a dark panel. It is grown
outwards from the alpha channel, and the artwork is inset by exactly that much
so the halo is never clipped.

Every operation is a Qt composition on :class:`QImage`, which — unlike
``QPixmap`` — needs no display, no ``QApplication`` and no window system. That
is what keeps this fast enough for a live preview and testable headlessly.
"""

import json
import logging
import math
import shutil
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from mangame.domain.models import IconState
from mangame.store import paths
from mangame.ui.emblems import emblem_name as emblem_name
from mangame.ui.emblems import forget_artwork

LOG = logging.getLogger(__name__)

#: Extensions accepted by the Settings file picker. Every import is normalised
#: to the source PNG from which the three stored states are generated.
VECTOR_SUFFIXES = frozenset({".svg", ".svgz"})
RASTER_SUFFIXES = frozenset({".png", ".webp", ".jpg", ".jpeg", ".bmp", ".gif"})
SUPPORTED_SUFFIXES = VECTOR_SUFFIXES | RASTER_SUFFIXES

#: Where black and white land in the grey state. Pulling the range off both
#: ends is what keeps "grey" distinguishable from "near-black" at 16px.
GREY_FLOOR = 0.34
GREY_CEILING = 0.86

#: One generated file per state is enough; QIcon scales it for the panel.
OUTPUT_SIZE = 256

#: User imports are normalised to one PNG, which remains the source of truth.
SOURCE_SIZE = 1024
DROPIN_VERSION = 1
MARKER = ".source.json"

BREAK_FILL = "#232323"
BREAK_RIM = "#D2D2D2"


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


def silhouette(image: QImage) -> QImage:
    """Flatten to near-black and ring the shape in near-white."""
    source = image.convertToFormat(QImage.Format.Format_ARGB32)

    result = _ring(source, QColor(BREAK_RIM), rim_width(max(source.width(), source.height())))
    painter = QPainter(result)
    painter.drawImage(0, 0, _tinted(source, QColor(BREAK_FILL)))
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
) -> QImage:
    """The imported artwork as it should look in one icon state."""
    if state is IconState.READY:
        return load(source, size)
    if state is IconState.DUE:
        return grayscale(load(source, size))
    # The rim grows outwards, so the art is inset by exactly the ring it needs.
    return silhouette(_inset(load(source, size), rim_width(size)))


def _signature(source: Path) -> dict[str, int | str]:
    stat = source.stat()
    return {
        "version": DROPIN_VERSION,
        "source": source.name,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _marker(output: Path) -> Path:
    return output / MARKER


def _is_current(source: Path, output: Path) -> bool:
    try:
        recorded = json.loads(_marker(output).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    expected = _signature(source)
    return recorded == expected and all(
        (output / f"{state.value}.png").is_file() for state in IconState
    )


def _generate(source: Path, name: str) -> None:
    """Replace one generated directory from its source PNG."""
    rendered = {state: state_image(source, state, OUTPUT_SIZE) for state in IconState}
    signature = _signature(source)
    output = paths.user_emblem_dir() / name
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    for state, image in rendered.items():
        target = output / f"{state.value}.png"
        if not image.save(str(target)):
            raise OSError(f"could not write {target}")
    _marker(output).write_text(
        json.dumps(signature, indent=2) + "\n",
        encoding="utf-8",
    )
    forget_artwork()


def sync_dropins() -> list[str]:
    """Generate root-level PNGs dropped into the user emblem directory.

    A file named ``Hunter x Hunter.png`` becomes the ``hunter-x-hunter``
    emblem. A small metadata marker skips rendering unchanged sources, so
    calling this from the tray's refresh timer is cheap.
    """
    root = paths.user_emblem_dir()
    grouped: dict[str, list[Path]] = {}
    for source in sorted(root.glob("*.png")):
        name = emblem_name(source.stem)
        if name:
            grouped.setdefault(name, []).append(source)

    generated: list[str] = []
    for name, candidates in grouped.items():
        if len(candidates) != 1:
            LOG.warning(
                "several dropped PNGs resolve to %s: %s",
                name,
                ", ".join(path.name for path in candidates),
            )
            continue
        source = candidates[0]
        output = root / name
        try:
            if _is_current(source, output):
                continue
            _generate(source, name)
        except (OSError, UnsupportedArtworkError) as exc:
            LOG.warning("could not generate emblem from %s: %s", source, exc)
            continue
        generated.append(name)
    return generated


def install(source: Path, name: str) -> str:
    """Store one source PNG and derive its three state images.

    Returns the folded name the emblem was stored under, which is what a series
    config then refers to. User artwork shadows bundled artwork of the same
    name, so importing "onepiece" replaces the shipped hat.
    """
    folder = emblem_name(name)
    if not folder:
        raise UnsupportedArtworkError("an emblem needs a name")

    root = paths.user_emblem_dir()
    stored = root / f"{folder}.png"
    if source.resolve() != stored.resolve():
        image = load(source, SOURCE_SIZE)
        if not image.save(str(stored)):
            raise OSError(f"could not write {stored}")
    _generate(stored, folder)
    return folder


def uninstall(name: str) -> bool:
    """Remove a user-installed emblem. Bundled artwork is never touched."""
    home = paths.user_emblem_dir()
    root = home / emblem_name(name)
    if not root.is_dir():
        return False
    source_name = f"{emblem_name(name)}.png"
    try:
        marker = json.loads(_marker(root).read_text(encoding="utf-8"))
        if isinstance(marker.get("source"), str):
            source_name = marker["source"]
    except (json.JSONDecodeError, OSError):
        pass
    shutil.rmtree(root)
    (home / source_name).unlink(missing_ok=True)
    forget_artwork()
    return True


def user_emblems() -> list[str]:
    """Emblem names the user installed, as opposed to the bundled ones."""
    sync_dropins()
    root = paths.user_emblem_dir()
    if not root.is_dir():
        return []
    return sorted(child.name for child in root.iterdir() if child.is_dir())
