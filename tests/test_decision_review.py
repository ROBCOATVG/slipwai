"""What the review of the decision log changed that nothing held: each case here goes red with its fix undone.

The count on the Decisions tab as the page draws it and as the poll repaints it, least sure first where the
newest is not the least sure, a slice's own panel in that order, the box that opens from an address, and the
status filter the script reads. `test_decision_cards` holds the rest of that review.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai.decision_cards import SCRIPT, listing, slice_panel
from slipwai.decision_log import decisions, mark
from slipwai.feedback_card import SCRIPT as FEEDBACK_SCRIPT
from slipwai.voyage_page import SCRIPT as PAGE_SCRIPT

ENTRY = ("## D{n} — Does a settlement keep its answer?\n- **Stage:** plan · **Slice:** L05 · "
         "**When:** 2026-11-1{n}T10:00:00Z · **Stream:** ORD\n- **Decision:** (a).\n"
         "- **Confidence:** {sure} · **Would reverse if:** somebody says so.\n- **Status:** {status}\n\n")


def book(root: Path, *entries: str) -> None:
    (root / "specs/ordering").mkdir(parents=True, exist_ok=True)
    (root / "specs/ordering/decisions.md").write_text("# Decisions\n\n" + "".join(entries), encoding="utf-8")


class TabCountTest(BoardTest):
    def test_the_tab_and_the_poll_count_what_nobody_has_read_not_what_awaits_confirmation(self) -> None:
        book(self.root, ENTRY.format(n=1, sure="medium", status="standing"),
             ENTRY.format(n=2, sure="low", status="awaiting human confirmation"),
             ENTRY.format(n=3, sure="high", status="awaiting human confirmation"))
        self.assertEqual(json.loads(self.get("/live.json")[1])["decisions"], 2,
                         "two unread and less than sure, one of them awaiting; the high one is not counted")
        self.assertIn('<span class="count" data-decisions-unread>2 to review</span>', self.get("/voyage")[1])
        self.assertIn("count('[data-decisions-unread]', found.decisions, 'to review');", PAGE_SCRIPT)


class LeastSureFirstTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        book(self.root, ENTRY.format(n=1, sure="low", status="standing"),
             ENTRY.format(n=2, sure="high", status="standing"))

    def order(self, html: str) -> list[str]:
        return sorted(("D1", "D2"), key=lambda number: html.index(f'data-key="md:{number}"'))

    def test_the_older_decision_comes_first_where_it_is_the_one_less_sure(self) -> None:
        self.assertEqual(self.order(listing(decisions(self.root))), ["D1", "D2"])

    def test_a_slice_s_own_panel_is_unread_first_and_least_sure_first_among_them(self) -> None:
        self.assertEqual(self.order(slice_panel(self.root, "L05")[0]), ["D1", "D2"])
        mark(self.root, ["md:D1"])
        self.assertEqual(self.order(slice_panel(self.root, "L05")[0]), ["D2", "D1"], "what was read drops below")


class ScriptTest(unittest.TestCase):
    def test_the_feedback_box_opens_on_the_context_an_address_carries(self) -> None:
        read = FEEDBACK_SCRIPT[FEEDBACK_SCRIPT.index("new URLSearchParams(location.search)"):]
        read = read[:read.index("document.addEventListener('click'")]
        self.assertIn("else if (key.startsWith('feedback-')) given[key.slice(9)] = value;", read)
        self.assertIn("if (!ask && !Object.keys(given).length) return;", read)
        self.assertIn("open(given, ask);", read)

    def test_the_decisions_script_filters_by_status_and_a_confirmed_card_changes_its_own(self) -> None:
        self.assertIn("const FILTERS = ['stream', 'slice', 'by', 'status'];", SCRIPT)
        self.assertIn("card.dataset.status = 'confirmed';", SCRIPT)


if __name__ == "__main__":
    unittest.main()
