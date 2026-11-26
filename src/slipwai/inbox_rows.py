"""Which rows of the fleet's inbox are a wait on a person, and which are only left to be read.

Split from `fleet.py` at its budget. The board's page has never counted a note as a wait; the terminal and
the agent's inbox did, and these two functions are the one answer all three now give.
"""
from __future__ import annotations


def holds_up(row: dict) -> bool:
    """Whether this inbox row is a wait on a person, rather than something left for them to read.

    A note a slice left (`told` with nothing it needs on trunk) and decisions under the ceiling hold nothing
    up, and the board's page has never counted them. The terminal and the agent's inbox did: lean-coffee-club
    said *12 things waiting on you* over nine notes, two merges waiting on trunk and one question.
    """
    if row.get("paused") == "yes" or row.get("probably") == "yes" or row.get("obsolete"):
        return False  # paused, a merged slice's hand-back to confirm, or a park an earlier slipwai wrote
    if row.get("acts") == "fleet":
        return False  # the mender lands it, or it lands with its slice's merge: nobody waits on a person (#172)
    if row.get("kind") == "told":
        return bool(row.get("needs"))
    if row.get("kind") == "decisions":
        return row.get("blocking") == "yes"
    return True


def inbox_split(waiting: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """The inbox as (waiting on a person, paused and lifting by itself, left to read)."""
    on_you = [row for row in waiting if holds_up(row)]
    resting = [row for row in waiting if row.get("paused") == "yes"]
    notes = [row for row in waiting if not holds_up(row) and row.get("paused") != "yes"]
    return on_you, resting, notes
