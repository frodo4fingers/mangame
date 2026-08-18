# mangame

A system-tray app that tells you, at a glance, whether there is manga to read.

One icon per series. Three states, and nothing else to interpret:

| Icon | Meaning |
| --- | --- |
| **Full colour** | A chapter is out and you have not read it. |
| **Grey** | You are caught up; the next chapter is due. |
| **Black** | A break has been announced — there is no chapter this week. |

Or one icon for everything: mangame's own **M** wears the same three states,
and reports the best news in your library. Pick either in Settings — and if you
would rather the aggregate icon wore a straw hat, a book or your own artwork,
pick that too.

Runs on Linux, Windows and macOS — in the system tray, the notification area,
or the menu bar, whichever your desktop calls it.

## Install

Needs Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run mangame
```

`uv run mangame` starts the tray. There is no window; everything happens in the
tray menu. Turn on **Start on login** in Settings to have it come back by
itself.

## The menu

**Either mouse button opens it.** An icon in a panel shows nothing but a
picture, so whichever button you try first has to arrive somewhere.

The menu holds verbs only — the things you *do*:

- **Open chapter / Mark as read** — only when there is something to open.
- **Add manga…**
- **Check now**
- **Settings…**
- **Quit**

Nothing nests. Everything with a *value* lives in the settings window instead,
which keeps the menu to one flat list that cannot run off the edge of a screen.

## Settings

**Settings…** opens one window with three tabs:

- **General** — the reading language, whether the panel shows one icon for the
  whole library (and which emblem it wears) or one per manga, new-chapter
  notifications, and start on login (an XDG `.desktop` entry on Linux, an
  `HKCU\...\Run` value on Windows, a LaunchAgent plist on macOS).
- **Manga** — which series get their own tray icon, which emblem each one
  wears, and adding or dropping a series.
- **Artwork** — turn any picture into an emblem; see [Your own
  artwork](#your-own-artwork).

Changes take effect as you make them. Choosing a different reading language
re-opens the window in that language, because it is the menu language too.

## Adding a manga

**Add manga…** opens one window that does the whole job: type a title,
hit Enter, pick a result, choose Add. The field, the results and the outcome
stay on screen, so a search that found the wrong thing is one edit away from
the right one.

Results are grouped by series rather than listed per source. One row reading

```
One Piece (1997)
mangadex · mangaupdates · anilist
```

is one series found by three sources, and Add links all of them — MangaDex
supplies chapter times, AniList supplies the hiatus flag, and a series needs
both to use all three icon states. Anything you already track is greyed out and
labelled, instead of silently doing nothing when you add it twice.

Only sources that can serve your reading language are searched, so every result
is one that can actually be tracked.

## How often it checks

You never set an interval. mangame learns each series' release rhythm from the
timestamps it has already seen, and asks more often the closer the next chapter
gets:

| Situation | Checked about every |
| --- | --- |
| Next chapter more than three days away | a day |
| Three days to twelve hours away | six hours |
| Twelve hours to two hours away | an hour |
| Due within two hours, or overdue by less than twelve | ten minutes |
| Overdue by up to three days | 45 minutes |
| Overdue for a fortnight or more | six hours, then a day |
| A chapter is waiting, unread | twelve hours |
| On an announced break | a day, tightening to 15 minutes as it ends |
| Series finished or cancelled | a week |

Never faster than five minutes, never slower than a week, and never faster than
a source allows. Each series is nudged off its neighbours by a fixed amount
derived from its name, so tracking thirty titles does not fire thirty requests
in the same second. Requests are conditional, so a check that finds nothing new
usually transfers nothing. Timing is by wall clock rather than by sleeping, so
a laptop that suspends overnight catches up the moment it wakes instead of
starting the clock again.

**Check now** in the menu ignores all of that and asks immediately.

## Languages

The three supported languages are the ones the sources can actually be held to:

| Language | Codes asked for | Chapter sources |
| --- | --- | --- |
| English | `en` | MangaDex, MangaUpdates, feeds |
| Español | `es`, `es-la` | MangaDex, feeds |
| Deutsch | `de` | MangaDex, feeds |

Spanish asks for two codes because MangaDex files Latin-American translations
under `es-la`; both are stored as `es`, so you see whichever lands first.

MangaUpdates is English-only on purpose. Its release records carry no language
field and its `lang` filter is silently ignored, so anything else would be an
English scanlation presented as a German one. AniList is asked in every
language: it reports hiatus and status, never chapters, and those are true
whichever translation you wait for.

A per-series `language` in `config.json` overrides the global setting, for the
one title you follow in a different language from the rest.

## Where things are stored

Resolved by `platformdirs`, so they land wherever your OS expects:

| What | Linux | Windows | macOS |
| --- | --- | --- | --- |
| Settings | `~/.config/mangame/config.json` | `%APPDATA%\mangame\config.json` | `~/Library/Application Support/mangame/config.json` |
| Database | `~/.local/share/mangame/state.sqlite3` | `%APPDATA%\mangame\state.sqlite3` | `~/Library/Application Support/mangame/state.sqlite3` |
| Your own artwork | `~/.local/share/mangame/emblems/` | `%APPDATA%\mangame\emblems\` | `~/Library/Application Support/mangame/emblems/` |

On Linux the `XDG_CONFIG_HOME` and `XDG_DATA_HOME` variables are honoured if
you set them.

`config.json` is plain JSON and safe to hand-edit while the app is running —
every poll re-reads it.

## Settings only the file has

Everything in the settings window is in `config.json` too, plus a few things
that are not worth a control:

| Key | Default | What it does |
| --- | --- | --- |
| `max_tray_icons` | `8` | How many icons one-per-manga mode may draw. Past this the rest are simply not shown, so a long library does not fill the panel — switch to one icon for everything instead. |
| `series[].enabled` | `true` | Set to `false` to stop polling a series without dropping what is already known about it. |
| `series[].language` | unset | Overrides the reading language for one title; see [Languages](#languages). |

## Adding a source

Almost every manga site, tracker and publisher blog already publishes an
RSS/Atom feed, and a feed carries the only two things mangame needs: item
titles and publication timestamps. So the built-in `feed` source takes the feed
URL as its reference, and adding a site is a config entry rather than a code
change:

```jsonc
{
  "series": [
    {
      "key": "my-series",
      "title": "My Series",
      "emblem": "onepiece",
      "sources": {
        "feed": "https://example.test/series/my-series/rss"
      }
    }
  ]
}
```

Everything downstream — release rhythm, expected next chapter, break detection,
how often to poll, which icon to draw — is derived from those timestamps. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Your own artwork

**Settings ▸ Artwork** turns any picture into a full emblem. Pick a PNG or SVG
and say which manga it is for; mangame derives the other two states for you:

| State | Derived by |
| --- | --- |
| ready | your picture, unchanged |
| due | luminance, remapped into a mid-grey band |
| break | a flat silhouette with a rim in the opposite tone |

The grey band is deliberate. Plain luminance would render dark artwork almost
black, which is exactly what *break* looks like, and at 16 pixels there is no
detail left to tell them apart by.

**Use for** is preselected from the file name, and says out loud whether it
found anything: a file called `hunterxhunter.png` matches a manga tracked as
`hunter-x-hunter`, and the button then reads **Use for Hunter x Hunter**. If
the name matches nothing — or matches two things equally — it says so and the
button stays disabled until you pick, because artwork silently landing on no
manga at all looks exactly like artwork that worked.

Importing installs the picture *and* gives it to that manga, in one step. Pick
**A shared emblem…** instead to name it yourself and use it for several series;
the list under **Your artwork** shows which manga wears each one, or that none
does yet.

**Break style** picks which way round the silhouette goes — dark shape with a
light rim, or light shape with a dark rim. The preview shows all three states
on a light *and* a dark panel, so you can see which one survives on yours. The
rim is what keeps either choice visible on the other background.

SVGs are re-rendered at every icon size rather than scaled from one bitmap, so
small tray sizes stay crisp. Non-square pictures keep their proportions.

Emblems land in the user emblem directory and can be dropped in by hand too:

```
emblems/<name>/<ready|due|break>/<16|18|20|22|24|32|36|44|48|64|128|256>.png
```

User artwork takes priority over the bundled sets, so you can override
`onepiece` or `book` without touching the installation.

Any series whose emblem is *Generated badge* — or whose artwork has gone
missing — gets a monogram: its initial on a colour derived from the title. Two
untouched series therefore never look alike.

The bundled straw hat, book and M are original work; see
[Development](#development) to redraw them.

## Desktop support

mangame uses Qt's `QSystemTrayIcon`, so it sits wherever the platform puts one:
the notification area on Windows, the menu bar on macOS, the panel on Linux.

On Linux that means the StatusNotifierItem protocol. KDE, XFCE, Cinnamon, MATE
and most tiling-WM bars support it out of the box. **GNOME needs the
[AppIndicator and KStatusNotifierItem](https://extensions.gnome.org/extension/615/appindicator-support/)
extension**, which GNOME does not ship by default; without it no tray icon can
appear, for any application.

Some panels report where they drew the icon and some do not. Where they do, the
menu opens against the icon; where they do not, it opens at the pointer. Either
way it is kept inside the desktop's work area, so it is never left behind a
panel or off the edge of the screen.

## Development

```bash
uv sync --extra dev
uv run pytest                                   # no network, no display
uv run ruff format .
uv run ruff check .
uv run mypy src tests tools                     # also --platform win32 / darwin
uv run pre-commit install
```

The domain layer (`src/mangame/domain/`) is pure: no I/O, no clock, no
network — the current time is always passed in. That is what makes the
release-rhythm, break-detection and scheduling rules directly testable.

The bundled artwork is generated, not committed by hand. `tools/gen_icons.py`
draws each emblem in three palettes and rasterises every tray size; it needs
`inkscape` and ImageMagick's `convert` on `PATH`. Re-run it after editing a
shape or a palette, optionally naming one emblem:

```bash
uv run python tools/gen_icons.py           # all of them
uv run python tools/gen_icons.py mangame   # just the M
```
