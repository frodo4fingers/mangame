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

## Follow-up: one dialog for search and add (2026-08)

Adding a manga was a chain of modal boxes: type a query, wait blind, then pick
from a combo box — and when nothing was found, a combo box containing a single
empty string stood in for an error message. Refining a search meant starting
again from the menu.

- [x] `ui/add_dialog.py` — one window with the query field, the results list,
      a status line and Add/Cancel.
- [x] Results grouped by title, showing which sources back each series, so what
      Add links is visible rather than surprising.
- [x] Series already tracked are greyed out and labelled instead of silently
      doing nothing.
- [x] Empty and failed searches say so in the status line, in place of the fake
      combo box.
- [x] The search only asks sources that serve the reading language.
- [x] Search threads are held until Qt reports them finished, and waited on at
      shutdown.
- [x] `slugify` moved to `store/config.series_key()`, so the dialog decides
      "already tracked" with the identity the store actually stores under.
- [x] 40 new tests; README and architecture doc updated.

### Bugs this removed

1. **Results were mapped back by label string.** `labels.index(chosen)` picked
   the *first* match with that text, so two sources returning the same title
   and year could attach the wrong reference. Rows now carry their index.
2. **A dropped QThread reference.** `self._search` was overwritten by each new
   search; a thread collected while still running takes the process with it.
3. **The no-results dialog was a lie.** `QInputDialog.getItem(..., [""])` is a
   combo box, not a message, and it offered an empty string as a choice.
4. **"Already tracked" was decided by title.** Tracking dedupes by slug, so a
   series stored as "Kagurabachi!" left the search hit "Kagurabachi" looking
   addable — and Add then did nothing at all.

### Verified, not assumed

- Live search for "one piece" returns 41 grouped rows; One Piece itself is one
  row backed by mangadex · mangaupdates · anilist, greyed when already tracked.
- End to end through the real tray: adding Kagurabachi in English links all
  three sources; in German it links mangadex + anilist and the dialog is in
  German. Config written, tray icon created, in both cases.
- The empty state shows the query back with Add disabled and no rows.
- With "Kagurabachi!" tracked, the search hit "Kagurabachi" comes back greyed
  and unselectable, and selection skips to the next row.

## Settings dialog and artwork import

The context menu had grown three levels deep and was no longer maintainable —
and, on a panel at a screen edge, no longer even displayable. Everything with a
*value* moved into one window; the menu kept the verbs.

- [x] `ui/artwork.py`: PNG/SVG → the three icon states.
      - greyscale via Qt's gamma-correct `Grayscale8`, remapped into a mid band
        so dark artwork cannot come out looking like a break
      - silhouette in a dark or a light tone, each ringed in the opposite one,
        with the artwork inset by exactly the rim it grows
      - install/uninstall into the user emblem directory, invalidating the
        memoised `icon_for`
- [x] `ui/settings_dialog.py`: General / Manga / Artwork, applying as you go.
- [x] Tray menu flattened to verbs only: header, Open, Mark read, Add, Check
      now, Settings…, Quit. No submenus at all.
- [x] `Settings.with_series_change()` / `.without_series()`, so the tray and the
      dialog edit the series list the same way.
- [x] 96 new tests, including the dialogs driven for real on Qt's offscreen
      platform. README and architecture doc updated.

### Bugs this removed

1. **The generated monogram was unreachable.** `icon_for` fell back to the
   bundled `book` before it ever reached the monogram, and `emblem_for()` hands
   every series but One Piece the name `"monogram"` — so every one of them wore
   the identical book icon. Missing artwork now falls back to the monogram, and
   `book` is just another emblem you can pick.
2. **A dialog emitting from a stale copy.** Each change was built from the
   settings the dialog opened with, so turning off notifications and then
   changing an emblem silently turned notifications back on.
3. **A truncated emblem column.** The picker was sized by the header, clipping
   "Generated badge" — and every translation of it.

### Verified, not assumed

- The One Piece SVG imported as `luffy-hat` writes all 12 sizes for all three
  states in ~180 ms, and is selectable for a series immediately afterwards.
- Screenshots of all three tabs, in English and German, plus the preview strip
  zoomed: colour → mid-grey → silhouette, each shown on a light and a dark
  panel. Both tones stay legible on both backgrounds.
- The live tray menu is **flat** — 7 entries, no submenus — for a ready series
  and 5 for a waiting one.
- Kagurabachi and Sakamoto Days now show distinct pink "K" and green "S"
  badges where both previously showed the same book.
- The stale-copy regression tests were confirmed to fail against the old code.

### Follow-up: flat chrome for the settings dialog

- [x] Measured the inset before touching it: dialog layout 11 + tab pane frame
      2 + page layout 11 = 24px around every control. Now 12.
- [x] `setDocumentMode(True)` removes the pane, so the tab labels and the page
      content align to the same edge.
- [x] Group boxes → bold labels. Fusion draws a flat group box's frame anyway,
      which was verified by rendering both.
- [x] Table and list frames removed, grid lines off, header sections no longer
      highlight.
- [x] Preview cells given a fixed width and a reserved height — without the box
      the captions decided the widths, so the row was ragged and jumped when a
      picture was chosen. German wraps to two lines and still lines up.
- [x] 6 regression tests, each confirmed to fail against the previous layout.

## Importing artwork says which manga it found

Found in the user's own data: artwork imported as `hunterxhunter` while the
series is keyed `hunter-x-hunter`, so Hunter x Hunter still wore the generated
badge. The import wrote 36 files, reported success and changed nothing visible.

