"""A captain that is stopped, relit, left without a harbourmaster, or met by a run that fell over.

Four ways a fleet used to stick with nothing wrong in the work: a slice in flight stepped past for ever once
its captain was relit on the same machine; `fleet stop` killing a captain where it stood and leaving its
`/sail` running; a dead harbourmaster nothing restarted; and one failed run parking a slice a second run
would have finished. Beside `test_captain.py`, which is at its budget.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import unittest

import checkout_packages  # noqa: F401
from captain_fixture import SILENT, WORKS, Fixture, fake_drive

from slipwai import logs
from slipwai.process_alive import alive

#: A `/sail` that starts a delegate of its own, says it is working, and then works for ever — the stage a
#: stop lands in the middle of. The delegate's pid is written down so the test can ask whether it outlived
#: the stop.
DEEP_IN = """import json, pathlib, subprocess, sys, time, datetime
slice_id, fairway = sys.argv[1], sys.argv[2]
delegate = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
pathlib.Path("delegate.pid").write_text(str(delegate.pid))
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
with path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps({"v": 1, "t": now, "kind": "heartbeat", "fairway": fairway}) + "\\n")
time.sleep(600)
"""


def counted(body: str) -> str:
    """A fake that numbers its runs in `runs` and keeps what `SLIPWAI_RETRY` told each one in `told`."""
    return f"""import os, pathlib
runs = pathlib.Path("runs")
n = int(runs.read_text()) + 1 if runs.is_file() else 1
runs.write_text(str(n))
with pathlib.Path("told").open("a") as told:
    told.write(os.environ.get("SLIPWAI_RETRY", "-") + "\\n")
{body}
"""


class ResumeTest(Fixture):
    def test_a_slice_claimed_and_not_merged_is_resumed_with_no_park_and_no_takeover(self) -> None:
        """Relit on the same machine after a kill or a reboot: its own claim back, no park, no `taken-over`."""
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertIn("ORD-01 is through its gate and merged", done.stdout)
        self.assertNotIn("nothing to start", done.stdout)

    def test_a_merged_slice_is_not_resumed(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="a1b2c3d"))
        self.grant("ORD-02")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertIn("ORD-02 is through its gate and merged", done.stdout)

    def test_a_claimed_slice_still_parked_is_not_resumed(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("parked", fairway="ORD", why="choose the storage"))
        done = self.captain("ORD", self.sail(WORKS))
        self.assertIn("is parked", done.stdout)
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "claimed"]), 1)


class StopTest(Fixture):
    def test_a_stop_ends_the_stage_writes_stopped_and_gives_the_claim_back(self) -> None:
        captain = subprocess.Popen([sys.executable, str(self.script), "ORD", "--once"], cwd=self.root,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   env={**os.environ, "SLIPWAI_SAIL": self.sail(DEEP_IN),
                                        "SLIPWAI_MACHINE": "harbour_one"})
        self.addCleanup(captain.kill)
        until = time.monotonic() + 60
        while not any(e.kind == "heartbeat" for e in self.read("ORD")) or \
                not (self.root / "delegate.pid").is_file():
            self.assertLess(time.monotonic(), until, "the stage never started")
            time.sleep(0.2)
        delegate = int((self.root / "delegate.pid").read_text())
        self.addCleanup(lambda: os.kill(delegate, signal.SIGKILL) if alive(delegate) else None)
        captain.send_signal(signal.SIGTERM)
        said, _ = captain.communicate(timeout=60)
        self.assertEqual(captain.returncode, 0, said)
        stops = [e for e in self.read("ORD") if e.kind == "stopped"]
        self.assertEqual([e.fields["slice"] for e in stops], ["ORD-01"], said)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "parked"], [])
        self.assertEqual(self.claimed_by("ORD"), "")
        bound = time.monotonic() + 10
        while alive(delegate) and time.monotonic() < bound:
            time.sleep(0.1)
        self.assertFalse(alive(delegate), "the stage's delegate outlived the stop")
        # And the next captain lit carries the slice on, which is the other half of a stop.
        self.grant("ORD-01")
        again = self.captain("ORD", self.sail(WORKS), machine="harbour_one")
        self.assertIn("ORD-01 is through its gate and merged", again.stdout)


class HarbourmasterTest(Fixture):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "scripts/agents/harbourmaster.py").write_text(
            "import time\ntime.sleep(600)\n", encoding="utf-8")
        self.running = self.root / ".slipwai/running"
        self.running.mkdir(parents=True)
        self.addCleanup(self.put_out)
        self.grant("ORD-01")

    def put_out(self) -> None:
        pid = self.recorded()
        if pid and alive(pid):
            os.kill(pid, signal.SIGKILL)

    def recorded(self) -> int:
        path = self.running / "harbourmaster.pid"
        return int(path.read_text().strip()) if path.is_file() else 0

    def test_a_harbourmaster_that_died_is_started_again_and_said(self) -> None:
        (self.running / "harbourmaster.pid").write_text("999999\n", encoding="utf-8")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertIn("harbourmaster had stopped, so it was started again", done.stdout)
        self.assertNotEqual(self.recorded(), 999999)
        self.assertTrue(alive(self.recorded()))

    def test_one_that_is_running_is_left_alone(self) -> None:
        standing = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
        self.addCleanup(standing.kill)
        (self.running / "harbourmaster.pid").write_text(f"{standing.pid}\n", encoding="utf-8")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertNotIn("started again", done.stdout)
        self.assertEqual(self.recorded(), standing.pid)

    def test_one_nobody_recorded_is_not_this_captain_s_to_start(self) -> None:
        """A harbourmaster started by hand has no pid file, and a second beside it is two writers."""
        done = self.captain("ORD", self.sail(WORKS))
        self.assertNotIn("started again", done.stdout)
        self.assertEqual(self.recorded(), 0)

    def test_a_captain_already_restarting_it_is_left_to_do_so(self) -> None:
        (self.running / "harbourmaster.pid").write_text("999999\n", encoding="utf-8")
        (self.running / "harbourmaster.restarting").write_text("", encoding="utf-8")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertNotIn("started again", done.stdout)
        self.assertEqual(self.recorded(), 999999)


class RetryTest(Fixture):
    def test_a_run_that_exits_non_zero_is_run_again_and_told_why(self) -> None:
        once = counted(f"""import sys
