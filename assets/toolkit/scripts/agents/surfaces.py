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

import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402

ROOT = harness.ROOT
COMMAND = ROOT / "commands/mockups.md"
SPECS = ROOT / "specs"
MOCKUPS = "mockups"
#: One state's verdict in `mock-states.md`, read the way the board reads it.
VERDICT = re.compile(r"^-\s*.+?\s*\u2014\s*(approved|parked|n/a)\b", re.MULTILINE)
#: Where a disapproved storyboard's verdicts go once it is drawn again, newest last.
DISAPPROVED = "disapproved.md"
#: Read by the board, so a window that did not start this still shows the drawing as running.
PID = ROOT / ".slipwai" / "surfaces.pid"


def specifications() -> list[Path]:
    return sorted(SPECS.glob("*/spec.md")) if SPECS.is_dir() else []


def drawn(feature: str) -> list[Path]:
    """Every surface drawn for that feature, which is what the session is expected to leave some of."""
    return sorted((SPECS / feature / MOCKUPS).glob("*.html"))


def turned_down(feature: str) -> str:
    """The disapproved storyboard's verdicts, or `""` where this is a first drawing.

    Every state parked is what the board's Disapprove writes. That is a no to the drawing, and a session
    that found drawings already there and no word of it would review them as a person's hand-over and
    change nothing — which is how a disapproval used to end a run.
    """
    path = SPECS / feature / MOCKUPS / "mock-states.md"
    said = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    verdicts = VERDICT.findall(said)
    return said if verdicts and all(verdict == "parked" for verdict in verdicts) else ""


def retire(feature: str, said: str) -> None:
    """Move the old verdicts out of the way, so the new drawing waits on a verdict of its own. Kept, not
    deleted, because the reason is what the next person to read the storyboard will want to see answered."""
    home = SPECS / feature / MOCKUPS
    log = home / DISAPPROVED
    before = log.read_text(encoding="utf-8") if log.is_file() else "# Disapproved storyboards\n"
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    log.write_text(f"{before.rstrip()}\n\n## Redrawn {stamp}\n\n{said.strip()}\n", encoding="utf-8")
    (home / "mock-states.md").unlink(missing_ok=True)


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
    redraw = turned_down(feature)
    started = time.time()
    print(f"{said}; {why}", flush=True)
    if redraw:
        print(f"surfaces: the storyboard for {feature} was disapproved; drawing it again from the reason in "
              f"specs/{feature}/{MOCKUPS}/mock-states.md", flush=True)
    print(f"+ {line}", flush=True)
    environment = {**harness.child_environment(chosen), "SLIPWAI_STAGE": "surfaces",
                   **({"SLIPWAI_REDRAW": "1"} if redraw else {})}
    PID.parent.mkdir(parents=True, exist_ok=True)
    PID.write_text(f"{os.getpid()}\n", encoding="utf-8")
    try:
        done = subprocess.run(shlex.split(line), cwd=ROOT, env=environment, check=False)
    finally:
        if PID.is_file() and PID.read_text(encoding="utf-8").strip() == str(os.getpid()):
            PID.unlink()
    if done.returncode:
        print(f"surfaces: the session exited {done.returncode}; whatever it drew is under "
              f"specs/{feature}/{MOCKUPS}/, uncommitted or committed as it said", file=sys.stderr)
        return done.returncode
    written = [path for path in drawn(feature) if path not in before]
    if not written and not drawn(feature):
        print(f"surfaces: the session ended with nothing under specs/{feature}/{MOCKUPS}/, so there is no "
              f"storyboard to approve; read its last lines above", file=sys.stderr)
        return 1
    if redraw:
        if not any(path.stat().st_mtime >= started for path in drawn(feature)):
            print(f"surfaces: the session ended without redrawing anything under specs/{feature}/{MOCKUPS}/, so "
                  f"the disapproval stands and Draw the surfaces is still on the board; read its last lines "
                  f"above", file=sys.stderr)
            return 1
        retire(feature, redraw)
    print(f"drawn: {len(drawn(feature))} surface(s) under specs/{feature}/{MOCKUPS}/ — open the storyboard, "
          f"then /mockups {feature} in the agent walks you through approving each state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
