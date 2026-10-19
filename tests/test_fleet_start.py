"""Casting off: what `/cruise` starts now, and what it deliberately does not hold.

The replacement for the runner is not a better runner. It is no runner: the state is in the logs, the
captains read them, and the thing a person types starts processes and exits — so nothing in it can be the
thing that died at iteration two.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT
from slipwai.project.harbour import harbour_config

AGENTS = TOOLKIT_ROOT / "scripts/agents"
CARRIED = ("fleet.py", "clearance.py", "harbourmaster.py", "captain.py", "logs.py", "berths.py", "abreast.py",
           "telegraph.py", "inbox.py", "ids.py")
#: The `fairways` block is in neither the slices' order nor the alphabet's, which is how a test can tell
#: which one the fleet read (slice 18.2).
CHART = """fairways:
  FUL: {context: fulfilment, owns: ["apps/fulfilment/**"]}
  ORD: {context: ordering, owns: ["apps/orders/**"]}
  BIL: {context: billing, owns: ["apps/billing/**"]}
slices:
  ORD-01: {fairway: ORD, sets: [Placed], steers_by: []}
  BIL-01: {fairway: BIL, sets: [Charged], steers_by: []}
  FUL-01: {fairway: FUL, sets: [Picked], steers_by: []}
"""
#: A fake for both long-running processes: alive, quiet, and easy to kill.
SLEEPER = "import time\ntime.sleep(600)\n"


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in CARRIED:
            (place / name).write_text((AGENTS / name).read_text(encoding="utf-8"), encoding="utf-8")
        # The two long-running processes replaced by a sleeper: what is proved here is what gets started
        # and what is written down, not what either of them then does.
        for name in ("harbourmaster.py", "captain.py"):
            (place / name).write_text(SLEEPER, encoding="utf-8")
        (self.root / "specs/ordering").mkdir(parents=True)
        (self.root / "specs/ordering/chart.yaml").write_text(CHART, encoding="utf-8")
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")
        self.script = place / "fleet.py"
        self.addCleanup(self.run_it, "stop")

    def run_it(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), *argv],
                              capture_output=True, text=True, cwd=self.root, timeout=60)

    def telegraph(self, **changes: object) -> None:
        held = json.loads((self.root / "harbour.json").read_text(encoding="utf-8"))
        (self.root / "harbour.json").write_text(json.dumps({**held, **changes}), encoding="utf-8")

    def pids(self) -> list[str]:
        place = self.root / ".slipwai/running"
        return sorted(path.stem for path in place.glob("*.pid")) if place.is_dir() else []

    def running(self) -> list[str]:
        """What is actually alive, which is not the same as what has a pid file: a process that exited
        leaves its file behind deliberately, so that `list` can say it is gone rather than tidy it away."""
        from slipwai.process_alive import alive  # signal 0 is CTRL_C_EVENT on Windows, so never `os.kill`
        found = []
        for path in sorted((self.root / ".slipwai/running").glob("*.pid")):
            try:
                pid = int(path.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                continue
            if alive(pid):
                found.append(path.stem)
        return found


class CastOffTest(Fixture):
    def test_it_starts_the_harbourmaster_and_a_captain_per_fairway(self) -> None:
        done = self.run_it("start")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.pids(), ["captain-BIL", "captain-FUL", "captain-ORD", "harbourmaster"])

    def test_it_exits_rather_than_staying_in_the_loop(self) -> None:
        """The whole of the replacement: nothing a person types holds the state of the run."""
        done = self.run_it("start")
        self.assertEqual(done.returncode, 0)
        self.assertIn("slipwai fleet", done.stdout)

    def test_the_telegraph_decides_how_many_are_lit_and_the_rest_wait(self) -> None:
        self.telegraph(boilers=1)
        done = self.run_it("start")
        self.assertEqual(len([one for one in self.pids() if one.startswith("captain-")]), 1)
        self.assertIn("waiting for a berth", done.stdout)

    def test_a_telegraph_at_stop_lights_nothing_and_says_how_to_cast_off(self) -> None:
        self.telegraph(boilers=0, position="stop")
        done = self.run_it("start")
        self.assertEqual(self.pids(), [])
        self.assertIn("telegraph half-ahead", done.stdout)

    def test_the_lit_order_is_the_charts_fairways_block(self) -> None:
        """Slice 18.2. Which captain is lit first when there are fewer berths than fairways is a priority,
        so it is read from the block the split wrote and not from where a fairway's first slice happens to
        fall. `FUL` is last in the slices and second in the alphabet; the block puts it first."""
        self.telegraph(boilers=1)
        self.run_it("start")
        self.assertEqual([one for one in self.pids() if one.startswith("captain-")], ["captain-FUL"])

    def test_a_fairway_order_in_the_harbour_moves_one_up_without_hiding_the_rest(self) -> None:
        """What `slipwai telegraph --set fairways=BIL` writes. A setting that silently stopped the fairways
        it did not name would be a way to park a stream nobody meant to park, so the named ones go first
        and the others keep the chart's order behind them."""
        self.telegraph(boilers=1, fairways=["BIL"])
        done = self.run_it("start")
        self.assertEqual([one for one in self.pids() if one.startswith("captain-")], ["captain-BIL"])
        self.assertIn("waiting for a berth", done.stdout)

    def test_a_berth_a_captain_gave_up_is_taken_by_the_stream_that_displaced_it(self) -> None:
        """Slice 18.2, the other half of a captain's yield. The yielding captain exits; something has to
        light the one it yielded to, or moving a stream up would stop the run instead of reordering it."""
        import os
        import signal
        self.telegraph(boilers=1)
        self.run_it("start")
        self.assertEqual([one for one in self.pids() if one.startswith("captain-")], ["captain-FUL"])
        held = (self.root / ".slipwai/running/captain-FUL.pid").read_text(encoding="utf-8").strip()
        os.kill(int(held), signal.SIGTERM)  # what a captain that has yielded has just done to itself
        for _ in range(100):
            if "captain-FUL" not in self.running():
                break
            time.sleep(0.05)
        self.telegraph(boilers=1, fairways=["BIL"])
        self.run_it("relight")
        self.assertEqual([one for one in self.running() if one.startswith("captain-")], ["captain-BIL"])
        self.assertIn("captain-FUL", self.pids(), "the berth it gave up is still on the record")

    def test_relighting_never_starts_a_second_harbourmaster(self) -> None:
        """It is called from inside the one that is already running, which has no pid file of its own when
        a person started it by hand. Two harbourmasters is the one-writer rule broken in the file the whole
        design promises will never conflict."""
        self.run_it("relight")
        self.assertEqual([one for one in self.running() if one == "harbourmaster"], [])
        self.assertTrue([one for one in self.running() if one.startswith("captain-")],
                        "and it does light the captains, which is what it is for")

    def test_a_harbour_naming_a_fairway_the_chart_has_not_got_lights_the_chart_s_own(self) -> None:
        """A stale name is not a reason to light nothing: the chart is what says which fairways exist."""
        self.telegraph(boilers=1, fairways=["GONE"])
        self.run_it("start")
        self.assertEqual([one for one in self.pids() if one.startswith("captain-")], ["captain-FUL"])

    def park(self, fairway: str, t: str) -> None:
        from slipwai import logs
        path = self.root / logs.deck_path("ordering", fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(logs.entry("parked", fairway=fairway, why="trunk is red", t=t).line())

    def test_a_parked_fairway_is_not_lit_and_does_not_take_a_berth(self) -> None:
        """Its captain would read the park, say so and exit, and the next pass would light it again: three
        parked streams were relit every fifteen seconds for three and a half hours."""
        self.telegraph(boilers=1)
        self.park("FUL", "2026-10-12T09:00:00Z")
        done = self.run_it("relight")
        self.assertEqual([one for one in self.running() if one.startswith("captain-")], ["captain-ORD"])
        self.assertIn("FUL: parked, so not lit — trunk is red", done.stdout)

    def test_a_cleared_park_is_lit_again(self) -> None:
        from slipwai import logs
        at = "2026-10-12T09:00:00Z"
        self.park("FUL", at)
        path = self.root / logs.HARBOUR
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(logs.entry("cleared", harbour=True, fairway="FUL", parked=at, what="go").line(),
                        encoding="utf-8")
        self.run_it("relight")
        self.assertIn("captain-FUL", self.running())

    def test_starting_twice_does_not_start_a_second_of_anything(self) -> None:
        self.run_it("start")
        before = self.pids()
        done = self.run_it("start")
        self.assertEqual(self.pids(), before)
        self.assertIn("already running", done.stdout)


class AliveTest(unittest.TestCase):
    """Asking whether a process is running must not end it.

    `os.kill(pid, 0)` is a signal on Unix and `TerminateProcess` on Windows, where the signal number is the
    exit code and 0 is as fatal as any other. So this read as "nothing is running" on Windows for the best
    of reasons: it had just killed everything it asked about. Run on every platform, because a check that
    only runs where the bug was not is not a check.
    """

    fleet: Any

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location("fleet_script", AGENTS / "fleet.py")
        assert spec is not None and spec.loader is not None
        self.fleet = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(self.fleet)

    def test_asking_does_not_kill(self) -> None:
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(child.wait)
        self.addCleanup(child.kill)
        self.assertTrue(self.fleet.alive(child.pid))
        self.assertTrue(self.fleet.alive(child.pid), "the first ask ended it")
        self.assertIsNone(child.poll(), "asking whether it was running stopped it")

    def test_a_pid_nothing_is_using_reads_as_gone(self) -> None:
        self.assertFalse(self.fleet.alive(999999))


class StopTest(Fixture):
    def test_stop_asks_everything_it_started_and_says_what_a_captain_then_does(self) -> None:
        self.run_it("start")
        done = self.run_it("stop")
        self.assertIn("ends the stage it is on, writes `stopped`", done.stdout)

    def test_a_process_that_is_already_gone_is_said_and_not_quietly_tidied(self) -> None:
        """`stop` pretending it tidied something is how a person stops believing the output."""
        place = self.root / ".slipwai/running"
        place.mkdir(parents=True, exist_ok=True)
        (place / "captain-GONE.pid").write_text("999999\n", encoding="utf-8")
        done = self.run_it("stop")
        self.assertIn("not running", done.stdout)

    def test_list_says_what_is_running_and_what_was_started_and_is_not(self) -> None:
        self.run_it("start")
        done = self.run_it("list")
        self.assertIn("harbourmaster", done.stdout)
        self.assertIn("running", done.stdout)


if __name__ == "__main__":
    unittest.main()
