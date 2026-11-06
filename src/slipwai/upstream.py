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

from .fleet_page import plural, waiting_on_you
from .init_run import draw, outside_session
from .passage import record_verdict, specifications, storyboards, surfaces
from .stage_session import running
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


def open_asks(board: Any) -> int:
    """The cards a running stage has put up and nobody has answered."""
    session = running(board)
    if session is None:
        return 0
    turns = session.said(0)["turns"]
    asked = {t["ask"]["id"] for t in turns if t.get("kind") in ("permission", "question") and t.get("ask")}
    answered = {t["ask"]["id"] for t in turns if t.get("kind") == "answered" and t.get("ask")}
    return len(asked - answered)


def on_voyage(board: Any, fleet: dict[str, Any], able: dict[str, bool]) -> dict[str, Any]:
    """What the Voyage waits on a person for: one count, and the first thing in its own words with the way
    to it. `able` is the flags that show the strip's buttons, so the words here and the button there agree.

    A question on a card and a slice parked on somebody are counted each; a button the page is offering is
    one thing, whichever it is, because the stages come one at a time. A stage still running offers no
    button and is not a wait, which is what `able` already says.
    """
    held: list[tuple[int, str, str]] = []
    asked = open_asks(board)
    if asked:
        held.append((asked, "The agent asks you something" if asked == 1 else f"The agent asks you {asked} things",
                     "#stage-asks"))
    on_you = waiting_on_you(fleet)
    if on_you:
        held.append((on_you, f"{plural(on_you, 'slice')} waiting on you", "#tab-work"))
    fitting = getattr(board, "fitting", None)
    approving = unjudged(board.root) if fitting is None or fitting.said()["done"] else ""
    if approving:
        held.append((1, f"The storyboard for {approving} is drawn: approve it or send it back", "#tab-screens"))
    elif able.get("draftable"):
        held.append((1, "The draft ended without a specification: draft it again", "#draft"))
    elif able.get("drawable"):
        held.append((1, "The specification is ready: read it, then draw the surfaces", "#draw"))
    elif able.get("modelable"):
        held.append((1, "The storyboard is approved: model it", "#model"))
    elif able.get("launchable"):
        held.append((1, "The storyboard is approved: continue the build", "#launch"))
    elif able.get("castable"):
        held.append((1, "The chart is split: cast off the fleet", "#cast-off"))
    if not held:
        return {"count": 0, "text": "", "href": ""}
    return {"count": sum(n for n, _, _ in held), "text": held[0][1], "href": held[0][2]}
