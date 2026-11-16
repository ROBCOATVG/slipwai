"""A harbourmaster asked to stop sees the stopping captains off before it leaves.

`fleet stop` signals every process at once. A captain gives its claim back only once its `stopped` line is
on the forge, and the harbourmaster is what puts it there — and it used to die on the signal. In
game-club-manager the tables captain then waited ninety minutes, the whole wait bound, for a publisher that
had gone, and a migration refused to run until it left.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import unittest

import checkout_packages  # noqa: F401
from harbourmaster_fixture import TravelFixture

from slipwai import logs


@unittest.skipIf(sys.platform == "win32", "a stop on Windows is TerminateProcess, which no process hears")
class StopTest(TravelFixture):
    def lit(self, *extra: str) -> subprocess.Popen[str]:
        master = subprocess.Popen([sys.executable, str(self.script), "--interval", "0.2", *extra], cwd=self.root,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                  env={**os.environ, "SLIPWAI_MACHINE": "harbour_one"})
        self.addCleanup(master.kill)
        return master

    def a_captain(self) -> subprocess.Popen[bytes]:
        """Something alive with a captain's pid file, standing in for one that is ending its stage."""
        captain = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        self.addCleanup(captain.kill)
        running = logs.run_dir(self.root) / "running"
        running.mkdir(parents=True, exist_ok=True)
        (running / "captain-ORD.pid").write_text(str(captain.pid), encoding="utf-8")
        return captain

    def published(self) -> str:
        return self.carried("refs/slipwai/logs/ORD")

    def test_it_goes_on_publishing_until_the_captain_has_left_and_then_exits_cleanly(self) -> None:
        captain = self.a_captain()
        # The fairway is this machine's, so its log is this machine's to publish.
        held = subprocess.run([sys.executable, "scripts/agents/claims.py", "--take", "ORD"], cwd=self.root,
                              capture_output=True, text=True, timeout=30,
                              env={**os.environ, "SLIPWAI_MACHINE": "harbour_one"})
        self.assertEqual(held.returncode, 0, held.stdout + held.stderr)
        self.deck("ordering", "ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        master = self.lit()
        time.sleep(1.5)  # a pass or two, so the signal lands in the loop and not in the interpreter starting
        master.send_signal(signal.SIGTERM)
        time.sleep(1.0)
        self.assertIsNone(master.poll(), "it left while a captain was still stopping")
        # The line a stopping captain writes last, after the harbourmaster was told to go.
        self.deck("ordering", "ORD", logs.entry("stopped", fairway="ORD", slice="ORD-01"))
        until = time.monotonic() + 20
        while "stopped" not in self.published():
            self.assertLess(time.monotonic(), until, "the captain's last line never reached the forge")
            time.sleep(0.2)
        captain.kill()
        captain.wait()
        said, _ = master.communicate(timeout=20)
        self.assertEqual(master.returncode, 0, said)

    def test_with_no_captain_running_it_leaves_at_once(self) -> None:
        master = self.lit()
        time.sleep(1.5)
        master.send_signal(signal.SIGTERM)
        said, _ = master.communicate(timeout=20)
        self.assertEqual(master.returncode, 0, said)


if __name__ == "__main__":
    unittest.main()
