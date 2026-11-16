"""Layer 3, through the whole captain: a captain agent that misbehaves leaves a stream running on its rules.

The captain program run as a project runs it, with a stand-in captain agent (`fixtures/captain_stand_in.py`)
named in `SLIPWAI_CAPTAIN` and told how to misbehave. Three slices of one stream, any of which may start, and
one slot: so every turn is a choice, put to the agent as a `choose-next` event. What is proved: a start of a
slice clearance does not allow, more starts than slots, a retry past the attempts ceiling, an agent that dies
mid-decision and one silent past its bound are each refused or timed out, and the slice the rule would have
started is the one that runs; an agent that cannot be run at all for a whole voyage leaves a stream that still
finishes; and over the protocol the captain's own session is held open across events, its conversation
written like a slice's.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import checkout_packages  # noqa: F401
from captain_fixture import Fixture
from test_drive import STAND_IN

from slipwai import logs, talk

CAPTAIN = f"{sys.executable} {Path(__file__).resolve().parent / 'fixtures' / 'captain_stand_in.py'}"
#: Three slices of one stream that may each start now, each gated by its demo alone.
CHART = "slices:\n" + "".join(f"  ORD-0{n}:\n    fairway: ORD\n    sets: []\n    steers_by: []\n" for n in (1, 2, 3))
SAIL = """import sys, json, pathlib, datetime
slice_id, fairway = sys.argv[1], sys.argv[2]
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
if not pathlib.Path("no-demo").exists():
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"v": 1, "t": now, "kind": "demo", "fairway": fairway, "slice": slice_id,
                                 "verdict": "accepted"}) + "\\n")
