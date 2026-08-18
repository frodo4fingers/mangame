# Contributing

Thanks for looking. This is a small project with a few firm opinions; the ones
that would otherwise surprise you are written down here.

## Getting set up

Needs Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/frodo4fingers/mangame
cd mangame
uv sync --extra dev
uv run pre-commit install
uv run mangame
```

## The loop

Everything CI runs, you can run:

```bash
uv run pytest                       # no network, no display
uv run ruff format .
uv run ruff check .
uv run mypy src tests tools
uv run mypy --platform win32 src tests tools
uv run mypy --platform darwin src tests tools
uv run pre-commit run --all-files
```

The two extra mypy passes are not optional busywork: `service/autostart.py`
branches on `sys.platform`, so a single run only ever type-checks a third of
it.

Tests never touch the network — HTTP is stubbed with `respx` — and never need a
display, because the Qt tests run on the `offscreen` platform. If a test of
yours wants either, it is testing the wrong thing.

## House rules

- **Python 3.12 is the floor.** No `from __future__ import annotations`.
- **Pydantic models, not dataclasses.**
- **Never write to the real user profile from a test.** Set `MANGAME_HOME`;
  the XDG variables do not work on Windows.
- **Pass the clock in.** Nothing under `src/mangame/domain/` may call
  `datetime.now()`, open a socket, or read a file. That purity is what makes
  the release-rhythm and break-detection rules testable.
- **Comment the surprising, not the obvious.** If a line needs a reason,
  write the reason; if it needs a restatement, delete the comment.
- **Test names are sentences.** `test_a_break_that_ended_is_not_a_break`
  beats `test_break_2`.

## Adding a source

`src/mangame/sources/` holds one module per site behind a small protocol.
[README.md](README.md#adding-a-source) walks through it.

One rule learned the hard way: **fetch the real endpoint and read the actual
payload before writing the parser.** Adapters written from documentation alone
have shipped subtly wrong behaviour every time.

## Artwork

Bundled emblems are generated, never hand-edited:

```bash
uv run python tools/gen_icons.py [emblem]   # tray sizes, needs inkscape + convert
uv run python tools/gen_app_icon.py         # the .ico/.icns for installers
```

A new emblem needs all three states to read correctly at 16px. `TestEmblems`
and `TestAppMark` in `tests/test_ui_support.py` measure that statistically
rather than trusting the eye — a thin shape can look fine and still fail to
read as a silhouette.

## Releasing

1. Update `CHANGELOG.md` and the `version` in `pyproject.toml`.
2. Tag it: `git tag v0.2.0 && git push --tags`.
3. `.github/workflows/release.yml` freezes the app for Linux, Windows and
   both macOS architectures, checks each build starts, and attaches them to a
   GitHub Release together with the wheel and sdist.

Publishing to PyPI is off by default. To turn it on, register this repository
as a [trusted publisher](https://docs.pypi.org/trusted-publishers/) for the
`mangame` project, add a repository environment named `pypi`, and set the
repository variable `PUBLISH_TO_PYPI` to `true`.

macOS builds are unsigned; signing and notarising them needs an Apple
Developer certificate that this project does not have.

## Pull requests

Small and focused, with a test that fails without the change. If you are
fixing a bug, the test name should state the real-world shape it guards
against.
