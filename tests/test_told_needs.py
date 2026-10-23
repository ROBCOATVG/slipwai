"""A hand-back that names a shared surface is a need, not a note — slice 20.4 of the feedback-points plan.

recap's second day: 59 `told` lines, and the four that gated every story — a JWT library, two realm users,
the one-line wiring at the composition root — were written on the 21st and filed on the board under *Notes:
nothing here blocks a stream; Done clears one*. Each later slice asked again and shipped a stub, and the stub
is what Try it showed. Here the same lines read as they did, and one rewritten with needs is grouped under
*Waiting on you*, ticked when trunk gains the line, and gone when the last is met.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai import fleet, logs
from slipwai.bridge_page import inbox_rows, wait_group_of
from slipwai.fleet_page import live_sub

FIXTURE = Path(__file__).resolve().parent / "fixtures/recap-try"
EVENING = datetime(2026, 10, 22, 19, 0, tzinfo=UTC)
TOLD_AT = "2026-10-21T11:01:00Z"
NEEDS: list[dict[str, Any]] = [{"what": "jose in apps/recap-api/package.json", "by": "fleet",
          "check": {"kind": "text", "path": "apps/recap-api/package.json", "has": '"jose"'}},
         {"what": "ada and ines in docker/keycloak/realms/customers.json", "by": "fleet",
          "check": {"kind": "text", "path": "docker/keycloak/realms/customers.json", "has": '"ada"'}},
         {"what": "the catch-up routes bound to LB3's userinfo adapter at the composition root", "by": "person"}]


def copied() -> Path:
    root = Path(tempfile.mkdtemp())
    shutil.copytree(FIXTURE / ".slipwai", root / ".slipwai")
    return root


def with_a_hand_back(root: Path) -> Path:
    """The day's library log with LB3's 11:01 note rewritten as the need it was."""
    path = root / ".slipwai/logs/001-audiobook-recap/library.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(logs.entry("told", fairway="library", slice="LB3", by="session", t=TOLD_AT,
                                message="For the host: wiring the catch-up routes to the userinfo adapter is one "
                                        "line at the composition root, and the JWT library is the manifest's",
                                needs=NEEDS).line())
    return root


class AsItWasTest(unittest.TestCase):
    def test_the_day_s_told_lines_read_unchanged_and_none_is_a_need(self) -> None:
        found: Any = fleet.board(copied(), {"boilers": 3}, now=EVENING)
        self.assertEqual(found["unreadable"], {})
        told = [row for row in found["inbox"] if row["kind"] == "told"]
        self.assertTrue(told, "the day's notes to the host are still waiting")
        self.assertFalse(any(row.get("needs") for row in told))
        self.assertTrue(all(wait_group_of(row) == "note" for row in told))


class WithNeedsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = with_a_hand_back(copied())
        self.found: Any = fleet.board(self.root, {"boilers": 3}, now=EVENING)

    def row(self) -> dict[str, Any]:
        return next(row for row in self.found["inbox"] if row["kind"] == "told" and row["t"] == TOLD_AT)

    def test_the_hand_back_is_an_inbox_row_with_its_needs_and_is_grouped(self) -> None:
        row = self.row()
        self.assertEqual([need["what"] for need in row["needs"]], [need["what"] for need in NEEDS])
        self.assertEqual([need["met"] for need in row["needs"]], ["no", "no", "no"])
        self.assertEqual(row["needs"][0]["how"], "apps/recap-api/package.json holds '\"jose\"'")
        self.assertEqual((row["grouped"], row["cause"], row["slice"]), ("yes", "host", "LB3"))

    def test_it_joins_the_groups_under_waiting_on_you_by_its_needs_and_is_not_counted_twice(self) -> None:
        groups = [one for one in self.found["groups"] if one.get("source") == "told"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["slices"], ["LB3"])
        self.assertEqual(groups[0]["paused"], "no")
        self.assertEqual(len(groups[0]["needs"]), 3)
        told_rows = [row for row in self.found["inbox"] if row["kind"] == "told" and row.get("grouped") == "yes"]
        self.assertEqual(len(told_rows), 1)
        # Counted once, as its group, beside the day's other notes and questions — never as a note as well.
        alone = [row for row in self.found["inbox"]
                 if row["kind"] in ("told", "question") and row.get("grouped") != "yes"]
        expected = len([one for one in self.found["groups"] if one.get("paused") != "yes"]) + len(alone)
        self.assertIn(f"{expected} waiting on you", live_sub(self.found))

    def test_the_bridge_lists_it_under_needs_with_no_done_until_met(self) -> None:
        shown = inbox_rows([self.row()], controls=True, streams={})
        self.assertIn("Needs <span", shown)
        self.assertNotIn("Notes <span", shown)
        self.assertNotIn('data-dismiss="library"', shown, "Done is not offered while a need stands")
        self.assertIn("0 of 3 on trunk", shown)
        self.assertIn('data-need="2"', shown, "the person's need has its tick")
        self.assertIn("ticks itself when apps/recap-api/package.json holds", shown)

    def test_the_harbourmaster_s_receipts_tick_it_and_the_last_takes_it_off_the_board(self) -> None:
        harbour = self.root / ".slipwai/logs/harbour/vol_rmt_l07721.jsonl"
        with harbour.open("a", encoding="utf-8") as handle:
            handle.write(logs.entry("need-met", harbour=True, fairway="library", parked=TOLD_AT, need=0,
                                    how="trunk at 4e150b81").line())
        found: Any = fleet.board(self.root, {"boilers": 3}, now=EVENING)
        row = next(row for row in found["inbox"] if row["kind"] == "told" and row["t"] == TOLD_AT)
        self.assertEqual([need["met"] for need in row["needs"]], ["yes", "no", "no"])
        with harbour.open("a", encoding="utf-8") as handle:
            handle.write(logs.entry("told-met", harbour=True, fairway="library", told=TOLD_AT,
                                    what="needs met: 3 of 3").line())
        found = fleet.board(self.root, {"boilers": 3}, now=EVENING)
        self.assertFalse([row for row in found["inbox"] if row["kind"] == "told" and row["t"] == TOLD_AT])
        self.assertFalse([one for one in found["groups"] if one.get("source") == "told"])


if __name__ == "__main__":
    unittest.main()
