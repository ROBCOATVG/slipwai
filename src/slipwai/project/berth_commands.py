"""Provisioning a berth: the worktree, the record, and the sandbox it runs in.

`berths.py` says what a berth *is* and which numbers it gets. This is the part that makes the record true —
the verbs a person runs, and what each one does and undoes.

**Two sandbox kinds, and that is the whole matrix.** `none` runs the captain on this machine, which is the
honest answer for one captain on a trusted laptop and is what most people will use most of the time. `sbx`
runs it in Docker Sandboxes, which already exists to isolate agents and is the same thing wherever Docker
runs. The four-way matrix that was planned here — `sandbox-exec` on macOS, `bwrap` on Linux, Windows Sandbox
on native Windows, a container elsewhere — is gone: four implementations of one idea is four things to keep
working, and Apple deprecating `sandbox-exec` had already blocked this slice once. Decided 2026-10-07.

**`none` is offered rather than grudgingly tolerated.** A sandbox buys isolation *between concurrent
fairways on one machine*. A person running one captain on their own laptop is paying a Docker dependency
for a boundary they do not need, and a tool that pretends otherwise gets worked around rather than used.

**Removing a berth leaves nothing.** The worktree, the record, the scratch directory and the sandbox all
go, and `status` says what is there rather than what was asked for. A berth that half-exists is worse than
no berth: the next `add` picks the next index, the stale one keeps its ports, and nothing reconciles them.
"""
from __future__ import annotations

from ..berths import BERTHS, Berth

KINDS = ("none", "sbx")
DEFAULT_KIND = "none"


def berth_command() -> str:
    """`/berth` — what the three verbs do, for the page a person reads before running one."""
    return f"""---
description: Add, inspect or remove a berth — the provisioned place one captain works
argument-hint: add <name> [--sandbox none|sbx] | status | remove <name>
---

# Berth

A **berth** is the provisioned place one captain works: a git worktree, a block of ports, a database, a
scratch directory, and the sandbox it runs in. One berth holds one fairway at a time.

```sh
slipwai berth add orca --sandbox sbx    # make one
slipwai berth status                    # what exists, and what is stale
slipwai berth remove orca               # and leave nothing
```

## What `add` does

1. **Allocates.** Ports, database name and scratch directory all fall out of the berth's index and name
   (`src/slipwai/berths.py`). Nobody chooses a number, so nobody chooses the same number twice. The
   database carries **this machine's** identity too — `app_<machine>_<berth>` — so two people pointing two
   harbours at one database server cannot collide either, and nothing has to be configured to stop them.
   Ports do not, and that is not an oversight: a port is reachable from one machine, so two machines'
   blocks are not in the same space at all.
2. **Makes the worktree**, a sibling directory on a branch of its own.
3. **Writes the record** to `{BERTHS}/<name>.json`, which is what `status` reads and `remove` undoes.
4. **Creates the sandbox**, where the kind is `sbx`.

## The two sandbox kinds

| Kind | What it is | When |
|---|---|---|
| `none` | The captain runs on this machine | One captain, a machine you trust. Most laptops, most of the time |
| `sbx` | Docker Sandboxes, one per berth | Several captains at once, or a machine where a mistake in one fairway must not reach another |

`none` is a real answer, not a fallback. A sandbox buys isolation *between concurrent fairways on one
machine*; somebody running a single captain on their own laptop would be paying a Docker dependency for a
boundary they have not got, and a tool that pretends otherwise gets worked around rather than used.

**Either way the berth holds no credential** — not for the forge, the cloud or the chandlery. Anything that
needs one goes through the harbourmaster, which holds them and checks each request against what a run never
does. A berth with a token in it would be a sandbox with a way out.

## What `remove` undoes

The worktree, the record, the scratch directory and the sandbox. All of it, in that order, and `status`
afterwards shows nothing.

A berth that half-exists is worse than no berth: the next `add` takes the next index, the stale one keeps
its ports, and nothing reconciles the two. So `remove` reports what it could not remove rather than
exiting quietly, and `status` reads what is on disk rather than what the records claim.
"""


def status_line(berth: Berth, worktree_exists: bool, sandbox_running: bool) -> str:
    """One berth as `status` prints it: what is there, not what was asked for.

    The distinction is the point. A record saying `sbx` beside a sandbox that is not running is exactly the
    half-existing berth this is for, and a line that read the record alone would call it healthy.
    """
    ports = f"{min(berth.ports)}-{max(berth.ports)}"
    where = "worktree" if worktree_exists else "NO WORKTREE"
    sandbox = ("sandbox up" if sandbox_running else "SANDBOX DOWN") if berth.sandbox == "sbx" else "no sandbox"
    # The database column is wide because the name carries the machine now: `app_<machine>_<berth>` is up
    # to 52 characters, and a column that wraps is a column nobody reads down.
    return f"{berth.name:12} {ports:12} {berth.database:34} {where:12} {sandbox}"
