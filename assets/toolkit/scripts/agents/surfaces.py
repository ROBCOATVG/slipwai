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

**It has a budget, and the budget ends it.** A storyboard is a sketch a person reviews for flow, content,
states and feel, not the product, and a drawing stage with no clock spent seventy minutes on a redraw while
the person who asked for it waited. So the session is told its minutes (`SLIPWAI_BUDGET_MINUTES`, and the
wall-clock time they run out as `SLIPWAI_BUDGET_ENDS`) so that it can plan to them, and at the end of them it
is ended — it and every delegate it started — with what it drew left where it is and a line saying so. The
minutes come from `harbour.json`, the file the captain reads its stage budgets from, and move with the
telegraph's `stage_scale` the way those do.
"""
from __future__ import annotations

import json
import os
import re
import shlex
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
#: Read by the board, so a window that did not start this still shows the drawing as running. Three lines:
#: this process, when it started (epoch seconds) and its budget in seconds — the last two so the board can
#: say how far into its minutes the drawing is without a second copy of where the minutes come from.
PID = ROOT / ".slipwai" / "surfaces.pid"
#: Where the stage budgets are, which is where the captain reads its own.
HARBOUR = ROOT / "harbour.json"
#: Minutes for a first drawing and for a redraw, where `harbour.json` has no `surfaces` or `surfaces-redraw`
#: row. The generated file has none: its `stages` are the slice ladder's and a test holds them to that table,
#: which this stage is not on. A person who wants another number writes the row. Fifteen for a first drawing: a short design direction and a handful
#: of styled surfaces, each rendered once, is minutes of work, and the measured runs that took far longer
#: were spending the difference on polish nobody had asked for yet. Ten for a redraw, because a redraw
#: answers one reason, keeps the direction it has and changes only what the reason concerns.
FIRST_MINUTES = 15
REDRAW_MINUTES = 10


def budget(redraw: bool) -> float:
    """Seconds this drawing may take: the default scaled by `harbour.json`'s `stage_scale`, or the
    `surfaces` (or `surfaces-redraw`) row a person wrote there.

    A row is read as it stands, as `captain.stage_bound` reads its rows, because ringing the telegraph scales
    every row in `stages` in place and scaling it again here would count the telegraph twice. The default has
    no row to be scaled in, so `stage_scale` is applied to it here: a run rung down to `slow-ahead` draws to
    three quarters of the clock, like everything else. Never under a minute, which is the floor the
    telegraph's own scaling keeps: a budget of nothing would read as a drawing that failed.
    """
    try:
        held = json.loads(HARBOUR.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        held = {}
    held = held if isinstance(held, dict) else {}
    stages = held.get("stages") if isinstance(held.get("stages"), dict) else {}
    row = stages.get("surfaces-redraw" if redraw else "surfaces")
    minutes = row.get("minutes") if isinstance(row, dict) else None
    if isinstance(minutes, int | float) and not isinstance(minutes, bool) and minutes > 0:
        return max(1.0, float(minutes)) * 60.0
    scale = held.get("stage_scale")
    scale = float(scale) if isinstance(scale, int | float) and not isinstance(scale, bool) else 1.0
    return max(1.0, (REDRAW_MINUTES if redraw else FIRST_MINUTES) * scale) * 60.0


def specifications() -> list[Path]:
    return sorted(SPECS.glob("*/spec.md")) if SPECS.is_dir() else []


def drawn(feature: str) -> list[Path]:
    """Every surface drawn for that feature, which is what the session is expected to leave some of."""
    return sorted((SPECS / feature / MOCKUPS).glob("*.html"))


def touched(feature: str, since: float) -> bool:
    """Whether the session changed a drawing or the stylesheet they share at or after `since`.

    The stylesheet counts because it is often the whole of a good redraw: a reason about the look is a
    change to `mockups.css`, and nine surfaces redrawn to say the same thing would be the redraw the stage
    is told not to do. `research.md` does not count, because a redraw always writes to it.
    """
    home = SPECS / feature / MOCKUPS
    return any(path.stat().st_mtime >= since for pattern in ("*.html", "*.css") for path in home.glob(pattern))


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
    allowed = budget(bool(redraw))
    minutes = f"{allowed / 60:g}"
    ends = time.strftime("%H:%M", time.localtime(started + allowed))
    print(f"{said}; {why}", flush=True)
    if redraw:
        print(f"surfaces: the storyboard for {feature} was disapproved; drawing it again from the reason in "
              f"specs/{feature}/{MOCKUPS}/mock-states.md", flush=True)
    print(f"surfaces: the drawing has {minutes} minutes (until {ends}); at the end of them the session is "
          f"ended and whatever it drew is kept", flush=True)
    print(f"+ {line}", flush=True)
    environment = {**harness.child_environment(chosen), "SLIPWAI_STAGE": "surfaces",
                   "SLIPWAI_BUDGET_MINUTES": minutes, "SLIPWAI_BUDGET_ENDS": ends,
                   **({"SLIPWAI_REDRAW": "1"} if redraw else {})}
    PID.parent.mkdir(parents=True, exist_ok=True)
    PID.write_text(f"{os.getpid()}\n{started:.0f}\n{allowed:.0f}\n", encoding="utf-8")
    try:
        exited, expired = harness.run_bounded(shlex.split(line), ROOT, environment, allowed)
    finally:
        if PID.is_file() and PID.read_text(encoding="utf-8").partition("\n")[0].strip() == str(os.getpid()):
            PID.unlink()
    if expired:
        # Not a failure: a budget reached is the stage working as designed, and what it drew is a sketch a
        # person can already review. So it is said, and then judged by the same rules as any other end —
        # something drawn is a storyboard to look at (0); nothing drawn is still nothing to approve (1).
        storyboard = SPECS / feature / MOCKUPS / "storyboard.html"
        print(f"surfaces: ended at its budget of {minutes} minutes; kept {len(drawn(feature))} drawing(s) "
              f"under specs/{feature}/{MOCKUPS}/"
              + ("" if storyboard.is_file() else ", and no storyboard.html was written yet"), flush=True)
        exited = 0
    if exited:
        print(f"surfaces: the session exited {exited}; whatever it drew is under "
              f"specs/{feature}/{MOCKUPS}/, uncommitted or committed as it said", file=sys.stderr)
        return exited
    written = [path for path in drawn(feature) if path not in before]
    if not written and not drawn(feature):
        print(f"surfaces: the session ended with nothing under specs/{feature}/{MOCKUPS}/, so there is no "
              f"storyboard to approve; read its last lines above", file=sys.stderr)
        return 1
    if redraw:
        if not touched(feature, started):
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
