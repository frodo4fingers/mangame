# Lessons

### Verify API response *shapes* before writing an adapter
- **What**: Every source adapter was written only after curling the real
  endpoint and reading the actual payload. This caught MangaDex's 2037 sentinel,
  the fact that `/chapter?manga[]=` does not accept multiple ids, that
  MangaUpdates' `orderby:"date"` silently ignores the search term, and that
  MANGA Plus' `format=json` now returns 403.
- **Why**: Every one of those would have been a subtle wrong-behaviour bug, not
  a crash — the kind that survives code review and ships.
- **Rule**: Never write an HTTP adapter from documentation alone. Fetch the real
  endpoint, print the payload, then write the parser against what it actually
  returned.

### Real data beats synthetic fixtures for finding domain bugs
- **What**: The cadence engine passed every synthetic test I could think of, but
  produced a "154-day period" for One Piece. Two genuine algorithm bugs
  (backfills, coverage holes) only surfaced when run against live MangaDex data.
- **Why**: Synthetic fixtures encode the assumptions the algorithm was written
  with, so they cannot falsify those assumptions.
- **Rule**: For any inference/heuristic layer, run it against real data early —
  then turn each surprise into a regression test with a name that states the
  real-world shape it guards against.

### Never let derived state ratchet
- **What**: `_merge_learned` seeded its status ranking with the previous status,
  so `HIATUS` outranked every future "ongoing" and a series could never come
  back — the icon would stay black forever.
- **Why**: "Strongest signal wins" is right for resolving disagreement *within
  one observation* and wrong across time, where it becomes a one-way latch.
- **Rule**: When combining signals with a priority ranking, be explicit about
  whether you are ranking across *sources* or across *time*. Across time,
  prefer "the newest informative answer wins"; let uninformative answers
  abstain rather than vote.

### Sparse data deserves "I don't know", not a confident guess
- **What**: A single 11-day interval is enough to compute a period, but not
  enough to trust it. `Cadence.is_known` requires two intervals, so a
  one-sample series drops to a calm twice-daily poll instead of chasing a
  fabricated schedule.
- **Why**: A wrong confident schedule is worse than no schedule — it produces
  wrong icons and wasted requests, and it looks correct.
- **Rule**: Separate "measured" from "trusted". Let the consumer of an estimate
  see the sample size and decide.

### Type-check platform-specific code for every platform
- **What**: `winreg` and the macOS LaunchAgent paths are unreachable on Linux,
  so mypy either could not see them or called them dead code. Running
  `mypy --platform win32` and `--platform darwin` type-checks all three.
- **Why**: Cross-platform branches are exactly the code that cannot be run
  locally, so static checking is the only feedback available.
- **Rule**: In a cross-platform project, run the type checker once per target
  platform. Guard platform branches with `if sys.platform != "x": return` so the
  checker can narrow, and scope any `warn_unreachable` exemption to that module.

### `QSystemTrayIcon` is not a `QWidget`
- **What**: `menu.setParent(tray_icon)` fails to type-check and cannot work; a
  tray icon cannot own a menu's lifetime.
- **Why**: Without a parent, Python garbage-collects a `QMenu` that Qt is still
  displaying.
- **Rule**: In PySide, keep an explicit Python-side reference to any top-level
  `QMenu` that is not parented to a real widget.

### Keep the domain layer free of I/O and of the clock
- **What**: `domain/` takes `now` as a parameter everywhere and performs no I/O,
  so 199 tests run in under three seconds with no network and no mocking of
  time.
- **Why**: It made every rule in the brief — icon precedence, break confidence,
  the polling ladder — directly assertable rather than something to infer from
  observed behaviour.
- **Rule**: Push time and I/O to the edges. If a rule matters to the product,
  it should be testable without a clock or a socket.

### Sub-agents for breadth, direct work for depth
- **What**: Three parallel research agents (forkable repos, data sources, stack
  evaluation) ran while I built the stack-agnostic layers. Tracing a single bug
  through cadence → library → poller was done directly.
- **Why**: Independent research threads benefit from separate context; a single
  causal trace is corrupted by splitting it.
- **Rule**: Delegate breadth. Never delegate one continuous trace.

