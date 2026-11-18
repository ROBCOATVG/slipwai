"""The Next features tab: there once the project has a specification, with a hand-over that is a conversation
with the project's agent and ends in one idea captured — and never confirmed — under `docs/intake/`."""
from __future__ import annotations

import json
import re
import time

import checkout_packages  # noqa: F401
from intake_fixture import CLEAR, HandoverTest
from test_intake_document import HOSTILE

from slipwai.intake_document import LIMIT
from slipwai.project import intake


class CardTest(HandoverTest):
    def tab(self) -> str:
        found = re.search(r'<section class="tab" data-tab="next".*?</section>', self.get("/voyage")[1], re.S)
        return found.group(0) if found else ""

    def test_the_tab_is_there_with_no_idea_waiting_and_says_so(self) -> None:
        tab = self.tab()
        self.assertIn("No idea is waiting.", tab)
        self.assertIn('id="handover"', tab)
        self.assertIn('<input type="file" accept=".md,.txt,text/*">', tab, "what the first page's input accepts")
        self.assertNotIn('id="intake-go"', tab, "nothing to continue yet")

    def test_before_the_first_specification_there_is_no_tab_and_no_hand_over(self) -> None:
        (self.root / "specs/001-demo/spec.md").unlink()
        self.assertEqual(self.tab(), "")
        code, said = self.post("/handover/say", {"message": "Billing"})
        self.assertEqual(code, 400)
        self.assertIn("no specification yet", said)
        intake.capture(self.root, "Billing")  # an idea `/sail` captured is still shown, as it was
        self.assertIn('id="intake-go"', self.tab())
        self.assertNotIn('id="handover"', self.tab())

    def test_an_idea_waiting_is_listed_above_the_hand_over(self) -> None:
        intake.capture(self.root, "Billing")
        tab = self.tab()
        self.assertIn("<b>billing</b> — confirm.", tab)
        self.assertLess(tab.index('id="intake-go"'), tab.index('id="handover"'))

    def test_the_live_poll_repaints_no_part_of_the_tab(self) -> None:
        """The window's poll swaps bands; the box a person types in is in none of them, on the page or in
        what the poll carries, and the card's own script clears it only after a send the board accepted."""
        self.assertNotIn("data-band", self.tab())
        bands = json.loads(self.get("/live.json")[1])["bands"]
        self.assertFalse([name for name, band in bands.items() if "handover" in band["html"]])
        from slipwai.intake_card import SCRIPT
        self.assertEqual(SCRIPT.count("box.value = "), 1)
        self.assertLess(SCRIPT.index("if (!answer.ok) { refuse(await answer.text()); go.disabled = false; return; }"),
                        SCRIPT.index("box.value = "))
        self.assertNotIn("innerHTML", SCRIPT)

    def test_continue_with_nothing_waiting_points_at_the_hand_over(self) -> None:
        code, said = self.post("/intake", {})
        self.assertEqual(code, 400)
        self.assertIn("hand over a further feature in the box on this tab", said)
        self.assertIn("/sail", said)


