# Architecture

Two questions shaped every decision here:

1. How do you cover a **huge variety of sources** without a maintenance sink?
2. How do you notice a release **promptly** without hammering anyone's API?

## 1. Sources only report timestamps

The adapter contract (`sources/base.py`) is deliberately tiny. A source answers
two questions:

- which chapters of this series exist, and when were they published?
- can you find this series by name?

That is the cheapest thing any API, RSS feed or scraped page can offer.
*Everything* else is derived in `domain/`:

```
timestamps ─▶ cadence.estimate()   ─▶ release rhythm
           ─▶ cadence.expected_next() ─▶ when the next one is due
           ─▶ breaks.*             ─▶ is a break announced?
           ─▶ state.resolve()      ─▶ which icon to draw
           ─▶ schedule.decide()    ─▶ when to look again
```

Adding a source therefore never touches the scheduler, the break logic or the
UI. And because RSS/Atom is nearly universal, `sources/feed.py` accepts any feed
URL as its reference — most new sites cost a config line, not a release.

### Source tiers

| Tier | Source | Role | Cost |
| --- | --- | --- | --- |
| Sweep | MangaDex `/manga?ids[]=` | status + a change watermark for **100 series in one request** | ~1 request/day for a whole library |
| Detail | MangaDex feed, RSS/Atom | actual chapter timestamps | only when the watermark moved, or in the hot window |
| Status | AniList GraphQL | `RELEASING` / `HIATUS` / `FINISHED`, **aliased 40 series per query** | 1 request per sweep |
| Cross-check | MangaUpdates `/series/{id}` | `latest_chapter` watermark | 1 cheap request per series |

MangaUpdates' `/v1/releases/days` firehose is deliberately *not* used: it returns
roughly nine thousand releases per day, which costs far more than polling the
handful of series a user actually tracks.

### Search and poll ask the same sources

The add dialog searches only sources that serve the reading language, for the
same reason the poller skips them: a hit from a source that cannot answer in
your language would add a series nothing ever reports on. Results are then
grouped by title — the same normalisation the tray uses to cross-link matches —
so the row you pick lists exactly the sources that Add will attach.

### Reading language decides who is asked

The `Language` setting is the language you *read* in, not a label switch. It
picks the sources that are polled and the chapters that count as ready, so
`i18n/languages.py` — a three-entry registry of English, Spanish and German —
sits underneath both the source layer and the settings.

Each adapter declares `Capabilities.languages`, and `serves(language)` is true
when the language is in that set **or** the source carries no chapter
timestamps at all. Status-only sources are language-independent by nature: a
hiatus is a hiatus whichever translation you are waiting for. `_due_work()`
skips any source that does not serve the configured language, so a German
reader never spends a request on an English-only index.

Two things this exposed, both now fixed:

- **MangaUpdates cannot attribute language.** It used to stamp releases with
  whatever language was *requested*. Its release records are only
  `{id, title, volume, chapter, groups, release_date, time_added}`, and passing
  `lang` to `/v1/releases/search` is silently ignored — identical hit counts
  either way. So it declares English and stamps English. It is kept rather than
  demoted to status-only because MangaDex's English feed for licensed series
  only covers the free window, and MangaUpdates' long release history is what
  makes English cadence learning work.
- **The sweep watermark is language-blind.** MangaDex's `latestUploadedChapter`
  moves for *any* translation, so after switching language the watermark is
  unchanged and the batch sweep would short-circuit to "nothing changed" — the
  new language's chapters would never be fetched. `clear_due()`, which is both
  the "check now" path and the language-switch path, now clears ETag,
  `Last-Modified` and watermark along with the due time.

Language tags are folded at the boundary, not at the point of use: adapters
canonicalise on the way in and settings validate on load, so `es-la` from
MangaDex and `es_MX.UTF-8` from an OS locale both become `es`. That is why
Spanish asks MangaDex for `es` **and** `es-la` in one request but stores one
code, and why `chapters_for(language=...)` can be an exact match rather than a
prefix dance.

A source the user pointed at themselves is treated differently from an index
mangame queries: `feed` accepts every language, because choosing a German feed
URL *is* the assertion that it carries German.

### Source quirks that are handled

- **MangaDex's 2037 sentinel.** MANGA Plus-linked chapters carry
  `publishAt = 2037-12-31` to hide official schedules. Taken at face value it
  would put every simulpub series on a twelve-year break, so future dates are
  only believed inside `MAX_ANNOUNCE_HORIZON` (180 days) — and when they are
  believed, they become the strongest break signal available.
