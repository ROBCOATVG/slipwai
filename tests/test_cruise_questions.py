"""Under `/cruise` the skipper answers a slice's questions; a person sees only what it cannot decide.

hr-test-2 had `.specify/cruise.json` saying `enabled: true, decide: recommended-first`, and three slices
parked on thirteen questions "for a person": the captain dispatched `/sail`, the ladder a person drives,
and nothing told the session it was cruising. Now the session is told, the captain puts any question a run
still stops on to `sail-decide-skipper` before anything is parked, and a slice that parked on questions
before that is answered at the next turn — its park cleared by the decisions themselves.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

import captain_fixture
import checkout_packages  # noqa: F401
import harbourmaster_fixture
from captain_fixture import WORKS

from slipwai import logs

#: A fake `/sail` that asks `Q1` until a `decision` carries it, then does the slice's work.
ASKS_UNTIL_DECIDED = f"""import sys, json, pathlib, datetime
slice_id, fairway = sys.argv[1], sys.argv[2]
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
lines = [json.loads(one) for one in path.read_text().splitlines()] if path.is_file() else []
if any(one.get("kind") == "decision" and one.get("id") == "Q1" for one in lines):
    exec({WORKS!r})
else:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({{"v": 1, "t": now, "kind": "question", "fairway": fairway, "slice": slice_id,
                                 "id": "Q1", "what": "sync or async pricing?"}}) + "\\n")
"""


def skipper(decides: bool = True) -> str:
    """A fake owner: argv `<slice> <fairway> <ids>`, a `decision` line per id — or nothing, `unavailable`."""
    return f"""import sys, json, pathlib, datetime
slice_id, fairway, ids = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
pathlib.Path("skipper-ran").write_text(sys.argv[3])
now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
if {decides!r}:
    with path.open("a", encoding="utf-8") as handle:
        for ident in ids:
            handle.write(json.dumps({{"v": 1, "t": now, "kind": "decision", "fairway": fairway, "slice": slice_id,
                                     "id": ident, "what": "D9: async", "decided_by": "sail-decide-skipper"}}) + "\\n")
