"""What `slipwai package new` writes, as text.

Prose rather than logic, and the whole of `package_new`'s length — so it lives here and that module
stays the few dozen lines that decide *which* of these a package gets and what goes in their blanks.
Every `TODO` in them is a decision the keel cannot make for a publisher.
"""
from __future__ import annotations

ENTRY_POINT = '''#!/usr/bin/env python3
"""{title}: what `./init --extension {name}` does in a project.

This runs inside a generated or adopted project, which has no slipwai to import — the standard library only,
like every other script under `scripts/`. It is held to the six obligations, and each one below is marked
where it is met so that a change can see what it is breaking.

It answers two points of the keel's closed set, because `extension.json` declares it at both: `init`, the
election, and `project`, every re-projection — `make agents`, `slipwai migrate`, `./init --integration`.
`SLIPWAI_POINT` says which, and at `project` nothing is installed: a re-projection happens often and is not
an election. Declare another script at either point and it is fired instead of this one.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

def project_root() -> Path:
    """The project this is installed in: the nearest parent holding `project.json`, falling back to three up.

    Three up is where `scripts/extensions/<key>/init.py` sits, and counting parents is right until somebody
    moves the script or a layout puts the delivery files under a subdirectory — which `layout.delivery`
    does. So the marker is looked for first and the count is only the fallback.
    """
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return here.parents[3]


ROOT = project_root()
BEGIN = "<!-- extension:{name}:begin -->"
END = "<!-- extension:{name}:end -->"
BLOCK = """TODO: what the agent needs to know about {name} — the command it runs, what it answers, when to
reach for it. One short section; this is read on every turn."""


def say(message: str) -> None:
    print(f"[{name}] {{message}}")


def install_tool() -> bool:
    """TODO: install whatever this extension needs, and return whether it is there now.

    Obligation 2, non-fatal: a tool that cannot be installed on this machine is said and returns False. The
    project still works; what this extension adds does not, and the message says how to get it.
    Obligation 5, recovers: the message names the command that fixes it.
    """
    say("TODO: nothing to install yet")
    return True


def project_guidance() -> None:
    """Obligation 3, projects: the block is marker-fenced and replaced whole.

    Obligation 1, idempotent: a second run rewrites the same block rather than appending a second one.
    Obligation 6, merges: everything outside the markers is a person's and is left exactly as it was.
    """
    agents = ROOT / "AGENTS.md"
    text = agents.read_text(encoding="utf-8") if agents.is_file() else ""
    block = f"{{BEGIN}}\\n\\n## {title}\\n\\n{{BLOCK}}\\n\\n{{END}}"
    if BEGIN in text and END in text:
        head, rest = text.split(BEGIN, 1)
        text = head + block + rest.split(END, 1)[1]
    else:
        text = (text.rstrip() + "\\n\\n" + block + "\\n") if text.strip() else block + "\\n"
    agents.write_text(text, encoding="utf-8")
    say("AGENTS.md block written")


def main() -> int:
    if os.environ.get("SLIPWAI_POINT") == "project":
        project_guidance()  # a re-projection, not an election: install nothing
        return 0
    if not install_tool():
        return 0  # obligation 2: not fatal to the rest of `./init`
    project_guidance()
    # Obligation 4, gated: if this extension writes an index, a cache or a lock, ship a
    # `scripts/check-{name}.py` that refuses a stale one, and write it from here.
    say("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

README = '''# {title}

A slipwai extension: optional dev tooling a project elects at `./init`.

TODO: what this installs, and what it is for.

## Installing

```sh
{command} extension install <this directory, or its git URL>
```

Then, in a project:

```sh
./init --extension {name}
```

## The six obligations

`{command} extension check .` prints these; the conformance suite runs them.

{obligations}
'''

LANGUAGE_README = '''# {title}

A slipwai language package: it answers the backend protocol, and `slipwai generate --backend {name}` writes a
skeleton with it.

TODO: what this language and framework are, in two sentences.

## Installing

```sh
{command} language install <this directory>
```

## Checking it

```sh
{command} package check .
```

Every required member answered, and the generated project built and tested.
'''


QUICKSTART_README = '''# {title}

A slipwai quickstart: the languages to install, the answers to give and the extensions to elect, settled
once and given a name. `slipwai generate <project> --quickstart {name}` carries it out, and
`slipwai quickstart show {name}` says in plain words what it would do first.

TODO: what kind of product this suits, in two sentences. Write it for somebody who has never installed a
language package — the `suits` line in `quickstart.json` is the row they choose it by.

## Checking it

```sh
{command} package check .
```

That it reads, that every package it names is named by a **range** rather than by one version, and what it
would answer. A quickstart that pinned a version would hold every team that installs it to the day it was
written.

## Publishing it

