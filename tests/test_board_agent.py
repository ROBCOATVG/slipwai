"""What the runner keeps of a tool call, read off the protocol's updates as the agents send them.

OpenCode titles a call with its tool's name and sends what it is about in the update that follows — a
skill's `id`, a file's `path` — and a failed call's reason as content; the page's one line needs each.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.board_agent import telling, tool_fields


class ToolFieldsTest(unittest.TestCase):
    def test_the_telling_field_is_the_first_that_says_what_the_call_is_about(self) -> None:
        self.assertEqual(telling({"rawInput": {"command": "ls -la\nmore", "path": "x"}}), "ls -la")
        self.assertEqual(telling({"rawInput": {"id": "frontend-design"}}), "frontend-design")
        self.assertEqual(telling({"rawInput": {"path": "README.md"}}), "README.md")
        self.assertEqual(telling({"rawInput": {}}), "")
        self.assertEqual(telling({"rawInput": "not a dict"}), "")

    def test_a_failed_call_s_reason_is_kept_as_its_note(self) -> None:
        reason = {"type": "text", "text": "Unable to load skill frontend-design"}
        fields = tool_fields({"toolCallId": "c1", "title": "skill", "kind": "other", "status": "failed",
                              "rawInput": {"id": "frontend-design"}, "content": [{"type": "content", "content": reason}]})
        self.assertEqual((fields["what"], fields["note"], fields["path"]),
                         ("frontend-design", "Unable to load skill frontend-design", ""))
        self.assertEqual(tool_fields({"toolCallId": "c2"})["note"], "")


if __name__ == "__main__":
    unittest.main()