"""


class AgentBase(Fixture):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "specs/ordering/chart.yaml").write_text(CHART, encoding="utf-8")
        self.settings(bound=20)

    def settings(self, **captain: object) -> None:
        held = json.loads((self.root / "harbour.json").read_text(encoding="utf-8"))
        (self.root / "harbour.json").write_text(json.dumps({**held, "captain": {"agent": True, **captain}}),
                                                encoding="utf-8")

    def granted(self, *slices: str) -> None:
        for slice_id in slices:
            self.harbour(logs.entry("granted", harbour=True, fairway="ORD", request=f"merge-{slice_id}",
                                    what="merge", slice=slice_id, commit="a1b2c3d"))

    def turn(self, mode: str, *argv: str, captain: str = CAPTAIN, **env: str) -> str:
        clean = {key: value for key, value in os.environ.items() if key not in ("SLIPWAI_ACP", "SLIPWAI_CAPTAIN")}
        done = subprocess.run([sys.executable, str(self.script), "ORD", *(argv or ("--once",))], cwd=self.root,
                              capture_output=True, text=True, timeout=180,
                              env={**clean, "SLIPWAI_SAIL": self.sail(SAIL), "SLIPWAI_CAPTAIN": captain,
                                   "STAND_IN_CAPTAIN": mode, **env})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout

    def claimed(self) -> list[str]:
        return [str(e.fields["slice"]) for e in self.read("ORD") if e.kind == "claimed"]

    def results(self) -> list[dict]:
        folder = logs.run_dir(self.root) / "orders" / "ORD"
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("*.result.json"))]

    def closed(self) -> list[dict]:
        folder = logs.run_dir(self.root) / "events" / "ORD"
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("*.closed.json"))]


class AgentTest(AgentBase):
    def test_the_stand_in_s_choice_is_the_one_that_starts(self) -> None:
        self.granted("ORD-01")
        said = self.turn("today")
        self.assertIn("ORD-01 is through its gate and merged", said)
        self.assertEqual([one["by"] for one in self.closed()], ["captain"])
        self.assertEqual([one["state"] for one in self.results()], ["done"])

    def test_a_start_clearance_does_not_allow_is_refused_and_the_rule_starts_the_first(self) -> None:
        self.granted("ORD-01")
        said = self.turn("uncleared", STAND_IN_TARGET="BIL-02")
        self.assertEqual(self.claimed(), ["ORD-01"], said)
        self.assertEqual([(one["state"], one["why"][:40]) for one in self.results()],
                         [("refused", "BIL-02 is not one clearance lets start n")])
        self.assertEqual(self.closed()[0]["by"], "rule")
        self.assertIn("choose-next decided by the rule", said)

    def test_more_starts_than_slots_are_refused_past_the_first(self) -> None:
        self.granted("ORD-01")
        self.turn("greedy", STAND_IN_TARGET="BIL-02")
        self.assertEqual(self.claimed(), ["ORD-01"])
        states = [(one["state"], one["why"]) for one in self.results()]
        self.assertEqual(states[0][0], "done")
        self.assertEqual([why for state, why in states[1:3]], ["the stream has 1 free slot(s), and they are taken"] * 2)
        self.assertEqual(states[3][0], "refused")
        self.assertEqual(self.closed()[0]["by"], "captain", "its one allowed start was its decision")

    def test_a_retry_past_the_attempts_ceiling_is_refused_and_the_slice_parks(self) -> None:
        self.budget(minutes=5, attempts=0)
        self.settings(bound=20)
        (self.root / "no-demo").write_text("", encoding="utf-8")
        self.turn("retry")
        kinds = [e.kind for e in self.read("ORD")]
        self.assertEqual((kinds.count("claimed"), kinds.count("parked")), (1, 1))
        gate = [one for one in self.closed() if one["by"] == "rule"]
        self.assertTrue(gate)
        self.assertIn(("refused", "`retry` is not an order this gate-failed event takes: park, say, ask, none"),
                      [(one["state"], one["why"]) for one in self.results()])

    def test_an_agent_that_dies_mid_decision_is_the_rule_for_that_decision(self) -> None:
        self.granted("ORD-01")
        said = self.turn("die")
        self.assertIn("ORD-01 is through its gate and merged", said)
        self.assertEqual([(one["by"], one["why"]) for one in self.closed()],
                         [("rule", "the captain gave no order this event takes")])

    def test_an_agent_silent_past_its_bound_is_ended_and_the_record_says_rule(self) -> None:
        self.settings(bound=2)
        self.granted("ORD-01")
        said = self.turn("silent")
        self.assertIn("ORD-01 is through its gate and merged", said)
        record = self.closed()[0]
        self.assertEqual((record["by"], record["cost"]["ended"]), ("rule", "bound"))
        self.assertGreaterEqual(record["cost"]["seconds"], 2)

    def test_an_agent_unavailable_for_a_whole_voyage_leaves_a_stream_that_finishes(self) -> None:
        self.granted("ORD-01", "ORD-02", "ORD-03")
        said = self.turn("today", "--interval", "0.2", captain="/nowhere/no-such-captain")
        merged = [str(e.fields["slice"]) for e in self.read("ORD") if e.kind == "merged"]
        self.assertEqual(merged, ["ORD-01", "ORD-02", "ORD-03"], said)
        self.assertEqual({one["by"] for one in self.closed()}, {"rule"})
        self.assertTrue(all("cannot be run" in one["why"] for one in self.closed()))

    def test_a_message_to_the_stream_is_put_to_its_captain(self) -> None:
        self.granted("ORD-01")
        home = talk.place(logs.run_dir(self.root), "ORD", talk.CAPTAIN)
        sent = talk.send(home, "say", "start with ORD-01, please")
        self.turn("today")
        events = [json.loads(path.read_text(encoding="utf-8"))
                  for path in sorted((logs.run_dir(self.root) / "events" / "ORD").glob("*.json"))
                  if not path.name.endswith(".closed.json") and path.name != "state.json"]
        message = next(one for one in events if one["kind"] == "message")
        self.assertEqual({key: message["facts"][key] for key in ("inbox", "from", "text")},
                         {"inbox": sent["id"], "from": "person", "text": "start with ORD-01, please"})
        self.assertIsNone(message["slice"])
        receipt = next(one for one in talk.receipts(home) if one["id"] == sent["id"])
        self.assertEqual(receipt["state"], "unaddressed", "the rule routes nothing, and it is not put again")

    def test_over_the_protocol_the_captain_s_session_is_held_open_across_events(self) -> None:
        self.granted("ORD-01", "ORD-02")
        clean = {key: value for key, value in os.environ.items() if key not in ("SLIPWAI_SAIL", "SLIPWAI_CAPTAIN")}
        done = subprocess.run([sys.executable, str(self.script), "ORD", "--interval", "0.2"], cwd=self.root,
                              capture_output=True, text=True, timeout=240, env={**clean, "SLIPWAI_ACP": STAND_IN})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([one["by"] for one in self.closed()][:2], ["captain", "captain"], done.stdout)
        thread = talk.thread(talk.place(logs.run_dir(self.root), "ORD", talk.CAPTAIN))
        self.assertEqual([one["loaded"] for one in thread if one["kind"] == "session"], [False],
                         "one session for every event")
        self.assertGreaterEqual(sum(1 for one in thread if one["kind"] == "turn" and one["state"] == "ended"), 2)


if __name__ == "__main__":
    import unittest
    unittest.main()
