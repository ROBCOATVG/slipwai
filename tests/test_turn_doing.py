"""What an answer under way is doing now: read off the pieces of a reply as they arrive.

What is proved: thinking, an answer being written and a tool's input being typed each have their line; a
file being written is named, with how much of it so far; the line is empty once the block is whole; and a
sketch's poll carries the line and how long the answer has been under way, and neither once it is over.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import brief_session
from slipwai.brief_session import Sketch
from slipwai.turn_child import Doing


def piece(kind: str, **more: object) -> dict:
    """One line of the stream as `claude -p --include-partial-messages` prints it."""
    return {"type": "stream_event", "event": {"type": kind, "index": 0, **more}}


class DoingTest(unittest.TestCase):
    def test_each_kind_of_block_has_its_line_and_none_once_it_is_whole(self) -> None:
        doing = Doing()
        doing.take(piece("content_block_start", content_block={"type": "thinking", "thinking": ""}))
        self.assertEqual(doing.now, "Thinking…")
        doing.take(piece("content_block_delta", delta={"type": "thinking_delta", "thinking": "hm"}))
        self.assertEqual(doing.now, "Thinking…")
        doing.take(piece("content_block_stop"))
        self.assertEqual(doing.now, "")
        doing.take(piece("content_block_start", content_block={"type": "text", "text": ""}))
        self.assertEqual(doing.now, "Writing its answer…")
        doing.take({"type": "assistant", "message": {"content": []}})
        self.assertEqual(doing.now, "")

    def test_a_file_being_written_is_named_with_how_much_so_far(self) -> None:
        doing = Doing()
        doing.take(piece("content_block_start", content_block={"type": "tool_use", "name": "Write", "input": {}}))
        self.assertEqual(doing.now, "Writing…")
        whole = json.dumps({"file_path": "C:\\Users\\kit\\.slipwai\\sketches\\club\\prototype\\index.html",
                            "content": "<p>" + "x" * 5000})
        for at in range(0, len(whole), 40):  # the input arrives in pieces that split anywhere, the name included
            typed = {"type": "input_json_delta", "partial_json": whole[at:at + 40]}
            doing.take(piece("content_block_delta", delta=typed))
            if at == 0:
                self.assertEqual(doing.now, "Writing…", "half a name is not a name")
        self.assertEqual(doing.now, f"Writing prototype/index.html, {len(whole) // 1024} KB so far")
        doing.take(piece("content_block_stop"))
        self.assertEqual(doing.now, "")

    def test_a_read_names_its_file_and_an_unknown_tool_still_says_something(self) -> None:
        doing = Doing()
        doing.take(piece("content_block_start", content_block={"type": "tool_use", "name": "Read"}))
        doing.take(piece("content_block_delta", delta={"partial_json": '{"file_path": "/home/kit/brief/prd.md"}'}))
        self.assertEqual(doing.now, "Reading brief/prd.md")
        doing.take(piece("content_block_start", content_block={"type": "tool_use", "name": "Mystery"}))
        self.assertEqual(doing.now, "Working…")


class PollTest(unittest.TestCase):
    def test_the_poll_carries_what_it_is_doing_and_for_how_long_and_neither_after(self) -> None:
        area = Path(tempfile.mkdtemp())
        patched = mock.patch.object(brief_session, "SKETCHES", area / "sketches")
        patched.start()
        self.addCleanup(patched.stop)
        script = area / "agent.py"
        script.write_text(
            "import json, sys, time\n"
            "def out(event): print(json.dumps(event), flush=True)\n"
            "out({'type': 'stream_event', 'event': {'type': 'content_block_start',\n"
            "     'content_block': {'type': 'thinking'}}})\n"
            "time.sleep(1.5)\n"
            "out({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'Done.'}]}})\n",
            encoding="utf-8")
        sketch = Sketch("club-boats", [sys.executable, str(script)])
        sketch.ask("go")
        seen = {}
        for _ in range(200):
            said = sketch.said()
            if said["doing"]:
                seen = said
            if not said["busy"]:
                break
            time.sleep(0.05)
        self.assertEqual(seen.get("doing"), "Thinking…")
        self.assertGreaterEqual(seen["for"], 0)
        self.assertEqual((said["doing"], said["for"], said["turns"][-1]["text"]), ("", 0, "Done."))

    def test_the_agent_is_asked_for_its_reply_in_pieces(self) -> None:
        with mock.patch("shutil.which", return_value="/somewhere/claude"), \
                mock.patch.object(Sketch, "environment", return_value={"PATH": "/somewhere"}), \
                mock.patch.object(brief_session, "SKETCHES", Path(tempfile.mkdtemp())):
            sketch = Sketch("club-boats")
            sketch.session = "abc"
            self.assertIn("--include-partial-messages", sketch.argv("hello") or [])
