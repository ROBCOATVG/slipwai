"""The board's card says what a headless session did, not only which tool it reached for.

A session redrawing eleven screens read as a column of `→ Write`, `→ Write`, `→ Bash`, while each event was
carrying the file it wrote, the sentence the agent gave its command and the job it handed a delegate.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.session_log import Folder, folded_line

ROOT = Path("/work/hr")


def tool(name: str, parent: str = "", **given: object) -> str:
    return json.dumps({"type": "assistant", "parent_tool_use_id": parent or None,
                       "message": {"content": [{"type": "tool_use", "id": "t", "name": name, "input": given}]}})


def system(subtype: str, **fields: object) -> str:
    return json.dumps({"type": "system", "subtype": subtype, **fields})


class FoldTest(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Folder(ROOT)

    def fold(self, *lines: str) -> list[str]:
        return [said for line in lines for said in self.folder.fold(line)]

    def test_a_file_tool_names_the_file_as_it_sits_in_the_project(self) -> None:
        self.assertEqual(self.fold(tool("Write", file_path="/work/hr/specs/001/mockups/03.html")),
                         ["→ Write specs/001/mockups/03.html"])

    def test_a_run_of_one_file_tool_lists_its_paths_under_one_name(self) -> None:
        self.assertEqual(self.fold(tool("Write", file_path="/work/hr/a.html"),
                                   tool("Write", file_path="/work/hr/b.html"),
                                   tool("Bash", description="Run the gate"),
                                   tool("Write", file_path="/work/hr/c.html")),
                         ["→ Write a.html", "    b.html", "→ Bash: Run the gate", "→ Write c.html"])

    def test_a_shell_command_says_its_description_or_else_its_first_line(self) -> None:
        self.assertEqual(self.fold(tool("Bash", command="make verify\necho done")), ["→ Bash: make verify"])
        self.assertTrue(self.fold(tool("Bash", command="x" * 400))[0].endswith("…"))

    def test_a_delegate_says_its_task_and_its_own_calls_sit_under_it(self) -> None:
        self.assertEqual(self.fold(tool("Agent", description="Redraw mock-ups 08 and 09"),
                                   tool("Write", parent="toolu_1", file_path="/work/hr/08.html")),
                         ["→ Agent: Redraw mock-ups 08 and 09", "    → Write 08.html"])

    def test_a_delegate_s_prose_is_left_out(self) -> None:
        said = json.dumps({"type": "assistant", "parent_tool_use_id": "toolu_1",
                           "message": {"content": [{"type": "text", "text": "Thinking aloud."}]}})
        self.assertEqual(self.fold(said), [])

    def test_a_background_task_says_when_it_finishes_and_a_foreground_one_does_not(self) -> None:
        self.assertEqual(self.fold(
            system("task_started", task_id="a", is_backgrounded=True, description="Redraw 01"),
            system("task_started", task_id="b", is_backgrounded=False, description="ls"),
            system("task_notification", task_id="b", status="completed", summary="ls"),
            system("task_notification", task_id="a", status="completed", summary="Redraw 01"),
            system("task_started", task_id="c", is_backgrounded=True),
            system("task_notification", task_id="c", status="failed", summary="Screenshot")),
            ["✓ Redraw 01", "✗ Screenshot — failed"])

    def test_a_browser_call_names_its_server_action_and_page(self) -> None:
        self.assertEqual(self.fold(tool("mcp__chrome-devtools__new_page", url="file:///work/hr/m/03.html")),
                         ["→ chrome-devtools: new_page: m/03.html"])

    def test_the_todo_list_is_a_count_and_the_item_in_hand(self) -> None:
        todos = [{"content": "Redraw 01", "status": "completed"},
                 {"content": "Redraw 02", "activeForm": "Redrawing 02", "status": "in_progress"},
                 {"content": "Storyboard", "status": "pending"}]
        self.assertEqual(self.fold(tool("TodoWrite", todos=todos)), ["☐ 1 of 3 done: Redrawing 02"])

    def test_the_harness_s_plumbing_says_nothing(self) -> None:
        self.assertEqual(self.fold(tool("ToolSearch", query="select:x"), tool("ScheduleWakeup", delaySeconds=60)), [])

    def test_a_workflow_says_its_name(self) -> None:
        self.assertEqual(self.fold(tool("Workflow", script="export const meta = {\n  name: 'redraw-mockups',")),
                         ["→ Workflow: redraw-mockups"])

    def test_one_line_on_its_own_still_folds(self) -> None:
        self.assertEqual(folded_line(tool("Read", file_path="/elsewhere/x.md")), ["→ Read /elsewhere/x.md"])
        self.assertEqual(folded_line("plain words"), ["plain words"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
