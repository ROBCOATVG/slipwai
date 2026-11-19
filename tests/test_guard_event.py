"""What a `before-search` guard is handed: the search itself, and not only the word searched for.

The point existed and could not hold the rule it was added for (#121). `session.py` passed a guard
`pattern or query or command` and nothing else, so a guard could not tell a search of `specs/` from a search
of the source, a Glob from a Grep, a shell command from a pattern, or one session from another — and the
`tool` the contract page promised was never delivered. A guard that had to refuse *a symbol search of the
source, until this session has asked the index* had nothing to decide any of that with.

So the event is forwarded: one JSON object on the guard's stdin, normalised, with the fields that are not
there left out rather than sent empty. `SLIPWAI_QUERY` stays exactly what it was, because a guard written
before this reads that and nothing else.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from guard_project import PROBE, TOOLKIT, Project

from slipwai import guards

DOCS = Path(__file__).resolve().parents[1] / "docs/extensions.md"
#: A Claude Code `PreToolUse` event, as the harness writes one: what a sub-agent's Grep looks like.
GREP = {"session_id": "s-1", "transcript_path": "/home/x/.claude/t.jsonl", "cwd": "/work/project",
        "permission_mode": "default", "hook_event_name": "PreToolUse", "tool_name": "Grep",
        "tool_input": {"pattern": "place_order", "path": "specs/", "glob": "*.md", "output_mode": "content"},
        "tool_use_id": "toolu_1", "agent_id": "a-7", "agent_type": "sail-implement-shipwright"}


class HandedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()
        self.addCleanup(self.project.close)
        self.project.extension("probe", {"before-search": {"run": "g.py", "budget": "30s"},
                                         "before-write": {"run": "g.py", "budget": "30s"},
                                         "before-command": {"run": "g.py", "budget": "30s"},
                                         "before-fetch": {"run": "g.py", "budget": "30s"}}, **{"g.py": PROBE})
        self.project.guards("--elect", "probe")

    def one(self) -> dict:
        rows = self.project.handed("probe")
        self.assertEqual(len(rows), 1, rows)
        return rows[0]

    def test_a_grep_arrives_whole_and_says_whose_it_is(self) -> None:
        done = self.project.session("before-search", GREP, SLIPWAI_STAGE="implement", SLIPWAI_SLICE="1.2",
                                    SLIPWAI_FAIRWAY="ORD")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.one()["event"], {
            "v": 1, "point": "before-search", "tool": "Grep", "query": "place_order",
            "pattern": "place_order", "path": "specs/", "glob": "*.md", "cwd": "/work/project",
            "session": "s-1", "agent": "a-7", "agent_type": "sail-implement-shipwright",
            "stage": "implement", "slice": "1.2", "fairway": "ORD"})

    def test_what_a_search_did_not_name_is_absent_rather_than_empty(self) -> None:
        """An empty string is a claim — *the path was nothing* — and a guard that reads `""` as *the whole
        tree* and one that reads it as *no evidence* decide opposite ways. A key that is not there is not."""
        self.project.session("before-search", {"session_id": "s-1", "cwd": "/w", "tool_name": "Grep",
                                               "tool_input": {"pattern": "place_order", "path": ""}})
        self.assertEqual(self.one()["event"], {"v": 1, "point": "before-search", "tool": "Grep",
                                               "query": "place_order", "pattern": "place_order",
                                               "cwd": "/w", "session": "s-1"})

    def test_a_glob_is_told_apart_from_a_grep(self) -> None:
        self.project.session("before-search", {"session_id": "s-1", "cwd": "/w", "tool_name": "Glob",
                                               "tool_input": {"pattern": "**/order*.py", "path": "apps"}})
        event = self.one()["event"]
        self.assertEqual((event["tool"], event["pattern"], event["path"]), ("Glob", "**/order*.py", "apps"))
        self.assertNotIn("command", event)

    def test_a_shell_search_hands_over_the_command_and_not_a_pattern(self) -> None:
        """A `grep` typed into the shell is the same search by another door. What the guard is handed is
        the command, as a command: it is the guard's to parse, and a pattern the keel guessed out of it
        would be a second parser of shell that nobody could get right."""
        self.project.session("before-search", {"session_id": "s-1", "cwd": "/w", "tool_name": "Bash",
                                               "tool_input": {"command": "rg -n place_order apps/",
                                                              "description": "find the handler"}})
        event = self.one()["event"]
        self.assertEqual(event["command"], "rg -n place_order apps/")
        self.assertEqual(event["query"], "rg -n place_order apps/")
        self.assertNotIn("pattern", event)
        self.assertNotIn("description", event)

    def test_a_guard_is_not_handed_the_conversation(self) -> None:
        """The harness's event names the transcript, and a guard that was given the path would be one read
        away from everything the person and the agent said. A search guard decides about a search."""
        self.project.session("before-search", GREP)
        handed = self.one()
        self.assertNotIn("transcript", handed["stdin"])
        self.assertNotIn("toolu_1", handed["stdin"])
        self.assertNotIn("output_mode", handed["stdin"])

    def test_the_variables_a_guard_already_read_are_what_they_were(self) -> None:
        self.project.session("before-search", GREP, SLIPWAI_STAGE="implement")
        environment = self.one()["environment"]
        self.assertEqual(environment["SLIPWAI_QUERY"], "place_order")
        self.assertEqual(environment["SLIPWAI_STAGE"], "implement")
        self.assertEqual(environment["SLIPWAI_TOOL"], "Grep")
        self.assertEqual(environment["SLIPWAI_POINT"], "before-search")

    def test_the_tool_the_contract_promises_reaches_every_tool_call_guard(self) -> None:
        for verb, tool, tool_input in (("before-write", "Edit", {"file_path": "apps/x.py"}),
                                       ("before-command", "Bash", {"command": "ls"}),
                                       ("before-fetch", "WebFetch", {"url": "https://example.com/a"})):
            with self.subTest(verb=verb):
                self.project.session(verb, {"tool_name": tool, "tool_input": tool_input, "cwd": "/w"})
                self.assertEqual(self.project.handed("probe")[-1]["environment"]["SLIPWAI_TOOL"], tool)

    def test_an_event_that_names_no_tool_promises_none(self) -> None:
        self.project.session("before-search", {"tool_input": {"pattern": "x"}})
        handed = self.one()
        self.assertNotIn("SLIPWAI_TOOL", handed["environment"])
        self.assertNotIn("tool", handed["event"])


class StillTheOldContractTest(unittest.TestCase):
    """A guard written before the event was forwarded reads `SLIPWAI_QUERY` and never touches stdin."""

    OLD = ("import os, sys\n"
           "if 'place_order' in os.environ.get('SLIPWAI_QUERY', ''):\n"
           "    print('ask the index: codegraph explore place_order', file=sys.stderr)\n"
           "    sys.exit(2)\n")

    def setUp(self) -> None:
        self.project = Project()
        self.addCleanup(self.project.close)
        self.project.extension("old", {"before-search": {"run": "g.py", "budget": "30s"}}, **{"g.py": self.OLD})
        self.project.guards("--elect", "old")

    def test_it_refuses_what_it_refused_and_its_words_reach_the_agent(self) -> None:
        done = self.project.session("before-search", GREP)
        self.assertEqual(done.returncode, 2)
        self.assertIn("ask the index: codegraph explore place_order", done.stderr)
        self.assertEqual(self.project.session("before-search", {**GREP, "tool_input": {"pattern": "x"}})
                         .returncode, 0)

    def test_a_command_too_long_for_a_pipe_does_not_wedge_a_guard_that_never_reads_it(self) -> None:
        """The event is written where the guard may read it and nobody waits for it to. A megabyte of
        command into a pipe nobody empties is a writer blocked for ever, in front of a tool call."""
        long = "echo " + "place_order " * 100_000
        done = self.project.session("before-search", {"tool_name": "Bash", "tool_input": {"command": long}})
        self.assertEqual(done.returncode, 2)

    def test_fired_by_hand_it_waits_for_no_event(self) -> None:
        """`guards.py before-search --query x` at a terminal has a keyboard for a stdin. It reads the event
        only when it is told one is there."""
        process = subprocess.Popen([sys.executable, str(self.project.extensions / "guards.py"),
                                    "before-search", "--query", "place_order"], cwd=self.project.root,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(process.kill)
        try:
            self.assertEqual(process.wait(timeout=120), 2)
        finally:
            for pipe in (process.stdin, process.stdout, process.stderr):
                assert pipe is not None
                pipe.close()


class FailsOpenTest(unittest.TestCase):
    """A guard that cannot answer has refused nothing, and the budget is the longest a search can wait."""

    def setUp(self) -> None:
        self.project = Project()
        self.addCleanup(self.project.close)

    def guard(self, body: str, **declared: str) -> None:
        self.project.extension("cg", {"before-search": {"run": "g.py", **declared}}, **{"g.py": body})
        self.project.guards("--elect", "cg")

    def test_a_crash_a_wrong_code_and_a_missing_script_all_let_the_search_run(self) -> None:
        for body in ("raise RuntimeError('broken')\n", "raise SystemExit(1)\n", "raise SystemExit(3)\n",
                     "import json, sys\njson.loads(sys.stdin.read())['no-such-key']\n"):
            with self.subTest(body=body.strip()):
                self.guard(body)
                self.assertEqual(self.project.session("before-search", GREP).returncode, 0)
        (self.project.extensions / "cg/g.py").unlink()
        done = self.project.session("before-search", GREP)
        self.assertEqual(done.returncode, 0)
        self.assertIn("is not in this project", done.stderr)

    def test_a_guard_that_left_something_running_cannot_hold_the_search_past_its_budget(self) -> None:
        """Ended at its budget, and the call goes ahead — even where the guard started something that
        outlives it and still holds its output open. Waiting for that output to close was waiting on a
        process nobody had a budget for.

        The stand-in guard and what it starts both wait on a file this case removes when it is over, so
        neither ever finishes on its own: what is held is that the runner comes back at all."""
        marker = self.project.root / "held"
        marker.write_text("", encoding="utf-8")
        self.addCleanup(lambda: marker.unlink(missing_ok=True))
        waits = ("import os, sys, time\n"
                 f"while os.path.exists({str(marker)!r}):\n    time.sleep(0.05)\n")
        self.guard("import subprocess, sys\n"
                   f"subprocess.Popen([sys.executable, '-c', {waits!r}])\n" + waits, budget="1s")
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            done = subprocess.run([sys.executable, str(self.project.extensions / "guards.py"),
                                   "before-search", "--query", "x"], cwd=self.project.root,
                                  stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=120)
            err.seek(0)
            said = err.read().decode("utf-8", "replace")
        self.assertEqual(done.returncode, 0)
        self.assertIn("budget", said)


class ContractTest(unittest.TestCase):
    """The page an extension author reads, the keel's own list and the script that builds the event say
    one thing. A field in one and not the others is a promise somebody will write a guard against."""

    def documented(self) -> list[str]:
        section = DOCS.read_text(encoding="utf-8").split("### What a `before-search` guard is handed", 1)[1]
        table = section.split("**A field that the search did not name", 1)[0]
        return re.findall(r"^\| `([a-z_]+)` \|", table, re.MULTILINE)

    def built(self) -> list[str]:
        source = (TOOLKIT / "scripts/agents/tool_event.py").read_text(encoding="utf-8")
        return json.loads(re.search(r"^FIELDS = (\[.*?\])$", source, re.MULTILINE | re.DOTALL).group(1))  # type: ignore[union-attr]

    def test_the_page_lists_exactly_what_the_event_carries(self) -> None:
        self.assertEqual(self.documented(), list(guards.SEARCH_EVENT))
        self.assertEqual(self.built(), list(guards.SEARCH_EVENT))

    def test_the_keel_says_a_search_guard_is_given_them(self) -> None:
        self.assertEqual(set(guards.SEARCH_EVENT) - set(guards.guard("before-search").given), {"v", "point"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
