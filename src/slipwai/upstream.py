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

**And only where there is nothing to discuss.** The first real run asked a question of a finished storyboard,
the reply's turn ended well, and that end was read as the step's: the board approved forty-nine states
straight past a review with fourteen Blockers, and started the model. A reply is not a step ending; a person's
word to a stage holds the board until they say to carry on (`stage_talk`), and a storyboard whose review has
a Blocker, whose research has a question open, or whose review cannot be read is left for the person, with
the reason said in the stage card and under Waiting on you (`stopped`).

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

from . import stage_talk
from .drawn import withdrawn
from .init_run import draft, draw, outside_session
from .passage import record_verdict, specifications, storyboards, surfaces
from .review_reading import gate
from .stage_steps import launch
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
    """The feature whose storyboard is drawn and has no verdict yet, or one a conversation has withdrawn part
    of by changing its pages, or `""` where there is none."""
    judged = {path.parent.parent.name for path in storyboards(root)}
    for spec in specifications(root):
        mockups = spec.parent / "mockups"
        drawn = mockups.is_dir() and next(mockups.glob("*.html"), None)
        if drawn and (spec.parent.name not in judged or withdrawn(root, spec.parent.name)):
            return spec.parent.name
    return ""


#: Which stage a command's conversation is, said the way a person reads it.
NAMED = {"mockups": "drawing", "model": "model", "draft": "draft", "launch": "launch", "assess": "assessment"}


def stopped(root: Path) -> tuple[str, str]:
    """Why the board, set to advance, will not press the next button by itself, and where on the page to go
    about it; `("", "")` where nothing holds it, and always on a project left at `park`.

    A person's word holds it — anything said to a stage, answered or queued, until they press Carry on or
    give the verdict the step waits for. And a storyboard is never approved past a review with a Blocker, a
    question only the person can answer, or a review that cannot be read."""
    if not advancing(root):
        return "", ""
    held = stage_talk.held(root)
    if held:
        named = " and ".join(f"the {NAMED.get(one, one)} stage" for one in held)
        queued = any(stage_talk.undelivered(root, one) for one in held)
        return (f"You said something to {named}{', and it waits to be said' if queued else ''}: the board does "
                "not move on by itself until you press Carry on" + (", or approve or disapprove the storyboard"
                                                                    if "mockups" in held else ""),
                "#storyboard-talk" if "mockups" in held else "#fitting")
    # Not while the drawing is still under way: what it has written so far is not yet the storyboard.
    waiting = unjudged(root) if outside_session(root) is None else ""
    why = gate(root, waiting) if waiting else ""
    if why:
        return (f"The storyboard for {waiting} waits for you rather than being approved by the board: {why}",
                "#mockups")
    return "", ""


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
        # Anything a person has said, and a storyboard with something in it to discuss, is a stop: `stopped`
        # says which, and the page says it where the person is looking.
        if advancing(board.root) and stopped(board.root)[0]:
            return
        # The draft is not a step a person holds off: a document with no specification is drafted the
        # moment the board sees it, once. What a draft that drafted nothing leaves is the button, and a line.
        if board.draftable() and not board.drafted:
            board.drafted = True
            board.fitting = draft(board.root, running.said()["lines"] if running else None)
            return
        done = not running or (running.said()["done"] and not running.said()["code"])
        step = next_step(board.root, done and not outside_session(board.root), board.drawable(), board.launchable())
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

