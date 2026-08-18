# Graph Report - mangame  (2026-08-18)

## Corpus Check
- 51 files · ~43,215 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 988 nodes · 3306 edges · 15 communities detected
- Extraction: 43% EXTRACTED · 57% INFERRED · 0% AMBIGUOUS · INFERRED: 1899 edges (avg confidence: 0.61)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]

## God Nodes (most connected - your core abstractions)
1. `PublicationStatus` - 96 edges
2. `IconState` - 95 edges
3. `SourceSignal` - 85 edges
4. `Database` - 80 edges
5. `Library` - 80 edges
6. `Cadence` - 79 edges
7. `Translator` - 71 edges
8. `Chapter` - 67 edges
9. `SourceMatch` - 67 edges
10. `HttpClient` - 67 edges

## Surprising Connections (you probably didn't know these)
- `db()` --calls--> `Database`  [INFERRED]
  tests/test_store.py → src/mangame/store/db.py
- `TestNaming` --uses--> `IconState`  [INFERRED]
  tests/test_artwork.py → src/mangame/domain/models.py
- `Deriving the grey and break states from one picture.  These run without a displa` --uses--> `IconState`  [INFERRED]
  tests/test_artwork.py → src/mangame/domain/models.py
- `A coloured circle on transparency, with a second colour inside it.` --uses--> `IconState`  [INFERRED]
  tests/test_artwork.py → src/mangame/domain/models.py
- `Shared fixtures. Every test works off explicit clocks — no ``utcnow`` anywhere.` --uses--> `Chapter`  [INFERRED]
  tests/conftest.py → src/mangame/domain/models.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (76): The match that represents the group.          Ranked rather than "whichever sour, Which way round a silhouette is drawn., SilhouetteTone, available(), Menu translations.  The whole UI is a handful of menu labels, so a plain dict pe, Looks up a menu label, falling back to English key by key., Languages with a catalog, as ``{code: endonym}``, in menu order., Translator (+68 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (75): AniListSource, AniList adapter — the hiatus oracle.  AniList carries no chapter-level release t, One aliased GraphQL document covers up to :data:`MAX_ALIASES` series., Status-only source used to detect declared hiatuses., _title_of(), Capabilities, FetchRequest, The contract every source adapter implements.  Deliberately tiny. A source has t (+67 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (69): BatchSource, Registry, load(), User settings.  Stored as JSON rather than TOML on purpose: reading *and* writin, One tracked series, as the user configured it., Everything the tiny menu can change, plus a few file-only escape hatches., Read settings, falling back to defaults on a missing or broken file., SeriesConfig (+61 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (79): BaseModel, active(), from_announced_next(), from_status(), is_suspected(), merge(), Turn raw source signals into announced-break windows.  Break detection is ranked, The announced break covering ``now``, or the next one starting soon.      A brea (+71 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (63): _blank(), emblem_name(), _fitted(), grayscale(), _inset(), install(), load(), Turning one picture into a three-state emblem set.  The tray says three things w (+55 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (40): AddSeriesDialog, group_matches(), primary(), _priority(), One dialog for finding a series and adding it.  Adding used to be a chain of mod, Collapse per-source matches into one candidate per series.      First-appearance, Search and add, in one window., True between asking for a search and being handed its outcome. (+32 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (23): _as_utc(), estimate(), expected_next(), _forward_run(), _intervals(), _is_weekly_multiple(), _numeric(), release_events() (+15 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (22): is_enabled(), is_supported(), launch_command(), _linux_desktop_file(), _linux_enabled(), _linux_set(), _macos_enabled(), _macos_plist() (+14 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (21): canonical(), codes(), get(), labels(), Language, normalize(), The languages mangame can actually read manga in.  This is the *reading* languag, One language mangame can read in. (+13 more)

### Community 9 - "Community 9"
Cohesion: 0.13
Nodes (11): _backoff(), decide(), _jitter(), inputs(), test_each_distance_selects_its_tier(), TestApproachingTheDueDate, TestBackoff, TestBoundsAndJitter (+3 more)

### Community 10 - "Community 10"
Cohesion: 0.19
Nodes (11): aggregate(), icon_state_for(), _phase(), resolve(), _tooltip(), announced_break(), latest(), series() (+3 more)

### Community 11 - "Community 11"
Cohesion: 0.26
Nodes (5): _link(), _parse_datetime(), parse_feed(), _text(), TestParseFeed

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (1): mangame — a tray-sized manga release radar.

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Numeric chapter order when parseable, falling back to publish time.

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): 0.0-1.0 trust in this cadence, from sample size and regularity.

## Knowledge Gaps
- **51 isolated node(s):** `mangame — a tray-sized manga release radar.`, `Where mangame keeps its things, per platform.`, `Drop-in folder so users can add their own emblems without a rebuild.`, `User settings.  Stored as JSON rather than TOML on purpose: reading *and* writin`, `The identity a tracked series is stored under.      Lives with the model that ow` (+46 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 12`** (2 nodes): `mangame — a tray-sized manga release radar.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `Numeric chapter order when parseable, falling back to publish time.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `0.0-1.0 trust in this cadence, from sample size and regularity.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `IconState` connect `Community 0` to `Community 2`, `Community 3`, `Community 4`, `Community 7`, `Community 10`?**
  _High betweenness centrality (0.231) - this node is a cross-community bridge._
- **Why does `PublicationStatus` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 9`, `Community 10`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `Database` connect `Community 2` to `Community 1`, `Community 3`, `Community 4`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Are the 93 inferred relationships involving `PublicationStatus` (e.g. with `LearnedState` and `PollState`) actually correct?**
  _`PublicationStatus` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `IconState` (e.g. with `MangameTray` and `The tray: one icon per tracked series, and a deliberately tiny menu.  The menu h`) actually correct?**
  _`IconState` has 92 INFERRED edges - model-reasoned connections that need verification._
- **Are the 82 inferred relationships involving `SourceSignal` (e.g. with `Library` and `The library: config + learned state + read state, folded into one view.  Both th`) actually correct?**
  _`SourceSignal` has 82 INFERRED edges - model-reasoned connections that need verification._
- **Are the 59 inferred relationships involving `Database` (e.g. with `BreakWindow` and `Cadence`) actually correct?**
  _`Database` has 59 INFERRED edges - model-reasoned connections that need verification._