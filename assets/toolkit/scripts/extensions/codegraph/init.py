#!/usr/bin/env python3
"""`./init --extension codegraph`: install and index CodeGraph, and point the agent at it.

CodeGraph (https://github.com/colbymchenry/codegraph) is a local, 100%-offline MCP code-knowledge graph.
Its own installer already wires the MCP server into whichever coding agents it finds and appends its own
instruction block to their context files — but that config is the user's, on the one machine `./init` ran on,
and never reaches a container, a CI runner or the fresh session a `/cruise` iteration is. So this script does the
three things that belong to the project rather than to CodeGraph itself: index this repository, add one
marker-fenced pointer to `AGENTS.md` so the primary agent reaches for the graph on a cross-file question instead
of falling back to grep-and-read, and name the server in the committed project MCP file of every harness installed
here, so the connection travels with the checkout. The same block tells a delegated agent to probe its own session rather than assume it
inherited the primary agent's connection. The pointer says how to tell that an environment cannot reach
the index at all, because a checkout travels into
places its tooling does not, and `make check-codegraph` is what notices an index nothing is maintaining.
See docs/extensions.md for what every extension's `init.py` owes.

Never fails `./init`: a missing `codegraph` CLI is reported, not fatal.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agents"))
from code_index import CODEGRAPH  # noqa: E402
from guidance import record_extension, replace_block, write_project_mcp  # noqa: E402

def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json`.

    This script's own tree is `<root>/scripts` in a generated project and `<root>/<layout.delivery>/scripts`
    where the method was installed beside an existing codebase (`project.json`'s `layout.delivery`), so how
    far below the root it sits is not something to count; `depth` is only the fallback for a tree with no
    manifest at all.
    """
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 3)
MARKER_BEGIN = "<!-- extension:codegraph:begin -->"
MARKER_END = "<!-- extension:codegraph:end -->"
GUIDANCE = f"""
{MARKER_BEGIN}
## CodeGraph
This project is indexed by CodeGraph (`.codegraph/`). **The index answers symbol questions; text search answers
questions about words.** Who calls a function, what it calls, where a type is used, what a change would reach:
ask the index first —

    scripts/codegraph callers <symbol>        scripts/codegraph impact <symbol>
    scripts/codegraph explore <names or a question>

`scripts/codegraph` runs the pinned CLI through `npx`, or an installed `codegraph`, so it answers in every session
with a shell — a delegate's included — whatever MCP tools that session was given; `codegraph_explore` over MCP is
the same index where your tools list it. A search of `spec.md`, `decisions.md`, the PRD, `model.yaml` or a test's
string literal ("done for the day") is a text search, and grep is right for it; locating a file by name is a
`find`, not a question for the index. Say which route you used when you report what you found.

**What holds this, so nobody has to remember it.** In Claude Code a hook refuses a search of the source for a
symbol — a name the index defines, or one shaped like one — from any session or delegate that has not asked the
index yet, and names the commands above; once it has, grep is its own business. Another hook syncs the index each
time a delegate returns. A `/cruise` runner opens the database before every iteration, integrity-checks it, moves a
corrupt one aside and rebuilds it (it is derived from the source and ignored by Git), and syncs a stale one; its
log says what it did, and `python3 scripts/agents/cruise.py status` says how often each delegate asked the index
and which searched the source for a symbol first. `python3 scripts/agents/code_index.py health` is the same repair
by hand.

**The connection travels with the checkout.** The project-scoped MCP file of every harness installed here
names the server, started through `npx` at the same pinned version: `.mcp.json` for Claude Code (with
`alwaysLoad`, so its tool is loaded at session start rather than behind the tool-search step), `.codex/config.toml`
for Codex, `.gemini/settings.json` for Gemini CLI, `.cursor/mcp.json` for Cursor, `opencode.json` for opencode.
Where a harness still lists `codegraph_explore` as a bare name with no schema, it is not loaded yet rather than
unavailable — load it by name through that harness's tool-search step, or use `scripts/codegraph`.

**It is only current while a client is attached.** CodeGraph's watcher runs in a daemon that starts with an MCP
client or a `codegraph` command, shuts down on an idle timeout, and turns itself off where CodeGraph decides it
is sandboxed — so the syncs above do the keeping, and `make check-codegraph`, part of `make verify`, fails a
corrupt database, syncs a stale one, and fails with the date it was last written where the tree still cannot be
brought current. A corrupt database is the one CodeGraph's own `status` and `sync` call up to date.

**A sub-agent does not inherit this session's connection**, and needs none: `scripts/codegraph` is in its shell.
Do not pass the parent conversation merely to carry that fact — every harness receives this `AGENTS.md` block,
while a delegate keeps its focused stage brief. `commands/drive.md`, *Who runs each stage*, carries the same
boundary.

**Where no route exists** — no Node and no `codegraph` — `scripts/codegraph` says so; then say in as many words
that the answer is a text search ("the database is here, the tooling is not"), and work as a project with no
index would. Install Node, or the CLI
(`curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh`), and re-adopt with
`./init --extension codegraph`.
{MARKER_END}
"""


# The server, started through `npx` rather than the `codegraph` binary because the file it goes into is committed
# and travels: a checkout with Node reaches the index whether or not the CLI was installed there — a container, a
# sandbox, a CI runner, the cases the block above describes. Written into the project MCP file of every harness
# installed here (`scripts/agents/registry.json`, `projectMcp`; `guidance.write_project_mcp`). Proved 2026-09-22:
# a Claude Code 2.1.280 print session given `.mcp.json` with `--mcp-config` connected this server and answered a
# caller question through `codegraph_explore`.
# Pinned to the release every other route runs (`scripts/agents/code_index.py`), so the server and the CLI never
# write one database from two versions of its schema.
MCP_COMMAND = ["npx", "-y", CODEGRAPH, "serve", "--mcp"]


def project_guidance() -> None:
    """Record this election and make its factory-owned projections current: the guidance block, and the MCP file
    each installed harness reads. Installation and indexing are `main`'s alone."""
    record_extension("codegraph")
    replace_block("codegraph", GUIDANCE)
    for line in write_project_mcp("codegraph", MCP_COMMAND):
        print(f"codegraph: {line}")


def main() -> int:
    if shutil.which("codegraph") is None:
        # Naming the recovery matters more than naming the tool: without the second command this project
        # keeps no pointer to CodeGraph, so a reader who installs the CLI and stops there ends up with a
        # working index no agent is ever told about.
        print(
            "CodeGraph CLI not found: nothing was indexed and AGENTS.md is unchanged.\n"
            "Install it:\n"
            "  curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh\n"
            "Then adopt it here, which is what points the agent at it:\n"
            "  ./init --extension codegraph",
            file=sys.stderr,
        )
        return 0
    # `check=False`: an extension may not fail `./init` (docs/extensions.md), and a raised
    # CalledProcessError here would also skip the pointer below — leaving exactly the half-adopted state
    # the missing-CLI branch takes care to avoid.
    installed = subprocess.run(["codegraph", "install", "--yes", "--init"], cwd=ROOT, check=False)
    if installed.returncode != 0:
        print(
            f"`codegraph install` exited {installed.returncode}: AGENTS.md is unchanged.\n"
            "Fix what it reported, then adopt it here:\n"
            "  ./init --extension codegraph",
            file=sys.stderr,
        )
        return 0
    project_guidance()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
