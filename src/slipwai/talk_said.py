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
import threading
from pathlib import Path
from typing import Any

from . import talk
from .deck import entries, feature_of, streams
from .logs import run_dir
from .talk_placed import said, slice_named

#: Where the board keeps the little it records about conversations, under the run folder: what a person has
#: seen, and each "Tell every captain".
BOARD = "board"
TOLD_ALL = "told-all.jsonl"
SLICE = re.compile(r"[A-Za-z0-9_.-]{1,40}")
#: One writer at a time for the board's own small records, which two windows can write at once.
WRITING = threading.Lock()
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


def receipt_line(root: Path, fairway: str, slice_id: str, message: dict[str, Any]) -> str:
    """What a route answers: where the message went, where it honestly stands, and the id to follow it by —
    never "told" for something nothing has read yet."""
    line, _ = said(root, fairway, slice_id, str(message["id"]))
    return f"{slice_id or f'the {fairway} captain'}: {line} · message {message['id']}"


def replace(root: Path, fairway: str, slice_id: str, was: str) -> None:
    """Take back an answer not yet read, so the one that follows it stands in its place."""
    if was:
        old = next((one for one in talk.inbox(home(root, fairway, slice_id)) if str(one["id"]) == was), None)
        if old is None or old.get("from") != talk.PERSON:
            raise ValueError(f"{slice_id or fairway} has no answer {was} of yours to change")
        steer(root, fairway, slice_id or talk.CAPTAIN, "withdraw", of=was)


def tell(root: Path, fairway: str, message: str, slice_id: str = "", by: str = "", mode: str = "wait",
         of: str = "", replaces: str = "") -> str:
    """The board's one way to say something to a stream: to the slice named, or to the stream's captain. `of`
    names what it answers (`park:<instant>`), and `replaces` an answer of the person's it takes back."""
    if not fairway or not message.strip():
        raise ValueError("a message needs a stream to go to and something to say")
    known(root, fairway)
    replace(root, fairway, slice_id, replaces)
    sent = say(root, fairway, slice_id, message, mode, by, of)
    return receipt_line(root, fairway, slice_id, sent)


def asked_by(root: Path, fairway: str, question: str) -> str:
    """The slice whose question this is, off the stream's log, or `''` where the question names none."""
    found, _ = entries(root, fairway)
    asked = [e for e in found if e.kind == "question" and str(e.fields.get("id", "")) == question]
    if not asked:
        raise ValueError(f"{fairway} has asked no question {question}")
    return slice_named(str(asked[-1].fields.get("slice") or ""))


def answer(root: Path, fairway: str, question: str, message: str, replaces: str = "") -> str:
    """A person's answer to a question: to the slice that asked it, where the captain carries it to the park
    and records the decision when it carries the slice on; to the captain where no slice asked it. It carries
    `question:<id>`, which is how the question's row shows it was answered."""
    if not fairway or not message.strip():
        raise ValueError("an answer needs a stream to go to and something to say")
    if not SLICE.fullmatch(question):
        raise ValueError(f"{question!r} is not a question's id")
    known(root, fairway)
    named = asked_by(root, fairway, question)
    words = message if named else f"Answer to {question}: {message.strip()}"
    replace(root, fairway, named, replaces)
    sent = say(root, fairway, named, words, by=talk.PERSON, of=f"question:{question}")
    return f"answered {question} · " + receipt_line(root, fairway, named, sent)


def told_all_path(root: Path) -> Path:
    return run_dir(root) / BOARD / TOLD_ALL


def every_stream(root: Path) -> list[str]:
    """Every stream with a log, once each, in name order."""
    return sorted({fairway for _, fairway in streams(root)})


#: How many "Tell every captain" the board keeps: the file is cut back to these on each write.
KEEP_TOLD = 10
#: Bytes a message's own fields take beside its words — id, instant, kind, sender, signature — allowed for when
#: a tell is measured against the one limit, `talk.LARGEST`.
ROOM = 1024


def tell_every_captain(root: Path, message: str) -> dict[str, Any]:
    """One message placed in each captain's inbox, and the board's note of which id went to which."""
    if not message.strip():
        raise ValueError("a message needs something to say")
    # Refused before any captain is told, by the limit `talk.send` holds a message to, with room for the fields
    # beside the words: one refused part way would be a tell some captains had and the board kept no note of.
    size = len(json.dumps(message, ensure_ascii=False).encode("utf-8")) + ROOM
    if size > talk.LARGEST:
        raise ValueError(f"this message is {size:,} bytes, and a message may be {talk.LARGEST:,}: say it shorter, "
                         f"or put what is long in a file and say where it is")
    every = every_stream(root)
    if not every:
        raise ValueError("no stream has a log here yet, so there is no captain to tell")
    ids = {fairway: talk.send(home(root, fairway), "say", message, by=talk.PERSON)["id"] for fairway in every}
    record = {"t": talk.now(), "text": message.strip(), "ids": ids}
    path = told_all_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with WRITING:
        kept = [json.dumps(one, ensure_ascii=False) for one in reversed(told_all(root, KEEP_TOLD - 1))]
        aside = path.with_name(f".{TOLD_ALL}.part")
        aside.write_text("".join(f"{one}\n" for one in [*kept, json.dumps(record, ensure_ascii=False)]),
                         encoding="utf-8")
        os.replace(aside, path)
    return record


def told_all(root: Path, keep: int = 3) -> list[dict[str, Any]]:
    """The last few "Tell every captain", newest first, read from the file's tail in whole lines; a line that
    is not one is passed over. The tail is as long as the records kept can be, each a message of at most
    `talk.LARGEST` and its ids: read shorter, a long tell was a half line, passed over — and dropped from the
    file by the next tell, which keeps what this returns."""
    window = KEEP_TOLD * 2 * talk.LARGEST
    got = talk.read_bytes(told_all_path(root), window, -window)
    if got is None:
        return []
    held, size = got
    if size > len(held):
        held = held.split(b"\n", 1)[1] if b"\n" in held else b""  # the cut fell inside a line: never half of one
    lines = held.decode("utf-8", errors="replace").splitlines()
    found = []
    for line in lines:
        try:
            one = json.loads(line)
        except ValueError:
            continue
        if isinstance(one, dict) and isinstance(one.get("ids"), dict):
            found.append(one)
    return list(reversed(found[-keep:]))
