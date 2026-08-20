# GitHub repository setup

These settings cannot live in Git. Apply them when the remote repository is
created.

## Publish

```bash
git remote add origin git@github.com:frodo4fingers/mangame.git
git push -u origin main
```

Enable Issues and Discussions. Keep Actions enabled for this repository.

## Protect `main`

Create a branch ruleset for `main`:

- require a pull request before merging;
- require one approval when a second maintainer exists;
- dismiss stale approvals after new commits;
- require conversation resolution;
- require every check from `.github/workflows/ci.yml`;
- require the branch to be up to date before merging;
- block force pushes and deletion;
- allow squash merges and automatically delete merged branches.

Do not require an approval while the project has only one maintainer; that
would make every maintenance change impossible.

## Security

Enable:

- private vulnerability reporting;
- Dependabot alerts and security updates;
- secret scanning and push protection;
- read-only default `GITHUB_TOKEN` permissions.

The workflows request write permissions only in the jobs that publish a
release or PyPI package.

## Labels

Create at least:

- `bug`
- `enhancement`
- `artwork`
- `dependencies`
- `good first issue`
- `help wanted`

Use milestones for release scope. Issues and milestones are the public
wishlist; do not mirror their status into `ROADMAP.md`.

## Apps and publishing

Install Renovate and allow it to read `renovate.json5`; Dependabot already
handles Python and GitHub Actions, while Renovate is restricted to pre-commit
hooks.

For PyPI, follow [RELEASING.md](RELEASING.md): configure a trusted publisher,
create the `pypi` environment and set `PUBLISH_TO_PYPI=true` only when the
project name is ready to publish.
