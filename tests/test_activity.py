"""What each slice is doing now: the activity log its session's hooks write, and the board's reading of it.

The writer is `scripts/agents/session.py`, run the way a harness runs it — an event on stdin, the captain's
names in the environment — in a project whose main checkout is a real Git repository, because the log is
filed under the main checkout whichever worktree the session runs in. The reader is `slipwai.activity`, and
the strip and the window are `slipwai.live_page`, held on lines written here.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from slipwai.activity import caption, fold, lines_of, live, log_path, task_of
from slipwai.assets import TOOLKIT_ROOT
from slipwai.live_page import strip_html, strip_payload, window_body, window_payload

AGENTS = TOOLKIT_ROOT / "scripts/agents"
NOW = datetime(2026, 10, 21, 9, 30, tzinfo=UTC)


def at(minutes_ago: float) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def line(minutes_ago: float, kind: str, what: str, agent: str = "session", **fields: object) -> dict:
    return {"t": at(minutes_ago), "kind": kind, "what": what, "agent": agent, **fields}


class WriterTest(unittest.TestCase):
    """`session.py`'s hooks and the session's own two sentences, landing in the main checkout's log."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in ("session.py", "logs.py", "benchmark.py", "registry.json"):
            (place / name).write_text((AGENTS / name).read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.named = {"SLIPWAI_FAIRWAY": "leaver-offboarding", "SLIPWAI_SLICE": "L10", "SLIPWAI_STAGE": "drive"}

    def fire(self, *argv: str, event: dict | None = None, named: dict | None = None) -> subprocess.CompletedProcess:
        environment = {key: value for key, value in os.environ.items() if not key.startswith("SLIPWAI_")}
        return subprocess.run([sys.executable, str(self.root / "scripts/agents/session.py"), *argv],
                              input=json.dumps(event or {}), capture_output=True, text=True, cwd=self.root,
                              timeout=60, env={**environment, **(self.named if named is None else named)})

    def written(self) -> list[dict]:
        path = self.root / ".slipwai/activity/leaver-offboarding/L10.jsonl"
        if not path.is_file():
            return []
        return [json.loads(one) for one in path.read_text(encoding="utf-8").splitlines()]

    def test_a_sub_agent_is_a_start_a_link_and_a_done_with_its_commit(self) -> None:
        self.fire("before-delegate", event={"tool_use_id": "toolu_1", "tool_input": {
            "description": "L10 T018: R17 redraft confirm", "subagent_type": "sail-implement-shipwright",
            "model": "sonnet", "prompt": "a long brief nobody reads on a board"}})
        self.fire("agent-started", event={"agent_id": "a3cd25", "agent_type": "sail-implement-shipwright"})
        self.fire("before-command", event={"agent_id": "a3cd25", "agent_type": "sail-implement-shipwright",
                                           "tool_input": {"command": "make unit", "description": "Run unit tests"}})
        self.fire("after-delegate", event={"tool_use_id": "toolu_1", "tool_name": "Agent", "tool_input": {
            "description": "L10 T018: R17 redraft confirm", "subagent_type": "sail-implement-shipwright"},
            "tool_response": {"agentId": "a3cd25", "totalTokens": 61000,
                              "content": "commit a5fd5e2 — R17 green"}})
        kinds = [(one["kind"], one["agent"], one["what"]) for one in self.written()]
        self.assertEqual(kinds, [("start", "toolu_1", "L10 T018: R17 redraft confirm"),
                                 ("link", "a3cd25", "sail-implement-shipwright"),
                                 ("ran", "a3cd25", "Run unit tests"),
                                 ("done", "toolu_1", "L10 T018: R17 redraft confirm")])
        start, done = self.written()[0], self.written()[-1]
        self.assertEqual((start["role"], start["model"], start["slice"], start["fairway"]),
                         ("sail-implement-shipwright", "sonnet", "L10", "leaver-offboarding"))
        self.assertNotIn("prompt", json.dumps(start), "a brief is not a line for a person")
        self.assertEqual((done["commit"], done["id"], done["tokens"]), ("a5fd5e2", "a3cd25", 61000))

    def test_a_failed_command_is_its_own_line_with_the_first_line_of_why(self) -> None:
        self.fire("after-failure", event={"tool_name": "Bash", "agent_id": "a1", "tool_input": {
            "command": "npm test", "description": "Run test suite"}, "error": "Exit code 1\nError: nope"})
        self.fire("after-failure", event={"tool_name": "Read", "tool_input": {"file_path": "x"}, "error": "gone"})
        self.assertEqual([(one["kind"], one["what"], one["said"]) for one in self.written()],
                         [("failed", "Run test suite", "Exit code 1")])

    def test_a_command_with_no_description_is_said_by_its_first_words(self) -> None:
        self.fire("before-command", event={"tool_input": {"command": "git log --oneline -5 main -- specs x y z"}})
        self.assertEqual(self.written()[0]["what"], "git log --oneline -5 main --")

    def test_the_session_says_what_it_is_doing_and_what_it_waits_on(self) -> None:
        self.assertEqual(self.fire("say", "T018", "done", "(a5fd5e2).", "Dispatching", "T018a.").returncode, 0)
        self.fire("waiting", "the UX gates")
        self.assertEqual([(one["kind"], one["what"]) for one in self.written()],
                         [("said", "T018 done (a5fd5e2). Dispatching T018a."), ("wait", "the UX gates")])
        self.assertEqual(self.fire("say").returncode, 1)

    def test_saying_something_is_neither_a_command_line_nor_a_write_to_scripts(self) -> None:
        """The sentence may hold anything a person writes, `>` included, and the guard that refuses a shell
        write to `scripts/` must not read a sentence about the work as one."""
        done = self.fire("before-command", event={"tool_input": {
            "command": 'python3 scripts/agents/session.py say "T3 > T2: rm the old notice"'}})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.written(), [])

    def test_a_session_nobody_dispatched_writes_nothing(self) -> None:
        self.fire("say", "hello", named={})
        self.fire("before-command", event={"tool_input": {"command": "ls"}}, named={})
        self.assertFalse((self.root / ".slipwai/activity").exists())

    def test_a_worktree_files_its_lines_under_the_main_checkout(self) -> None:
        subprocess.run(["git", "-C", str(self.root), "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q",
                        "--allow-empty", "-m", "one"], check=True)
        berth = self.root.parent / f"{self.root.name}-L10"
        subprocess.run(["git", "-C", str(self.root), "worktree", "add", "-q", "--detach", str(berth)], check=True)
        (berth / "project.json").write_text("{}", encoding="utf-8")
        (berth / "scripts/agents").mkdir(parents=True)
        for name in ("session.py", "logs.py"):
            (berth / "scripts/agents" / name).write_text((AGENTS / name).read_text(encoding="utf-8"),
                                                         encoding="utf-8")
        subprocess.run([sys.executable, str(berth / "scripts/agents/session.py"), "say", "from the berth"],
                       input="{}", capture_output=True, text=True, cwd=berth, timeout=60,
                       env={**os.environ, **self.named})
        self.assertEqual([one["what"] for one in self.written()], ["from the berth"])
        self.assertFalse((berth / ".slipwai/activity").exists())

    def test_a_stage_opened_and_closed_is_a_line_on_every_harness(self) -> None:
        folder = self.root / "specs/001/slices/L10"
        folder.mkdir(parents=True)
        for argv in (["start", str(folder), "implement"], ["end", str(folder), "implement", "outcome=accepted"]):
            subprocess.run([sys.executable, str(self.root / "scripts/agents/benchmark.py"), *argv], cwd=self.root,
                           capture_output=True, text=True, timeout=60, env={**os.environ, **self.named})
        self.assertEqual([(one["kind"], one["what"]) for one in self.written()],
                         [("stage", "implement started"), ("stage", "implement ended: accepted")])


