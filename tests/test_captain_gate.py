"""What closes a slice, and what gets it to trunk. The second half of the captain's suite.

Both halves are about the same inversion as `test_captain.py` — the log is the state — applied to the two
places it was not: a turn that wrote none of what closes a slice, and a merge nobody performed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

import checkout_packages  # noqa: F401
from captain_fixture import SLICES, WORKS, Fixture, fake_drive  # noqa: F401

from slipwai import fleet, logs
from slipwai.bridge_page import page


class GateTest(Fixture):
    """What closes a slice: every mark the chart says it sets, and a demo, written during this turn.

    This is the fault that started slice 7.8. In the first real run `/sail` printed a help message, exited
    0, and the captain wrote `claimed`, then `request: merge`, and said the slice was through its gate —
    with nothing else in the log at all.
    """

    def attempts(self, many: int) -> None:
        held = json.loads((self.root / "harbour.json").read_text(encoding="utf-8"))
        (self.root / "harbour.json").write_text(json.dumps({**held, "attempts": many}), encoding="utf-8")

    def test_a_drive_that_exits_cleanly_having_written_nothing_parks_and_asks_for_no_merge(self) -> None:
        done = self.captain("ORD", self.sail("import sys\nsys.exit(0)\n"))
        self.assertEqual([e for e in self.read("ORD") if e.kind == "request"], [], done.stdout)
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1)
        self.assertIn("Placed", parked[0])

    def test_a_demo_with_no_mark_set_parks_naming_the_mark_the_chart_promised(self) -> None:
        done = self.captain("ORD", self.sail(fake_drive(marks=False)))
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("sets Placed", parked[0], done.stdout)
        self.assertIn("no `mark-set` for Placed", parked[0])

    def test_a_mark_set_with_no_demo_parks_saying_nobody_watched_it(self) -> None:
        done = self.captain("ORD", self.sail(fake_drive(demo=False)))
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("no `demo` line", parked[0], done.stdout)

    def test_a_slice_that_sets_no_mark_passes_on_its_demo_alone(self) -> None:
        """One rule, not a special case: every mark in `sets`, which is vacuous when that is empty."""
        self.deck("BIL", logs.entry("mark-set", fairway="BIL", slice="BIL-01", mark="Charged"),
                  logs.entry("claimed", fairway="BIL", slice="BIL-01"),
                  logs.entry("merged", fairway="BIL", slice="BIL-01", commit="a1b2c3d"))
        self.grant("BIL-02")
        done = self.captain("BIL", self.sail(WORKS))
        self.assertIn("BIL-02", done.stdout)
        self.assertIn("merged", done.stdout)

    def test_the_lines_have_to_be_this_turn_s(self) -> None:
        """Without it a retry passes on the previous turn's lines, which is the same fault as a cursor that
        outlives its log: a reader reporting a run that did not happen."""
        self.deck("ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"),
                  logs.entry("demo", fairway="ORD", slice="ORD-01", verdict="accepted"))
        done = self.captain("ORD", self.sail("import sys\nsys.exit(0)\n"))
        self.assertEqual([e for e in self.read("ORD") if e.kind == "request"], [], done.stdout)
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "parked"]), 1)

    def test_an_open_question_parks_with_the_question_and_not_with_a_missing_mark(self) -> None:
        """A stage that stopped to ask is not a stage that wrote nothing."""
        asks = """import sys, json, pathlib, datetime
slice_id, fairway = sys.argv[1], sys.argv[2]
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
with path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps({"v": 1, "t": now, "kind": "question", "fairway": fairway, "slice": slice_id,
                             "id": "Q1", "what": "sync or async pricing?"}) + "\\n")
