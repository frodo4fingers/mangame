"""Diagnostics must survive the no-console environment of packaged GUI builds."""

import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from mangame import __version__, diagnostics
from mangame.store import paths


@pytest.fixture
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    root.handlers = []
    yield
    for handler in root.handlers:
        if handler not in original_handlers:
            handler.close()
    root.handlers = original_handlers
    root.setLevel(original_level)


def test_logging_works_without_standard_streams(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restore_logging: None,
) -> None:
    monkeypatch.setenv(paths.HOME_VAR, str(tmp_path))
    monkeypatch.setattr(sys, "stderr", None)

    target = diagnostics.configure_logging()
    logging.getLogger("mangame.test").warning("visible after packaging")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert target == tmp_path / "mangame.log"
    assert "visible after packaging" in target.read_text(encoding="utf-8")


def test_the_report_names_the_runtime_and_support_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(paths.HOME_VAR, str(tmp_path))

    report = diagnostics.report()

    assert f"mangame {__version__}" in report
    assert f"Settings: {tmp_path / 'config.json'}" in report
    assert f"Database: {tmp_path / 'state.sqlite3'}" in report
    assert f"Log: {tmp_path / 'mangame.log'}" in report
