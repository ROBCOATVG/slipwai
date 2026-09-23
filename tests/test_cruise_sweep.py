"""What the last sweep of `/cruise` against `/drive` found lost between them, held here so it stays found: a
setting changed mid-run took effect only at the next run, and a process the demo left up — for an actor who,
under `/cruise`, is not coming — survived into the next iteration. Both are the runner's, run here for real
against a fake harness the way `test_cruise_runner` does; the command text and the registry rows those
findings changed are held beside the text they changed, in `test_cruise` and `test_cruise_start`.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from support import FactoryTestCase
from test_cruise_runner import cruise, enable, fake_harness, logged


class CruiseSweepTest(FactoryTestCase):
    def test_a_setting_changed_during_a_run_takes_effect_at_the_next_iteration(self) -> None:
        """`/cruise-settings` promises a change takes effect at the next iteration, and the budgets, the stuck
        window, the poll and `enabled` are the runner's to honour: it reads the file before every iteration
        rather than once. `enabled: false` mid-run ends the run at the next boundary, in the runner's words,
        and a file a hand edit broke keeps the last good table instead of ending the run on a traceback."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "settings", "standard", "python")
            enable(repo, max_iterations="5")
            env = fake_harness(Path(directory), """mkdir -p specs && touch "specs/progress-$n"
if [ "$n" -eq 1 ]; then python3 scripts/agents/cruise.py --set max_iterations=1 > /dev/null; fi
echo "cruise: continue\"""")
            budgeted = cruise(repo, "run", env=env)
            self.assertEqual(budgeted.returncode, 0, budgeted.stderr)
            self.assertIn("cruise: budget spent — 1 iteration(s)", budgeted.stdout)
            self.assertEqual(len(logged(repo)), 1, "the budget the first iteration set held from the second")
            enable(repo, max_iterations="5")
            (Path(directory) / "calls").unlink()
            env = fake_harness(Path(directory), """mkdir -p specs && touch "specs/progress-$n"
if [ "$n" -eq 1 ]; then python3 scripts/agents/cruise.py --set enabled=false > /dev/null; fi
touch "specs/disabled-$n"
echo "cruise: continue\"""")
            disabled = cruise(repo, "run", env=env)
            self.assertEqual(disabled.returncode, 0, disabled.stderr)
            self.assertIn("cruise: `enabled` is now false (/cruise-settings); the run ends here", disabled.stdout)
            self.assertEqual(len(logged(repo)), 2)
            self.assertIn("not enabled", cruise(repo, "run", env=env).stderr)
            enable(repo, max_iterations="2")
            (Path(directory) / "calls").unlink()
            env = fake_harness(Path(directory), """mkdir -p specs && touch "specs/progress-$n"
if [ "$n" -eq 1 ]; then echo '{"enabled": true, "decide": "nobody"}' > .specify/cruise.json; fi
touch "specs/broken-$n"
echo "cruise: continue\"""")
            broken = cruise(repo, "run", env=env)
            self.assertEqual(broken.returncode, 0, broken.stderr)
            self.assertIn("`decide` must be one of recommended-first, skipper-always, not 'nobody'", broken.stdout)
            self.assertIn("keeping the settings the last iteration ran under", broken.stdout)
            self.assertNotIn("Traceback", broken.stderr)
            self.assertIn("cruise: budget spent — 2 iteration(s)", broken.stdout)

    def test_what_an_iteration_leaves_running_is_ended_with_it(self) -> None:
        """`commands/drive.md` leaves the demo's app running past the end of the turn, because a person's first
        action is opening it. Under `/cruise` the hand has finished with it, and a server that outlived its
        iteration took the port the next slice's demo needed. So the runner ends the iteration's process group
        once the session has exited, and says so in the feed when there was anything to end."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "leftover", "standard", "python")
            enable(repo)
            left = Path(directory) / "left.pid"
            # The stand-in for a dev server keeps no hold on the runner's pipe, the way a harness's own child
            # processes do not; what it keeps is the process group.
            env = fake_harness(Path(directory), f"""sleep 300 > /dev/null 2>&1 &
echo $! > {left}
echo "cruise: done\"""")
            run = cruise(repo, "run", env=env)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("cruise: iteration 1 left a process running — a dev server, a watcher — and it was ended "
                          "with the iteration", run.stdout)
            pid = int(left.read_text())
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                # Ended but not yet reaped reads as alive; the state it is in is what matters.
                if (Path("/proc") / str(pid) / "status").is_file() and "zombie" in (
                        Path("/proc") / str(pid) / "status").read_text():
                    break
                time.sleep(0.05)
            else:
                self.fail(f"the process the iteration left behind (pid {pid}) is still running")
            # An iteration that leaves nothing behind says nothing about it.
            (Path(directory) / "calls").unlink()
            clean = cruise(repo, "run", env=fake_harness(Path(directory), 'echo "cruise: done"'))
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertNotIn("left a process running", clean.stdout)

    def test_the_iterations_own_model_is_a_setting_the_row_passes_with_its_flag(self) -> None:
        """Under `/drive` a person chose the session's model when they opened it; under `/cruise` nobody did, and
        `.specify/models.json` maps `host` to that unchosen default. `model` in `.specify/cruise.json` names it:
        the runner appends the registry row's `modelFlag` with it on every iteration, reads it with the settings
        so a change holds from the next iteration, says before the first which model runs, and says instead that
        the default runs where a row records no flag — never leaving it to be inferred from a transcript."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "model", "standard", "python")
            bare = Path(directory) / "bin"
            bare.mkdir()
            for tool in ("python3", "git", "sh"):
                found = shutil.which(tool)
                assert found is not None, tool
                (bare / tool).symlink_to(found)
            args = Path(directory) / "claude-args"
            (bare / "claude").write_text(f'#!/bin/sh\necho "$*" >> {args}\n'
                                         'case "$*" in *"--model opus"*) ;; *) exit 0 ;; esac\n'
                                         'python3 scripts/agents/cruise.py --set model=null > /dev/null\n'
                                         'echo "cruise: continue"\n')
            (bare / "claude").chmod(0o755)
            enable(repo, model="opus", max_iterations="2")
            env = {"PATH": str(bare), "CRUISE_POLL_SECONDS": "0"}
            run = cruise(repo, "run", env=env)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("cruise: the iteration itself runs on `opus` (--model opus); every stage "
                          "`.specify/models.json` maps to `host` runs there too", run.stdout)
            lines = args.read_text().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(lines[0].endswith(f"--add-dir {repo.parent} --model opus"), lines[0])
            # The first iteration set it back to null, and the second ran without the flag.
            self.assertNotIn("--model", lines[1])
            self.assertTrue(lines[1].endswith(f"--add-dir {repo.parent}"), lines[1])
            # A harness whose row records no flag runs its own default, and the runner says so rather than
            # dropping the setting silently.
            (repo / ".specify/integration.json").write_text(json.dumps({"installed_integrations": ["cursor-agent"]}))
            (bare / "agent").write_text('#!/bin/sh\necho "cruise: done"\n')
            (bare / "agent").chmod(0o755)
            enable(repo, harness="cursor-agent", model="gpt-5")
            unflagged = cruise(repo, "run", env=env)
            self.assertEqual(unflagged.returncode, 0, unflagged.stderr)
            self.assertIn("cruise: `model` is `gpt-5`, but the Cursor row records no `modelFlag`", unflagged.stdout)
            self.assertIn("so the harness's own default runs", unflagged.stdout)
