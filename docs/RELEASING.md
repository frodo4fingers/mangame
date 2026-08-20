# Releasing

Releases are built from tags by `.github/workflows/release.yml`. Do not upload
locally built binaries to a release; the workflow is the provenance record.

## Before tagging

1. Start from a clean `main` branch.
2. Move the completed entries from `CHANGELOG.md`'s Unreleased section into a
   section named for the release.
3. Update the only version number, `__version__` in
   `src/mangame/__init__.py`.
4. Run the full gate from `CONTRIBUTING.md`.
5. Run `actionlint` with `shellcheck` installed.
6. Exercise a development build on the real tray environments affected by the
   release. For a general release that means Windows, macOS, KDE/Wayland and
   GNOME with the AppIndicator extension.

The tag, package version and changelog section must agree:

```bash
uv run python tools/check_release.py v0.2.0
```

## Publish

```bash
git tag -s v0.2.0
git push origin main v0.2.0
```

Use an unsigned tag only when signing is not configured, and record that
exception in the release notes.

The workflow builds Linux, Windows and both macOS architectures, runs the
stream-free packaged smoke test, builds the wheel and source distribution, and
publishes SHA-256 checksums with the files.

## PyPI

Register this repository as a
[trusted publisher](https://docs.pypi.org/trusted-publishers/) for `mangame`,
create a GitHub environment named `pypi`, and set the repository variable
`PUBLISH_TO_PYPI` to `true`. No API token belongs in repository secrets.

## Signing

macOS signing/notarisation and Windows code signing remain disabled until the
project has the required certificates. Never weaken a runner or bypass an
operating-system warning to simulate signing.
