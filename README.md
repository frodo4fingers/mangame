# mangame

[![CI](https://github.com/frodo4fingers/mangame/actions/workflows/ci.yml/badge.svg)](https://github.com/frodo4fingers/mangame/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A system-tray app that tells you, at a glance, whether there is manga to read.

![A tray tooltip reading "One Piece — ch. 1192 is ready to read", followed by
the reading language and the sources that were checked](docs/images/tray-ready.png)

One icon per series. Three states, and nothing else to interpret:

| Icon | Meaning |
| --- | --- |
| **Full colour** | A chapter is out and you have not read it. |
| **Grey** | You are caught up; the next chapter is due. |
| **Black** | A break has been announced — there is no chapter this week. |

![The same tooltip a few days earlier, reading "One Piece — next chapter
expected So 06 Sep 15:00 UTC"](docs/images/tray-due.png)

Hovering says the rest: what is waiting or when it is expected, in which
language, and which sources agreed on it.

Or use one icon for everything — mangame's own **M** wears the same three
states and reports the best news in your library. Pick either in Settings, and
give the aggregate icon a straw hat, a book or your own artwork if you prefer.

Runs on Linux, Windows and macOS — in the system tray, the notification area,
or the menu bar, whichever your desktop calls it.

## Install

### Download a build

No Python, no toolchain — grab the file for your platform from the
[releases page](https://github.com/frodo4fingers/mangame/releases) and run it.

| Platform | File | Then |
| --- | --- | --- |
| Linux (x86-64) | `mangame-linux-x86_64.tar.gz` | Unpack and run `./mangame`. |
| Windows (x86-64) | `mangame-windows-x86_64.zip` | Unpack and run `mangame.exe`. |
| macOS (Apple silicon) | `mangame-macos-arm64.zip` | Unpack and move `mangame.app` to Applications. |
| macOS (Intel) | `mangame-macos-x86_64.zip` | Same. |

Two things the operating system will ask about:

- **macOS** — the app is not signed with an Apple developer certificate, so
  Gatekeeper blocks the first launch. Right-click it and choose *Open*, or run
  `xattr -dr com.apple.quarantine mangame.app`.
- **Linux** — if your browser cleared the executable bit, `chmod +x mangame`.
  For a normal launcher entry, copy the bundled `mangame.desktop` into
  `~/.local/share/applications/` and `mangame.png` into
  `~/.local/share/icons/hicolor/512x512/apps/`.

### Install with uv or pipx

mangame is not on PyPI yet, so install it from the repository — this builds the
same package the releases are cut from:

```bash
uv tool install git+https://github.com/frodo4fingers/mangame
mangame
```

`pipx install git+https://github.com/frodo4fingers/mangame` does the same.
Append `@v0.2.0` to either URL to pin a release instead of tracking `main`.

### Run from source

Needs Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/frodo4fingers/mangame
cd mangame
uv sync
uv run mangame
```

However you start it, there is no window — everything happens in the tray menu.
Turn on **Start on login** in Settings to have it come back by itself.

## Using it

**Either mouse button opens the menu.** An icon in a panel shows nothing but a
picture, so whichever button you try first has to arrive somewhere.

The menu holds verbs only — Open chapter, Mark as read, Add manga, Check now,
Settings, Quit. Nothing nests, and everything with a *value* lives in the
settings window instead, so the menu stays one flat list that cannot run off the
edge of a screen.

**Settings…** opens one window with four tabs: **General** (reading language,
one icon or one per manga, notifications, start on login), **Manga** (which
series get their own icon, the emblem each wears, and adding or dropping one),
**Artwork** (turn any picture into an emblem) and **Diagnostics** (version and
support-file paths for a bug report). Changes take effect as you make them.

**Add manga…** does the whole job in one window: type a title, hit Enter, pick
a result, choose Add. Results are grouped by series rather than listed per
source, so one row like

```
One Piece (1997)
mangadex · mangaupdates · anilist
```

is one series found by three sources, and Add links all of them — MangaDex and
MangaUpdates supply chapter times, while AniList supplies the hiatus flag. A
series needs both to use all three icon states. Anything you already track is
greyed out.

Only sources that can serve your reading language are searched, so every result
is one that can actually be tracked.

## Languages

English, Español and Deutsch — the three the sources can actually be held to.
A per-series language overrides the global one, for the single title you follow
in a different language from the rest.

Which source serves which language, and why MangaUpdates is English-only, is in
[docs/CONFIGURATION.md](docs/CONFIGURATION.md#languages-in-detail).

## How often it checks

You never set an interval. mangame learns each series' rhythm from the
timestamps it has already seen and asks more often the closer the next chapter
gets — about daily when it is a week away, down to every ten minutes when it is
due. Requests are conditional, so a check that finds nothing new usually
transfers nothing, and a laptop that suspends overnight catches up the moment it
wakes. **Check now** ignores all of it and asks immediately.

The full ladder is in
[docs/CONFIGURATION.md](docs/CONFIGURATION.md#how-often-it-checks). mangame
talks only to those sources: no telemetry, no analytics, no update check — see
[SECURITY.md](SECURITY.md).

## Settings, storage and your own sources

Settings, database, logs and artwork land wherever your OS expects, and
`MANGAME_HOME` puts them all in one directory instead — for a portable copy on
a stick, or a second instance that leaves the first alone. `config.json` is
plain JSON and safe to hand-edit while the app runs.

Any site with an RSS/Atom feed can be tracked by adding a config entry rather
than writing code, because a feed carries the only two things mangame needs:
titles and timestamps.

Paths, environment variables, the `.env` lookup order, the keys that have no
control, and the feed recipe are all in
[docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Your own artwork

Drop one PNG named for the manga into the emblem directory — `Hunter x
Hunter.png` is matched to `hunter-x-hunter` without editing config — and
mangame derives the ready, due and break versions behind it. **Settings ▸
Artwork** is the same thing with a file picker, and tells you which manga the
filename matched before importing.

Anything without artwork gets a monogram: its initial on a colour derived from
the title, so two untouched series never look alike. Details and the
contributor workflow are in [docs/ARTWORK.md](docs/ARTWORK.md).

## Desktop support

mangame uses Qt's `QSystemTrayIcon`, so it sits wherever the platform puts one.
On Linux that means the StatusNotifierItem protocol: KDE, XFCE, Cinnamon, MATE
and most tiling-WM bars support it out of the box. **GNOME needs the
[AppIndicator and KStatusNotifierItem](https://extensions.gnome.org/extension/615/appindicator-support/)
extension**, which GNOME does not ship by default; without it no tray icon can
appear, for any application.

Where a panel reports the icon's position the menu opens against it, and where
it does not the menu opens at the pointer — either way inside the work area, so
it is never left behind a panel or off the screen.

## Development

```bash
uv sync --extra dev
uv run pytest          # no network, no display
uv run ruff format . && uv run ruff check .
uv run pre-commit install
```

The domain layer (`src/mangame/domain/`) is pure: no I/O, no clock, no
network — the current time is always passed in. That is what makes the
release-rhythm, break-detection and scheduling rules directly testable.

[CONTRIBUTING.md](CONTRIBUTING.md) has the full loop, including type-checking
each target platform and building a standalone executable.
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains why it is built this way,
and [AGENTS.md](AGENTS.md) is for working with an AI coding agent.

Questions and bug-report guidance live in [SUPPORT.md](SUPPORT.md); project
direction lives in [ROADMAP.md](ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE). Licences for dependencies bundled into standalone
builds are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
