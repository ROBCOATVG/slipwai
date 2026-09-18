# Contributing to Slipwai

Thank you for improving Slipwai.

## Where work happens

The canonical repository is
[git.treyco.dev/ROBCOATVG/slipwai](https://git.treyco.dev/ROBCOATVG/slipwai).
[GitHub](https://github.com/ROBCOATVG/slipwai) is its public mirror and the
public issue and contribution front door.

Open issues and pull requests on GitHub. The canonical instance is not open to
the public, so the mirror is where the source is readable and where a change is
proposed. Maintainers land accepted changes canonically and the mirror syncs
from there; that sync force-updates every branch, so a branch pushed straight
to GitHub is overwritten rather than reviewed. Work from a fork.

Nothing will report a pass or a failure on your pull request. The gate lives on
the canonical instance and Actions are disabled on the mirror, which is why
running `make verify` yourself is not optional — a maintainer runs the same
gate canonically before landing the change.

Do not open a public issue for a vulnerability; follow
[SECURITY.md](SECURITY.md).

## Before opening a pull request

1. Keep the change focused and include tests for changed behaviour.
2. Run `make verify`; it is the same lint, type, structure, and test gate CI
   runs.
3. For a user-visible change under `assets/`, `catalog.json`, or
   `src/slipwai/`, add a fragment under `changelog.d/` as described in
   `changelog.d/README.md`.
4. Preserve every nested third-party `LICENSE` and `NOTICE`. Do not edit an
   adapted skill without checking its adjacent provenance notes.

See [docs/maintaining.md](docs/maintaining.md) for the source layout and local
tooling.

By contributing, you agree that your contribution is licensed under the
repository's MIT License, subject to any narrower nested licence that applies
to the files you change.
