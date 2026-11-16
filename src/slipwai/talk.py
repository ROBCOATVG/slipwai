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

**Every message is signed, for the place it is in.** A message `from: person` can answer a park and stop
or resume a slice, and a session with a shell can write a file into its own inbox claiming to be anyone. So
`send` — the only writer, used by the board and by the fleet's own programs — signs every message with a
key kept at `talk/.key`, over who, what, how, its id and the stream and slice it is for, and a reader
refuses any file whose signature does not hold or whose id was handled already. The key is made with mode
0600 when the fleet starts or the board first writes, whichever is first; a key file that is anything else
(another mode, another owner, a link, too short) is said to be wrong and not used. That stops a session
forging a message by writing a file in the shape this page describes, and copying a signed one to another
slice or back out of `done/`; it does not stop one that reads the key by its path, which only running
sessions as another user would.

Carried into every project by `scripts/shared-modules.py`, which is why this imports nothing but the
standard library and is handed the run folder rather than finding it: the board reads with it, the captain
writes with it, and a reader and a writer that each kept a copy of the format would stop agreeing.
"""
# budget: 470 — the conversation's whole format in one place, both runtimes' copy: the inbox and its signing,
# the key and what makes one trustworthy, the thread read by offset, and the fold into receipts for every kind,
# which a reader and the writer must not disagree on
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import stat
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
STATES = ("queued", "delivered", "answered", "unaddressed", "not delivered", "withdrawn", "done")
NAME = re.compile(r"[A-Za-z0-9_.-]{1,64}")
KEY = ".key"
DONE = "done"
#: The fields a signature covers: everything that says who, what and how, and — beside them — where it is for.
SIGNED = ("id", "t", "from", "kind", "text", "mode", "of", "via")
#: The shortest key believed: a file emptied or cut short makes every message unsigned, so it is made again.
KEY_BYTES = 32
UNSIGNED = "it is not signed by the board or the fleet for this slice"
#: Why a message signed before the key was made again cannot be delivered, said with its text kept.
REKEYED = "the board's key changed before this was delivered: send it again"
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


def key_path(home: Path) -> Path:
    return Path(home).parent.parent / KEY


def key_trouble(path: Path) -> str:
    """Why the key file at `path` is not one this believes, or `''`: a link, not a plain file, readable or
    writable by anyone else, another user's. `missing` and `short` are the two a writer mends by making one."""
    try:
        held = path.lstat()
    except OSError:
        return "missing"
    if stat.S_ISLNK(held.st_mode) or not stat.S_ISREG(held.st_mode):
        return f"{path} is not a plain file"
    # Windows (this runs there under Git Bash) has no such modes: `st_mode` always reads as open to everybody,
    # so the check would refuse every key it ever made. There a key is held by where it is — the user's own
    # profile — and the mode says nothing either way, so it is not asked.
    if os.name != "nt" and held.st_mode & 0o077:
        return f"{path} can be read by others (mode {stat.S_IMODE(held.st_mode):o}), so the board did not write it"
    if hasattr(os, "getuid") and held.st_uid != os.getuid():
        return f"{path} belongs to another user"
    return "short" if held.st_size < KEY_BYTES else ""


