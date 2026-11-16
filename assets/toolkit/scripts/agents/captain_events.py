#!/usr/bin/env python3
"""The program under the captain's agent: an event out, orders in, each checked again, done or refused.

Where a stream's captain is an agent (`harbour.json` `captain.agent`), every choice the captain program used
to make by a fixed rule (`captain_rules.py`) goes through `Helm.decide`: an event file is written with the
facts the choice needs and the orders the program will accept for it (`may`), the agent is woken with it, and
what it orders through `orders.py` is read here while it works. **Nothing the script checked is believed**:
each order is held again to its signature, its shape, its event, `may`, and the rule that owns the thing it
touches — clearance and the free slots for a start, the attempts for a retry, a person's hold for a resume —
and is done or refused, the result written beside it. An event is closed by its orders or, where the agent
is silent past its bound, gives nothing allowed, or cannot be run, by the fixed rule for that one decision,
and the closing record says which and why. The next event tries the agent again.

One event at a time, because there is one captain: a slice's thread that meets its gate while the agent is
answering another waits its turn. The stream's deck log is never the agent's: what an order does to a slice
goes through the slice's conversation (`talk.py`), signed by this process, and every line in the log is still
written by the captain program alone.

Standalone and dependency-free: this runs inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent))

import orders as order_door  # noqa: E402
import talk  # noqa: E402

Order = dict[str, Any]
Check = Callable[[Order, list[Order]], str]
#: The orders that are a decision, by the event they answer, handed back to the program to carry out.
DECIDING = {"choose-next": ("start",), "gate-failed": ("retry", "park"), "stuck": ("park",),
            "question": ("allow", "refuse"), "permission": ("allow", "refuse")}
#: The events whose choice has to be made one way or the other: with no deciding order the rule makes it.
#: Any other is the captain's where it did anything at all — a nudge to a stuck slice is its answer.
NEEDS = ("choose-next", "gate-failed", "question", "permission")
#: What one event may be answered with at most: past this an agent is flooding, and the rest are refused.
FLOOD = 12
#: How often the orders folder is read while the agent works.
LOOK = 0.1
#: Read-only tool kinds a captain may allow a slice's session outside its berth. A write outside the berth
#: is never the captain's to allow: it is another slice's work, or the project's own controls.
READS = ("read", "search", "fetch", "think")


class Turn(Protocol):
    """One wake-up of the agent, however it runs: whether it is done, when it was ready, and how to end it."""

    kind: str

    def finished(self) -> bool: ...

    def ready(self) -> float | None: ...

    def end(self) -> None: ...


class Runner(Protocol):
    def wake(self, event: Path, state: Path, held: dict[str, Any], env: dict[str, str]) -> Turn | str: ...

    def bound(self, turn: Turn) -> float: ...


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, body: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    aside = path.with_name(f".{path.name}.{secrets.token_hex(2)}.part")
    aside.write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(aside, path)


class Stream(Protocol):
    """What the helm asks of the captain program about its stream, so it holds no copy of the program's state."""

    def slices(self) -> set[str]: ...

    def fairways(self) -> set[str]: ...

    def merged(self, slice_id: str) -> bool: ...

    def merging(self, slice_id: str) -> bool: ...

    def hold(self, slice_id: str, why: str) -> None: ...

    def state(self) -> dict[str, Any]: ...