### Qt popups ignore the panel, and only the tray notices
- **What**: Tray submenus hung 44px behind the KDE panel. Qt fits popups to the
  full screen rectangle, not the work area, because the platform theme asks it
  to. Parenting the menu and `setScreen()` both changed nothing, and Qt's XCB
  SNI never exports the menu over DBusMenu, so Plasma could not place it either.
- **Why**: A tray menu is the one menu that always opens against a panel, so it
  is the only place where "full screen" and "work area" visibly differ.
- **Rule**: Measure the geometry before theorising about the cause. Clamp popups
  to `availableGeometry()` yourself, and keep the arithmetic in a pure function
  so it can be tested without a display.

### A setting means something, and the meaning has to reach the network layer
- **What**: "Language" was built as a UI-label switch. The user meant the
  language they *read* the manga in. The plumbing half-existed — settings and
  queries were language-aware — but every source was asked in every language
  and MangaUpdates stamped whatever language was *requested* onto releases it
  cannot attribute at all, so a German reader would have been shown an English
  scanlation labelled German.
- **Why**: A setting that only reaches the presentation layer looks implemented
  and passes its tests. The damage shows up at the boundary where a source is
  asked a question it cannot answer, and answers anyway.
- **Rule**: Trace a user-facing setting all the way to the request it changes.
  Make each adapter declare what it can actually serve (`Capabilities.languages`)
  and let the scheduler skip the rest — never let a source guess a field the API
  does not return. Verify the limitation against the live API before writing it
  down: MangaUpdates' `lang` filter returns identical hit counts either way.

### Cache validators answer the previous question
- **What**: Switching language left ETag, `Last-Modified` and MangaDex's
  `latestUploadedChapter` watermark in place, so the next poll short-circuited
  to "nothing changed" and the new language's chapters were never fetched.
- **Why**: A validator is only valid for the request that produced it. The
  reading language is part of that request even though it is not part of the URL
  the validator was stored against.
- **Rule**: When a setting changes the *question* asked of a source, invalidate
  the cached answer with it. `clear_due()` clears validators and watermarks, not
  just the due time.

### One code is not one language
- **What**: MangaDex files Spanish under both `es` and `es-la`, and lists both
  in `availableTranslatedLanguages` for the same series. Asking for one code
  would have hidden the other's chapters — Latin-American Spanish is where most
  One Piece translations actually land.
- **Why**: Language tags are a family, not an identifier. OS locales
  (`es_MX.UTF-8`) and region codes (`es-419`) widen the family further.
- **Rule**: Model a language as a canonical code plus the source codes it
  covers. Ask for every code in one request, fold to the canonical code at the
  boundary (adapter on the way in, validator on config load), and keep the
  round trip under test so no code is fetched under one name and stored under
  another.

### A wizard of modal boxes is one dialog wearing a disguise
- **What**: Adding a manga was `getText` → blind wait → `getItem`, with
  `getItem(..., [""])` standing in for "nothing found". Every step threw away
  the previous one's context, so refining a search meant restarting from the
  menu, and the error state offered an empty string as a choice.
- **Why**: `QInputDialog` is a shortcut for asking *one* question. A flow that
  asks, waits, then asks again is a single task, and splitting it across modal
  boxes loses the state that makes the task recoverable.
- **Rule**: When two dialogs are always shown in sequence, they are one dialog.
  Build it as a `QDialog` where the input, the results and the status line stay
  on screen together, and keep the decision logic (grouping, ranking, what is
  selectable) in pure functions so it can be tested without a display.

### Never map a selection back by its label
- **What**: The old results list recovered the chosen match with
  `matches[labels.index(chosen)]`. Two sources returning the same title and
  year produce the same label, so the wrong reference could be attached.
- **Why**: A label is for humans; it is not an identifier and nothing stops it
  from repeating.
- **Rule**: Put the index or the object on the item (`Qt.ItemDataRole.UserRole`)
  and read it back from there.

### A QThread must outlive the last reference you were holding
- **What**: Each search assigned `self._search`, so starting a second search
  dropped the first thread's only Python reference while it might still be
  running — and a collected running QThread takes the process with it.
- **Why**: Qt owns the thread, Python owns the wrapper, and the wrapper dying
  first is fatal rather than merely untidy.
- **Rule**: Keep workers in a set, discard them on `finished`, and wait for
  them during shutdown.

