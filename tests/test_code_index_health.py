"""The code index held by the harness and the runner: sound before an iteration, current during it, asked first.

A `/cruise` iteration on an indexed project found `codegraph_explore` failing on "database disk image is malformed",
repaired the index by hand, asked it once and went back to grep; its delegates located `decideCue` and its callers
with `grep -n` and `sed -n` although their brief said to ask the index; and nothing counted which of them asked. So:
the runner opens and integrity-checks the database before every iteration, rebuilds a corrupt one and syncs a stale
one; Claude Code's hooks refuse a symbol search of the source until the asker has queried the index, and sync it
after each delegate; `check-codegraph` fails a corrupt database instead of skipping it; and the log, the feed and
`status` count index queries per delegate and name the one that grepped first. Every CLI here is a fake that keeps
a real SQLite database, so the integrity checks and the rebuild are real.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_cruise_index import bare_path
from test_cruise_runner import cruise, enable, fake_harness, logged

# `codegraph` as far as the index goes: `init`, `index` and `sync` write a real database describing every tracked
# Python file and defining `decideCue`; `explore` and `callers` answer only from a database that passes SQLite's
# integrity check, the way the real one fails on a malformed file. Every call is logged.
FAKE_CODEGRAPH = """#!/usr/bin/env python3
import hashlib, os, sqlite3, subprocess, sys
from pathlib import Path
with open(os.environ["FAKE_CODEGRAPH_LOG"], "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
db = Path(".codegraph/codegraph.db")
verb = sys.argv[1]
if verb in ("init", "index", "sync"):
    db.parent.mkdir(exist_ok=True)
    db.unlink(missing_ok=True)
    connection = sqlite3.connect(db)
    connection.execute("CREATE TABLE files (path TEXT PRIMARY KEY, content_hash TEXT, indexed_at REAL)")
    connection.execute("CREATE TABLE nodes (id TEXT, kind TEXT, name TEXT)")
    for path in subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split():
        if path.endswith(".py") and Path(path).is_file():
            digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            connection.execute("INSERT INTO files VALUES (?, ?, 1.0)", (path, digest))
    connection.execute("INSERT INTO nodes VALUES ('1', 'function', 'decideCue')")
    connection.commit()
    connection.close()
    print("Done")
elif verb in ("explore", "callers", "impact"):
    try:
        verdict = sqlite3.connect(f"file:{db}?mode=ro", uri=True).execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.Error as error:
        sys.exit(f"Error: {error}")
    if verdict != "ok":
        sys.exit(f"Error: {verdict}")
    print(f"{verb}: src/submit.ts submitCue -> decideCue")
"""


def tool_result(identifier: str, text: str, parent: str | None, error: bool) -> str:
    return json.dumps({"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": identifier, "content": text, "is_error": error}]},
        "parent_tool_use_id": parent})


def tool_use(identifier: str, name: str, given: dict, parent: str | None = None) -> str:
    return json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": identifier, "name": name, "input": given}]}, "parent_tool_use_id": parent})


DONE = json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "cruise: done",
                   "permission_denials": []})


class CodeIndexHealthTest(FactoryTestCase):
    def indexed(self, directory: str, name: str) -> tuple[Path, dict[str, str], Path]:
        """A project with an index built by the fake CLI, and a PATH on which that CLI is the only route."""
        repo = self.generate(directory, name, "standard", "python")
        here = Path(directory)
        tools = here / "tools"
        tools.mkdir()
        (tools / "codegraph").write_text(FAKE_CODEGRAPH)
        (tools / "codegraph").chmod(0o755)
        log = here / "codegraph-calls"
        # No `npx`, so the fake is the route; the few tools the fake harness itself runs.
        env = {"PATH": f"{tools}:{bare_path(here, 'dirname', 'cat', 'mkdir', 'touch')}", "FAKE_CODEGRAPH_LOG": str(log)}
        built = subprocess.run(["scripts/codegraph", "init", "-y", "."], cwd=repo, env={**os.environ, **env},
                               text=True, capture_output=True)
        self.assertEqual(built.returncode, 0, built.stderr)
        log.unlink()
        return repo, env, log

    def guard(self, repo: Path, env: dict[str, str], tool: str, given: dict, agent: str | None = None):
        happened = {"session_id": "s1", "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": given,
                    **({"agent_id": agent, "agent_type": "drive-tasks"} if agent else {})}
        return subprocess.run(["python3", "scripts/agents/code_index.py", "guard"], cwd=repo, text=True,
                              capture_output=True, env={**os.environ, **env}, input=json.dumps(happened))

    def test_a_corrupt_index_is_rebuilt_by_the_runner_before_the_iteration_asks_it(self) -> None:
        """The acceptance the report asked for: corrupt the database, start the run, and the iteration's first index
        call answers — the iteration never touches the index to repair it. The entry and the feed say what the
        runner did, and the corrupt copy is kept aside rather than deleted."""
        with tempfile.TemporaryDirectory() as directory:
            repo, env, log = self.indexed(directory, "corrupted")
            enable(repo)
            database = repo / ".codegraph/codegraph.db"
            database.write_bytes(b"this is not a database " * 400)
            asked = Path(directory) / "asked"
            harness = fake_harness(Path(directory), f"scripts/codegraph explore decideCue > {asked} 2>&1\n"
                                                    'echo "cruise: done"')
            run = cruise(repo, "run", env={**env, **harness})
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("cruise: code index before iteration 1 — rebuilt: the database failed its integrity check",
                          run.stdout)
            self.assertEqual(asked.read_text().strip(), "explore: src/submit.ts submitCue -> decideCue")
            calls = log.read_text().splitlines()
            self.assertEqual(calls[0], "init -y .", "the runner rebuilt before the iteration ran")
            self.assertEqual(calls[-1], "explore decideCue", "the iteration's only index call was a query")
            entry = logged(repo)[-1]
            self.assertEqual(entry["index"]["state"], "rebuilt")
            aside = list((repo / ".codegraph/corrupt").iterdir())
            self.assertEqual([path.read_bytes()[:23] for path in aside], [b"this is not a database "])

            # Sound and current: nothing to do, and the entry says so.
            again = cruise(repo, "run", env={**env, **harness})
            self.assertIn("cruise: code index before iteration 2 — current", again.stdout)
            # Behind the tree: synced before the iteration, not during it.
            stale = next(path for path in repo.rglob("*.py") if ".codegraph" not in path.parts and "scripts" not in
                         path.parts)
            stale.write_text(stale.read_text() + "\n# changed\n")
            log.unlink()
            synced = cruise(repo, "run", env={**env, **harness})
            self.assertIn("cruise: code index before iteration 3 — synced: 1 tracked file(s) were ahead of the index",
                          synced.stdout)
            self.assertEqual(log.read_text().splitlines()[0], "sync .")

    def test_the_gate_repairs_a_corrupt_or_stale_index_before_it_judges_and_fails_one_it_cannot(self) -> None:
        """`codegraph status` and `sync` call a malformed database up to date, and the gate used to skip one whose
        schema it could not read. Now, where the CLI is reachable, it rebuilds a corrupt one and syncs a stale one
        before comparing — the database is derived and ignored, so a `/drive` verify never goes red on a broken
        index it could have mended — and fails, saying how to repair it, where it cannot."""
        with tempfile.TemporaryDirectory() as directory:
            repo, env, log = self.indexed(directory, "gated")
            gate = ["python3", "scripts/check-codegraph.py"]
            clean = subprocess.run(gate, cwd=repo, env={**os.environ, **env}, text=True, capture_output=True)
            self.assertEqual(clean.returncode, 0, clean.stderr)
            stale = next(path for path in repo.rglob("*.py") if ".codegraph" not in path.parts and "scripts" not in
                         path.parts)
            stale.write_text(stale.read_text() + "\n# changed\n")
            synced = subprocess.run(gate, cwd=repo, env={**os.environ, **env}, text=True, capture_output=True)
            self.assertEqual(synced.returncode, 0, synced.stderr)
            self.assertIn("check-codegraph: synced 1 file(s) first; index current", synced.stdout)
            stale.write_text(stale.read_text() + "\n# again\n")
            unsynced = subprocess.run(gate, cwd=repo, env={**os.environ, **env, "CODEGRAPH_GATE_NO_SYNC": "1"},
                                      text=True, capture_output=True)
            self.assertEqual(unsynced.returncode, 1)
            database = repo / ".codegraph/codegraph.db"
            database.write_bytes(b"garbage " * 1000)
            rebuilt = subprocess.run(gate, cwd=repo, env={**os.environ, **env}, text=True, capture_output=True)
            self.assertEqual(rebuilt.returncode, 0, rebuilt.stderr)
            self.assertRegex(rebuilt.stdout,
                             r"check-codegraph: rebuilt a corrupt database first \([\d.]+s\); index current")
            self.assertEqual(log.read_text().splitlines()[-1], "init -y .")
            for unrepaired in ({"CODEGRAPH_GATE_NO_SYNC": "1"}, {"PATH": str(bare_path(Path(directory)))}):
                database.write_bytes(b"garbage " * 1000)
                corrupt = subprocess.run(gate, cwd=repo, env={**os.environ, **env, **unrepaired}, text=True,
                                         capture_output=True)
                self.assertEqual(corrupt.returncode, 1, unrepaired)
                self.assertIn("fails SQLite's integrity check", corrupt.stderr)
                self.assertIn("python3 scripts/agents/code_index.py health", corrupt.stderr)

    def test_a_drive_session_opens_on_a_sound_index_and_hears_only_what_was_done(self) -> None:
        """A person's `/drive` has no runner in front of it, so Claude Code's `SessionStart` hook (`startup`) takes
        the runner's step: a corrupt index is rebuilt before the session's first question, and the line saying so
        is the only thing the hook adds to the session's context — a sound one adds nothing."""
        with tempfile.TemporaryDirectory() as directory:
            repo, env, log = self.indexed(directory, "opened")
            settings = json.loads((repo / ".claude/settings.json").read_text())
            hook = {"type": "command", "timeout": 900, "command": "python3 scripts/agents/code_index.py session"}
            self.assertIn({"matcher": "startup", "hooks": [hook]}, settings["hooks"]["SessionStart"])
            session = ["python3", "scripts/agents/code_index.py", "session"]
            quiet = subprocess.run(session, cwd=repo, env={**os.environ, **env}, text=True, capture_output=True)
            self.assertEqual((quiet.returncode, quiet.stdout), (0, ""))
            (repo / ".codegraph/codegraph.db").write_bytes(b"garbage " * 1000)
            said = subprocess.run(session, cwd=repo, env={**os.environ, **env}, text=True, capture_output=True)
            self.assertEqual(said.returncode, 0, said.stderr)
            self.assertIn("code-index: at session start the index was rebuilt — the database failed its integrity "
                          "check", said.stdout)
            self.assertEqual(log.read_text().splitlines(), ["init -y ."])
            # No route: said, and the session still opens.
            bare = {**os.environ, "PATH": str(bare_path(Path(directory)))}
            unreachable = subprocess.run(session, cwd=repo, env=bare, text=True, capture_output=True)
            self.assertEqual(unreachable.returncode, 0)
            self.assertIn("at session start the index was unreachable", unreachable.stdout)

    def test_a_symbol_search_of_the_source_waits_for_the_index_and_a_search_for_words_does_not(self) -> None:
        """Claude Code's PreToolUse hook, per asker: the session and each delegate (`agent_id`). A search of the
        source for a symbol — a name the index defines, or one shaped like one — is refused with the command that
        answers it until that asker has queried the index; then its searches are its own. Words, phrases, searches
        confined to documents, a search of another command's output, and a read by line number are never refused."""
        with tempfile.TemporaryDirectory() as directory:
            repo, env, _ = self.indexed(directory, "guarded")
            settings = json.loads((repo / ".claude/settings.json").read_text())
            self.assertIn({"matcher": "Grep|Bash|mcp__codegraph__.*", "hooks": [
                {"type": "command", "command": "python3 scripts/agents/code_index.py guard"}]},
                settings["hooks"]["PreToolUse"])
            self.assertEqual(settings["hooks"]["PostToolUse"], [{"matcher": "Agent|Task", "hooks": [
                {"type": "command", "command": "python3 scripts/agents/code_index.py sync"}]}])
            self.assertIn("Bash(scripts/codegraph *)", settings["permissions"]["allow"])

            refused = self.guard(repo, env, "Bash", {"command": 'grep -rn "decideCue" apps/'}, agent="a1")
            self.assertEqual(refused.returncode, 2)
            self.assertIn("code-index: refused: `decideCue` is a symbol", refused.stderr)
            self.assertIn("`scripts/codegraph callers decideCue`", refused.stderr)
            for tool, given in (("Grep", {"pattern": "openCaptureEvent", "path": "apps/web/src"}),
                                ("Bash", {"command": "sed -n '/mapCueOutcomeToResponse/,+20p' apps/x/submit-cue.ts"}),
                                ("Bash", {"command": "cd apps && rg -n 'decideCue|submitCue'"}),
                                ("Grep", {"pattern": "\\bdecideCue\\b"})):
                self.assertEqual(self.guard(repo, env, tool, given, agent="a1").returncode, 2, given)
            for tool, given in (("Bash", {"command": 'grep -rn "done for the day" apps/web/src'}),
                                ("Bash", {"command": "grep -n decideCue specs/cap4/spec.md docs/prd.md"}),
                                ("Grep", {"pattern": "decideCue", "glob": "*.md"}),
                                ("Bash", {"command": "git ls-files | grep decideCue"}),
                                ("Bash", {"command": "sed -n '10,40p' apps/x/decide-cue.ts"}),
                                ("Grep", {"pattern": "status", "path": "apps"}),
                                ("Bash", {"command": "make verify"})):
                allowed = self.guard(repo, env, tool, given, agent="a1")
                self.assertEqual(allowed.returncode, 0, f"{given}: {allowed.stderr}")

            asked = self.guard(repo, env, "Bash", {"command": "scripts/codegraph callers decideCue"}, agent="a1")
            self.assertEqual(asked.returncode, 0, asked.stderr)
            self.assertEqual(self.guard(repo, env, "Bash", {"command": 'grep -rn "decideCue" apps/'},
                                        agent="a1").returncode, 0)
            # Asking is per asker: a sibling delegate, and the session itself, have not.
            self.assertEqual(self.guard(repo, env, "Grep", {"pattern": "decideCue"}, agent="a2").returncode, 2)
            self.assertEqual(self.guard(repo, env, "Grep", {"pattern": "decideCue"}).returncode, 2)
            self.assertEqual(self.guard(repo, env, "mcp__codegraph__codegraph_explore",
                                        {"query": "decideCue callers"}).returncode, 0)
            self.assertEqual(self.guard(repo, env, "Grep", {"pattern": "decideCue"}).returncode, 0)

            # No route to the index, or no index: nothing to send anyone to, so nothing is refused.
            self.assertEqual(self.guard(repo, {"PATH": str(bare_path(Path(directory)))}, "Grep",
                                        {"pattern": "decideCue"}, agent="a3").returncode, 0)
            (repo / ".codegraph/codegraph.db").unlink()
            self.assertEqual(self.guard(repo, env, "Grep", {"pattern": "decideCue"}, agent="a4").returncode, 0)

    def test_the_log_the_feed_and_status_count_index_queries_per_delegate_and_name_who_grepped_first(self) -> None:
        """`status` used to count the iterations that asked. Per delegate now, from the stream Claude Code tags with
        `parent_tool_use_id`: the host, then each delegate in the order it was sent, with its queries — and the one
        that searched the source for a symbol before it had asked, which is the pattern the report found."""
        with tempfile.TemporaryDirectory() as directory:
            repo, env, _ = self.indexed(directory, "counted")
            enable(repo)
            stream = "\n".join([
                tool_use("t1", "Agent", {"subagent_type": "drive-tasks", "description": "implement T1"}),
                tool_use("t2", "Bash", {"command": 'grep -n "decideCue" apps/web/src/decide-cue.ts'}, parent="t1"),
                tool_result("t2", "PreToolUse:Bash hook error: code-index: refused: `decideCue` is a symbol", "t1",
                            True),
                tool_use("t3", "Bash", {"command": "sed -n '/openCaptureEvent/,+30p' apps/web/src/capture.ts"},
                         parent="t1"),
                tool_use("t4", "Agent", {"subagent_type": "drive-skipper", "description": "review T1"}),
                tool_use("t5", "mcp__codegraph__codegraph_explore", {"query": "decideCue callers"}, parent="t4"),
                # An index answer that quotes the hook's words — its own source is indexed too — is not a refusal.
                tool_result("t5", 'REFUSED = "code-index: refused"', "t4", False),
                tool_use("t6", "Grep", {"pattern": "decideCue", "path": "apps"}, parent="t4"),
                tool_use("t7", "Bash", {"command": "scripts/codegraph impact decideCue"}),
                tool_use("t8", "Bash", {"command": 'grep -rn "done for the day" apps/web/src'}),
                DONE,
            ])
            (Path(directory) / "stream.jsonl").write_text(stream + "\n")
            harness = fake_harness(Path(directory), f"cat {Path(directory) / 'stream.jsonl'}")
            run = cruise(repo, "run", env={**env, **harness, "CRUISE_HARNESS_STREAM": "claude"})
            self.assertEqual(run.returncode, 0, run.stderr)
            summary = "cruise: iteration 1 asked the code index 2 time(s) — host 1, drive-tasks 0, drive-skipper 1"
            flagged = ("cruise:   drive-tasks searched the source for `decideCue`, `openCaptureEvent` before "
                       "asking the index")
            self.assertIn(summary, run.stdout)
            self.assertIn(flagged, run.stdout)
            self.assertIn("cruise:   drive-tasks was refused 1 symbol search(es) until it asked", run.stdout)
            self.assertNotIn("drive-skipper was refused", run.stdout)
            self.assertNotIn("drive-skipper searched", run.stdout)
            self.assertNotIn("host searched", run.stdout)
            use = logged(repo)[-1]["index_use"]
            self.assertEqual([(agent["agent"], agent["queries"], agent["searched_first"]) for agent in use],
                             [("host", 1, []), ("drive-tasks", 0, ["decideCue", "openCaptureEvent"]),
                              ("drive-skipper", 1, [])])
            status = cruise(repo, "status", env=env)
            self.assertIn(summary, status.stdout)
            self.assertIn(flagged, status.stdout)
