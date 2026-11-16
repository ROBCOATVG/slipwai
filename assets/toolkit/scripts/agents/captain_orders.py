#!/usr/bin/env python3
"""What a captain's order must be to be done, and what doing it is: the program's half of `orders.py`.

`refusal` is every rule an order is held to again, whatever the script that wrote it said: its shape, its
signature, its stream and event, the event's `may`, how many verified orders the event has had, and the rule
that owns what it touches. `Acts` does the orders every event shares — a message, a pause, a stop, a resume,
a sentence or a question for the person — through the slice's conversation, signed by this process as the
captain's. **Nothing a captain orders reads as a person's**: a message it routes is from the captain, with the
person's words quoted beside its own, so it never answers a park or a question and its interrupt costs the
slice an attempt as any captain's does.

Standalone and dependency-free: this runs inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent))

import orders as order_door  # noqa: E402
import talk  # noqa: E402

Order = dict[str, Any]
#: Verified orders one event may have at most: past this an agent is flooding, and the rest are refused. Only
#: orders that verify count, so files nobody signed cannot crowd the captain's own out.
FLOOD = 12
#: Read-only tool kinds a captain may allow a slice's session outside its berth. A write outside the berth
#: is never the captain's to allow: it is another slice's work, or the project's own controls.
READS = ("read", "search", "fetch", "think")
#: The orders whose rules every event shares, held here rather than by the event's own check.
COMMON = ("say", "ask", "message", "pause", "resume", "stop", "none")


class Stream(Protocol):
    """What the helm asks of the captain program about its stream, so it holds no copy of the program's state."""

    def slices(self) -> set[str]: ...

    def fairways(self) -> set[str]: ...

    def merged(self, slice_id: str) -> bool: ...

    def merging(self, slice_id: str) -> bool: ...

    def hold(self, slice_id: str, why: str) -> None: ...

    def state(self) -> dict[str, Any]: ...

    def decided(self, slice_id: str, question: str, answer: str) -> str: ...


@dataclass
class Taken:
    """What one event's orders came to: every file read, how many verified, and whether one gave the key away."""

    seen: list[str] = field(default_factory=list)
    counted: int = 0
    rekey: bool = False


def refusal(helm: Any, order: Any, path: Path, held: dict[str, Any], check: Callable[[Order, list[Order]], str] | None,
            done: list[Order], taken: Taken) -> str:
    """Why this order is not done, or `''`."""
    why = order_door.shape(order)
    if why:
        return why
    if order.get("id") != path.stem:
        return "its id is not its file's name"
    if not order_door.signed(helm.key, order):
        return "it is not signed by this stream's captain: only the captain's session gives orders"
    if helm.key.hex() in json.dumps({key: value for key, value in order.items() if key != "sig"}):
        taken.rekey = True
        return "it carries the captain's key in its words; the key is replaced, and the order is not done"
    taken.counted += 1
    if taken.counted > FLOOD:
        return f"more than {FLOOD} orders for one event: the rest are not read"
    if order.get("fairway") != helm.fairway:
        return f"it is for {order.get('fairway')}, and this is {helm.fairway}'s captain"
    if order.get("event") != held["id"]:
        return f"event {order.get('event')} is not open: it was closed, or never was"
    if order["verb"] not in held["may"]:
        return f"`{order['verb']}` is not an order this {held['kind']} event takes: {', '.join(held['may'])}"
    if check is not None and order["verb"] not in COMMON:
        return check(order, done)
    return helm.acts.common(order, held)


def person_asked(home: Path) -> str:
    """A hold a person has asked for and that is not yet on the thread as `paused` or `stopped`: a pause
    waiting for the turn under way to end, or a pause or stop still in the inbox. `pause`, `stop` or `''`."""
    if talk.pending_pause(home) == talk.PERSON:
        return "pause"
    waiting = [one for one in talk.unseen(home) if one.get("from") == talk.PERSON and one.get("kind") in ("pause", "stop")]
    return str(waiting[-1]["kind"]) if waiting else ""


