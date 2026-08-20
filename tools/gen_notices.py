"""Generate the runtime dependency notice from installed package metadata."""

import argparse
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
NOTICE = ROOT / "THIRD_PARTY_NOTICES.md"


def _key(name: str) -> str:
    return name.lower().replace("_", "-")


def runtime_distributions() -> list[metadata.Distribution]:
    queue = [
        Requirement(raw).name
        for raw in metadata.requires("mangame") or []
        if Requirement(raw).marker is None
    ]
    found: dict[str, metadata.Distribution] = {}
    while queue:
        requested = queue.pop(0)
        key = _key(requested)
        if key in found:
            continue
        distribution = metadata.distribution(requested)
        found[key] = distribution
        for raw in distribution.requires or []:
            requirement = Requirement(raw)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                queue.append(requirement.name)
    return [found[key] for key in sorted(found)]


def _license(distribution: metadata.Distribution) -> str:
    expression = distribution.metadata.get("License-Expression")
    if expression:
        return expression
    written = distribution.metadata.get("License") or ""
    return next((line.strip() for line in written.splitlines() if line.strip()), "See package")


def render() -> str:
    rows = []
    for distribution in runtime_distributions():
        name = distribution.metadata["Name"]
        url = f"https://pypi.org/project/{name}/{distribution.version}/"
        rows.append(f"| [{name}]({url}) | {distribution.version} | {_license(distribution)} |")

    return (
        "# Third-party notices\n\n"
        "The standalone builds include the runtime packages below. Versions are\n"
        "generated from `uv.lock` through the installed environment; the licence\n"
        "terms published by each project remain authoritative.\n\n"
        "| Package | Version | Licence |\n"
        "| --- | --- | --- |\n"
        f"{chr(10).join(rows)}\n\n"
        "PySide6 and shiboken6, including the Qt libraries they package, are used\n"
        "under the LGPL-3.0-only option. mangame's source and complete PyInstaller\n"
        "build recipe are available in this repository so a recipient can rebuild\n"
        "the application with a modified compatible library.\n\n"
        "Licence texts:\n\n"
        "- [LGPL 3.0](https://www.gnu.org/licenses/lgpl-3.0.html)\n"
        "- [GPL 2.0](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)\n"
        "- [GPL 3.0](https://www.gnu.org/licenses/gpl-3.0.html)\n"
        "- [MIT](https://spdx.org/licenses/MIT.html)\n"
        "- [BSD 3-Clause](https://spdx.org/licenses/BSD-3-Clause.html)\n"
        "- [MPL 2.0](https://www.mozilla.org/MPL/2.0/)\n"
        "- [Python Software Foundation 2.0](https://spdx.org/licenses/PSF-2.0.html)\n"
    )


def write() -> None:
    NOTICE.write_text(render(), encoding="utf-8")
    print(f"built {NOTICE.relative_to(ROOT)}")


def check() -> None:
    expected = render()
    if not NOTICE.is_file() or NOTICE.read_text(encoding="utf-8") != expected:
        raise SystemExit("THIRD_PARTY_NOTICES.md is stale; run tools/gen_notices.py")
    print("third-party notices match the locked runtime dependencies")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    if parser.parse_args().check:
        check()
    else:
        write()
