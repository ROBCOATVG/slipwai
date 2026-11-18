"""A conversation as the board reads it: turns in order, each receipt in words, and what a person has seen.

`talk.receipts` says where each message stands; this says it the way a person reads it — *Queued · goes in
when its current turn ends*, *Held: this slice is at its merge*, *Delivered 11:47*, *Not delivered* with why —
and puts the agent's replies and asks between them, and the thread's pauses and stops with who made them.

**Whether a slice can be interrupted is on its thread.** A driver held open writes a `session` line when it
opens one; print mode hands what was said over in the prompt and writes `delivered` with no turn after it.
So the newer of the two says which, and a slice whose thread says neither yet is not offered an interrupt.

**Seen** is a small record under the run folder, per project rather than per browser, written by the window
that showed a thread: how many of its lines that speak to a person — a reply, an ask, a failure, a hold its
captain placed — had been shown. A card carries a marker while a thread has more than that.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from . import talk
from .logs import run_dir

SEEN = "seen.json"
SEEING = threading.Lock()
#: The thread's lines that speak to a person, which "seen" counts.
HEARD = ("reply", "ask", "failed", "unaddressed")
WHO_ANSWERS = ".specify/cruise.json"
#: The `decide` values under which nobody is asked a product question: the captain's own list.
DECIDES = ("recommended-first", "skipper-always")


def clock(stamp: str) -> str:
    """An instant from the thread as the hour and minute on this machine's clock."""
    try:
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return ""
    # `%-d` is glibc and BSD only: Windows refuses it, so the day is written without the platform.
    if when.date() == datetime.now().astimezone().date():
        return when.strftime("%H:%M")
    return f"{when.day} {when:%b %H:%M}"


def held_open(lines: list[dict[str, Any]]) -> str:
    """`protocol` where the newest word on how messages reach the slice is a session its driver opened,
    `print` where it is a delivery handed over in a prompt, `''` where the thread says neither yet."""
    about = {str(one.get("about", "")) for one in lines if one.get("kind") == "turn"}
    said = ""
    for one in lines:
        if one.get("kind") == "session":
            said = "protocol"
        elif one.get("kind") == "delivered" and str(one.get("id", "")) not in about:
            said = "print"
    return said


def who(message: dict[str, Any]) -> str:
    """Who a message is from, as the thread says it: a person, a person through a captain, a captain."""
    by, via = str(message.get("from", "")), str(message.get("via", ""))
    if via.startswith("captain:") and by == talk.PERSON:
        return f"You, through the {via.removeprefix('captain:')} captain"
    if by == talk.PERSON:
        return "You"
    if by.startswith("captain:"):
        return f"Captain · {by.removeprefix('captain:')}"
    return {"feedback": "Your confirmed feedback", "skipper": "The skipper", "session": "A session"}.get(by, by)


def says(receipt: dict[str, Any], how: str) -> tuple[str, str]:
    """A receipt in words, and its tone: `wait`, `good`, `quiet` or `bad`."""
    state, why = receipt["state"], receipt["why"]
    at = clock(receipt.get("delivered") or "")
    if state == "queued":
        if why.lower().startswith("held"):
            return why[:1].upper() + why[1:], "wait"
        if why:
            return f"Queued · {why}", "wait"
        if how == "print":
            return PRINT_WAIT, "wait"
        if receipt.get("mode") == "interrupt":
            return "Queued · interrupts its turn", "wait"
        return "Queued · goes in when its current turn ends", "wait"
    if state == "delivered":
        cut = receipt.get("mode") == "interrupt"
        return ("Interrupted its turn · delivered " if cut else "Delivered ") + at, "good"
    if state == "answered":
        return "Answered", "good"
    if state == "unaddressed":
        return f"Delivered {at}, not addressed".replace("  ", " "), "quiet"
    if state == "not delivered":
        return f"Not delivered: {why}" if why else "Not delivered", "bad"
    if state == "withdrawn":
        return "Withdrawn", "quiet"
    return "Done", "quiet"


PRINT_WAIT = "Queued · goes in when the captain next starts it; if it merges first, it is not delivered"
#: What a waiting message will meet, by where its slice is: a message's turn needs a session, and a slice
#: parked, queued for a slot or merged has none open.
WHERE = {"done": "Queued · this slice has merged, so it will not be delivered: its captain says so when it "
                 "next looks",
         "waiting": "Queued · it is parked: its captain takes a person's message as the answer to the park",
         "queued": "Queued · goes in when the slice next starts",
         "todo": "Queued · goes in when the slice first starts"}


