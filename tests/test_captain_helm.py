"""Layer 3, at the helm: a captain agent that misbehaves is refused or timed out, every time, each its own case.

`captain_events.Helm` is what stands between the agent and the stream: it writes the event, wakes the agent,
reads its orders and holds each to every rule again. Here the agent is a function that writes order files the
moment it is woken — or never — so each case is one misbehaviour and nothing else: an order not in `may`, a
malformed file, one unsigned or signed with a slice's key, an agent silent past its bound, a flood, a resume
of a person's hold, a pause over it, a message to a slice at its merge, and an answer to a product question.
Each is refused with why, and where it was the whole of the answer the fixed rule decides, said in the
closing record. The captain program around the helm is `test_captain_agent`'s.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import time
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401
from captain_fixture import AGENTS, CARRIED

from slipwai import logs, talk


def loaded(root: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"{name}_{root.name}", root / "scripts/agents" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


class Turn:
    deferred = False

    def __init__(self, done: bool, kind: str = "named") -> None:
        self.done, self.kind, self.began, self.ended = done, kind, time.monotonic(), False

    def finished(self) -> bool:
        return self.done

    def started(self) -> float:
        return self.began

    def ready(self) -> float:
        return self.began

    def end(self) -> None:
        self.ended = True


class Runner:
    """An agent that is a function: it writes its orders when woken, and is finished at once — or never."""

    def __init__(self, act: Callable[[dict, dict], object] | None, bound: float = 0.5) -> None:
        self.act, self.limit, self.turns = act, bound, []  # type: ignore[var-annotated]

    def wake(self, event: Path, state: Path, held: dict, env: dict) -> Any:
        if self.act is None:
            turn = Turn(done=False)
        else:
            self.act(held, env)
            turn = Turn(done=True)
        self.turns.append(turn)
        return turn

    def bound(self, turn: Any) -> float:
        return self.limit

    def holds_session(self) -> bool:
        return False

    def reset(self) -> None:
        self.resets = getattr(self, "resets", 0) + 1


class Stream:
    def __init__(self, root: Path | None = None) -> None:
        self.held: list[tuple[str, str]] = []
        self.at_merge: set[str] = set()
        self.home = root or Path(tempfile.mkdtemp())
        self.answers: list[tuple[str, str, str]] = []

    def root(self) -> Path:
        return self.home

    def checkout_busy(self) -> bool:
        return False

    def decided(self, slice_id: str, question: str, answer: str) -> str:
        self.answers.append((slice_id, question, answer))
        return f"captain-{slice_id}-{len(self.answers)}"

    def slices(self) -> set[str]:
        return {"ORD-01", "ORD-02"}

    def fairways(self) -> set[str]:
        return {"ORD", "BIL"}

    def merged(self, slice_id: str) -> bool:
        return False

    def merging(self, slice_id: str) -> bool:
        return slice_id in self.at_merge

    def hold(self, slice_id: str, why: str) -> None:
        self.held.append((slice_id, why))

    def state(self) -> dict:
        return {"in_flight": []}


class HelmBase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        (self.root / "scripts/agents").mkdir(parents=True)
        for name in CARRIED:
            (self.root / "scripts/agents" / name).write_text((AGENTS / name).read_text(encoding="utf-8"),
                                                             encoding="utf-8")
        self.events = loaded(self.root, "captain_events")
        self.orders = self.events.order_door
        self.run_dir = logs.run_dir(self.root)
        self.stream = Stream(self.root)
        self.said: list[str] = []

    def helm(self, act: Callable[[dict, dict], object] | None, bound: float = 0.5) -> Any:
        return self.events.Helm(self.run_dir, "ORD", Runner(act, bound), self.stream, say=self.said.append)

    def order(self, held: dict, env: dict, verb: str, key: bytes | None = None, **said: Any) -> str:
        body = {"v": 1, "id": f"20261116T090000Z-{len(list(self.folder().glob('*'))):06x}", "t": "2026-11-16T09:00:00Z",
                "event": held["id"], "fairway": "ORD", "verb": verb, **said}
        secret = bytes.fromhex(env[self.orders.KEY]) if key is None else key
        if secret:
            body["sig"] = self.orders.sign(secret, body)
        self.orders.write(self.folder(), body)
        return str(body["id"])

    def folder(self) -> Path:
        return self.run_dir / "orders" / "ORD"

    def results(self) -> list[tuple[str, str]]:
        found = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(self.folder().glob("*.result.json"))]
        return [(one["state"], one["why"]) for one in found]

    def closed(self) -> list[dict]:
        return [json.loads(path.read_text(encoding="utf-8"))
                for path in sorted((self.run_dir / "events/ORD").glob("*.closed.json"))]

    def choose(self, helm: Any) -> tuple[list[dict], str]:
        default = [{"verb": "start", "slice": "ORD-01"}]

        def check(order: dict, done: list[dict]) -> str:
            return "" if order.get("slice") in ("ORD-01", "ORD-02") else f"{order.get('slice')} is not cleared"
        return helm.decide("choose-next", "", {"free": 1, "cleared": []}, ["start", "say", "none"], default, check)


class HelmTest(HelmBase):
    def test_an_order_not_in_may_is_refused_and_the_rule_decides(self) -> None:
        chosen, by = self.choose(self.helm(lambda held, env: self.order(held, env, "retry", slice="ORD-01", note="x")))
        self.assertEqual((chosen, by), ([{"verb": "start", "slice": "ORD-01"}], "rule"))
        self.assertEqual(self.results(), [("refused", "`retry` is not an order this choose-next event takes: "
                                                      "start, say, none")])
        self.assertEqual(self.closed()[0]["by"], "rule")

    def test_a_merge_is_not_an_order_at_all(self) -> None:
        _, by = self.choose(self.helm(lambda held, env: self.order(held, env, "merge", slice="ORD-01")))
        self.assertEqual(by, "rule")
        self.assertIn("'merge' is not an order a captain gives", self.results()[0][1])

    def test_a_malformed_order_is_refused(self) -> None:
        def act(held: dict, env: dict) -> None:
            self.folder().mkdir(parents=True, exist_ok=True)
            (self.folder() / "garbage.json").write_text("{not json", encoding="utf-8")
            self.order(held, env, "start", slice="ORD-01", interrupt="yes")
        _, by = self.choose(self.helm(act))
        self.assertEqual(by, "rule")
        self.assertEqual(sorted(why for _, why in self.results()),
                         ["`interrupt` is true or false", "it is not an order this reads"])

    def test_an_unsigned_order_or_one_a_slice_signed_is_refused(self) -> None:
        def act(held: dict, env: dict) -> None:
            self.order(held, env, "start", key=b"", slice="ORD-02")
            self.order(held, env, "start", key=b"a key a slice's session made", slice="ORD-02")
        chosen, by = self.choose(self.helm(act))
        self.assertEqual((chosen[0]["slice"], by), ("ORD-01", "rule"))
        self.assertEqual({why for _, why in self.results()},
                         {"it is not signed by this stream's captain: only the captain's session gives orders"})

    def test_a_start_the_rules_do_not_allow_is_refused(self) -> None:
        chosen, by = self.choose(self.helm(lambda held, env: self.order(held, env, "start", slice="BIL-02")))
        self.assertEqual((chosen[0]["slice"], by), ("ORD-01", "rule"))
        self.assertEqual(self.results(), [("refused", "BIL-02 is not cleared")])

    def test_silence_until_the_bound_is_the_rule_and_says_so(self) -> None:
        helm = self.helm(None, bound=0.3)
        chosen, by = self.choose(helm)
        self.assertEqual((chosen[0]["slice"], by), ("ORD-01", "rule"))
        record = self.closed()[0]
        self.assertEqual((record["by"], record["cost"]["ended"]), ("rule", "bound"))
        self.assertIn("within its bound", record["why"])
        self.assertTrue(helm.runner.turns[0].ended, "the turn was ended at the bound")
        self.assertIn("decided by the rule", self.said[0])

    def test_an_order_given_after_its_event_closed_is_refused(self) -> None:
        helm = self.helm(None, bound=0.2)
        helm.runner.holds_session = lambda: True  # one held session: one key for both events
        self.choose(helm)
        late = {"id": self.closed()[0]["id"]}
        self.order(late, helm.environment(), "start", slice="ORD-02")
        helm.runner.act = lambda held, env: None
        self.choose(helm)
        self.assertIn(("refused", f"event {late['id']} is not open: it was closed, or never was"), self.results())

    def test_a_flood_is_cut_off(self) -> None:
        def act(held: dict, env: dict) -> None:
            for count in range(40):
                self.order(held, env, "say", text=f"order {count}")
        _, by = self.choose(self.helm(act))
        states = [state for state, _ in self.results()]
        flood = self.events.captain_orders.FLOOD
        self.assertEqual((states.count("done"), states.count("refused")), (flood, 40 - flood))
        self.assertEqual(by, "rule", "saying things is not a decision")

    def message(self, act: Callable[[dict, dict], object]) -> tuple[list[dict], str]:
        helm = self.helm(act)
        return helm.decide("message", "", {"inbox": "m1", "from": "person", "text": "hi"},
                           ["message", "pause", "resume", "stop", "say", "ask", "none"],
                           [{"verb": "none", "why": "rule"}])

    def test_a_person_s_hold_is_not_the_captain_s_to_lift_or_cover(self) -> None:
        home = talk.place(self.run_dir, "ORD", "ORD-01")
        talk.note(home, "stopped", by="person", why="wrong way")

        def act(held: dict, env: dict) -> None:
            self.order(held, env, "resume", slice="ORD-01", why="carry on")
            self.order(held, env, "pause", slice="ORD-01", why="hold it")
        _, by = self.message(act)
        self.assertEqual(by, "rule")
        whys = [why for _, why in self.results()]
        self.assertEqual(whys, ["only a person lifts a hold a person placed",
                                "a person holds ORD-01 already (stopped), and their hold stands until they lift it"])
        self.assertEqual(talk.halted(home)[:2], ("stopped", "person"))
        self.assertEqual(talk.pending(home), [], "nothing was sent to the slice")

    def test_a_message_to_a_slice_at_its_merge_is_held(self) -> None:
        self.stream.at_merge.add("ORD-01")
        _, by = self.message(lambda held, env: self.order(held, env, "message", slice="ORD-01", text="one more thing"))
        self.assertEqual(by, "captain")
        self.assertEqual(self.results()[0][0], "done")
        self.assertIn("held: ORD-01 is at its merge", self.results()[0][1])
        self.assertEqual(self.stream.held, [("ORD-01", "held: this slice is at its merge")])
        sent = talk.pending(talk.place(self.run_dir, "ORD", "ORD-01"))
        self.assertEqual([(one["from"], one["text"]) for one in sent], [("captain:ORD", "one more thing")])

    def test_a_routed_message_names_who_said_it_and_what_it_routes(self) -> None:
        asked = talk.send(talk.place(self.run_dir, "ORD", talk.CAPTAIN), "say", "tell ORD-02 to use euros")
        self.message(lambda held, env: self.order(held, env, "message", slice="ORD-02", of=asked["id"]))
        sent = talk.pending(talk.place(self.run_dir, "ORD", "ORD-02"))
        self.assertEqual([(one["from"], one["via"], one["of"], one["quote"]) for one in sent],
                         [("captain:ORD", "captain:ORD", asked["id"], "tell ORD-02 to use euros")])
        self.assertNotEqual(sent[0]["text"], "tell ORD-02 to use euros", "the captain's words are its own")

    def test_a_nudge_to_a_stuck_slice_is_the_captain_s_answer(self) -> None:
        helm = self.helm(lambda held, env: self.order(held, env, "message", slice="ORD-01", text="try the seed again",
                                                      interrupt=True))
        chosen, by = helm.decide("stuck", "ORD-01", {"slice": "ORD-01", "warnings": [{"kind": "quiet"}]},
                                 ["message", "pause", "stop", "park", "say", "ask", "none"],
                                 [{"verb": "none", "why": "rule"}])
        self.assertEqual((chosen, by), ([], "captain"))
        sent = talk.pending(talk.place(self.run_dir, "ORD", "ORD-01"))
        self.assertEqual([(one["mode"], one["text"]) for one in sent], [("interrupt", "try the seed again")])

    def test_every_answer_the_captain_gives_is_a_decision_for_a_person_to_review(self) -> None:
        helm = self.helm(lambda held, env: self.order(held, env, "allow", ask="ask-2", why="5433"))
        ask = {"id": "ask-2", "what": "question", "text": "Which port is the test database on?", "slice": "ORD-01"}
        answer = helm.ruling(ask, {"verb": "refuse", "ask": "ask-2", "why": "declined"})
        self.assertEqual((answer["action"], answer["by"]), ("accept", "captain"))
        self.assertTrue(answer["content"]["answer"].startswith("5433"))
        self.assertEqual(self.stream.answers, [("ORD-01", "Which port is the test database on?", "5433")])
        self.assertIn("recorded as decision captain-ORD-01-1", answer["why"])

    def test_a_write_outside_the_berth_is_not_the_captain_s_to_allow(self) -> None:
        helm = self.helm(lambda held, env: self.order(held, env, "allow", ask="ask-1", why="fine"))
        ask = {"id": "ask-1", "what": "permission", "text": "Write /etc/hosts", "slice": "ORD-01",
               "root": str(self.root), "tool": {"kind": "edit", "locations": ["/etc/hosts"]}}
        answer = helm.ruling(ask, {"verb": "refuse", "ask": "ask-1", "why": "outside the berth"})
        self.assertEqual((answer["allow"], answer["by"]), (False, "rule"))
        self.assertIn("not the captain's to allow", self.results()[0][1])
        read = dict(ask, tool={"kind": "read", "locations": [str(self.root / "specs/x.md")]})
        self.assertTrue(helm.ruling(read, {"verb": "refuse", "ask": "ask-1", "why": "x"})["allow"])


if __name__ == "__main__":
    unittest.main()
