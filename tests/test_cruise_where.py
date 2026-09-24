"""`/where-are-we` and `/whats-next` beside a running `/cruise`: answered from the runner's state, and unchanged
without one.

Both commands used to answer as if the person's session were about to take the next slice, which under `/cruise`
is the runner's. Each now asks `scripts/agents/cruise.py where` first. The verb is the whole guarantee that nothing
changes outside a run: it prints nothing where no runner is running — a `/drive` project, a run that ended, a
project with no `/cruise` settings at all — and the commands read silence as "answer as written". With a runner
alive it prints the iteration, the checkpoint's slice, stage and next step, and a park's reason, all of which is
run here for real against a fake harness.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from support import FactoryTestCase
from test_cruise_runner import cruise, enable, fake_harness

from slipwai.project.cruise_record import CHECKPOINT, RUNNER_LOG

CHECKPOINT_TEXT = """# Cruise checkpoint — iteration 1
- **Feature:** 001-orders · **Slice:** S3 · **Stage:** implement · **Written:** 2026-09-24T09:00:00Z
- **Delegates out:** drive-implement · apps/api/src/orders.py · T004 the order total
- **Open question:** none
- **Next:** finish T004, then converge
- **Rules:** run commands/drive.md as written
"""


class CruiseWhereTest(FactoryTestCase):
    def test_where_prints_nothing_without_a_runner_and_the_run_beside_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "where", "standard", "python")
            for command in ("commands/where-are-we.md", "commands/whats-next.md"):
                text = (repo / command).read_text()
                self.assertIn("## Under a `/cruise` run", text)
                self.assertIn("Run `python3 scripts/agents/cruise.py where` first.", text)
                self.assertIn("prints **nothing where no runner is running** — then everything above stands exactly as "
                              "written", text)
                self.assertIn("`/cruise` watches the run, `/cruise-tell` steers it, `/cruise-stop` ends it", text)
            self.assertIn("`/where-are-we` and `/whats-next` read the runner's state first (`where`)",
                          (repo / "commands/cruise.md").read_text())
            # Silence, and nothing but silence, wherever no runner is running: before /cruise is enabled, and with
            # the settings file gone altogether.
            silent = cruise(repo, "where")
            self.assertEqual((silent.returncode, silent.stdout, silent.stderr), (0, "", ""))
            settings = (repo / ".specify/cruise.json").read_text()
            (repo / ".specify/cruise.json").unlink()
            unset = cruise(repo, "where")
            self.assertEqual((unset.returncode, unset.stdout, unset.stderr), (0, "", ""))
            (repo / ".specify/cruise.json").write_text(settings)
            enable(repo)
            # An iteration that writes its checkpoint and keeps working: `where` reads the run from disk.
            env = fake_harness(Path(directory), f"""mkdir -p specs && cat > {CHECKPOINT} <<'CP'
{CHECKPOINT_TEXT}CP
sleep 3
echo "cruise: done\"""")
            try:
                self.assertEqual(cruise(repo, "start", env=env).returncode, 0)
                for _ in range(100):
                    if (repo / CHECKPOINT).is_file() and "iteration 1 started" in (repo / RUNNER_LOG).read_text():
                        break
                    time.sleep(0.05)
                else:
                    self.fail("the iteration never wrote its checkpoint")
                going = cruise(repo, "where", env=env)
                self.assertEqual(going.returncode, 0, going.stderr)
                lines = going.stdout.splitlines()
                self.assertRegex(lines[0], r"^cruise: a run is going here — runner pid \d+ since .*, 0 iteration\(s\) "
                                           r"logged, iteration 1 in flight$")
                self.assertEqual(lines[1:], [
                    "cruise: feature 001-orders · slice S3 · stage implement · checkpoint written 2026-09-24T09:00:00Z",
                    "cruise: delegates out — drive-implement · apps/api/src/orders.py · T004 the order total",
                    "cruise: next — finish T004, then converge",
                    "cruise: nothing to run from here — the runner is on it; `/cruise` watches it, `/cruise-tell` "
                    "steers it, `/cruise-stop` ends it"])
            finally:
                cruise(repo, "stop", "--now")
            self.assertEqual(cruise(repo, "where", env=env).stdout, "", "the run ended; silence again")
            # A parked run: the park's reason, and what a person does about it.
            (repo / ".specify/cruise.stop").unlink()
            (Path(directory) / "calls").unlink()
            env = {**fake_harness(Path(directory), 'echo "cruise: parked: the payments sandbox credential"'),
                   "CRUISE_POLL_SECONDS": "30"}
            try:
                self.assertEqual(cruise(repo, "start", env=env).returncode, 0)
                for _ in range(100):
                    if (repo / RUNNER_LOG).is_file() and "cruise: waiting;" in (repo / RUNNER_LOG).read_text():
                        break
                    time.sleep(0.05)
                else:
                    self.fail("the run never parked")
                parked = cruise(repo, "where", env=env).stdout.splitlines()
                self.assertRegex(parked[0], r"1 iteration\(s\) logged, parked after iteration 1$")
                self.assertIn("cruise: parked — the payments sandbox credential", parked)
                self.assertEqual(parked[-1], "cruise: nothing to run from here — a person provides what the park "
                                             "names; `/cruise-tell` with it resumes the run, `/cruise-stop` ends it")
            finally:
                cruise(repo, "stop", "--now")