### Show a thing as unavailable using the identity that makes it unavailable
- **What**: The add dialog greyed out series it already tracked by comparing
  titles, but tracking refuses duplicates by slug. A series stored as
  "Kagurabachi!" left the search hit "Kagurabachi" looking addable, and Add
  then silently did nothing — the exact failure the greying was added to stop.
- **Why**: Two normalisations of "the same series" existed in different layers.
  A disabled state computed from the looser one is decoration, not a guarantee.
- **Rule**: Derive the affordance from the rule that enforces it. Move the
  identity function next to the model that owns the key and call it from both
  sides, rather than reimplementing "close enough" in the UI.

### A fallback that never fails hides the fallback behind it
- **What**: `icon_for` resolved `_find(emblem) or _find("book")` before falling
  through to the generated monogram. Since `book` always exists, the monogram
  was dead code — and because `emblem_for()` returns `"monogram"` for every
  series but One Piece, *every* tracked series wore the same book icon.
- **Why**: Chained fallbacks are ordered by specificity, and a catch-all placed
  above a better answer silently deletes it. Nothing errors; it just looks
  boring, so nobody looks.
- **Rule**: Put the *most specific* fallback last only if it can fail. If a
  step always succeeds, everything after it is unreachable — check that by
  asserting two different inputs produce two different outputs, not just that
  the output is non-null.

### A dialog that reports changes must also adopt them
- **What**: The settings dialog emitted `self._settings.model_copy(update=...)`
  for every edit, but `self._settings` only changed when the tray echoed a save
  back. Turning off notifications and then picking an emblem emitted a copy of
  the *original* settings with a new emblem — quietly turning notifications on
  again.
- **Why**: An edit is a function of the current state, not the opening state.
  Holding the opening state makes every change independent of every other one,
  which is exactly wrong.
- **Rule**: Route every emit through one method that assigns the new value
  before emitting it. Then test *two* edits in a row — a single-edit test
  passes happily against the broken version.

### Widgets need a display, images do not
- **What**: `QPixmap` requires a `QGuiApplication`; `QImage` requires nothing.
  Writing the artwork transforms against `QImage` made them assertable pixel by
  pixel in ordinary unit tests, with no display and no fixture.
- **Why**: The rendering primitives are split precisely along "does this touch
  the window system".
- **Rule**: Keep image work on `QImage` and convert to `QPixmap` at the last
  moment, in the widget. Where widgets really are the thing under test, drive
  them on `QT_QPA_PLATFORM=offscreen` rather than skipping the test.

### PySide6 type stubs and PySide6 runtime disagree
- **What**: `QImage.save(path, b"PNG")` satisfies mypy — the stub says the
  format is `bytes` — and raises `ValueError` at runtime, which wants `str`.
- **Why**: The stubs are generated from the C++ signature; the binding converts
  differently.
- **Rule**: Where an argument is optional and inferable, omit it. Qt derives the
  format from the file suffix, which keeps both the checker and the runtime
  happy.

### Padding you did not write is still padding you shipped
- **What**: The settings tabs looked heavily inset. Nobody had set a margin:
  Qt's defaults stacked three of them — the dialog layout (11), the tab pane
  frame (2) and each page's layout (11) — for 24px on every edge.
- **Why**: Each default is reasonable alone and they are invisible in the code,
  so nesting containers quietly compounds them.
- **Rule**: Measure before tuning — map a child widget's origin into the window
  and read the number. Then let exactly one container own the margin and zero
  the rest, and assert the leftmost *control*, not the page origin: a test that
  measures the container passes happily while the padding inside it returns.

### `setFlat` is a hint, and Fusion declines it
- **What**: `QGroupBox.setFlat(True)` was supposed to drop the frame for the
  flat look; rendered side by side with a boxed one, Fusion draws them almost
  identically.
- **Why**: Style hints are advisory, and each style decides what it honours.
- **Rule**: Verify a styling call by rendering it and comparing, not by reading
  the docs. Where a style ignores the hint, drop the widget instead of fighting
  it — a bold label groups content perfectly well without a box.

### Ask for the thing the user wants, not the thing the code stores
- **What**: The artwork tab asked for an emblem *name*, then expected a second,
  unmentioned trip to another tab to actually use it. A file saved as
  "hunterxhunter.png" for a series keyed "hunter-x-hunter" imported cleanly,
  reported success and changed nothing.