"""


class CaptainTest(captain_fixture.Fixture):
    def cruise(self, enabled: bool = True) -> None:
        (self.root / ".specify").mkdir(exist_ok=True)
        (self.root / ".specify/cruise.json").write_text(
            json.dumps({"enabled": enabled, "decide": "recommended-first"}), encoding="utf-8")

    def sail_with(self, fairway: str, sail: str, owner: str) -> subprocess.CompletedProcess:
        path = self.root / "fake-skipper.py"
        path.write_text(owner, encoding="utf-8")
        return subprocess.run([sys.executable, str(self.script), fairway, "--once"], capture_output=True,
                              text=True, cwd=self.root, timeout=90,
                              env={**os.environ, "SLIPWAI_SAIL": sail,
                                   "SLIPWAI_SKIPPER": f"{sys.executable} {path}"})

    def test_a_question_a_cruising_run_stops_on_goes_to_the_skipper_and_the_slice_carries_on(self) -> None:
        self.cruise()
        self.grant("ORD-01")
        done = self.sail_with("ORD", self.sail(ASKS_UNTIL_DECIDED), skipper())
        lines = self.read("ORD")
        self.assertEqual([e for e in lines if e.kind == "parked"], [], done.stdout + done.stderr)
        decisions = [e for e in lines if e.kind == "decision"]
        self.assertEqual([(e.fields["id"], e.fields["decided_by"]) for e in decisions],
                         [("Q1", "sail-decide-skipper")])
        self.assertIn("ORD-01 is through its gate and merged", done.stdout)

    def test_a_question_the_skipper_cannot_decide_is_parked_for_a_person(self) -> None:
        self.cruise()
        done = self.sail_with("ORD", self.sail(ASKS_UNTIL_DECIDED), skipper(decides=False))
        self.assertTrue((self.root / "skipper-ran").is_file(), done.stdout)
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1, done.stdout)
        self.assertIn("Q1: sync or async pricing?", parked[0])

    def test_without_cruise_nobody_but_a_person_answers(self) -> None:
        self.cruise(enabled=False)
        self.sail_with("ORD", self.sail(ASKS_UNTIL_DECIDED), skipper())
        self.assertFalse((self.root / "skipper-ran").is_file())
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "parked"]), 1)

    def test_a_slice_already_parked_on_questions_is_answered_and_resumed_at_the_next_turn(self) -> None:
        """hr-test-2's L07, L09, L13 and L21 were parked on questions before the session was told it was
        cruising. A restart puts them to the skipper and carries each slice on, told the decisions."""
        self.cruise()
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="sync or async?",
                             t="2026-10-20T08:15:00Z"),
                  logs.entry("parked", fairway="ORD", slice="ORD-01", t="2026-10-20T08:16:00Z",
                             why="ORD-01 stops before the plan on one open product question for a person"))
        self.grant("ORD-01")
        done = self.sail_with("ORD", self.sail(WORKS), skipper())
        self.assertEqual((self.root / "skipper-ran").read_text(), "Q1", done.stdout + done.stderr)
        self.assertIn("ORD-01 is through its gate and merged", done.stdout)

    def test_a_question_the_skipper_left_open_is_not_put_to_it_again(self) -> None:
        self.cruise()
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="the API key?",
                             t="2026-10-20T08:15:00Z"),
                  logs.entry("parked", fairway="ORD", slice="ORD-01", t="2026-10-20T08:16:00Z", why="Q1"))
        self.sail_with("ORD", self.sail(WORKS), skipper(decides=False))
        (self.root / "skipper-ran").unlink()
        self.sail_with("ORD", self.sail(WORKS), skipper(decides=False))
        self.assertFalse((self.root / "skipper-ran").is_file(), "an `unavailable` stays the person's")
        self.assertEqual([e for e in self.read("ORD") if e.kind == "request"], [])


class HarbourmasterTest(harbourmaster_fixture.Fixture):
    def cleared(self) -> list[tuple[str, str]]:
        return [(str(e.fields["parked"]), str(e.fields["what"])) for e in self.harbour() if e.kind == "cleared"]

    def asked(self, *more: logs.Entry) -> None:
        self.deck("ordering", "ORD",
                  logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="?", t="2026-10-20T08:15:00Z"),
                  logs.entry("question", fairway="ORD", slice="ORD-01", id="Q2", what="?", t="2026-10-20T08:15:01Z"),
                  logs.entry("parked", fairway="ORD", slice="ORD-01", why="two questions", t="2026-10-20T08:16:00Z"),
                  *more)

    def test_a_slice_s_park_on_questions_clears_once_every_question_is_decided(self) -> None:
        self.asked(logs.entry("decision", fairway="ORD", id="Q1", what="a", t="2026-10-20T08:20:00Z",
                              decided_by="sail-decide-skipper"))
        self.run_once()
        self.assertEqual(self.cleared(), [], "Q2 is still open")
        self.deck("ordering", "ORD", logs.entry("decision", fairway="ORD", id="Q2", what="b",
                                                t="2026-10-20T08:21:00Z", decided_by="sail-decide-skipper"))
        self.run_once()
        self.assertEqual(self.cleared(), [("2026-10-20T08:16:00Z", "answered by decisions Q1, Q2")])

    def test_a_park_on_something_other_than_questions_is_still_a_person_s(self) -> None:
        self.deck("ordering", "ORD",
                  logs.entry("parked", fairway="ORD", slice="ORD-01", why="the gate stayed red",
                             t="2026-10-20T08:16:00Z"),
                  logs.entry("decision", fairway="ORD", id="Q1", what="a", t="2026-10-20T08:20:00Z"))
        self.run_once()
        self.assertEqual(self.cleared(), [])


    def test_a_park_written_after_every_question_was_decided_is_not_cleared_by_them(self) -> None:
        """hr-test-2's L21: D45-D50 answered its questions, then it parked "implementation held by D50 until
        L09 is on main" — and two seconds later that park was cleared as answered by those same decisions."""
        self.asked(logs.entry("decision", fairway="ORD", id="Q1", what="a", t="2026-10-20T08:20:00Z"),
                   logs.entry("decision", fairway="ORD", id="Q2", what="b", t="2026-10-20T08:21:00Z"))
        self.run_once()
        first = self.cleared()
        self.assertEqual(first, [("2026-10-20T08:16:00Z", "answered by decisions Q1, Q2")])
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", slice="ORD-01",
                                                why="held by D2 until ORD-02 is on main", t="2026-10-20T09:00:00Z"))
        self.run_once()
        self.assertEqual(self.cleared(), first, "a park on something else is still a person's")

if __name__ == "__main__":  # pragma: no cover
    unittest.main()
