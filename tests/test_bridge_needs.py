"""A need ticked from the page: the one route the Fleet tab added.

Split from `test_bridge.py`, which is at its claimed budget; the fixture is the same served board.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import logs


class NeedRouteTest(BoardTest):
    def test_a_need_ticked_from_the_page_is_a_need_done_line_and_only_for_a_need_the_park_lists(self) -> None:
        at = "2026-10-21T16:03:00Z"
        self.deck("ORD", logs.entry("parked", fairway="ORD", slice="ORD-01", why="ORD-01: D32", cause="host",
                                    needs=[{"what": "decide whether LB13 follows", "by": "person"}], t=at))
        code, said = self.post("/need", {"fairway": "ORD", "parked": at, "need": 0})
        self.assertEqual(code, 200, said)
        self.assertEqual([(e.fields["parked"], e.fields["need"]) for e in self.read("ORD") if e.kind == "need-done"],
                         [(at, 0)])
        code, said = self.post("/need", {"fairway": "ORD", "parked": at, "need": 4})
        self.assertEqual(code, 400)
        self.assertIn("no need 4", said)


if __name__ == "__main__":
    unittest.main()