class Helm:
    def __init__(self, run: Path, fairway: str, runner: Runner, stream: Stream,
                 say: Callable[[str], None] = print) -> None:
        self.run, self.fairway, self.runner, self.stream, self.say = Path(run), fairway, runner, stream, say
        self.events = self.run / "events" / fairway
        self.orders = self.run / "orders" / fairway
        self.home = talk.place(self.run, fairway, talk.CAPTAIN)
        #: The key orders are signed with, made now and kept in this process's memory: the captain's agent is
        #: handed it in its environment, and no slice's session ever is.
        self.key = secrets.token_bytes(32)
        self.lock = threading.Lock()
        self.asks = 0

    def environment(self) -> dict[str, str]:
        """What the captain's agent is started under, beside its harness's own."""
        return {order_door.KEY: self.key.hex(), order_door.FAIRWAY: self.fairway,
                order_door.EVENTS: str(self.events), order_door.ORDERS: str(self.orders), "SLIPWAI_STAGE": "captain"}

    # -- one decision ------------------------------------------------------------------------------------------

    def decide(self, kind: str, slice_id: str, facts: dict[str, Any], may: list[str], default: list[Order],
               check: Check | None = None) -> tuple[list[Order], str]:
        """Put one choice to the agent and return (the orders that decide it, `captain` or `rule`)."""
        with self.lock:
            held = self.open(kind, slice_id, facts, may, default)
            began = time.monotonic()
            done: list[Order] = []
            seen: list[str] = []
            turn = self.runner.wake(self.events / f"{held['id']}.json", self.events / "state.json", held,
                                    self.environment())
            how, ready = "unavailable", None
            if isinstance(turn, str):
                why = f"the captain agent cannot be run: {turn}"
            else:
                how, why = self.watch(turn, held, check, done, seen)
                ready = turn.ready()
            self.take(held, check, done, seen)  # whatever landed as it ended, before the event closes
            deciding = [one for one in done if one["verb"] in DECIDING.get(kind, ())]
            acted = [one for one in done if one["verb"] != "none"]
            by = "captain" if (deciding if kind in NEEDS else acted) else "rule"
            if by == "rule" and how == "finished":
                declined = next((one for one in done if one["verb"] == "none"), None)
                why = (f"the captain declined: {declined.get('why')}" if declined else
                       "the captain gave no order this event takes" if not done else
                       "the captain acted and gave no decision")
            elif by == "captain":
                why = "; ".join(f"{one['verb']} {one.get('slice') or one.get('ask') or ''}".strip() for one in done)
            closed = {"v": 1, "id": held["id"], "t": now(), "by": by, "why": why, "orders": seen,
                      "cost": {"seconds": round(time.monotonic() - began, 3), "ready_seconds": ready,
                               "ended": how, "via": getattr(turn, "kind", "none"), "tokens": None}}
            write_json(self.events / f"{held['id']}.closed.json", closed)
            self.sweep()
            if by == "rule":
                self.say(f"captain: {kind}{' on ' + slice_id if slice_id else ''} decided by the rule — {why}")
                return default, by
            return deciding, by

    def watch(self, turn: Turn, held: dict[str, Any], check: Check | None, done: list[Order],
              seen: list[str]) -> tuple[str, str]:
        """Read orders while the agent works, until it ends its turn or its bound runs out. (how, why)."""
        while True:
            self.take(held, check, done, seen)
            if turn.finished():
                return "finished", ""
            ready = turn.ready()
            bound = self.runner.bound(turn)
            if ready is not None and time.monotonic() - ready > bound:
                turn.end()
                return "bound", f"the captain agent said nothing it could act on within its bound of {bound:.0f}s"
            time.sleep(LOOK)

    def open(self, kind: str, slice_id: str, facts: dict[str, Any], may: list[str],
             default: list[Order]) -> dict[str, Any]:
        t = now()
        held = {"v": 1, "id": f"{t.replace('-', '').replace(':', '')}-{secrets.token_hex(3)}", "t": t, "kind": kind,
                "fairway": self.fairway, "slice": slice_id or None, "facts": facts, "may": list(may),
                "default": default}
        try:
            state = self.stream.state()
        except Exception as fault:  # noqa: BLE001 — a fold that fails must not cost the decision
            state = {"unreadable": str(fault)}
        write_json(self.events / "state.json", {"v": 1, "t": t, "fairway": self.fairway, **state})
        write_json(self.events / f"{held['id']}.json", held)
        return held

    # -- the orders --------------------------------------------------------------------------------------------

    def waiting(self) -> list[Path]:
        return [path for path in sorted(self.orders.glob("*.json")) if not path.name.endswith(".result.json")
                and not path.with_name(f"{path.stem}.result.json").exists()] if self.orders.is_dir() else []

    def answer(self, path: Path, state: str, why: str) -> None:
        write_json(path.with_name(f"{path.stem}.result.json"), {"v": 1, "t": now(), "state": state, "why": why})

    def take(self, held: dict[str, Any], check: Check | None, done: list[Order], seen: list[str]) -> None:
        for path in self.waiting():
            try:
                order = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeDecodeError):
                self.answer(path, "refused", "it is not an order this reads")
                continue
            seen.append(path.stem)
            why = self.refusal(order, path, held, check, done, seen)
            if why:
                self.answer(path, "refused", why)
                continue
            try:
                said = self.act(order, held)
            except ValueError as fault:
                self.answer(path, "refused", str(fault))
                continue
            done.append(order)
            self.answer(path, "done", said)

    def refusal(self, order: Any, path: Path, held: dict[str, Any], check: Check | None, done: list[Order],
                seen: list[str]) -> str:
        """Why this order is not done, or `''` — every rule again, whatever the script said."""
        why = order_door.shape(order)
        if why:
            return why
        if order.get("id") != path.stem:
            return "its id is not its file's name"
        if not order_door.signed(self.key, order):
            return "it is not signed by this stream's captain: only the captain's session gives orders"
        if order.get("fairway") != self.fairway:
            return f"it is for {order.get('fairway')}, and this is {self.fairway}'s captain"
        if order.get("event") != held["id"]:
            return f"event {order.get('event')} is not open: it was closed, or never was"
        if order["verb"] not in held["may"]:
            return f"`{order['verb']}` is not an order this {held['kind']} event takes: {', '.join(held['may'])}"
        if len(seen) > FLOOD:
            return f"more than {FLOOD} orders for one event: the rest are not read"
        if check is not None and order["verb"] not in ("say", "ask", "message", "pause", "resume", "stop", "none"):
            return check(order, done)
        return self.common(order)

    def common(self, order: Order) -> str:
        """The rules for the orders every event shares: who may be spoken to, and whose hold is whose."""
        verb, target = order["verb"], str(order.get("slice") or "")
        if verb == "message" and target.startswith("captain:"):
            other = target.removeprefix("captain:")
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
            text = str(order.get("text") or "") or str((routed or {}).get("text", ""))
            if target.startswith("captain:"):
                home = talk.place(self.run, target.removeprefix("captain:"), talk.CAPTAIN)
            else:
                home = talk.place(self.run, self.fairway, target)
            sent = talk.send(home, "say", text, "interrupt" if order.get("interrupt") else "wait",
                             by=str(routed.get("from") or me) if routed else me, of=str(order.get("of") or ""),
                             via=me if routed else "")
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
        """The message in this captain's own conversation an order routes, or None — `ValueError` where it
        names one that is not there."""
        if not of:
            return None
        found = next((one for one in talk.inbox(self.home) if str(one["id"]) == of), None)
        if found is None:
            raise ValueError(f"{of} is not a message in {self.fairway}'s captain's conversation")
        return found

    def sweep(self) -> None:
        """Every order still unanswered once its event is closed: refused, saying so."""
        for path in self.waiting():
            self.answer(path, "refused", "its event was closed before it was read: the decision was made")

    # -- what a slice's session asks mid-turn ----------------------------------------------------------------

    def ruling(self, ask: dict[str, Any], default: Order) -> dict[str, Any]:
        """`drive.ruling`'s place, for this stream's slices: a product question goes where it always has; any
        other question, and a permission outside the berth, is the captain's to answer within the rules."""
        what = str(ask.get("what") or "")
        if what == "question" and product(str(ask.get("text") or "")):
            return answer_of(what, default, "rule")
        facts = {"ask": str(ask.get("id", "")), "text": str(ask.get("text") or ""),
                 "options": list(ask.get("options") or []), "tool": ask.get("tool") or None}
        may = ["allow", "refuse", "none"] + (["say"] if what == "question" else [])

        def check(order: Order, done: list[Order]) -> str:
            if str(order.get("ask")) != facts["ask"]:
                return f"{order.get('ask')} is not the ask this event is about ({facts['ask']})"
            if any(one["verb"] in ("allow", "refuse") for one in done):
                return "this ask is answered already"
            if order["verb"] == "allow" and what == "permission" and not readable(ask):
                return ("a write or a command outside the berth is not the captain's to allow: only reading is, "
                        "and only inside the project")
            return ""

        chosen, by = self.decide(what, str(ask.get("slice") or ""), facts, may, [default], check)
        return answer_of(what, chosen[0] if chosen else default, by)