def ready(run: Path) -> str:
    """Make this run folder's key where there is none, or one emptied or cut short, with mode 0600 from the
    first byte. `''` once there is a key to believe; otherwise what is wrong with the one that is there,
    said so it can be removed — never used."""
    path = Path(run) / TALK / KEY
    trouble = key_trouble(path)
    if trouble not in ("missing", "short"):
        return trouble
    path.parent.mkdir(parents=True, exist_ok=True)
    aside = path.with_name(f"{KEY}.{secrets.token_hex(4)}.part")
    handle = os.open(aside, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(handle, secrets.token_bytes(KEY_BYTES))
    finally:
        os.close(handle)
    try:
        if trouble == "short":
            os.replace(aside, path)
        else:
            os.link(aside, path)  # the first to place it wins, and every sender then reads the same key
    except FileExistsError:
        pass
    except OSError as fault:
        # A file system that takes no hard link, or a folder gone read-only: said, and the run goes on without
        # messages rather than not at all.
        return f"the conversation key could not be placed at {path} ({fault})"
    finally:
        aside.unlink(missing_ok=True)
    return key_trouble(path)


def key(home: Path, make: bool = False) -> bytes:
    """The signing key of every conversation under this run folder, or nothing where there is none to
    believe. A sender makes one where there is none (`make`); `ValueError` saying what to do where the one
    there cannot be used."""
    path = key_path(home)
    if make:
        trouble = ready(path.parent.parent)
        if trouble:
            raise ValueError(f"the conversation key is not one to sign with — {trouble}. Remove {path} and "
                             f"send again: the next message makes a new one")
    if key_trouble(path):
        return b""
    try:
        return path.read_bytes()
    except OSError as fault:
        if make:
            raise ValueError(f"the conversation key at {path} cannot be read ({fault}); check its owner, or "
                             f"remove it and send again") from fault
        return b""


def signature(secret: bytes, message: dict[str, Any], home: Path) -> str:
    body = json.dumps({**{name: message.get(name) for name in SIGNED},
                       "for": [Path(home).parent.name, Path(home).name]}, sort_keys=True, ensure_ascii=False)
    return hmac.new(secret, body.encode("utf-8"), hashlib.sha256).hexdigest()


def genuine(home: Path, message: dict[str, Any]) -> bool:
    """Whether the message carries the signature `send` made with this run folder's key, for this stream and
    slice. Nobody is taken at their word: a file any session could write is not a message."""
    secret = key(home)
    return bool(secret) and hmac.compare_digest(str(message.get("sig", "")), signature(secret, message, home))


def send(home: Path, kind: str, text: str = "", mode: str = "wait", by: str = PERSON, of: str = "",
         via: str = "") -> dict[str, Any]:
    """Drop one thing into a conversation's inbox, signed and whole: written aside and renamed into place.
    `ValueError` with what to do where it cannot be."""
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
    message["sig"] = signature(key(home, make=True), message, home)
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


def handled(home: Path) -> set[str]:
    """The ids already moved aside: a file of one of these back in the inbox is a replay."""
    folder = Path(home) / "inbox" / DONE
    return {path.stem for path in folder.glob("*.json")} if folder.is_dir() else set()


def pending(home: Path) -> list[dict[str, Any]]:
    """The messages not yet handled, oldest first, signed for this slice: what a driver looks at twice a
    second. A file that is not one of these waits for `refused` to answer it."""
    done = handled(home)
    return [one for one in read_box(Path(home) / "inbox")[0] if str(one["id"]) not in done and genuine(home, one)]


def refused(home: Path) -> list[tuple[Path, str]]:
    """Files waiting in the inbox that will never be delivered, each with why: not a message this reads,
    not signed for this slice, or one already handled."""
    box = Path(home) / "inbox"
    found, bad = read_box(box)
    done = handled(home)
    out = [(path, "it is not a message this reads") for path in bad]
    for message in found:
        path = box / f"{message['id']}.json"
        if str(message["id"]) in done:
            out.append((path, "it was handled already"))
        elif not genuine(home, message):
            out.append((path, REKEYED if rekeyed(home, message) else UNSIGNED))
    return out


def rekeyed(home: Path, message: dict[str, Any]) -> bool:
    """Whether a signed message failed only because the key was made again after it was sent: it carries a
    signature and is older than the key. A signed message copied in from elsewhere is newer, and stays a
    forgery."""
    try:
        made = datetime.fromtimestamp(key_path(home).stat().st_mtime, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return False
    return bool(message.get("sig")) and str(message.get("t", "")) < made


def malformed(home: Path) -> list[Path]:
    """Files waiting in the inbox that are not a message this reads."""
    return read_box(Path(home) / "inbox")[1]


def inbox(home: Path) -> list[dict[str, Any]]:
    """Every message, handled or not, oldest first: what receipts are read from."""
    waiting, _ = read_box(Path(home) / "inbox")
    moved, _ = read_box(Path(home) / "inbox" / DONE)
    every = {str(one["id"]): one for one in [*waiting, *moved]}  # a replay of a handled one is that one
    return sorted(every.values(), key=lambda one: (str(one.get("t", "")), str(one["id"])))


def settle(home: Path, ident: str) -> None:
    """Move a handled message aside, where receipts still read it and the driver's look does not."""
    path = Path(home) / "inbox" / f"{ident}.json"
    if path.is_file():
        (path.parent / DONE).mkdir(exist_ok=True)
        os.replace(path, path.parent / DONE / path.name)


def reject(home: Path, path: Path, why: str = "it is not a message this reads") -> None:
    """A file in the inbox that will not be delivered: moved aside, with a receipt saying so — and what it
    said, where it said anything, so a message refused for a remade key can be sent again as it was."""
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        held = None
    text = str(held.get("text") or "") if isinstance(held, dict) else ""
    (path.parent / DONE).mkdir(exist_ok=True)
    os.replace(path, path.parent / DONE / f"{path.stem}.{secrets.token_hex(2)}.bad")
    note(home, "failed", id=path.stem, why=why, refused=True, text=text or None)


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
        kind, by = one.get("kind"), str(one.get("by", ""))
        # A hold a person placed stands until a person lifts it, whatever anyone else says meanwhile: a
        # captain's stop or pause on top of it is not a second hold, and its stop does not hand the slice
        # back to the queue. A merge ends it as well, since a merged slice is held by nothing.
        person_holds = last[1] == PERSON
        if kind == "resumed":
            if not person_holds or by in (PERSON, "merge"):
                last = ("", "", "")
        elif kind in ("paused", "stopped") and person_holds and by != PERSON:
            continue
        elif kind == "stopped" and by != PERSON:
            last = ("", "", "")
        elif kind in ("paused", "stopped"):
            last = (str(kind), by, str(one.get("why", "")))
    return last


def paused(home: Path, lines: list[dict[str, Any]] | None = None) -> bool:
    """Whether the last word on the thread about holding the slice is `paused`."""
    return halted(home, lines)[0] == "paused"


def waiting_why(lines: list[dict[str, Any]]) -> str:
    """Why a queued message waits beyond the turn under way, where the slice is held or gone."""
    if any(one.get("kind") == "merged" for one in lines):
        return "this slice has merged"
    how, by, _ = halted(Path("."), lines)
    if how == "paused":
        return "paused: delivered when it is resumed"
    if how == "stopped":
        return f"stopped by {'you' if by == PERSON else by}: resume it to deliver this"
    return ""


def receipts(home: Path) -> list[dict[str, Any]]:
    """Everything sent into this conversation with where it stands, oldest first: `state` one of `STATES`
    (`done` for a pause, resume, stop or withdrawal acted on); `delivered` the instant, `reply` the agent's
    words, `why` where it was not delivered or is waiting on something. Files refused on arrival are listed
    too, under the name they came in with."""
    lines = thread(home)
    messages = inbox(home)
    pending_withdrawals = {str(one.get("of", "")) for one in messages if one.get("kind") == "withdraw"}
    given = handed(lines)
    held_back = waiting_why(lines)
    found = []
    for message in messages:
        ident, kind = str(message["id"]), str(message.get("kind"))
        mine = [one for one in lines if ident in (str(one.get("id", "")), str(one.get("to", "")))
                and not one.get("refused")]
        kinds = [one["kind"] for one in mine]
        # Verified when it was handled: a message the thread has a word about is read from the thread, and
        # only one nobody has handled yet is held to the key — which may have been made again since.
        handled_already = bool(mine)
        delivered = next((one for one in reversed(mine) if one["kind"] == "delivered"), None) \
            if ident in given else None
        reply = next((one for one in mine if one["kind"] == "reply"), None)
        failed = next((one for one in mine if one["kind"] == "failed"), None)
        held = next((one for one in reversed(mine) if one["kind"] == "held"), None)
        state, why = "queued", str(held.get("why", "")) if held else held_back
        if not handled_already and not genuine(home, message):
            state, why = "not delivered", REKEYED if rekeyed(home, message) else UNSIGNED
        elif failed is not None and reply is None:
            state, why = "not delivered", str(failed.get("why", ""))
        elif kind != "say":
            state, why = ("done", "") if "seen" in kinds else ("queued", why)
        elif "withdrawn" in kinds or (ident in pending_withdrawals and delivered is None):
            state, why = "withdrawn", ""
        elif reply is not None:
            state, why = "answered", ""
        elif "unaddressed" in kinds:
            state, why = "unaddressed", ""
        elif delivered is not None:
            state, why = "delivered", ""
        found.append({"id": ident, "kind": kind, "t": str(message.get("t", "")), "from": str(message.get("from", "")),
                      "text": str(message.get("text", "")), "mode": str(message.get("mode", "wait")),
                      "state": state, "delivered": str(delivered.get("t", "")) if delivered else "",
                      "reply": str(reply.get("text", "")) if reply else "", "why": why})
    for one in lines:
        if one.get("kind") == "failed" and (one.get("refused") or one.get("malformed")):
            found.append({"id": str(one.get("id", "")), "kind": "", "t": str(one.get("t", "")), "from": "",
                          "text": str(one.get("text", "")), "mode": "wait", "state": "not delivered", "delivered": "", "reply": "",
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
