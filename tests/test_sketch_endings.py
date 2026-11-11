"""How a sketch's answer ends, where it does not end well: never in silence.

What is proved, on stand-in agents: the stream is read as UTF-8 whatever the platform reads by default; an
answer stopped at the limit, one that crashed half way, one that left without a word, one the board itself
stopped hearing and one the person stopped each say so; and one that had begun says how to pick it up.
"""
from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import brief_session
from slipwai.brief_session import Sketch


class EndingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        patched = mock.patch.object(brief_session, "SKETCHES", self.area / "sketches")
        patched.start()
        self.addCleanup(patched.stop)

    def settle(self) -> dict:
        for _ in range(200):
            said = self.sketch.said()
            if not said["busy"]:
                return said
            time.sleep(0.05)
        self.fail("the sketch never finished answering")

    def test_the_agents_stream_is_read_as_utf8_whatever_the_platform_reads_by_default(self) -> None:
        """Windows reads a pipe as cp1252, where byte 0x9D means nothing: a `❌` in a file the agent read
        ended the reader mid-turn, the page showed the session stopped, and the agent was still running."""
        script = self.area / "marks.py"
        script.write_text(
            "import json, sys\n"
            "line = json.dumps({'type': 'assistant', 'message': {'content': [\n"
            "    {'type': 'text', 'text': 'Anti-patterns: \\u274c none \\u201cquoted\\u201d'}]}}, ensure_ascii=False)\n"
            "sys.stdout.buffer.write(line.encode('utf-8') + b'\\n')\n", encoding="utf-8")
        self.sketch = Sketch("club-boats", [sys.executable, str(script)])
        with mock.patch.object(brief_session.subprocess, "Popen", wraps=brief_session.subprocess.Popen) as opened:
            self.sketch.ask("go")
            said = self.settle()
        self.assertEqual(said["turns"][-1]["text"], "Anti-patterns: ❌ none “quoted”")
        self.assertEqual(opened.call_args.kwargs["encoding"], "utf-8")
        self.assertTrue(self.sketch.begun, "the turn was heard to its end, so the next one resumes the session")

    def test_an_answer_stopped_at_the_limit_says_so_and_the_next_one_resumes(self) -> None:
        """A turn that had spoken and was then stopped at the limit ended with no word: the page showed a
        conversation that had stopped, mid-drawing, and nothing about why."""
        script = self.area / "slow.py"
        script.write_text(
            "import json, sys, time\n"
            "print(json.dumps({'type': 'assistant', 'message': {'content': [\n"
            "    {'type': 'text', 'text': 'Now the drawing itself.'}]}}), flush=True)\n"
            "time.sleep(60)\n", encoding="utf-8")
        self.sketch = Sketch("club-boats", [sys.executable, str(script)])
        with mock.patch.object(brief_session, "LIMIT", 1):
            self.sketch.ask("go")
            said = self.settle()
        self.assertEqual([(t["kind"], t["text"][:40]) for t in said["turns"][1:]],
                         [("text", "Now the drawing itself."), ("error", "This answer was stopped after 0 minutes,")])
        self.assertIn("carry on", said["turns"][-1]["text"])
        self.assertTrue(self.sketch.begun, "it had answered, so the next thing said resumes the session")

    def stand_in(self, body: str) -> None:
        script = self.area / "other.py"
        script.write_text("import json, sys, time\n"
                          "def say(text):\n"
                          "    print(json.dumps({'type': 'assistant', 'message': {'content': [\n"
                          "        {'type': 'text', 'text': text}]}}), flush=True)\n" + body, encoding="utf-8")
        self.sketch = Sketch("club-boats", [sys.executable, str(script)])

    def test_no_ending_of_an_answer_is_a_silence(self) -> None:
        """Each of these ended with nothing on the page: the conversation had simply stopped."""
        with self.subTest("it crashed half way through, and what it printed about it is shown"):
            self.stand_in("say('Now the drawing itself.')\n"
                          "print('Error: out of credit', file=sys.stderr)\nsys.exit(3)\n")
            self.sketch.ask("go")
            last = self.settle()["turns"][-1]
            self.assertEqual(last["kind"], "error")
            self.assertIn("status 3 before the answer was finished", last["text"])
            self.assertIn("Error: out of credit", last["text"])
            self.assertIn("carry on", last["text"])
        with self.subTest("it left without a word"):
            self.stand_in("print('Session ID is already in use')\nsys.exit(1)\n")
            self.sketch.ask("go")
            last = self.settle()["turns"][-1]
            self.assertIn("status 1 and said nothing. The last it printed: Session ID is already in use", last["text"])
            self.assertNotIn("carry on", last["text"], "nothing was begun, so there is nothing to carry on")
        with self.subTest("it ended well and said nothing at all"):
            self.stand_in("pass\n")
            self.sketch.ask("go")
            self.assertEqual(self.settle()["turns"][-1]["text"], "The session ended without an answer.")
        with self.subTest("the board's own hearing failed, and the agent is not left running unseen"):
            self.stand_in("say('one')\nsay('two')\ntime.sleep(60)\n")
            heard = []

            def fails(line: str) -> bool:
                heard.append(line)
                if len(heard) == 2:
                    raise RuntimeError("the reader broke")
                return True

            with mock.patch.object(self.sketch, "take", fails):
                self.sketch.ask("go")
                last = self.settle()["turns"][-1]
            self.assertEqual(last["kind"], "error")
            self.assertIn("stopped hearing the session", last["text"])
            self.assertIn("the reader broke", last["text"])
        with self.subTest("the person stopped it"):
            self.stand_in("say('working')\ntime.sleep(60)\n")
            self.sketch.ask("go")
            for _ in range(100):
                if len(self.sketch.said()["turns"]) > 1:
                    break
                time.sleep(0.05)
            self.sketch.cancel()
            self.assertEqual(self.settle()["turns"][-1]["text"], "Stopped.")
