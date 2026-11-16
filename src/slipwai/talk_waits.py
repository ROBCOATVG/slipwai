"""What the conversations add to the board: a card's last word and its marker, and what waits on a person.

Two things a conversation can hold a person up with, and one it never does. A product question a slice
asked is *Holding work up* where the project says a person answers them, and nothing at all where the
skipper does (the skipper's answer is in the thread, and in the decision log). A slice a person paused is
*When you have time* — it will not move until they resume it — and one its captain paused is neither: the
captain resumes what it paused. A message nobody has read is a marker on a card, never a count.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from . import talk
from .fleet_page import first_sentence
from .logs import run_dir
from .talk_fold import last, open_asks, person_answers, placed_for, seen, turns, unseen

IN_FLIGHT = ("working", "queued", "waiting")


def window(fairway: str, slice_id: str, where: str = "") -> str:
    """A slice's window, where its conversation and its asks are answered."""
    return f"/slice?fairway={quote(fairway, safe='')}&slice={quote(slice_id, safe='')}{where}"


def captain_window(fairway: str) -> str:
    """A stream's captain's window: its slices, what it decided today, and its conversation."""
    return f"/captain-window?fairway={quote(fairway, safe='')}"


def talking(root: Path, rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Each slice with a conversation folder, folded, keyed by slice: the rows say which stream it is in."""
    run = run_dir(root)
    found: dict[str, dict[str, Any]] = {}
    held: dict[str, set[str]] = {}
    for row in rows:
        fairway = row.get("fairway") or ""
        if not fairway:
            continue
        if fairway not in held:
            held[fairway] = set(talk.conversations(run, fairway))
        if row["slice"] in held[fairway]:
            try:
                found[row["slice"]] = turns(talk.place(run, fairway, row["slice"]))
            except ValueError:
                continue
    return found


def summaries(root: Path, rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    """A card's part of each conversation: the last thing said with its receipt, whether something in it
    is news to a person, and the product question waiting on them, if one is."""
    kept = seen(root)
    asks_you = person_answers(root)
    found = {}
    by_slice = {row["slice"]: row for row in rows}
    for slice_id, folded in talking(root, rows).items():
        fairway = by_slice[slice_id].get("fairway", "")
        waiting = open_asks(folded) if asks_you else []
        folded = {**folded, "turns": placed_for(folded["turns"], by_slice[slice_id].get("state", ""))}
        mine = [one for one in folded["turns"] if one["kind"] == "said" and one["who"] == "You"
                and not one["steer"] and one["state"] == "queued"]
        found[slice_id] = {"last": last(folded), "new": unseen(root, fairway, slice_id, folded["heard"], kept),
                           "ask": waiting[0] if waiting else None, "halted": folded["halted"],
                           "by": folded["by"], "how": folded["how"],
                           # The person's newest message still waiting: on a parked slice, their answer.
                           "answer": {"id": mine[-1]["id"], "text": mine[-1]["text"], "t": mine[-1]["t"],
                                      "line": mine[-1]["line"], "tone": mine[-1]["tone"],
                                      "changeable": True} if mine else None}
    return found


def items(root: Path, rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """What the conversations put on the one list: (holding work up, when you have time)."""
    holding: list[dict[str, Any]] = []
    later: list[dict[str, Any]] = []
    asks_you = person_answers(root)
    by_slice = {row["slice"]: row for row in rows}
    for slice_id, folded in talking(root, rows).items():
        row = by_slice[slice_id]
        if row.get("state") not in IN_FLIGHT:
            continue
        for one in open_asks(folded) if asks_you else []:
            holding.append({"n": 1, "slice": slice_id, "href": window(row["fairway"], slice_id, f"#ask-{one['id']}"),
                            "text": f"{slice_id} asks: {first_sentence(one['text'], 90) or 'a question'}"})
        if folded["halted"] == "paused" and folded["by"] == talk.PERSON:
            later.append({"n": 1, "href": window(row["fairway"], slice_id),
                          "text": f"{slice_id} is paused by you: resume it when you are ready"})
    return holding, later
