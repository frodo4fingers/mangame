"""The command line, including the stream-free path used by packaged builds."""

import importlib.metadata
import sys
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from mangame import __main__, __version__
from mangame.store import paths

ROOT = Path(__file__).resolve().parent.parent


class TestVersion:
    def test_it_reports_a_version_and_stops(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Returning 0 without reaching QApplication is the point: asking a
        # tray app what it is must not start a tray.
        monkeypatch.setattr("sys.argv", ["mangame", "--version"])

        assert __main__.main() == 0
        assert capsys.readouterr().out.strip() == f"mangame {__version__}"

    def test_the_short_flag_works_too(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr("sys.argv", ["mangame", "-V"])

        assert __main__.main() == 0
        assert __version__ in capsys.readouterr().out

    def test_the_installed_metadata_agrees_with_the_package(self) -> None:
        # pyproject reads the version out of __init__.py rather than repeating
        # it. If that wiring is ever undone, these two drift apart silently.
        assert importlib.metadata.version("mangame") == __version__

    def test_the_build_does_not_hardcode_a_second_version(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

        assert "version" not in project
        assert "version" in project["dynamic"]

    def test_a_windowed_build_without_stdout_does_not_crash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.argv", ["mangame", "--version"])
        monkeypatch.setattr(sys, "stdout", None)

        assert __main__.main() == 0


class TestHelp:
    def test_it_explains_itself_and_stops(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr("sys.argv", ["mangame", "--help"])

        assert __main__.main() == 0
        assert "usage: mangame" in capsys.readouterr().out

    def test_the_short_flag_works_too(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr("sys.argv", ["mangame", "-h"])

        assert __main__.main() == 0
        assert "usage: mangame" in capsys.readouterr().out

    def test_it_names_the_only_environment_variable_that_exists(self) -> None:
        assert paths.HOME_VAR in __main__.USAGE

    def test_it_does_not_advertise_options_it_ignores(self) -> None:
        # Everything the usage text offers has to be handled above; a flag
        # that only appears in the help is a lie.
        offered = {
            word.strip("[]") for word in __main__.USAGE.split() if word.strip("[]").startswith("--")
        }

        assert offered == {"--version", "--help"}

    def test_a_windowed_build_without_stdout_does_not_crash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.argv", ["mangame", "--help"])
        monkeypatch.setattr(sys, "stdout", None)

        assert __main__.main() == 0


class TestPackagedEntry:
    def test_the_smoke_path_exercises_storage_and_bundled_artwork(
        self,
        qapp: QApplication,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(paths.HOME_VAR, str(tmp_path))

        assert __main__._smoke_test(qapp) == 0
        assert paths.database_file().is_file()

    def test_no_tray_is_reported_without_assuming_stderr_exists(
        self,
        qapp: QApplication,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("sys.argv", ["mangame"])
        monkeypatch.setattr(sys, "stderr", None)
        monkeypatch.setattr("mangame.__main__.env.load", lambda: None)
        monkeypatch.setattr(
            "mangame.__main__.diagnostics.configure_logging",
            lambda: tmp_path / "log",
        )
        monkeypatch.setattr(__main__, "_application", lambda: qapp)

        with patch(
            "mangame.__main__.QSystemTrayIcon.isSystemTrayAvailable",
            return_value=False,
        ):
            assert __main__.main() == 1
