# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
uses [semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A Diagnostics tab with copyable runtime and support-file information, plus
  rotating local logs for packaged GUI builds that have no console.
- A stream-free packaged smoke test that cannot hang a release indefinitely.
- Contributor-facing pull request, conduct, support, roadmap and artwork
  guidance.
- An approved icon contact sheet and generated-artwork contract that catches
  stale SVGs, missing sizes and unreviewed pixel changes.
- Release metadata agreement checks, dependency notices and SHA-256 checksums.
- Python 3.14 CI coverage and immutable current GitHub Action revisions.
- `MANGAME_HOME` puts settings, database, logs and artwork in one directory of your
  choosing — a portable install, or a second instance that leaves the first
  alone.
- Standalone builds for Linux, Windows and both macOS architectures, produced
  and smoke-tested by the release workflow.
- Continuous integration across three operating systems and two Python
  versions, including a check that an installed wheel can still find its
  artwork.
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

## [0.1.0]

First release.

- A tray icon per series, or one icon for the whole library, in three states:
  full colour when a chapter is waiting, grey when the next one is due, and a
  dark silhouette when a break has been announced.
- Polling that adapts to each series: rare while a title is far from its next
  chapter, frequent as the window approaches, and backing off again for
  dormant or ended series.
- Reading language as a first-class setting, with sources chosen to match it.
- Break detection from source metadata and from the gaps between releases.
- Bundled emblems, plus drop-in artwork of your own converted to all three
  states on import.
- Start on login for Linux, Windows and macOS.

[Unreleased]: https://github.com/frodo4fingers/mangame/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/frodo4fingers/mangame/releases/tag/v0.1.0
