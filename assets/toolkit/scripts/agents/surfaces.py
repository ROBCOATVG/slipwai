#!/usr/bin/env python3
"""`/mockups`, started for you: the surfaces researched, drawn and storyboarded, and then a stop.

The half of the mock-up stage that does not need anybody. `/mockups` is two halves — a researcher and a
draughtsman, then a person looked at one surface at a time — and the second half is the point of the stage,
so it is not automated here and never will be. What is automated is the wait in front of it: a person who
has read the specification and wants the screens drawn had to open the agent and type the command, and the
board, which had just run two headless sessions for them, had nothing to offer.

    python3 scripts/agents/surfaces.py              # the first feature with a specification
    python3 scripts/agents/surfaces.py 001-thing    # a named one

One headless session with `commands/mockups.md` as its rules, told which stage it is
(`SLIPWAI_STAGE=surfaces`) the way `draft.py` and `launch.py` tell theirs, because that file has two faces
and the environment is how it tells them apart. It stops at the storyboard. Nothing is marked approved by
a session nobody was in: the verdicts are what `/mockups` asks a person for, and a file full of approvals
that nobody gave is the one outcome this stage exists to prevent.
"""
from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402

ROOT = harness.ROOT
COMMAND = ROOT / "commands/mockups.md"
SPECS = ROOT / "specs"
MOCKUPS = "mockups"


def specifications() -> list[Path]:
    return sorted(SPECS.glob("*/spec.md")) if SPECS.is_dir() else []


def drawn(feature: str) -> list[Path]:
    """Every surface drawn for that feature, which is what the session is expected to leave some of."""
    return sorted((SPECS / feature / MOCKUPS).glob("*.html"))


def main(argv: list[str]) -> int:
    specs = specifications()
    if not specs:
        print("surfaces: there is no specs/<feature>/spec.md to draw surfaces for; `make draft` writes the "
              "first one, or /speckit-specify does with the agent", file=sys.stderr)
        return 2
    feature = argv[0] if argv else specs[0].parent.name
    if not (SPECS / feature / "spec.md").is_file():
        named = ", ".join(path.parent.name for path in specs)
        print(f"surfaces: {feature} has no specification here; this project has {named}", file=sys.stderr)
        return 2
    try:
        chosen, said = harness.choose()
    except harness.NoHarness as refusal:
        print(f"surfaces: {refusal}", file=sys.stderr)
        return 2
    template, why = harness.template(chosen)
    prompt = harness.prompt_for(chosen, "mockups", COMMAND, feature)
    line = template.replace("{prompt}", shlex.quote(prompt))
    before = set(drawn(feature))
    print(f"{said}; {why}", flush=True)
    print(f"+ {line}", flush=True)
    environment = {**harness.child_environment(chosen), "SLIPWAI_STAGE": "surfaces"}
    done = subprocess.run(shlex.split(line), cwd=ROOT, env=environment, check=False)
    if done.returncode:
        print(f"surfaces: the session exited {done.returncode}; whatever it drew is under "
              f"specs/{feature}/{MOCKUPS}/, uncommitted or committed as it said", file=sys.stderr)
        return done.returncode
    written = [path for path in drawn(feature) if path not in before]
    if not written and not drawn(feature):
        print(f"surfaces: the session ended with nothing under specs/{feature}/{MOCKUPS}/, so there is no "
              f"storyboard to approve; read its last lines above", file=sys.stderr)
        return 1
    print(f"drawn: {len(drawn(feature))} surface(s) under specs/{feature}/{MOCKUPS}/ — open the storyboard, "
          f"then /mockups {feature} in the agent walks you through approving each state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
