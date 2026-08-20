"""Build installer icons from the app mark's single source PNG."""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "artwork" / "mangame.png"
OUT = ROOT / "packaging" / "icons"

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def build() -> None:
    if not SOURCE.is_file():
        sys.exit(f"missing {SOURCE}")

    OUT.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE) as opened:
        source = opened.convert("RGBA")

    source.resize((512, 512), Image.Resampling.LANCZOS).save(OUT / "mangame.png")
    source.resize((256, 256), Image.Resampling.LANCZOS).save(
        OUT / "mangame.ico",
        sizes=[(size, size) for size in ICO_SIZES],
        format="ICO",
    )
    source.resize((1024, 1024), Image.Resampling.LANCZOS).save(
        OUT / "mangame.icns",
        format="ICNS",
    )

    for made in sorted(OUT.iterdir()):
        print(f"built {made.relative_to(ROOT)} ({made.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build()
