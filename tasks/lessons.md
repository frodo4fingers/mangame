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
