#!/usr/bin/env python3
"""How `/drive` hands implementation to `drive-implement`: the boundary a delegate is handed, and the cycle it runs.

`.specify/drive.json` holds both — `delegate`: how much one delegate is handed, every rule of one user story, one
rule, or one task; `cycle`: how many RED tests one RED-GREEN-REFACTOR cycle opens with, a rule's examples together
or one at a time. This reads the file and says what the settings are and mean, checks a hand edit, and changes them
through `--set`, refusing anything the ladder could not act on. `commands/drive.md`, *How implementation is
delegated*, says which veto overrides a setting on a slice; nothing here decides that.

    python3 scripts/agents/drive.py                                   # both settings and what each means
    python3 scripts/agents/drive.py --check                           # well-formed; `make check-agents` runs this
    python3 scripts/agents/drive.py --set delegate=rule cycle=example # change them, checked, any time

A change takes effect at the next implementation stage `/drive` runs: the file is read before every one and
cached nowhere. `slipwai migrate` merges a newer factory's file over an edited one rather than replacing it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json` (see models.py)."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 2)
CONFIG = ROOT / ".specify/drive.json"
DELEGATES = {
    "story": "every rule of one user story, each rule its own cycle in one context",
    "rule": "one rule with its examples",
    "task": "one task as the tasks stage cut it",
}
CYCLES = {
    "rule": "a rule's examples written together, each failing for its own stated reason, then the code",
    "example": "one failing test, then the code that passes it",
}
DEFAULTS = {"delegate": "story", "cycle": "rule"}
# Every rule of a story red before any is implemented is the batch Principle V prohibits: not a value.
REFUSED = {"cycle": {"story": "a story is never a cycle unit — every rule of a story red before any is implemented "
                              "is the batch Principle V prohibits; `cycle=rule` is the widest cycle there is"}}
VETOES = ("on a slice whose tasks carry no story tag, `story` falls to `rule`; on a map that does not number its "
          "rules, the boundary falls to `task` and the cycle to `example` (commands/drive.md, *How implementation is "
          "delegated*)")
ABSENT = (f"no {CONFIG.relative_to(ROOT)}: /drive delegates per {DEFAULTS['delegate']} and cycles per "
          f"{DEFAULTS['cycle']}, the defaults; `slipwai migrate` writes the file")


def check(table: object) -> list[str]:
    """Everything a hand edit can break, each as one finding."""
    if not isinstance(table, dict):
        return ["the file is not a JSON object"]
    findings = []
    for key, known in (("delegate", DELEGATES), ("cycle", CYCLES)):
        value = table.get(key)
        if value not in known:
            refused = REFUSED.get(key, {}).get(value)
            findings.append(f"`{key}` is {value!r}; {refused}" if refused
                            else f"`{key}` must be one of {', '.join(known)}, not {value!r}")
    return findings


def assign(table: dict[str, Any], assignment: str) -> str:
    """Apply one `delegate=…` or `cycle=…` in place and say what changed; `check` decides whether it stands."""
    key, separator, value = assignment.partition("=")
    if not separator or key not in DEFAULTS or not value:
        raise RuntimeError(f"--set takes delegate=story|rule|task or cycle=rule|example, not {assignment!r}")
    table[key] = value
    return f"{key} = {value}"


def describe(table: dict[str, Any]) -> str:
    return "\n".join((
        f"delegate: {table['delegate']} — {DELEGATES[table['delegate']]}",
        f"cycle: {table['cycle']} — {CYCLES[table['cycle']]}",
        f"vetoes: {VETOES}",
    ))


def main() -> None:
    arguments = sys.argv[1:]
    if not CONFIG.is_file():
        print(ABSENT)
        return
    table = json.loads(CONFIG.read_text())
    if "--set" in arguments:
        assignments = arguments[arguments.index("--set") + 1:]
        if not assignments:
            raise RuntimeError("--set takes delegate=story|rule|task or cycle=rule|example")
        changed = [assign(table, assignment) for assignment in assignments]
        findings = check(table)
        if findings:
            raise RuntimeError("not written — the change would leave the file malformed:\n  - " + "\n  - ".join(findings))
        CONFIG.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n")
        for line in changed:
            print(line)
        print(f"{CONFIG.relative_to(ROOT)} written; it takes effect at the next implementation stage /drive runs. "
              "Commit it: the choice is versioned with the project.")
        return
    findings = check(table)
    if findings:
        raise RuntimeError(f"{CONFIG.relative_to(ROOT)}:\n  - " + "\n  - ".join(findings))
    if "--check" in arguments:
        print(f"check-drive: {CONFIG.relative_to(ROOT)} delegates per {table['delegate']} and cycles per {table['cycle']}")
        return
    print(describe(table))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"drive: {error}", file=sys.stderr)
        raise SystemExit(1) from None
