# Preparing the 2.0 release

The owner clarified the ordering on 2026-10-12: prepare migration, distributions and the cutover in
advance; spend the release version after the rest of the implementation and its acceptance checks pass.
`VERSION` stays a development snapshot throughout preparation. This page does not mark slice 8.5 done.

## Prove the distributions without publishing

Run from a clean candidate checkout:

```sh
make verify
make test-migration
make test-wheel
make test-executable
python3 scripts/tag-release.py --dry-run
```

The wheel is rebuilt from its source distribution with pinned tooling, installed in a fresh environment,
and exercised outside the checkout. The executable receives the same smoke: version, plugin material,
native command skills and adoption of existing UTF-8 code. Neither format bundles a language. Generation
against the packages people actually install is the separate published-package backstop.

The `release artifacts` workflow is manual and has read-only repository permission. After this workflow
lands on the default branch, build a specific reviewed revision on Linux, macOS and Windows:

```sh
gh workflow run release-artifacts.yml --ref main -f revision=main
gh run list --workflow release-artifacts.yml --limit 1
```

Use the run's actual identifier to inspect or download its artifacts. Each platform must pass both
smokes before it uploads, and `slipwai-revision.txt` records the checkout that was actually tested.
These builds create no tag, forge release or registry upload.

## Prepare the cutover

Keep all of these reviewable before cutting the release:

- Migration passes for both profiles, every supported backend and adopted repositories, including
  an installed 1.x base, renamed files, legacy package directories and in-flight work.
- The automated two-clone multiplayer acceptance exercise and fresh native-captain exercise have
  recorded outcomes. The owner accepted the automated exercise on 2026-10-12 in place of the live
  second-person/separate-hardware requirement; seeded interruption and ladder/gate stand-ins stay explicit.
- The reference pages, feature-to-delegate figures, version-1 comparison and assembled changelog describe
  the final tree.
- The published-package backstop passes against the candidate. Prepare any required package releases
  and channel updates before the keel's final cut.
- An upstream pull request retains this fork's history. Prepare the switch of package workflow `uses:`
  and `package_new.KEEL_REPO` to the canonical upstream, and removal of the development keel override
  from the channel. Apply that switch with the upstream merge, not while upstream still holds version 1.
- The final 1.x upgrade notice is prepared on its own branch and tested against an available 2.x result;
  it must not claim an unpublished release is available.

GitHub (`ROBCOATVG/slipwai`) is the canonical repository; the Gitea copy is retired. Keep publication
separate from artifact preparation. A passing artifact build is evidence about its recorded revision, not
permission to publish an arbitrary later commit.

## The final cut

After the prepared changes and required acceptance checks are complete, run the full gate on the final
rebased tree and inspect the release dry-run. Cut through `make release`, retain the resulting version,
changelog and tag as one release, and publish only the exact tagged tree that passed the platform and
published-package gates. The PyPI and executable publication route must be ready before spending the tag;
a tag with no working publication path is not a completed release.

## How a tag is published

`make release` writes `VERSION`, the changelog entry and the tag on one commit; `git push --follow-tags`
sends both to GitHub. The tag's own `verify` run then does three things in order, each only if the one
before passed:

1. **The gate** on the tagged commit, on Linux, macOS and Windows, and the docs job.
2. **`distributions`**: on each platform, the tag is checked against `VERSION`, and the wheel and the
   executable are built and smoked. The executable is named `slipwai-<version>-<platform>` with a
   `.sha256` beside it.
3. **`publish`**: the wheel and source distribution go to PyPI, and a GitHub release for the tag carries
   the three executables, their checksums and the Python distributions. A version with `dev`, `a`, `b` or
   `rc` in it is marked a pre-release.

PyPI takes the upload by **trusted publishing**: it accepts this repository's `verify.yml` running in the
`pypi` environment, and no token is stored anywhere. Set that up once on PyPI, under the `slipwai`
project's *Publishing* settings, with owner `ROBCOATVG`, repository `slipwai`, workflow `verify.yml` and
environment `pypi`. Until it is set up, `publish` fails at the upload, after the gate, so a tag pushed
before then spends its number without a release.

A fork's tag builds nothing: both jobs are limited to `ROBCOATVG/slipwai`.