class Acts:
    def __init__(self, run: Path, fairway: str, stream: Stream) -> None:
        self.run, self.fairway, self.stream = run, fairway, stream
        self.home = talk.place(run, fairway, talk.CAPTAIN)
        self.asks = 0
        #: The messages already routed, each once.
        self.used: set[str] = set()

    def common(self, order: Order, held: dict[str, Any]) -> str:
        """The rules for the orders every event shares: who may be spoken to, and whose hold is whose."""
        verb, target = order["verb"], str(order.get("slice") or "")
        if verb in ("message", "say", "ask") and self.carries_key(order):
            return "it carries the conversation key in its words, which is never said to anyone"
        if verb == "message" and order.get("of"):
            # What a person said is routed once, by the event that put it to the captain, and no other: an old
            # "yes, go ahead" cannot be attached to whatever the captain says next.
            if held["kind"] != "message" or str(order["of"]) != str(held["facts"].get("inbox") or ""):
                return f"{order['of']} is not the message this event put to the captain"
            if str(order["of"]) in self.used:
                return f"{order['of']} has been routed already"
            if self.routed(str(order["of"])) is None:
                return f"{order['of']} is not a genuine message in {self.fairway}'s captain's conversation"
        if verb == "message" and target.startswith("captain:"):
            other = target.removeprefix("captain:")
            if held["kind"] == "message" and str(held["facts"].get("from") or "").startswith("captain:"):
                # One hop: what a captain said is routed to a slice, never on to a third captain, so two
                # captains cannot keep each other awake.
                return "a message from another captain may be routed to a slice, never on to a captain"
            return "" if other in self.stream.fairways() and other != self.fairway else \
                f"{other} is not another stream's captain on this chart"
        if verb not in ("message", "pause", "resume", "stop"):
            return ""
        if target not in self.stream.slices():
            return f"{target} is not a slice of {self.fairway}"
        if self.stream.merged(target):
            return f"{target} has merged: there is nothing left to steer"
        home = talk.place(self.run, self.fairway, target)
        how, by, _ = talk.halted(home)
        asked = person_asked(home)
        if verb == "resume" and ((how and by == talk.PERSON) or asked):
            return "only a person lifts a hold a person placed"
        if verb == "resume" and not how:
            return f"{target} is not paused or stopped"
        if verb in ("pause", "stop") and ((how and by == talk.PERSON) or asked):
            return (f"a person holds {target} already ({how or asked}), and their hold stands until they lift it")
        return ""

    def carries_key(self, order: Order) -> bool:
        """Whether an order's words carry the conversation key, as raw bytes or written out in hex."""
        secret = talk.key(self.home)
        if not secret:
            return False
        said = " ".join(str(order.get(name) or "") for name in ("text", "why", "note", "needs"))
        return secret.hex() in said or secret.decode("latin-1") in said

    def act(self, order: Order, held: dict[str, Any]) -> str:
        """Do one order the rules allow. A decision is the caller's to carry out; the rest are done here."""
        verb, target = order["verb"], str(order.get("slice") or "")
        me = f"captain:{self.fairway}"
        if verb == "message":
            routed = self.routed(str(order.get("of") or ""))
            # Who is quoted is the routed message's own `from`, which its signature covers: never a field a
            # file supplied unverified, since only a genuine message can be routed at all.
            quoted = str((routed or {}).get("from") or "")
            text = str(order.get("text") or "") or (f"Routed to you by your captain, from {quoted}." if routed else "")
            home = (talk.place(self.run, target.removeprefix("captain:"), talk.CAPTAIN)
                    if target.startswith("captain:") else talk.place(self.run, self.fairway, target))
            # From the captain, always: a person's words it routes are quoted, unaltered, beside its own.
            sent = talk.send(home, "say", text, "interrupt" if order.get("interrupt") else "wait", by=me,
                             of=str(order.get("of") or ""), via=me if routed else "",
                             quote=str(routed.get("text") or "") if routed else "", quote_from=quoted)
            if routed:
                self.used.add(str(routed["id"]))
                talk.note(self.home, "reply", to=str(routed["id"]), text=f"routed to {target}", by="captain")
            if not target.startswith("captain:") and self.stream.merging(target):
                self.stream.hold(target, "held: this slice is at its merge")
                return f"sent as {sent['id']}, and held: {target} is at its merge"
            return f"sent as {sent['id']}"
        if verb in ("pause", "resume", "stop"):
            sent = talk.send(talk.place(self.run, self.fairway, target), verb, str(order.get("why") or ""), by=me)
            return f"sent as {sent['id']}"
        if verb == "say":
            of = str(order.get("of") or "") or (str(held["facts"].get("inbox") or "") if held["kind"] == "message" else "")
            if of:
                talk.note(self.home, "reply", to=of, text=str(order["text"]), by="captain")
            else:
                talk.note(self.home, "said", text=str(order["text"]), by="captain")
            return "said"
        if verb == "ask":
            self.asks += 1
            ident = f"captain-ask-{held['id']}-{self.asks}"
            talk.note(self.home, "ask", id=ident, what="question", text=str(order["text"]),
                      options=list(order.get("options") or []), by="captain")
            return f"asked as {ident}"
        return ""

    def routed(self, of: str) -> dict[str, Any] | None:
        """The message in this captain's own conversation an order routes, or None — and None for any file in
        that inbox whose signature does not hold: what can be routed is only what was really said."""
        if not of:
            return None
        found = next((one for one in talk.inbox(self.home) if str(one["id"]) == of), None)
        return found if found is not None and talk.genuine(self.home, found) else None
