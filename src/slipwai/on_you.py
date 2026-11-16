"""What waits on a person, as one list: the strip above the page, its count on the tab, and the column.

Three places said it, each from its own reading. The strip counted the parks the fleet groups and the
questions no park holds; the Fleet tab's badge counted every inbox row that was not paused, notes and
unread decisions among them; the column counted slices the fold had in `waiting`. On one run the three
said 4, 9 and 2 at once, and none of them was wrong by its own lights.

So this is the one reading, in two groups. *Holding work up*: a slice parked on a person, a card a running
stage has put up, the one button the run cannot pass without, and a stream's log nobody can read (its
captain stops at every start until a person repairs the line). *When you have time*: a capability with
something to look at, and a feedback proposal waiting for Confirm. A note nobody has read and a slice paused
until a set time are not on it: neither holds anything up, and neither needs a person to move. Each item
links to where it is acted on, and the column draws exactly the slices this names.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .bridge_page import inbox_rows
from .feedback import items
from .fleet_page import first_sentence, group_card, parks_table, plural
from .stage_session import running
from .upstream import unjudged

NOTHING_WAITS: dict[str, Any] = {"count": 0, "text": "", "href": "", "holding": [], "later": [], "slices": []}


def open_asks(board: Any) -> int:
    """The cards a running stage has put up and nobody has answered."""
    session = running(board)
    if session is None:
        return 0
    turns = session.said(0)["turns"]
    asked = {t["ask"]["id"] for t in turns if t.get("kind") in ("permission", "question") and t.get("ask")}
    answered = {t["ask"]["id"] for t in turns if t.get("kind") == "answered" and t.get("ask")}
    return len(asked - answered)


def button_waiting(board: Any, able: dict[str, bool]) -> tuple[str, str]:
    """The one step the page offers that the run cannot pass without: what it says, and where it is."""
    fitting = getattr(board, "fitting", None)
    approving = unjudged(board.root) if fitting is None or fitting.said()["done"] else ""
    if approving:
        return f"The storyboard for {approving} is drawn: approve it or send it back", "#tab-screens"
    for flag, said, where in (("draftable", "The draft ended without a specification: draft it again", "#draft"),
                              ("drawable", "The specification is ready: read it, then draw the storyboard", "#draw"),
                              ("modelable", "The storyboard is approved: model it", "#model"),
                              ("launchable", "The storyboard is approved: continue the build", "#launch"),
                              ("castable", "The chart is split: cast off the fleet", "#cast-off")):
        if able.get(flag):
            return said, where
    return "", ""


def slice_item(row: dict[str, str]) -> dict[str, Any]:
    """A slice parked on a person, said as its name and what it waits for, linked to its card."""
    name = f'{row["slice"]} · {row["title"]}' if row.get("title") else row["slice"]
    asked = [one for one in str(row.get("asked") or "").splitlines() if one.strip()]
    why = (f"{plural(len(asked), 'question')} open" if asked
           else first_sentence(str(row.get("park") or row.get("why") or ""), 90) or "waiting on you")
    return {"n": 1, "text": f"{name}: {why}", "href": f"#card-{row['slice']}", "slice": row["slice"]}


def waiting(board: Any, fleet: dict[str, Any], able: dict[str, bool],
            rows: list[dict[str, str]] | None = None, root: Path | None = None) -> dict[str, Any]:
    """The list: how many things, the first of them in its own words with the way to it, both groups, and
    the slices the column draws. `able` is the flags that show the strip's buttons, so the words here and
    the button there agree; a stage still running offers no button, and is not a wait."""
    holding: list[dict[str, Any]] = []
    asked = open_asks(board)
    if asked:
        holding.append({"n": asked, "href": "#stage-asks", "text": "The agent asks you something" if asked == 1
                        else f"The agent asks you {asked} things"})
    holding += [slice_item(row) for row in rows or [] if row.get("state") == "waiting"]
    holding += [{"n": 1, "text": f"The {row['fairway']} log cannot be read: its captain cannot start",
                 "href": "#from-streams"} for row in fleet.get("inbox") or [] if row.get("kind") == "unreadable"]
    said, where = button_waiting(board, able)
    if said:
        holding.append({"n": 1, "text": said, "href": where})
    later = [{"n": 1, "text": f"{name} is ready for you to see", "href": "#feedback"}
             for name in sorted(fleet.get("demo_due_in") or {})]
    proposed = len([one for one in items(root or board.root) if one.state == "proposed"])
    if proposed:
        said = ("A piece of feedback has" if proposed == 1 else f"{proposed} pieces of feedback have")
        later.append({"n": proposed, "href": "#feedback", "text": f"{said} a proposed route to confirm"})
    if not holding and not later:
        return dict(NOTHING_WAITS)
    first = (holding or later)[0]
    return {"count": sum(one["n"] for one in holding + later), "text": first["text"], "href": first["href"],
            "holding": holding, "later": later, "slices": [one["slice"] for one in holding if one.get("slice")]}


def streams_card(fleet: dict[str, Any], controls: bool = True) -> str:
    """What the streams have asked of a person or told them, answered here: each park with what it needs,
    a question no park holds, a hand-back, a note, the decisions nobody has read, a log nobody can read.

    The Fleet tab carried this, and it is not machinery. It sits under the work because that is where the
    slices it is about are; a paused park is left out, since nothing in it is a person's to do.
    """
    groups = [g for g in fleet.get("groups") or [] if g.get("paused") != "yes"]
    others = [row for row in fleet.get("inbox") or [] if row["kind"] != "parked"]
    if not groups and not others:
        return ""
    cards = "".join(group_card(group, controls) for group in groups)
    listed = inbox_rows(others, controls, fleet.get("streams")) if others else ""
    return (f'<div class="card" id="from-streams"><h2>From the streams</h2><p class="empty">What each stream '
            f"has asked of you or left for you, answered from here. Notes and unread decisions hold nothing up, "
            f"so they are not counted as waiting on you.</p>{cards}{listed}</div>{parks_table(fleet)}")

