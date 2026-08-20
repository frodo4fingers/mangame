"""Generate the mangame tray emblem asset set.

Produces, for every emblem and every :class:`IconState`, an SVG master plus
rasterised PNGs at all tray-relevant pixel sizes and a Windows ``.ico``.

All artwork here is original. Emblems are deliberately generic real-world
objects (a straw boater hat, a book) or procedurally generated monograms, so
no third-party character art or logo is ever reproduced.

Run with:  uv run python tools/gen_icons.py
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "src" / "mangame" / "assets" / "emblems"
REFERENCE = REPO_ROOT / "docs" / "icon-reference.png"
PIXEL_MANIFEST = REPO_ROOT / "docs" / "icon-pixels.json"

# Tray icons are tiny. 16-24px carries Windows/Linux panels, 36px covers a
# retina macOS menu bar, the large sizes are for the .ico and about dialogs.
PNG_SIZES = (16, 18, 20, 22, 24, 32, 36, 44, 48, 64, 128, 256)
ICO_SIZES = (16, 20, 24, 32, 48, 64, 256)

# The review sheet shows the sizes where visual regressions are easiest to
# miss, on the two panel tones used by the in-app artwork preview.
REFERENCE_SIZES = (16, 22, 32)
REFERENCE_LIGHT = "#F2F2F2"
REFERENCE_DARK = "#1B1B1B"
REFERENCE_PANEL_WIDTH = 48
REFERENCE_CELL_WIDTH = 2 * REFERENCE_PANEL_WIDTH
REFERENCE_GAP = 4
REFERENCE_PADDING = 6
REFERENCE_CELL_HEIGHT = (
    2 * REFERENCE_PADDING + sum(REFERENCE_SIZES) + REFERENCE_GAP * (len(REFERENCE_SIZES) - 1)
)


class Palette(BaseModel):
    """Colours for one icon state.

    ``line`` is the outline. It is deliberately chosen per state so that every
    icon stays legible on both light and dark panels: the near-black ``break``
    silhouette gets a *light* outline, the others get a dark one.
    """

    name: str
    base: str
    shade: str
    accent: str
    accent_shade: str
    line: str
    line_opacity: float = Field(default=1.0, ge=0.0, le=1.0)


PALETTES: tuple[Palette, ...] = (
    # Something is ready to read -> full colour, maximum salience.
    Palette(
        name="ready",
        base="#EFBB4F",
        shade="#C8912B",
        accent="#DC3B2C",
        accent_shade="#A82418",
        line="#42300F",
    ),
    # The week is due but nothing has dropped -> desaturated, still legible.
    Palette(
        name="due",
        base="#ADADAD",
        shade="#878787",
        accent="#969696",
        accent_shade="#6F6F6F",
        line="#3F3F3F",
    ),
    # A break was announced -> flat silhouette with a light rim so it survives
    # on a dark panel too.
    Palette(
        name="break",
        base="#232323",
        shade="#232323",
        accent="#232323",
        accent_shade="#232323",
        line="#D2D2D2",
        line_opacity=0.85,
    ),
)


SVG_HEADER = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'

# The "onepiece" emblem, drawn as a generic straw boater hat: wide brim ellipse
# + low domed crown + ribbon band. Emblems are named after the series they are
# hinted for, not after the shape.
_CROWN = "M14 45 C14 27 19 15 32 15 C45 15 50 27 50 45 Z"
_BRIM = (
    "M32 37 C47 37 58 40.5 58 45.5 C58 50.5 47 54 32 54 C17 54 6 50.5 6 45.5 C6 40.5 17 37 32 37 Z"
)


def _onepiece(p: Palette) -> str:
    return f"""{SVG_HEADER}
  <defs><clipPath id="crown"><path d="{_CROWN}"/></clipPath></defs>
  <g stroke="{p.line}" stroke-opacity="{p.line_opacity}" stroke-width="3"
     stroke-linejoin="round" stroke-linecap="round">
    <path d="{_CROWN}" fill="{p.base}"/>
    <g clip-path="url(#crown)" stroke="none">
      <rect x="10" y="30" width="44" height="11" fill="{p.accent}"/>
      <rect x="10" y="37" width="44" height="4" fill="{p.accent_shade}"/>
    </g>
    <path d="{_CROWN}" fill="none"/>
    <path d="{_BRIM}" fill="{p.base}"/>
    <path d="M10 47.5 C17 51.5 47 51.5 54 47.5" fill="none"
          stroke="{p.shade}" stroke-opacity="0.9" stroke-width="3"/>
  </g>
