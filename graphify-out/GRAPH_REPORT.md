# Graph Report - mangame  (2026-08-18)

## Corpus Check
- 53 files · ~55,878 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1210 nodes · 4189 edges · 29 communities detected
- Extraction: 39% EXTRACTED · 61% INFERRED · 0% AMBIGUOUS · INFERRED: 2564 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
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

## God Nodes (most connected - your core abstractions)
1. `IconState` - 193 edges
2. `Translator` - 161 edges
3. `Settings` - 146 edges
4. `SeriesConfig` - 133 edges
5. `PublicationStatus` - 96 edges
6. `Database` - 95 edges
7. `SettingsDialog` - 95 edges
8. `Library` - 95 edges
9. `SourceSignal` - 85 edges
10. `HttpClient` - 84 edges

## Surprising Connections (you probably didn't know these)
- `Database` --calls--> `db()`  [INFERRED]
  src/mangame/store/db.py → tests/test_service.py
- `Database` --calls--> `db()`  [INFERRED]
  src/mangame/store/db.py → tests/test_store.py
- `utcnow()` --calls--> `now()`  [INFERRED]
  src/mangame/domain/breaks.py → tests/conftest.py
- `IconState` --uses--> `TestNaming`  [INFERRED]
  src/mangame/domain/models.py → tests/test_artwork.py
- `IconState` --uses--> `Deriving the grey and break states from one picture.  These run without a displa`  [INFERRED]
  src/mangame/domain/models.py → tests/test_artwork.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (109): AniListSource, AniList adapter — the hiatus oracle.  AniList carries no chapter-level release t, One aliased GraphQL document covers up to :data:`MAX_ALIASES` series., Status-only source used to detect declared hiatuses., _title_of(), BatchSource, Capabilities, FetchRequest (+101 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (105): BaseModel, active(), from_announced_next(), from_status(), is_suspected(), merge(), Turn raw source signals into announced-break windows.  Break detection is ranked, The announced break covering ``now``, or the next one starting soon.      A brea (+97 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (117): The match that represents the group.          Ranked rather than "whichever sour, Which way round a silhouette is drawn., SilhouetteTone, available(), Menu translations.  The whole UI is a handful of menu labels, so a plain dict pe, Looks up a menu label, falling back to English key by key., Languages with a catalog, as ``{code: endonym}``, in menu order., Translator (+109 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (29): A copy with one series dropped., A copy in which one tracked series has been edited in place.          Order is p, QDialog, classify(), emblem_choices(), file_filter(), flatten(), heading() (+21 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (61): AddSeriesDialog, Search and add, in one window., True between asking for a search and being handed its outcome., Fill the list with what the search found., One series in the results list, with every source that offered it., SeriesCandidate, SourceMatch, Database (+53 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (63): _blank(), emblem_name(), _fitted(), grayscale(), _inset(), install(), load(), Turning one picture into a three-state emblem set.  The tray says three things w (+55 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (41): available_emblems(), emblem_roots(), _find(), _hue_for(), icon_for(), _initial(), monogram(), Emblem resolution: series + state -> a tray-ready :class:`QIcon`.  Two mechanism (+33 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (31): _as_utc(), estimate(), expected_next(), _forward_run(), _intervals(), _is_weekly_multiple(), _numeric(), Learn a series' release rhythm from nothing but publication timestamps.  This is (+23 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (26): group_matches(), primary(), _priority(), One dialog for finding a series and adding it.  Adding used to be a chain of mod, Collapse per-source matches into one candidate per series.      First-appearance, The identity two matches must share to be the same series.      Deliberately the, title_key(), The identity a tracked series is stored under.      Lives with the model that ow (+18 more)

### Community 9 - "Community 9"
Cohesion: 0.13
Nodes (11): Poller, RuntimeError, chapter(), db(), FakeRegistry, FakeSource, settings_with(), TestLanguageRouting (+3 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (21): canonical(), codes(), get(), labels(), Language, normalize(), The languages mangame can actually read manga in.  This is the *reading* languag, One language mangame can read in. (+13 more)

### Community 11 - "Community 11"
Cohesion: 0.21
Nodes (17): is_enabled(), is_supported(), launch_command(), _linux_desktop_file(), _linux_enabled(), _linux_set(), _macos_enabled(), _macos_plist() (+9 more)

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (1): mangame — a tray-sized manga release radar.

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Numeric chapter order when parseable, falling back to publish time.

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): 0.0-1.0 trust in this cadence, from sample size and regularity.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Has this client actually opened a connection pool yet?

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): A copy in which one tracked series has been edited in place.          Order is p

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): A copy with one series dropped.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Read settings, falling back to defaults on a missing or broken file.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Write settings atomically so a crash cannot truncate the file.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Looks up a menu label, falling back to English key by key.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Languages with a catalog, as ``{code: endonym}``, in menu order.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Colours for one icon state.      ``line`` is the outline. It is deliberately cho

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Simple async token bucket.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): What a previous response told us to send back next time.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Adapter-facing result. ``not_modified`` means "reuse what you had".

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Rate-limited, cache-aware JSON client shared by every adapter.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Looks up a menu label, falling back to English key by key.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Languages with a catalog, as ``{code: endonym}``, in menu order.

