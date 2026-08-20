"""Turn one PNG per emblem into mangame's three tray states.

Drop ``<name>.png`` into ``artwork/`` and run:

    uv run python tools/gen_icons.py

The source PNG is the artwork. Everything under
``src/mangame/assets/emblems/`` is derived output.
"""

import argparse
import hashlib
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, UnidentifiedImageError

from mangame.domain.models import IconState
from mangame.ui.emblem_names import emblem_name

if TYPE_CHECKING:
    from PySide6.QtGui import QImage

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "artwork"
OUT_ROOT = REPO_ROOT / "src" / "mangame" / "assets" / "emblems"
TRANSFORM_SOURCE = REPO_ROOT / "src" / "mangame" / "ui" / "artwork.py"
OUTPUT_SIZE = 256

SOURCE_DIGEST_KEY = "mangame-source-sha256"
TRANSFORM_DIGEST_KEY = "mangame-transform-sha256"
PIXEL_DIGEST_KEY = "mangame-pixels-sha256"
STATE_KEY = "mangame-state"


def sources() -> dict[str, Path]:
    return {
        emblem_name(path.stem): path
        for path in sorted(SOURCE_ROOT.glob("*.png"))
        if emblem_name(path.stem)
    }


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _transform_digest() -> str:
    """Fingerprint everything that decides the generated pixels."""
    source = TRANSFORM_SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n")
    digest = hashlib.sha256(source.encode())
    digest.update(f"\0size={OUTPUT_SIZE}".encode())
    for state in IconState:
        digest.update(f"\0state={state.value}".encode())
    return digest.hexdigest()


def _image_bytes(image: "QImage") -> bytes:
    from PySide6.QtGui import QImage

    converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    return bytes(converted.constBits())


def _expected(source: Path, state: IconState) -> "QImage":
    from mangame.ui import artwork

    return artwork.state_image(source, state, OUTPUT_SIZE)


def _stamp(
    image: "QImage",
    *,
    source_digest: str,
    transform_digest: str,
    state: IconState,
) -> None:
    """Embed cross-platform provenance without prescribing renderer pixels."""
    image.setText(SOURCE_DIGEST_KEY, source_digest)
    image.setText(TRANSFORM_DIGEST_KEY, transform_digest)
    image.setText(PIXEL_DIGEST_KEY, hashlib.sha256(_image_bytes(image)).hexdigest())
    image.setText(STATE_KEY, state.value)


def build(only: str | None = None) -> None:
    """Generate every source PNG, or one named emblem."""
    available = sources()
    if only is not None:
        name = emblem_name(only)
        if name not in available:
            raise SystemExit(f"no source PNG at {SOURCE_ROOT / f'{name}.png'}")
        available = {name: available[name]}

    transform_digest = _transform_digest()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name, source in available.items():
        out_dir = OUT_ROOT / name
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir()
        source_digest = _file_digest(source)
        for state in IconState:
            target = out_dir / f"{state.value}.png"
            image = _expected(source, state)
            _stamp(
                image,
                source_digest=source_digest,
                transform_digest=transform_digest,
                state=state,
            )
            if not image.save(str(target)):
                raise SystemExit(f"could not write {target}")
        print(f"built {name}")

    if only is None:
        for stale in sorted(path for path in OUT_ROOT.iterdir() if path.is_dir()):
            if stale.name not in available:
                shutil.rmtree(stale)
                print(f"removed {stale.name}: no source PNG")


def _image_problems(
    target: Path,
    *,
    source_digest: str,
    transform_digest: str,
    state: IconState,
) -> list[str]:
    relative = target.relative_to(REPO_ROOT)
    try:
        with Image.open(target) as actual:
            actual.load()
            if actual.size != (OUTPUT_SIZE, OUTPUT_SIZE):
                return [f"wrong size for {relative}"]
            if (
                actual.info.get(SOURCE_DIGEST_KEY) != source_digest
                or actual.info.get(TRANSFORM_DIGEST_KEY) != transform_digest
                or actual.info.get(STATE_KEY) != state.value
            ):
                return [f"stale {relative}"]
            pixels = hashlib.sha256(actual.convert("RGBA").tobytes()).hexdigest()
            if actual.info.get(PIXEL_DIGEST_KEY) != pixels:
                return [f"modified {relative}"]
    except (OSError, UnidentifiedImageError):
        return [f"unreadable {relative}"]
    return []


def contract_problems() -> list[str]:
    """Anything under bundled output that disagrees with its source PNG."""
    problems: list[str] = []
    available = sources()
    if not available:
        return [f"no source PNGs in {SOURCE_ROOT.relative_to(REPO_ROOT)}"]

    transform_digest = _transform_digest()
    for name, source in available.items():
        out_dir = OUT_ROOT / name
        source_digest = _file_digest(source)
        for state in IconState:
            target = out_dir / f"{state.value}.png"
            if not target.is_file():
                problems.append(f"missing {target.relative_to(REPO_ROOT)}")
                continue
            problems.extend(
                _image_problems(
                    target,
                    source_digest=source_digest,
                    transform_digest=transform_digest,
                    state=state,
                )
            )

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
    print("bundled emblems match their source PNGs and transform")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("emblem", nargs="?")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check and args.emblem:
        parser.error("an emblem cannot be combined with --check")
    check() if args.check else build(args.emblem)