- [x] The Name field became a **Use for** picker over the tracked manga,
      preselected by matching the file name.
- [x] `squash()` compares titles, keys and file names on letters alone, so
      punctuation cannot be the reason an import lands nowhere.
- [x] `match_series()` refuses to guess between two candidates — an ambiguous
      name is not a match.
- [x] `NameMatch` names the outcome, and the sentence, the button label, the
      visible fields and whether the import works are derived from it in one
      place.
- [x] Importing installs **and** assigns, in one action.
- [x] "Your artwork" says which manga wears each emblem, or that none does.
- [x] The empty tab hides the verdict row and the preview block instead of
      reserving holes for them.
- [x] 39 new tests; README and architecture doc updated.

### Bugs this removed

1. **A silent no-op import.** The only feedback was "Added “x”. Pick it for a
   series under Manga." — which reads like success whether or not the name
   meant anything to the app.
2. **A stale suggested name.** The name was filled in only when the field was
   empty, so choosing a second picture kept the first one's name and would
   have filed it under the wrong emblem.
3. **The installed list was keyed by its own label.** Removing an emblem read
   the item's text, which now carries the wearer too; the name comes from the
   item's data instead.

### Verified, not assumed

- `hunterxhunter.svg`, `Hunter X Hunter.svg` and `onepiece-hat.svg` all match;
  `bleach-logo.svg` matches nothing, says so in bold, and cannot be imported
  until a manga is picked.
- End to end through the real tray: pick the file, one click, config on disk
  says `emblem='hunter-x-hunter'`, and the tray icon's pixels change.
- Screenshots of all four states in English and German.

## Keeping the network off the startup path

Asked whether Python was the right language for a tray app. Measured instead of
guessed: Qt is ~48 MB of the resident set and is language-independent, so a
rewrite that keeps Qt saves a third of memory for a total rewrite. The two
costs that were *actually* misplaced were both in `sources/http.py`.

- [x] `import httpx` moved inside the methods that use it, with a
      `TYPE_CHECKING` import for the annotations.
- [x] `HttpClient` opens its connection pool on first request, not in its
      constructor, and exposes `connected` so this is observable.
- [x] `aclose()` no longer opens a pool purely to close it.
- [x] 10 tests, 9 of which fail against the previous code.

### Measured, in a controlled A/B against the stashed old code

| | Old | New |
| --- | --- | --- |
| time to visible tray | 825 ms | 668 ms |
| `SourceRegistry()` | 354 ms, +10.2 MB | 0.6 ms, +0.04 MB |
| httpx loaded at tray-visible | yes | no |
| real app, fresh, same age | 96.2 MB | 85.4 MB |

The repeated cost turned out to be the interesting one: `SearchWorker` builds a
registry per search, so every search paid ~350 ms opening four TLS contexts and
then skipped the sources that could not serve the reading language anyway.

### Rejected after measuring

- **Rewriting in Rust/Go.** Keeps Qt, so it saves ~40 MB of 122 for a total
  rewrite. Dropping Qt reaches ~8 MB but the settings dialog — now the centre
  of the app — would need building three times.
- **Rendering fewer icon sizes.** `QIcon.addFile` is already lazy; twelve sizes
  cost ~11 kB, not twelve bitmaps. The claim was wrong before it was measured.

## The app gets a mark of its own, and you choose which picture you get

The aggregate tray icon wore One Piece's straw hat — hardcoded in
`_render_single` — so a library of thirty titles looked like one of them.

- [x] `tools/gen_icons.py` draws a third bundled emblem, `mangame`: a heavy M,
      in the same three palettes as the hat and the book.
- [x] `Settings.tray_emblem` points the aggregate icon at any installed emblem,
      imported artwork included. Defaults to the M.
- [x] The General tab's checkbox became a pair of radios — one icon for
      everything, or one per manga — with the emblem picker on the first row,
      greying out with it.
- [x] Four new catalogue keys in all three languages; the German and Spanish
      dialogs were rendered and checked for clipping.
- [x] `tests/test_tray.py` is new: it builds a real tray against a throwaway
      config and compares rasterised icons.

### The M needed measuring, not looking at

Drawn at the family's proportions it looked fine and was wrong. A letter has
far less area per unit of outline than a hat, so the *break* state came out
39% dark pixels against 59% (hat) and 66% (book) — an outline drawing where
the others are silhouettes.

| | ready | due | break |
| --- | --- | --- | --- |
| straw hat | median 0.51, sat 0.72 | 0.57, sat 0 | 0.14, 59% dark |
| book | 0.48, sat 0.74 | 0.53, sat 0 | 0.14, 66% dark |
| M, first cut | 0.29, sat 0.75 | 0.36, sat 0 | **0.51, 39% dark** |
| M, shipped | 0.48, sat 0.74 | 0.53, sat 0 | 0.14, 67% dark |

Fixed by fattening the stems and by `paint-order="stroke fill"`, which puts the
outline behind the fill so only its outer half shows; the stroke is doubled to
6 to keep the visible rim the width the family uses.

### Verified

- 459 tests, ruff and mypy clean on linux, win32 and darwin.
- The three aggregate-icon tests fail against the previous commit, and the two
  "reported once" tests fail if the second radio is also connected.
- The real app, on the real config, screenshotted in the real panel: the M in
  aggregate mode, two series icons in per-manga mode, and the book after
  pointing `tray_emblem` at it.
