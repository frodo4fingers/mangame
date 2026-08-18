# Graph Report - mangame  (2026-08-18)

## Corpus Check
- 51 files · ~47,511 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1071 nodes · 3605 edges · 20 communities detected
- Extraction: 41% EXTRACTED · 59% INFERRED · 0% AMBIGUOUS · INFERRED: 2115 edges (avg confidence: 0.6)
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
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]

## God Nodes (most connected - your core abstractions)
1. `IconState` - 139 edges
2. `Translator` - 115 edges
3. `Settings` - 99 edges
4. `PublicationStatus` - 96 edges
5. `SourceSignal` - 85 edges
6. `SeriesConfig` - 84 edges
7. `Database` - 80 edges
8. `Library` - 80 edges
9. `Cadence` - 79 edges
10. `SettingsDialog` - 74 edges

## Surprising Connections (you probably didn't know these)
- `Database` --calls--> `db()`  [INFERRED]
  src/mangame/store/db.py → tests/test_service.py
- `IconState` --uses--> `TestNaming`  [INFERRED]
  src/mangame/domain/models.py → tests/test_artwork.py
- `IconState` --uses--> `Deriving the grey and break states from one picture.  These run without a displa`  [INFERRED]
  src/mangame/domain/models.py → tests/test_artwork.py
- `IconState` --uses--> `A coloured circle on transparency, with a second colour inside it.`  [INFERRED]
  src/mangame/domain/models.py → tests/test_artwork.py
- `Chapter` --uses--> `Shared fixtures. Every test works off explicit clocks — no ``utcnow`` anywhere.`  [INFERRED]
  src/mangame/domain/models.py → tests/conftest.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (106): Which way round a silhouette is drawn., SilhouetteTone, available(), Menu translations.  The whole UI is a handful of menu labels, so a plain dict pe, Looks up a menu label, falling back to English key by key., Languages with a catalog, as ``{code: endonym}``, in menu order., Translator, load() (+98 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (95): BaseModel, active(), from_announced_next(), from_status(), is_suspected(), merge(), Turn raw source signals into announced-break windows.  Break detection is ranked, The announced break covering ``now``, or the next one starting soon.      A brea (+87 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (85): AniListSource, AniList adapter — the hiatus oracle.  AniList carries no chapter-level release t, One aliased GraphQL document covers up to :data:`MAX_ALIASES` series., Status-only source used to detect declared hiatuses., _title_of(), BatchSource, Capabilities, FetchRequest (+77 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (52): AddSeriesDialog, Search and add, in one window., True between asking for a search and being handed its outcome., Fill the list with what the search found., One series in the results list, with every source that offered it., The match that represents the group.          Ranked rather than "whichever sour, SeriesCandidate, SourceMatch (+44 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (63): _blank(), emblem_name(), _fitted(), grayscale(), _inset(), install(), load(), Turning one picture into a three-state emblem set.  The tray says three things w (+55 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (18): group_matches(), primary(), _priority(), One dialog for finding a series and adding it.  Adding used to be a chain of mod, Collapse per-source matches into one candidate per series.      First-appearance, The identity two matches must share to be the same series.      Deliberately the, title_key(), The identity a tracked series is stored under.      Lives with the model that ow (+10 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (12): Library, Poller, RuntimeError, chapter(), db(), FakeRegistry, FakeSource, settings_with() (+4 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (26): available_emblems(), emblem_roots(), _find(), _hue_for(), icon_for(), _initial(), monogram(), Emblem resolution: series + state -> a tray-ready :class:`QIcon`.  Two mechanism (+18 more)

### Community 8 - "Community 8"
Cohesion: 0.1
Nodes (23): _as_utc(), estimate(), expected_next(), _forward_run(), _intervals(), _is_weekly_multiple(), _numeric(), release_events() (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (21): canonical(), codes(), get(), labels(), Language, normalize(), The languages mangame can actually read manga in.  This is the *reading* languag, One language mangame can read in. (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (8): decide(), _jitter(), inputs(), test_each_distance_selects_its_tier(), TestBoundsAndJitter, TestBreaks, TestSpecialCases, tier()

### Community 11 - "Community 11"
Cohesion: 0.19
Nodes (11): aggregate(), icon_state_for(), _phase(), resolve(), _tooltip(), announced_break(), latest(), series() (+3 more)

### Community 12 - "Community 12"
Cohesion: 0.21
Nodes (17): is_enabled(), is_supported(), launch_command(), _linux_desktop_file(), _linux_enabled(), _linux_set(), _macos_enabled(), _macos_plist() (+9 more)

### Community 13 - "Community 13"
Cohesion: 0.26
Nodes (5): _link(), _parse_datetime(), parse_feed(), _text(), TestParseFeed

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (5): build(), Palette, Generate the mangame tray emblem asset set.  Produces, for every emblem and ever, Colours for one icon state.      ``line`` is the outline. It is deliberately cho, _run()

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): mangame — a tray-sized manga release radar.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Numeric chapter order when parseable, falling back to publish time.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): 0.0-1.0 trust in this cadence, from sample size and regularity.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Looks up a menu label, falling back to English key by key.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Languages with a catalog, as ``{code: endonym}``, in menu order.

## Knowledge Gaps
- **53 isolated node(s):** `mangame — a tray-sized manga release radar.`, `Where mangame keeps its things, per platform.`, `Drop-in folder so users can add their own emblems without a rebuild.`, `User settings.  Stored as JSON rather than TOML on purpose: reading *and* writin`, `The identity a tracked series is stored under.      Lives with the model that ow` (+48 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 15`** (2 nodes): `mangame — a tray-sized manga release radar.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Numeric chapter order when parseable, falling back to publish time.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `0.0-1.0 trust in this cadence, from sample size and regularity.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Looks up a menu label, falling back to English key by key.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Languages with a catalog, as ``{code: endonym}``, in menu order.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `IconState` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 11`?**
  _High betweenness centrality (0.217) - this node is a cross-community bridge._
- **Why does `Database` connect `Community 1` to `Community 2`, `Community 3`, `Community 6`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `PublicationStatus` connect `Community 1` to `Community 0`, `Community 2`, `Community 6`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Are the 136 inferred relationships involving `IconState` (e.g. with `MangameTray` and `The tray: one icon per tracked series, and a deliberately tiny menu.  The menu h`) actually correct?**
  _`IconState` has 136 INFERRED edges - model-reasoned connections that need verification._
- **Are the 111 inferred relationships involving `Translator` (e.g. with `SeriesCandidate` and `AddSeriesDialog`) actually correct?**
  _`Translator` has 111 INFERRED edges - model-reasoned connections that need verification._
- **Are the 91 inferred relationships involving `Settings` (e.g. with `MangameTray` and `The tray: one icon per tracked series, and a deliberately tiny menu.  The menu h`) actually correct?**
  _`Settings` has 91 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `PublicationStatus` (e.g. with `LearnedState` and `PollState`) actually correct?**
  _`PublicationStatus` has 93 INFERRED edges - model-reasoned connections that need verification._