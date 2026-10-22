"""A park as a record: the optional fields a `parked` line may carry, and the shape each is held to.

Split from `test_logs.py` at its budget.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401

from slipwai import logs


class RecordTest(unittest.TestCase):
    """A park is a record: a cause, a time it lifts by itself, the needs it waits on, and what follows.

    Eleven parks on the recap voyage were three causes, eight of them a session limit written as
    "`/sail` exited 1" and retried into the ground. A board can group what it can read, and nothing can
    group a paragraph.
    """

    def test_a_park_written_before_parks_had_a_cause_still_reads_and_is_other(self) -> None:
        line = json.dumps({"v": logs.V, "t": logs.now(), "kind": "parked", "fairway": "library",
                           "why": "LB3: `/sail` exited 1. That was the last of 3 run(s)"})
        self.assertEqual(logs.cause_of(logs.read(line)), "other")

    def test_a_full_record_round_trips(self) -> None:
        needs = [{"what": "context: catch-up on LB6..LB10 in docs/event-model/model.yaml", "by": "fleet",
                  "check": {"kind": "text", "path": "docs/event-model/model.yaml", "has": "context: catch-up"}},
                 {"what": "decide whether LB13 follows", "by": "person"}]
        written = logs.entry("parked", fairway="library", slice="LB6", why="LB6 waits on a host change (D32)",
                             cause="host", needs=needs, then="re-dispatch LB6 in catch-up at T001")
        back = logs.read(written.line())
        self.assertEqual(back.fields["cause"], "host")
        self.assertEqual(back.fields["needs"], needs)
        self.assertEqual(back.fields["then"], "re-dispatch LB6 in catch-up at T001")

    def test_a_cause_outside_the_set_is_refused_both_ways(self) -> None:
        with self.assertRaises(logs.Unreadable) as refused:
            logs.entry("parked", fairway="library", why="x", cause="tired")
        self.assertIn("limit, host, question", str(refused.exception))
        line = json.dumps({"v": logs.V, "t": logs.now(), "kind": "parked", "fairway": "library", "why": "x",
                           "cause": "tired"})
        with self.assertRaises(logs.Unreadable):
            logs.read(line)

    def test_an_until_is_an_instant_in_the_log_s_own_format(self) -> None:
        logs.entry("parked", fairway="library", why="x", cause="limit", until="2026-10-21T20:40:00Z")
        with self.assertRaises(logs.Unreadable) as refused:
            logs.entry("parked", fairway="library", why="x", cause="limit", until="9:40pm")
        self.assertIn("2026-10-21T20:40:00Z", str(refused.exception))

    def test_a_need_says_what_and_a_check_is_one_of_two_kinds(self) -> None:
        for bad in ([{"by": "person"}], "fix main", [{"what": "x", "by": "robot"}],
                    [{"what": "x", "check": {"kind": "shell", "run": "rm -rf"}}],
                    [{"what": "x", "check": {"kind": "text", "path": "a.yaml"}}],
                    [{"what": "x", "check": {"kind": "make"}}]):
            with self.subTest(bad=bad), self.assertRaises(logs.Unreadable):
                logs.entry("parked", fairway="library", why="x", cause="host", needs=bad)
        logs.entry("parked", fairway="library", why="x", cause="host",
                   needs=[{"what": "x", "check": {"kind": "make", "target": "check-model"}}])

    def test_a_limit_or_a_time_ahead_is_paused_and_a_host_change_is_not(self) -> None:
        limit = logs.entry("parked", fairway="library", slice="LB3", why="refused", cause="limit",
                           until="2026-10-21T20:40:00Z")
        timed = logs.entry("parked", fairway="library", slice="LB9", why="budget", cause="budget",
                           until="2026-10-21T18:00:00Z")
        host = logs.entry("parked", fairway="library", slice="LB6", why="D32", cause="host")
        found = logs.paused([limit, timed, host], now="2026-10-21T17:05:00Z")
        self.assertEqual([str(e.fields["slice"]) for e in found], ["LB3", "LB9"])
        self.assertEqual([str(e.fields["slice"]) for e in logs.paused([limit, timed, host],
                                                                      now="2026-10-21T19:00:00Z")], ["LB3"])

    def test_a_need_met_is_a_harbour_receipt_naming_the_park_and_the_need(self) -> None:
        self.assertEqual(logs.HARBOUR_KINDS["need-met"], ("fairway", "parked", "need", "how"))


if __name__ == "__main__":
    unittest.main()
