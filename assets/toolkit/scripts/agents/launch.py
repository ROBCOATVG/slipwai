#!/usr/bin/env python3
"""`/launch`: from a drafted specification to a running fleet, with nobody asked again until a captain parks.

`/draft` stops at `specs/<feature>/spec.md` so a person can read it; this is what they run having read it,
and what the board's **Continue the build** button runs. Three steps, each skipped where it is already done:
the chart and the split, in one headless session with `commands/launch.md` as its rules; `/cruise` enabled;
and the fleet cast off (`fleet.py start`). The session is told which stage it is (`SLIPWAI_STAGE=launch`) the
way a captain tells a `/sail` session, because the page it reads has two faces.

    python3 scripts/agents/launch.py                # chart and split if needed, enable, cast off
    python3 scripts/agents/launch.py --boilers 2    # passed through to the fleet
"""
from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clearance  # noqa: E402
import harness  # noqa: E402

ROOT = harness.ROOT
COMMAND = ROOT / "commands/launch.md"
SPECS = ROOT / "specs"


def specified() -> bool:
    return SPECS.is_dir() and any(SPECS.glob("*/spec.md"))


def split() -> bool:
    """Whether a chart with slices in it exists, which is what the fleet lights captains from."""
    charted, _ = clearance.chart()
    return bool(charted.get("slices"))


def chart_and_split() -> int:
    """The upstream stages, in one dispatched session. Its exit status, or a refusal's."""
    try:
        chosen, said = harness.choose()
    except harness.NoHarness as refusal:
        print(f"launch: {refusal}", file=sys.stderr)
        return 2
    template, why = harness.template(chosen)
    line = template.replace("{prompt}", shlex.quote(harness.prompt_for(chosen, "launch", COMMAND)))
    print(f"{said}; {why}", flush=True)
    print(f"+ {line}", flush=True)
    environment = {**harness.child_environment(chosen), "SLIPWAI_STAGE": "launch"}
    exited = harness.run_session(shlex.split(line), ROOT, environment)
    if exited:
        print(f"launch: the session exited {exited}; nothing was cast off", file=sys.stderr)
        return exited
    if not split():
        print("launch: the session ended without a split, so there is nothing to light a captain for; read its "
              "last lines above — a park there names what a person has to decide", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str]) -> int:
    if not specified():
        print("launch: no specs/<feature>/spec.md to build from. `/draft docs/prd.md` writes one from a product "
              "requirements document, and `/speckit-specify` writes one with you", file=sys.stderr)
        return 2
    if split():
        print("charted and split already; enabling /cruise and casting off", flush=True)
    elif (code := chart_and_split()):
        return code
    enabled = subprocess.run([sys.executable, str(HERE / "cruise.py"), "--set", "enabled=true"], cwd=ROOT,
                             check=False)
    if enabled.returncode:
        return enabled.returncode
    return subprocess.run([sys.executable, str(HERE / "fleet.py"), "start", *argv], cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
