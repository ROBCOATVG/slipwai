"""The code index under `/cruise`: a run says before its first iteration how the index will be reached, or that it
cannot be; Claude Code's iteration is passed the project's `.mcp.json` when the checkout carries one; an index call
is a line of the feed; and `status` says in how many iterations the index was asked — the number that tells an index
kept fresh from an index used, which a run in a fresh checkout showed are not the same thing.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_cruise_runner import cruise, enable, fake_harness

from slipwai.project.cruise_record import RUNNER_STREAM

MCP_CALL = json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
    {"type": "tool_use", "id": "toolu_mcp1", "name": "mcp__codegraph__codegraph_explore",
     "input": {"query": "what calls post_entry"}}]}, "parent_tool_use_id": None})
DONE = json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "cruise: {last}",
                   "permission_denials": []})


def index(repo: Path) -> None:
    """An adopted index: the database the gate reads, holding nothing this test needs beyond its presence."""
    (repo / ".codegraph").mkdir(exist_ok=True)
    connection = sqlite3.connect(repo / ".codegraph/codegraph.db")
    connection.execute("CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, content_hash TEXT, indexed_at REAL)")
    connection.commit()
    connection.close()


def bare_path(directory: Path, *tools: str) -> Path:
    """A PATH holding only what the runner itself needs, plus the named tools, so the machine cannot answer."""
    bare = directory / "bare"
    bare.mkdir(exist_ok=True)
    for tool in ("python3", "git", "sh", *tools):
        found = shutil.which(tool)
        assert found is not None, tool
        if not (bare / tool).exists():
            (bare / tool).symlink_to(found)
    return bare


class CruiseIndexTest(FactoryTestCase):
    def test_the_run_says_how_the_index_is_reached_before_the_first_iteration(self) -> None:
        """Nothing where no index was adopted. With one: over MCP where the row knows the project file and the file
        is here; through the CLI where it is not, naming the command that writes the file; and, where neither
        `codegraph` nor `npx` is on PATH, that no iteration can reach it — said at `start` and at the top of the
        run log, before a feed that fell back to text search without saying."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "reach", "standard", "python")
            enable(repo)
            here = Path(directory)
            fake_claude = here / "bin"
            fake_claude.mkdir()
            (fake_claude / "claude").write_text(f'#!/bin/sh\necho "$*" >> {here / "claude-args"}\n'
                                                'echo "cruise: done"\n')
            (fake_claude / "claude").chmod(0o755)
            env = {"PATH": f"{fake_claude}:{bare_path(here)}", "CRUISE_POLL_SECONDS": "0"}
            plain = cruise(repo, "run", env=env)
            self.assertEqual(plain.returncode, 0, plain.stderr)
            self.assertNotIn("code index", plain.stdout)
            index(repo)
            unreachable = cruise(repo, "run", env=env)
            self.assertIn("cruise: the code index (.codegraph) is here, but neither `codegraph` nor `npx` is on PATH: "
                          "no iteration can reach it", unreachable.stdout)
            (fake_claude / "codegraph").write_text("#!/bin/sh\nexit 0\n")
            (fake_claude / "codegraph").chmod(0o755)
            by_cli = cruise(repo, "run", env=env)
            self.assertIn("cruise: the code index (.codegraph) is here, but .mcp.json is not, so an iteration reaches "
                          "it only through the `codegraph` CLI; `./init --extension codegraph` writes the file",
                          by_cli.stdout)
            self.assertNotIn("--mcp-config", (here / "claude-args").read_text())
            (repo / ".mcp.json").write_text('{"mcpServers": {"codegraph": {}}}')
            over_mcp = cruise(repo, "run", env=env)
            self.assertIn("cruise: the code index is reached over MCP — .mcp.json is passed to every iteration with "
                          "its tools allowed", over_mcp.stdout)
            # The file is passed by name, after the row's own flags, only now that it exists.
            self.assertTrue((here / "claude-args").read_text().splitlines()[-1].endswith(
                "--allowedTools Bash,Skill,Agent,WebFetch,WebSearch,mcp__codegraph__* --mcp-config .mcp.json"))
            started = cruise(repo, "start", env=env)
            self.assertEqual(started.returncode, 0, started.stderr)
            self.assertIn("cruise: the code index is reached over MCP", started.stdout)
            for _ in range(200):
                if cruise(repo, "status", env=env).stdout.startswith("cruise: no runner is running"):
                    break
            # A harness whose row names no project file reaches the index through the CLI, and the run says so.
            enable(repo, harness="cursor-agent")
            (fake_claude / "agent").write_text('#!/bin/sh\necho "cruise: done"\n')
            (fake_claude / "agent").chmod(0o755)
            other = cruise(repo, "run", env=env)
            self.assertIn("cruise: the code index is reached through the `codegraph` CLI; this harness's row names no "
                          "project MCP file", other.stdout)

    def test_an_index_call_is_a_line_of_the_feed_and_status_counts_the_iterations_that_asked(self) -> None:
        """The gate checks that the index is fresh, not that anyone uses it: a run kept `check-codegraph` green with
        `codegraph sync` and answered every caller question with grep. So the feed shows each index call as it
        happens, and `status` says in how many of the stream's iterations the index was asked — and, when never,
        that every such answer was a text search."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "asked", "standard", "python")
            enable(repo)
            index(repo)
            first = MCP_CALL + "\n" + DONE.replace("{last}", "continue")
            second = DONE.replace("{last}", "continue")
            third = json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "toolu_b", "name": "Bash",
                 "input": {"command": "npx -y @colbymchenry/codegraph explore 'who calls post_entry'"}}]},
                "parent_tool_use_id": None}) + "\n" + DONE.replace("{last}", "done")
            (Path(directory) / "streams").mkdir()
            for number, text in enumerate((first, second, third), start=1):
                (Path(directory) / f"streams/{number}.jsonl").write_text(text + "\n")
            env = fake_harness(Path(directory), f'mkdir -p specs && touch "specs/progress-$n"\n'
                                                f'cat {Path(directory)}/streams/$n.jsonl')
            run = cruise(repo, "run", env={**env, "CRUISE_HARNESS_STREAM": "claude"})
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("  codegraph.codegraph_explore  what calls post_entry", run.stdout)
            self.assertIn("  $ npx -y @colbymchenry/codegraph explore 'who calls post_entry'", run.stdout)
            self.assertIn("# iteration 3 ", (repo / RUNNER_STREAM).read_text())
            status = cruise(repo, "status")
            self.assertIn("cruise: the code index was asked in 2 of 3 iteration(s) the stream holds (2 queries)",
                          status.stdout)
            # Never asked: the stream holds iterations, none of them touched the index, and status says what that means.
            (repo / RUNNER_STREAM).write_text("# iteration 1 2026-09-22T10:00:00Z\n" + second + "\n"
                                              "# iteration 2 2026-09-22T10:01:00Z\n" + second + "\n")
            never = cruise(repo, "status")
            self.assertIn("cruise: the code index was never asked in the 2 iteration(s) the stream holds — every "
                          "answer about callers and blast radius was a text search", never.stdout)
            # No index adopted: nothing to count, whatever the stream holds.
            shutil.rmtree(repo / ".codegraph")
            self.assertNotIn("code index", cruise(repo, "status").stdout)
