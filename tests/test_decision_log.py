"""The decision log: every decision readable in one place, each with the read receipt the ceiling counts."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.decision_log import card, decisions, mark, parse
from slipwai.deck import entries

BOOK = """# Decisions

## D1 — Are the connector writes built?
- **Stage:** clarify · **Slice:** — · **When:** 2026-10-19T12:20:00Z · **Stream:** upstream
- **Question:** The PRD allows the writes "if used".
- **Options:** A — not built (recommended) · B — build both
- **Decision:** A — no connector write in this phase.
- **Why:** An invitation reaches the leaver. · **Read against:** non-goal 5
- **Decided by:** host (stage recommendation)
- **Status:** standing

## D7 — Does a settlement keep its answer?
- **Stage:** plan · **Slice:** L05 · **When:** 2026-10-21T11:16:44Z · **Stream:** ORD
- **Decision:** (a). The source alone settles it.
- **Why:** As D2.
"""


class LogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "specs/ordering").mkdir(parents=True)
        (self.root / "specs/ordering/decisions.md").write_text(BOOK, encoding="utf-8")
        self.deck = self.root / logs.deck_path("ordering", "ORD")
        self.deck.parent.mkdir(parents=True)
        lines = [logs.entry("question", fairway="ORD", slice="L05", id="L05-Q2", what="Which bank question?"),
                 logs.entry("decision", fairway="ORD", slice="L05", id="L05-Q1", what="D7 (a): source settles it",
                            decided_by="sail-decide-skipper"),
                 logs.entry("decision", fairway="ORD", slice="L05", id="L05-Q2", what="decide for me",
                            decided_by="human")]
        self.deck.write_text("".join(one.line() for one in lines), encoding="utf-8")

    def test_an_entry_reads_its_question_its_options_and_why_from_decisions_md(self) -> None:
        book = parse(BOOK)
        self.assertEqual(book["D1"]["title"], "Are the connector writes built?")
        self.assertEqual(book["D1"]["Options"], "A — not built (recommended) · B — build both")
        self.assertEqual(book["D1"]["Read against"], "non-goal 5")
        self.assertEqual(book["D1"]["Stream"], "upstream")

    def test_a_deck_decision_is_shown_as_its_decisions_md_entry(self) -> None:
        found = {one.number: one for one in decisions(self.root)}
        self.assertEqual(found["D7"].title, "Does a settlement keep its answer?")
        self.assertEqual(found["D7"].decision, "(a). The source alone settles it.")
        self.assertTrue(found["D7"].key.startswith("deck:ORD:"))
        self.assertFalse(found["D7"].read)

    def test_a_persons_own_answer_is_shown_with_the_question_it_answered_and_is_read(self) -> None:
        mine = next(one for one in decisions(self.root) if one.yours)
        self.assertEqual((mine.title, mine.decision, mine.read), ("Which bank question?", "decide for me", True))

    def test_a_decision_from_before_the_fleet_is_in_the_log_too(self) -> None:
        early = next(one for one in decisions(self.root) if one.number == "D1")
        self.assertEqual(early.key, "md:D1")
        self.assertEqual(early.parts["Why"], "An invitation reaches the leaver.")

    def test_mark_read_writes_the_deck_receipt_the_ceiling_counts(self) -> None:
        d7 = next(one for one in decisions(self.root) if one.number == "D7")
        mark(self.root, [d7.key, "md:D1"])
        found, _ = entries(self.root, "ORD", "ordering")
        self.assertEqual([e.fields["told"] for e in found if e.kind == "read"], [d7.when])
        self.assertTrue(all(one.read for one in decisions(self.root)))
        with self.assertRaises(ValueError):
            mark(self.root, ["../etc"])

    def test_a_berths_copy_adds_the_decisions_its_slice_took_since_it_branched(self) -> None:
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm",
                        "x"], check=True)
        berth = self.root.parent / f"{self.root.name}-L05"
        subprocess.run(["git", "-C", str(self.root), "worktree", "add", "-q", "-b", "slice/L05", str(berth)],
                       check=True)
        book = berth / "specs/ordering/decisions.md"
        book.write_text(BOOK + "\n## D9 — New in the berth?\n- **Decision:** yes.\n", encoding="utf-8")
        self.assertIn("D9", {one.number for one in decisions(self.root)})

    def test_the_card_counts_what_is_unread_and_offers_each_its_receipt(self) -> None:
        html, unread = card(self.root)
        self.assertEqual(unread, 2)
        self.assertIn('data-decision-read="md:D1"', html)
        self.assertIn("<b>Your answer:</b> decide for me", html)


if __name__ == "__main__":
    unittest.main()
