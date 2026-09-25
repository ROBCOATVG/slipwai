MINOR

**The code index is kept sound, kept current and asked first by the harness, not by a sentence in a brief.** A
`/cruise` iteration on an indexed project started against a corrupt `.codegraph/codegraph.db` — which CodeGraph's
own `status` and `sync` report as up to date — repaired it by hand, asked it once and went back to grep, and its
delegates located symbols with `grep -n` and `sed -n` although their brief said to ask the index; nothing counted
who asked it. Now:

- Before every iteration the runner opens the database, runs SQLite's integrity check, moves a corrupt one to
  `.codegraph/corrupt/` and rebuilds it, and syncs one the tree has moved past; the log entry's `index` says which.
  A Claude Code session takes the same step when it opens (a `SessionStart` hook), so a person's `/drive` starts on
  a sound index too, and hears about it only when something was done. `python3 scripts/agents/code_index.py health`
  is the same repair by hand.
- `scripts/codegraph` runs the pinned CLI (`@colbymchenry/codegraph@1.6.0`, the version the MCP server now runs
  too) through `npx`, or an installed `codegraph`, so every session with a shell — a delegate's included — has a
  route. Claude Code's `.mcp.json` entry carries `alwaysLoad`, so `codegraph_explore` is loaded at session start
  instead of behind the tool-search step a delegate had to take by name.
- Claude Code's `PreToolUse` hook refuses a search of the source for a symbol — a name the index defines, or one
  shaped like one — from any session or delegate that has not asked the index yet, naming the command that
  answers; words, phrases and searches confined to documents are text search and never refused. A `PostToolUse`
  hook syncs the index each time a delegate returns, because CodeGraph turns its own watcher off where it decides
  it is sandboxed.
- `check-codegraph` no longer skips a database that fails the integrity check: where the CLI is reachable it
  rebuilds it, and syncs a stale index, before comparing, and fails only where the index cannot be made sound and
  current — so `make verify` on any harness mends a broken index rather than going red on it
  (`CODEGRAPH_GATE_NO_SYNC=1` compares without repairing).
- The log entry's `index_use`, the feed and `cruise.py status` count index queries per delegate and name each
  that searched the source for a symbol before asking.

The hooks and per-delegate counts are Claude Code's; on other harnesses the runner's repair, the gate, the wrapper
and a per-iteration count hold.

**Catch-up.** `slipwai migrate` brings the scripts, the hooks and the delegate briefs. Run `make agents` (or
`./init --extension codegraph`) once in a project that adopted the index, so `.mcp.json` and the `AGENTS.md` block
name the pinned server with `alwaysLoad`, and commit the result.
