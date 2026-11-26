"""Who acts on each need the board lists, asked the mender's own way (`need_owner`), with what it has tried.

manda's board offered *Have the mender try again* on every hand-back, the five the mender would never take
among them, and drew every one under *Waiting on you*. A need is the mender's, a slice merge's, a decision's
or a person's, and only the last two wait on anybody: so each unmet need gets `who` and, where it is not the
mender, `whose` — the sentence saying why it is that one's — and the mender's last failure as `tried`. A
need the mender would take whose attempts are spent is `spent`, which is the one place *Have the mender try
again* means anything. A row whose unmet needs are all the fleet's own is `acts: fleet`, and is not a wait.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from .logs import Entry, asks_a_decision, unmerged
from .need_check import trunk_commit
from .need_owner import DEFAULT_ATTEMPTS, MENDER, MERGE, SPENT, allowed, cruising, spent, tally, touched, whose


class Stream(Protocol):
    name: str
    entries: list[Entry]

    @property
    def merged(self) -> list[str]: ...


#: Who acts, where it is the fleet's own work: the board draws these apart and counts none as a wait.
FLEET = (MENDER, MERGE)


def landed(found: Sequence[Stream], harbour: list[Entry]) -> frozenset[str]:
    """Every slice that has merged: a stream's `merged` lines, and the harbour's `granted` with a commit."""
    merged = {name for one in found for name in one.merged}
    merged |= {str(e.fields.get("slice", "")) for e in harbour if e.kind == "granted" and e.fields.get("commit")}
    return frozenset(merged - {""})


def who_acts(root: Path | None, found: Sequence[Stream], rows: list[dict[str, Any]], harbour: list[Entry],
             trunk: object = None) -> list[dict[str, Any]]:
    """The rows, each unmet need marked with who acts and why, and each row with needs `acts`: `fleet` where
    nothing in it waits on a person, `you` where something does."""
    if not any(row.get("needs") for row in rows):
        return rows
    merged = landed(found, harbour)
    flying = [name for one in found for name in unmerged(one.entries) if name not in merged]
    busy = touched(root, trunk_commit(root, trunk), flying) if root is not None else None
    done = tally(harbour)
    limit, cruise = (allowed(root), cruising(root)) if root is not None else (DEFAULT_ATTEMPTS, False)
    for row in rows:
        unmet = [need for need in row.get("needs") or [] if need.get("met") != "yes"]
        for need in unmet:
            raw = {"what": need.get("what", ""), "by": need.get("by", "person"), "plain": need.get("plain", ""),
                   "check": need.get("check"), **({"decide": True} if need.get("decide") else {})}
            who, why = whose(raw, asks_a_decision(raw), cruise, busy, merged)
            mine = done.get((str(row.get("fairway", "")), str(row.get("t", "")), int(need.get("index", -1))))
            if who == MENDER and spent(mine, limit):
                who = SPENT
                why = ("The mender tried and could not land it" + (f": {mine['why']}" if mine and mine.get("why")
                                                                     else "."))
            need.update(who=who, whose=why)
            if mine and mine.get("why"):
                need["tried"] = str(mine["why"])
        if unmet:
            row["acts"] = "fleet" if all(need["who"] in FLEET for need in unmet) else "you"
    return rows
