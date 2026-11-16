"""The keel's reader of what a captain decided: each event, how it was closed, its orders and their results.

What is proved: an event closed by the captain lists its orders with the program's answers, one closed by the
rule says why, one still open reads as open, a torn file costs nothing but itself, and `since` keeps the rows
to a day.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.captain_decisions import decided, off, tally
from slipwai.logs import run_dir


class ReaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.events = run_dir(self.root) / "events" / "ORD"
        self.orders = run_dir(self.root) / "orders" / "ORD"
        self.events.mkdir(parents=True)
        self.orders.mkdir(parents=True)

    def put(self, path: Path, body: object) -> None:
        path.write_text(json.dumps(body), encoding="utf-8")

    def event(self, ident: str, t: str, kind: str, closed: dict | None) -> None:
        self.put(self.events / f"{ident}.json", {"v": 1, "id": ident, "t": t, "kind": kind, "slice": "ORD-01",
                                                 "facts": {}, "may": ["start"], "default": []})
        if closed is not None:
            self.put(self.events / f"{ident}.closed.json", {"v": 1, "id": ident, **closed})

    def test_each_event_is_read_with_how_it_closed_and_what_was_ordered(self) -> None:
        self.event("e1", "2026-11-16T09:00:00Z", "choose-next",
                   {"by": "captain", "why": "start ORD-02", "cost": {"seconds": 4.5, "ended": "finished"}})
        self.event("e2", "2026-11-16T10:00:00Z", "gate-failed",
                   {"by": "rule", "why": "the captain declined: nothing to add", "cost": {"seconds": 1.0}})
        self.event("e3", "2026-11-16T11:00:00Z", "stuck", None)
        self.event("e0", "2026-11-15T23:00:00Z", "stuck", {"by": "rule", "why": "old"})
        self.put(self.orders / "o1.json", {"v": 1, "id": "o1", "event": "e1", "verb": "start", "slice": "ORD-02"})
        self.put(self.orders / "o1.result.json", {"state": "done", "why": ""})
        self.put(self.orders / "o2.json", {"v": 1, "id": "o2", "event": "e1", "verb": "start", "slice": "BIL-01"})
        self.put(self.orders / "o2.result.json", {"state": "refused", "why": "BIL-01 is not cleared"})
        (self.events / "torn.json").write_text("{", encoding="utf-8")
        rows = decided(self.root, "ORD", since="2026-11-16T00:00:00Z")
        self.assertEqual([(row["id"], row["by"]) for row in rows], [("e3", "open"), ("e2", "rule"), ("e1", "captain")])
        self.assertEqual([(one["verb"], one["slice"], one["state"]) for one in rows[2]["orders"]],
                         [("start", "ORD-02", "done"), ("start", "BIL-01", "refused")])
        self.assertEqual(rows[1]["why"], "the captain declined: nothing to add")
        self.assertEqual(tally(rows), {"events": 3, "by_captain": 1, "by_rule": 1, "refused": 1, "seconds": 5.5})

    def test_a_stream_with_no_captain_agent_has_nothing_to_read(self) -> None:
        self.assertEqual(decided(self.root, "BIL"), [])
        self.assertIsNone(off(self.root, "BIL"))

    def test_a_captain_turned_off_says_why(self) -> None:
        self.put(self.events / "agent-off.json", {"v": 1, "why": "it changed the project"})
        self.assertEqual((off(self.root, "ORD") or {}).get("why"), "it changed the project")
        self.assertEqual(decided(self.root, "ORD"), [], "not an event")


if __name__ == "__main__":
    unittest.main()
