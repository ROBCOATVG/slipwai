#!/usr/bin/env python3
"""`./init --extension codegraph`: install and index CodeGraph, and point the agent at it.

CodeGraph (https://github.com/colbymchenry/codegraph) is a local, 100%-offline MCP code-knowledge graph.
Its own installer already wires the MCP server into whichever coding agents it finds and appends its own
instruction block to their context files — but that config is the user's, on the one machine `./init` ran on,
and never reaches a container, a CI runner or the fresh session a `/cruise` iteration is. So this script does the
three things that belong to the project rather than to CodeGraph itself: index this repository, add one
marker-fenced pointer to `AGENTS.md` so the primary agent reaches for the graph on a cross-file question instead
of falling back to grep-and-read, and write the committed `.mcp.json` that carries the server with the checkout. The same block tells a delegated agent to probe its own session rather than assume it
inherited the primary agent's connection. The pointer says how to tell that an environment cannot reach
the index at all, because a checkout travels into
places its tooling does not, and `make check-codegraph` is what notices an index nothing is maintaining.
See docs/extensions.md for what every extension's `init.py` owes.

Never fails `./init`: a missing `codegraph` CLI is reported, not fatal.
"""
from __future__ import annotations

import json
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

**The connection travels with the checkout.** `.mcp.json` at the root names the server, started through `npx`
so a checkout with Node reaches the index whether or not the `codegraph` CLI was ever installed there. Claude
Code reads that file, and a `/cruise` iteration is started with it and its tools allowed; every other harness
reaches the same index through the routes below.

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


MCP_FILE = ROOT / ".mcp.json"
# The server as Claude Code's project-scoped `.mcp.json` names one (code.claude.com/docs/en/mcp, the scope table;
# CodeGraph's own `codegraph install --location=local` writes the same file, read from its 1.6.0 bundle
# 2026-09-22). Started through `npx` rather than the `codegraph` binary because the file is committed and travels:
# a checkout with Node reaches the index whether or not the CLI was installed there — a container, a sandbox, a CI
# runner, the cases the block above describes. Proved 2026-09-22: a Claude Code 2.1.280 print session given this
# file with `--mcp-config` connected the server and answered a caller question through `codegraph_explore`.
MCP_SERVER = {"type": "stdio", "command": "npx", "args": ["-y", "@colbymchenry/codegraph", "serve", "--mcp"]}


def write_mcp_config() -> None:
    """Make `.mcp.json` carry the CodeGraph server, leaving every other server a person configured as it was: a
    file the user may hand-edit is a merge target (docs/extensions.md, 6), and one that does not parse is left
    alone and said so rather than replaced."""
    document: dict = {}
    if MCP_FILE.is_file():
        try:
            loaded = json.loads(MCP_FILE.read_text())
        except ValueError:
            loaded = None
        if not isinstance(loaded, dict):
            print(f"{MCP_FILE.name} is not a JSON object; left as it is — add the server to it by hand: "
                  f"{json.dumps({'mcpServers': {'codegraph': MCP_SERVER}})}", file=sys.stderr)
            return
        document = loaded
    servers = document.get("mcpServers")
    if not isinstance(servers, dict):
        servers = document["mcpServers"] = {}
    if servers.get("codegraph") == MCP_SERVER:
        return
    servers["codegraph"] = MCP_SERVER
    MCP_FILE.write_text(json.dumps(document, indent=2) + "\n")


def project_guidance() -> None:
    """Record this election and make its factory-owned projections current: the guidance block, and the MCP file
    the checkout carries. Installation and indexing are `main`'s alone."""
    record_extension("codegraph")
    replace_block("codegraph", GUIDANCE)
    write_mcp_config()


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