## Knowledge Gaps
- **68 isolated node(s):** `mangame — a tray-sized manga release radar.`, `Where mangame keeps its things, per platform.`, `Drop-in folder so users can add their own emblems without a rebuild.`, `User settings.  Stored as JSON rather than TOML on purpose: reading *and* writin`, `The identity a tracked series is stored under.      Lives with the model that ow` (+63 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 12`** (2 nodes): `mangame — a tray-sized manga release radar.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `Numeric chapter order when parseable, falling back to publish time.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `0.0-1.0 trust in this cadence, from sample size and regularity.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Has this client actually opened a connection pool yet?`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `A copy in which one tracked series has been edited in place.          Order is p`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `A copy with one series dropped.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Read settings, falling back to defaults on a missing or broken file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Write settings atomically so a crash cannot truncate the file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Looks up a menu label, falling back to English key by key.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Languages with a catalog, as ``{code: endonym}``, in menu order.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Colours for one icon state.      ``line`` is the outline. It is deliberately cho`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Simple async token bucket.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `What a previous response told us to send back next time.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Adapter-facing result. ``not_modified`` means "reuse what you had".`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Rate-limited, cache-aware JSON client shared by every adapter.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Looks up a menu label, falling back to English key by key.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Languages with a catalog, as ``{code: endonym}``, in menu order.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `IconState` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 9`?**
  _High betweenness centrality (0.256) - this node is a cross-community bridge._
- **Why does `Translator` connect `Community 2` to `Community 0`, `Community 3`, `Community 4`, `Community 6`, `Community 8`, `Community 10`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `SettingsDialog` connect `Community 3` to `Community 2`, `Community 4`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Are the 190 inferred relationships involving `IconState` (e.g. with `MangameTray` and `The tray: one icon per tracked series, and a deliberately tiny menu.  The menu h`) actually correct?**
  _`IconState` has 190 INFERRED edges - model-reasoned connections that need verification._
- **Are the 157 inferred relationships involving `Translator` (e.g. with `SeriesCandidate` and `AddSeriesDialog`) actually correct?**
  _`Translator` has 157 INFERRED edges - model-reasoned connections that need verification._
- **Are the 138 inferred relationships involving `Settings` (e.g. with `MangameTray` and `The tray: one icon per tracked series, and a deliberately tiny menu.  The menu h`) actually correct?**
  _`Settings` has 138 INFERRED edges - model-reasoned connections that need verification._
- **Are the 130 inferred relationships involving `SeriesConfig` (e.g. with `MangameTray` and `The tray: one icon per tracked series, and a deliberately tiny menu.  The menu h`) actually correct?**
  _`SeriesConfig` has 130 INFERRED edges - model-reasoned connections that need verification._
