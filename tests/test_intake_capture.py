"""What the hand-over's capture says and writes beyond the brief: a warning where an attached document names
requirement ids the project already specifies, and never a refusal."""
from __future__ import annotations

import checkout_packages  # noqa: F401
from intake_fixture import CLEAR, HandoverTest

from slipwai.intake_card import SCRIPT, handover_html

SPEC = "# Demo\n\n- **FR-001**: System MUST take a card payment.\n- **FR-002**: System MUST send a receipt.\n"


class OverlapAtCaptureTest(HandoverTest):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "specs/001-demo/spec.md").write_text(SPEC, encoding="utf-8")

    def test_an_id_the_specification_holds_is_listed_beside_the_capture_and_the_idea_is_still_captured(self) -> None:
        said = self.say(CLEAR, {"name": "billing.md", "text": "FR-002 again, FR-009 new.\n"})
        self.assertIn("FR-002 (billing.md; in specs/001-demo)", said["overlap"])
        self.assertNotIn("FR-009", said["overlap"])
        self.assertIn("a match on the ids only", said["overlap"])
        self.assertTrue(said["ready"], "a warning takes no capture away")
        code, captured = self.post("/handover/capture", {})
        self.assertEqual(code, 200, captured)
        self.assertIn("FR-002 (billing.md; in specs/001-demo)", captured, "said again with the capture")
        self.assertEqual(len(self.written()), 2, "the brief and the document, as without a warning")
        self.assertEqual(self.settle()["overlap"], "", "and let go of with the conversation")

    def test_a_reopened_board_still_says_it_and_start_again_stops(self) -> None:
        self.say("Billing", {"name": "billing.md", "text": "FR-001\n"})
        self.assertIn("FR-001", self.opened().said()["overlap"])
        self.post("/handover/reset", {})
        self.assertEqual(self.settle()["overlap"], "")

    def test_no_document_or_no_shared_id_is_no_warning(self) -> None:
        self.assertEqual(self.say("Like FR-001, but for clubs.")["overlap"], "", "words are not a document")
        self.assertEqual(self.say("", {"name": "new.md", "text": "FR-300 and FR-301.\n"})["overlap"], "")

    def test_the_page_draws_the_warning_as_text_beside_the_capture_and_leaves_the_box_alone(self) -> None:
        self.assertIn('<p class="warn" role="note" hidden></p>', handover_html())
        self.assertIn("warn.textContent = said.overlap", SCRIPT)
        self.assertNotIn("innerHTML", SCRIPT)
        self.assertEqual(SCRIPT.count("box.value = "), 1, "still cleared only by a send the board accepted")
