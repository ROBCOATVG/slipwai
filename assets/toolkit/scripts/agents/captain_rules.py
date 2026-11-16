#!/usr/bin/env python3
"""The captain's fixed rules: what the program decides where nothing else does.

The captain chose in four places, each a line or two inside a longer loop: which cleared slice starts next,
whether a slice that missed its gate runs again and with what words, what to do about a slice that is
stuck, and where something said to the stream goes. Each is a rule here, taking the facts and returning the
order the rule gives — in the shape `orders.py` writes, so an order from the captain's agent and one from
the rule are read by one path. The program decides with these where the stream runs on it alone, and where
the agent is silent past its bound, gives an order it may not, or cannot be run.

Nothing here reads a file or writes one: a rule is the facts in and the order out, which is what lets the
same rule be the default an event offers the agent and the fallback the program applies.

Standalone and dependency-free: this runs inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

from typing import Any

Order = dict[str, Any]


def choose_next(candidates: list[str], free: int) -> list[Order]:
    """The slices to start now: the first `free` of them, in the order they were offered — split order for
    new work, furthest along first for work carried on, which the caller has already put them in."""
    return [{"verb": "start", "slice": one} for one in candidates[:max(0, free)]]


def last_run(why: str, tried: int) -> str:
    """What a park says where the retries are spent."""
    return f"{why}. That was the last of {tried} run(s), which is what `attempts` allows"


def after_gate(slice_id: str, why: str, tried: int, ceiling: int) -> Order:
    """After a run that did not close its gate: run it again told why, while `attempts` allows; park it
    saying why and how many runs it had once they are spent."""
    if tried <= ceiling:
        return {"verb": "retry", "slice": slice_id, "note": why}
    return {"verb": "park", "slice": slice_id, "why": last_run(why, tried)}


#: What the rule does about a stuck slice, a message to the stream and a red trunk: nothing. The stage bound
#: still ends a slice that writes nothing, a red trunk still holds every new start, and a message to the
#: stream stays queued for whoever reads it next.
STILL = {
    "stuck": "the rule does nothing about a stuck slice: the stage bound still ends one that writes nothing",
    "message": "the rule routes nothing: the message stays queued for the captain's next wake-up",
    "trunk-red": "the rule holds every new start until trunk is green, and sends no word of its own",
    "choose-next": "the rule starts the slices first in order",
    "gate-failed": "the rule retries while `attempts` allows, and parks once they are spent",
}


def none(kind: str) -> Order:
    return {"verb": "none", "why": STILL.get(kind, "the rule does nothing here")}


def on_ask(ask: dict[str, Any]) -> Order:
    """Something a slice's session asked mid-turn that the berth's policy did not settle: a permission
    outside the berth is refused, and a question declined — a product question becomes a `question` line in
    the deck log, which goes where the project's who-answers setting says, as it always has."""
    if ask.get("what") == "permission":
        return {"verb": "refuse", "ask": str(ask.get("id", "")), "why": "outside the berth, and nobody is here to allow it"}
    return {"verb": "refuse", "ask": str(ask.get("id", "")),
            "why": "nobody is here; what a person must decide is a `question` line in the deck log"}
