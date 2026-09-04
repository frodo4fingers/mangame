# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
uses [semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A first run now starts already following One Piece, with the emblem the app
  ships artwork for. An empty tracker could not demonstrate what the three
  icon states mean, and asked a new user to know what to search for before
  seeing anything work. Removing it is remembered like any other change, and
  every other series is still found through search.
- An OnePiece-Tube source for German readers. The official simulpub decides
  when a chapter is *scheduled*, but a fan translation often decides when one
  is first *readable*, and a tracker that only asks the publisher will show
  "expected Sunday" while the chapter is already on screen. Only chapters the
  site can actually serve are reported, so the icon never turns on for an
  entry that opens on nothing.

### Fixed

- Cadence learning no longer counts the same chapter twice when more than one
  source carries it. A mirror that relists a chapter days after the official
  release used to be read as a release of its own, which both invented an
  interval between a chapter and itself and made the gap to the genuinely next
  chapter look short. A fortnightly series tracked on two such sources settled
  on a three-day period and stopped learning its release weekday entirely.

## [0.1.0]

First release.

The `v0.1.0` tag is unsigned because tag signing was not configured for this
initial release.

### Added

- A tray icon per series, or one icon for the whole library, in three states:
  full colour when a chapter is waiting, grey when the next one is due, and a
  dark silhouette when a break has been announced.
- Polling that adapts to each series: rare while a title is far from its next
  chapter, frequent as the window approaches, and backing off again for
  dormant or ended series.
- Reading language as a first-class setting, with sources chosen to match it.
- Break detection from source metadata and from the gaps between releases.
- Start on login for Linux, Windows and macOS.
- A Diagnostics tab with copyable runtime and support-file information, plus
  rotating local logs for packaged GUI builds that have no console.
- A stream-free packaged smoke test that cannot hang a release indefinitely.
- Contributor-facing pull request, conduct, support, roadmap and artwork
  guidance.
- A one-PNG artwork workflow: drop a title-named image into the emblem
  directory and mangame derives the ready, due and break states automatically.
- Bundled artwork uses the same source-PNG generator and stores one 256px image
  per state instead of a twelve-resolution ladder.
- Release metadata agreement checks, dependency notices and SHA-256 checksums.
- Python 3.14 CI coverage and immutable current GitHub Action revisions.
- `MANGAME_HOME` puts settings, database, logs and artwork in one directory of your
  choosing — a portable install, or a second instance that leaves the first
  alone.
- Standalone builds for Linux, Windows and both macOS architectures, produced
  and smoke-tested by the release workflow.
- Continuous integration across three operating systems and Python 3.12–3.14,
  including a check that an installed wheel can still find its artwork.
- `AGENTS.md`, so the project's conventions travel with the repository instead
  of living in one maintainer's editor settings.
- A git-ignored `.env` for machine-local paths, with `.env.example` as the
  committed template. Read from the working directory, from beside the
  executable, or from the configuration directory, and never allowed to
  override a variable the real environment already set.
- `MANGAME_EMBLEM_DIR` keeps imported artwork in a directory of its own,
  wherever settings and database live.

### Fixed

- Test isolation no longer relies on the XDG variables, which Windows ignores;
  running the suite there would have written into the real user profile.
- Cross-platform CI now runs tests with the requested interpreter and validates
  generated artwork without depending on platform-specific Qt rasterisation.

[Unreleased]: https://github.com/frodo4fingers/mangame/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/frodo4fingers/mangame/releases/tag/v0.1.0