</svg>
"""


# Generic fallback: a stack-of-volumes / open book mark.
def _book(p: Palette) -> str:
    return f"""{SVG_HEADER}
  <g stroke="{p.line}" stroke-opacity="{p.line_opacity}" stroke-width="3"
     stroke-linejoin="round" stroke-linecap="round">
    <path d="M7 13 C16 9 26 9 32 14 L32 53 C26 48 16 48 7 52 Z" fill="{p.base}"/>
    <path d="M57 13 C48 9 38 9 32 14 L32 53 C38 48 48 48 57 52 Z" fill="{p.shade}"/>
    <path d="M32 14 L32 53" fill="none"/>
    <path d="M24 22 L24 44" fill="none" stroke="{p.accent}" stroke-width="4"/>
  </g>
</svg>
"""


# The app's own mark: a heavy M. It stands for the whole library rather than
# for any one series, which is why it is a letter and not an object -- the
# aggregate icon used to borrow the straw hat, and a library of thirty titles
# then looked like One Piece.
#
# Drawn as a single filled silhouette rather than a stroked letterform: at 16px
# a stroked M closes up into a blob, whereas a solid shape with an 8px-wide
# valley keeps its three strokes apart.
#
# The stems are deliberately fat. A letter has far less area per unit of
# outline than a hat or a book does, and in the break state -- a near-black
# body with a light rim -- a thin glyph turns into an outline drawing instead
# of a silhouette. Fat stems plus ``paint-order`` (below) keep the body dark.
_M = "M8 53 L8 11 L24 11 L32 30 L40 11 L56 11 L56 53 L41 53 L41 28 L36 39 L28 39 L23 28 L23 53 Z"


def _mangame(p: Palette) -> str:
    # paint-order="stroke fill" puts the outline *behind* the fill, so only its
    # outer half shows. On the hat and the book that would barely register; on
    # a letterform it is the difference between a dark mark with a rim and a
    # pale one with a dark hole.
    return f"""{SVG_HEADER}
  <defs><clipPath id="mark"><path d="{_M}"/></clipPath></defs>
  <g stroke="{p.line}" stroke-opacity="{p.line_opacity}" stroke-width="6"
     paint-order="stroke fill" stroke-linejoin="round" stroke-linecap="round">
    <path d="{_M}" fill="{p.base}"/>
    <g clip-path="url(#mark)" stroke="none">
      <rect x="32" y="8" width="26" height="48" fill="{p.shade}"/>
      <rect x="6" y="45" width="52" height="6" fill="{p.accent}"/>
      <rect x="6" y="49" width="52" height="4" fill="{p.accent_shade}"/>
    </g>
  </g>
