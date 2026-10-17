#!/usr/bin/env python3
"""`/cruise`'s settings: what a run does at each of the ladder's stops, read and changed in one place.

This was a runner. It held the state of a run, decided what happened next, re-invoked the ladder in a fresh
session each time — and died at iteration two, after which seventeen iterations ran from interactive sessions
and it knew about none of them. What replaced it is not a better runner but **no runner**: the state lives in
the append-only logs, a captain per stream reads them, and `scripts/agents/fleet.py` starts those captains and
exits. Nothing holds a run, so nothing can be the thing that died.

What is left here is the settings, which outlived the loop because they were never the loop's: they are the
answers a run gives at `/sail`'s stops — who decides a product question, what a release becomes, what a demo
is driven with, what an unratified constitution does, what a block becomes. A captain reads this file; so does
`/sail` under one. The shape is `sail.py`'s, which does the same job for the ladder's own settings.

    python3 scripts/agents/cruise.py                       # every setting and what it controls
    python3 scripts/agents/cruise.py --check               # well-formed; `make check-agents` runs this
    python3 scripts/agents/cruise.py --set enabled=true    # change settings, checked, any time

Where the runner's verbs went, each to the thing that owns it now:

| was | is |
|---|---|
| `run`, `start`, `stop`, `status` | `scripts/agents/fleet.py start`, `stop`, `list` |
| `watch` | `scripts/agents/fleet.py watch` — the deck logs, not one runner's output |
| `tell`, `told` | `scripts/agents/fleet.py tell <stream>`, and `scripts/agents/inbox.py <stream>` |
| `guard`, `stopping` | the `before-write` and `before-stop` guards, `scripts/agents/session.py` |
| `compacting`, `resume` | the `before-compact` and `after-compact` hooks, same script |
| `loop`, `denials`, `where` | gone: there is no outer loop to report, and `slipwai fleet` is where a run stands |

Standalone and dependency-free: this ships inside a generated project, which has no slipwai to import.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json` (see models.py)."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


SCRIPT = Path(__file__).resolve()
ROOT = project_root(SCRIPT, 2)
# No bytecode: a `__pycache__/` written beside the scripts is an untracked directory in the project, which
# `add-service` refuses to start over.
sys.dont_write_bytecode = True
CONFIG = ROOT / ".specify/cruise.json"

# Every setting: the values it takes, its default, and what it controls. The factory writes the same list
# into `.specify/cruise.json` and `commands/cruise-settings.md`, so the file, the command and this reader
# cannot disagree about what a run may be asked.
CHOICES: dict[str, tuple[str, ...]] = {
    "enabled": ("true", "false"),
    "decide": ("recommended-first", "skipper-always"),
    "release": ("flagged", "park"),
    "constitution": ("ratify", "park"),
    "hand": ("browser", "http", "cli"),
    "unblock": ("bosun", "park"),
    "upstream": ("park", "advance"),
}
# Free text, or null: the model the ladder itself runs on, passed through the harness row's own `modelFlag`.
TEXTS = ("model",)
# There are no numbers here any more. `stuck_after`, `max_iterations`, `max_hours` and `poll_minutes` were
# the loop's budget — how many times it would re-invoke the ladder, for how long, and how often a parked loop
# looked for a reason to resume — and there is no loop. What bounds a run now is the telegraph (`harbour.json`:
# `boilers`, `bunker_per_day`, `attempts`, `wait_bound`), which is one lever rather than four numbers nobody
# set. A file still carrying the four is read without complaint and the four are ignored; `slipwai migrate`
# takes them out, because a setting nothing reads is worse than one that was never there.
DEFAULTS: dict[str, Any] = {
    "enabled": False, "decide": "recommended-first", "release": "flagged", "constitution": "ratify",
    "hand": "browser", "unblock": "bosun", "upstream": "park", "model": None,
}
# Settings that arrived after projects already had this file. Absent is the default rather than a finding, so
# a project written before one existed still passes `make check-agents`; `--set` writes it in.
LATER = ("upstream",)
CONTROLS = {
    "enabled": "whether `/cruise` runs at all; `false` is a refusal that says so",
    "decide": "who answers a product question: the host where the stage recommends an answer or a standing "
              "decision covers it and `sail-decide-skipper` otherwise, or `sail-decide-skipper` for every question",
    "release": "the release-constraint stage: every slice continues or opens a flag seeded off, so every merge "
               "is dark; or park at the push and let a person say it is a release they want",
    "constitution": "an unratified constitution: the skipper drafts and ratifies it, marked pending human "
                    "review; or park",
    "hand": "the top of the hand's ladder for a demo; each falls through to the next where it cannot run",
    "unblock": "what a block becomes: work for `sail-unblock-bosun` first — a stub, a narrower reading, a repair — parking "
               "only at the catastrophic or when it fails; or a park at once",
    "upstream": "the steps above the chart — the drafted specification, the storyboard and the event model: "
                "stop at each for a person, or have the board start the next one, and approve the storyboard, "
                "as each ends well",
    "model": "the model the iteration itself runs on — the driver, and every stage `.specify/models.json` maps to "
             "`host`; null is the harness's default, which nobody at the wheel chooses",
}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def check(table: object) -> list[str]:
    """Everything a hand edit can break, each as one finding."""
    if not isinstance(table, dict):
        return ["the file is not a JSON object"]
    findings = []
    for key, values in CHOICES.items():
        value = table.get(key, DEFAULTS[key] if key in LATER else None)
        if key == "enabled":
            if not isinstance(value, bool):
                findings.append(f"`enabled` must be true or false, not {value!r}")
        elif value not in values:
            findings.append(f"`{key}` must be one of {', '.join(values)}, not {value!r}")
    for key in TEXTS:
        value = table.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            findings.append(f"`{key}` must be a model identifier or null, not {value!r}")
    return findings


def assign(table: dict[str, Any], assignment: str) -> str:
    """Apply one `key=value` in place and say what changed; `check` decides whether it stands."""
    key, separator, value = assignment.partition("=")
    if not separator or not value or key not in DEFAULTS:
        raise RuntimeError(f"--set takes key=value with a key from {', '.join(DEFAULTS)}, not {assignment!r}")
    if key == "enabled":
        if value not in CHOICES[key]:
            raise RuntimeError(f"`enabled` is true or false, not {value!r}")
        table[key] = value == "true"
    elif key in CHOICES:
        table[key] = value
    else:
        table[key] = None if value == "null" else value
    return f"{key} = {json.dumps(table[key])}"


def describe(table: dict[str, Any]) -> str:
    return "\n".join(f"{key}: {json.dumps(table.get(key, DEFAULTS[key]))} — {CONTROLS[key]}" for key in DEFAULTS)


def load() -> dict[str, Any]:
    table = json.loads(CONFIG.read_text(encoding="utf-8"))
    findings = check(table)
    if findings:
        raise RuntimeError(f"{CONFIG.relative_to(ROOT)}:\n  - " + "\n  - ".join(findings))
    return table


def enabled() -> dict[str, Any]:
    table = load()
    if not table["enabled"]:
        raise RuntimeError("not enabled: `python3 scripts/agents/cruise.py --set enabled=true`, checked, turns it on")
    return table


ABSENT = f"no {CONFIG.relative_to(ROOT)}: /cruise is not enabled here; `slipwai migrate` writes the file"


def main() -> None:
    arguments = sys.argv[1:]
    if not CONFIG.is_file():
        print(ABSENT)
        return
    if "--set" in arguments:
        table = json.loads(CONFIG.read_text(encoding="utf-8"))
        assignments = arguments[arguments.index("--set") + 1:]
        if not assignments:
            raise RuntimeError(f"--set takes key=value with a key from {', '.join(DEFAULTS)}")
        changed = [assign(table, assignment) for assignment in assignments]
        findings = check(table)
        if findings:
            raise RuntimeError("not written — the change would leave the file malformed:\n  - "
                               + "\n  - ".join(findings))
        CONFIG.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for line in changed:
            print(line)
        print(f"{CONFIG.relative_to(ROOT)} written; a captain reads it at its next boundary. "
              "Commit it: the choice is versioned with the project.")
        return
    table = load()
    if "--check" in arguments:
        state = "enabled" if table["enabled"] else "not enabled"
        print(f"check-cruise: {CONFIG.relative_to(ROOT)} is well-formed; /cruise is {state}")
        return
    if arguments:
        raise RuntimeError(f"`{arguments[0]}` is not something this reads any more. It was the runner's, and "
                           f"there is no runner: `scripts/agents/fleet.py` starts and stops the fleet and "
                           f"watches the logs, `scripts/agents/session.py` answers the harness's own moments. "
                           f"This file is the settings — run it with no arguments to see them.")
    print(describe(table))
    if shutil.which("git") is None:
        print("note: git is not on PATH; a captain needs it for every berth it makes")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"cruise: {error}", file=sys.stderr)
        raise SystemExit(1) from None
