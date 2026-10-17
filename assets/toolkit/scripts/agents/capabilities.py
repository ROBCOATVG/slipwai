#!/usr/bin/env python3
"""Which capabilities are whole, which have been accepted, and which are owed a demo.

A **capability** is the chunk of work a person's demo is of: usually several slices, named on the chart, and
the smallest thing that means anything on its own to whoever is being shown it. Version 1 stopped a person
at the end of every slice and showed them a fraction of a capability to assemble in their head.

So a whole capability is first owed its **gates** — converge over its diff, gaps over it, the design review
from screenshots, one adversary pass, mutation, and the hand's walk of every example, because a test that passes and a path
that works are different claims and only one of them is machine-checked — and **nobody is stopped for
them**. They are recorded in `specs/<feature>/capabilities/<capability>/gates.md`, whose `Cleared:` line says
they are done. The stop a person attends runs after that.

**This is not a release gate.** Accepting a demo says the capability is right. Hoisting a flag says the
business wants it live, which may be another quarter or never, and stays a person's act on their own timing.
A capability may sit accepted and dark for as long as the business wants, so the two are reported here as
separate columns and neither is ever derived from the other. A capability under the `open` release mode has
no flag at all and still has a demo.

    python3 scripts/agents/capabilities.py          # every capability, with what it is waiting for
    python3 scripts/agents/capabilities.py --gates  # only the ones owed their gates now
    python3 scripts/agents/capabilities.py --due    # only the ones owed a demo now
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())
SPECS = ROOT / "specs"
LOGS = ROOT / ".slipwai/logs"
V = 1
#: What a gate record's last word says once every gate has run with nothing above the bar left open.
CLEARED = re.compile(r"^Cleared:\s*\S", re.MULTILINE)


def load_yaml(text: str) -> object:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - exercised on a machine without PyYAML
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "PyYAML"], check=True)
        import yaml  # type: ignore[import-not-found]
    return yaml.safe_load(text)


def chart() -> tuple[dict, str]:
    for path in sorted(SPECS.glob("*/chart.yaml")) if SPECS.is_dir() else []:
        loaded = load_yaml(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded, path.parent.name
    return {}, ""


def lines(feature: str) -> list[dict]:
    """Every deck log's lines, and the harbour log's, in no particular order across files."""
    paths = [*(LOGS / feature).glob("*.jsonl")] if (LOGS / feature).is_dir() else []
    found: list[dict] = []
    for path in sorted(paths):
        for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not text.strip():
                continue
            try:
                line = json.loads(text)
            except ValueError:
                raise SystemExit(f"capabilities: {path.name}:{number} is not JSON. Reading past it would "
                                 f"report a capability whole that is not.") from None
            if isinstance(line, dict) and line.get("v") != V:
                raise SystemExit(f"capabilities: {path.name}:{number} says v{line.get('v')} and this reader "
                                 f"knows v{V}. Run `slipwai upgrade`.")
            if isinstance(line, dict):
                found.append(line)
    return found


def slices_by_capability(charted: dict) -> dict[str, list[str]]:
    """Each capability against its slices, in the chart's order, which is split order."""
    grouped: dict[str, list[str]] = {}
    for slice_id, entry in (charted.get("slices") or {}).items():
        if isinstance(entry, dict) and entry.get("capability"):
            grouped.setdefault(str(entry["capability"]), []).append(str(slice_id))
    return grouped


def cleared(feature: str, capabilities: list[str]) -> set[str]:
    """The capabilities whose gate record carries its `Cleared:` line."""
    found = set()
    for capability in capabilities:
        record = SPECS / feature / "capabilities" / capability / "gates.md"
        if record.is_file() and CLEARED.search(record.read_text(encoding="utf-8")):
            found.add(capability)
    return found


def state(charted: dict, written: list[dict], gated: set[str] | frozenset[str] = frozenset()) -> list[dict]:
    """One row per capability: its slices, how many have merged, and whether it is whole, gated or accepted.

    `accepted` and `hoisted` are kept apart on purpose. A capability the business is deliberately holding
    back is not a late one, and a board that derived one from the other could not tell them apart.
    """
    merged = {str(line["slice"]) for line in written if line.get("kind") == "merged" and line.get("slice")}
    accepted = {str(line["capability"]) for line in written
                if line.get("kind") == "accepted" and line.get("capability")}
    hoisted = {str(line["flag"]) for line in written if line.get("kind") == "flag-hoisted" and line.get("flag")}
    rows = []
    for capability, members in slices_by_capability(charted).items():
        done = [slice_id for slice_id in members if slice_id in merged]
        rows.append({
            "capability": capability,
            "slices": members,
            "merged": len(done),
            "whole": len(done) == len(members),
            "gated": capability in gated,
            "accepted": capability in accepted,
            "hoisted": capability in hoisted,
            "waiting": [slice_id for slice_id in members if slice_id not in merged],
        })
    return rows


def gates_due(rows: list[dict]) -> list[dict]:
    """Whole and its gates not yet cleared: converge, gaps, design review, adversary, mutation and the walk."""
    return [row for row in rows if row["whole"] and not row["gated"] and not row["accepted"]]


def due(rows: list[dict]) -> list[dict]:
    """Whole, gated and not yet accepted. That is the whole trigger, and nothing about a flag is in it."""
    return [row for row in rows if row["whole"] and row["gated"] and not row["accepted"]]


def main(argv: list[str]) -> int:
    charted, feature = chart()
    if not charted:
        print("capabilities: no chart yet, so no capability is owed a demo")
        return 0
    rows = state(charted, lines(feature), cleared(feature, list(slices_by_capability(charted))))
    if "--gates" in argv:
        owed = gates_due(rows)
        print(f"capabilities: {len(owed)} owed their gates")
        for row in owed:
            print(f"  {row['capability']} — {', '.join(row['slices'])}")
        return 0
    if "--due" in argv:
        owed = due(rows)
        print(f"capabilities: {len(owed)} owed a demo")
        for row in owed:
            print(f"  {row['capability']} — {', '.join(row['slices'])}")
        return 0
    print(f"capabilities: {len(rows)} in {feature}")
    for row in rows:
        if row["accepted"]:
            where = "accepted" + (", hoisted" if row["hoisted"] else ", not hoisted")
        elif row["whole"] and row["gated"]:
            where = "whole and gated — a demo is due"
        elif row["whole"]:
            where = "whole — gates due"
        else:
            where = f"{row['merged']} of {len(row['slices'])} merged, waiting on {', '.join(row['waiting'])}"
        print(f"  {row['capability']}: {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