</svg>
"""


EMBLEMS = {"onepiece": _onepiece, "book": _book, "mangame": _mangame}


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def reference_image() -> Image.Image:
    """The approved small-size view, on light and dark panels."""
    sheet = Image.new(
        "RGBA",
        (len(PALETTES) * REFERENCE_CELL_WIDTH, len(EMBLEMS) * REFERENCE_CELL_HEIGHT),
    )
    for row, emblem in enumerate(EMBLEMS):
        for column, palette in enumerate(PALETTES):
            left = column * REFERENCE_CELL_WIDTH
            top = row * REFERENCE_CELL_HEIGHT
            sheet.paste(
                REFERENCE_LIGHT,
                (left, top, left + REFERENCE_PANEL_WIDTH, top + REFERENCE_CELL_HEIGHT),
            )
            sheet.paste(
                REFERENCE_DARK,
                (
                    left + REFERENCE_PANEL_WIDTH,
                    top,
                    left + REFERENCE_CELL_WIDTH,
                    top + REFERENCE_CELL_HEIGHT,
                ),
            )

            icon_top = top + REFERENCE_PADDING
            for size in REFERENCE_SIZES:
                source = OUT_ROOT / emblem / palette.name / f"{size}.png"
                with Image.open(source) as opened:
                    icon = opened.convert("RGBA")
                light_x = left + (REFERENCE_PANEL_WIDTH - size) // 2
                dark_x = left + REFERENCE_PANEL_WIDTH + (REFERENCE_PANEL_WIDTH - size) // 2
                sheet.alpha_composite(icon, (light_x, icon_top))
                sheet.alpha_composite(icon, (dark_x, icon_top))
                icon_top += size + REFERENCE_GAP
    return sheet


def write_reference() -> None:
    REFERENCE.parent.mkdir(parents=True, exist_ok=True)
    reference_image().save(REFERENCE)
    PIXEL_MANIFEST.write_text(pixel_manifest_text(), encoding="utf-8")
    print(f"built {REFERENCE.relative_to(REPO_ROOT)}")
    print(f"built {PIXEL_MANIFEST.relative_to(REPO_ROOT)}")


def pixel_manifest_text() -> str:
    """Hashes of decoded pixels, so every shipped tray size is intentional."""
    manifest: dict[str, str] = {}
    for emblem in EMBLEMS:
        for palette in PALETTES:
            for size in PNG_SIZES:
                path = OUT_ROOT / emblem / palette.name / f"{size}.png"
                with Image.open(path) as opened:
                    image = opened.convert("RGBA")
                digest = hashlib.sha256()
                digest.update(f"{image.width}x{image.height}\0".encode())
                digest.update(image.tobytes())
                manifest[str(path.relative_to(OUT_ROOT))] = digest.hexdigest()
    return f"{json.dumps(manifest, indent=2, sort_keys=True)}\n"


def contract_problems() -> list[str]:
    """Anything that changed outside the approved generated-artwork contract."""
    problems: list[str] = []
    for emblem, render in EMBLEMS.items():
        for palette in PALETTES:
            directory = OUT_ROOT / emblem / palette.name
            svg = directory / f"{emblem}-{palette.name}.svg"
            if not svg.is_file():
                problems.append(f"missing {svg.relative_to(REPO_ROOT)}")
            elif svg.read_text(encoding="utf-8") != render(palette):
                problems.append(f"stale {svg.relative_to(REPO_ROOT)}")

            present = {int(path.stem) for path in directory.glob("*.png") if path.stem.isdigit()}
            if present != set(PNG_SIZES):
                problems.append(
                    f"{directory.relative_to(REPO_ROOT)} has PNG sizes {sorted(present)}, "
                    f"expected {list(PNG_SIZES)}"
                )

            for size in PNG_SIZES:
                path = directory / f"{size}.png"
                if not path.is_file():
                    continue
                try:
                    with Image.open(path) as image:
                        if image.size != (size, size):
                            problems.append(
                                f"{path.relative_to(REPO_ROOT)} is {image.size}, "
                                f"expected {(size, size)}"
                            )
                        image.verify()
                except OSError as exc:
                    problems.append(f"unreadable {path.relative_to(REPO_ROOT)}: {exc}")

            ico = directory / f"{emblem}-{palette.name}.ico"
            if not ico.is_file():
                problems.append(f"missing {ico.relative_to(REPO_ROOT)}")

    if not REFERENCE.is_file():
        problems.append(f"missing {REFERENCE.relative_to(REPO_ROOT)}")
    elif not problems:
        expected = reference_image()
        with Image.open(REFERENCE) as opened:
            actual = opened.convert("RGBA")
        if actual.size != expected.size or actual.tobytes() != expected.tobytes():
            problems.append(
                f"stale {REFERENCE.relative_to(REPO_ROOT)}; "
                "run tools/gen_icons.py --update-reference"
            )
    if not PIXEL_MANIFEST.is_file():
        problems.append(f"missing {PIXEL_MANIFEST.relative_to(REPO_ROOT)}")
    elif not problems and PIXEL_MANIFEST.read_text(encoding="utf-8") != pixel_manifest_text():
        problems.append(
            f"stale {PIXEL_MANIFEST.relative_to(REPO_ROOT)}; "
            "run tools/gen_icons.py --update-reference"
        )
    return problems


def check() -> None:
    problems = contract_problems()
    if problems:
        raise SystemExit("\n".join(f"- {problem}" for problem in problems))
    print("generated artwork matches its SVG and visual reference")


def build(only: str | None = None) -> None:
    """Render every emblem, or just ``only``.

    Regenerating an emblem that did not change still rewrites its PNGs, and a
    different Inkscape build produces different bytes for identical artwork.
    Naming one emblem keeps that churn out of the diff.
    """
    wanted = EMBLEMS if only is None else {only: EMBLEMS[only]}
    for emblem, render in wanted.items():
        for palette in PALETTES:
            out_dir = OUT_ROOT / emblem / palette.name
            out_dir.mkdir(parents=True, exist_ok=True)

            svg_path = out_dir / f"{emblem}-{palette.name}.svg"
            svg_path.write_text(render(palette), encoding="utf-8")

            for size in PNG_SIZES:
                _run(
                    [
                        "inkscape",
                        str(svg_path),
                        "--export-type=png",
                        f"--export-filename={out_dir / f'{size}.png'}",
                        f"--export-width={size}",
                        f"--export-height={size}",
                    ]
                )

            _run(
                [
                    "convert",
                    *[str(out_dir / f"{s}.png") for s in ICO_SIZES],
                    str(out_dir / f"{emblem}-{palette.name}.ico"),
                ]
            )
            print(f"built {emblem}/{palette.name}")
    write_reference()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("emblem", nargs="?", choices=sorted(EMBLEMS))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update-reference", action="store_true")
    args = parser.parse_args()

    if (args.check or args.update_reference) and args.emblem:
        parser.error("an emblem cannot be combined with --check or --update-reference")
    if args.check:
        check()
    elif args.update_reference:
        write_reference()
    else:
        build(args.emblem)
