"""Where a person's message went, and what will honestly become of it: aimed at its slice, said as it stands.

A park's row, a question's row and a group's button each answer something, and the answer used to be a deck
line that answered at once. Now it is a message in an inbox, read when a captain or a driver next looks — so
two things follow. **It is aimed at what it is about**: a park whose `slice` field is empty still names its
slice at the head of its `why` (`ORD-01: awaiting Q1`), and the row was drawn for that slice, so it goes to
that slice; only what is about the whole stream goes to its captain. And **it says where it stands**, on the
row it was sent from: sent and waiting for the captain's next turn, sent while the fleet is not running at
all, read by the captain, delivered — never "told" for something nothing has read yet. A row with an answer
placed shows that answer instead of a second box, with "change my answer", which withdraws it and places
another.

Each answer carries the thing it answers in its `of` — `park:<instant>`, `question:<id>` — which is how a row
finds its own among the inbox's messages.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import talk
from .logs import run_dir
from .process_alive import alive

SLICE = re.compile(r"([A-Za-z0-9_.-]{1,40}): ")
#: What a slice's id may be: the conversation folder it names (`talk_said.SLICE`).
SLICE_ID = re.compile(r"[A-Za-z0-9_.-]{1,40}")


def slice_named(named: str) -> str:
    """A `slice` field as a slice's id, or `''` where it holds anything else (`"the chart"`): what is about no
    slice goes to the stream's captain, which a field no conversation could be named by would otherwise refuse."""
    return named if SLICE_ID.fullmatch(named) else ""


def running(root: Path) -> bool:
    """Whether anything the fleet started is alive: its pid files, each checked against the process table."""
    folder = run_dir(root) / "running"
    for path in sorted(folder.glob("*.pid")) if folder.is_dir() else []:
        try:
            if alive(int(path.read_text(encoding="utf-8").strip())):
                return True
        except (OSError, ValueError):
            continue
    return False


def aim_of(row: dict[str, Any]) -> str:
    """The slice a row is about: its own field, or the name a park's `why` starts with; `''` for the stream."""
    named = slice_named(str(row.get("slice") or ""))
    if named:
        return named
    found = SLICE.match(str(row.get("what") or row.get("why") or ""))
    return found.group(1) if found else ""


def key_of(row: dict[str, Any]) -> str:
    """What an answer to this row carries in its `of`: the park's instant, or the question's id."""
    if row.get("kind") == "parked" or (row.get("kind") == "told" and row.get("needs")):
        return f"park:{row.get('t', '')}"
    if row.get("kind") == "question" and row.get("id"):
        return f"question:{row['id']}"
    return ""


def standing(receipt: dict[str, Any], lines: list[dict[str, Any]], live: bool, slice_id: str) -> tuple[str, str]:
    """Where a person's message stands, honestly, and its tone: what has read it, or what will."""
    state = receipt["state"]
    if state in ("answered", "delivered", "unaddressed"):
        return "delivered", "good"
    if state == "not delivered":
        return f"not delivered: {receipt['why']}" if receipt["why"] else "not delivered", "bad"
    if state == "withdrawn":
        return "withdrawn", "quiet"
    if any(one.get("kind") == "seen" and str(one.get("id")) == receipt["id"] for one in lines):
        return ("read by the captain · delivered when the slice carries on" if slice_id
                else "read by the captain"), "wait"
    if not live:
        return "sent · the fleet is not running: read when it is cast off", "wait"
    return "sent · the captain reads it at its next turn", "wait"


def receipt_of(home: Path, ident: str) -> dict[str, Any] | None:
    return next((one for one in talk.receipts(home) if one["id"] == ident), None)


def said(root: Path, fairway: str, slice_id: str, ident: str, live: bool | None = None) -> tuple[str, str]:
    """One message's standing, read now: what a route answers with."""
    home = talk.place(run_dir(root), fairway, slice_id or talk.CAPTAIN)
    receipt = receipt_of(home, ident)
    if receipt is None:
        return "not found in its inbox", "bad"
    return standing(receipt, talk.thread(home), running(root) if live is None else live, slice_id)


def answer_to(root: Path, fairway: str, slice_id: str, key: str, live: bool) -> dict[str, Any] | None:
    """The answer a person placed for one park or question, if one is still standing: the newest not taken
    back, with its words, when it was sent, where it stands, and whether it can still be changed."""
    try:
        home = talk.place(run_dir(root), fairway, slice_id or talk.CAPTAIN)
    except ValueError:
        return None
    mine = [one for one in talk.inbox(home) if one.get("kind") == "say" and one.get("of") == key
            and one.get("from") == talk.PERSON]
    if not mine:
        return None
    lines = talk.thread(home)
    for message in reversed(mine):
        receipt = receipt_of(home, str(message["id"]))
        if receipt is None or receipt["state"] == "withdrawn":
            continue
        line, tone = standing(receipt, lines, live, slice_id)
        return {"id": str(message["id"]), "text": str(message.get("text", "")), "t": str(message.get("t", "")),
                "line": line, "tone": tone, "slice": slice_id,
                "changeable": receipt["state"] == "queued" and not line.startswith("read")}
    return None


def placed(root: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The waiting rows, each with the slice it is aimed at and the answer a person placed for it."""
    live = running(root)
    found = []
    for row in rows:
        key = key_of(row)
        if not key:
            found.append(row)
            continue
        aim = aim_of(row)
        given = answer_to(root, str(row.get("fairway", "")), aim, key, live)
        found.append({**row, "aim": aim, "key": key, **({"answer": given} if given else {})})
    return found