- **Why**: The field mirrored the storage layout — emblems are directories, so
  the dialog asked for a directory name. The user's intention was never "make
  me an emblem"; it was "make my manga look like this".
- **Rule**: Name the field after the intention and derive the identifier. If a
  task needs two steps in two places, that is one step the design has not
  finished, and the gap between them is where silent failure lives.

### A confirmation next to the control is one the user can skim past
- **What**: The fix for "did the name match?" could have been a validation
  message. Instead the button says *Use for Hunter x Hunter* and is disabled
  when nothing matched.
- **Why**: A message is passive and optional; the label on the control you are
  about to press is neither, and a disabled control makes the wrong outcome
  unavailable rather than merely discouraged.
- **Rule**: Put the confirmation in the action. Reserve prose for the case the
  action cannot express — here, *why* nothing matched and what to do instead.

### Guess out loud, and refuse to guess between two
- **What**: File names are matched against series by squashing both to letters,
  so punctuation cannot cause a miss. Where two series match equally, the
  result is "no match" rather than the first one.
- **Why**: A wrong guess here is worse than no guess: artwork lands on the
  wrong manga and everything afterwards looks fine.
- **Rule**: A guess is acceptable when it is visible and reversible before it
  commits. Ambiguity is not a weak match, it is the absence of one.

### Reserve space for content, not for its absence
- **What**: The preview strip kept a fixed cell size so it would not jump when
  filled — correct — but the empty tab then showed three captions under three
  blank squares, which reads as breakage.
- **Why**: "Don't reflow" and "don't show scaffolding" are different problems.
  Fixed cell sizes solve the first; visibility solves the second.
- **Rule**: Reserve dimensions within a block, and hide the whole block when it
  has nothing to say. A layout shift caused by the user's own action is
  feedback; one caused by content arriving on its own is instability.

### `isVisibleTo()` answers a different question than `setVisible()` asks
- **What**: Asserting a hidden widget with `isVisibleTo(dialog)` failed even
  when shown, because the widget sits on a tab page that is not current.
- **Why**: `isVisibleTo` walks ancestors; `isHidden` reports the widget's own
  explicit flag, which is what `setVisible` toggles.
- **Rule**: Test the flag you set. Use `isHidden()` for "did I hide this", and
  keep `isVisible()` for "is the user actually looking at it".

### Measure before optimising, and be willing to retract
- **What**: I proposed two optimisations. One (deferring httpx) was worth
  ~10 MB and ~160 ms. The other (rendering fewer icon sizes) was wrong:
  `QIcon.addFile` already stores a filename and rasterises on demand, so twelve
  sizes cost ~11 kB. Measuring also found a bigger fish neither guess named —
  four eagerly-constructed connection pools, rebuilt on every search.
- **Why**: Both guesses were plausible. Plausibility is not evidence, and the
  cost that actually hurt was in the repetition, not the size.
- **Rule**: Measure the specific claim before implementing it, and say so when
  it does not survive. A retracted optimisation is a result; an implemented one
  that saves nothing is debt.

### A long-lived process is not a baseline
- **What**: The first comparison put the old build at 122 MB against 85 MB. But
  the old process had been running for hours with dialogs opened repeatedly.
  Fresh, at the same age, it was 96 MB — a real 11 MB win, not 37.
- **Why**: Resident memory in a GUI process grows with what the user did to it,
  not only with what the code allocates at startup.
- **Rule**: Compare processes of the same age doing the same things, and
  isolate the change with a stash-and-rerun A/B rather than trusting whatever
  happens to be running.

### Lazy is worth more where it repeats than where it is large
- **What**: Deferring the httpx *import* saved 3.4 MB once. Deferring the four
  `AsyncClient` constructions saved 10 MB and 350 ms **per search**, because
  `SearchWorker` builds a registry every time.
- **Why**: Startup costs are paid once and amortise. A cost inside a
  user-triggered path is paid at exactly the moment the user is waiting.
- **Rule**: Before optimising a construction cost, find out how often it is
  constructed. "Once at startup" and "once per interaction" deserve very
  different amounts of effort.

