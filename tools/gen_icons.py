"""Turn one PNG per emblem into mangame's three tray states.

Drop ``<name>.png`` into ``artwork/`` and run:

    uv run python tools/gen_icons.py

The source PNG is the artwork. Everything under
``src/mangame/assets/emblems/`` is derived output.
"""

import argparse
import shutil
from pathlib import Path

from PySide6.QtGui import QImage

from mangame.domain.models import IconState
from mangame.ui import artwork

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "artwork"
OUT_ROOT = REPO_ROOT / "src" / "mangame" / "assets" / "emblems"
OUTPUT_SIZE = 256


def sources() -> dict[str, Path]:
    return {
        artwork.emblem_name(path.stem): path
        for path in sorted(SOURCE_ROOT.glob("*.png"))
        if artwork.emblem_name(path.stem)
    }


def _image_bytes(image: QImage) -> bytes:
    converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    return bytes(converted.constBits())


def _expected(source: Path, state: IconState) -> QImage:
    return artwork.state_image(source, state, OUTPUT_SIZE)


def build(only: str | None = None) -> None:
    """Generate every source PNG, or one named emblem."""
    available = sources()
    if only is not None:
        name = artwork.emblem_name(only)
        if name not in available:
            raise SystemExit(f"no source PNG at {SOURCE_ROOT / f'{name}.png'}")
        available = {name: available[name]}

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name, source in available.items():
        out_dir = OUT_ROOT / name
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir()
        for state in IconState:
            target = out_dir / f"{state.value}.png"
            if not _expected(source, state).save(str(target)):
                raise SystemExit(f"could not write {target}")
        print(f"built {name}")

    if only is None:
        for stale in sorted(path for path in OUT_ROOT.iterdir() if path.is_dir()):
            if stale.name not in available:
                shutil.rmtree(stale)
                print(f"removed {stale.name}: no source PNG")


def contract_problems() -> list[str]:
    """Anything under bundled output that disagrees with its source PNG."""
    problems: list[str] = []
    available = sources()
    if not available:
        return [f"no source PNGs in {SOURCE_ROOT.relative_to(REPO_ROOT)}"]

    for name, source in available.items():
        out_dir = OUT_ROOT / name
        for state in IconState:
            target = out_dir / f"{state.value}.png"
            if not target.is_file():
                problems.append(f"missing {target.relative_to(REPO_ROOT)}")
                continue
            actual = QImage(str(target))
            expected = _expected(source, state)
            if actual.size() != expected.size() or _image_bytes(actual) != _image_bytes(expected):
                problems.append(f"stale {target.relative_to(REPO_ROOT)}")

        unexpected = sorted(
            path.relative_to(REPO_ROOT)
            for path in out_dir.rglob("*")
            if path.is_file() and path.name not in {f"{state.value}.png" for state in IconState}
        )
        problems.extend(f"unexpected generated file {path}" for path in unexpected)

    for stale in sorted(path for path in OUT_ROOT.iterdir() if path.is_dir()):
        if stale.name not in available:
            problems.append(f"no source PNG for {stale.relative_to(REPO_ROOT)}")
    return problems


def check() -> None:
    problems = contract_problems()
    if problems:
        raise SystemExit("\n".join(f"- {problem}" for problem in problems))
    print("bundled emblems match their source PNGs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("emblem", nargs="?")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check and args.emblem:
        parser.error("an emblem cannot be combined with --check")
    check() if args.check else build(args.emblem)
