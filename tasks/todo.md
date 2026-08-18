# mangame — build plan

## Goal

A cross-platform system-tray app (Linux/Windows/macOS) with a manga-themed icon
that is **black** when a break is announced, **grey** when the week is due for a
release, and **full colour** when something is ready to read. Minimal menu:
language, which manga appear in the tray, start on boot/login. Cover a wide
variety of sources with minimal daily scanning effort, and poll harder as a due
date approaches.

## Plan

- [x] Research forkable projects on GitHub
- [x] Research manga data sources and their real API shapes
- [x] Evaluate the cross-platform tray stack
- [x] Design the source/domain split
- [x] Generate original tray artwork for three states
- [x] Scaffold the uv project (ruff, mypy strict, pytest)
- [x] Domain layer: models, cadence, breaks, state, schedule
- [x] Source adapters: MangaDex, AniList, MangaUpdates, generic RSS/Atom
- [x] Store: SQLite + JSON settings
- [x] Service: library, poller, autostart
- [x] i18n catalogue (7 languages)
- [x] Qt tray UI and worker threads
- [x] Entry point
- [x] Test suite
- [x] Verify live end-to-end against real APIs
- [x] Pre-commit, README, architecture docs

## Findings from research

**No forkable project exists.** The closest matches were all dead or wrong-shaped:
`xgi/houdoku` (Java reader, unmaintained since Dec 2024), `olback/tray-item-rs`
(dead), `Ayaan3216/Manga-Notifier` (no licence, Windows-only).
`Kevinsillo/discord-voice-tray` was useful only as a reference for icon-state
swapping. Built from scratch.

**Stack:** PySide6 `QSystemTrayIcon`. Runner-up Tauri v2, which only wins if
binary size is paramount. `pystray` eliminated — no release since Sept 2023,
blocks the macOS main thread, `HAS_MENU = False` on some Linux backends.

**Sources:** verified live before writing any adapter. MangaDex `/manga?ids[]=`
takes 100 ids per request and returns status plus a change watermark, which is
the cheap daily sweep. AniList aliases 40 series into one GraphQL query.
MangaUpdates' `/releases/days` firehose returns ~9000 rows/day and was rejected
as more expensive than per-series polling.

## Review

### What was built

39 source files, 199 tests, clean on ruff and on mypy `--strict` for all three
platforms (`linux`, `win32`, `darwin`).

The load-bearing idea: **a source only ever reports "which chapters exist and
when were they published"**. Cadence, expected-next, break detection, poll
pacing and icon state are all derived from that in a pure `domain/` layer. This
is what makes "huge variety of sources, minimal effort" tractable — and the
generic RSS/Atom adapter means most new sites cost a config line, not a release.

### Bugs found by writing tests, and fixed

1. **Backfills read as fresh releases.** MangaDex carries One Piece chapters 1–3
   stamped *months after* chapter 1148. Ordered by time, that backfill looked
   like a new release and produced a 154-day "cadence". Fixed with
   `_forward_run()`, which keeps only the trailing stretch where publish time
   rises with chapter number.
2. **Coverage holes read as breaks.** With the backfill gone, the gap between
   chapters 1148 and 1189 still produced a 222-day period. A source missing 41
   chapters is not reporting a fourteen-month break. Intervals are now
   number-aware: small skips are divided by the chapters they span, large ones
   are dropped. One Piece then reports one honest 11-day sample and, because a
   single sample is not trusted, falls back to a calm twice-daily check.
3. **A series could never come off hiatus.** `_merge_learned` seeded its status
   ranking from the *previous* status, making `HIATUS` a ratchet that no later
   "ongoing" could undo — the icon would have stayed black forever. Status is
   now ranked only within a single poll, with sources that answer "unknown" not
   voting.
4. **`pt-BR` and OS locales fell back to English.** The catalogue key is
   `pt-br`, so the conventional casing silently lost the translation. Added
   `normalize()`, which also degrades `de_DE.UTF-8` → `de`.
5. **Dead guard** in `state._tooltip` (`isinstance(x, object)` is always true).
6. **`menu.setParent(tray_icon)`** — `QSystemTrayIcon` is not a `QWidget`.
   Menus are now held in a dict so Python cannot collect one Qt is showing.

### Verified, not assumed

- Tray icon appears and the menu renders on this KDE/X11 machine, with exactly
  the four top-level entries the brief asked for.
- A real poll of One Piece across MangaDex + MangaUpdates + AniList returns
  chapter 1190 (2026-08-09), resolves to READY, and re-arms all three sources.
- Cadence learning on live data: Kagurabachi → weekly/Sunday (0.87),
  Boushoku no Berserk → fortnightly/Tuesday (0.94), an omake-only series →
  correctly no rhythm.
- mypy passes under `--platform win32` and `--platform darwin`, so the Windows
  registry and macOS LaunchAgent paths are type-checked despite being written
  on Linux.

### Deliberately not done

- **MANGA Plus adapter.** Its API returns protobuf and `format=json` now 403s.
  It would need a protobuf decoder for one source; the RSS escape hatch covers
  the same ground for now.
- **Packaged binaries.** Nuitka/PyInstaller builds and per-OS installers are a
  release concern, not a correctness one.
- **Magazine skip calendars.** The break-confidence ranking already has a slot
  for them (`MEDIUM`); no calendar data source is wired up yet.

## Follow-up: the reading language (2026-08)

The `Language` menu was built as a UI-label switch. It was meant to be the
language the *manga* is read in — which sources get polled, and which chapters
count as ready. Scope narrowed to English, Spanish and German.

- [x] `i18n/languages.py` — a registry of the three languages, each a canonical
      code plus the source codes it covers (`es` → `es`, `es-la`).
- [x] Catalogues trimmed to the languages we can actually poll for; the menu no
      longer offers French, Portuguese, Italian or Japanese.
- [x] `Capabilities.languages` + `serves()`, declared per adapter.
- [x] MangaDex asks for every code of the chosen language in one request and
      folds `es-la` → `es` on the way in.
- [x] MangaUpdates declared English-only; it no longer stamps releases with the
      requested language.
- [x] The poller skips sources that cannot serve the configured language.
- [x] `clear_due()` clears validators and watermarks, so a language switch is
      not answered "nothing changed".
- [x] Settings normalise language tags on load (`ReadingLanguage`).
- [x] The tray links only sources that serve the language, and switching
      language forces an immediate re-check.
- [x] 46 new tests; docs updated.

### Bugs this exposed

1. **MangaUpdates mislabelled every release.** `_chapter_from()` stamped the
   *requested* language onto records that carry no language at all. Verified
   against the live API: release records are only
   `{id, title, volume, chapter, groups, release_date, time_added}`, and
   `/v1/releases/search` ignores `lang` — 9832 hits with or without it. A German
   reader would have been told a German chapter landed on the strength of an
   English scanlation.
2. **The sweep watermark is language-blind.** `latestUploadedChapter` moves for
   any translation, so after a language switch the watermark is unchanged, the
   batch sweep reports `unchanged`, and the new language's chapters are never
   fetched.
3. **Spanish needs two codes.** MangaDex lists both `es` and `es-la` for the
   same series; One Piece has 14 chapters under `es` and its Latin-American
   translations under `es-la`. Asking for one code hides the other.

### Verified, not assumed

- Live MangaDex per-language totals for One Piece (en 6, de 6, es 14, pt-br 68),
  and that a multi-value `translatedLanguage[]` request returns HTTP 200.
- `availableTranslatedLanguages` lists 24 codes including both Spanish variants.
- MangaUpdates returns identical `total_hits` with and without a `lang`
  parameter, which is what the English-only declaration rests on.
