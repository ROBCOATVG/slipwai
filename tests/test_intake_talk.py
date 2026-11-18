"""The hand-over's conversation kept: across a board restart, with no agent to run it, and when it is let go."""
from __future__ import annotations

import time

import checkout_packages  # noqa: F401
from intake_fixture import CLEAR, HandoverTest

from slipwai.board_settings import Launch
from slipwai.errors import Busy
from slipwai.intake_talk import ROLE, Handover


class KeptTest(HandoverTest):
    def quiet(self, talk: Handover) -> dict:
        for _ in range(400):
            said = talk.said()
            if not said["busy"]:
                return said
            time.sleep(0.05)
        self.fail("the hand-over never finished answering")

    def test_a_reopened_board_shows_the_conversation_and_carries_it_on_in_the_same_session(self) -> None:
        first = self.say("Billing for clubs", {"name": "billing.md", "text": "# Billing\n"})
        self.assertFalse(self.talk.resume(), "a conversation in hand is not loaded over")
        assert self.talk.agent is not None
        self.talk.agent.close()  # the board stopped
        again = self.opened()  # and started: a new object, the run folder kept
        texts = [(t["role"], t["kind"], t["text"]) for t in again.said()["turns"]]
        self.assertEqual(texts, [(t["role"], t["kind"], t["text"]) for t in first["turns"]
                                 if t["kind"] in ("text", "attached")],
                         "what was said and attached, before any agent is started")
        self.assertTrue(again.resume())
        said = self.quiet(again)
        self.assertFalse(again.resume(), "picked up once, not at every poll")
        self.assertEqual((said["agent"], said["model"]), ("stand-in 0.1", "A"), "which agent and model, at once")
        self.assertEqual(len(said["turns"]), len(texts), "what the agent replays on a load is not said twice")
        assert again.agent is not None
        self.assertTrue(again.agent.loaded, "the same session, loaded")
        self.assertEqual(again.ask(CLEAR), "asked")
        said = self.quiet(again)
        answer = [t["text"] for t in said["turns"] if t["role"] == "agent" and t["kind"] == "text"][-1]
        self.assertTrue(answer.startswith("Drawn: Billing for clubs."), "no role a second time: it is loaded")
        self.assertEqual(said["documents"], ["billing.md"])
        again.capture()
        self.assertEqual(self.written(), ["billing-for-clubs/billing.md", "billing-for-clubs/brief.md",
                                          "billing-for-clubs/conversation.md"])
        brief = (self.root / "docs/intake/billing-for-clubs/brief.md").read_text(encoding="utf-8")
        self.assertEqual(brief, "# Billing for clubs\n\nBilling for clubs\n", "the request is their first words")

    def test_with_no_agent_to_launch_it_says_where_to_look_and_runs_nothing_headless(self) -> None:
        nobody = Handover(self.root.resolve(), launch=Launch("none", "None", (), "nothing here"))
        self.assertEqual(nobody.ask("Billing for clubs"), "no agent")
        said = nobody.said()
        self.assertFalse(said["busy"])
        self.assertEqual(said["turns"][-1]["kind"], "error")
        self.assertIn("Settings tab", said["turns"][-1]["text"])
        self.assertIn("/sail", said["turns"][-1]["text"])
        with self.assertRaises(ValueError):
            nobody.capture()
        self.assertFalse((self.root / "docs/intake").exists())

    def test_start_again_lets_go_of_the_words_the_documents_and_the_session(self) -> None:
        self.say(CLEAR, {"name": "billing.md", "text": "# Billing\n"})
        self.assertEqual(self.post("/handover/reset", {}), (200, "cleared"))
        said = self.settle()
        self.assertEqual((said["turns"], said["ready"], said["documents"], said["open"], said["agent"]),
                         ([], False, [], False, ""), "nothing to start again from, and no agent named over nothing")
        self.assertFalse((self.root / ".slipwai/handover").exists())
        self.assertEqual(self.post("/handover/capture", {})[0], 400)
        self.assertEqual(self.opened().said()["turns"], [], "and a restart brings none of it back")

    def test_what_the_person_says_next_unsays_ready_and_a_turn_under_way_is_not_captured(self) -> None:
        self.assertTrue(self.say(CLEAR)["ready"])
        self.assertFalse(self.say("And invoices too")["ready"], "the agent has not said so about this")
        self.talk.busy = True
        with self.assertRaises(Busy):
            self.talk.capture()
        self.talk.busy = False

    def test_the_role_keeps_the_session_to_intake(self) -> None:
        for held in ("You can read and search this project and nothing else", "do not assess,\nspecify, plan, chart",
                     "Do not ask whether this is a new feature"):
            self.assertIn(held, ROLE)