"""
        done = self.captain("ORD", self.sail(asks))
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1, done.stdout)
        self.assertIn("Q1: sync or async pricing?", parked[0], done.stderr)
        self.assertIn("cruise-tell ORD", parked[0])
        self.assertNotIn("no `mark-set`", parked[0])
        self.assertEqual([e for e in self.read("ORD") if e.kind == "request"], [])

    def test_the_answer_to_the_park_becomes_the_decision_and_the_slice_resumes(self) -> None:
        """`/cruise-tell` clears the park; the captain writes the `decision` carrying the question's id, so
        the resumed `/sail` reads it in the log and clearance stops saying *awaiting decision*."""
        at = "2026-10-13T09:00:00Z"
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="sync or async?"),
                  logs.entry("parked", fairway="ORD", why="ORD-01 is awaiting a decision — Q1", t=at))
        self.harbour(logs.entry("cleared", harbour=True, fairway="ORD", parked=at, what="async, via the port"))
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(WORKS))
        decisions = [e for e in self.read("ORD") if e.kind == "decision"]
        self.assertEqual([(e.fields["id"], e.fields["what"]) for e in decisions], [("Q1", "async, via the port")],
                         done.stdout)
        self.assertEqual(decisions[0].fields.get("decided_by"), "human")
        self.assertIn("Q1 on ORD-01 is decided", done.stdout)
        self.assertIn("ORD-01 is through its gate and merged", done.stdout)

    def test_a_demo_sent_back_is_driven_again_rather_than_parked(self) -> None:
        """The person who sent it back is present and has just written notes. Parking would ask them to come
        back and restart a fairway before anything acted on them."""
        once = f"""import pathlib
