# Contributing

Thanks for looking. This is a small project with a few firm opinions; the ones
that would otherwise surprise you are written down here.

Participation is covered by the [code of conduct](CODE_OF_CONDUCT.md).
By submitting a contribution, you agree that it may be distributed under the
repository's [MIT licence](LICENSE); submit only work you have the right to
license that way.

If you are working with an AI coding agent, point it at
[AGENTS.md](AGENTS.md) — the same rules, stated the way an agent needs them.

## Getting set up

Needs Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/frodo4fingers/mangame
cd mangame
uv sync --locked --extra dev
uv run pre-commit install
uv run mangame
```

The full pre-commit run includes gitleaks in Docker, so Docker must be
available. Artwork generation uses Pillow from the normal development
environment and needs no external renderer.

Dependabot updates Python and GitHub Actions dependencies. `renovate.json5`
covers pre-commit hook revisions, which Dependabot does not manage; enable the
Renovate GitHub app after the repository is published. Maintainers should
apply [docs/REPOSITORY_SETUP.md](docs/REPOSITORY_SETUP.md) once to configure
the settings Git cannot carry.

## The loop

Everything CI runs, you can run:

```bash
uv run pytest                       # no network, no display
uv run ruff format .
uv run ruff check .
uv run mypy --platform linux src tests tools
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
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#1-sources-only-report-timestamps)
explains why the contract is deliberately small.

One rule learned the hard way: **fetch the real endpoint and read the actual
payload before writing the parser.** Adapters written from documentation alone
have shipped subtly wrong behaviour every time.

A source contribution must:

1. implement the `Source` protocol in `sources/base.py`;
2. declare search, chapter/status and language capabilities honestly;
3. set a conservative rate limit and use the shared HTTP client;
4. register the adapter in `sources/registry.py`;
5. add `respx` tests for search, parsing, failures, conditional requests and
   language filtering without touching the network;
6. update the README and security documentation when the app contacts a new
   domain.

If a site already exposes RSS or Atom, prefer the built-in `feed` source over a
new adapter.

## Artwork

Add one original PNG to `artwork/`; the generated ready, due and break files
are never hand-edited:

```bash
uv run python tools/gen_icons.py [emblem]
uv run python tools/gen_icons.py --check
uv run python tools/gen_app_icon.py         # the .ico/.icns for installers
```

The normal development environment is sufficient; no external renderer is
needed. A new emblem still needs all three generated states to read correctly
at 16px. `TestEmblems` and `TestAppMark` in `tests/test_ui_support.py` measure
that statistically rather than trusting the eye.

Read [docs/ARTWORK.md](docs/ARTWORK.md) before proposing bundled artwork. It
defines the one-PNG workflow and the original-work requirement.

## Releasing

Follow [docs/RELEASING.md](docs/RELEASING.md). The only version number is
`__version__` in `src/mangame/__init__.py`; `pyproject.toml` reads it
dynamically.

## Pull requests

Small and focused, with a test that fails without the change. If you are
fixing a bug, the test name should state the real-world shape it guards
against.

Use the pull request template. UI and artwork changes need before/after images.
The public wishlist is the issue tracker and its milestones; [ROADMAP.md](ROADMAP.md)
contains direction only.
