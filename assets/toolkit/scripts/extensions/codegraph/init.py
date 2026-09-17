#!/usr/bin/env python3
"""`./init --extension codegraph`: install and index CodeGraph, and point the agent at it.

CodeGraph (https://github.com/colbymchenry/codegraph) is a local, 100%-offline MCP code-knowledge graph.
Its own installer already wires the MCP server into whichever coding agents it finds and appends its own
instruction block to their context files — this script only does the two things that belong to the
project rather than to CodeGraph itself: index this repository, and add one marker-fenced pointer to
`AGENTS.md` so the primary agent reaches for the graph on a cross-file question instead of falling back to
grep-and-read. The same block tells a delegated agent to probe its own session rather than assume it
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
from guidance import record_extension, replace_block  # noqa: E402

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
This project is indexed by CodeGraph (`.codegraph/`). For any question about call paths, symbol usage, or
the blast radius of a change, query it directly — `codegraph_explore` over MCP, or the `codegraph` CLI —
before grep or reading files one at a time. Say which route you used when you report what you found.

**Check you can reach it before you trust it.** The index is data in this checkout; the tooling that
serves and maintains it is not, and a tree carried into a container, a sandbox or a CI runner routinely
has one without the other. Probe the available routes in order: use `codegraph_explore` when this session
offers it — treating a bare tool name as not loaded yet rather than unavailable, because a harness that
defers MCP tools lists `codegraph_explore` with no schema and refuses the call until you load it by name
through that harness's own tool-search step; otherwise use the installed CLI when
`command -v codegraph` succeeds; otherwise, when
`command -v npm` succeeds, use `npx -y @colbymchenry/codegraph explore <query>` to reach the same index
without installing the CLI globally. Only when all three routes are unavailable should you say so in as
many words ("the database is here, the tooling is not, so this answer is a text search"). Then work as a
project with no index would. Restore a durable connection by configuring the CodeGraph MCP server for this
project, or by installing the CLI and re-adopting the extension, which is what re-points the agent:
`curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh` then
`./init --extension codegraph`.

**It is only current while a client is attached.** CodeGraph's watcher runs in a daemon that starts with
an MCP client or a `codegraph` command and shuts down on an idle timeout, so wherever the tooling is
absent the database stops being written to and nothing says so: it answers *nothing calls that* for code
it has never read, which is the failure it exists to prevent. `make check-codegraph`, part of `make
verify`, compares the index with the tracked source and fails with the date it was last written.
Attaching a client once — an MCP session, or `codegraph sync` in this directory — catches it up itself.

**A sub-agent does not inherit this session's connection.** A fresh delegate checks its own tools before
exploring and follows the same MCP, installed-CLI, then `npx` order. It says the index is unavailable
before falling back to text search only when none of those routes exists. Do not pass the parent
conversation merely to carry that fact — every harness receives this `AGENTS.md` block, while a delegate
keeps its focused stage brief. `commands/drive.md`, *Who runs each stage*, carries the same boundary.
{MARKER_END}
"""


def project_guidance() -> None:
    """Record this election and make its factory-owned guidance region current."""
    record_extension("codegraph")
    replace_block("codegraph", GUIDANCE)


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
