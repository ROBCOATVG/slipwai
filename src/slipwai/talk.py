"""A conversation with a slice or a captain: its inbox, its thread, and the receipts folded from the two.

Everything said to a slice used to be a `told` line in its stream's deck log, which the captain read at a
boundary and the session was asked, in prose, to look for between stages. Prose that asks for a read is
the instruction that failed four times in MANDA. So a message now goes into the slice's own folder and its
driver — the one thing holding the slice's session — delivers it and writes down that it did.

`talk/<fairway>/<slice>/` under the run folder, `talk/<fairway>/_captain/` for a captain's:

- `inbox/<id>.json`: one file per thing sent, written whole and renamed into place by whoever sends it, so
  a reader never meets half a message. `kind` is `say`, `pause`, `resume`, `stop` or `withdraw` (`of`).
  Once handled it is moved to `inbox/done/`, so what is looked at twice a second is only what is waiting.
- `thread.jsonl`: append-only, and written by one hand, the driver inside the captain's process: a line
  per fact — `seen`, `delivered`, `reply`, `unaddressed`, `failed`, `withdrawn`, `ask`, `answer`, `turn`,
  `paused`, `resumed`, `stopped`, `session`, and `held` (kept back, with why) and `returned` (a delivery
  that never reached a session, queued again). Read by offset: a reader takes only what was appended.
- `session.json`: the session id and harness saved when the driver closed, read when it opens again.

A receipt is never stored: a message in the inbox with no `delivered` is queued, and so on down the thread.

**A person's word is signed.** A message `from: person` can answer a park and can stop or resume a slice,
and a session with a shell can write a file into its own inbox. So `send` signs a person's message with a
key kept at `talk/.key` (mode 0600, written by the first sender) and a reader believes `from: person` only
where the signature holds. That stops a session forging a person by writing a file in the shape this page
describes; it does not stop one that reads the key by its path, which only running sessions as another
user would.

Carried into every project by `scripts/shared-modules.py`, which is why this imports nothing but the
standard library and is handed the run folder rather than finding it: the board reads with it, the captain
writes with it, and a reader and a writer that each kept a copy of the format would stop agreeing.
"""
# budget: 380 — the conversation's whole format in one place, both runtimes' copy: the inbox and its signing,
# the thread read by offset, and the fold into receipts, which a reader and the writer must not disagree on
from __future__ import annotations

import hashlib
import hmac
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
PERSON = "person"
#: What a receipt can say, in the order a message moves through them.
STATES = ("queued", "delivered", "answered", "unaddressed", "not delivered", "withdrawn")
NAME = re.compile(r"[A-Za-z0-9_.-]{1,64}")
KEY = ".key"
DONE = "done"
#: The fields a signature covers: everything that says who, what and how.
SIGNED = ("id", "t", "from", "kind", "text", "mode", "of", "via")
#: One lock for every thread file this process appends to and every cached read of one: a slice's driver and
#: the captain acting for a closed one are two threads of one process, and the rule is one writer.
WRITING = threading.RLock()
READ: dict[Path, tuple[int, list[dict[str, Any]], bytes]] = {}


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


def key(home: Path, make: bool = False) -> bytes:
    """The signing key of every conversation under this run folder, made on first use by a sender."""
    path = Path(home).parent.parent / KEY
    try:
        return path.read_bytes()
    except OSError:
        if not make:
            return b""
    path.parent.mkdir(parents=True, exist_ok=True)
    aside = path.with_name(f"{KEY}.{secrets.token_hex(4)}.part")
    aside.write_bytes(secrets.token_bytes(32))
    os.chmod(aside, 0o600)
    try:
        os.link(aside, path)  # the first to place it wins, and every sender then reads the same key
    except FileExistsError:
        pass
    finally:
        aside.unlink(missing_ok=True)
    return path.read_bytes()


def signature(secret: bytes, message: dict[str, Any]) -> str:
    body = json.dumps({name: message.get(name) for name in SIGNED}, sort_keys=True, ensure_ascii=False)
    return hmac.new(secret, body.encode("utf-8"), hashlib.sha256).hexdigest()


