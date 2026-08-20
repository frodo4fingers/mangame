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

### The aggregate icon has a mark of its own

One icon for the whole library used to wear One Piece's straw hat, hardcoded,
so a shelf of thirty titles looked like one of them. It now wears `mangame`, a
letter M — the aggregate must not look like a member of the set it aggregates,
which rules out every object and leaves a monogram.

Not the *generated* monogram, though: that one takes its letter and its hue
from a series title, and this icon stands for all of them. So the M is bundled
artwork like the hat and the book, drawn by `tools/gen_icons.py` in the same
three palettes, and `Settings.tray_emblem` may point at any installed emblem
instead — including imported artwork.

Two details are load-bearing, and both were found by measuring rather than by
looking:

- **The stems are fat.** A letter has far less area per unit of outline than a
  hat or a book. Drawn at the family's proportions the *break* state — a dark
  body with a light rim — came out only 39% dark pixels against 59% and 66%
  for the other two: an outline drawing, not a silhouette.
- **`paint-order="stroke fill"`** puts the outline behind the fill, so only its
  outer half shows and the body stays solid. The stroke is doubled to 6 to
  keep the *visible* rim the same width as everywhere else.

`TestAppMark` in `tests/test_ui_support.py` pins this by comparing the mark's
median lightness and mean saturation against the series artwork, so the
threshold moves with the family instead of being a number someone once typed.

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
parameter. That is what makes 459 tests run in under ten seconds with no
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

Both buttons raise it. A tray icon has no affordance but its picture, so the
button someone tries first has to lead somewhere, and once the values moved out
there is only one somewhere left. The left button used to open the newest
chapter when one was waiting — invisible (nothing says an icon is clickable,
let alone that it is clickable *sometimes*) and, in aggregate mode, dead, since
the state it consulted is only recorded per series. `Context` stays unhandled:
the platform raises the menu for the right button itself.

Where the menu appears is `menu.menu_anchor()`. StatusNotifierItem hosts — KDE's
panel, GNOME's AppIndicator extension — draw the icon in their own process and
report an empty rectangle to Qt, so the pointer is the only anchor available
there; Windows and macOS report a real one and get the menu lined up with the
icon. `fitted_position` then lifts it clear of the panel either way.

An open menu is never rebuilt. `refresh()` runs every minute and re-derives
each icon's menu; swapping the object drops the last Python reference to the
one on screen, and Qt deletes it under the pointer. A minute of staleness is
the cheaper failure, and the better behaviour besides — items do not move while
you are reaching for them.

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

### The tray mode is two pictures of a library, not a switch

"One icon for the whole library" was a checkbox. It reads as a feature you can
turn on, which invites the question "on top of what?" — but the two settings
are alternatives: either the panel shows one icon or it shows several. A pair
of radios states that; a checkbox hides it.

The emblem the aggregate icon wears sits *on* the one-icon row and greys out
with it. A control that cannot apply says so by being unavailable rather than
by being explained in a sentence beside it, and putting it on the row makes it
obvious which option it belongs to. The remaining hint is indented to the
radio's *label*, measured from `QStyle.PixelMetric.PM_ExclusiveIndicatorWidth`
because the indicator's width is a platform decision, so it attaches to one
option instead of floating under the group.

Only `_one_icon.toggled` is connected. Both radios move on every click, so
reacting to both would save the same change twice.

### Importing artwork asks which manga, not what to call it

The artwork tab used to ask for a *name*. That is a file system's question, not
the user's: nobody wants an emblem, they want their manga to look like
something. Naming it left the actual job — picking it in the Manga tab — as an
unmentioned second step, and skipping that step was invisible. Artwork saved as
`hunterxhunter.png` for a series keyed `hunter-x-hunter` installed perfectly
and changed nothing, because a hyphen is not something a file name is expected
to get right.

So the tab asks which manga instead, preselected by matching the file name, and
importing installs *and* assigns in one action. Three rules make the guess
safe:

- **Compare on squashed letters.** `series_key` turns punctuation into
  separators, which is right for an identity and too strict for recognising a
  file. Dropping every non-alphanumeric makes `hunterxhunter`,
  `hunter-x-hunter` and `Hunter x Hunter` the same word.
- **Ambiguity is not a match.** Two candidates mean the file name decided
  nothing. Guessing between them attaches artwork to the wrong manga, and
  nothing afterwards looks wrong enough to notice.
- **Say what was found, and let the button carry it.** The verdict line names
  the manga; the button reads *Use for Hunter x Hunter*. A confirmation you
  have to click past is one you cannot skim past — which a message beside the
  field always was. When nothing matches, the button is disabled rather than
  merely discouraged: the wrong action is unavailable, not just unlabelled.

