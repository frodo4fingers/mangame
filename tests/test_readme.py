"""The documentation, held to the code.

Prose is not testable and is not tested here. File names, sizes, defaults,
language codes and release artifact names are, and those are exactly what had
gone stale: the database was documented under a name it has never had, the
Windows data directory under one platformdirs does not use, and the test count
under a number three releases old.

Only facts that appear verbatim in both places are pinned, so ordinary editing
stays free. Every markdown file in the repository has its relative links
checked, because five of them now cross-reference each other.
"""

import re
from pathlib import Path

import pytest

from mangame.domain.models import IconState
from mangame.i18n import languages
from mangame.store import config, paths
from mangame.ui import emblems

README = Path(__file__).resolve().parents[1] / "README.md"
TEXT = README.read_text(encoding="utf-8")

RELEASE = README.parent / ".github" / "workflows" / "release.yml"
RELEASE_LABELS = set(re.findall(r"label: ([a-z0-9_-]+)", RELEASE.read_text(encoding="utf-8")))


class TestPaths:
    def test_the_database_is_named_as_it_is_written(self) -> None:
        assert paths.database_file().name in TEXT

    def test_no_earlier_name_for_it_survives(self) -> None:
        stale = set(re.findall(r"\b[\w-]+\.(?:db|sqlite3?)\b", TEXT))
        assert stale <= {paths.database_file().name}

    def test_the_settings_file_is_named_as_it_is_written(self) -> None:
        assert paths.config_file().name in TEXT

    def test_the_artwork_directory_is_named_as_it_is_written(self) -> None:
        assert f"{paths.user_emblem_dir().name}/" in TEXT


class TestArtwork:
    def test_the_documented_icon_sizes_are_the_ones_rendered(self) -> None:
        # The drop-in path is spelt as emblems/<name>/<state>/<16|18|...>.png,
        # which is a promise about what a hand-made emblem has to contain.
        written = re.search(r"<((?:\d+\|)+\d+)>\.png", TEXT)
        assert written is not None, "the drop-in path is no longer documented"
        assert tuple(int(n) for n in written.group(1).split("|")) == emblems.SIZES

    def test_the_documented_states_are_the_ones_derived(self) -> None:
        written = re.search(r"<((?:\w+\|)+\w+)>/<", TEXT)
        assert written is not None
        assert set(written.group(1).split("|")) == {s.value for s in IconState}

    @pytest.mark.parametrize("emblem", ["onepiece", "book", "mangame"])
    def test_every_emblem_it_names_is_shipped(self, emblem: str) -> None:
        assert emblem in TEXT
        assert emblem in emblems.available_emblems()


class TestLanguages:
    @pytest.mark.parametrize("code", languages.codes())
    def test_every_offered_language_has_a_row(self, code: str) -> None:
        assert f"`{code}`" in TEXT

    def test_it_does_not_promise_a_language_that_cannot_be_polled(self) -> None:
        promised = set(re.findall(r"^\| \w+ \| `([\w`, -]+)` \|", TEXT, re.MULTILINE))
        offered = {c for row in promised for c in re.findall(r"[\w-]+", row)}
        assert offered <= set(languages.codes()) | set(languages.source_codes("es"))


class TestFileOnlySettings:
    def test_the_tray_icon_cap_is_documented_at_its_real_default(self) -> None:
        default = config.Settings().max_tray_icons
        assert re.search(rf"`max_tray_icons` \| `{default}`", TEXT)

    @pytest.mark.parametrize("key", ["max_tray_icons", "enabled", "language"])
    def test_it_only_documents_keys_that_exist(self, key: str) -> None:
        fields = set(config.Settings.model_fields) | set(config.SeriesConfig.model_fields)
        assert key in fields
        assert key in TEXT


class TestWhatItPromisesToShip:
    """Download names are a promise the release workflow has to keep.

    A README that names an archive nobody builds sends users to a 404, and
    nothing else in the suite reads the workflow.
    """

    def test_every_download_it_offers_is_actually_built(self) -> None:
        offered = set(re.findall(r"`mangame-([a-z0-9_-]+)\.(?:tar\.gz|zip)`", TEXT))

        assert offered, "the download table no longer names any file"
        assert offered <= RELEASE_LABELS, offered - RELEASE_LABELS

    def test_every_build_produced_is_offered(self) -> None:
        offered = set(re.findall(r"`mangame-([a-z0-9_-]+)\.(?:tar\.gz|zip)`", TEXT))

        assert offered >= RELEASE_LABELS, RELEASE_LABELS - offered

    def test_the_portable_directory_variable_is_named_correctly(self) -> None:
        assert paths.HOME_VAR in TEXT


ROOT = README.parent
DOCS = sorted(p for p in [*ROOT.glob("*.md"), *(ROOT / "docs").glob("*.md")])


class TestEveryDocument:
    """Applied to all of them, not just the README.

    Five markdown files now cross-link each other. A link that rots is a
    reader sent to a 404, and none of them is otherwise read by a test.
    """

    @pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.name)
    def test_its_relative_links_resolve(self, doc: Path) -> None:
        body = doc.read_text(encoding="utf-8")

        for link in re.findall(r"\]\((?!\w+:)([^)#]+)\)", body):
            assert (doc.parent / link).exists(), f"{doc.name} links to missing {link}"

    def test_the_agent_guide_is_the_only_one_of_its_kind(self) -> None:
        # AGENTS.md is read by every major coding agent. A second copy under
        # another tool's name is a rule that will drift out of agreement.
        rivals = [p.name for p in ROOT.rglob("CLAUDE.md")]
        rivals += [p.name for p in (ROOT / ".github").glob("copilot-instructions.md")]

        assert (ROOT / "AGENTS.md").is_file()
        assert not rivals, f"agent guidance duplicated in {rivals}"
