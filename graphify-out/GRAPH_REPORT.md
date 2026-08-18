# Graph Report - mangame  (2026-08-18)

## Corpus Check
- 52 files · ~49,265 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1102 nodes · 3679 edges · 24 communities detected
- Extraction: 41% EXTRACTED · 59% INFERRED · 0% AMBIGUOUS · INFERRED: 2161 edges (avg confidence: 0.6)
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

## God Nodes (most connected - your core abstractions)
1. `IconState` - 139 edges
2. `Translator` - 115 edges
3. `Settings` - 99 edges
4. `PublicationStatus` - 96 edges
5. `SourceSignal` - 85 edges
6. `SeriesConfig` - 84 edges
7. `HttpClient` - 84 edges
8. `Database` - 80 edges
9. `Library` - 80 edges
10. `Cadence` - 79 edges

## Surprising Connections (you probably didn't know these)
- `Database` --calls--> `db()`  [INFERRED]
  src/mangame/store/db.py → tests/test_store.py
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
Cohesion: 0.02
Nodes (133): AddSeriesDialog, Search and add, in one window., True between asking for a search and being handed its outcome., One series in the results list, with every source that offered it., SeriesCandidate, Which way round a silhouette is drawn., SilhouetteTone, available() (+125 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (92): The match that represents the group.          Ranked rather than "whichever sour, AniListSource, AniList adapter — the hiatus oracle.  AniList carries no chapter-level release t, One aliased GraphQL document covers up to :data:`MAX_ALIASES` series., Status-only source used to detect declared hiatuses., _title_of(), Capabilities, FetchRequest (+84 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (78): BaseModel, active(), from_announced_next(), from_status(), is_suspected(), merge(), Turn raw source signals into announced-break windows.  Break detection is ranked, The announced break covering ``now``, or the next one starting soon.      A brea (+70 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (48): BatchSource, Registry, Database, Library, The library: config + learned state + read state, folded into one view.  Both th, Reads and updates everything about the user's tracked series., Assemble one fully-populated series from config + database., Fold fresh source signals into stored state.          Returns the number of genu (+40 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (63): _blank(), emblem_name(), _fitted(), grayscale(), _inset(), install(), load(), Turning one picture into a three-state emblem set.  The tray says three things w (+55 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (28): group_matches(), primary(), _priority(), One dialog for finding a series and adding it.  Adding used to be a chain of mod, Collapse per-source matches into one candidate per series.      First-appearance, Fill the list with what the search found., The identity two matches must share to be the same series.      Deliberately the, title_key() (+20 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (23): _as_utc(), estimate(), expected_next(), _forward_run(), _intervals(), _is_weekly_multiple(), _numeric(), release_events() (+15 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (21): is_enabled(), is_supported(), launch_command(), _linux_desktop_file(), _linux_enabled(), _linux_set(), _macos_enabled(), _macos_plist() (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (26): available_emblems(), emblem_roots(), _find(), _hue_for(), icon_for(), _initial(), monogram(), Emblem resolution: series + state -> a tray-ready :class:`QIcon`.  Two mechanism (+18 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (21): canonical(), codes(), get(), labels(), Language, normalize(), The languages mangame can actually read manga in.  This is the *reading* languag, One language mangame can read in. (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (12): _backoff(), decide(), _jitter(), _ladder(), inputs(), test_each_distance_selects_its_tier(), TestApproachingTheDueDate, TestBackoff (+4 more)

### Community 11 - "Community 11"
Cohesion: 0.19
Nodes (11): aggregate(), icon_state_for(), _phase(), resolve(), _tooltip(), announced_break(), latest(), series() (+3 more)

### Community 12 - "Community 12"
Cohesion: 0.2
Nodes (2): picture(), TestArtworkTab

### Community 13 - "Community 13"
Cohesion: 0.26
Nodes (5): _link(), _parse_datetime(), parse_feed(), _text(), TestParseFeed

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
Nodes (1): Simple async token bucket.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): What a previous response told us to send back next time.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Adapter-facing result. ``not_modified`` means "reuse what you had".

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Rate-limited, cache-aware JSON client shared by every adapter.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Looks up a menu label, falling back to English key by key.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Languages with a catalog, as ``{code: endonym}``, in menu order.