tried = pathlib.Path("tried")
first = not tried.is_file()
tried.write_text("x")
exec({fake_drive("behaviour")!r} if first else {fake_drive()!r})
"""
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(once))
        verdicts = [e.fields["verdict"] for e in self.read("ORD") if e.kind == "demo"]
        self.assertEqual(verdicts, ["behaviour", "accepted"], done.stdout)
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "request"]), 1)

    def test_a_demo_sent_back_past_the_bound_parks_naming_the_verdict_and_the_count(self) -> None:
        self.attempts(1)
        done = self.captain("ORD", self.sail(fake_drive("implementation")))
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "demo"]), 2, done.stdout)
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("implementation", parked[0])
        self.assertIn("last of 2 run(s)", parked[0])

    def test_attempts_of_zero_is_one_run_and_no_retry(self) -> None:
        self.attempts(0)
        self.captain("ORD", self.sail(fake_drive("behaviour")))
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "demo"]), 1)


class FixTrunkTest(Fixture):
    """A trunk this fairway reddened is worth more than any slice it could start.

    The harbourmaster wrote the `merged` line for the commit that went red, so it knows whose it was and
    sends `fix-trunk`. Captains elsewhere keep building throughout, and that work is not wasted, because a
    sibling is cleared by a mark being set and not by a merge.
    """

    def order(self, slice_id: str = "ORD-01", fairway: str = "ORD", job: str = "audit") -> None:
        self.harbour(logs.entry("fix-trunk", harbour=True, fairway=fairway, slice=slice_id,
                                commit="a1b2c3d4", job=job))

    def test_the_fix_is_taken_before_any_new_slice(self) -> None:
        """ORD-02 is what split order would give it next. The order outranks split order."""
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="a1b2c3d4"))
        self.order()
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(WORKS))
        claimed = [e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"]
        self.assertEqual(claimed[-1], "ORD-01", done.stdout)
        self.assertIn("trunk is red", done.stdout)

    def test_an_order_another_fairway_was_sent_is_not_this_one_s(self) -> None:
        self.order(slice_id="BIL-01", fairway="BIL")
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(WORKS))
        claimed = [e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"]
        self.assertEqual(claimed, ["ORD-01"], done.stdout)
        self.assertNotIn("trunk is red", done.stdout)

    def test_an_order_already_answered_by_a_later_merge_is_not_taken_again(self) -> None:
        """The fix reaches trunk the way everything else does, so the line that says any slice is done is
        the line that says this one is."""
        self.order()
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="fixed001"))
        done = self.captain("ORD", self.sail(WORKS))
        self.assertNotIn("trunk is red", done.stdout)
        # Back to split order, which here has nothing ready — `Placed` was never set, because the lines
        # above are seeded rather than driven. What matters is that it went looking rather than re-driving
        # a slice it has already fixed.
        self.assertIn("ORD-02 waits on", done.stdout)
        self.assertEqual([e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"], ["ORD-01"])





class IdleFairwayTest(Fixture):
    """The actual clearance script drives the board; no mocked ready set can prove these agree."""

    def setUp(self) -> None:
        super().setUp()
        self.chart = self.root / "specs/ordering/chart.yaml"
        self.chart.write_text(json.dumps({"slices": {
            "ORD-00": {"fairway": "ORD", "observed": True, "sets": ["Known"]},
            "ORD-01": {"fairway": "ORD", "sets": ["Placed"]},
            "ORD-02": {"fairway": "ORD", "steers_by": ["Placed"]},
            "ORD-03": {"fairway": "ORD", "steers_by": ["Known"]},
            "ORD-04": {"fairway": "ORD"},
            "ORD-05": {"fairway": "ORD", "steers_by": ["NotSet"]},
            "BIL-01": {"fairway": "BIL"},
        }}), encoding="utf-8")
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc"))

    def board(self) -> dict:
        return fleet.board(self.root)

    def test_a_merged_fairway_with_three_cleared_slices_is_idle_with_three_waiting(self) -> None:
        row = self.board()["berths"][0]
        self.assertEqual((row["state"], row["waiting"]), ("idle", 3))
        rendered = page(self.board(), {})
        self.assertIn("data-state=\"idle\"", rendered)
        self.assertIn("<th>Waiting</th>", rendered)

    def test_claimed_and_merged_work_is_excluded_and_finished_means_no_work_left(self) -> None:
        for slice_id in ("ORD-02", "ORD-03", "ORD-04"):
            self.deck("ORD", logs.entry("claimed", fairway="ORD", slice=slice_id),
                      logs.entry("merged", fairway="ORD", slice=slice_id, commit="abc"))
        row = self.board()["berths"][0]
        self.assertEqual((row["state"], row["waiting"]), ("finished", 0))

    def test_a_missing_read_port_is_visible_and_never_guesses_finished(self) -> None:
        script = self.root / "scripts/agents/clearance.py"
        script.write_text("raise AssertionError('an old script must never run an install')\n", encoding="utf-8")
        board = self.board()
        self.assertEqual(board["berths"][0]["state"], "unknown")
        self.assertEqual(board["berths"][0]["waiting"], fleet.NOTHING)
        self.assertIn("offline JSON query port", board["unreadable"]["clearance"])
        self.assertIn("Waiting counts unavailable", page(board, {}))
        self.assertIn("slipwai migrate", page(board, {}))

    def test_each_feature_reports_its_own_three_ready_slices(self) -> None:
        chart = self.root / "specs/payments/chart.yaml"
        chart.parent.mkdir()
        chart.write_text(json.dumps({"slices": {
            "PAY-01": {"fairway": "PAY"}, "PAY-02": {"fairway": "PAY"},
            "PAY-03": {"fairway": "PAY"}, "PAY-04": {"fairway": "PAY"},
        }}), encoding="utf-8")
        path = self.root / logs.deck_path("payments", "PAY")
        path.parent.mkdir(parents=True)
        path.write_text(logs.entry("claimed", fairway="PAY", slice="PAY-01").line()
                        + logs.entry("merged", fairway="PAY", slice="PAY-01", commit="def").line(), encoding="utf-8")
        rows = self.board()["berths"]
        self.assertEqual({row["feature"]: (row["state"], row["waiting"]) for row in rows},
                         {"ordering": ("idle", 3), "payments": ("idle", 3)})

    def test_a_query_refusal_preserves_the_actual_log_fault_and_repair(self) -> None:
        path = self.root / logs.deck_path("ordering", "ORD")
        with path.open("a", encoding="utf-8") as handle:
            handle.write('{"v": 99, "kind": "mark-set"}\n')
        board = self.board()
        self.assertIn("says v99", board["unreadable"]["clearance"])
        self.assertIn("Run `slipwai upgrade`", board["unreadable"]["clearance"])

    def test_the_json_query_without_yaml_refuses_without_installing_anything(self) -> None:
        script = self.root / "scripts/agents/clearance.py"
        done = subprocess.run([sys.executable, "-B", "-S", str(script), "--json"],
                              capture_output=True, text=True, timeout=30,
                              env={**os.environ, "PYTHONPATH": "", "PIP_NO_INDEX": "1"})
        self.assertNotEqual(done.returncode, 0)
        error = json.loads(done.stdout)["error"]
        self.assertIn("PyYAML is not installed", error)
        self.assertIn("python3 -m pip install PyYAML", error)


if __name__ == "__main__":
    unittest.main()
