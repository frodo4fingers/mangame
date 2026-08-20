"""Keep a release tag, package version and changelog section in agreement."""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mangame import __version__  # noqa: E402

CHANGELOG = ROOT / "CHANGELOG.md"


def release_problems(version: str, changelog: str, tag: str | None = None) -> list[str]:
    problems: list[str] = []
    expected_tag = f"v{version}"

    if tag and tag.startswith("v") and tag != expected_tag:
        problems.append(f"tag {tag} does not match package version {version}")

    headings = set(re.findall(r"^## \[([^\]]+)\]$", changelog, re.MULTILINE))
    if version not in headings:
        problems.append(f"CHANGELOG.md has no ## [{version}] release section")

    expected_link = (
        f"[{version}]: https://github.com/frodo4fingers/mangame/releases/tag/{expected_tag}"
    )
    if expected_link not in changelog:
        problems.append(f"CHANGELOG.md has no release link for {expected_tag}")
    return problems


def check(tag: str | None = None) -> None:
    problems = release_problems(__version__, CHANGELOG.read_text(encoding="utf-8"), tag)
    if problems:
        raise SystemExit("\n".join(f"- {problem}" for problem in problems))
    print(f"release metadata agrees on v{__version__}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", nargs="?")
    check(parser.parse_args().tag)
