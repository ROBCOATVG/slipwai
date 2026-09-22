"""`/cruise` continues on every harness: which harness the runner drives an iteration through, and a typed
`/cruise` starting that runner detached rather than running the ladder in a session nothing re-invokes.

The registry's `headless` column is what the loop runs a harness through, read from each harness's own
documentation and dated; the runner takes the first installed harness with a row on the PATH, else any harness
on the PATH, and asks every harness but Claude Code to read the command file. `start`, `stop` and `status` are run
here for real, against a fake harness, and the runner is watched to its end.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest import mock

from support import FactoryTestCase
from test_cruise_runner import LOG, REGISTRY, STOP_FILE, cruise, enable, fake_harness, logged

from slipwai.project.cruise_record import RUNNER_LOG, RUNNER_PID


class CruiseStartTest(FactoryTestCase):
    def test_the_registry_says_how_each_harness_runs_headless_or_that_nobody_checked(self) -> None:
        """The loop guesses no flag: a harness runs headless the way its own documentation says, on the date
        the row names, and a harness with `null` is told to use its own loop over `/cruise` in a session."""
        for entry in REGISTRY:
            self.assertIn("headless", entry, entry["key"])
            row = entry["headless"]
            if row is None:
                continue
            self.assertIn("{prompt}", row["command"], entry["key"])
            for field in ("how", "command", "permissions", "sandboxPermissions", "source"):
                self.assertIn(field, row, f"{entry['key']}: {field}")
            self.assertRegex(row["source"], r"read \d{4}-\d{2}-\d{2}", entry["key"])
        claude = next(entry for entry in REGISTRY if entry["key"] == "claude")["headless"]
        self.assertEqual(claude["command"], "claude -p {prompt} --output-format text {permissions}")
        self.assertEqual(claude["permissions"], "--permission-mode acceptEdits")
        self.assertEqual(claude["sandboxPermissions"], "--dangerously-skip-permissions")
        # A print session ends its background delegates after 600s unless told to wait: a real run lost its
        # story delegate mid-slice to exactly that.
        self.assertEqual(claude["env"], {"CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS": "0"})
        self.assertTrue(next(entry for entry in REGISTRY if entry["key"] == "codex")["headless"])
        # Every harness with a print mode has a row now — 27 of 36 — and the nine without say why not.
        with_rows = {entry["key"] for entry in REGISTRY if entry["headless"] is not None}
        for key in ("cursor-agent", "gemini", "copilot", "codex", "qwen", "opencode", "goose", "amp", "droid"):
            self.assertIn(key, with_rows)
        for entry in REGISTRY:
            if entry["headless"] is None:
                self.assertTrue(entry.get("headlessReason"), entry["key"])
                self.assertRegex(entry["headlessReason"], r"2026-09-22", entry["key"])
        self.assertIsNone(next(entry for entry in REGISTRY if entry["key"] == "zed")["headless"])
        # Only Claude Code's print mode is known to resolve `/cruise` itself; every other is asked to read the file.
        self.assertEqual([entry["key"] for entry in REGISTRY
                          if entry["headless"] is not None and entry["headless"].get("prompt") == "slash"], ["claude"])
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "headless", "standard", "python")
            # A PATH with nothing but what the runner itself needs, so what the machine happens to have installed
            # cannot answer for the registry.
            bare = Path(directory) / "bare"
            bare.mkdir()
            for tool in ("python3", "git", "sh"):
                found = shutil.which(tool)
                assert found is not None, tool
                (bare / tool).symlink_to(found)
            enable(repo, harness="zed")
            unknown = cruise(repo, "run", env={"PATH": str(bare)})
            self.assertEqual(unknown.returncode, 1)
            self.assertIn("no harness this loop can run an iteration through is on PATH: Zed is installed, and none "
                          "of the harnesses the registry records a headless command for is on PATH", unknown.stderr)
            self.assertIn("Cursor (`agent`)", unknown.stderr)
            self.assertIn("set CRUISE_HARNESS_COMMAND", unknown.stderr)
            # An editor with no command line still runs: through whichever CLI harness is on PATH, asked to read
            # the command file — the same words on every harness — and the log names the harness that ran.
            fake_cursor = Path(directory) / "cursor-bin"
            fake_cursor.mkdir()
            (fake_cursor / "agent").write_text(f'#!/bin/sh\necho "$*" >> {Path(directory) / "agent-args"}\n'
                                               'echo "cruise: done"\n')
            (fake_cursor / "agent").chmod(0o755)
            fallen = cruise(repo, "run", "--feature", "S1", env={"PATH": f"{fake_cursor}:{bare}"})
            self.assertEqual(fallen.returncode, 0, fallen.stderr)
            self.assertIn("cruise: harness: Cursor, found on PATH — Zed is the installed harness, and the registry "
                          "records no way to run it headless; edits are accepted", fallen.stdout)
            self.assertEqual((Path(directory) / "agent-args").read_text(),
                             "-p --output-format text --force Run the /cruise command: read commands/cruise.md and "
                             "follow it exactly as written, with `S1` as its argument.\n")
            self.assertEqual(logged(repo)[-1]["harness"], "cursor-agent")
            (repo / LOG).unlink()
            # The registry's own template is what runs when nothing overrides it, with the permission flag the
            # row names — said once, at the start — and `--sandbox` is the only way to bypass them all.
            enable(repo, harness="claude")
            fake_claude = Path(directory) / "bin"
            fake_claude.mkdir()
            (fake_claude / "claude").write_text(
                '#!/bin/sh\necho "$* wait=$CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS'
                ' session=${CLAUDE_CODE_SESSION_ID:-none} nested=${CLAUDECODE:-none}"'
                f' >> {Path(directory) / "claude-args"}\n'
                'echo "cruise: done"\n')
            (fake_claude / "claude").chmod(0o755)
            # A loop started from inside a Claude Code session inherits that session's id and its nesting guard;
            # the child must have neither.
            env = {"PATH": f"{fake_claude}:{bare}", "CRUISE_POLL_SECONDS": "0",
                   "CLAUDE_CODE_SESSION_ID": "the-parent-session", "CLAUDECODE": "1"}
            plain = cruise(repo, "run", env=env)
            self.assertEqual(plain.returncode, 0, plain.stderr)
            self.assertIn("cruise: harness: Claude Code; edits are accepted and every other permission is the "
                          "harness's own to grant or refuse", plain.stdout)
            sandboxed = cruise(repo, "run", "--sandbox", "--feature", "S1", env=env)
            self.assertEqual(sandboxed.returncode, 0, sandboxed.stderr)
            self.assertIn("--sandbox: every permission check is bypassed", sandboxed.stdout)
            self.assertEqual((Path(directory) / "claude-args").read_text(),
                             "-p /cruise --output-format text --permission-mode acceptEdits wait=0 session=none "
                             "nested=none\n"
                             "-p /cruise S1 --output-format text --dangerously-skip-permissions wait=0 session=none "
                             "nested=none\n")
            self.assertNotIn("session", logged(repo)[-1])
            # An iteration whose output carries no last line is logged as such and treated as `continue` —
            # and this is the third iteration in a row that changed nothing, so the run parks as stuck.
            (fake_claude / "claude").write_text(f'#!/bin/sh\necho "$*" >> {Path(directory) / "claude-args"}\n'
                                                'echo nothing to see\n')
            silent = cruise(repo, "run", "--no-park", env=env)
            self.assertEqual(silent.returncode, 3, silent.stdout + silent.stderr)
            self.assertEqual(logged(repo)[-1]["last_line"], "no last line")
            self.assertIn("no progress since iteration 1; one iteration to unblock, then park", silent.stdout)
            self.assertIn("the bosun's iteration did not move it", silent.stdout)
            self.assertEqual(logged(repo)[-1].get("attempt"), "unblock")
            self.assertEqual((Path(directory) / "claude-args").read_text().splitlines()[-1],
                             "-p /cruise unblock: no progress since iteration 1 --output-format text "
                             "--permission-mode acceptEdits")

    def test_a_typed_cruise_starts_the_runner_detached_and_a_person_stops_it_from_anywhere(self) -> None:
        """A `/cruise` typed into a session has nobody to re-invoke it, on any harness, so the command starts
        the runner instead of running the ladder: `start` checks everything that can refuse before it forks —
        the settings, a runner already running, the stop file, a session that is itself an iteration — then
        detaches the loop from the session, writes its pid and its log, and says so. `status` says whether it
        is running; `stop` ends it after the iteration in flight, and `--now` ends that iteration too."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "start", "standard", "python")
            refused = cruise(repo, "start")
            self.assertEqual(refused.returncode, 1)
            self.assertIn("not enabled", refused.stderr)
            enable(repo)
            env = fake_harness(Path(directory), """mkdir -p specs && touch "specs/progress-$n"; sleep 0.3
if [ "$n" -lt 3 ]; then echo "cruise: continue"; else echo "cruise: done"; fi""")
            nested = cruise(repo, "start", env={**env, "CRUISE_RUNNER": "1", "CRUISE_ITERATION": "5"})
            self.assertEqual(nested.returncode, 1)
            self.assertIn("this session is iteration 5 of a run already under way", nested.stderr)
            (repo / STOP_FILE).touch()
            halted = cruise(repo, "start", env=env)
            self.assertEqual(halted.returncode, 1)
            self.assertIn(f"{STOP_FILE} is present: a person ended the last run", halted.stderr)
            (repo / STOP_FILE).unlink()
            self.assertIn("cruise: no runner is running here", cruise(repo, "status").stdout)
            started = cruise(repo, "start", "--feature", "001-campaign", env=env)
            self.assertEqual(started.returncode, 0, started.stderr)
            self.assertRegex(started.stdout, r"cruise: runner started as pid \d+, detached from this session "
                                             r"\(harness: CRUISE_HARNESS_COMMAND, as given\)")
            self.assertIn("each iteration runs `/cruise 001-campaign` in a fresh session; this session runs no stage "
                          "of it", started.stdout)
            self.assertIn(f"it writes to {RUNNER_LOG}; `python3 scripts/agents/cruise.py status` says where it is; "
                          f"`touch {STOP_FILE}` ends it after the iteration in flight", started.stdout)
            match = re.search(r"pid (\d+)", started.stdout)
            assert match is not None
            pid = int(match.group(1))
            self.assertEqual((repo / RUNNER_PID).read_text().split()[0], str(pid))
            running = cruise(repo, "status")
            self.assertRegex(running.stdout, rf"cruise: the runner is running \(pid {pid}, since \d{{4}}-")
            again = cruise(repo, "start", env=env)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertIn(f"cruise: the runner is already running (pid {pid}, since", again.stdout)
            foreground = cruise(repo, "run", env=env)
            self.assertEqual(foreground.returncode, 1)
            self.assertIn(f"a runner is already running here (pid {pid}", foreground.stderr)
            deadline = time.time() + 10
            while time.time() < deadline and (repo / RUNNER_PID).exists():
                time.sleep(0.1)
            self.assertFalse((repo / RUNNER_PID).exists(), "the runner did not finish in time")
            self.assertEqual([entry["last_line"] for entry in logged(repo)],
                             ["cruise: continue", "cruise: continue", "cruise: done"])
            run_log = (repo / RUNNER_LOG).read_text()
            self.assertIn("cruise: runner started", run_log)
            self.assertIn("iteration 3 of the fake harness", run_log)
            self.assertIn("cruise: done — every specification is satisfied", run_log)
            self.assertIn("cruise: no runner is running here", cruise(repo, "status").stdout)
            # `stop` with nothing running still leaves the signal; `stop --now` ends the iteration in flight.
            idle = cruise(repo, "stop")
            self.assertEqual(idle.returncode, 0, idle.stderr)
            self.assertIn(f"{STOP_FILE} written; no runner is running here", idle.stdout)
            (repo / STOP_FILE).unlink()
            (Path(directory) / "calls").unlink()
            slow = fake_harness(Path(directory), 'sleep 30; echo "cruise: continue"')
            started = cruise(repo, "start", env=slow)
            self.assertEqual(started.returncode, 0, started.stderr)
            match = re.search(r"pid (\d+)", started.stdout)
            assert match is not None
            pid = int(match.group(1))
            time.sleep(0.5)
            now = cruise(repo, "stop", "--now")
            self.assertEqual(now.returncode, 0, now.stderr)
            self.assertIn(f"{STOP_FILE} written and the runner (pid {pid}) terminated with the iteration in flight",
                          now.stdout)
            deadline = time.time() + 5
            while time.time() < deadline and (repo / RUNNER_PID).exists():
                time.sleep(0.1)
            self.assertFalse((repo / RUNNER_PID).exists())
            self.assertIn(f"{STOP_FILE} is present; remove it before the next run", cruise(repo, "status").stdout)
            # A run with nothing left to do is over almost as soon as it starts. Whether it ends inside `start`'s
            # own wait or a moment after is the runner's timing against `start`'s poll, so what is held here is
            # what holds either way: a clean start, a runner gone, a run that reads as done. Which sentence `start`
            # says when the end falls inside its wait is proved below, where the timing is fixed.
            (repo / STOP_FILE).unlink()
            (Path(directory) / "calls").unlink()
            quick = cruise(repo, "start", env=fake_harness(Path(directory), 'echo "cruise: done"'))
            self.assertEqual(quick.returncode, 0, quick.stderr)
            deadline = time.time() + 10
            while time.time() < deadline and (repo / RUNNER_PID).exists():
                time.sleep(0.1)
            self.assertFalse((repo / RUNNER_PID).exists(), "the runner did not finish in time")
            self.assertEqual(logged(repo)[-1]["last_line"], "cruise: done")
            self.assertIn("cruise: done — every specification is satisfied", (repo / RUNNER_LOG).read_text())

    def test_a_runner_that_ends_inside_starts_wait_is_reported_finished_or_refused_by_its_exit(self) -> None:
        """`start` waits for the runner's pid file, and a runner can end inside that wait: cleanly, because there
        was nothing left to do, or with an error, because it refused after all. The first is a finished run and
        `start` says so with the log's last lines; the second is the refusal, with the same lines, as an error.
        Whether a real runner ends inside the wait is a race against `start`'s poll, so the runner is stood in
        for here by a process whose end is certain, and the script is driven in this process to reach it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "quick", "standard", "python")
            enable(repo)
            specification = importlib.util.spec_from_file_location("cruise_quick", repo / "scripts/agents/cruise.py")
            assert specification is not None and specification.loader is not None
            module: Any = importlib.util.module_from_spec(specification)
            specification.loader.exec_module(module)

            class Ended:
                """What `Popen` returns for a runner that wrote its last lines and ended before `start` looked."""
                pid = 4242

                def __init__(self, command: list[str], stdout: Any, exit_code: int, **_: Any) -> None:
                    self.command, self.returncode = command, exit_code
                    stdout.write(b"cruise: harness: CRUISE_HARNESS_COMMAND, as given\n"
                                 b"cruise: done \xe2\x80\x94 every specification is satisfied\n")

                def poll(self) -> int:
                    return self.returncode

            def ending(exit_code: int) -> Any:
                return lambda command, **keywords: Ended(command, exit_code=exit_code, **keywords)

            env = fake_harness(Path(directory), 'echo "cruise: done"')
            said = io.StringIO()
            with (mock.patch.dict(module.os.environ, env), mock.patch.object(module.subprocess, "Popen", ending(0)),
                  contextlib.redirect_stdout(said)):
                module.start([])
            self.assertRegex(said.getvalue(), re.escape(
                "cruise: the runner started and already ended (harness: CRUISE_HARNESS_COMMAND, as given); "
                f"{RUNNER_LOG} says: cruise: runner started ") + r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
                + re.escape(" from a session, detached | cruise: harness: CRUISE_HARNESS_COMMAND, as given | "
                            "cruise: done — every specification is satisfied\n"))
            self.assertEqual(said.getvalue().count("\n"), 1)
            self.assertFalse((repo / RUNNER_PID).exists())
            with (mock.patch.dict(module.os.environ, env), mock.patch.object(module.subprocess, "Popen", ending(1)),
                  self.assertRaises(RuntimeError) as refused):
                module.start([])
            self.assertTrue(str(refused.exception).startswith(
                f"the runner ended at once (exit 1); {RUNNER_LOG} says: "), str(refused.exception))
            self.assertTrue(str(refused.exception).endswith(
                " | cruise: harness: CRUISE_HARNESS_COMMAND, as given | cruise: done — every specification is "
                "satisfied"), str(refused.exception))
