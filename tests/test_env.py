"""The ``.env`` layer: machine-local paths that must never reach the repository.

The published project has to be empty. Anything that differs between one
machine and the next is an environment variable, and these tests pin down what
a ``.env`` may say, where it is looked for, and what it is not allowed to do.
"""

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from mangame.store import env, paths

EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"

GITIGNORE = EXAMPLE.parent / ".gitignore"


@pytest.fixture
def nowhere(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """No ``.env`` in reach, and nothing left behind afterwards.

    Both the working directory and the platform's configuration directory are
    real places that really might hold one, and a test that reads the author's
    own file is a test that passes for the wrong reason.

    The restore matters just as much: :func:`env.load` writes straight into
    ``os.environ``, which ``monkeypatch`` cannot know about, so without this a
    single test would redirect every later one to a directory that does not
    exist.
    """
    before = {k: v for k, v in os.environ.items() if k.startswith(env.PREFIX)}
    for name in before:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(paths, "default_config_dir", lambda: tmp_path / "config")

    yield tmp_path

    for name in [k for k in os.environ if k.startswith(env.PREFIX)]:
        del os.environ[name]
    os.environ.update(before)


class TestWhatAFileMaySay:
    def test_comments_and_blank_lines_are_skipped(self) -> None:
        assert env.parse("# a note\n\n  \nMANGAME_HOME=/data\n") == {"MANGAME_HOME": "/data"}

    def test_an_export_prefix_is_tolerated(self) -> None:
        # Someone will paste a line straight out of their shell profile.
        assert env.parse("export MANGAME_HOME=/data") == {"MANGAME_HOME": "/data"}

    @pytest.mark.parametrize("quote", ['"', "'"])
    def test_quotes_protect_surrounding_spaces(self, quote: str) -> None:
        parsed = env.parse(f"MANGAME_HOME={quote}/my games/manga{quote}")

        assert parsed == {"MANGAME_HOME": "/my games/manga"}

    def test_windows_line_endings_parse(self) -> None:
        # A file edited in Notepad arrives with CRLF, and a stray carriage
        # return in a path is a directory that will never be found.
        parsed = env.parse("MANGAME_HOME=C:\\data\r\nMANGAME_EMBLEM_DIR=C:\\art\r\n")

        assert parsed == {"MANGAME_HOME": "C:\\data", "MANGAME_EMBLEM_DIR": "C:\\art"}

    def test_only_the_first_equals_separates(self) -> None:
        assert env.parse("MANGAME_HOME=a=b") == {"MANGAME_HOME": "a=b"}

    def test_a_line_that_is_not_an_assignment_is_ignored(self) -> None:
        assert env.parse("just some prose\nMANGAME_HOME=/data") == {"MANGAME_HOME": "/data"}

    def test_surrounding_whitespace_is_dropped(self) -> None:
        assert env.parse("  MANGAME_HOME = /data  ") == {"MANGAME_HOME": "/data"}

    def test_a_trailing_note_is_a_comment_not_a_path(self) -> None:
        # The template is full of '#', so someone will annotate a line.
        assert env.parse("MANGAME_HOME=/data  # my stuff") == {"MANGAME_HOME": "/data"}

    def test_quoting_keeps_a_hash_that_is_meant(self) -> None:
        assert env.parse('MANGAME_HOME="/data/#1"') == {"MANGAME_HOME": "/data/#1"}


class TestWhatItRefusesToDo:
    def test_it_exports_nothing_but_mangame_variables(self, tmp_path: Path) -> None:
        # A .env is a tempting place to park unrelated secrets, and this app
        # has no business putting someone's database password in its process.
        path = tmp_path / ".env"
        path.write_text("MANGAME_HOME=/data\nAWS_SECRET_ACCESS_KEY=hunter2\n", encoding="utf-8")

        assert env.read(path) == {"MANGAME_HOME": "/data"}

    def test_a_missing_file_is_not_an_error(self, tmp_path: Path) -> None:
        assert env.read(tmp_path / "absent") == {}

    def test_an_unreadable_file_does_not_stop_the_app(self, tmp_path: Path) -> None:
        # Optional overrides are never worth refusing to start over.
        path = tmp_path / ".env"
        path.write_bytes(b"\xff\xfe\x00binary")

        assert env.read(path) == {}

    def test_the_real_environment_always_wins(
        self, nowhere: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Otherwise a file left in some directory could silently override
        # "MANGAME_HOME=/tmp/x mangame" typed on the command line.
        (nowhere / ".env").write_text("MANGAME_HOME=/from-file", encoding="utf-8")
        monkeypatch.setenv(paths.HOME_VAR, "/from-the-shell")

        env.load()

        assert paths.home_override() == Path("/from-the-shell")


class TestLoading:
    def test_an_unset_variable_is_filled_in(
        self, nowhere: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (nowhere / ".env").write_text("MANGAME_HOME=/from-file", encoding="utf-8")
        monkeypatch.delenv(paths.HOME_VAR, raising=False)

        used = env.load()

        assert used == nowhere / ".env"
        assert paths.home_override() == Path("/from-file")

    def test_no_file_anywhere_is_the_normal_case(self, nowhere: Path) -> None:
        assert env.load() is None


class TestWhereItLooks:
    def test_an_explicit_path_comes_first(
        self, nowhere: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(env.ENV_FILE_VAR, str(nowhere / "elsewhere.env"))

        assert env.candidates()[0] == nowhere / "elsewhere.env"

    def test_the_working_directory_serves_a_clone(self, nowhere: Path) -> None:
        assert nowhere / ".env" in env.candidates()

    def test_the_config_directory_is_the_last_resort(self, nowhere: Path) -> None:
        # A tray app started at login has no working directory worth the name,
        # so without this nothing would ever be found in the ordinary case.
        assert env.candidates()[-1] == nowhere / "config" / ".env"

    def test_a_frozen_build_looks_beside_itself(
        self, nowhere: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The whole point of a portable install is that the stick carries its
        # own configuration.
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", str(nowhere / "bin" / "mangame"))

        assert nowhere / "bin" / ".env" in env.candidates()

    def test_an_ordinary_run_does_not(self, nowhere: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)

        assert all(c.parent != Path(sys.executable).resolve().parent for c in env.candidates())


class TestTheTemplateStaysHonest:
    """``.env.example`` is committed; the real file never is.

    It is also the only documentation most people will read about these
    variables, so it has to name all of them and reveal none of anyone's.
    """

    def test_it_documents_every_variable_the_code_reads(self) -> None:
        text = EXAMPLE.read_text(encoding="utf-8")
        declared = {
            value
            for module in (paths, env)
            for value in vars(module).values()
            if isinstance(value, str) and value.startswith(env.PREFIX)
        }

        assert declared, "no variables discovered — the check would pass vacuously"
        for name in sorted(declared):
            assert name in text, f"{name} is read by the code but not in .env.example"

    def test_every_setting_in_it_is_commented_out(self) -> None:
        # Copying the template must change nothing until a line is chosen.
        live = env.parse(EXAMPLE.read_text(encoding="utf-8"))

        assert live == {}, f"the template would take effect: {live}"

    def test_the_real_file_cannot_be_committed(self) -> None:
        rules = GITIGNORE.read_text(encoding="utf-8").splitlines()

        assert ".env" in rules
        assert "!.env.example" in rules