## Knowledge Gaps
- **59 isolated node(s):** `mangame — a tray-sized manga release radar.`, `Where mangame keeps its things, per platform.`, `Drop-in folder so users can add their own emblems without a rebuild.`, `User settings.  Stored as JSON rather than TOML on purpose: reading *and* writin`, `The identity a tracked series is stored under.      Lives with the model that ow` (+54 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 12`** (25 nodes): `._on_name_typed()`, `.set_source()`, `picture()`, `TestArtworkTab`, `.test_a_name_the_user_typed_is_left_alone()`, `.test_a_picture_matching_nothing_cannot_be_imported()`, `.test_a_picture_named_after_a_manga_is_offered_to_it()`, `.test_a_shared_emblem_asks_for_a_name_instead()`, `.test_a_shared_emblem_is_installed_without_touching_any_manga()`, `.test_all_three_states_are_previewed()`, `.test_an_imported_emblem_can_be_picked_straight_away()`, `.test_an_imported_emblem_can_be_removed_again()`, `.test_an_unreadable_file_says_so_instead_of_importing_it()`, `.test_clearing_a_shared_name_blocks_the_import()`, `.test_importing_does_not_look_like_a_settings_edit()`, `.test_importing_writes_the_emblem_and_hands_it_to_the_manga()`, `.test_nothing_can_be_imported_before_a_picture_is_chosen()`, `.test_only_the_no_match_line_is_set_in_bold()`, `.test_picking_a_manga_by_hand_unblocks_an_unmatched_picture()`, `.test_switching_tone_redraws_the_break_preview()`, `.test_the_button_names_the_manga_it_is_about_to_change()`, `.test_the_empty_tab_shows_no_verdict_and_no_preview()`, `.test_the_list_says_which_manga_wears_each_emblem()`, `.test_the_suggested_name_follows_the_picture()`, `.test_the_preview_row_keeps_its_shape_before_and_after_a_picture()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (2 nodes): `mangame — a tray-sized manga release radar.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Numeric chapter order when parseable, falling back to publish time.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `0.0-1.0 trust in this cadence, from sample size and regularity.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Has this client actually opened a connection pool yet?`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Simple async token bucket.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `What a previous response told us to send back next time.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Adapter-facing result. ``not_modified`` means "reuse what you had".`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Rate-limited, cache-aware JSON client shared by every adapter.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Looks up a menu label, falling back to English key by key.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Languages with a catalog, as ``{code: endonym}``, in menu order.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `IconState` connect `Community 0` to `Community 2`, `Community 3`, `Community 4`, `Community 7`, `Community 8`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.234) - this node is a cross-community bridge._
- **Why does `Database` connect `Community 3` to `Community 0`, `Community 2`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `HttpClient` connect `Community 1` to `Community 3`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 136 inferred relationships involving `IconState` (e.g. with `MangameTray` and `The tray: one icon per tracked series, and a deliberately tiny menu.  The menu h`) actually correct?**
  _`IconState` has 136 INFERRED edges - model-reasoned connections that need verification._
- **Are the 111 inferred relationships involving `Translator` (e.g. with `SeriesCandidate` and `AddSeriesDialog`) actually correct?**
  _`Translator` has 111 INFERRED edges - model-reasoned connections that need verification._
- **Are the 91 inferred relationships involving `Settings` (e.g. with `MangameTray` and `The tray: one icon per tracked series, and a deliberately tiny menu.  The menu h`) actually correct?**
  _`Settings` has 91 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `PublicationStatus` (e.g. with `LearnedState` and `PollState`) actually correct?**
  _`PublicationStatus` has 93 INFERRED edges - model-reasoned connections that need verification._