- **Backfills.** Aggregators upload old chapters long after the fact; MangaDex
  carries One Piece 1–3 stamped *months after* chapter 1148. Ordered by time
  that looks like a brand-new release, so `_forward_run()` keeps only the
  trailing stretch where publish time rises with chapter number.
- **Coverage holes.** A source that has chapter 1148 and 1189 and nothing
  between is not reporting a fourteen-month break. Intervals spanning more than
  `MAX_NUMBER_STEP` chapters are discarded rather than guessed at; small skips
  are divided by the number of chapters they span.
- **Multi-chapter dumps.** Anything inside `BATCH_WINDOW` (18h) is one release,
  not several, so a catch-up dump cannot masquerade as a daily cadence.

## 2. Cadence is learned, not configured

`domain/cadence.py` derives the rhythm from publication times alone, using a
two-pass median so one skipped week cannot drag the period, then snapping to
the cadences publishers actually use (weekly, fortnightly, monthly…). Weekly
rhythms also learn their weekday and hour, so a chapter that slips a few hours
does not permanently shift the schedule.

A cadence is only *trusted* (`is_known`) once it has at least two intervals.
One sample is measured and displayed but never drives tight polling — for a
sparsely covered series the honest answer is "no rhythm known", and the
scheduler falls back to a calm twice-daily check.

Verified against live data: Kagurabachi is learned as weekly/Sunday
(confidence 0.87) and Boushoku no Berserk as fortnightly/Tuesday (0.94), while
a series where the source only carries omake chapters correctly reports no
rhythm at all.

## 3. Break detection is ranked by trust

`domain/breaks.py`, strongest first:

1. **Publisher-stated next date** that is meaningfully later than the rhythm
   predicts. Stated outright → `HIGH`.
2. **Explicit hiatus flags** (AniList `HIATUS`, MangaUpdates). → `HIGH`.
3. **Magazine skip calendars** (combined issues, Golden Week, New Year) —
   one entry covers every series a magazine carries. → `MEDIUM`.
4. **Silence.** → `LOW`, and deliberately *never* enough to blacken the icon.

Only `HIGH`/`MEDIUM` windows turn the icon black. An inferred break shows up in
the tooltip as "possibly on an unannounced break" and leaves the icon grey,
because black means *announced* — a promise the app should not make on a guess.

Status is ranked across the sources in a single poll, never across polls: doing
the latter would make `HIATUS` a ratchet that no later "ongoing" could undo, and
a series that came back would stay black forever.

## 4. Icon state: READY > BREAK > DUE

`domain/state.py`. The precedence is the whole product in one rule: "is there
something to read?" always wins. An announced break does not make a freshly
published chapter less readable — only once you are caught up does the icon go
black to say the next slot is cancelled.

## 5. Polling tightens as the due date approaches

`domain/schedule.py` is a ladder, most specific first:

| Tier | When | Interval |
| --- | --- | --- |
| `ended` | completed/cancelled | 7 d |
| `unread` | a chapter is already waiting | 12 h |
| `break-openended` | indefinite hiatus | 24 h |
| `break` / `break-closing` / `break-ending` | announced break, by how close the end is | 24 h / 3 h / 15 min |
| `unknown-cadence` | no rhythm learned yet | 12 h |
| `far` / `approaching` / `near` / `imminent` | >3 d / >12 h / >2 h / due soon | 24 h / 6 h / 1 h / 10 min |
| `hot` / `late` / `stalled` / `dormant` | overdue by <12 h / <3 d / <14 d / more | 10 min / 45 min / 6 h / 24 h |

On top of the ladder:

- **Deterministic jitter** of ±12%, derived from `blake2s(series_key:tier)`, so
  thirty tracked series do not fire thirty requests in the same second — and so
  a restart does not re-stampede.
- **Error backoff** that can only ever slow things down, never speed them up.
- Floors and ceilings: never faster than 5 minutes, never slower than 7 days,
  and never faster than the source's own `min_interval`.

Two properties matter more than the exact numbers:

- **Absolute wall-clock due times, not sleeps.** A laptop that suspends for a
  day notices what it owes the instant it wakes.
- **Conditional requests.** ETag/Last-Modified are stored per (series, source)
  and replayed, so most polls are a 304 that costs almost nothing. That is what
  makes the 10-minute hot window affordable in the first place.

## 6. Three states from one picture

`ui/artwork.py`. Bundled emblems are drawn three times from three palettes;
anything a user imports is one picture, so *due* and *break* have to be derived.

