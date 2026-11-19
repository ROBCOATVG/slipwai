"""What the hand-over's capture says and writes beyond the brief: a warning where an attached document names
requirement ids the project already specifies, and never a refusal; and, where the board can launch no agent,
the words and the document as an idea marked *not discussed* — with an agent, never without the conversation."""
from __future__ import annotations

import checkout_packages  # noqa: F401
from intake_fixture import CLEAR, HandoverTest

from slipwai import feedback
from slipwai.board_settings import Launch
from slipwai.intake_card import SCRIPT, handover_html
from slipwai.project import intake

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


class NoAgentTest(HandoverTest):
    """A board that can launch nothing: the launch a session would run through is one this machine has not got."""

    def setUp(self) -> None:
        super().setUp()
        self.launch = Launch("none", "None", (), "nothing here")
        self.talk = self.opened()

    def looked(self) -> dict:
        """The window's poll after the board has looked for an agent, which it does once, off the request."""
        self.get("/handover.json?since=0")
        self.assertTrue(self.talk.looked.wait(30), "the board never finished looking for an agent")
        return self.settle()

    def test_the_form_says_there_is_no_conversation_before_anything_is_typed(self) -> None:
        said = self.looked()
        self.assertTrue(said["raw"])
        self.assertEqual((said["turns"], said["open"], said["ready"]), ([], False, False))

    def test_words_and_a_document_are_captured_as_an_idea_marked_not_discussed(self) -> None:
        self.assertEqual(self.post("/handover/say", {"message": "Billing for clubs",
                                                     "document": {"name": "billing.md", "text": "# Billing\n"}}),
                         (200, "no agent"))
        said = self.settle()
        self.assertTrue(said["raw"])
        self.assertFalse(said["ready"], "nobody said it was one clear idea")
        self.assertEqual([t["role"] for t in said["turns"] if t["kind"] == "text"], ["person"],
                         "no turn stands in for an agent's")
        told = said["turns"][-1]
        self.assertEqual(told["kind"], "error")
        for words in ("no agent this board can run", "not discussed", "Settings tab", "/sail"):
            self.assertIn(words, told["text"])
        code, captured = self.post("/handover/capture", {})
        self.assertEqual(code, 200, captured)
        self.assertIn("captured docs/intake/billing-for-clubs, marked not discussed", captured)
        self.assertEqual(self.written(), ["billing-for-clubs/billing.md", "billing-for-clubs/brief.md",
                                          "billing-for-clubs/not-discussed"])
        mark = (self.root / "docs/intake/billing-for-clubs/not-discussed").read_text(encoding="utf-8")
        self.assertTrue(mark.startswith("not discussed\n"))
        idea = intake.ideas(self.root)[0]
        self.assertEqual((idea.state, idea.discussed), ("confirm", False), "captured, never confirmed")
        self.assertIn("not discussed", idea.detail)
        self.assertFalse((self.root / ".slipwai/handover/session").exists(), "no session was ever started")
        tab = self.get("/voyage")[1]
        self.assertIn("<b>billing-for-clubs</b> — confirm.", tab)
        self.assertIn("not discussed", tab)

    def test_nothing_said_is_nothing_to_capture(self) -> None:
        code, refused = self.post("/handover/capture", {})
        self.assertEqual(code, 400)
        self.assertIn("nothing to capture yet", refused)
        self.assertFalse((self.root / "docs/intake").exists())

    def test_new_scope_from_feedback_is_captured_raw_and_still_becomes_the_item(self) -> None:
        item = feedback.capture(self.root, "A reminder a week before.", {"from": "voyage"})
        item.fields.update(route="scope", proposed="2026-11-19T10:00:00Z")
        feedback.write(item)
        self.assertEqual(self.post("/feedback", {"verb": "confirm", "number": item.number})[0], 200)
        self.settle()
        code, captured = self.post("/handover/capture", {})
        self.assertEqual(code, 200, captured)
        self.assertEqual(feedback.find(self.root, item.number).fields["became"], "docs/intake/a-reminder-a-week-before")
        self.assertFalse(intake.ideas(self.root)[0].discussed)

    def test_an_agent_made_ready_since_takes_the_raw_capture_away(self) -> None:
        self.post("/handover/say", {"message": "Billing for clubs"})
        self.assertTrue(self.settle()["raw"])
        self.talk.launch = Launch("stand-in", "Stand-in", ("stand-in",), "")
        code, refused = self.post("/handover/capture", {})
        self.assertEqual(code, 400)
        self.assertIn("an agent can be launched now", refused)
        self.assertFalse(self.settle()["raw"])
        self.assertFalse((self.root / "docs/intake").exists())


class NoSkipTest(HandoverTest):
    def test_with_an_agent_the_conversation_is_the_only_way_in(self) -> None:
        self.get("/handover.json?since=0")
        self.assertTrue(self.talk.looked.wait(30))
        said = self.say("Billing for clubs", {"name": "billing.md", "text": "# Billing\n"})
        self.assertEqual((said["raw"], said["ready"]), (False, False))
        code, refused = self.post("/handover/capture", {})
        self.assertEqual(code, 400)
        self.assertIn("once the agent says the idea is ready", refused)
        self.assertFalse((self.root / "docs/intake").exists())
        self.say(CLEAR)
        self.assertEqual(self.post("/handover/capture", {})[0], 200)
        idea = intake.ideas(self.root)[0]
        self.assertTrue(idea.discussed)
        self.assertNotIn("not-discussed", "".join(self.written()))

    def test_the_page_offers_the_raw_capture_only_where_the_board_said_there_is_no_agent(self) -> None:
        self.assertIn("take.hidden = !(said.ready || (said.raw && said.open));", SCRIPT)
        self.assertIn("'Capture as an idea, not discussed'", SCRIPT)
        self.assertEqual(handover_html().count("data-capture"), 1, "one capture, and no button that skips")
        self.assertIn('<p class="alone" role="note" hidden>No agent can be launched from this board', handover_html())
        self.assertIn("alone.hidden = !said.raw;", SCRIPT)
        self.assertNotIn("skip", handover_html().lower())

    def test_a_document_cannot_be_called_the_mark(self) -> None:
        code, refused = self.post("/handover/say", {"message": "Billing",
                                                    "document": {"name": "not-discussed", "text": "discussed\n"}})
        self.assertEqual(code, 400)
        self.assertIn("a name intake keeps for itself", refused)


class SurfacesTest(HandoverTest):
    def test_the_surfaces_the_agent_named_are_kept_with_the_idea_as_a_suggestion(self) -> None:
        self.assertTrue(self.say(f"Billing for clubs.\nSurfaces it seems to touch: Member list; Checkout\n{CLEAR}")
                        ["ready"])
        code, captured = self.post("/handover/capture", {})
        self.assertEqual(code, 200, captured)
        self.assertIn("Kept as a suggestion for the storyboard: it seems to touch Member list; Checkout.", captured)
        idea = intake.ideas(self.root)[0]
        self.assertEqual(idea.surfaces, ("Member list", "Checkout"))
        self.assertIn(f"{idea.slug}/surfaces.json", self.written())
        self.assertIn("Seems to touch (a suggestion): Member list; Checkout", self.get("/voyage")[1])

    def test_an_agent_that_named_none_leaves_no_hint(self) -> None:
        self.say(CLEAR)
        self.assertNotIn("suggestion", self.post("/handover/capture", {})[1])
        self.assertEqual(intake.ideas(self.root)[0].surfaces, ())
        self.assertNotIn("surfaces.json", "".join(self.written()))
