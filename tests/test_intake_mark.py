"""An idea nobody talked through: the mark `capture` writes beside its brief, and everything that reads it — the
list of ideas, the page a project keeps about intake, and the page and script that assess one."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT as TOOLKIT
from slipwai.intake_document import named
from slipwai.project import intake


class MarkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())

    def test_an_idea_is_discussed_unless_capture_is_told_otherwise(self) -> None:
        shaped, _ = intake.capture(self.root, "Billing for clubs")
        raw, _ = intake.capture(self.root, "Export the members", discussed=False)
        self.assertFalse((shaped / intake.UNDISCUSSED).exists())
        self.assertEqual((raw / intake.UNDISCUSSED).read_text(encoding="utf-8").splitlines()[0], "not discussed")
        found = {one.slug: one for one in intake.ideas(self.root)}
        self.assertEqual((found["billing-for-clubs"].discussed, found["billing-for-clubs"].detail),
                         (True, "waiting for a yes that this is a new feature"))
        self.assertFalse(found["export-the-members"].discussed)
        self.assertEqual(found["export-the-members"].detail,
                         "waiting for a yes that this is a new feature; not discussed with an agent")

    def test_the_mark_stays_through_the_yes_and_the_assessment(self) -> None:
        raw, _ = intake.capture(self.root, "Export the members", discussed=False)
        (raw / intake.CONFIRMED).write_text("yes\nperson\n", encoding="utf-8")
        idea = intake.ideas(self.root)[0]
        self.assertEqual((idea.state, idea.discussed), ("assessing", False))
        self.assertIn("not discussed", idea.detail)

    def test_no_document_can_be_called_the_mark(self) -> None:
        for name in ("not-discussed", "NOT-DISCUSSED"):
            with self.assertRaises(ValueError):
                named(name)

    def test_the_intake_page_and_the_assessment_say_what_the_mark_means_and_what_to_do(self) -> None:
        self.assertIn("`not-discussed` is there where the board could launch no agent", intake.readme())
        page = (TOOLKIT / "commands/assess.md").read_text(encoding="utf-8")
        for said in ("**Where `not-discussed` is in that directory, nobody shaped this idea.**",
                     "say whether it is one feature or several",
                     "the verdict\n   is `needs-clarification`",
                     "do not\n   guess your way to a `go`",
                     "Leave `not-discussed` where it is"):
            self.assertIn(said, page)
        script = (TOOLKIT / "scripts/agents/assess.py").read_text(encoding="utf-8")
        self.assertIn('(folder / "not-discussed").is_file()', script)
        self.assertLess(script.index('(folder / "confirmed").is_file()'), script.index('"not-discussed"'),
                        "said for an idea a person has agreed to, as the session is about to start")


if __name__ == "__main__":
    unittest.main()
