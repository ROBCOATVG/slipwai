"""The steps above the chart, advanced without a person when the project says so.

Drafting the specification, drawing the storyboard and modelling each end at a stop: the board shows what was
made and a person presses the button for the next step, or approves the storyboard. That stop is the default
and the reason is in `init_run` — a specification somebody has read is the line between what the agent
drafts and what runs unattended. `upstream: advance` in `.specify/cruise.json` is a person choosing to give
that line up for a project: each step, when it ends well, presses the next one's button itself.

**Only the buttons a person would have pressed, and only after a step that ended well.** A step that failed
stops here as it always did, so does a disapproved storyboard, and so does anything the board is already
running. What is decided is the one step the board would offer next — this reads the same `drawable` and
`launchable` the buttons are shown by, so it cannot press one that is not there.

**An approval given this way says so.** The storyboard's `mock-states.md` carries a line naming the setting,
because the file is what the model and the chart read as a person's verdict, and one nobody gave has to be
told apart from one somebody did.

The board does this when it is polled, which is what every open board window does every few seconds. A
board with no window open advances nothing until one is.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from .init_run import draw, launch, model_session
from .passage import record_verdict, specifications, storyboards, surfaces
from .wheel import orders

#: The setting, and the value that advances rather than stops.
SETTING = "upstream"
ADVANCE = "advance"
#: The line an approval given by this setting carries at the top of `mock-states.md`.
#: One advance at a time across the board's windows, which all poll: two at once would be two drawings.
PRESSING = threading.Lock()
APPROVED_BY = ("<!-- Approved by the board, not a person: `upstream` is `advance` in .specify/cruise.json. "
               "To judge it yourself, set that back to `park`, delete this file, and approve or disapprove "
               "the storyboard on the board. -->")


def advancing(root: Path) -> bool:
    """Whether this project has asked for the steps above the chart to advance on their own."""
    return orders(root).get(SETTING) == ADVANCE


def unjudged(root: Path) -> str:
    """The feature whose storyboard is drawn and has no verdict yet, or `""` where there is none."""
    judged = {path.parent.parent.name for path in storyboards(root)}
    for spec in specifications(root):
        mockups = spec.parent / "mockups"
        if spec.parent.name not in judged and mockups.is_dir() and next(mockups.glob("*.html"), None):
            return spec.parent.name
    return ""


def next_step(root: Path, idle: bool, drawable: bool, launchable: bool) -> str:
    """The step to start: `draw`, `approve <feature>`, `launch`, or `""` for nothing.

    `idle` is the board having nothing running and nothing that failed: a step that ended badly is a stop
    whatever this says, because what it made is not something to build on unattended.
    """
    if not idle or not advancing(root):
        return ""
    # A disapproved storyboard is a person's no, and what it waits on is a drawing they have not seen yet.
    if surfaces(root)[2]:
        return ""
    # Drawn once: a stage that found nothing to draw writes its `mock-states.md` and no page, and `drawable`
    # reads pages, so without this it would be drawn again on every poll.
    if drawable and not storyboards(root):
        return "draw"
    waiting = unjudged(root)
    if waiting:
        return f"approve {waiting}"
    return "launch" if launchable else ""


def advance(board: Any) -> None:
    """Press the next step's button on `board` — the bridge's request, which holds the project's running
    child — where `upstream` is `advance` and the step before ended well."""
    if not PRESSING.acquire(blocking=False):
        return  # another window's poll is already pressing it
    try:
        running = board.fitting
        done = not running or (running.said()["done"] and not running.said()["code"])
        step = next_step(board.root, done and not model_session(board.root), board.drawable(), board.launchable())
        lines = running.said()["lines"] if running else None
        if step == "draw":
            board.fitting = draw(board.root, lines)
        elif step.startswith("approve "):
            board.after_storyboard(record_verdict(board.root, step.split()[1], "approved", by=APPROVED_BY))
        elif step == "launch":
            board.launched = True
            board.fitting = launch(board.root, lines)
    finally:
        PRESSING.release()
