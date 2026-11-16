"""What the board says to the fleet: every word placed in an inbox, signed, and never a deck line.

The board wrote a `told` into a stream's deck log for everything a person said — an answer on a red card,
a box under a stream, the MCP tool, confirmed feedback — and the captain read it at its next boundary, and a
session was asked in prose to look for it. Now each is a message in a conversation's inbox (`talk.py`), which
the slice's driver delivers and receipts, or the stream's captain reads and routes:

- one naming a slice goes to that slice;
- one naming only a stream goes to its captain (`_captain`), which works out which slices it is for;
- an answer to a question goes to the slice that asked it, where the captain turns a person's message to a
  parked slice into the `told` that clears the park (`captain.heard_closed`), and to the captain where the
  question names no slice;
- confirmed feedback goes from `feedback`, which answers no park.

Every one returns the message, so a caller can follow its receipt by its id. What the board still writes to
a deck log is a receipt, not something said: `deck.mark_read` and `deck.dismiss` (the `read` the decision
ceiling and the waiting list count) and `deck.tick_need` (a need a person ticked, which the harbourmaster
turns into its own receipt).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from . import talk
from .deck import entries, feature_of, streams
from .logs import run_dir

#: Where the board keeps the little it records about conversations, under the run folder: what a person has
#: seen, and each "Tell every captain".
BOARD = "board"
TOLD_ALL = "told-all.jsonl"
SLICE = re.compile(r"[A-Za-z0-9_.-]{1,40}")
STEERS = ("pause", "resume", "stop", "withdraw")


def teller() -> str:
    """Whose a message is: `person`, or `session` under a session the captain dispatched — which starts
    with `SLIPWAI_FAIRWAY` set, so the MCP server it reaches says so: a session's word answers no park."""
    return "session" if os.environ.get("SLIPWAI_FAIRWAY") else talk.PERSON


def home(root: Path, fairway: str, slice_id: str = "") -> Path:
    """A slice's conversation, or its stream's captain's; `ValueError` for a name that would leave the folder."""
    if slice_id and not SLICE.fullmatch(slice_id):
        raise ValueError(f"{slice_id!r} is not a slice id")
    return talk.place(run_dir(root), fairway, slice_id or talk.CAPTAIN)


def known(root: Path, fairway: str) -> None:
    """Refuse a stream this project has no log for: a message to a misspelt one is a message nobody reads."""
    if not fairway or not feature_of(root, fairway):
        raise ValueError(f"{fairway or 'that'} has no log here, so there is nowhere for this to go. A stream "
                         f"gets a log when its captain writes its first line")


def say(root: Path, fairway: str, slice_id: str, text: str, mode: str = "wait", by: str = "",
        of: str = "") -> dict[str, Any]:
    """One message, into a slice's inbox or its captain's."""
    known(root, fairway)
    if not text.strip():
        raise ValueError("a message needs something to say")
    return talk.send(home(root, fairway, slice_id), "say", text, mode, by or teller(), of=of)


def steer(root: Path, fairway: str, slice_id: str, kind: str, why: str = "", of: str = "") -> dict[str, Any]:
    """Pause, resume or stop a slice, or withdraw a message not yet delivered: a person's, and signed."""
    if kind not in STEERS:
        raise ValueError(f"{kind!r} is not something a person does to a slice: {', '.join(STEERS)}")
    if not slice_id:
        raise ValueError("pause, resume, stop and withdraw name the slice they are for")
    known(root, fairway)
    return talk.send(home(root, fairway, slice_id), kind, why, by=talk.PERSON, of=of)


def receipt_line(message: dict[str, Any], to: str) -> str:
    """What a route answers: who it went to, and the id its receipt is followed by."""
    return f"told {to} · message {message['id']}"


def tell(root: Path, fairway: str, message: str, slice_id: str = "", by: str = "", mode: str = "wait") -> str:
    """The board's one way to say something to a stream: to the slice named, or to the stream's captain."""
    if not fairway or not message.strip():
        raise ValueError("a message needs a stream to go to and something to say")
    sent = say(root, fairway, slice_id, message, mode, by)
    return receipt_line(sent, slice_id or f"the {fairway} captain")


def asked_by(root: Path, fairway: str, question: str) -> str:
    """The slice whose question this is, off the stream's log, or `''` where the question names none."""
    found, _ = entries(root, fairway)
    asked = [e for e in found if e.kind == "question" and str(e.fields.get("id", "")) == question]
    if not asked:
        raise ValueError(f"{fairway} has asked no question {question}")
    return str(asked[-1].fields.get("slice") or "")


def answer(root: Path, fairway: str, question: str, message: str) -> str:
    """A person's answer to a question: to the slice that asked it, where the captain carries it to the park
    and records the decision when it carries the slice on; to the captain where no slice asked it."""
    if not fairway or not message.strip():
        raise ValueError("an answer needs a stream to go to and something to say")
    if not SLICE.fullmatch(question):
        raise ValueError(f"{question!r} is not a question's id")
    known(root, fairway)
    named = asked_by(root, fairway, question)
    if named and not SLICE.fullmatch(named):
        named = ""  # a question asked of the chart or the stream as a whole goes to its captain
    words = message if named else f"Answer to {question}: {message.strip()}"
    sent = say(root, fairway, named, words, by=talk.PERSON)
    return f"answered {question} · message {sent['id']}"


def told_all_path(root: Path) -> Path:
    return run_dir(root) / BOARD / TOLD_ALL


def every_stream(root: Path) -> list[str]:
    """Every stream with a log, once each, in name order."""
    return sorted({fairway for _, fairway in streams(root)})


def tell_every_captain(root: Path, message: str) -> dict[str, Any]:
    """One message placed in each captain's inbox, and the board's note of which id went to which."""
    if not message.strip():
        raise ValueError("a message needs something to say")
    every = every_stream(root)
    if not every:
        raise ValueError("no stream has a log here yet, so there is no captain to tell")
    ids = {fairway: talk.send(home(root, fairway), "say", message, by=talk.PERSON)["id"] for fairway in every}
    record = {"t": talk.now(), "text": message.strip(), "ids": ids}
    path = told_all_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as out:
        out.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def told_all(root: Path, keep: int = 3) -> list[dict[str, Any]]:
    """The last few "Tell every captain", newest first; a line that is not one is passed over."""
    try:
        lines = told_all_path(root).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    found = []
    for line in lines:
        try:
            one = json.loads(line)
        except ValueError:
            continue
        if isinstance(one, dict) and isinstance(one.get("ids"), dict):
            found.append(one)
    return list(reversed(found[-keep:]))
