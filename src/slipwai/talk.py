"""A conversation with a slice or a captain: its inbox, its thread, and the receipts folded from the two.

Everything said to a slice used to be a `told` line in its stream's deck log, which the captain read at a
boundary and the session was asked, in prose, to look for between stages. Prose that asks for a read is
the instruction that failed four times in MANDA. So a message now goes into the slice's own folder and its
driver — the one thing holding the slice's session — delivers it and writes down that it did.

`talk/<fairway>/<slice>/` under the run folder, `talk/<fairway>/_captain/` for a captain's:

- `inbox/<id>.json`: one file per thing sent, written whole and renamed into place by whoever sends it, so
  a reader never meets half a message. `kind` is `say`, `pause`, `resume`, `stop` or `withdraw` (`of`).
- `thread.jsonl`: append-only, and written by one hand, the driver inside the captain's process: a line
  per fact — `seen`, `delivered`, `reply`, `unaddressed`, `failed`, `withdrawn`, `ask`, `answer`, `turn`,
  `paused`, `resumed`, `stopped`, `session`.
- `session.json`: the session id saved when the driver closed, read when it opens again.

A receipt is never stored: a message in the inbox with no `delivered` is queued, and so on down the thread.

Carried into every project by `scripts/shared-modules.py`, which is why this imports nothing but the
standard library and is handed the run folder rather than finding it: the board reads with it, the captain
writes with it, and a reader and a writer that each kept a copy of the format would stop agreeing.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

V = 1
TALK = "talk"
CAPTAIN = "_captain"
KINDS = ("say", "pause", "resume", "stop", "withdraw")
#: Kinds that steer the driver rather than say something to the agent: each is read once and acted on.
CONTROLS = ("pause", "resume", "stop", "withdraw")
MODES = ("wait", "interrupt")
#: What a receipt can say, in the order a message moves through them.
STATES = ("queued", "delivered", "answered", "unaddressed", "not delivered", "withdrawn")
NAME = re.compile(r"[A-Za-z0-9_.-]{1,64}")
#: One lock for every thread file this process appends to: a slice's driver and the captain acting for a
#: closed one are two threads of one process, and the rule is one writer.
WRITING = threading.Lock()


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def place(run: Path, fairway: str, slice_id: str = CAPTAIN) -> Path:
    """A slice's conversation folder, or a captain's; `ValueError` for a name that would leave the folder."""
    for name in (fairway, slice_id):
        if not NAME.fullmatch(name or "") or name in (".", ".."):
            raise ValueError(f"{name!r} is not a stream or slice name")
    return Path(run) / TALK / fairway / slice_id


def conversations(run: Path, fairway: str) -> list[str]:
    """The slices of one stream that have a conversation folder, the captain's last."""
    home = Path(run) / TALK / fairway
    found = sorted(path.name for path in home.iterdir() if path.is_dir()) if home.is_dir() else []
    return [one for one in found if one != CAPTAIN] + [one for one in found if one == CAPTAIN]