```sh
{command} package release .
{command} package register . --channel <a channel checkout>
```
'''


#: The package's own `make`. Three targets, because a publisher has three questions: is it right, what do I
#: ship, and where does it go. Each is the keel's verb with the package's own directory already filled in, so
#: a publisher who forgets the flags still runs the right thing.
MAKEFILE = """# {name}: what a publisher runs. The keel is `slipwai`; install it with `pip install slipwai`.
.DEFAULT_GOAL := check
CHANNEL ?= ../slipwai-index

.PHONY: check version release register
check: ## Run the conformance suite this package's kind is held to
	slipwai package check .

version: ## Cut a release: assemble changelog.d/ into CHANGELOG.md, write VERSION, delete the fragments
	slipwai package version .

release: check ## Build the release file and its index entry under dist/
	slipwai package release . --out dist

register: check ## Build it and write it into a channel checkout (CHANNEL=<directory>)
	slipwai package register . --channel $(CHANNEL)
"""

#: The package's CI: the keel's reusable workflow, called rather than copied, so a fix to it reaches every
#: package. **It is the package's contract test**, so it runs from the package's side against both ends of the
#: contract: the newest published keel its `core` range takes, and the keel's `main` — on every push, and
#: every night, so a keel change that breaks this package is a red run here the next morning rather than a
#: surprise in somebody's generation (`docs/backend-protocol.md`, *Compatibility*).
WORKFLOW = """name: verify

on:
  push:
    branches: [main]
    # A tag is what publishes. A green run on `main` is a package that works; it is not a package
    # anybody asked for, and publishing every commit is how a chandlery fills with versions nobody
    # chose. `git tag v1.1.0 && git push --follow-tags` is the whole of releasing.
    tags: ['v*']
  pull_request:
  # Every night, against the keel's `main`, whether or not this package changed: the keel moves without
  # telling anybody, and this is how a package hears that it did.
  schedule:
    - cron: '23 4 * * *'
  # Asking for the matrix on a branch nobody has merged yet. On `main` and on a tag it runs anyway —
  # see the `matrix:` line below — so this is for checking a change before it gets there.
  #
  #   gh workflow run verify.yml -R <owner>/<repo> -f matrix=true
  workflow_dispatch:
    inputs:
      matrix:
        description: Run the generated-variant matrix too — builds images and starts containers
        type: boolean
        default: false

# A called workflow cannot ask for more than its caller has, and the publish job attaches the release to
# this repository's own tag — so the permission is granted here or that job never starts. `contents: write`
# is this repository's own contents and nobody else's; the channel is reached with a token, not with this.
permissions:
  contents: write

jobs:
  conformance:
    strategy:
      fail-fast: false
      matrix:
        # '' is the newest published keel this package's `core` range takes; the second is the keel's `main`,
        # the side of the contract that has not been released yet.
        keel: ['', 'git+https://github.com/{keel}@main']
    uses: {keel}/.github/workflows/package.yml@main
    with:
      package: {name}
      kind: {kind}
      # **The two-gate split, for a package.** A pull request gets conformance, which is the fast half and
      # the one an author runs over and over. `main` and a tag get the matrix as well — every generated
      # variant of every backend, each held to its own native gate — because that is the integration point
      # and a check nobody remembers to ask for is not a check. It was opt-in everywhere, and the only way
      # to opt in was a person typing `gh workflow run`, which is the same as off.
      # One line, not a folded block: this feeds a `type: boolean` input, and a folded scalar is one more
      # thing between the expression and the value that could hand it a string with a newline on the end.
      # Against the published keel only: the keel's `main` is held to the contract, which conformance is.
      matrix: ${{{{ matrix.keel == '' && (inputs.matrix || github.ref_name == 'main' || github.ref_type == 'tag') }}}}
      # What the runner needs installed before the matrix runs: `go`, `node`, `java`, `uv`, `pack`. The
      # matrix generates a project per row and runs *that project's* own `make verify`, so the runner needs
      # this language's toolchain — and this package is the only thing that knows which.
      toolchains: ''
      # Packages to install beside this one before conformance, space-separated. A framework's family is
      # worked out from its own `requires` and does not go here. This is for a *family*, which declares no
      # backend of its own and is proved through one of its frameworks — `java` names `java-spring`.
      beside: ''
      # Where a tag publishes to: put the channel in the first quotes. Empty publishes nowhere, which is right
      # for a fork, and only the published-keel row ever publishes, so a tag publishes once.
      channel: ${{{{ matrix.keel == '' && '' || '' }}}}
      # Which keel to prove against: the row's. A bare version is one on PyPI, anything else is passed to pip
      # as it stands, and empty installs the newest `slipwai`.
      keel: ${{{{ matrix.keel }}}}
    # A token that may open a pull request on that channel. Without it a tag still builds the release
    # and attaches it to itself, and `slipwai package register` finishes the job by hand — so a fork
    # needs no credential and a package nobody owns can still be proved.
    secrets:
      chandlery_token: ${{{{ secrets.CHANDLERY_TOKEN }}}}
"""


#: A package's own changelog. Started empty rather than with an entry: the first release writes the first
#: entry, and a scaffold that wrote one would be a scaffold claiming a release nobody cut.
CHANGELOG = """# Changelog

What changed in each release of {name}. Newest first, one entry per released version; the entry being
written lives in `changelog.d/` until `slipwai package version` assembles it.
"""

FRAGMENTS = """# changelog.d

One file per change, `<a-few-words>.md`. `slipwai package version` assembles them into the next entry of
`CHANGELOG.md` and deletes them.

One file per change rather than a block at the top of the changelog, because two changes in flight at once
are two branches inserting at the same spot. There is no shared line to conflict on here.

## The shape

```markdown
MINOR

**What changed, in a sentence somebody installing this would recognise.** Then a paragraph: what it does
for them, and what it cost if that matters.

**Catch-up:** what an existing project has to do to get it, as a command where there is one.
```

The first line is the level this change claims — `PATCH`, `MINOR` or `MAJOR`. The entry's level is the
highest any fragment claims, so a release carrying a fix and a new option is a MINOR and not both.

The conformance suite holds `VERSION`, `CHANGELOG.md` and this directory together: a released version has
an entry under its number and no fragments left over. That is why cutting a release is a command and not
an edit.
"""

FIRST = """MINOR

**TODO: what this {kind} is, in a sentence somebody choosing it would recognise.** Then a paragraph: what
it does for them, and what it costs.

**Catch-up:** nothing; this is the first release of {name}.
"""