class FoldTest(unittest.TestCase):
    """One slice's lines, read as what it is doing now and what a person would step in for."""

    def test_a_brief_is_its_task_and_its_words(self) -> None:
        self.assertEqual(task_of("L10 T018: R17 redraft confirm", "L10"), ("T018", "R17 redraft confirm"))
        self.assertEqual(task_of("Review the slice's whole diff", "L10"), ("", "Review the slice's whole diff"))

    def test_the_sub_agents_are_their_lanes_and_their_own_commands_follow_them(self) -> None:
        lines = [line(30, "start", "L10 T017: R15 failures, retry", "toolu_1", role="sail-implement-shipwright"),
                 line(29, "link", "sail-implement-shipwright", "a17", role="sail-implement-shipwright"),
                 line(25, "ran", "Run unit tests", "a17"),
                 line(20, "done", "L10 T017: R15 failures, retry", "toolu_1", commit="9f1fa53", id="a17"),
                 line(4, "start", "L10 T018: R17 redraft confirm", "toolu_2", role="sail-implement-shipwright",
                      model="sonnet"),
                 line(3, "link", "sail-implement-shipwright", "a18", role="sail-implement-shipwright"),
                 line(1, "ran", "Read the page", "a18"),
                 line(0.5, "said", "T017 done (9f1fa53). Dispatching T018.")]
        found = fold(lines, "L10", NOW.timestamp())
        self.assertEqual([(one["task"], one["commit"]) for one in found["agents"]], [("T017", "9f1fa53"), ("T018", "")])
        self.assertEqual(found["current"]["what"], "R17 redraft confirm")
        self.assertEqual(found["current"]["last"], "Read the page", "its own command, matched by the link line")
        self.assertEqual(found["said"], "T017 done (9f1fa53). Dispatching T018.")
        self.assertEqual(found["warnings"], [])

    def test_a_task_far_past_its_slices_usual_is_said_to_be_taking_long(self) -> None:
        lines = [line(60, "start", "L13 T015: one", "t1", role="r"), line(54, "done", "L13 T015: one", "t1"),
                 line(50, "start", "L13 T016: two", "t2", role="r"), line(44, "done", "L13 T016: two", "t2"),
                 line(14, "start", "L13 T017: styling and previews", "t3", role="r"), line(1, "ran", "x", "t3")]
        found = fold(lines, "L13", NOW.timestamp())
        self.assertEqual([one["kind"] for one in found["warnings"]], ["long"])
        self.assertIn("14m on T017", found["warnings"][0]["said"])
        self.assertIn("its others took 6m", found["warnings"][0]["said"])

    def test_the_same_command_failing_three_times_running_is_going_round_in_circles(self) -> None:
        lines = [line(5 - n, "failed", "Run unit tests", "a1") for n in range(3)]
        self.assertEqual([one["kind"] for one in fold(lines, "L10", NOW.timestamp())["warnings"]], ["circles"])
        mended = lines[:2] + [line(2.5, "ran", "Run unit tests", "a1"), lines[2]]
        self.assertEqual(fold(mended, "L10", NOW.timestamp())["warnings"], [])

    def test_nothing_for_a_while_is_quiet(self) -> None:
        found = fold([line(9, "ran", "make verify")], "L08", NOW.timestamp())
        self.assertEqual([one["kind"] for one in found["warnings"]], ["quiet"])
        self.assertEqual(fold([line(2, "ran", "make verify")], "L08", NOW.timestamp())["warnings"], [])


