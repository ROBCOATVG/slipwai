"""What the drawing stage found, read for a person: the review's counts and Blockers, and the open questions.

The files are an agent's, so the reading is held across the shapes an agent writes — a tagged list, a table,
findings under a severity heading, a summary sentence — and to one rule where the shape is not found: it says
so, rather than reading nothing as clean.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.review_reading import gate, reading

REVIEW = """# Review of the handed-over mock-ups

84 findings: 14 Blockers, 40 Should-address, 30 Nice-to-have.

## Booking page
- [Blocker] No error state for a declined card
- **Should-address:** The empty state says nothing
- Nice-to-have — rounder corners

## Calendar
| Severity | Finding |
|---|---|
| Blocker | Two bookings can overlap |
| Nice-to-have | Colour |

## Rota
### Blockers
- Nobody owns the rota
### Should-address
- Labels
"""

RESEARCH = """# Research

## Booking
What members expect.

### Questions
- Who can cancel a booking?
- [x] Do members pay? Answered: no, it is free.
- Is there a waiting list
  when every boat is out?
"""


class ReadingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.home = self.root / "specs/001-boats/mockups"
        self.home.mkdir(parents=True)

    def write(self, name: str, text: str) -> None:
        (self.home / name).write_text(text, encoding="utf-8")

    def test_the_counts_the_blockers_and_where_each_is_are_read_from_every_shape_an_agent_writes(self) -> None:
        self.write("review.md", REVIEW)
        found = reading(self.root, "001-boats")
        self.assertEqual(found.counts, {"blocker": 14, "should": 40, "nice": 30}, "the summary the file states")
        self.assertEqual([(one.where, one.text) for one in found.blockers],
                         [("Booking page", "No error state for a declined card"),
                          ("Calendar", "Two bookings can overlap"), ("Rota", "Nobody owns the rota")])
        self.assertEqual(gate(self.root, "001-boats"), "the review has 14 Blocker findings")

    def test_an_open_question_is_one_not_marked_answered_and_a_long_one_is_read_whole(self) -> None:
        self.write("research.md", RESEARCH)
        found = reading(self.root, "001-boats")
        self.assertEqual(found.questions, ["Who can cancel a booking?",
                                           "Is there a waiting list when every boat is out?"])
        self.assertEqual(found.answered, 1)
        self.assertIn("2 questions in the research only you can answer are open", gate(self.root, "001-boats"))

    def test_a_file_whose_shape_is_not_found_is_unreadable_and_unread_is_not_clean(self) -> None:
        self.write("review.md", "We looked at the pages and they are mostly fine, with some worries.\n")
        self.write("research.md", "# Research\n\n## Questions\nWe wonder about payments, and about who pays.\n")
        found = reading(self.root, "001-boats")
        self.assertFalse(found.review_read)
        self.assertFalse(found.research_read)
        said = gate(self.root, "001-boats")
        self.assertIn("review.md could not be read", said)
        self.assertIn("research.md could not be read", said)

    def test_no_review_and_no_questions_is_nothing_to_discuss(self) -> None:
        self.assertEqual(gate(self.root, "001-boats"), "", "no review written, no research written")
        self.write("research.md", "# Research\n\n## Questions\nNone.\n")
        self.write("review.md", "# Review\n\n- [Should-address] A label\n- [Nice-to-have] A colour\n")
        self.assertEqual(gate(self.root, "001-boats"), "")


if __name__ == "__main__":
    unittest.main()
