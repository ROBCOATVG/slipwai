"""The surfaces an idea seems to touch: read off one line of the agent's last reply, and written with the idea as
a hint that says in itself it is a suggestion."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.intake_document import named
from slipwai.intake_surfaces import ASK, HEAD, LONG, MOST, suggested
from slipwai.intake_talk import READY, ROLE
from slipwai.project import intake


class SuggestedTest(unittest.TestCase):
    def test_the_names_are_the_ones_on_the_line_in_the_order_given_once_each(self) -> None:
        reply = f"It is one idea.\n{HEAD} Member list; `Checkout`;  member   LIST ; ;Receipt.\n{READY}"
        self.assertEqual(suggested(["An earlier reply.", reply]), ["Member list", "Checkout", "Receipt"])

    def test_no_line_or_an_earlier_replys_line_is_no_suggestion(self) -> None:
        self.assertEqual(suggested([]), [])
        self.assertEqual(suggested([f"One idea. {READY}"]), [])
        self.assertEqual(suggested([f"{HEAD} Checkout\n{READY}", f"On reflection, none. {READY}"]), [],
                         "what the agent said last is what it thinks")
        self.assertEqual(suggested([f"I would not say '{HEAD} Checkout' here."]), [], "the line starts with it")

    def test_what_an_agent_says_is_held_to_a_few_short_names(self) -> None:
        many = "; ".join(f"Screen {n}" for n in range(40))
        self.assertEqual(len(suggested([f"{HEAD} {many}"])), MOST)
        long = suggested([f"{HEAD} {'x' * 500}; ../../etc/passwd; a\tb\x00c"])
        self.assertEqual(len(long[0]), LONG)
        self.assertEqual(long[1], "../../etc/passwd", "a name is kept as text and is never a path the board opens")
        self.assertEqual(long[2], "a b c", "one line of plain text")

    def test_the_role_asks_for_the_line_and_says_it_is_a_suggestion(self) -> None:
        self.assertIn(ASK, ROLE)
        self.assertIn(f"`{HEAD} <name>; <name>`", ROLE)
        self.assertIn("a suggestion the storyboard stage\nstarts from and may change", ROLE)
        self.assertIn("name them on one\nline just before that last line", ROLE, "ahead of the line the page waits for")
        self.assertTrue(ROLE.index(READY) < ROLE.index(HEAD), "asked once the ready line has been named")


class HintTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())

    def test_the_hint_is_written_beside_the_brief_and_says_what_it_is(self) -> None:
        folder, _ = intake.capture(self.root, "Billing for clubs", surfaces=["Member list", "Checkout"])
        held = json.loads((folder / intake.SURFACES).read_text(encoding="utf-8"))
        self.assertEqual(held["suggested"], ["Member list", "Checkout"])
        self.assertIs(held["authoritative"], False)
        self.assertEqual(held["by"], "hand-over")
        self.assertIn("suggestion", held["note"])
        self.assertEqual(intake.suggested_surfaces(self.root, "billing-for-clubs"), ("Member list", "Checkout"))
        idea = intake.ideas(self.root)[0]
        self.assertEqual(idea.surfaces, ("Member list", "Checkout"))

    def test_no_suggestion_writes_no_file_and_a_file_that_does_not_read_is_no_suggestion(self) -> None:
        folder, _ = intake.capture(self.root, "Billing for clubs")
        self.assertFalse((folder / intake.SURFACES).exists())
        self.assertEqual(intake.suggested_surfaces(self.root, "billing-for-clubs"), ())
        for text in ("not json", "[]", '{"suggested": "Checkout"}', '{"suggested": [1, {"a": 2}, "Checkout"]}'):
            (folder / intake.SURFACES).write_text(text, encoding="utf-8")
            self.assertIn(intake.suggested_surfaces(self.root, "billing-for-clubs"), ((), ("Checkout",)))
        self.assertEqual(intake.suggested_surfaces(self.root, "no-such-idea"), ())

    def test_no_document_can_be_called_the_hint_and_the_intake_page_documents_it(self) -> None:
        with self.assertRaises(ValueError):
            named("surfaces.json")
        page = intake.readme()
        self.assertIn("`surfaces.json`", page)
        self.assertIn('"authoritative": false', page)
        self.assertIn("never edited", page)


if __name__ == "__main__":
    unittest.main()
