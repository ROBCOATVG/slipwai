"""Approve and Reject on the card of a block that waits on a person's verdict on a mock-up.

manda's S97 waited on a person approving a founder-facing mock-up state, and its card could only chat. Now
the card writes the verdict's own record — `mock-states.md`, as the storyboard's Approve writes it — and
answers the park with a signed message from the person, which the real captain turns into the person's
`told` and the real harbourmaster clears the park on; or, past the decision ceiling, holds it, and the board
says so. Driven through the project's own `captain.py` and `harbourmaster.py`.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import checkout_packages  # noqa: F401
from board_fixture import BoardTest
from captain_fixture import AGENTS, WORKS, Fixture

from slipwai import logs, talk
from slipwai.cli_fleet import config
from slipwai.fleet import board
from slipwai.park_verdict import awaiting, give

CLAIMED, PARKED = "2026-11-21T09:00:00Z", "2026-11-21T16:12:42Z"
WHY = "ORD-01: held until a person approves a founder-facing mock state; run /mockups ordering to draw it."
PAGE = ('<!doctype html><title>What you told us</title><article class="state"><h2>listed</h2></article>'
        '<article class="state"><h2>skipped</h2></article>')


def drawn(root: Path) -> None:
    home = root / "specs/ordering/mockups"
    home.mkdir(parents=True, exist_ok=True)
    (home / "told-us.html").write_text(PAGE, encoding="utf-8")


class VerdictTest(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.fake = self.sail(WORKS)
        drawn(self.root)
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=CLAIMED),
                  logs.entry("parked", fairway="ORD", slice="ORD-01", why=WHY, cause="gate", t=PARKED))

    def record(self) -> str:
        return (self.root / "specs/ordering/mockups/mock-states.md").read_text(encoding="utf-8")

    def harbourmaster(self) -> list[logs.Entry]:
        """One pass of the real harbourmaster, lighting nothing (`boilers: 0`), and its receipts."""
        for name in ("harbourmaster.py", "lockfiles.py", "conflicts.py", "telegraph.py", "mender.py",
                     "capabilities.py"):
            shutil.copy(AGENTS / name, self.root / "scripts/agents" / name)
        done = subprocess.run([sys.executable, str(self.root / "scripts/agents/harbourmaster.py"), "--once",
                               "--no-fetch"], capture_output=True, text=True, cwd=self.root, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return [e for e in logs.harbour_fold(self.root) if e.kind == "cleared"]

    def test_approve_writes_the_storyboard_s_record_and_the_person_s_answer_clears_the_park(self) -> None:
        self.assertTrue(awaiting(self.root, "ordering"), "a page with no verdict waits on one")
        said = give(self.root, "ORD", "ORD-01", f"park:{PARKED}", "ordering", "approve")
        self.assertIn("ORD-01: sent", said)
        self.assertIn("## Surface: What you told us\n- listed — approved\n- skipped — approved", self.record())
        [message] = talk.inbox(talk.place(logs.run_dir(self.root), "ORD", "ORD-01"))
        self.assertEqual((message["from"], message["of"], message["kind"]), ("person", f"park:{PARKED}", "say"))
        self.assertTrue(message.get("sig"), "signed, as the card's own box signs what it sends")
        done = self.captain("ORD", self.fake)
        told = [e for e in self.read("ORD") if e.kind == "told"]
        self.assertEqual([(e.fields["by"], e.fields["slice"]) for e in told], [("person", "ORD-01")], done.stdout)
        self.assertTrue(str(told[0].fields["message"]).startswith("Approved the drawn mock-up states of ordering"))
        self.budget(minutes=5, boilers=0)
        self.assertEqual([str(e.fields["parked"]) for e in self.harbourmaster()], [PARKED])
        self.assertFalse(awaiting(self.root, "ordering"), "the drawing has its verdict now")

    def test_past_the_ceiling_the_verdict_is_written_and_its_answer_held_and_said_to_be(self) -> None:
        self.deck("ORD", logs.entry("decision", fairway="ORD", id="D1", what="a", t="2026-11-21T10:00:00Z"))
        give(self.root, "ORD", "ORD-01", f"park:{PARKED}", "ordering", "approve")
        self.captain("ORD", self.fake)
        self.budget(minutes=5, boilers=0, decision_ceiling=0)
        self.assertEqual(self.harbourmaster(), [], "past the ceiling, no answer clears the park")
        row = next(one for one in board(self.root, config(self.root))["inbox"]  # type: ignore[attr-defined]
                   if one["kind"] == "parked")
        self.assertIn("Your answer 'Approved the drawn mock-up states of ordering", row["action"]["held"])
        self.assertIn("is HELD: 1 unread decisions, ceiling 0", row["action"]["held"])

    def test_reject_needs_its_line_and_parks_every_drawn_state_with_it(self) -> None:
        with self.assertRaisesRegex(ValueError, "one line what to change"):
            give(self.root, "ORD", "ORD-01", f"park:{PARKED}", "ordering", "reject", "  ")
        give(self.root, "ORD", "ORD-01", f"park:{PARKED}", "ordering", "reject", "too dense for a founder")
        self.assertIn("- listed — parked: too dense for a founder", self.record())
        [message] = talk.inbox(talk.place(logs.run_dir(self.root), "ORD", "ORD-01"))
        self.assertIn("Rejected the drawn mock-up states of ordering: too dense for a founder", message["text"])

    def test_nothing_is_written_where_no_drawing_waits_or_the_park_is_not_a_verdict(self) -> None:
        give(self.root, "ORD", "ORD-01", f"park:{PARKED}", "ordering", "approve")
        with self.assertRaisesRegex(ValueError, "waits on a verdict: run `/mockups ordering`"):
            give(self.root, "ORD", "ORD-01", f"park:{PARKED}", "ordering", "approve")
        self.deck("ORD", logs.entry("parked", fairway="ORD", slice="ORD-02", why="ORD-02: the gate stayed red",
                                    cause="gate", t="2026-11-21T17:00:00Z"))
        with self.assertRaisesRegex(ValueError, "does not wait on a mock-up verdict"):
            give(self.root, "ORD", "ORD-02", "park:2026-11-21T17:00:00Z", "ordering", "approve")


class CardTest(BoardTest):
    """The board's card offers the two buttons while a drawing waits, and its route writes the verdict."""

    def setUp(self) -> None:
        super().setUp()
        drawn(self.root)
        self.deck("ORD", logs.entry("parked", fairway="ORD", slice="ORD-01", why=WHY, cause="gate", t=PARKED))

    def test_the_card_offers_approve_and_reject_and_its_route_writes_the_record(self) -> None:
        from slipwai.board_read import read
        from slipwai.fleet_page import waiting_card
        found = read(self.root).fleet
        card = waiting_card(found, True, "")
        self.assertIn('data-park-verdict="approve"', card)
        self.assertIn(f'data-of="park:{PARKED}"', card)
        self.assertIn("these wait on one: specs/ordering/mockups/told-us.html", card, "it says what it is a verdict on")
        code, said = self.post("/park/verdict", {"fairway": "ORD", "slice": "ORD-01", "of": f"park:{PARKED}",
                                                 "feature": "ordering", "verdict": "approve"})
        self.assertEqual(code, 200, said)
        self.assertIn("— approved", (self.root / "specs/ordering/mockups/mock-states.md").read_text(encoding="utf-8"))
        card = waiting_card(read(self.root).fleet, True, "")
        self.assertNotIn('data-park-verdict="approve"', card, "nothing waits on a verdict any more")
        self.assertIn("Approve and Reject appear here once a drawing", card)
