"""What a fairway owes a person at a boundary: messages unread, decisions unreviewed, waits overrun.

All three rules exist because the first attempt failed the same way three times: something was true and
nothing said so. "Read the inbox between stages" was documented and under load did not happen. 125
decisions were taken and 105 never read, and nobody saw the backlog accumulate because nothing counted. A
wait with no bound looked exactly like a run that had stopped, which is how seventeen iterations produced
no log line and nobody noticed for a fortnight.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC)


def at(minutes_ago: int) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


class InboxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts/agents").mkdir(parents=True)
        shutil.copy(ROOT / "assets/toolkit/scripts/agents/inbox.py", self.tree / "scripts/agents/inbox.py")
        (self.tree / "project.json").write_text("{}", encoding="utf-8")
        (self.tree / ".slipwai/logs/ordering").mkdir(parents=True)
        spec = importlib.util.spec_from_file_location("inbox", self.tree / "scripts/agents/inbox.py")
        assert spec is not None and spec.loader is not None
        self.inbox = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(self.inbox)

    def write(self, lines: list[dict]) -> None:
        path = self.tree / ".slipwai/logs/ordering/ORD.jsonl"
        path.write_text("".join(json.dumps({"v": 1, **line}) + "\n" for line in lines), encoding="utf-8")

    def told(self, minutes_ago: int, message: str = "which store?") -> dict:
        return {"kind": "told", "fairway": "ORD", "t": at(minutes_ago), "message": message}

    def read_of(self, told: dict) -> dict:
        return {"kind": "read", "fairway": "ORD", "t": at(0), "told": told["t"]}

    def decision(self, minutes_ago: int) -> dict:
        return {"kind": "decision", "fairway": "ORD", "t": at(minutes_ago), "id": "D-ORD-01", "what": "x"}

    def test_park_waits_are_timed_until_the_original_fairway_receipt_arrives(self) -> None:
        park = {"kind": "parked", "fairway": "ORD", "t": at(120), "why": "decide"}
        other = {"kind": "cleared", "fairway": "BIL", "parked": at(120), "t": at(1), "what": "x"}
        self.write([park, {"kind": "heartbeat", "fairway": "ORD", "t": at(1)}, other])
        state = self.inbox.owed("ORD", NOW)
        self.assertEqual(state["parks"][0]["waited"], 120)
        self.assertEqual(len(state["overdue_parks"]), 1)
        self.assertTrue(state["forced"])
        self.write([park, {**other, "fairway": "ORD"}])
        self.assertEqual(self.inbox.owed("ORD", NOW)["parks"], [])
        self.assertFalse(self.inbox.owed("ORD", NOW)["forced"])

    def test_a_message_with_no_receipt_is_unread(self) -> None:
        self.write([self.told(5)])
        self.assertEqual(len(self.inbox.owed("ORD", NOW)["unread"]), 1)

    def test_the_receipt_is_the_told_s_own_timestamp_not_a_count(self) -> None:
        """A count would read as answered the moment anything was answered."""
        first, second = self.told(10, "one"), self.told(5, "two")
        self.write([first, second, self.read_of(first)])
        unread = self.inbox.owed("ORD", NOW)["unread"]
        self.assertEqual([line["message"] for line in unread], ["two"])

    def test_a_message_inside_its_bound_does_not_force_a_boundary(self) -> None:
        self.write([self.told(5)])
        self.assertFalse(self.inbox.owed("ORD", NOW)["forced"])

    def test_a_message_past_its_bound_forces_one(self) -> None:
        """A wait with no bound looks exactly like a run that has stopped."""
        self.write([self.told(120)])
        state = self.inbox.owed("ORD", NOW)
        self.assertTrue(state["forced"])
        self.assertEqual(len(state["overrun"]), 1)

    def test_an_answered_message_never_forces_one_however_old(self) -> None:
        old = self.told(600)
        self.write([old, self.read_of(old)])
        self.assertFalse(self.inbox.owed("ORD", NOW)["forced"])

    def test_decisions_a_person_has_not_read_are_counted(self) -> None:
        self.write([self.decision(5) for _ in range(3)])
        self.assertEqual(len(self.inbox.owed("ORD", NOW)["unreviewed"]), 3)

    def test_under_the_ceiling_the_fairway_runs_on(self) -> None:
        self.write([self.decision(5) for _ in range(3)])
        state = self.inbox.owed("ORD", NOW)
        self.assertFalse(state["over_ceiling"])
        self.assertFalse(state["forced"])

    def test_over_the_ceiling_the_fairway_parks(self) -> None:
        """125 decisions with 105 unread is not a record of judgement, it is a backlog of it."""
        self.write([self.decision(5) for _ in range(12)])
        state = self.inbox.owed("ORD", NOW)
        self.assertTrue(state["over_ceiling"])
        self.assertTrue(state["forced"])

    def test_the_bound_and_the_ceiling_come_from_harbour_json(self) -> None:
        (self.tree / "harbour.json").write_text(
            json.dumps({"decision_ceiling": 2, "wait_bound": 5}), encoding="utf-8")
        self.write([self.decision(1) for _ in range(3)])
        self.assertTrue(self.inbox.owed("ORD", NOW)["over_ceiling"])

    def test_a_project_with_no_harbour_file_still_has_both_rules(self) -> None:
        """The file is the answer; the defaults keep the rules working rather than conditional on it."""
        self.assertEqual(self.inbox.settings(), (self.inbox.DEFAULT_CEILING, self.inbox.DEFAULT_WAIT))

    def test_an_unreadable_instant_never_forces_a_boundary(self) -> None:
        """A boundary forced on the strength of a timestamp nobody can parse is a boundary nobody can explain."""
        self.write([{"kind": "told", "fairway": "ORD", "t": "whenever", "message": "x"}])
        self.assertFalse(self.inbox.owed("ORD", NOW)["forced"])

    def test_a_log_line_nobody_can_read_stops_the_read(self) -> None:
        """Reading past it would report an empty inbox that is not empty."""
        (self.tree / ".slipwai/logs/ordering/ORD.jsonl").write_text("not json\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as refused:
            self.inbox.owed("ORD", NOW)
        self.assertIn("is not JSON", str(refused.exception))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
