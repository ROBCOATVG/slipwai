"""The board's first page: the conversation on a tab, the brief counting itself up, and the files it serves.

Driven through the board with a stand-in for the agent, as the console's tests are, so what runs here is the
page's own routes over the real session and a script that writes and prints what an agent would.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest import mock
from urllib.parse import quote

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import board_settings, brief_session
from slipwai.board_settings import Launch
from slipwai.brief_page import chosen, served
from slipwai.brief_session import Sketch

STAND_IN = """
import json, sys
from pathlib import Path
message = sys.argv[-1]
home = Path.cwd()
(home / "brief" / "prd.md").write_text("# Requirements\\n", encoding="utf-8")
(home / "prototype" / "index.html").write_text("<title>Play</title><button>Book</button>", encoding="utf-8")
print(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "tool_use", "name": "Write", "input": {"file_path": "prototype/index.html"}}]}}))
print(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "text", "text": "step: 1\\nDrawn: " + message}]}}))
print(json.dumps({"type": "result", "is_error": False, "result": "done"}))
"""


class FirstPageTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.area = Path(tempfile.mkdtemp())
        patched = mock.patch.object(brief_session, "SKETCHES", self.area / "sketches")
        patched.start()
        self.addCleanup(patched.stop)
        script = self.area / "agent.py"
        script.write_text(STAND_IN, encoding="utf-8")
        brief_session.SKETCHED["club-boats"] = Sketch("club-boats", [sys.executable, str(script)])
        self.addCleanup(brief_session.SKETCHED.clear)

    def settle(self) -> dict:
        for _ in range(200):
            _, body = self.get("/brief.json?sketch=club-boats&since=0")
            said = json.loads(body)
            if not said["busy"]:
                return said
            time.sleep(0.05)
        self.fail("the sketch never finished answering")

    def test_the_tab_is_beside_start_a_project_and_not_on_the_published_copy(self) -> None:
        board = self.get("/")[1]
        self.assertLess(board.index('href="/brief"'), board.index("Start from a PRD"),
                        "the first door, in the order a person arrives: an idea before a document")
        self.assertNotIn('href="/brief"', self.rendered(controls=False))

    def test_the_page_with_no_sketch_lists_the_ones_this_machine_has_and_asks_for_a_name(self) -> None:
        (self.area / "sketches" / "older").mkdir(parents=True)
        code, said = self.get("/brief")
        self.assertEqual(code, 200)
        self.assertIn('href="/brief?sketch=older"', said)
        self.assertIn('name="name"', said)
        self.assertIn("starts a project from the next tab as before", said)

    def test_a_name_opens_a_sketch_with_the_four_steps_and_the_first_marked(self) -> None:
        self.assertEqual(chosen("name=Club+Boat+Bookings"), "club-boat-bookings")
        self.assertEqual(chosen("sketch=club-boats"), "club-boats")
        self.assertIsNone(chosen(""))
        code, said = self.get("/brief?name=Club%20boats")
        self.assertEqual(code, 200)
        self.assertIn('data-sketch="club-boats"', said)
        self.assertIn('<span class="now">1 Describe</span>', said)
        self.assertIn("4 Hand over", said)
        self.assertIn("Nothing written yet.", said)
        home = brief_session.workspace("club-boats") / "brief"
        self.assertIn('href="/brief/read?sketch=club-boats"', said, "the brief can be read as a document")
        self.assertIn(f'<a class="hand-over" id="hand-over" hidden href="/generate?brief={quote(str(home))}">', said,
                      "a link to the start page with its last field filled, shown once the brief has a document")
        self.assertIn("Green: the builder can start from it without asking. Amber: what the draft will", said)
        with self.assertRaises(urllib.error.HTTPError, msg="a name that is not one is refused") as refused:
            self.get("/brief?name=%2F..%2F")
        self.assertEqual(refused.exception.code, 400)

    def test_a_turn_is_asked_through_the_page_and_polled_back_with_the_step_and_the_check(self) -> None:
        code, said = self.post("/brief/ask", {"sketch": "club-boats", "message": "Members book a boat."})
        self.assertEqual((code, said), (200, "asked"))
        polled = self.settle()
        self.assertEqual([(t["role"], t["kind"]) for t in polled["turns"]],
                         [("person", "text"), ("sketch", "wrote"), ("sketch", "text")])
        self.assertEqual(polled["step"], 1)
        self.assertEqual(polled["check"][0], "requirements document: prd.md, by name")
        self.assertIn('src="/brief/files/club-boats/prototype/index.html"', self.get("/brief?sketch=club-boats")[1],
                      "the prototype is embedded once there is one")
        self.assertEqual(self.post("/brief/ask", {"sketch": "club-boats", "message": "  "})[0], 400)
        self.assertEqual(self.post("/brief/reset", {"sketch": "club-boats"}), (200, "cleared"))

    def test_the_cards_are_answered_and_a_turn_stopped_through_the_page(self) -> None:
        patched = mock.patch.object(board_settings, "SETTINGS", self.area / "board.json")
        patched.start()
        self.addCleanup(patched.stop)
        agent = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"
        brief_session.SKETCHED["over-acp"] = Sketch("over-acp", launch=Launch("stand-in", "Stand-in",
                                                                               (sys.executable, str(agent)), ""))
        self.addCleanup(brief_session.SKETCHED["over-acp"].reset)
        page = self.get("/brief?sketch=over-acp")[1]
        self.assertIn('<button class="stop" type="button" hidden>Stop</button>', page)
        self.assertEqual(self.post("/brief/ask", {"sketch": "over-acp", "message": "outside"}), (200, "asked"))
        asked = None
        for _ in range(400):
            turns = json.loads(self.get("/brief.json?sketch=over-acp&since=0")[1])["turns"]
            asked = next((t for t in turns if t["kind"] == "permission"), None)
            if asked:
                break
            time.sleep(0.05)
        assert asked is not None
        self.assertEqual(self.post("/brief/answer", {"sketch": "over-acp", "id": "p77", "option": "yes-once"})[0],
                         400)
        self.assertEqual(self.post("/brief/answer", {"sketch": "over-acp", "id": asked["ask"]["id"], "decline": True}),
                         (200, "answered"))
        for _ in range(400):
            said = json.loads(self.get("/brief.json?sketch=over-acp&since=0")[1])
            if not said["busy"]:
                break
            time.sleep(0.05)
        self.assertIn("on stand-in 0.1", self.get("/brief?sketch=over-acp")[1])
        self.assertEqual(self.post("/brief/cancel", {"sketch": "over-acp"}), (200, "stopped"))

    def test_a_document_a_person_brought_begins_the_sketch_with_it_read_first(self) -> None:
        listing = self.get("/brief")[1]
        self.assertIn('<textarea id="said" name="said"', listing)
        self.assertIn('<input type="file" accept=".md,.txt,text/*">', listing)
        brief_session.SKETCHED["from-a-doc"] = Sketch("from-a-doc", [sys.executable, str(self.area / "agent.py")])
        code, slug = self.post("/brief/new", {"name": "From a doc", "document": "# Bookings\n\n## Open\n\n- When?\n"})
        self.assertEqual((code, slug), (200, "from-a-doc"))
        opened = self.get("/brief?sketch=from-a-doc")[1]
        self.assertIn('data-sketch="from-a-doc"', opened)
        polled = json.loads(self.get("/brief.json?sketch=from-a-doc&since=0")[1])
        self.assertEqual(polled["turns"][0], {"role": "person", "kind": "text", "text": brief_session.BROUGHT},
                         "the document is the first thing said, so step 0 begins without a word typed")
        self.assertEqual(polled["check"][0], "requirements document: prd.md, by name", "read before the first turn")
        self.assertEqual(self.post("/brief/new", {"name": "From a doc", "document": "# Again\n"})[0], 400)
        brief_session.SKETCHED["in-words"] = Sketch("in-words", [sys.executable, str(self.area / "agent.py")])
        self.assertEqual(self.post("/brief/new", {"name": "In words", "said": "A way to find games nearby"}),
                         (200, "in-words"))
        polled = json.loads(self.get("/brief.json?sketch=in-words&since=0")[1])
        self.assertEqual(polled["turns"][0]["text"], "A way to find games nearby",
                         "what was typed under the name is the first thing said, not a document to review")
        self.assertEqual(self.post("/brief/new", {"name": "", "document": ""})[0], 400)

    def test_a_file_is_served_from_the_workspace_and_nothing_outside_it(self) -> None:
        home = brief_session.prepared(brief_session.workspace("club-boats"))
        (home / "prototype" / "index.html").write_text("<title>Play</title>", encoding="utf-8")
        (home / "brief" / "look").mkdir()
        (home / "brief" / "look" / "look.css").write_text(":root{}", encoding="utf-8")
        code, said = self.get("/brief/files/club-boats/prototype/index.html")
        self.assertEqual((code, said), (200, "<title>Play</title>"))
        sheet = served("/brief/files/club-boats/brief/look/look.css")
        assert sheet is not None
        self.assertEqual(sheet[1], "text/css; charset=utf-8")
        for outside in ("/brief/files/club-boats/../agent.py", "/brief/files/club-boats/.claude/skills/x",
                        "/brief/files/club-boats/", "/brief/files/nope/prototype/index.html"):
            with self.subTest(outside=outside):
                self.assertIsNone(served(outside))
        with self.assertRaises(urllib.error.HTTPError) as missing:
            self.get("/brief/files/club-boats/nothing.html")
        self.assertEqual(missing.exception.code, 404)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class ReadingTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        patched = mock.patch.object(brief_session, "SKETCHES", self.root / "sketches")
        patched.start()
        self.addCleanup(patched.stop)

    def test_the_brief_s_documents_are_read_on_the_board_and_a_missing_one_is_said(self) -> None:
        home = brief_session.started("club-boats")
        (home / "brief").mkdir(exist_ok=True)
        (home / "brief" / "prd.md").write_text("# Club boats\n\nMembers **book** a boat.\n\n## Open\n\n- When?\n",
                                              encoding="utf-8")
        code, page = self.get("/brief/read?sketch=club-boats")
        self.assertEqual(code, 200)
        self.assertIn("<h1>Club boats</h1>", page)
        self.assertIn("<b>book</b>", page)
        self.assertIn('href="/brief?sketch=club-boats"', page, "the way back is the brief, not the voyage")
        self.assertIn("the brief</a>", page)
        self.assertIn('<a href="/brief?sketch=club-boats">\u2190 The brief</a>', page,
                      "the bar goes back to the brief too")
        self.assertNotIn("The voyage", page)
        with self.assertRaises(urllib.error.HTTPError) as refused:
            self.get("/brief/read?sketch=club-boats&file=people")
        self.assertEqual(refused.exception.code, 404)
        with self.assertRaises(urllib.error.HTTPError) as refused:
            self.get("/brief/read?sketch=club-boats&file=secrets")
        self.assertEqual(refused.exception.code, 404)
