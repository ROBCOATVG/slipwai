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

Inspect every check without changing anything:

```sh
python3 scripts/tag-release.py --dry-run
```

A `v*` tag runs the complete `verify.yml` gate against the tagged commit. Only
after every gate job passes does CI:

1. build and smoke-test the standalone executable;
2. attach it to the canonical Gitea release; and
3. build, install, smoke-test, and upload the wheel to PyPI.

The first public release is the one exception to bump arithmetic:
`1.0.0.dev0` has no released predecessor. Its fragments describe the release,
`make release` writes the first `## 1.0.0` entry without a bump label, and the
open commit moves `main` to `1.0.1.dev0`.

## Release authority and the GitHub mirror

The publish jobs are guarded to run only when `github.server_url` is
`https://git.treyco.dev`. GitHub may run the same verification jobs after the
mirror receives a commit or tag, but it does not upload the package or create a
second release.

Configure the canonical Gitea repository with:

- `PYPI_TOKEN`: a PyPI API token able to publish `slipwai`;
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
