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

    def root(self) -> Path: ...

    def checkout_busy(self) -> bool: ...

    def decided(self, slice_id: str, question: str, answer: str) -> str: ...


@dataclass
class Taken:
    """What one event's orders came to: every file read, those that verified, those waiting to be done, and
    whether one gave the key away."""

    seen: list[str] = field(default_factory=list)
    counted: int = 0
    pending: list[Path] = field(default_factory=list)
    verified: list[Order] = field(default_factory=list)
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


class Acts:
    def __init__(self, run: Path, fairway: str, stream: Stream) -> None:
        self.run, self.fairway, self.stream = run, fairway, stream
        self.home = talk.place(run, fairway, talk.CAPTAIN)
        self.asks = 0

    def common(self, order: Order, held: dict[str, Any]) -> str:
        """The rules for the orders every event shares: who may be spoken to, and whose hold is whose."""
        verb, target = order["verb"], str(order.get("slice") or "")
        if verb == "message" and order.get("of"):
            found = self.routed(str(order["of"]))
            if found is None:
                return f"{order['of']} is not a message in {self.fairway}'s captain's conversation"
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
        how, by, _ = talk.halted(talk.place(self.run, self.fairway, target))
        if verb == "resume" and how and by == talk.PERSON:
            return "only a person lifts a hold a person placed"
        if verb == "resume" and not how:
            return f"{target} is not paused or stopped"
        if verb in ("pause", "stop") and how and by == talk.PERSON:
            return f"a person holds {target} already ({how}), and their hold stands until they lift it"
        return ""

    def act(self, order: Order, held: dict[str, Any]) -> str:
        """Do one order the rules allow. A decision is the caller's to carry out; the rest are done here."""
        verb, target = order["verb"], str(order.get("slice") or "")
        me = f"captain:{self.fairway}"
        if verb == "message":
            routed = self.routed(str(order.get("of") or ""))
            text = str(order.get("text") or "") or (f"Routed to you by your captain, from {routed.get('from')}."
                                                    if routed else "")
            home = (talk.place(self.run, target.removeprefix("captain:"), talk.CAPTAIN)
                    if target.startswith("captain:") else talk.place(self.run, self.fairway, target))
            # From the captain, always: a person's words it routes are quoted, unaltered, beside its own.
            sent = talk.send(home, "say", text, "interrupt" if order.get("interrupt") else "wait", by=me,
                             of=str(order.get("of") or ""), via=me if routed else "",
                             quote=str(routed.get("text") or "") if routed else "")
            if routed:
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
        """The message in this captain's own conversation an order routes, or None."""
        if not of:
            return None
        return next((one for one in talk.inbox(self.home) if str(one["id"]) == of), None)
