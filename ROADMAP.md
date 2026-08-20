# Roadmap

This document describes direction, not a second issue tracker. GitHub Issues
and milestones carry scope, ownership and status; this page should change only
when the direction changes.

## First public release

- Publish the repository, protect `main` with required CI checks and create a
  small labelled backlog for contributors. The exact one-time settings are in
  [docs/REPOSITORY_SETUP.md](docs/REPOSITORY_SETUP.md).
- Exercise the tray on Windows, macOS, KDE/Wayland and GNOME with the required
  AppIndicator extension.
- Publish release archives with third-party licence notices, checksums or
  attestations, and enable PyPI through a trusted publisher.
- Sign Windows builds and sign/notarise macOS builds when project credentials
  exist.

## Next

- Add source adapters only after inspecting real endpoint responses and
  documenting their rate limits and language guarantees.
- Add magazine skip calendars as a medium-confidence break signal.
- Improve diagnostics around repeated source failures without adding telemetry
  or sending user data anywhere.
- Evaluate native package formats after the portable archives have real usage
  data.

## Artwork wishlist

Bundled artwork stays deliberately small and generic. New emblems should fill
a broadly useful role, remain recognisable at 16 pixels and be original work;
series logos and character art are out of scope. The visual acceptance contract
is in [docs/ARTWORK.md](docs/ARTWORK.md).

Requests belong in issues labelled `artwork`; accepted work should also be
labelled `help wanted`. The existing pixels do not change merely because an
idea enters the wishlist: every visual change updates the approved contact
sheet and is reviewed explicitly.