def placed_for(found: list[dict[str, Any]], where: str) -> list[dict[str, Any]]:
    """The turns with each plainly waiting message said as what it will meet where its slice now is."""
    if where not in WHERE:
        return found
    return [{**one, "line": WHERE[where]} if one["kind"] == "said" and one["state"] == "queued"
            and not one.get("held") and not one["steer"] else one for one in found]


def answer_of(lines: list[dict[str, Any]], ident: str) -> dict[str, Any] | None:
    return next((one for one in reversed(lines) if one.get("kind") == "answer" and str(one.get("to")) == ident), None)


#: Each conversation's fold, kept by what its files were when it was made: a poll every few seconds of a
#: long thread that has not moved is then a few `stat`s, not every message read and every receipt folded.
FOLDED: dict[Path, tuple[tuple, dict[str, Any]]] = {}
FOLDING = threading.Lock()


def stamp_of(home: Path) -> tuple:
    """What the conversation's files are now: the thread's size and time, the inbox's and `done/`'s, the key's."""
    found: list[tuple[int, int] | None] = []
    for path in (home / "thread.jsonl", home / "inbox", home / "inbox" / talk.DONE, talk.key_path(home)):
        try:
            held = path.stat()
            found.append((held.st_size, held.st_mtime_ns))
        except OSError:
            found.append(None)
    return tuple(found)


def turns(home: Path) -> dict[str, Any]:
    """Everything in one conversation, oldest first, ready to draw: `said` (a message and its receipt),
    `ask` (what the agent asked, and its answer where it has one), `note` (a pause, a resume, a stop and
    who made it) — with how messages reach it, what holds it, and how many lines speak to a person. Kept
    while its files stay as they were; a caller reads it and never changes it."""
    now = stamp_of(Path(home))
    with FOLDING:
        kept = FOLDED.get(Path(home))
        if kept is not None and kept[0] == now:
            return kept[1]
    made = fold(Path(home))
    with FOLDING:
        FOLDED[Path(home)] = (now, made)
        while len(FOLDED) > 512:
            FOLDED.pop(next(iter(FOLDED)))
    return made


def fold(home: Path) -> dict[str, Any]:
    lines = talk.thread(home)
    how = held_open(lines)
    messages = {str(one["id"]): one for one in talk.inbox(home)}
    answered_by_you = {str(one.get("of")): one for one in messages.values()
                       if one.get("kind") == "say" and one.get("of")}
    found: list[dict[str, Any]] = []
    for receipt in talk.receipts(home):
        message = messages.get(receipt["id"], {})
        if receipt["kind"] == "withdraw" or (receipt["kind"] in STEER_SAID and receipt["state"] == "done"):
            continue  # its effect is the thread's own line, which says who made it
        line, tone = says(receipt, how)
        steer = receipt["kind"] if receipt["kind"] in STEER_SAID else ""
        text = (STEER_SAID[steer] + (f": {receipt['text']}" if receipt["text"] else "")) if steer else receipt["text"]
        found.append({"kind": "said", "t": receipt["t"], "order": (0, sent_at(home, receipt["id"]), receipt["id"]),
                      "id": receipt["id"], "who": who(message) if message else
                      "A file in its inbox", "text": text, "steer": steer, "state": receipt["state"],
                      "line": line, "tone": tone, "reply": receipt["reply"], "of": str(message.get("of", "")),
                      "held": bool(receipt["why"])})
    for index, one in enumerate(lines):
        kind = one.get("kind")
        if kind == "ask":
            ident = str(one.get("id", ""))
            given = answer_of(lines, ident)
            yours = answered_by_you.get(ident)
            found.append({"kind": "ask", "t": str(one.get("t", "")), "order": (1, index, ""), "id": ident,
                          "what": str(one.get("what", "")),
                          "text": str(one.get("text", "")),
                          "options": [str(o) for o in one.get("options") or [] if isinstance(o, str | int | float)],
                          "answer": str(given.get("text", "")) if given else "",
                          "by": str(given.get("by", "")) if given else "",
                          # Who asked: a captain's own ask (`by: captain`) waits on a person whatever the run.
                          "asker": str(one.get("by", "")),
                          "yours": str(yours.get("id")) if yours else ""})
        elif kind in ("paused", "resumed", "stopped"):
            by = str(one.get("by", ""))
            named = "you" if by == talk.PERSON else f"its {by.removeprefix('captain:')} captain" \
                if by.startswith("captain:") else by or "the captain"
            why = str(one.get("why", ""))
            found.append({"kind": "note", "t": str(one.get("t", "")), "order": (1, index, ""), "by": by,
                          "text": f"{kind.capitalize()} by {named}" + (f": {why}" if why else "")})
    # By the second first, then in the order things happened within it: the messages as they were sent, ahead
    # of the thread's lines of that second, which are in the order its one writer appended them. By the second
    # alone, with ids that are random, two turns of one second drew in either order and "the newest" was a guess.
    found.sort(key=lambda one: (one["t"], one["order"]))
    halt, by, why, since = talk.hold(home, lines)
    return {"turns": found, "how": how, "halted": halt, "by": by, "why": why, "since": since, "heard": heard(lines),
            "merged": any(one.get("kind") == "merged" for one in lines)}