`NameMatch` names the outcome — idle, matched, chosen, none, shared — and the
sentence, the button's label, which fields are visible and whether the import
works are all derived from it in one place, so they cannot disagree.

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

### Nothing on the way to a visible icon pays for the network

A tray app is judged on resident memory, because it is measured while doing
nothing. Two costs used to land on the startup path without being needed there,
both in `sources/http.py`:

| | Cost | Now paid |
| --- | --- | --- |
| `import httpx` | ~3.4 MB, ~140 ms | first request |
| `httpx.AsyncClient` × 4 (one per adapter) | ~10.2 MB, ~350 ms | first request *to that source* |

Neither belonged there. The GUI imports `mangame.sources` to ask a *metadata*
question — which adapters serve which reading language — and metadata needs no
transport. So `httpx` is imported inside the two methods that genuinely use it,
with a `TYPE_CHECKING` import for the annotations, and each `HttpClient` opens
its pool on first request rather than in its constructor.

The second one matters more than its size suggests, because it is paid
repeatedly. `SearchWorker` builds a fresh `SourceRegistry` for **every** search
and then deliberately skips sources that cannot serve the reading language — but
the constructor had already opened a pool for each of them. Searching cost
~350 ms of TLS-context setup before a single byte moved. It is now ~1 ms.

It is also permanent, not merely deferred. On a German library, MangaUpdates
serves English only and `feed` is unused, so two of the four pools are never
opened at all.

Measured on the real app, same config, same age: **96.2 MB → 85.4 MB**, and
~160 ms off time-to-visible-tray.

**Not changed, having measured it:** the icon path. `QIcon.addFile` already
records a filename and rasterises on demand, so listing twelve sizes costs
~11 kB per icon, not twelve bitmaps. The procedural monogram *is* rendered
eagerly at four sizes, but that is deliberate — text drawn at the target size
beats text scaled to it, and the whole cache is a fraction of one pool.

## 8. Shipping it

### One directory can override the platform's

`platformdirs` puts settings and data where each OS expects, which is right for
an installed app and wrong for two other cases: a portable copy that should
keep its state beside itself, and a test that must not touch the developer's
real profile.

`MANGAME_HOME` covers both. `store/paths.py` consults it before asking
`platformdirs`, so config, database and imported artwork all land in one
directory of the caller's choosing.

The test suite used to isolate itself by pointing `XDG_DATA_HOME` at a
temporary directory. That works on Linux — and on macOS, where recent
`platformdirs` honours the XDG variables too — but **Windows ignores them
entirely**. On a Windows runner those tests would have written into the real
`%APPDATA%\mangame`, contaminating each other and the machine. The bug was
invisible for as long as the project only ever ran its tests on Linux; adding a
three-platform CI matrix is what made it matter.

### The version has one home

`src/mangame/__init__.py` states `__version__`, and `pyproject.toml` declares
`dynamic = ["version"]` so hatchling reads it from there. Nothing else may
carry a version number: the PyInstaller spec interpolates it into the macOS
`Info.plist`, and a test asserts the installed metadata agrees with the
package.

That matters more for a frozen build than a wheel. `importlib.metadata` has
nothing to answer with inside a PyInstaller bundle, so `mangame --version` has
to read a constant the app carries itself.

### Frozen builds, one recipe

`packaging/mangame.spec` is the single build description, and the release
workflow runs exactly the command a developer would run locally. It branches
once, on `sys.platform`:

- **Linux and Windows** — a one-file executable, because the promise is
  "download it and run it".
- **macOS** — an `.app` bundle rather than a bare binary, because only a bundle
  can carry `LSUIElement`, and without that a tray-only app still claims a Dock
  tile it has no use for.

Every build runs a hidden `--smoke-test` once on its runner before it is
allowed near a release page. The mode opens the settings/database paths and
loads the bundled app icon, then exits without creating a tray or depending on
stdout/stderr. That last constraint matters on Windows, where a PyInstaller
`console=False` executable has neither stream. The workflow also imposes a
30-second timeout, so a platform unexpectedly reporting a tray cannot hang the
release forever. A bundle that cannot do that much is broken in a way no unit test
would catch.

The same reasoning covers the wheel: CI installs the built artifact into a
fresh environment and asserts the emblem directory is present and populated. A
wheel that imports cleanly but ships no artwork starts with an empty tray.

### Diagnostics survive packaging

`diagnostics.configure_logging()` always installs a rotating file handler and
adds stderr only when one exists. Settings → Diagnostics exposes the version,
runtime, platform and support-file paths without including the user's library.
The report is copyable; the log remains separate because source failures may
contain a URL or local path that should be reviewed before sharing.
