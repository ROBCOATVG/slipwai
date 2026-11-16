#!/usr/bin/env python3
"""The program under the captain's agent: an event out, orders in, each checked again, done or refused.

Where a stream's captain is an agent (`harbour.json` `captain.agent`), every choice the captain program used
to make by a fixed rule (`captain_rules.py`) goes through `Helm.decide`: an event file is written with the
facts the choice needs and the orders the program will accept for it (`may`), the agent is woken with it, and
what it orders through `orders.py` is read here while it works. **Nothing the script checked is believed**:
each order is held again to its signature, its shape, its event, `may`, and the rule that owns the thing it
touches — clearance and the free slots for a start, the attempts for a retry, a person's hold for a resume —
and is done or refused, the result written beside it (`captain_orders.py`). An event is closed by its orders
or, where the agent is silent past its bound, gives nothing allowed, or cannot be run, by the fixed rule for
that one decision, and the closing record says which and why. The next event tries the agent again.

**Bounded, whoever waits.** One captain answers one event at a time, and an ask from a slice's turn under way
is put ahead of every other. Nobody waits past the bound for the captain to be free, and a captain whose
session is not ready within the bound has that event closed by the rule. Past `captain.per_hour` events in an
hour the stream runs on its rules alone until the hour has passed, and says so.

**Checked afterwards, where the agent ran as a process.** A headless captain is started in a folder of its
own with the harness's most restrictive mode its registry row offers, but a session with a shell can still
reach the project. So the project's tree is read before and after (`captain_guard.py`), its orders are done
only once it has ended and the tree is as it was, and a captain that changed anything has every order of that
event refused, the event closed by the rule, and the agent turned off for the stream until a person turns it
back on.

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

import captain_guard  # noqa: E402
import captain_orders  # noqa: E402
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
#: What a slice's turn under way asks: put to the captain ahead of everything else, since the turn waits on it.
ASKS = ("question", "permission")
#: How often the orders folder is read while the agent works.
LOOK = 0.1
#: Events a stream's captain is woken for in an hour, where `harbour.json` does not say.
PER_HOUR = 30


class Turn(Protocol):
    """One wake-up of the agent, however it runs: whether it is done, when it started and was ready, how to
    end it, and whether its orders wait for it to end before they are done (a process, which is checked)."""

    kind: str
    deferred: bool

    def finished(self) -> bool: ...

    def started(self) -> float: ...

    def ready(self) -> float | None: ...

    def end(self) -> None: ...


class Runner(Protocol):
    def wake(self, event: Path, state: Path, held: dict[str, Any], env: dict[str, str]) -> Turn | str: ...

    def bound(self, turn: Turn | None) -> float: ...

    def holds_session(self) -> bool: ...

    def reset(self) -> None: ...


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, body: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    aside = path.with_name(f".{path.name}.{secrets.token_hex(2)}.part")
    aside.write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(aside, path)


class Helm:
    def __init__(self, run: Path, fairway: str, runner: Runner, stream: captain_orders.Stream,
                 say: Callable[[str], None] = print, settings: dict[str, Any] | None = None) -> None:
        self.run, self.fairway, self.runner, self.stream, self.say = Path(run), fairway, runner, stream, say
        self.settings = settings or {}
        self.events = self.run / "events" / fairway
        self.orders = self.run / "orders" / fairway
        self.home = talk.place(self.run, fairway, talk.CAPTAIN)
        #: The key orders are signed with, made in this process's memory and handed to the captain's agent in
        #: its environment, never to a slice's session. Who else can read it: any process of the same user, on
        #: a platform that shows another process's environment (`/proc/<pid>/environ` on Linux, `ps eww` on
        #: macOS). A 0600 file, or a descriptor the agent inherits, is readable by the same user just the same,
        #: so neither is better; what is, is a key that is good for little: a headless captain is handed a new
        #: one at every wake-up, a held session one per session, and a key an order carries in its words is
        #: replaced at once.
        self.key = secrets.token_bytes(32)
        self.acts = captain_orders.Acts(self.run, fairway, stream)
        self.cond = threading.Condition()
        self.busy = False
        self.queue: list[tuple[int, int]] = []
        self.tickets = 0
        self.said_ceiling = False

    def environment(self) -> dict[str, str]:
        """What the captain's agent is started under, beside its harness's own: a new key unless the session
        that was handed the last one is still open."""
        if not self.runner.holds_session():
            self.key = secrets.token_bytes(32)
        return {order_door.KEY: self.key.hex(), order_door.FAIRWAY: self.fairway,
                order_door.EVENTS: str(self.events), order_door.ORDERS: str(self.orders), "SLIPWAI_STAGE": "captain",
                "SLIPWAI_CAPTAIN_ORDERS_PY": str(Path(__file__).resolve().parent / "orders.py")}

    # -- whose turn ---------------------------------------------------------------------------------------------

    def acquire(self, priority: int, until: float) -> bool:
        """The captain, for this decision, once every earlier ask and decision of higher priority is done — or
        False at `until`, when the caller decides by the rule rather than wait on a captain any longer."""
        with self.cond:
            self.tickets += 1
            ticket = (priority, self.tickets)
            self.queue.append(ticket)
            try:
                while self.busy or min(self.queue) != ticket:
                    left = until - time.monotonic()
                    if left <= 0:
                        return False
                    self.cond.wait(left)
                self.busy = True
                return True
            finally:
                self.queue.remove(ticket)
                self.cond.notify_all()

    def release(self) -> None:
        with self.cond:
            self.busy = False
            self.cond.notify_all()

    # -- one decision ------------------------------------------------------------------------------------------

    def decide(self, kind: str, slice_id: str, facts: dict[str, Any], may: list[str], default: list[Order],
               check: Check | None = None) -> tuple[list[Order], str]:
        """Put one choice to the agent and return (the orders that decide it, `captain` or `rule`)."""
        off = captain_guard.turned_off(self.events)
        if off:
            return default, self.ruled(kind, slice_id, f"the captain agent is turned off for this stream: {off}")
        if captain_guard.past_ceiling(self.events, int(self.settings.get("per_hour") or PER_HOUR)):
            if not self.said_ceiling:
                self.said_ceiling = True
                self.say(f"captain: {self.fairway} has woken its captain {self.settings.get('per_hour') or PER_HOUR} "
                         f"times this hour, the ceiling; it runs on its rules alone until the hour has passed")
            return default, "rule"
        self.said_ceiling = False
        if not self.acquire(0 if kind in ASKS else 1, time.monotonic() + self.runner.bound(None)):
            return default, self.ruled(kind, slice_id, "the captain was answering another event for the whole "
                                                       "of its bound")
        try:
            return self.decided(kind, slice_id, facts, may, default, check)
        finally:
            self.release()

    def ruled(self, kind: str, slice_id: str, why: str) -> str:
        self.say(f"captain: {kind}{' on ' + slice_id if slice_id else ''} decided by the rule — {why}")
        return "rule"

    def decided(self, kind: str, slice_id: str, facts: dict[str, Any], may: list[str], default: list[Order],
                check: Check | None) -> tuple[list[Order], str]:
        held = self.open(kind, slice_id, facts, may, default)
        began = time.monotonic()
        done: list[Order] = []
        taken = captain_orders.Taken()
        before = captain_guard.snapshot(self.stream.root(), self.stream.checkout_busy(), self.run)
        turn = self.runner.wake(self.events / f"{held['id']}.json", self.events / "state.json", held,
                                self.environment())
        how, ready, changed = "unavailable", None, ""
        if isinstance(turn, str):
            why = f"the captain agent cannot be run: {turn}"
        else:
            how, why = self.watch(turn, held, check, done, taken)
            ready = turn.ready()
        self.take(held, check, done, taken, live=not getattr(turn, "deferred", False))
        if not isinstance(turn, str) and getattr(turn, "deferred", False):
            after = captain_guard.snapshot(self.stream.root(), self.stream.checkout_busy(), self.run)
            changed = captain_guard.changed(before, after)
            if changed:
                captain_guard.turn_off(self.events, f"its captain changed the project while deciding: {changed}")
                self.say(f"captain: WARNING — {self.fairway}'s captain agent changed the project while it decided "
                         f"({changed}). Its orders are refused, and the agent is off for this stream until a "
                         f"person turns it back on")
                for path in taken.pending:
                    self.answer(path, "refused", f"the captain changed the project while deciding: {changed}")
                done.clear()
                why = f"its captain changed the project while deciding, so its orders were refused: {changed}"
            else:
                for path, order in zip(taken.pending, taken.verified, strict=True):
                    self.carry(path, order, held, done)
        if taken.rekey:
            self.key = secrets.token_bytes(32)
            self.runner.reset()
        deciding = [one for one in done if one["verb"] in DECIDING.get(kind, ())]
        acted = [one for one in done if one["verb"] != "none"]
        by = "captain" if (deciding if kind in NEEDS else acted) and not changed else "rule"
        if by == "rule" and how == "finished" and not changed:
            declined = next((one for one in done if one["verb"] == "none"), None)
            why = (f"the captain declined: {declined.get('why')}" if declined else
                   "the captain gave no order this event takes" if not done else
                   "the captain acted and gave no decision")
        elif by == "captain":
            why = "; ".join(f"{one['verb']} {one.get('slice') or one.get('ask') or ''}".strip() for one in done)
        closed = {"v": 1, "id": held["id"], "t": now(), "by": by, "why": why, "orders": taken.seen,
                  "cost": {"seconds": round(time.monotonic() - began, 3), "ready_seconds": ready,
                           "ended": "changed" if changed else how, "via": getattr(turn, "kind", "none"),
                           "tokens": None}}
        write_json(self.events / f"{held['id']}.closed.json", closed)
        self.sweep()
        if by == "rule":
            self.ruled(kind, slice_id, why)
            return default, by
        return deciding, by

    def watch(self, turn: Turn, held: dict[str, Any], check: Check | None, done: list[Order],
              taken: captain_orders.Taken) -> tuple[str, str]:
        """Read orders while the agent works, until it ends its turn or its bound runs out. (how, why)."""
        bound = self.runner.bound(turn)
        while True:
            self.take(held, check, done, taken, live=not getattr(turn, "deferred", False))
            if turn.finished():
                return "finished", ""
            ready = turn.ready()
            if ready is None and time.monotonic() - turn.started() > bound:
                turn.end()
                return "bound", f"the captain's session was not ready within its bound of {bound:.0f}s"
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

    def take(self, held: dict[str, Any], check: Check | None, done: list[Order], taken: captain_orders.Taken,
             live: bool = True) -> None:
        """Read every order not yet read. Live, each is done as it comes; otherwise each that passes is held
        until the agent has ended and the project is found as it was."""
        for path in self.waiting():
            if path in taken.pending:
                continue
            try:
                order = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeDecodeError):
                self.answer(path, "refused", "it is not an order this reads")
                continue
            taken.seen.append(path.stem)
            why = captain_orders.refusal(self, order, path, held, check, [*done, *taken.verified], taken)
            if why:
                self.answer(path, "refused", why)
            elif live:
                self.carry(path, order, held, done)
            else:
                taken.pending.append(path)
                taken.verified.append(order)

    def carry(self, path: Path, order: Order, held: dict[str, Any], done: list[Order]) -> None:
        try:
            said = self.acts.act(order, held)
        except ValueError as fault:
            self.answer(path, "refused", str(fault))
            return
        done.append(order)
        self.answer(path, "done", said)

    def sweep(self) -> None:
        """Every order still unanswered once its event is closed: refused, saying so."""
        for path in self.waiting():
            self.answer(path, "refused", "its event was closed before it was read: the decision was made")

    # -- what a slice's session asks mid-turn ----------------------------------------------------------------

    def ruling(self, ask: dict[str, Any], default: Order) -> dict[str, Any]:
        """`drive.ruling`'s place, for this stream's slices. A permission outside the berth is the captain's to
        allow within the rules. A question is the captain's to answer where the project lets it
        (`captain.answers`, on by default), and every answer it gives is written as a `decision` in the deck
        log, `decided_by` the captain, which a person reviews like any other and which counts toward the
        ceiling on unreviewed decisions: the program cannot tell a product question from an operational one by
        its words, so it does not try — it bounds the captain's answers and shows every one."""
        what = str(ask.get("what") or "")
        if what == "question" and self.settings.get("answers") is False:
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

        slice_id = str(ask.get("slice") or "")
        chosen, by = self.decide(what, slice_id, facts, may, [default], check)
        order = chosen[0] if chosen else default
        if what == "question" and by == "captain" and order.get("verb") == "allow":
            ident = self.stream.decided(slice_id, facts["text"], str(order.get("why") or ""))
            order = {**order, "why": f"{order.get('why')} (the captain's answer, recorded as decision {ident} for a "
                                     f"person to review)"}
        return answer_of(what, order, by)


def readable(ask: dict[str, Any]) -> bool:
    """Whether a permission is a read inside the project: the most a captain may allow outside a berth."""
    tool = ask.get("tool") or {}
    root = Path(str(ask.get("root") or "")).resolve() if ask.get("root") else None
    places = [str(one) for one in tool.get("locations") or []]
    if str(tool.get("kind") or "") not in captain_orders.READS or not places or root is None:
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
