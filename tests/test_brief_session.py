"""The conversation that writes a brief, driven by a stand-in for the agent.

The agent is a command the sketch is handed, so what runs here is the real conversation — the workspace, the
turns, the poll, the step line, the brief read back — over a script that writes what an agent would write
and prints the stream it would print.
"""
from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import board_settings, brief_session
from slipwai.board_settings import Launch
from slipwai.brief_session import Sketch, checked, prepared, slug_of, started, workspace

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "brief"

#: What the agent does for one turn: it writes the requirements document and one surface into `brief/`, says
#: which step it is at, and says something. The message is the last argument, which is how the sketch passes it.
STAND_IN = """
import json, sys
from pathlib import Path
message = sys.argv[-1]
home = Path.cwd()
(home / "brief" / "prd.md").write_text("# Requirements\\n\\n## What it must do\\n\\n- Book a boat.\\n",
                                       encoding="utf-8")
(home / "brief" / "surfaces").mkdir(exist_ok=True)
(home / "brief" / "surfaces" / "book.html").write_text(
    '<title>Book a boat</title><article class="state" data-decided="person"><h2>Empty</h2></article>', encoding="utf-8")
print('a banner, not json')
print(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "tool_use", "name": "Write", "input": {"file_path": "brief/prd.md"}}]}}))
print(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "text", "text": "step: 2\\nI have drawn it. Tap through: " + message}]}}))
print(json.dumps({"type": "result", "is_error": False, "result": "done"}))
"""


AGENT = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"