class ConversationTest(HandoverTest):
    def test_words_alone_become_a_conversation_and_then_one_idea_that_is_not_confirmed(self) -> None:
        said = self.say(CLEAR)
        self.assertEqual([(t["role"], t["kind"]) for t in said["turns"]][:2], [("person", "text"), ("agent", "text")])
        self.assertTrue(said["turns"][1]["text"].startswith("Role given. Drawn: Billing for clubs."),
                        "the role went ahead of the person's words, and only their words were acted on")
        self.assertEqual((said["agent"], said["model"]), ("stand-in 0.1", "A"), "which agent and model it is on")
        self.assertTrue(said["ready"])
        self.assertFalse((self.root / "docs/intake").exists(), "nothing is written until the person captures it")
        code, captured = self.post("/handover/capture", {})
        self.assertEqual(code, 200)
        self.assertIn("captured docs/intake/billing-for-clubs-the-idea-is-ready-to-capture", captured)
        self.assertEqual(self.written(), ["billing-for-clubs-the-idea-is-ready-to-capture/brief.md"])
        idea = intake.ideas(self.root)[0]
        self.assertEqual(idea.state, "confirm", "captured, and still waiting for the person's yes")
        self.assertIn(CLEAR, (self.root / "docs/intake" / idea.slug / "brief.md").read_text(encoding="utf-8"))
        self.assertEqual(self.settle()["turns"], [], "the conversation is let go of with its idea")
        self.assertFalse((self.root / ".slipwai/handover").exists())
        self.assertEqual(self.post("/intake", {}), (200, f"confirmed {idea.slug}"), "confirming is the old button")

    def test_a_document_is_read_by_the_agent_and_lands_beside_the_brief(self) -> None:
        text = "# Billing\r\n\nMembers pay by card.\n"
        said = self.say("", {"name": "billing-prd.md", "text": text})
        self.assertEqual([(t["kind"], t["text"]) for t in said["turns"]][:2],
                         [("text", "Here is a document for a further feature: billing-prd.md. Read it first."),
                          ("attached", "billing-prd.md")])
        self.assertEqual(said["documents"], ["billing-prd.md"])
        self.assertFalse(said["ready"], "the agent has not said the idea is one clear thing")
        code, refused = self.post("/handover/capture", {})
        self.assertEqual(code, 400)
        self.assertIn("once the agent says the idea is ready", refused)
        self.assertTrue(self.say(f"Only the card payments. {CLEAR}")["ready"])
        self.assertEqual(self.post("/handover/capture", {})[0], 200)
        self.assertEqual(self.written(), ["billing-prd/billing-prd.md", "billing-prd/brief.md",
                                          "billing-prd/conversation.md"])
        home = self.root / "docs/intake/billing-prd"
        self.assertEqual((home / "billing-prd.md").read_bytes(), text.encode(), "the document, byte for byte")
        talked = (home / "conversation.md").read_text(encoding="utf-8")
        self.assertIn("**Person:** Only the card payments.", talked)
        self.assertIn("**Agent:** Drawn: Only the card payments.", talked)
        self.assertEqual(intake.ideas(self.root)[0].state, "confirm")

    def test_the_session_can_read_and_cannot_write(self) -> None:
        said = self.say("Billing for clubs")
        refused = next(t for t in said["turns"] if t["kind"] == "error")
        self.assertIn("can read and cannot do", refused["text"])
        self.assertEqual(next(t for t in said["turns"] if t["kind"] == "tool_update")["tool"]["status"], "failed")
        self.assertFalse((self.root / "prototype").exists(), "the write the agent asked leave for did not happen")
        self.assertFalse((self.root / "brief").exists())
        self.assertTrue((self.root / ".slipwai/handover/session").is_file(), "kept under the run's folder")

    def test_a_question_from_the_agent_is_a_card_answered_on_the_tab(self) -> None:
        self.assertEqual(self.post("/handover/say", {"message": "ask"}), (200, "asked"))
        asked = None
        for _ in range(400):
            turns = json.loads(self.get("/handover.json?since=0")[1])["turns"]
            asked = next((t for t in turns if t["kind"] == "question"), None)
            if asked:
                break
            time.sleep(0.05)
        assert asked is not None
        code, busy = self.post("/handover/say", {"message": "and another thing"})
        self.assertEqual(code, 409, "a turn under way: the page waits")
        self.assertEqual(self.post("/handover/answer", {"id": asked["ask"]["id"], "answer": "blue"}),
                         (200, "answered"))
        self.assertIn("You said: blue", [t["text"] for t in self.settle()["turns"]])
        self.assertEqual(self.post("/handover/answer", {"id": "q9", "answer": "x"})[0], 400)
        self.assertEqual(self.post("/handover/cancel", {}), (200, "stopped"))


class RefusalTest(HandoverTest):
    def refused(self, body: dict, why: str) -> None:
        code, said = self.post("/handover/say", body)
        self.assertEqual(code, 400, said)
        self.assertIn(why, said)

    def tearDown(self) -> None:
        self.assertEqual(self.settle()["turns"], [], "a refused post starts no conversation")
        self.assertFalse((self.root / ".slipwai/handover").exists(), "and keeps nothing")
        self.assertFalse((self.root / "docs/intake").exists())

    def test_an_empty_post_is_refused(self) -> None:
        for body in ({}, {"message": "   "}, {"message": "", "document": None}):
            self.refused(body, "say what the feature is, or choose its document")
        self.refused({"message": "", "document": {"name": "empty.md", "text": " \n"}}, "empty.md is empty")
        self.refused({"message": "Billing", "document": "a path, not a document"}, "its name and its text")

    def test_an_oversized_document_or_message_is_refused(self) -> None:
        self.refused({"message": "Billing", "document": {"name": "big.md", "text": "a" * (LIMIT + 1)}}, "256 KB")
        self.refused({"message": "a" * (LIMIT + 1)}, "what you typed is more than 256 KB")

    def test_a_document_that_is_not_text_is_refused(self) -> None:
        self.refused({"message": "Billing", "document": {"name": "logo.png", "text": "\x89PNG\x00\x01"}},
                     "does not read as text")

    def test_a_hostile_file_name_writes_nothing_inside_the_project_or_out_of_it(self) -> None:
        before = sorted(one for one in self.root.rglob("*") if one.is_file())
        for name in HOSTILE:
            with self.subTest(name=name):
                code, said = self.post("/handover/say", {"message": "Billing",
                                                         "document": {"name": name, "text": "yes\nperson\n"}})
                self.assertEqual(code, 400, said)
        self.assertEqual(sorted(one for one in self.root.rglob("*") if one.is_file()), before)
        self.assertFalse((self.root.parent / "evil.md").exists())
