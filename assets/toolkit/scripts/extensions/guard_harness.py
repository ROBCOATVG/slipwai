#!/usr/bin/env python3
"""The harness's side of a guard: the row that makes it run for the tools an agreed guard `sees`.

A harness runs a hook for the tools its matcher names. The keel writes the rows for the guard points — a
search, a write, a shell command — because those are the same in every project. The tools a guard asks to
*see* are not: they are one extension's MCP tools, and which extensions a project agreed to is decided in
the project. So that one row is written here, from `.slipwai/guards.json`, whenever an agreement changes
and at every `make agents`.

    python3 scripts/extensions/guard_harness.py     # write, narrow or remove the row; say nothing if nothing moved

**The matcher is exactly what was declared, and nothing declared can be wide.** Each pattern is one MCP
server's tools, by name or all of that server's (`guards.py` holds the expression), so the row can never
name a search, a write or every call. With no agreed guard seeing anything the row is removed, and the file
is what it was.

Only Claude Code's `.claude/settings.json` is written, because it is the only harness the registry records
a pre-tool event for whose shape was read. The row's command is taken from the `before-search` row already
in that file, so it carries whatever path this project keeps its scripts at; a file with no such row, or
one that is not JSON, is left alone. Nothing here is fatal: the agreement is the registry, not this.

Standalone and dependency-free: this ships inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import json
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


def main() -> int:
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
