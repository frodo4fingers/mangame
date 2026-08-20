# Security policy

## Supported versions

The latest release. This is a small project; fixes go into the next release
rather than into patches for older ones.

## Reporting a vulnerability

Please report privately through GitHub's
[security advisories](https://github.com/frodo4fingers/mangame/security/advisories/new)
rather than opening a public issue. You should get a reply within a week.

## What the app does with your machine

Worth knowing before you audit it, and stated so you do not have to take it on
trust:

- **It talks only to the manga sources it polls.** There is no telemetry, no
  analytics, no crash reporting and no update check. The sources it may contact
  are the ones listed in the README, and only those matching your reading
  language.
- **It has no accounts and does not ask for credentials.** Settings are not
  encrypted, so do not put tokens into source URLs. Treat the library, local
  paths and logs as private even though the app stores them only on this
  machine.
- **It stores everything locally** — a JSON settings file, a SQLite database
  any artwork you import and rotating diagnostic logs. See *Where things are
  stored* in the README, or set `MANGAME_HOME` to put it all somewhere you
  choose. Review a log before sharing it: source errors may include URLs or
  local paths.
- **It never executes anything it downloads.** Responses are parsed as JSON or
  XML into validated Pydantic models; images you import are read with Qt's
  image loaders and re-encoded as PNG.
- **Start on login** writes an XDG `.desktop` file, a per-user `HKCU` registry
  value, or a `LaunchAgent` plist, depending on the platform. All three are
  per-user and need no administrator rights.

## About the released builds

Binaries are built by GitHub Actions from a tagged commit, using the same
`packaging/mangame.spec` you can run yourself.

Each packaged GUI build runs a stream-free smoke mode before publication, and
the release includes SHA-256 checksums. Windowed Windows builds have no console;
runtime errors are therefore written to the local rotating log and exposed
through Settings → Diagnostics.

The macOS builds are **not signed or notarised** — this project has no Apple
Developer certificate — so Gatekeeper will object to the first launch. If that
is not acceptable to you, build from source instead.
