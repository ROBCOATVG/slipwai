#!/usr/bin/env python3
"""The harness's side of a guard: the row that makes it run for the tools an agreed guard `sees`.

A harness runs a hook for the tools its matcher names. The keel writes the rows for the guard points — a
search, a write, a shell command — because those are the same in every project. The tools a guard asks to
*see* are not: they are one extension's MCP tools, and which extensions a project agreed to is decided in
the project. So that one row is written here, from `.slipwai/guards.json`, whenever an agreement changes
and at every `make agents`.

    python3 scripts/extensions/guard_harness.py          # write, narrow or remove the row
    python3 scripts/extensions/guard_harness.py --held   # which installed harness holds which guard, as JSON

**The matcher is exactly what was declared, and nothing declared can be wide.** Each pattern is one MCP
server's tools, by name or all of that server's (`guards.py` holds the expression), so the row can never
name a search, a write or every call. With no agreed guard seeing anything the row is removed, and the file
is what it was.

Only Claude Code's `.claude/settings.json` is written, because it is the only harness the registry records
a pre-tool event for whose shape was read. `--held` says so as data: per installed harness, the moments a
guard is run at there, which `hooks.py` hands an extension at `init` and `project`. The row's command is taken from the `before-search` row already
in that file, so it carries whatever path this project keeps its scripts at; a file with no such row, or
one that is not JSON, is left alone. Nothing here is fatal: the agreement is the registry, not this.

Standalone and dependency-free: this ships inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEES = re.compile(r"mcp__[A-Za-z0-9_-]+__(?:[A-Za-z0-9_-]+|\.\*)")
SEES_LIMIT = 8
SEARCH, VERB = " before-search", " tool-use"


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
REGISTRY = ROOT / ".slipwai/guards.json"
SETTINGS = ROOT / ".claude/settings.json"


def seen() -> list[str]:
    """Every tool pattern an agreed guard sees, once each, in an order two machines agree on."""
    try:
        guards = json.loads(REGISTRY.read_text(encoding="utf-8")).get("guards")
    except (OSError, ValueError, AttributeError, UnicodeDecodeError):
        return []
    found: set[str] = set()
    for bodies in (guards.values() if isinstance(guards, dict) else ()):
        for body in (bodies if isinstance(bodies, list) else ()):
            declared = body.get("sees") if isinstance(body, dict) else None
            found.update(pattern for pattern in (declared if isinstance(declared, list) else [])[:SEES_LIMIT]
                         if isinstance(pattern, str) and SEES.fullmatch(pattern))
    return sorted(found)


def commands(row: object) -> list[str]:
    hooks = row.get("hooks") if isinstance(row, dict) else None
    return [str(hook.get("command", "")) for hook in (hooks if isinstance(hooks, list) else [])
            if isinstance(hook, dict)]


def claude() -> str | None:
    """Write, narrow or remove the row in `.claude/settings.json`. What it did, or None where nothing moved."""
    try:
        settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    rows = hooks.get("PreToolUse") if isinstance(hooks, dict) else None
    if not isinstance(rows, list):
        return None
    kept = [row for row in rows if not any(command.endswith(VERB) for command in commands(row))]
    search = next((command for row in rows for command in commands(row) if command.endswith(SEARCH)), None)
    patterns = seen()
    if patterns and search is not None:
        kept.append({"matcher": "|".join(patterns),
                     "hooks": [{"type": "command", "command": search[:-len(SEARCH)] + VERB}]})
    if kept == rows:
        return None
    hooks["PreToolUse"] = kept
    SETTINGS.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return ", ".join(patterns) if patterns and search is not None else "nothing"


#: Every moment a guard's script can be run at: the seven it may refuse at, and the one it is only told at.
MOMENTS = ("session", "before-search", "before-write", "before-command", "before-fetch", "after-delegate",
           "before-stop", "tool-use")
HARNESSES = HERE.parent / "agents/registry.json"
INTEGRATION = ROOT / ".specify/integration.json"


def holds(row: dict) -> list[str]:
    """The moments this harness runs a guard at, as its registry row records: what it says outright, else
    the events its hook projection writes. A row that records neither holds nothing — which is most of
    them, and is the answer, not a gap in it."""
    hooks = row.get("hooks")
    hooks = hooks if isinstance(hooks, dict) else {}
    projection = hooks.get("projection")
    events = projection.get("events") if isinstance(projection, dict) else None
    named = hooks.get("guards") if isinstance(hooks.get("guards"), list) else list(events or ())
    return [moment for moment in MOMENTS if moment in named]


def installed() -> list[str]:
    """The harnesses installed in this project, and the one an `./init` in progress is installing."""
    keys: list[str] = []
    try:
        state = json.loads(INTEGRATION.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        state = {}
    recorded = state.get("installed_integrations") if isinstance(state, dict) else None
    if isinstance(recorded, list) and recorded:
        keys = [key for key in recorded if isinstance(key, str)]
    elif isinstance(state, dict) and isinstance(state.get("default_integration"), str):
        keys = [state["default_integration"]]
    chosen = os.environ.get("SLIPWAI_INTEGRATION")
    return list(dict.fromkeys([*keys, *([chosen] if chosen else [])]))


def held() -> dict[str, list[str]]:
    """Per installed harness, the moments a guard holds at there. What an extension is handed as
    `SLIPWAI_GUARDS_HELD` at `init` and `project`, so its guidance says whether its guard holds here
    rather than assuming the one harness it was written on. Nothing at all where the registry cannot be
    read: an extension told nothing says nothing, and one told a guess would say it."""
    try:
        rows = {row["key"]: row for row in json.loads(HARNESSES.read_text(encoding="utf-8"))["harnesses"]}
    except (OSError, ValueError, KeyError, TypeError, UnicodeDecodeError):
        return {}
    return {key: holds(rows[key]) if isinstance(rows.get(key), dict) else [] for key in installed()}


def main() -> int:
    if "--held" in sys.argv[1:]:
        print(json.dumps(held(), indent=2))
        return 0
    try:
        wrote = claude()
    except Exception as error:  # noqa: BLE001 — the agreement is the registry; this row is written again
        print(f"guards: the harness's row could not be written ({type(error).__name__}); `make agents` "
              "writes it again", file=sys.stderr)
        return 0
    if wrote is not None:
        print(f"guards: {SETTINGS.relative_to(ROOT).as_posix()} now tells an agreed guard about {wrote}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
