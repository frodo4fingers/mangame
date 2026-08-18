"""Generate the mangame tray emblem asset set.

Produces, for every emblem and every :class:`IconState`, an SVG master plus
rasterised PNGs at all tray-relevant pixel sizes and a Windows ``.ico``.

All artwork here is original. Emblems are deliberately generic real-world
objects (a straw boater hat, a book) or procedurally generated monograms, so
no third-party character art or logo is ever reproduced.

Run with:  uv run python tools/gen_icons.py
"""

import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "src" / "mangame" / "assets" / "emblems"

# Tray icons are tiny. 16-24px carries Windows/Linux panels, 36px covers a
# retina macOS menu bar, the large sizes are for the .ico and about dialogs.
PNG_SIZES = (16, 18, 20, 22, 24, 32, 36, 44, 48, 64, 128, 256)
ICO_SIZES = (16, 20, 24, 32, 48, 64, 256)


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

# Straw boater hat: wide brim ellipse + low domed crown + ribbon band.
_CROWN = "M14 45 C14 27 19 15 32 15 C45 15 50 27 50 45 Z"
_BRIM = (
    "M32 37 C47 37 58 40.5 58 45.5 C58 50.5 47 54 32 54 C17 54 6 50.5 6 45.5 C6 40.5 17 37 32 37 Z"
)


def _strawhat(p: Palette) -> str:
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


EMBLEMS = {"strawhat": _strawhat, "book": _book}


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def build() -> None:
    for emblem, render in EMBLEMS.items():
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


if __name__ == "__main__":
    build()