- **Greyscale** leans on Qt's `Grayscale8` conversion, which is a gamma-correct
  Rec. 709 luminance — it linearises, weights, then re-encodes — and then
  remaps the result into a mid band (0.34–0.86). Plain luminance would be
  honest and useless: dark artwork would come out almost black, which is
  exactly what *break* looks like, and at 16 pixels there is no detail left to
  distinguish them by. The band is what guarantees the states are told apart.
- **Silhouette** flattens everything opaque to one tone and rings it in the
  opposite one, matching the palettes `tools/gen_icons.py` uses. A dark
  silhouette vanishes on a dark panel and a light one vanishes on a light
  panel, so the rim is what makes either choice survive the other background.
  It is grown by stamping the alpha mask across a disc of offsets and punching
  the original shape back out — draw calls rather than a pixel loop — and the
  artwork is inset by exactly the rim width so the halo is never clipped.

Everything works on `QImage`, which needs no display, no `QApplication` and no
window system. That is what keeps the live preview cheap (a full 12-size,
3-state import takes under 200 ms) and lets the pixel assertions in
`tests/test_artwork.py` be the real thing.

Missing artwork falls back to the **monogram**, never to another emblem. A
generated badge still says which series it is; a shared stand-in would make
every untouched series look identical — which is precisely the bug that
existed while `"monogram"` silently resolved to the bundled `book`.

## 7. Layers

```
ui/          Qt tray, dialogs, artwork, worker threads   ← the only Qt-aware code
service/     library, poller, autostart          ← orchestration
sources/     adapters + HTTP plumbing            ← the only network code
store/       SQLite + JSON settings              ← the only persistence
domain/      models, cadence, breaks, state, schedule
i18n/        reading languages + menu catalogues
```

`domain/` is pure: no I/O, no network, and no clock — `now` is always a
parameter. That is what makes 380 tests run in under seven seconds with no
network access, and it is why the rules above can be asserted directly rather
than inferred from behaviour.

The same split is applied inside `ui/`: the parts worth asserting are pulled
out of the widgets. `menu.fitted_position()` clamps a popup into the work area,
`add_dialog.group_matches()` decides which rows the add dialog shows, and every
transform in `artwork.py` is a plain function over images. The dialogs
themselves are driven for real, on Qt's offscreen platform, because their
interesting failures are wiring failures — a checkbox connected to nothing
looks fine in a screenshot.

### Menus hold verbs, dialogs hold values

The tray menu was once three levels deep (Manga ▸ Stop tracking ▸ a series).
That is slow to reach, and on a panel pinned to a screen edge Qt would size the
popup against the screen rather than the work area and run it off the display.
`menu.fitted_position()` clamps that, but the real fix was structural: the menu
now lists only actions, and everything with a value lives in
`ui/settings_dialog.py`. A flat list of verbs cannot overflow.

The dialogs own no services. They emit what the user asked for and are handed
settings back, which is what lets them be tested without a poller, a database
or a display. Two rules make that loop safe:

- A dialog updates **its own copy** as it emits. Emitting from the copy it
  opened with would mean a second edit silently reverts the first.
- Echoing saved settings back in is guarded, or the echo re-enters as a fresh
  edit and loops.

The chrome is flat, and mostly by subtraction. Qt stacks three insets by
default — the dialog's layout, the tab widget's pane frame and each page's
layout — which put 24px between every control and the window edge. Document
mode drops the pane, the pages carry no horizontal margin of their own, and the
dialog's single margin is the one the tab labels already align to. Group boxes
are labels instead: Fusion draws a box's frame even when the box is asked to be
flat, and another frame is exactly what was being removed.

Threading: `PollWorker` and `SearchWorker` are `QThread`s that each run their
own asyncio loop and open their **own** SQLite connection (connections are not
shareable across threads; WAL makes concurrent use safe). `PollWorker` re-reads
settings every tick, so there is no shared mutable state between threads at all.

## Technology choices

- **PySide6 `QSystemTrayIcon`** — actively maintained by the Qt Company, real
  release cadence, LGPL, runtime `setIcon()` swapping, checkable menu items, and
  better macOS behaviour than the Python alternatives. `pystray` was rejected:
  no PyPI release since September 2023, it blocks the macOS main thread, and it
  reports `HAS_MENU = False` on some Linux backends.
- **Plain `sqlite3` over SQLAlchemy + Alembic** — four tables, one local file,
  and binary size matters for something that sits in a tray all day.
- **JSON over TOML for settings** — the stdlib both reads *and* writes JSON;
  `tomllib` is read-only, and a hand-rolled writer is a bug farm.
- **Pydantic models throughout** — validation at the edges (API payloads,
  config files, the database) is exactly where the untrusted data is.