#: How a slice's session marks a question as a product one when it asks mid-turn: what a captain never answers.
PRODUCT = "Product question:"


def product(text: str) -> bool:
    return text.strip().lower().startswith(PRODUCT.lower())


def readable(ask: dict[str, Any]) -> bool:
    """Whether a permission is a read inside the project: the most a captain may allow outside a berth."""
    tool = ask.get("tool") or {}
    root = Path(str(ask.get("root") or "")).resolve() if ask.get("root") else None
    places = [str(one) for one in tool.get("locations") or []]
    if str(tool.get("kind") or "") not in READS or not places or root is None:
        return False
    for place in places:
        try:
            Path(place).expanduser().resolve().relative_to(root)
        except ValueError:
            return False
    return True


def answer_of(what: str, order: Order, by: str) -> dict[str, Any]:
    """The answer `drive` hands the agent, from an order: `allow` for a permission, `accept` with the words for
    a question; anything else refuses or declines, with why."""
    allow = order.get("verb") == "allow"
    if what == "permission":
        return {"allow": allow, "why": str(order.get("why") or ""), "by": by}
    if allow:
        return {"action": "accept", "content": {"answer": str(order.get("why") or "")},
                "why": str(order.get("why") or ""), "by": by}
    return {"action": "decline", "why": str(order.get("why") or ""), "by": by}
