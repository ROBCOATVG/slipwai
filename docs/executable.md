# Install the command, or use the standalone executable

Both put a `slipwai` on the `PATH` that scaffolds without a factory checkout. The installed package needs
Python 3.11+ and an installer — **`uv` is the recommended one**, and it is worth having anyway, because a
generated project's `./init` uses `uv` to fetch Spec Kit; `pip` works too. The executable needs nothing but
Git.

## Install it with uv

Every public release is published to PyPI:

```sh
uv tool install slipwai
slipwai --version
```

`uv tool install` puts `slipwai` on the `PATH` in its own environment.
Inside an existing environment, `uv pip install slipwai` is the equivalent.
An organisation that mirrors PyPI may point uv at that mirror in its normal
configuration; `slipwai upgrade` honours the index recorded in uv's receipt.

No `uv`? Install it — `curl -LsSf https://astral.sh/uv/install.sh | sh`, or `brew install uv`,
or `pipx install uv` — or use `pip` below.

## Install it with pip

```sh
pip install slipwai
slipwai --version
```

The package carries the catalog, templates, skills, commands, frontend assets, wrappers and dependency locks
inside it, so an installed `slipwai` and a checkout's `./slipwai` produce the same repository from the same
answers.

## Use a released executable

Release archives contain a platform-native `slipwai` executable with the same material embedded. It requires
Git to create the new repository and initial commit, but it does not require Python. They are attached to
the tag they were built from, at
[git.treyco.dev/ROBCOATVG/slipwai/releases](https://git.treyco.dev/ROBCOATVG/slipwai/releases),
each with a `.sha256` beside it.

## Upgrade it

```sh
slipwai upgrade          # replace this copy with the newest release published
slipwai upgrade --pre    # count the snapshot of main as a version to upgrade to
slipwai upgrade --check  # say what is installed and what is published, and change nothing (--pre combines)
```

It works out which of the four ways this copy was installed and does the right thing for that one: a `uv`
tool is upgraded with `uv`, a package in an environment with that environment's `pip`, and the two that
cannot replace themselves from the inside — a running executable, a checkout that may hold local commits —
are told exactly what to do instead.

It asks the registry itself before any of that, rather than leaving the question to the installer, because
`uv tool upgrade` answers an index it cannot authenticate against with `Nothing to upgrade` and exit 0 — a
machine three versions behind, told it is current. Here a `401` is quoted as a `401`, with the two variables
to export. The index it asks is the one in the tool's own receipt, so a copy installed from a mirror is
checked against that mirror; `SLIPWAI_INDEX` overrides it, which is what a `pip`-installed copy behind a
different index wants.

PyPI also holds snapshots of `main` — for example `1.1.0.dev7`, published on every green push
([The snapshot of main](publishing.md#the-snapshot-of-main)). It is a pre-release, so `upgrade` passes it
over the way `pip` and `uv` do: the default is always the newest *release*. `slipwai upgrade --pre` counts
the snapshot too, and a copy that is itself a snapshot counts it without being asked — whoever installed
`1.1.0.dev4` was asking for `main`. Following the snapshot is temporary by construction: a snapshot sorts
below the release it leads to, so the first `upgrade` after that release is cut lands on it, and from a
release copy snapshots are ignored again unless `--pre` says otherwise. The snapshot executable is the
forge's `snapshot` pre-release, beside the releases.

The public version line begins at 1.0.0. An installation from the earlier
private line has a numerically higher version and therefore needs a one-time
replacement rather than `slipwai upgrade`:

```sh
uv tool uninstall slipwai
uv tool install slipwai
```

Then run `slipwai migrate` in each existing generated repository. The merge
accepts the lower public number; catch-up notes from the private version line
do not apply to this one-time transition.

## Run it

Interactively, one question at a time:

```sh
slipwai generate
```

Or with the answers, which is the form for scripts and CI:

```sh
slipwai generate my-product \
  --language go \
  --frontend react-vite \
  --profile standard \
  --output .
```

Unlike `./slipwai generate` in a checkout, an installed or packaged `slipwai` defaults its output parent to the
current working directory: it has no checkout to scaffold beside. `slipwai --version` reports the embedded
factory version, `slipwai upgrade` replaces it with the newest one published, and `slipwai add-service` /
`slipwai add-frontend` work from inside a generated project as they do from a checkout. Every flag behaves
as in [Scaffold a new project](generating.md).

## Build and package them yourself

The package, built into `dist/`, installed into a throwaway virtual environment and proved to scaffold
on its own:

```sh
make test-wheel
```

The executable for the current operating system and architecture, smoke-tested the same way, and the
release archive with its SHA-256 checksum written to `release/`:

```sh
make test-executable
make package-executable
```

Each first invocation installs its exactly pinned build tooling — `requirements-publish.txt`,
`requirements-build.txt` — into ignored `.build-tools/`. Linux builders also need the distribution's
`binutils` package (`objdump` and `objcopy`) for the executable. On a `v*` tag, `.github/workflows/package.yml`
repeats the executable's smoke test on Linux and publishes that archive — the forge has no macOS or Windows
runner, so a release carries the Linux binary and those two platforms build their own — and
`.github/workflows/publish-package.yml` publishes the package to the forge's registry — see
[Publish the factory](publishing.md).
