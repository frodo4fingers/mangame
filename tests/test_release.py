"""Release automation must not publish stale metadata or notices."""

from pathlib import Path

from tools.check_release import release_problems
from tools.gen_notices import render

VERSION = "1.2.3"
CHANGELOG = """\
# Changelog

## [1.2.3]

- A change.

[1.2.3]: https://github.com/frodo4fingers/mangame/releases/tag/v1.2.3
"""


def test_matching_release_metadata_is_accepted() -> None:
    assert release_problems(VERSION, CHANGELOG, "v1.2.3") == []


def test_a_tag_for_another_version_is_rejected() -> None:
    assert release_problems(VERSION, CHANGELOG, "v1.2.4") == [
        "tag v1.2.4 does not match package version 1.2.3"
    ]


def test_a_missing_changelog_section_is_rejected() -> None:
    problems = release_problems(VERSION, CHANGELOG.replace("## [1.2.3]", "## [Unreleased]"))

    assert "CHANGELOG.md has no ## [1.2.3] release section" in problems


def test_a_missing_release_link_is_rejected() -> None:
    problems = release_problems(VERSION, CHANGELOG.replace("/tag/v1.2.3", "/tag/v1.2.2"))

    assert "CHANGELOG.md has no release link for v1.2.3" in problems


def test_a_manual_branch_build_does_not_pretend_to_be_a_tag() -> None:
    assert release_problems(VERSION, CHANGELOG, "main") == []


def test_the_third_party_notice_matches_the_installed_runtime() -> None:
    assert render() == (Path(__file__).resolve().parents[1] / "THIRD_PARTY_NOTICES.md").read_text(
        encoding="utf-8"
    )
