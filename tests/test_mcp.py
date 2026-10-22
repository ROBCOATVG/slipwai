"""The read side as tools, so the agent asks the harbour instead of a person copying a board between windows.

Two things are held here and they are the whole slice.

**The answers are the same fold.** `fleet` is what `slipwai fleet` prints, `stream` is what
`slipwai fleet <stream>` prints, and neither keeps anything: a board that can be wrong about what happened
is worse than no board. A tool that computed its own version of the board would be a second answer, and the
one you were looking at would be whichever window you had open.

**The one write is the bridge's own.** Answering a `told` goes through `bridge.tell`, so the line an agent
writes into a stream's deck log is the line a person typing into the bridge would have written — same
fields, same file, same reader at the other end.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import logs, mcp
from slipwai.assets import VERSION
from slipwai.cli_fleet import lines, stream_lines
from slipwai.project.harbour import CONFIG, harbour_config


class Harbour(unittest.TestCase):
    """A directory with logs in it, which is all the read side ever needs."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".slipwai").mkdir()
        (self.root / CONFIG).write_text(harbour_config(), encoding="utf-8")
        self.deck("ordering", logs.entry("claimed", fairway="ordering", slice="S1"))

    def deck(self, fairway: str, *entries: logs.Entry, feature: str = "ordering") -> None:
        path = self.root / logs.deck_path(feature, fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def call(self, name: str, **arguments: object) -> dict:
        found = mcp.answer({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                            "params": {"name": name, "arguments": arguments}}, self.root)
        assert found is not None
        return found

    def text(self, name: str, **arguments: object) -> str:
        found = self.call(name, **arguments)
        return "\n".join(part["text"] for part in found["result"]["content"])


class ProtocolTest(Harbour):
    """Enough of MCP to be a server, written against the standard library and nothing else."""

    def test_initialize_answers_with_the_keels_own_version(self) -> None:
        found = mcp.answer({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}, self.root)
        assert found is not None
        self.assertEqual(found["result"]["serverInfo"], {"name": mcp.NAME, "version": VERSION})
        self.assertIn("tools", found["result"]["capabilities"])

    def test_a_notification_is_not_answered(self) -> None:
        """A notification carries no id, and a reply to one is a protocol error at the other end."""
        self.assertIsNone(mcp.answer({"jsonrpc": "2.0", "method": "notifications/initialized"}, self.root))

    def test_a_method_the_server_has_not_got_is_an_error_rather_than_a_crash(self) -> None:
        found = mcp.answer({"jsonrpc": "2.0", "id": 2, "method": "resources/list"}, self.root)
        assert found is not None
        self.assertEqual(found["error"]["code"], mcp.NO_SUCH_METHOD)
        self.assertIn("resources/list", found["error"]["message"])

    def test_every_tool_is_listed_with_a_description_and_a_schema(self) -> None:
        found = mcp.answer({"jsonrpc": "2.0", "id": 3, "method": "tools/list"}, self.root)
        assert found is not None
        listed = found["result"]["tools"]
        self.assertEqual([tool["name"] for tool in listed], [tool.name for tool in mcp.TOOLS])
        for tool in listed:
            self.assertTrue(tool["description"])
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_the_read_side_is_read_and_the_one_write_says_so(self) -> None:
        """`tell` is the only tool that changes anything, and it is the write the bridge already allows."""
        writing = [tool.name for tool in mcp.TOOLS if tool.writes]
        self.assertEqual(writing, ["tell"])

    def test_a_tool_the_server_has_not_got_is_an_error_result_naming_the_ones_it_has(self) -> None:
        found = self.call("berth")
        self.assertTrue(found["result"]["isError"])
        self.assertIn("fleet", found["result"]["content"][0]["text"])


class SameFoldTest(Harbour):
    """What the tool answers is what the verb prints, because it is the same call."""

    def test_fleet_is_what_the_board_prints(self) -> None:
        self.assertEqual(self.text("fleet"), "\n".join(lines(self.root)))

    def test_a_stream_is_what_reading_that_streams_log_prints(self) -> None:
        self.assertEqual(self.text("stream", fairway="ordering"),
                         "\n".join(stream_lines(self.root, "ordering", mcp.RECENT)))

    def test_a_stream_nobody_has_written_names_the_streams_there_are(self) -> None:
        self.assertIn("ordering", self.text("stream", fairway="shipping"))

    def test_the_inbox_is_what_is_waiting_on_a_person_and_nothing_else(self) -> None:
        self.deck("ordering", logs.entry("told", fairway="ordering", message="which currency?"))
        said = self.text("inbox")
        self.assertIn("which currency?", said)
        self.assertNotIn("berths", said)

    def test_a_pause_is_listed_apart_and_not_counted_as_waiting_on_you(self) -> None:
        self.deck("ordering", logs.entry("claimed", fairway="ordering", slice="ORD-01"),
                  logs.entry("parked", fairway="ordering", slice="ORD-01", why="refused", cause="limit",
                             until="2999-01-01T20:40:00Z"))
        said = self.text("inbox")
        self.assertIn("waiting on you: nothing", said)
        self.assertIn("paused, nothing needed from you: 1", said)

    def test_an_empty_inbox_says_so_rather_than_answering_nothing(self) -> None:
        self.assertIn("nothing", self.text("inbox"))


class TellTest(Harbour):
    """The one write, and it is the bridge's."""

    def test_the_line_is_the_one_the_bridge_would_have_written(self) -> None:
        self.text("tell", fairway="ordering", message="use the minor unit")
        written = (self.root / logs.deck_path("ordering", "ordering")).read_text(encoding="utf-8")
        last = json.loads(written.splitlines()[-1])
        self.assertEqual(last["kind"], "told")
        self.assertEqual(last["fairway"], "ordering")
        self.assertEqual(last["message"], "use the minor unit")
        self.assertEqual(last["by"], "person", "a person's line is the only kind that answers a park")

    def test_under_a_dispatched_session_the_line_is_the_session_s(self) -> None:
        with mock.patch.dict(os.environ, {"SLIPWAI_FAIRWAY": "ordering"}):
            self.text("tell", fairway="ordering", message="for the host: two gates are red")
        written = (self.root / logs.deck_path("ordering", "ordering")).read_text(encoding="utf-8")
        self.assertEqual(json.loads(written.splitlines()[-1])["by"], "session")

    def test_a_message_with_nothing_in_it_is_an_error_result_rather_than_a_line(self) -> None:
        found = self.call("tell", fairway="ordering", message="   ")
        self.assertTrue(found["result"]["isError"])

    def test_a_stream_with_no_log_is_refused_because_there_is_nowhere_for_it_to_go(self) -> None:
        found = self.call("tell", fairway="shipping", message="anything")
        self.assertTrue(found["result"]["isError"])
        self.assertIn("shipping", found["result"]["content"][0]["text"])


class NotAHarbourTest(unittest.TestCase):
    """A directory with no logs in it is said, not drawn as an empty board."""

    def test_every_tool_refuses_a_directory_that_is_not_a_harbour(self) -> None:
        root = Path(tempfile.mkdtemp())
        found = mcp.answer({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                            "params": {"name": "fleet", "arguments": {}}}, root)
        assert found is not None
        self.assertTrue(found["result"]["isError"])
        self.assertIn("not a harbour", found["result"]["content"][0]["text"])


class GateTest(Harbour):
    """`clearance` and `check-chart` are the project's own scripts, run rather than reimplemented."""

    def script(self, path: str, body: str) -> None:
        place = self.root / path
        place.parent.mkdir(parents=True, exist_ok=True)
        place.write_text(body, encoding="utf-8")

    def test_clearance_returns_what_the_projects_own_script_printed(self) -> None:
        self.script("scripts/agents/clearance.py", "print('clearance: 3 of 3')\n")
        self.assertIn("clearance: 3 of 3", self.text("clearance"))

    def test_check_chart_returns_what_the_projects_own_script_printed(self) -> None:
        self.script("scripts/check-chart.py", "print('check-chart: 2 charts, 7 marks')\n")
        self.assertIn("7 marks", self.text("check-chart"))

    def test_a_failing_gate_is_an_error_result_carrying_what_it_said(self) -> None:
        self.script("scripts/check-chart.py",
                    "import sys; print('the chart does not hold', file=sys.stderr); sys.exit(1)\n")
        found = self.call("check-chart")
        self.assertTrue(found["result"]["isError"])
        self.assertIn("does not hold", found["result"]["content"][0]["text"])

    def test_a_project_without_the_script_says_which_file_is_missing(self) -> None:
        found = self.call("clearance")
        self.assertTrue(found["result"]["isError"])
        self.assertIn("scripts/agents/clearance.py", found["result"]["content"][0]["text"])


class TransportTest(Harbour):
    """One JSON object per line, in and out, which is what a harness speaks to a stdio server."""

    def test_the_server_answers_each_line_and_skips_the_notifications(self) -> None:
        sent = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        ]
        found = subprocess.run(
            [sys.executable, "-m", "slipwai", "mcp", "--root", str(self.root)],
            input="\n".join(sent) + "\n", capture_output=True, text=True, timeout=60,
            env={**mcp_env(), "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        )
        answers = [json.loads(line) for line in found.stdout.splitlines() if line.strip()]
        self.assertEqual([answer["id"] for answer in answers], [1, 2])

    def test_a_line_that_is_not_json_is_an_error_rather_than_the_end_of_the_session(self) -> None:
        answers = mcp.serve_lines(["{not json", json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/list"})],
                                  self.root)
        self.assertEqual(json.loads(answers[0])["error"]["code"], mcp.BAD_JSON)
        self.assertEqual(json.loads(answers[1])["id"], 9)


def mcp_env() -> dict[str, str]:
    import os
    return {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}


if __name__ == "__main__":
    unittest.main()
