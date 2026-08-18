# AGENTS.md

Instructions for AI coding agents working in this repository. Read this before
changing anything.

This is the single source for agent guidance — Copilot, Codex, Cursor and
others all read `AGENTS.md`. Do not add a second copy under another name; a
duplicated rule is a rule that will drift.

Humans should read [CONTRIBUTING.md](CONTRIBUTING.md); it covers the same
ground more gently. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains
*why* the design is what it is, and is worth reading before proposing a change
to it.

## What this is

A cross-platform system-tray app that watches manga sources and shows, per
series or for the whole library, whether a chapter is waiting (full colour),
due (grey) or blocked by an announced break (dark silhouette). Python 3.12,
PySide6, uv, SQLite. No server, no accounts, no window.

## Commands

```bash
uv sync --extra dev          # set up
uv run mangame               # run it
uv run pytest                # fast, and needs neither network nor a display
uv run ruff format .
uv run ruff check .
uv run mypy src tests tools
```

Before claiming any change is done, run the full gate:

```bash
uv run ruff format --check . && uv run ruff check .
uv run mypy --platform linux src tests tools
uv run mypy --platform win32 src tests tools
uv run mypy --platform darwin src tests tools
uv run pytest
uv run pre-commit run --all-files
```

The three mypy runs are not redundant. `service/autostart.py` branches on
`sys.platform`, so a single run type-checks one third of it.

If you touch `.github/workflows/`, run `actionlint` — with `shellcheck`
installed, or its shell rules silently do not run.

## Hard rules

- **Python 3.12 is the floor.** Never add `from __future__ import annotations`.
- **Pydantic `BaseModel`, never `dataclasses`.**
- **`src/mangame/domain/` is pure.** No I/O, no network, no file access, and no
  `datetime.now()` — the current time is always a parameter. This is what makes
  the cadence, break-detection and scheduling rules testable, and it is the
  single most important invariant in the codebase.
- **Tests never touch the network or a display.** HTTP is stubbed with `respx`;
  Qt runs on the `offscreen` platform via the session-scoped `qapp` fixture.
- **Tests isolate with `MANGAME_HOME`, never the XDG variables.** Windows
  ignores XDG, so an XDG-based fixture writes into the real user profile there.
  The same applies to anything that calls `mkdir`: `user_emblem_dir()` creates
  what it returns, so a test expanding `~` must fake `HOME`/`USERPROFILE` too.
- **The repository publishes empty.** No tracked series, no imported artwork,
  nothing naming a person. Machine-local paths are environment variables read
  from a git-ignored `.env`; `.env.example` is the committed template and a
  test asserts it names every `MANGAME_*` variable the code reads.
- **One version number**, in `src/mangame/__init__.py`. `pyproject.toml`
  declares `dynamic = ["version"]` and reads it. Nothing else may hardcode it.
- **Bundled artwork is generated**, never hand-edited — see Artwork below.

## Where things live

| Path | Holds | Note |
| --- | --- | --- |
| `src/mangame/domain/` | Models, cadence learning, break detection, icon state, the poll-interval ladder | Pure. Guard this. |
| `src/mangame/sources/` | One adapter per site behind a shared protocol | The only place that talks to the network |
| `src/mangame/store/` | SQLite state, JSON settings, platform paths, `.env` | `env.load()` runs before any path is resolved |
| `src/mangame/service/` | Poller, library orchestration, start-on-login | Platform branching lives here |
| `src/mangame/ui/` | Tray, menus, dialogs, notifications, emblem rendering | Qt only here |
| `src/mangame/i18n/` | Translation catalogue, language codes | en, de, es |
| `tools/` | Artwork generators | Need `inkscape` and ImageMagick `convert` |
| `packaging/` | PyInstaller spec, icons, desktop entry | |

## Conventions

- **Test names are sentences that state the guarantee.**
  `test_a_break_that_ended_is_not_a_break`, not `test_break_2`.
- **Comment the surprising, not the obvious.** If a line needs a reason, write
  the reason. If it only needs restating, delete the comment.
- **Docstrings say why, not what.** The signature already says what.
- **A bug fix comes with a test that fails without it**, named for the
  real-world shape it guards against.

## Traps this project has already fallen into

Each of these cost real debugging time. They are all still reachable.

- **Never write an HTTP adapter from documentation.** Fetch the real endpoint,
  print the payload, then parse what actually came back. Every adapter here was
  written that way after doing it the other way went wrong.
- **`QSystemTrayIcon` is not a `QWidget`**, so its menu cannot be parented to
  it. The Python reference is all that keeps the menu alive — rebuilding icons
  on the refresh timer once deleted a menu while it was open on screen.
- **Do not script a block replacement across a boundary you have not just
  read.** This has silently deleted tests twice. Anchor on both ends, and check
  the test count moved by exactly what you added.
- **Documentation drifts silently.** `tests/test_readme.py` pins the
  machine-checkable claims — file names, defaults, language codes, release
  artifact names. Extend it rather than writing a fact that nothing verifies,
  and never put a hand-maintained count in a document.
- **When changing behaviour, grep the docs for the *rationale*, not just the
  description.** An explanation of why something is impossible is the first
  thing to fix when it becomes possible.

## Artwork

```bash
uv run python tools/gen_icons.py [emblem]   # tray sizes for one or all emblems
uv run python tools/gen_app_icon.py         # the .ico/.icns for installers
```

A new emblem must read correctly at 16px in all three states.
`TestEmblems` and `TestAppMark` in `tests/test_ui_support.py` measure that
statistically, because a thin shape can look fine to the eye and still fail to
read as a silhouette. Judge artwork by those measurements, and fix the drawing
rather than the threshold.

## Working notes

`tasks/todo.md` and `tasks/lessons.md` are the maintainer's private working
notes. They are gitignored on purpose. Update them if they exist locally; never
commit them, and never assume a clone has them.
