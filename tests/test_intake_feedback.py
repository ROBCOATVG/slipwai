"""Feedback's *New scope* on the board: the hand-over's own conversation, started from the item's words, and the
item confirmed as the idea that conversation captures."""
from __future__ import annotations

import checkout_packages  # noqa: F401
from intake_fixture import CLEAR, HandoverTest

from slipwai import feedback
from slipwai.feedback_card import SCRIPT
from slipwai.intake_feedback import WHERE

WORDS = "A reminder a week before the final day."
SLUG = "a-reminder-a-week-before-the-final-day"


class NewScopeTest(HandoverTest):
    def proposed(self, words: str = WORDS, route: str = "scope") -> feedback.Item:
        """A record as triage leaves it."""
        item = feedback.capture(self.root, words, {"from": "voyage"})
        item.fields.update(route=route, about="a reminder", proposed="2026-11-19T10:00:00Z")
        feedback.write(item)
        return item

    def confirm(self, item: feedback.Item, route: str = "") -> tuple[int, str]:
        return self.post("/feedback", {"verb": "confirm", "number": item.number, "route": route})

    def test_confirming_new_scope_opens_the_hand_over_from_the_items_words_and_writes_no_idea(self) -> None:
        item = self.proposed()
        code, said = self.confirm(item)
        self.assertEqual(code, 200, said)
        self.assertIn(f"feedback {item.number} is in the hand-over on {WHERE}", said)
        talked = self.settle()
        self.assertEqual((talked["turns"][0]["role"], talked["turns"][0]["text"]), ("person", WORDS))
        self.assertTrue(talked["turns"][1]["text"].startswith(f"Role given. Drawn: {WORDS}"),
                        "the same session, over the protocol, with the role ahead of the item's words")
        self.assertEqual(talked["feedback"], item.number)
        self.assertFalse((self.root / "docs/intake").exists(), "nothing is captured by confirming")
        self.assertEqual(feedback.find(self.root, item.number).state, "proposed", "and the item is not handed on yet")

    def test_a_document_rides_along_and_the_captured_idea_is_what_the_item_became(self) -> None:
        item = self.proposed(route="note")
        self.assertEqual(self.confirm(item, "scope")[0], 200, "routed as new scope by the person")
        self.settle()
        self.say(f"Only by email. {CLEAR}", {"name": "reminders.md", "text": "# Reminders\n"})
        code, said = self.post("/handover/capture", {})
        self.assertEqual(code, 200, said)
        self.assertIn(f"Feedback {item.number} is recorded as having become it.", said)
        self.assertEqual(self.written(), [f"{SLUG}/brief.md", f"{SLUG}/conversation.md", f"{SLUG}/reminders.md"])
        read = feedback.find(self.root, item.number)
        self.assertEqual((read.state, read.fields["became"], read.route), ("confirmed", f"docs/intake/{SLUG}", "scope"))
        self.assertEqual(read.fields["route"], "note", "what triage proposed is kept beside what the person chose")
        self.assertEqual(self.settle()["feedback"], "", "the conversation is let go of with its idea")

    def test_one_conversation_a_project_and_a_second_item_waits_for_it(self) -> None:
        first, second = self.proposed(), self.proposed("Export the members as a spreadsheet.")
        self.assertEqual(self.confirm(first)[0], 200)
        before = self.settle()["turns"]
        code, said = self.confirm(second)
        self.assertEqual(code, 400)
        self.assertIn("a hand-over is already open", said)
        code, said = self.confirm(first)
        self.assertEqual(code, 400)
        self.assertIn(f"feedback {first.number} is already in the hand-over", said)
        self.assertEqual(self.settle()["turns"], before, "neither press said anything to the agent")
        self.assertEqual(self.post("/handover/reset", {}), (200, "cleared"))
        self.assertEqual(feedback.find(self.root, first.number).state, "proposed", "Start again leaves it a proposal")
        self.assertEqual(self.confirm(second)[0], 200)
        self.assertEqual(self.settle()["feedback"], second.number)

    def test_an_item_handed_on_or_dropped_opens_nothing(self) -> None:
        item = self.proposed()
        feedback.drop(self.root, item.number)
        code, said = self.confirm(item, "scope")
        self.assertEqual(code, 400)
        self.assertIn("was already dropped", said)
        self.assertEqual(self.settle()["turns"], [])

    def test_a_conversation_from_the_tab_itself_marks_no_item(self) -> None:
        item = self.proposed()
        self.say(CLEAR)
        code, said = self.post("/handover/capture", {})
        self.assertEqual(code, 200)
        self.assertNotIn("Feedback", said)
        self.assertEqual(feedback.find(self.root, item.number).state, "proposed")

    def test_an_item_dropped_while_it_was_talked_through_is_said_and_the_idea_is_still_written(self) -> None:
        item = self.proposed(f"Reminders. {CLEAR}")
        self.assertEqual(self.confirm(item)[0], 200)
        self.assertTrue(self.settle()["ready"])
        feedback.drop(self.root, item.number)
        code, said = self.post("/handover/capture", {})
        self.assertEqual(code, 200)
        self.assertIn(f"Feedback {item.number} was not marked as having become it", said)
        self.assertEqual(len(self.written()), 1)

    def test_the_page_shows_the_tab_the_conversation_is_on_and_takes_nobodys_words(self) -> None:
        self.assertIn(f"String(said).includes('{WHERE}')", SCRIPT)
        self.assertIn("""document.querySelector('.tabs [data-tab="next"]')""", SCRIPT)
        self.assertNotIn("handover", SCRIPT, "the Feedback card never reaches into the hand-over's box")
