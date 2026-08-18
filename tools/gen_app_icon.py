"""Build the installer icons from the app's own mark.

The tray artwork tops out at 256px because no panel asks for more. An
application icon does: Windows shells show 256, macOS Finder shows 512 at
2x. This renders the ready-state ``mangame`` emblem large and packs it into
the two container formats the platform installers insist on.

    uv run python tools/gen_app_icon.py

Needs Inkscape on PATH. The results are committed, so a release build does
not need Inkscape — only a change to the mark means rerunning this.
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "mangame" / "assets" / "emblems" / "mangame" / "ready" / "mangame-ready.svg"
OUT = ROOT / "packaging" / "icons"

# Every size a Windows shell or a macOS Finder will reach for. ICNS refuses
# anything that is not a power of two, so the ladder stops being arbitrary
# above 256.
SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def _render(size: int, target: Path) -> None:
    subprocess.run(
        [
            "inkscape",
            str(SOURCE),
            "--export-type=png",
            f"--export-filename={target}",
            f"--export-width={size}",
            f"--export-height={size}",
        ],
        check=True,
        capture_output=True,
    )


def build() -> None:
    if not SOURCE.is_file():
        sys.exit(f"missing {SOURCE} — run tools/gen_icons.py first")

    OUT.mkdir(parents=True, exist_ok=True)
    scratch = OUT / "_png"
    scratch.mkdir(exist_ok=True)

    rendered: dict[int, Path] = {}
    for size in sorted({*SIZES, *ICO_SIZES}):
        png = scratch / f"{size}.png"
        _render(size, png)
        rendered[size] = png

    # The lone PNG a Linux desktop entry points at.
    Image.open(rendered[512]).save(OUT / "mangame.png")

    Image.open(rendered[256]).save(
        OUT / "mangame.ico", sizes=[(s, s) for s in ICO_SIZES], format="ICO"
    )

    Image.open(rendered[1024]).save(OUT / "mangame.icns", format="ICNS")

    for png in scratch.iterdir():
        png.unlink()
    scratch.rmdir()

    for made in sorted(OUT.iterdir()):
        print(f"built {made.relative_to(ROOT)} ({made.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build()
