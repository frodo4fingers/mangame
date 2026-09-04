# Configuration

Everything the settings window can do, `config.json` can do too — plus a few
things that are not worth a control. This is the reference; the
[README](../README.md) is the tour.

## Where things are stored

Resolved by `platformdirs`, so they land wherever your OS expects:

| What | Linux | Windows | macOS |
| --- | --- | --- | --- |
| Settings | `~/.config/mangame/config.json` | `%APPDATA%\mangame\config.json` | `~/Library/Application Support/mangame/config.json` |
| Database | `~/.local/share/mangame/state.sqlite3` | `%APPDATA%\mangame\state.sqlite3` | `~/Library/Application Support/mangame/state.sqlite3` |
| Your own artwork | `~/.local/share/mangame/emblems/` | `%APPDATA%\mangame\emblems\` | `~/Library/Application Support/mangame/emblems/` |
| Logs | `~/.local/state/mangame/log/mangame.log` | `%APPDATA%\mangame\Logs\mangame.log` | `~/Library/Logs/mangame/mangame.log` |
| Start on login | `~/.config/autostart/mangame.desktop` | a value under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` | `~/Library/LaunchAgents/io.mangame.agent.plist` |

Start on login is per-user everywhere, so enabling it never needs an
administrator, and clearing the checkbox removes the entry again.

On Linux the `XDG_CONFIG_HOME`, `XDG_DATA_HOME` and `XDG_STATE_HOME` variables
are honoured if you set them.

`config.json` is plain JSON and safe to hand-edit while the app is running —
every poll re-reads it.

## Pointing mangame somewhere else

Set `MANGAME_HOME` to put settings, database, logs and artwork in one directory
of your choosing instead — for a portable copy on a USB stick, or to run a
second instance without disturbing the first. It works the same on all three
platforms:

```bash
MANGAME_HOME=/media/stick/mangame mangame
```

Three variables move things around, and a `.env` file is a convenient place to
keep them:

| Variable | What it does |
| --- | --- |
| `MANGAME_HOME` | Settings, database, logs and artwork all in this one directory. |
| `MANGAME_EMBLEM_DIR` | Imported artwork here, wherever the rest lives. |
| `MANGAME_ENV_FILE` | Read those from this file instead of a `.env`. |

Copy [`.env.example`](../.env.example) to `.env` and uncomment what you need.
mangame reads the first one it finds:

1. `$MANGAME_ENV_FILE`, if you set it
2. `.env` in the current directory — handy when running from a clone
3. `.env` beside the executable — a portable install carries its own
4. `.env` in the configuration directory above — the only one a copy started
   at login will find, since it has no meaningful working directory

A variable already set in the real environment always wins over the file, so
the one-off above keeps working. `.env` is git-ignored: nothing about your
setup belongs in the repository.

## Settings only the file has

| Key | Default | What it does |
| --- | --- | --- |
| `max_tray_icons` | `8` | How many icons one-per-manga mode may draw. Past this the rest are simply not shown, so a long library does not fill the panel — switch to one icon for everything instead. |
| `series[].enabled` | `true` | Set to `false` to stop polling a series without dropping what is already known about it. |
| `series[].language` | unset | Overrides the reading language for one title, for the one series you follow in a different language from the rest. |

## Adding a source without writing code

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
[ARCHITECTURE.md](ARCHITECTURE.md).

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

## Languages in detail

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