class ProtocolTest(unittest.TestCase):
    """The same conversation over the Agent Client Protocol, on the stand-in agent `tests/test_acp.py` uses."""

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        for patched in (mock.patch.object(brief_session, "SKETCHES", self.area / "sketches"),
                        mock.patch.object(board_settings, "SETTINGS", self.area / "board.json")):
            patched.start()
            self.addCleanup(patched.stop)
        self.launch = Launch("stand-in", "Stand-in", (sys.executable, str(AGENT)), "a script")
        self.sketch = Sketch("club-boats", launch=self.launch)
        self.addCleanup(self.sketch.reset)

    def settle(self) -> dict:
        return self.settle_on(self.sketch)

    def settle_on(self, sketch: Sketch) -> dict:
        for _ in range(400):
            said = sketch.said()
            if not said["busy"]:
                return said
            time.sleep(0.05)
        self.fail("the sketch never finished answering")

    def until(self, kind: str) -> dict:
        for _ in range(400):
            found = [t for t in self.sketch.said()["turns"] if t["kind"] == kind]
            if found:
                return found[-1]
            time.sleep(0.05)
        self.fail(f"no {kind} turn arrived")

    def texts(self) -> list[str]:
        return [t["text"] for t in self.sketch.said()["turns"] if t["kind"] == "text"]

    def test_a_reopened_sketch_loads_its_kept_session_and_the_agent_replays_it(self) -> None:
        self.assertFalse(self.sketch.resume(), "nothing kept yet")
        self.assertEqual(self.sketch.ask("Members book a boat."), "asked")
        self.settle()
        self.assertFalse(self.sketch.resume(), "a conversation in hand is not loaded over")
        again = Sketch("club-boats", launch=self.launch)  # the board restarted: a new object, the folder kept
        self.addCleanup(again.reset)
        self.assertTrue(again.resume())
        for _ in range(400):
            if not again.said()["busy"]:
                break
            time.sleep(0.05)
        said = again.said()
        self.assertFalse(said["busy"])
        self.assertIn("earlier: hello again", [t["text"] for t in said["turns"]], "the agent replayed the session")
        self.assertIn(("person", "hello from before"), [(t["role"], t["text"]) for t in said["turns"]],
                      "the person's words replayed without the role the board put ahead of them")
        self.assertIn(("person", "and once more"), [(t["role"], t["text"]) for t in said["turns"]],
                      "two messages with no answer between them stay two turns")
        self.assertEqual((said["agent"], said["model"]), ("stand-in 0.1", "A"))
        self.assertEqual(again.ask("And a second boat."), "asked")
        self.assertEqual(self.settle_on(again)["turns"][-1]["kind"], "tool_update", "and the conversation goes on")

    def test_a_turn_is_the_agents_updates_as_they_arrive_and_the_brief_read_after(self) -> None:
        self.assertEqual(self.sketch.ask("Members book a boat.\nstep: 2"), "asked")
        said = self.settle()
        self.assertEqual([(t["role"], t["kind"]) for t in said["turns"]],
                         [("person", "text"), ("sketch", "text"), ("sketch", "tool"), ("sketch", "tool_update")])
        self.assertEqual(said["turns"][1]["text"], "Role given. Drawn: Members book a boat.",
                         "the eight steps went first, and the step line is read and taken out")
        self.assertEqual(said["step"], 2)
        self.assertEqual(said["turns"][2]["tool"]["kind"], "edit")
        self.assertTrue(said["turns"][2]["tool"]["what"].endswith("prototype/index.html"), "the input's telling field")
        self.assertNotIn("thought", [t["kind"] for t in said["turns"]], "the agent's reasoning is not a turn")
        self.assertFalse(said["thinking"])
        self.assertEqual((said["agent"], said["model"]), ("stand-in 0.1", "A"), "as the agent names them")
        self.assertEqual(said["turns"][3]["tool"]["status"], "completed")
        self.assertEqual(said["agent"], "stand-in 0.1", "as the agent named itself")
        self.assertEqual(said["check"][0], "requirements document: prd.md, by name")
        self.assertTrue((self.area / "board.json").is_file(), "what the agent offered was kept for the settings page")
        self.assertIn("model", board_settings.read(self.area / "board.json").offered["stand-in"][0]["id"])

    def test_the_role_heads_the_first_prompt_only(self) -> None:
        self.sketch.ask("first")
        self.settle()
        self.assertEqual(self.texts()[1], "Role given. Drawn: first", "the eight steps headed the first prompt")
        self.sketch.ask("second")
        self.settle()
        self.assertEqual(self.texts()[-1], "Drawn: second")

    def test_a_permission_outside_the_folder_is_a_card_the_person_answers(self) -> None:
        self.sketch.ask("outside")
        asked = self.until("permission")
        self.assertEqual(asked["ask"]["path"], "/etc/hosts")
        self.assertEqual([o["kind"] for o in asked["ask"]["options"]], ["allow_once", "reject_once"])
        self.assertTrue(self.sketch.answer(asked["ask"]["id"], "no-once"))
        self.settle()
        self.assertIn("refused outside", self.texts())
        self.assertEqual(self.until("answered")["ask"]["id"], asked["ask"]["id"])
        self.assertFalse(self.sketch.answer("p99", "yes-once"), "an answer to nothing waiting is refused")

    def test_a_question_is_a_card_answered_in_the_same_turn(self) -> None:
        self.sketch.ask("ask")
        asked = self.until("question")
        self.assertEqual((asked["text"], asked["ask"]["field"]), ("Which colour?", "answer"))
        self.sketch.answer(asked["ask"]["id"], "blue")
        self.settle()
        self.assertIn("You said: blue", self.texts())

    def test_a_stop_ends_the_turn_cancelled_and_the_session_stays(self) -> None:
        self.sketch.ask("slow")
        self.until("permission")
        self.assertEqual(self.sketch.cancel(), "stopped")
        said = self.settle()
        self.assertIn("Stopped.", [t["text"] for t in said["turns"][-3:]], "a tool's last update may land after")
        self.sketch.ask("again")
        self.assertEqual(self.settle()["turns"][-3]["text"], "Drawn: again", "the same session answers the next turn")

    def test_a_board_restart_loads_the_session_the_folder_kept(self) -> None:
        self.sketch.ask("first")
        self.settle()
        self.sketch.agent.close() if self.sketch.agent else None
        again = Sketch("club-boats", launch=self.launch)
        self.addCleanup(again.reset)
        again.ask("after")
        said = [t["text"] for t in again.said()["turns"] if t["kind"] == "text"]
        for _ in range(400):
            if not again.said()["busy"]:
                break
            time.sleep(0.05)
        said = [t["text"] for t in again.said()["turns"] if t["kind"] == "text"]
        self.assertIn("earlier: hello again", said, "the agent replayed the history it kept")
        self.assertEqual(said[-1], "Drawn: after", "and the role was not given twice")

    def test_with_nothing_to_launch_the_page_says_where_to_look(self) -> None:
        held = Sketch("club-boats")
        with mock.patch.object(brief_session, "chosen", return_value=None), \
                mock.patch("shutil.which", return_value=None), \
                mock.patch.object(held, "environment", return_value={"PATH": "/nowhere"}):
            self.assertEqual(held.ask("hello"), "no agent")
        self.assertIn("Settings tab", held.said()["turns"][-1]["text"])


class SketchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        patched = mock.patch.object(brief_session, "SKETCHES", self.area / "sketches")
        patched.start()
        self.addCleanup(patched.stop)
        script = self.area / "agent.py"
        script.write_text(STAND_IN, encoding="utf-8")
        self.sketch = Sketch("club-boats", [sys.executable, str(script)])

    def settle(self) -> dict:
        for _ in range(200):
            said = self.sketch.said()
            if not said["busy"]:
                return said
            time.sleep(0.05)
        self.fail("the sketch never finished answering")

    def test_a_name_becomes_a_slug_and_a_slug_that_is_not_one_is_refused(self) -> None:
        self.assertEqual(slug_of("  Club Boat Bookings! "), "club-boat-bookings")
        for bad in ("", "---", "../etc", "a" * 70):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                workspace(bad) if bad else slug_of(bad)
        self.assertEqual(workspace("club-boats"), brief_session.SKETCHES / "club-boats")

    def test_the_workspace_is_made_with_its_two_folders_and_the_three_skills(self) -> None:
        home = prepared(workspace("club-boats"))
        self.assertTrue((home / "brief").is_dir() and (home / "prototype").is_dir())
        for skill in ("frontend-design", "storyboard", "find-gaps"):
            self.assertTrue((home / ".claude" / "skills" / skill / "SKILL.md").is_file(), skill)

    def test_a_turn_writes_the_brief_and_the_page_is_told_the_step_and_the_count(self) -> None:
        self.assertEqual(self.sketch.ask("Members book a boat for a morning."), "asked")
        said = self.settle()
        self.assertEqual([(t["role"], t["kind"]) for t in said["turns"]],
                         [("person", "text"), ("sketch", "wrote"), ("sketch", "text")])
        self.assertEqual(said["turns"][1]["text"], "Write brief/prd.md")
        self.assertEqual(said["turns"][2]["text"], "I have drawn it. Tap through: Members book a boat for a morning.",
                         "the step line is read and taken out of what the person sees")
        self.assertEqual(said["step"], 2)
        self.assertFalse(said["ready"])
        self.assertEqual(said["check"][0], "requirements document: prd.md, by name")
        self.assertIn("surfaces: 1, states: 1, each with a heading, 1 decided by a person", said["check"][1])

    def test_nothing_said_and_a_second_turn_under_way_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            self.sketch.ask("   ")
        self.sketch.busy = True
        with self.assertRaises(ValueError):
            self.sketch.ask("again")
        self.sketch.busy = False

    def test_a_poll_carries_only_what_the_asker_does_not_have(self) -> None:
        self.sketch.ask("one")
        first = self.settle()
        self.assertEqual(self.sketch.said(first["at"])["turns"], [])

    def test_the_session_reads_and_writes_in_its_workspace_and_nothing_more(self) -> None:
        held = Sketch("club-boats")
        held.session = "abc"
        with mock.patch("shutil.which", return_value="/usr/local/bin/claude"), \
                mock.patch.object(held, "environment", return_value={"PATH": "/usr/local/bin"}):
            argv = held.argv("hello") or []
            self.assertIn("--strict-mcp-config", argv, "the person's own MCP servers do not reach the session")
            self.assertEqual(argv[argv.index("--mcp-config") + 1], '{"mcpServers":{}}')
            self.assertEqual(argv[argv.index("--tools") + 1], "Read,Write,Edit,Glob,Grep")
            self.assertEqual(argv[argv.index("--allowedTools") + 1], "Read,Write,Edit,Glob,Grep")
            for power in ("Bash", "WebFetch", "--dangerously-skip-permissions"):
                self.assertNotIn(power, " ".join(argv))
            prompt = argv[argv.index("--append-system-prompt") + 1]
            self.assertIn(str(held.home / "brief"), prompt)
            self.assertIn("--session-id", argv)
            held.begun = True
            self.assertIn("--resume", held.argv("two") or [])

    def test_a_document_a_person_brought_lands_as_the_briefs_own_before_the_first_turn(self) -> None:
        home = started("brought", "# Bookings\n\n## What it must do\n\n- Book a boat.\n\n## Open\n\n- When?\n")
        self.assertEqual((home / "brief" / "prd.md").read_text(encoding="utf-8").splitlines()[0], "# Bookings")
        self.assertEqual(checked(home)[0], "requirements document: prd.md, by name")
        self.assertIn("the draft will have to assume: 1", checked(home)[-1])
        with self.assertRaises(ValueError, msg="a second document is a refusal, not an overwrite"):
            started("brought", "# Another\n")
        self.assertEqual(started("brought"), home, "and no document is just the workspace")

    def test_the_prompt_asks_the_right_questions_and_reads_a_brought_document_first(self) -> None:
        """The question set follows the prd-development skill's shape, in a person's words: the one
        sentence, the problem with its evidence, why now, the measure and its guardrail, the stories' edge
        cases, out of scope with a reason, dependencies and risks, and gaps tagged where they fall."""
        prompt = brief_session.PROMPT.read_text(encoding="utf-8")
        for heading in ("*The one sentence.*", "*The problem.*", "*Why now.*", "*How they would know.*",
                        "*Each thing it does.*", "*Each flow.*", "*The people.*", "*Out of scope.*",
                        "*What it leans on, and what could go wrong.*"):
            self.assertIn(heading, prompt)
        for asked in ("what shows it is real", "what must not get worse",
                      "what happens when it\n     fails or is refused", "what if they do the steps out of order",
                      "why not now on each line", "never as a form",
                      "say back what was settled and check it against what came before",
                      "which part of the brief is weakest"):
            self.assertIn(asked, prompt)
        for taken in ("a contradiction", "a dangling reference", "overreach", "an unowned decision",
                      "fast, easy, simple, soon"):
            self.assertIn(taken, prompt, "step 0 reviews a brought document for the five things")
        self.assertIn("Step 0, before", prompt)
        self.assertIn("never tell them to open a file", prompt)
        self.assertIn("a line beginning `Source:`", prompt)

    def test_the_prompts_folder_block_is_the_reference_pages(self) -> None:
        """One shape, stated once: the page a developer reads and the prompt the session reads say the same."""
        page = (Path(__file__).resolve().parents[1] / "docs" / "reference" / "the-brief.md").read_text(encoding="utf-8")
        block = page.split("```\n", 2)[1].replace("<brief>/", "brief/")
        self.assertIn(block.strip(), brief_session.PROMPT.read_text(encoding="utf-8"))

    def test_the_brief_is_read_back_the_way_the_start_page_reads_it(self) -> None:
        home = prepared(workspace("fixture"))
        self.assertEqual(checked(home), [], "nothing yet")
        import shutil
        shutil.copytree(FIXTURE, home / "brief", dirs_exist_ok=True)
        self.assertEqual(checked(home)[0], "requirements document: prd.md, by name")

    def test_a_reset_forgets_the_conversation_and_keeps_the_files(self) -> None:
        self.sketch.ask("one")
        self.settle()
        self.assertEqual(self.sketch.reset(), "cleared")
        said = self.sketch.said()
        self.assertEqual((said["turns"], said["step"]), ([], 1))
        self.assertTrue((self.sketch.home / "brief" / "prd.md").is_file())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
