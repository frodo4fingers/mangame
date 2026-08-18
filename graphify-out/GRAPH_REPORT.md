# Graph Report - mangame  (2026-08-18)

## Corpus Check
- 53 files · ~54,385 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1187 nodes · 4007 edges · 31 communities detected
- Extraction: 40% EXTRACTED · 60% INFERRED · 0% AMBIGUOUS · INFERRED: 2405 edges (avg confidence: 0.6)
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
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]

## God Nodes (most connected - your core abstractions)
1. `IconState` - 180 edges
2. `Translator` - 150 edges
3. `Settings` - 135 edges
4. `SeriesConfig` - 122 edges
5. `PublicationStatus` - 96 edges
6. `Database` - 86 edges
7. `SettingsDialog` - 86 edges
8. `Library` - 86 edges
9. `SourceSignal` - 85 edges
10. `HttpClient` - 84 edges

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
Nodes (96): AniListSource, AniList adapter — the hiatus oracle.  AniList carries no chapter-level release t, One aliased GraphQL document covers up to :data:`MAX_ALIASES` series., Status-only source used to detect declared hiatuses., _title_of(), BatchSource, Capabilities, FetchRequest (+88 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (101): BaseModel, active(), from_announced_next(), from_status(), is_suspected(), merge(), Turn raw source signals into announced-break windows.  Break detection is ranked, The announced break covering ``now``, or the next one starting soon.      A brea (+93 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (28): A copy with one series dropped., A copy in which one tracked series has been edited in place.          Order is p, QDialog, classify(), emblem_choices(), file_filter(), flatten(), heading() (+20 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (113): Which way round a silhouette is drawn., SilhouetteTone, available(), Menu translations.  The whole UI is a handful of menu labels, so a plain dict pe, Looks up a menu label, falling back to English key by key., Languages with a catalog, as ``{code: endonym}``, in menu order., Translator, load() (+105 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (52): AddSeriesDialog, Search and add, in one window., True between asking for a search and being handed its outcome., Fill the list with what the search found., One series in the results list, with every source that offered it., The match that represents the group.          Ranked rather than "whichever sour, SeriesCandidate, SourceMatch (+44 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (63): _blank(), emblem_name(), _fitted(), grayscale(), _inset(), install(), load(), Turning one picture into a three-state emblem set.  The tray says three things w (+55 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (18): _parse(), Library, What a single source reports about a single series at one point in time.      Ad, SourceSignal, Poller, RuntimeError, chapter(), db() (+10 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (35): available_emblems(), emblem_roots(), _find(), _hue_for(), icon_for(), _initial(), monogram(), Emblem resolution: series + state -> a tray-ready :class:`QIcon`.  Two mechanism (+27 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (23): _as_utc(), estimate(), expected_next(), _forward_run(), _intervals(), _is_weekly_multiple(), _numeric(), release_events() (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (26): group_matches(), primary(), _priority(), One dialog for finding a series and adding it.  Adding used to be a chain of mod, Collapse per-source matches into one candidate per series.      First-appearance, The identity two matches must share to be the same series.      Deliberately the, title_key(), The identity a tracked series is stored under.      Lives with the model that ow (+18 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (21): canonical(), codes(), get(), labels(), Language, normalize(), The languages mangame can actually read manga in.  This is the *reading* languag, One language mangame can read in. (+13 more)

### Community 11 - "Community 11"
Cohesion: 0.19
Nodes (11): aggregate(), icon_state_for(), _phase(), resolve(), _tooltip(), announced_break(), latest(), series() (+3 more)

### Community 12 - "Community 12"
Cohesion: 0.17
Nodes (9): chapter_number(), _link(), _parse_datetime(), parse_feed(), _text(), The generic RSS/Atom adapter — how a new site becomes a config line., test_extraction(), TestChapterNumber (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.21
Nodes (17): is_enabled(), is_supported(), launch_command(), _linux_desktop_file(), _linux_enabled(), _linux_set(), _macos_enabled(), _macos_plist() (+9 more)

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (1): mangame — a tray-sized manga release radar.

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Numeric chapter order when parseable, falling back to publish time.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): 0.0-1.0 trust in this cadence, from sample size and regularity.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Has this client actually opened a connection pool yet?

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): A copy in which one tracked series has been edited in place.          Order is p

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): A copy with one series dropped.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Read settings, falling back to defaults on a missing or broken file.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Write settings atomically so a crash cannot truncate the file.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Looks up a menu label, falling back to English key by key.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Languages with a catalog, as ``{code: endonym}``, in menu order.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Colours for one icon state.      ``line`` is the outline. It is deliberately cho

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Simple async token bucket.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): What a previous response told us to send back next time.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Adapter-facing result. ``not_modified`` means "reuse what you had".

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Rate-limited, cache-aware JSON client shared by every adapter.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Looks up a menu label, falling back to English key by key.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Languages with a catalog, as ``{code: endonym}``, in menu order.

## Knowledge Gaps
- **67 isolated node(s):** `mangame — a tray-sized manga release radar.`, `Where mangame keeps its things, per platform.`, `Drop-in folder so users can add their own emblems without a rebuild.`, `User settings.  Stored as JSON rather than TOML on purpose: reading *and* writin`, `The identity a tracked series is stored under.      Lives with the model that ow` (+62 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 14`** (2 nodes): `mangame — a tray-sized manga release radar.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Numeric chapter order when parseable, falling back to publish time.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `0.0-1.0 trust in this cadence, from sample size and regularity.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Has this client actually opened a connection pool yet?`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `A copy in which one tracked series has been edited in place.          Order is p`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `A copy with one series dropped.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Read settings, falling back to defaults on a missing or broken file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Write settings atomically so a crash cannot truncate the file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Looks up a menu label, falling back to English key by key.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Languages with a catalog, as ``{code: endonym}``, in menu order.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Colours for one icon state.      ``line`` is the outline. It is deliberately cho`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Simple async token bucket.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `What a previous response told us to send back next time.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Adapter-facing result. ``not_modified`` means "reuse what you had".`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Rate-limited, cache-aware JSON client shared by every adapter.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Looks up a menu label, falling back to English key by key.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Languages with a catalog, as ``{code: endonym}``, in menu order.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `IconState` connect `Community 3` to `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 11`?**
  _High betweenness centrality (0.255) - this node is a cross-community bridge._
- **Why does `Translator` connect `Community 3` to `Community 0`, `Community 2`, `Community 4`, `Community 7`, `Community 9`, `Community 10`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `SettingsDialog` connect `Community 2` to `Community 3`, `Community 4`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Are the 177 inferred relationships involving `IconState` (e.g. with `MangameTray` and `The tray: one icon per tracked series, and a deliberately tiny menu.  The menu h`) actually correct?**
  _`IconState` has 177 INFERRED edges - model-reasoned connections that need verification._
- **Are the 146 inferred relationships involving `Translator` (e.g. with `SeriesCandidate` and `AddSeriesDialog`) actually correct?**
  _`Translator` has 146 INFERRED edges - model-reasoned connections that need verification._
- **Are the 127 inferred relationships involving `Settings` (e.g. with `MangameTray` and `The tray: one icon per tracked series, and a deliberately tiny menu.  The menu h`) actually correct?**
  _`Settings` has 127 INFERRED edges - model-reasoned connections that need verification._
- **Are the 119 inferred relationships involving `SeriesConfig` (e.g. with `MangameTray` and `The tray: one icon per tracked series, and a deliberately tiny menu.  The menu h`) actually correct?**
  _`SeriesConfig` has 119 INFERRED edges - model-reasoned connections that need verification._
