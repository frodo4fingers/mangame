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