if n == 1:
    sys.exit(3)
exec({WORKS!r})
""")
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(once))
        self.assertIn("ORD-01 is through its gate and merged", done.stdout)
        told = (self.root / "told").read_text().splitlines()
        self.assertEqual(told[0], "-")
        self.assertIn("exited 3", told[1])

    def test_a_missing_mark_is_retried_before_it_parks(self) -> None:
        self.grant("ORD-01")
        once = counted(f"exec({fake_drive(marks=False)!r} if n == 1 else {WORKS!r})")
        done = self.captain("ORD", self.sail(once))
        self.assertIn("ORD-01 is through its gate and merged", done.stdout)
        self.assertIn("no `mark-set` for Placed", (self.root / "told").read_text())

    def test_attempts_spent_parks_with_the_last_reason_and_the_count(self) -> None:
        self.attempts(1)
        self.captain("ORD", self.sail(counted("import sys\nsys.exit(3)\n")))
        self.assertEqual((self.root / "runs").read_text(), "2")
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1)
        self.assertIn("exited 3", parked[0])
        self.assertIn("last of 2 run(s)", parked[0])

    def test_a_stage_ended_for_silence_is_retried(self) -> None:
        self.budget(minutes=0.03, attempts=1)
        self.captain("ORD", self.sail(counted(SILENT)), timeout=120)
        self.assertEqual((self.root / "runs").read_text(), "2")
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("made no progress", parked[0])

    def attempts(self, many: int) -> None:
        import json
        held = json.loads((self.root / "harbour.json").read_text(encoding="utf-8"))
        (self.root / "harbour.json").write_text(json.dumps({**held, "attempts": many}), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