def send(home: Path, kind: str, text: str = "", mode: str = "wait", by: str = "person", of: str = "",
         via: str = "") -> dict[str, Any]:
    """Drop one thing into a conversation's inbox, whole: written aside and renamed into place."""
    if kind not in KINDS:
        raise ValueError(f"{kind!r} is not something a conversation takes: {', '.join(KINDS)}")
    if mode not in MODES:
        raise ValueError(f"{mode!r} is not a way to deliver: {', '.join(MODES)}")
    if kind == "say" and not text.strip():
        raise ValueError("a message needs something to say")
    if kind == "withdraw" and not of:
        raise ValueError("a withdrawal names the message it takes back")
    t = now()
    message: dict[str, Any] = {"v": V, "id": f"{t.replace('-', '').replace(':', '')}-{secrets.token_hex(3)}",
                               "t": t, "from": by, "kind": kind, "text": text.strip(), "mode": mode}
    if of:
        message["of"] = of
    if via:
        message["via"] = via
    box = Path(home) / "inbox"
    box.mkdir(parents=True, exist_ok=True)
    aside = box / f".{message['id']}.json.part"
    aside.write_text(json.dumps(message, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(aside, box / f"{message['id']}.json")
    return message


def inbox(home: Path) -> list[dict[str, Any]]:
    """Every message in the inbox, oldest first. A file being written, or one that is not a message, is
    passed over: the sender renames it into place whole, so it is read on the next look."""
    box = Path(home) / "inbox"
    found = []
    for path in sorted(box.glob("*.json")) if box.is_dir() else []:
        try:
            message = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        if isinstance(message, dict) and message.get("kind") in KINDS and message.get("id"):
            found.append(message)
    return sorted(found, key=lambda one: (str(one.get("t", "")), str(one["id"])))


def thread(home: Path) -> list[dict[str, Any]]:
    """The thread's lines, oldest first; a torn last line is skipped, never raised."""
    path = Path(home) / "thread.jsonl"
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    found = []
    for line in raw.splitlines():
        try:
            one = json.loads(line)
        except ValueError:
            continue
        if isinstance(one, dict) and one.get("kind"):
            found.append(one)
    return found


def note(home: Path, kind: str, **fields: Any) -> dict[str, Any]:
    """One fact on the thread. Only the driver, and the captain for a driver that is closed, call this."""
    line = {"v": V, "t": now(), "kind": kind, **{k: v for k, v in fields.items() if v is not None}}
    path = Path(home) / "thread.jsonl"
    with WRITING:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line


def ids(lines: list[dict[str, Any]], kind: str, field: str = "id") -> set[str]:
    return {str(one.get(field, "")) for one in lines if one.get("kind") == kind}


def unseen(home: Path, lines: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Inbox messages the thread has no `seen` for: what the driver has still to read."""
    seen = ids(thread(home) if lines is None else lines, "seen")
    return [one for one in inbox(home) if str(one["id"]) not in seen]


def queued(home: Path, lines: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """The messages waiting to be delivered: said, and not yet delivered, failed or withdrawn — a withdrawal
    still in the inbox counts already, so nothing it names is delivered on the way to reading it."""
    lines = thread(home) if lines is None else lines
    messages = inbox(home)
    done = ids(lines, "delivered") | ids(lines, "failed") | ids(lines, "withdrawn")
    done |= {str(one.get("of", "")) for one in messages if one.get("kind") == "withdraw"}
    return [one for one in messages if one.get("kind") == "say" and str(one["id"]) not in done]


def paused(home: Path, lines: list[dict[str, Any]] | None = None) -> bool:
    """Whether the last word on the thread about pausing is `paused`."""
    lines = thread(home) if lines is None else lines
    said = [one["kind"] for one in lines if one.get("kind") in ("paused", "resumed")]
    return bool(said) and said[-1] == "paused"


def receipts(home: Path) -> list[dict[str, Any]]:
    """Every message said into this conversation with where it stands, oldest first: `state` one of
    `STATES`; `delivered` the instant, `reply` the agent's words, `why` where it was not delivered."""
    lines = thread(home)
    messages = inbox(home)
    pending = {str(one.get("of", "")) for one in messages if one.get("kind") == "withdraw"}
    found = []
    for message in messages:
        if message.get("kind") != "say":
            continue
        ident = str(message["id"])
        mine = [one for one in lines if ident in (str(one.get("id", "")), str(one.get("to", "")))]
        kinds = [one["kind"] for one in mine]
        delivered = next((one for one in mine if one["kind"] == "delivered"), None)
        reply = next((one for one in mine if one["kind"] == "reply"), None)
        failed = next((one for one in mine if one["kind"] == "failed"), None)
        state = "queued"
        if "withdrawn" in kinds or (ident in pending and delivered is None):
            state = "withdrawn"
        elif failed is not None and reply is None:
            state = "not delivered"
        elif reply is not None:
            state = "answered"
        elif "unaddressed" in kinds:
            state = "unaddressed"
        elif delivered is not None:
            state = "delivered"
        found.append({"id": ident, "t": str(message.get("t", "")), "from": str(message.get("from", "")),
                      "text": str(message.get("text", "")), "mode": str(message.get("mode", "wait")),
                      "state": state, "delivered": str(delivered.get("t", "")) if delivered else "",
                      "reply": str(reply.get("text", "")) if reply else "",
                      "why": str(failed.get("why", "")) if failed else ""})
    return found


def save_session(home: Path, session_id: str, harness: str = "") -> None:
    """The session id the driver closed with, for the next open to load."""
    if not session_id:
        return
    path = Path(home) / "session.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    aside = path.with_name(".session.json.part")
    aside.write_text(json.dumps({"v": V, "id": session_id, "harness": harness, "t": now()}) + "\n", encoding="utf-8")
    os.replace(aside, path)


def saved_session(home: Path) -> dict[str, Any]:
    """What `save_session` wrote, or nothing."""
    try:
        held = json.loads((Path(home) / "session.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) and held.get("id") else {}