def genuine(home: Path, message: dict[str, Any]) -> bool:
    """Whether the message is who it says: anyone but a person is taken at its word; a person's must carry
    the signature `send` made with this run folder's key."""
    if message.get("from") != PERSON:
        return True
    secret = key(home)
    return bool(secret) and hmac.compare_digest(str(message.get("sig", "")), signature(secret, message))


def send(home: Path, kind: str, text: str = "", mode: str = "wait", by: str = PERSON, of: str = "",
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
    if by == PERSON:
        message["sig"] = signature(key(home, make=True), message)
    box = Path(home) / "inbox"
    box.mkdir(parents=True, exist_ok=True)
    aside = box / f".{message['id']}.json.part"
    aside.write_text(json.dumps(message, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(aside, box / f"{message['id']}.json")
    return message


def read_box(folder: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    """The messages in one folder of the inbox, and the files in it that are not one."""
    found, bad = [], []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            message = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            bad.append(path)
            continue
        if isinstance(message, dict) and message.get("kind") in KINDS and message.get("id") == path.stem:
            found.append(message)
        else:
            bad.append(path)
    return sorted(found, key=lambda one: (str(one.get("t", "")), str(one["id"]))), bad


def pending(home: Path) -> list[dict[str, Any]]:
    """The messages not yet handled, oldest first: what a driver looks at twice a second."""
    return read_box(Path(home) / "inbox")[0]


def malformed(home: Path) -> list[Path]:
    """Files waiting in the inbox that are not a message this reads."""
    return read_box(Path(home) / "inbox")[1]


def inbox(home: Path) -> list[dict[str, Any]]:
    """Every message, handled or not, oldest first: what receipts are read from."""
    waiting, _ = read_box(Path(home) / "inbox")
    handled, _ = read_box(Path(home) / "inbox" / DONE)
    return sorted([*handled, *waiting], key=lambda one: (str(one.get("t", "")), str(one["id"])))


def settle(home: Path, ident: str) -> None:
    """Move a handled message aside, where receipts still read it and the driver's look does not."""
    path = Path(home) / "inbox" / f"{ident}.json"
    if path.is_file():
        (path.parent / DONE).mkdir(exist_ok=True)
        os.replace(path, path.parent / DONE / path.name)


def reject(home: Path, path: Path, why: str = "it is not a message this reads") -> None:
    """A file in the inbox that is not a message: moved aside, with a receipt saying so."""
    (path.parent / DONE).mkdir(exist_ok=True)
    os.replace(path, path.parent / DONE / f"{path.stem}.bad")
    note(home, "failed", id=path.stem, why=why, malformed=True)


def thread(home: Path) -> list[dict[str, Any]]:
    """The thread's lines, oldest first, read from where the last read of it ended; a torn last line is left
    for the next read, never raised."""
    path = Path(home) / "thread.jsonl"
    with WRITING:
        offset, lines, rest = READ.get(path, (0, [], b""))
        try:
            with path.open("rb") as held:
                size = held.seek(0, 2)
                if size < offset:  # cut back or replaced: read it whole again
                    offset, lines, rest = 0, [], b""
                held.seek(offset)
                raw = rest + held.read()
                offset = held.tell()
        except OSError:
            return []
        *whole, rest = raw.split(b"\n")
        lines = list(lines)
        for line in whole:
            try:
                one = json.loads(line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(one, dict) and one.get("kind"):
                lines.append(one)
        READ[path] = (offset, lines, rest)
        return list(lines)


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


def handed(lines: list[dict[str, Any]]) -> set[str]:
    """The messages whose last word is `delivered`: a `returned` after it puts one back in the queue."""
    last: dict[str, str] = {}
    for one in lines:
        if one.get("kind") in ("delivered", "returned"):
            last[str(one.get("id", ""))] = str(one["kind"])
    return {ident for ident, kind in last.items() if kind == "delivered"}


def unseen(home: Path, lines: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Waiting messages the thread has no `seen` for: what the driver has still to read."""
    seen = ids(thread(home) if lines is None else lines, "seen")
    return [one for one in pending(home) if str(one["id"]) not in seen]


def queued(home: Path, lines: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """The messages waiting to be delivered: said, and not delivered, failed or withdrawn — a withdrawal
    still in the inbox counts already, so nothing it names is delivered on the way to reading it — and
    from whom they say, where it is a person."""
    lines = thread(home) if lines is None else lines
    messages = pending(home)
    done = handed(lines) | ids(lines, "failed") | ids(lines, "withdrawn")
    done |= {str(one.get("of", "")) for one in messages if one.get("kind") == "withdraw"}
    return [one for one in messages if one.get("kind") == "say" and str(one["id"]) not in done
            and genuine(home, one)]


def halted(home: Path, lines: list[dict[str, Any]] | None = None) -> tuple[str, str, str]:
    """(`paused` or `stopped` or `''`, by, why): the last word on the thread about holding the slice. A stop
    holds it only where a person made it; any other stop put it back in the queue."""
    last: tuple[str, str, str] = ("", "", "")
    for one in thread(home) if lines is None else lines:
        kind = one.get("kind")
        if kind == "resumed" or (kind == "stopped" and one.get("by") != PERSON):
            last = ("", "", "")
        elif kind in ("paused", "stopped"):
            last = (str(kind), str(one.get("by", "")), str(one.get("why", "")))
    return last


def paused(home: Path, lines: list[dict[str, Any]] | None = None) -> bool:
    """Whether the last word on the thread about holding the slice is `paused`."""
    return halted(home, lines)[0] == "paused"


def receipts(home: Path) -> list[dict[str, Any]]:
    """Every message said into this conversation with where it stands, oldest first: `state` one of
    `STATES`; `delivered` the instant, `reply` the agent's words, `why` where it was not delivered or is
    being held."""
    lines = thread(home)
    messages = inbox(home)
    pending_withdrawals = {str(one.get("of", "")) for one in messages if one.get("kind") == "withdraw"}
    given = handed(lines)
    found = []
    for message in messages:
        if message.get("kind") != "say":
            continue
        ident = str(message["id"])
        mine = [one for one in lines if ident in (str(one.get("id", "")), str(one.get("to", "")))]
        kinds = [one["kind"] for one in mine]
        delivered = next((one for one in reversed(mine) if one["kind"] == "delivered"), None) \
            if ident in given else None
        reply = next((one for one in mine if one["kind"] == "reply"), None)
        failed = next((one for one in mine if one["kind"] == "failed"), None)
        held = next((one for one in reversed(mine) if one["kind"] == "held"), None)
        state, why = "queued", str(held.get("why", "")) if held else ""
        if not genuine(home, message):
            state, why = "not delivered", "it says it is from a person and is not signed by the board"
        elif "withdrawn" in kinds or (ident in pending_withdrawals and delivered is None):
            state = "withdrawn"
        elif failed is not None and reply is None:
            state, why = "not delivered", str(failed.get("why", ""))
        elif reply is not None:
            state = "answered"
        elif "unaddressed" in kinds:
            state = "unaddressed"
        elif delivered is not None:
            state, why = "delivered", ""
        found.append({"id": ident, "t": str(message.get("t", "")), "from": str(message.get("from", "")),
                      "text": str(message.get("text", "")), "mode": str(message.get("mode", "wait")),
                      "state": state, "delivered": str(delivered.get("t", "")) if delivered else "",
                      "reply": str(reply.get("text", "")) if reply else "", "why": why})
    for one in lines:
        if one.get("kind") == "failed" and one.get("malformed"):
            found.append({"id": str(one.get("id", "")), "t": str(one.get("t", "")), "from": "", "text": "",
                          "mode": "wait", "state": "not delivered", "delivered": "", "reply": "",
                          "why": str(one.get("why", ""))})
    return found


def save_session(home: Path, session_id: str, harness: str = "") -> None:
    """The session id the driver closed with, and the harness it ran on, for the next open to load."""
    if not session_id:
        return
    path = Path(home) / "session.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    aside = path.with_name(".session.json.part")
    aside.write_text(json.dumps({"v": V, "id": session_id, "harness": harness, "t": now()}) + "\n", encoding="utf-8")
    os.replace(aside, path)


def forget_session(home: Path) -> None:
    """A stop ends the session for good: the next open starts fresh."""
    (Path(home) / "session.json").unlink(missing_ok=True)


def saved_session(home: Path) -> dict[str, Any]:
    """What `save_session` wrote, or nothing."""
    try:
        held = json.loads((Path(home) / "session.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) and held.get("id") else {}