class BoardTest(unittest.TestCase):
    """The strip, the caption and the window, read off a project's logs."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())

    def log(self, slice_id: str, lines: list[dict]) -> None:
        path = self.root / ".slipwai/activity/leaver-offboarding" / f"{slice_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(one) + "\n" for one in lines) + "not json\n", encoding="utf-8")

    def rows(self) -> list[dict[str, str]]:
        return [{"slice": "L10", "fairway": "leaver-offboarding", "state": "working", "chip": "Implementing · 19/23"},
                {"slice": "L13", "fairway": "leaver-offboarding", "state": "working", "chip": "Implementing · 17/23"},
                {"slice": "L08", "fairway": "leaver-offboarding", "state": "working", "chip": "Review"},
                {"slice": "L01", "fairway": "leaver-offboarding", "state": "done"}]

    def test_a_log_is_read_from_its_folder_and_nowhere_else(self) -> None:
        self.log("L10", [line(1, "said", "hello")])
        self.assertEqual([one["what"] for one in lines_of(self.root, "leaver-offboarding", "L10")], ["hello"])
        self.assertIsNone(log_path(self.root, "../..", "etc"))
        self.assertEqual(lines_of(self.root, "leaver-offboarding", "../../x"), [])

    def test_two_slices_waiting_at_once_are_each_told_of_the_other(self) -> None:
        now = datetime.now(UTC)
        stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.log("L08", [{"t": stamp, "kind": "wait", "what": "the UX gates", "agent": "session"}])
        self.log("L13", [{"t": stamp, "kind": "wait", "what": "its browser run", "agent": "session"}])
        folds = live(self.root, self.rows())
        self.assertEqual(sorted(folds), ["leaver-offboarding/L08", "leaver-offboarding/L13"],
                         "only working slices with a log; a done one is not read")
        self.assertIn("L13 waiting too", folds["leaver-offboarding/L08"]["warnings"][0]["said"])
        self.assertTrue(caption(folds["leaver-offboarding/L08"]).startswith("waiting on the UX gates · "))

    def test_the_strip_puts_the_slice_that_needs_a_look_first_and_names_one_with_no_log(self) -> None:
        now = datetime.now(UTC)
        self.log("L10", [{"t": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "kind": "said", "what": "Dispatching T018a.",
                          "agent": "session"}])
        self.log("L13", [{"t": (now - timedelta(minutes=12)).strftime("%Y-%m-%dT%H:%M:%SZ"), "kind": "ran",
                          "what": "Run unit tests", "agent": "session"}])
        rows = self.rows()
        drawn = strip_html(rows, live(self.root, rows))
        self.assertLess(drawn.index(">L13<"), drawn.index(">L10<"), "a quiet slice is the one to look at")
        self.assertIn("nothing for 12m", drawn)
        self.assertIn("“Dispatching T018a.”", drawn)
        self.assertIn("no activity log yet", drawn, "L08 has none, and says so rather than looking idle")
        self.assertIn('href="/slice?fairway=leaver-offboarding&amp;slice=L10"', drawn)
        self.assertNotIn(">L01<", drawn)
        self.assertEqual(strip_html([row for row in rows if row["state"] == "done"], {}), "")
        self.assertEqual(json.loads(strip_payload(rows, live(self.root, rows)))["html"], drawn)

    def test_the_window_is_lanes_a_feed_and_a_summary(self) -> None:
        now = datetime.now(UTC)

        def ago(minutes: float) -> str:
            return (now - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.log("L10", [
            {"t": ago(20), "kind": "stage", "what": "implement started", "agent": "session"},
            {"t": ago(10), "kind": "start", "what": "L10 T018: R17 redraft confirm", "agent": "t1",
             "role": "sail-implement-shipwright", "model": "sonnet"},
            {"t": ago(4), "kind": "done", "what": "L10 T018: R17 redraft confirm", "agent": "t1",
             "role": "sail-implement-shipwright", "commit": "a5fd5e2"},
            {"t": ago(1), "kind": "said", "what": "T018 done (a5fd5e2). <b>Dispatching</b> T018a.",
             "agent": "session"}])
        drawn = window_body(self.root, "leaver-offboarding", "L10")
        self.assertIn("T018", drawn)
        self.assertIn("implement-shipwright T018 R17 redraft confirm · commit a5fd5e2", drawn)
        self.assertIn("implement started", drawn)
        self.assertIn("&lt;b&gt;Dispatching&lt;/b&gt;", drawn, "what a session says is text, never markup")
        self.assertIn("Commits handed back:</b> 1", drawn)
        self.assertEqual(json.loads(window_payload(self.root, "leaver-offboarding", "L10"))["html"], drawn)
        self.assertIn("No activity log for this slice yet", window_body(self.root, "leaver-offboarding", "L99"))


if __name__ == "__main__":
    unittest.main()
