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
from datetime import datetime
from pathlib import Path
from typing import Any

from . import talk
from .logs import run_dir

SEEN = "seen.json"
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
    return when.strftime("%H:%M" if when.date() == datetime.now().astimezone().date() else "%-d %b %H:%M")


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
            return "Queued · goes in when the slice next starts", "wait"
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


def answer_of(lines: list[dict[str, Any]], ident: str) -> dict[str, Any] | None:
    return next((one for one in reversed(lines) if one.get("kind") == "answer" and str(one.get("to")) == ident), None)


def turns(home: Path) -> dict[str, Any]:
    """Everything in one conversation, oldest first, ready to draw: `said` (a message and its receipt),
    `ask` (what the agent asked, and its answer where it has one), `note` (a pause, a resume, a stop and
    who made it) — with how messages reach it, what holds it, and how many lines speak to a person."""
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
        found.append({"kind": "said", "t": receipt["t"], "id": receipt["id"], "who": who(message) if message else
                      "A file in its inbox", "text": text, "steer": steer, "state": receipt["state"],
                      "line": line, "tone": tone, "reply": receipt["reply"], "of": str(message.get("of", ""))})
    for one in lines:
        kind = one.get("kind")
        if kind == "ask":
            ident = str(one.get("id", ""))
            given = answer_of(lines, ident)
            yours = answered_by_you.get(ident)
            found.append({"kind": "ask", "t": str(one.get("t", "")), "id": ident, "what": str(one.get("what", "")),
                          "text": str(one.get("text", "")),
                          "options": [str(o) for o in one.get("options") or [] if isinstance(o, str | int | float)],
                          "answer": str(given.get("text", "")) if given else "",
                          "by": str(given.get("by", "")) if given else "",
                          "yours": str(yours.get("id")) if yours else ""})
        elif kind in ("paused", "resumed", "stopped"):
            by = str(one.get("by", ""))
            named = "you" if by == talk.PERSON else f"its {by.removeprefix('captain:')} captain" \
                if by.startswith("captain:") else by or "the captain"
            why = str(one.get("why", ""))
            found.append({"kind": "note", "t": str(one.get("t", "")), "by": by,
                          "text": f"{kind.capitalize()} by {named}" + (f": {why}" if why else "")})
    found.sort(key=lambda one: one["t"])
    halt, by, why = talk.halted(home, lines)
    return {"turns": found, "how": how, "halted": halt, "by": by, "why": why, "heard": heard(lines),
            "merged": any(one.get("kind") == "merged" for one in lines)}


STEER_SAID = {"pause": "Pause", "resume": "Resume", "stop": "Stop", "withdraw": "Withdraw"}


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
    held = seen(root)
    key = f"{fairway}/{slice_id or talk.CAPTAIN}"
    held[key] = max(held.get(key, 0), max(0, int(count)))
    path = seen_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    aside = path.with_name(f".{SEEN}.{os.getpid()}.part")
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
    """The product questions a slice asked that nothing has answered and no person has answered yet."""
    return [one for one in folded["turns"] if one["kind"] == "ask" and one["what"] == "question"
            and not one["answer"] and not one["yours"]]