### Deferred work must be observable, or it cannot be tested
- **What**: `HttpClient.connected` exists so tests can assert that a pool was
  never opened. Without it the only evidence of laziness would be timing.
- **Why**: An optimisation with no observable consequence silently regresses
  the first time someone adds an eager call.
- **Rule**: When making something lazy, expose the fact that it is still
  unloaded. Then assert on it.

### mypy narrows properties across await
- **What**: `assert client.connected is False` ... `await` ... `assert
  client.connected is True` failed as `[unreachable]`: mypy kept the
  `Literal[False]` narrowing of the member expression across the await.
- **Why**: mypy narrows member expressions, including properties, and an await
  does not invalidate that narrowing.
- **Rule**: For before/after assertions on a property, capture both into locals
  and compare the pair. It type-checks, and it reads better.

### An aggregate must not look like a member of the set
- **What**: One icon for the whole library wore One Piece's straw hat, because
  that was the nicest emblem available when the mode was written.
- **Why**: A summary that borrows one member's identity misreports what it is
  summarising, and does so most badly for the users with the most series.
- **Rule**: When a UI element stands for many things, give it its own mark.
  Letters and abstract shapes can do that; pictures of one of the things cannot.

### Measure new artwork against the artwork already shipping
- **What**: A new emblem looked right beside the others and was statistically
  nowhere near them: its break state was 39% dark pixels where the existing two
  are 59% and 66%, because a thin glyph is mostly outline.
- **Why**: The eye grades a picture on its own terms; the panel shows it next
  to the others at 16px, where only the gross statistics survive.
- **Rule**: Reduce artwork to a few numbers (median lightness, mean saturation,
  dark fraction) and compare against the existing set. Then write the test as
  that comparison, so the threshold moves with the family instead of being a
  number someone typed once.

### paint-order is how a filled glyph keeps a rim without losing its body
- **What**: A centred stroke eats half its width into the fill. On a bulky
  shape that is nothing; on a letterform it hollows the mark out.
- **Why**: Visible rim width and solid body are both wanted, and a centred
  stroke trades one for the other.
- **Rule**: `paint-order="stroke fill"` paints the outline behind the fill, so
  it only shows outside. Double the stroke width to keep the visible rim the
  same.

### Do not script a block replacement across a boundary you have not re-read
- **What**: A `str.replace` that inserted a new test class ended at the wrong
  place and silently deleted two existing tests. Only `ruff` noticing a
  now-unused import gave it away.
- **Why**: The replaced text was written from memory of the file, not from a
  fresh read, and a passing test run cannot notice tests that no longer exist.
- **Rule**: View the exact region first, and anchor a replacement on both its
  start *and* its end. Afterwards, check the test count went up by what you
  added — this is the second time this session that a blind edit destroyed
  working code.

### A tray icon's only affordance is its picture
- **What**: Left click opened the newest chapter when one was waiting, and did
  nothing otherwise — including always, in aggregate mode, where the state it
  read is never written.
- **Why**: An icon in a panel cannot show that it is clickable, so a behaviour
  that only sometimes happens is indistinguishable from a broken one.
- **Rule**: Give both buttons the same destination. If a click has a shortcut
  worth having, put it in the menu too, where it can be read.

### Rebuilding a menu on a timer deletes the one on screen
- **What**: `refresh()` runs every minute and replaced each icon's `QMenu`.
  The dict holding it was the only reference, so an open menu was collected.
- **Why**: `QSystemTrayIcon` is not a `QWidget`, so its menu cannot be
  parented to it and Python's refcount is what keeps it alive.
- **Rule**: Before replacing a widget on a timer, ask whether it can be on
  screen. Skip the rebuild while it is visible — stale beats vanished, and it
  also stops items moving under the pointer.

### Verify desktop integration by synthesising a real event
- **What**: `libXtst` via `ctypes` sent an actual click at the icon's screen
  coordinates, so KDE's panel and the StatusNotifierItem hop were exercised
  rather than mocked, and a screenshot showed the result.
- **Why**: The offscreen tests emit `activated` directly, which proves the
  handler and nothing about whether the desktop ever calls it.
- **Rule**: When behaviour depends on a component you do not own, drive it from
  the outside at least once. `XTestFakeButtonEvent` needs `restype`/`argtypes`
  set, or the 64-bit display pointer is truncated to an int.
