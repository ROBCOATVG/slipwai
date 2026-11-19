#!/usr/bin/env python3
"""Running an extension's hook at a point, and recording which extensions were elected.

Two jobs, one file, because they are two halves of one fact — which extensions this project elected and what
each of them attached to.

`--elect <key>...` writes `.slipwai/hooks.json` from `available.json` and `available-tools.json`, which the
generator wrote beside this script from the installed packages' manifests. `./init` calls it once, after the
elected extensions have installed themselves. The tool names go in the same file because they follow the
election exactly: unlike a guard, which may refuse a tool call and so is agreed to separately, a tool is
only ever something an extension already there needs the agent allowed to reach. The registry is a controlled file: an iteration that edits it is refused like one that
edits a gate, so a run cannot register a hook on itself.

`<point> [--key value ...]` runs whatever is attached to that point, in extension-name order, each with its
own budget, and **exits 0 whatever any of them did**. A hook is a second belt: the captain's controls — the
last line, the controlled-files diff, the bounded waits, the inbox receipt — all work with every hook
removed. An extension that could fail a stage is an extension that can stop a delivery loop it was added to
help, so what a failing hook produces is a `hook` line naming the extension, the point and the last thing it
printed.

`--fatal` is the one exception, and `make check-extensions` is the only caller that passes it. The `check`
point *is* a gate: an extension that says this project's index is stale is saying the gate should be red, and
a gate that cannot fail is not a gate. The rule it is an exception to is about the rungs of the ladder, which
is where a second control plane would do the damage.

Standalone and dependency-free, like everything else under `scripts/`: this ships inside a generated project,
which has no slipwai to import.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AVAILABLE = HERE / "available.json"
TOOLS = HERE / "available-tools.json"
DEFAULT_BUDGET = "30s"


def project_root() -> Path:
    """The project this runs in: the nearest parent holding `project.json`, else three directories up."""
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
REGISTRY = ROOT / ".slipwai/hooks.json"


def seconds(budget: str) -> float:
    """A budget as seconds. `30s`, `2m`, or a bare number; anything else falls back to the default rather
    than refusing — a budget nobody can parse is not a reason a hook does not run."""
    text = str(budget).strip().lower()
    scale = {"s": 1.0, "m": 60.0, "h": 3600.0}.get(text[-1:], 1.0)
    try:
        return float(text.rstrip("smh")) * scale
    except ValueError:
        return 30.0


def read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}


def elect(keys: list[str]) -> int:
    """Write `.slipwai/hooks.json` for the extensions `keys` names, by point, in firing order.

    And the tool names those extensions need a headless session allowed to call, which `harness.py` reads
    when it builds the command. Declared order is kept inside one extension and the extensions are taken in
    name order, so the list is the same on two machines that elected the same set.
    """
    available, offered = read(AVAILABLE), read(TOOLS)
    points: dict[str, list[dict]] = {}
    tools: list[str] = []
    for key in sorted(set(keys)):
        for name, body in sorted(available.get(key, {}).items()):
            points.setdefault(name, []).append({"extension": key, **body})
        for name in offered.get(key, []):
            if isinstance(name, str) and name.strip() and name not in tools:
                tools.append(name.strip())
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps({"v": 1, "points": points, "tools": tools}, indent=2) + "\n"
    REGISTRY.write_text(body, encoding="utf-8")
    attached = ", ".join(sorted(points)) or "no point"
    allowed = f", {len(tools)} tool name(s) allowed" if tools else ""
    print(f"hooks: {len(set(keys) & set(available))} extension(s) attached to {attached}{allowed}")
    return 0


def said(run: subprocess.CompletedProcess | None, failure: str = "") -> str:
    """The last thing a hook printed, which is what a `hook` line carries — one line, whatever it wrote."""
    if failure:
        return failure
    assert run is not None
    text = (run.stdout or "") + (run.stderr or "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else "said nothing"


def applies(body: dict, given: dict[str, str]) -> bool:
    """Whether this hook wants this rung. A hook that names no `stages` wants all of them."""
    stages = body.get("stages")
    return not isinstance(stages, list) or given.get("stage") in stages


def guards_held(point: str) -> dict[str, str]:
    """`SLIPWAI_GUARDS_HELD` at `init` and `project`: per installed harness, the moments a guard holds at.

    Those two points are where an extension writes what it tells the agent, and *a guard refuses that
    search here* is true on one harness and false on the next. Handed as JSON so the guidance can say which,
    and left out wherever it could not be worked out — a hook is never failed for a variable."""
    if point not in ("init", "project"):
        return {}
    try:
        import guard_harness  # beside this script; asked for here so every other point runs without it
        return {"SLIPWAI_GUARDS_HELD": json.dumps(guard_harness.held())}
    except Exception:  # noqa: BLE001
        return {}


def fire(point: str, given: dict[str, str], fatal: bool = False) -> int:
    """Run everything attached to `point`. 0 unless `fatal` and something failed — see the module docstring."""
    failed = 0
    for body in read(REGISTRY).get("points", {}).get(point, []):
        key, script = body.get("extension", "?"), body.get("run", "")
        if not applies(body, given):
            continue
        path = ROOT / "scripts/extensions" / key / script
        if not path.is_file():
            print(f"hook {key} {point}: {path} is not in this project", file=sys.stderr)
            failed += 1
            continue
        # `SLIPWAI_POINT` is how one script answers two points: an extension's entry point is the default
        # declaration for both `init` and `project`, and at `project` it re-projects its block and installs
        # nothing, because a re-projection happens on every `make agents` and is not an election.
        environment = {**os.environ, "SLIPWAI_POINT": point, **guards_held(point),
                       **{f"SLIPWAI_{name.upper()}": value for name, value in given.items()}}
        try:
            run = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, cwd=ROOT,
                                 timeout=seconds(body.get("budget", DEFAULT_BUDGET)), env=environment)
        except subprocess.TimeoutExpired:
            print(f"hook {key} {point}: over its {body.get('budget', DEFAULT_BUDGET)} budget, ended",
                  file=sys.stderr)
            failed += 1
            continue
        except OSError as error:
            print(f"hook {key} {point}: could not run ({type(error).__name__})", file=sys.stderr)
            failed += 1
            continue
        if run.returncode != 0:
            print(f"hook {key} {point}: exited {run.returncode}; {said(run)}", file=sys.stderr)
            failed += 1
            continue
        if run.stdout.strip():
            print(run.stdout.strip())
    return 1 if fatal and failed else 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 0
    if argv[0] == "--elect":
        return elect(argv[1:])
    given: dict[str, str] = {}
    rest = [word for word in argv[1:] if word != "--fatal"]
    for index in range(0, len(rest) - 1, 2):
        if rest[index].startswith("--"):
            given[rest[index][2:]] = rest[index + 1]
    return fire(argv[0], given, fatal="--fatal" in argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