STEER_SAID = {"pause": "Pause", "resume": "Resume", "stop": "Stop", "withdraw": "Withdraw"}


def sent_at(home: Path, ident: str) -> int:
    """When a message's file was written, to the nanosecond, wherever it now lies — waiting, or moved aside once
    handled, which keeps the instant: the order a sender placed messages in within one second. 0 where none is."""
    for folder in (Path(home) / "inbox", Path(home) / "inbox" / talk.DONE):
        try:
            return (folder / f"{ident}.json").stat().st_mtime_ns
        except (OSError, ValueError):
            continue
    return 0


def heard(lines: list[dict[str, Any]]) -> int:
    """How many of the thread's lines speak to a person: what "seen" is counted in."""
    return sum(1 for one in lines if one.get("kind") in HEARD
               or (one.get("kind") in ("paused", "stopped") and one.get("by") != talk.PERSON))


def last(folded: dict[str, Any]) -> dict[str, Any] | None:
    """The last thing said in a conversation, either way, with its receipt: what a card shows. A pause or a
    resume is the last word only where nothing was said."""
    said = [one for one in folded["turns"] if one["kind"] != "note"] or folded["turns"]
    for one in reversed(said):
        if one["kind"] == "said" and one["state"] == "answered":
            return {"who": "Reply", "text": one["reply"], "line": f"To: {one['text']}", "tone": "good"}
        if one["kind"] == "said" and not one["steer"]:
            return {"who": one["who"], "text": one["text"], "line": one["line"], "tone": one["tone"]}
        if one["kind"] == "ask":
            return {"who": "It asks", "text": one["text"], "line": f"Answered: {one['answer']}" if one["answer"]
                    else "Not answered yet", "tone": "good" if one["answer"] else "wait"}
        if one["kind"] == "note":
            return {"who": "", "text": one["text"], "line": "", "tone": "quiet"}
    return None


# -- seen ------------------------------------------------------------------------------------------------


def seen_path(root: Path) -> Path:
    return run_dir(root) / "board" / SEEN


def seen(root: Path) -> dict[str, int]:
    """How many lines of each conversation a window has shown, keyed `<stream>/<slice>`."""
    try:
        held = json.loads(seen_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return {str(k): int(v) for k, v in held.items() if isinstance(v, int)} if isinstance(held, dict) else {}


def see(root: Path, fairway: str, slice_id: str, count: int) -> int:
    """Record that a window showed this conversation up to `count` of its lines; never backwards."""
    talk.place(run_dir(root), fairway, slice_id or talk.CAPTAIN)  # the names, checked as a conversation's
    with SEEING:  # two windows showing threads at once read, change and write the one record in turn
        held = seen(root)
        key = f"{fairway}/{slice_id or talk.CAPTAIN}"
        held[key] = max(held.get(key, 0), max(0, int(count)))
        path = seen_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        aside = path.with_name(f".{SEEN}.{os.getpid()}.{threading.get_ident()}.part")
        aside.write_text(json.dumps(held, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(aside, path)
        return held[key]


def unseen(root: Path, fairway: str, slice_id: str, count: int, kept: dict[str, int] | None = None) -> int:
    """How many lines speaking to a person this conversation has past what a window showed."""
    held = seen(root) if kept is None else kept
    return max(0, count - held.get(f"{fairway}/{slice_id or talk.CAPTAIN}", 0))


# -- who answers ------------------------------------------------------------------------------------------


def person_answers(root: Path) -> bool:
    """Whether a product question waits for a person: read as the captain reads `.specify/cruise.json`,
    where a cruising run with a `decide` that answers its own is the skipper's, and anything else a person's."""
    try:
        held = json.loads((root / WHO_ANSWERS).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return True
    if not isinstance(held, dict):
        return True
    return not (held.get("enabled") is True and str(held.get("decide") or "recommended-first") in DECIDES)


def open_asks(folded: dict[str, Any]) -> list[dict[str, Any]]:
    """The questions nothing has answered and no person has answered yet. A captain's own `ask` is one; a slice's
    mid-turn question is not, today: its driver answers it at once — declined, or by its captain — and writes
    the `answer` beside the `ask`, since decision 12's five minutes held for a person are not built."""
    return [one for one in folded["turns"] if one["kind"] == "ask" and one["what"] == "question"
            and not one["answer"] and not one["yours"]]
