# Publishing Slipwai

The canonical repository is
[`git.treyco.dev/ROBCOATVG/slipwai`](https://git.treyco.dev/ROBCOATVG/slipwai).
GitHub is a public push-mirror, not a second release authority.

## Cutting a release

`main` carries the release it is working towards as a snapshot. For example,
`VERSION` reads `1.3.0.dev0`; CI turns each green `main` commit into a uniquely
numbered development release such as `1.3.0.dev7`.

`make release` makes and atomically pushes two commits and one tag:

```text
Release 1.3.0    VERSION 1.3.0.dev0 → 1.3.0; assemble changelog; tag v1.3.0
Open 1.3.1       VERSION 1.3.0 → 1.3.1.dev0, marked [skip ci]
git push --atomic origin main v1.3.0
```

The open commit is marked `[skip ci]` so the forge creates no run for it. It
raises `VERSION` and touches nothing else, on a tree the tag's own gate has just
passed; a second full run would prove the same thing and publish a `.dev1`
snapshot of code identical to the release beside it. The next change to `main`
is verified as itself.

Gitea matches that marker **anywhere** in the commit message, subject and body
alike — where GitHub reads only the first two lines. So a commit whose message
merely mentions the marker in prose silently skips its own run, and the first
sign of it is a green `main` with no run behind it. Call it "the skip-ci
marker" when writing about it; spell it out only when you mean it.

Inspect every check without changing anything:

```sh
python3 scripts/tag-release.py --dry-run
```

A `v*` tag runs the complete `verify.yml` gate against the tagged commit. Only
after every gate job passes does CI:

1. build and smoke-test the standalone executable;
2. attach it to the canonical Gitea release; and
3. build, install, smoke-test, and upload the wheel to PyPI.

## Cutting a release from the forge

The same release, without a checkout: **Actions → release → Run workflow** on
the canonical Gitea repository. It runs `scripts/tag-release.py` — the script
above, unchanged — so every refusal a laptop meets holds there too.

The form asks for two things:

- **version** — the release you mean to cut, e.g. `1.0.1`. It is held against
  what `main` carries, so a mis-click cannot spend a number nobody meant.
- **mode** — `dry-run` (the default) runs every check and writes nothing;
  `cut-the-release` commits, tags and pushes.

Before the script runs, the workflow also refuses a commit that is not already
green: the head of `main` must have a completed, successful `verify` run of its
own. The tag starts a run of its own and nothing publishes behind a red one, but
the tag would still be pushed — and a number is never reused.

The push is made with a personal access token rather than the job's own, and
that is not a preference. The release is published by the run the `v*` tag
starts, and a forge that declines to start runs for its own token would leave
the tag pushed with nothing built from it. `actions/checkout` runs with
`persist-credentials: false` for the same reason: the token it would otherwise
persist wins over the one the push is meant to use.

The first public release is the one exception to bump arithmetic:
`1.0.0.dev0` has no released predecessor. Its fragments describe the release,
`make release` writes the first `## 1.0.0` entry without a bump label, and the
open commit moves `main` to `1.0.1.dev0`.

## Release authority and the GitHub mirror

[github.com/ROBCOATVG/slipwai](https://github.com/ROBCOATVG/slipwai) is a
push-mirror of this repository and the public issue and pull request front
door. It is not a second release authority and it verifies nothing: Actions are
disabled on it, so a mirrored commit or tag runs no jobs there at all. The
publish jobs are guarded to run only when `github.server_url` is
`https://git.treyco.dev`, which is the second of the two locks rather than the
only one.

The canonical instance is sign-in only — an anonymous visitor is redirected to
a login page and sees no code, no issues, and no run logs — so the mirror is
also the only place the source is publicly readable. A signed-in user of the
instance reads this repository in full, run logs included.

Sync is a Gitea push mirror configured on the canonical repository under
**Settings → Mirror Settings**, not anything under `.github/workflows/`. Two
consequences are worth knowing before changing either side:

- It pushes *every* ref, so the moving `snapshot` tag lands on GitHub beside
  the `v*` tags, with no release attached to it there.
- It force-updates, so a branch pushed straight to GitHub is overwritten at the
  next sync. `main` carries no branch protection on the mirror for that reason:
  protection would reject the mirror's own push and sync would stop silently.

Mirror pushes authenticate with a GitHub personal access token holding write
access to the mirror, entered in those mirror settings. It is a Gitea mirror
credential rather than an Actions secret, so it is not in the list below and no
workflow can read it.

Configure the canonical Gitea repository with:

- `PYPI_TOKEN`: a PyPI API token able to publish `slipwai`;
- `RELEASE_TOKEN`: a Gitea personal access token with write access to this
  repository, used only by the `release` workflow above to push `main` and the
  tag. Needed only if releases are cut from the forge rather than a checkout;
- `RELEASE_USERNAME`: the login that token belongs to, if it is not the login
  of whoever dispatches the workflow;
- the normal Gitea Actions token permissions needed to attach release assets.

PyPI versions are immutable. A retry may upload a missing file for the same
version, but a published file cannot be replaced. Development snapshots
therefore use a new `.dev<N>` version on every green push; old snapshots remain
on PyPI.

## Retry a failed upload

The dispatch-only workflows under `.github/workflows/` retry packaging after a
tag's gate passed but an upload failed. They build the artefact from the tag
while running the corrected publishing code from `main`.

From a trusted workstation:

```sh
PYPI_TOKEN='pypi-…' make publish-wheel \
  PYPI_URL=https://upload.pypi.org/legacy/ \
  PYPI_INDEX=https://pypi.org/simple \
  PYPI_USER=__token__

GITEA_TOKEN='…' make publish-release \
  FORGE_URL=https://git.treyco.dev \
  FORGE_REPO=ROBCOATVG/slipwai \
  TAG=v1.0.0
```

## The snapshot of `main`

`scripts/snapshot-version.py` combines the base in `VERSION` with the commit
count since the newest release tag. It changes only the CI checkout, so
`VERSION` remains the single source of truth.

A `.dev` version is a PEP 440 pre-release. Normal `pip install slipwai`,
`uv tool install slipwai`, and `slipwai upgrade` ignore it. To follow snapshots:

```sh
uv tool install slipwai --prerelease allow
slipwai upgrade --pre
```

The standalone snapshot executable remains the canonical forge's moving
`snapshot` pre-release. Unlike a `v*` release tag, that marker may move.

## Serving rendered pages from Gitea

Gitea has no Pages feature, so `scripts/gitea-pages.py` can export each local
repository's `pages` branch and serve it at
`http://localhost:3301/<owner>/<repo>/`. See the script's module documentation
and `./scripts/install-gitea-pages` for local-host configuration.
