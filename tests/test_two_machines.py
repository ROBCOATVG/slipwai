"""Two clone stand-ins share a bare forge: interrupted work reaches trunk and the first board.

The takeover exercises seed stopped state and elapsed leases as in test_take_over. The greenfield
exercise seeds no completed work and finishes ORD then BIL sequentially across the clones. /sail and
the project's gate are
stand-ins as in test_loop; CI reports no runs through a local stand-in. Git, the captain, the
harbourmaster and the board are real. The owner accepted this automated exercise as the final
multiplayer criterion on 2026-10-12; it does not claim two people on separate physical hardware.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import checkout_packages  # noqa: F401
from captain_fixture import CARRIED, CHART, WORKS
from harbourmaster_fixture import AGENTS, TravelFixture

from slipwai import fleet, logs

ONE = "harbour_one"
TWO = "harbour_two"
RESUME = '''\
import pathlib, subprocess
path = pathlib.Path("rungs.txt")
assert path.read_text(encoding="utf-8") == "one\\ntwo\\nthree\\nfour\\n", "lost predecessor's work"
path.write_text(path.read_text(encoding="utf-8") + "five\\n", encoding="utf-8")
subprocess.run(["git", "add", "rungs.txt"], check=True)
subprocess.run(["git", "commit", "--quiet", "-m", "rung five"], check=True)
''' + WORKS


class TwoMachinesTest(TravelFixture):
    def setUp(self) -> None:
        super().setUp()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.forge, ignore_errors=True)
        for name in CARRIED:
            (self.root / "scripts/agents" / name).write_text(
                (AGENTS / name).read_text(encoding="utf-8"), encoding="utf-8")
        # The captain imports `fleet.py`, so it is carried; but every captain here is one this case runs,
        # and a harbourmaster relighting detached captains beside them — with no `SLIPWAI_SAIL`, writing
        # into the very logs whose silence a lease is judged on — would be a different exercise.
        (self.root / "scripts/agents/fleet.py").write_text(
            (AGENTS / "fleet.py").read_text(encoding="utf-8")
            + "\n\ndef relight(limit: object, say: bool = False) -> int:\n    return 0\n", encoding="utf-8")
        chart =self.root / "specs/ordering/chart.yaml"
        chart.parent.mkdir(parents=True)
        chart.write_text(CHART, encoding="utf-8")
        (self.root / "harbour.json").write_text(json.dumps({
            "trunk": "main", "wait_bound": 1,
            "ci": [sys.executable, "-c", "print('[]')"],
            "stages": {"default": {"minutes": 1, "tokens": 400}},
        }), encoding="utf-8")
        (self.root / "Makefile").write_text("verify:\n\t@echo 'verify: all gates passed'\n",
                                            encoding="utf-8")
        (self.root / "resume.py").write_text(RESUME, encoding="utf-8")
        for argv in (("add", "-A"), ("commit", "--quiet", "-m", "the chart and stand-ins"),
                     ("push", "--quiet", "origin", "main")):
            self.checked_git(*argv)
        self.two = self.root.parent / f"{self.root.name}-two"
        self.addCleanup(shutil.rmtree, self.two, ignore_errors=True)
        self.checked_git("clone", "--quiet", str(self.forge), str(self.two))
        self.checked_git("config", "user.name", "t", where=self.two)
        self.checked_git("config", "user.email", "t@local", where=self.two)

    def checked_git(self, *argv: str, where: Path | None = None) -> str:
        done = self.git(*argv, where=where)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout.strip()

    def stopped_mid_slice(self) -> str:
        """The durable state of a stopped captain, with the offline interval simulated by old dates."""
        self.checked_git("checkout", "--quiet", "-b", "slice/ORD-01")
        (self.root / "rungs.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
        self.checked_git("add", "rungs.txt")
        self.checked_git("commit", "--quiet", "-m", "four rungs in")
        made = self.checked_git("rev-parse", "HEAD")
        self.checked_git("checkout", "--quiet", "main")
        old = (datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        held = subprocess.run([sys.executable, "scripts/agents/claims.py", "--take", "ORD"],
                              cwd=self.root, capture_output=True, text=True, timeout=30,
                              env={**os.environ, "SLIPWAI_MACHINE": ONE, "GIT_AUTHOR_DATE": old})
        self.assertEqual(held.returncode, 0, held.stdout + held.stderr)
        self.deck("ordering", "ORD", replace(
            logs.entry("claimed", fairway="ORD", slice="ORD-01"), t=old))
        done = self.run_as(ONE)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.checked_git("rev-parse", "refs/slipwai/wip/ORD", where=self.forge), made)
        return made

    def test_the_releasing_machine_publishes_its_final_line_on_a_later_pass(self) -> None:
        self.stopped_mid_slice()
        self.deck("ordering", "ORD", logs.entry(
            "parked", fairway="ORD", why="a final stop after the previous publication"))
        released = subprocess.run([sys.executable, "scripts/agents/claims.py", "--release", "ORD"],
                                  cwd=self.root, capture_output=True, text=True, timeout=30,
                                  env={**os.environ, "SLIPWAI_MACHINE": ONE})
        self.assertEqual(released.returncode, 0, released.stdout + released.stderr)
        self.assertNotIn("a final stop", self.carried("refs/slipwai/logs/ORD"))
        later = self.run_as(ONE)
        self.assertEqual(later.returncode, 0, later.stdout + later.stderr)
        self.assertIn("a final stop", self.carried("refs/slipwai/logs/ORD"))

    def test_a_previous_writer_cannot_publish_after_the_claim_changes_machine(self) -> None:
        self.stopped_mid_slice()
        for machine, action in ((ONE, "--release"), (TWO, "--take")):
            changed = subprocess.run([sys.executable, "scripts/agents/claims.py", action, "ORD"],
                                     cwd=self.root if machine == ONE else self.two,
                                     capture_output=True, text=True, timeout=30,
                                     env={**os.environ, "SLIPWAI_MACHINE": machine})
            self.assertEqual(changed.returncode, 0, changed.stdout + changed.stderr)
        self.deck("ordering", "ORD", logs.entry(
            "parked", fairway="ORD", why="a stale former writer must not publish"))
        later = self.run_as(ONE)
        self.assertEqual(later.returncode, 0, later.stdout + later.stderr)
        self.assertNotIn("a stale former writer", self.carried("refs/slipwai/logs/ORD"))

    def test_an_unpublished_final_stop_retains_the_claim_until_the_publisher_returns(self) -> None:
        self.stopped_mid_slice()
        config = self.root / "harbour.json"
        config.write_text(json.dumps({**json.loads(config.read_text(encoding="utf-8")),
                                      "wait_bound": 0.001}), encoding="utf-8")
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", why="waiting for a person"))
        def captain() -> subprocess.CompletedProcess:
            return subprocess.run([sys.executable, "scripts/agents/captain.py", "ORD", "--once"],
                                  cwd=self.root, capture_output=True, text=True, timeout=30,
                                  env={**os.environ, "SLIPWAI_MACHINE": ONE})
        stopped = captain()
        self.assertEqual(stopped.returncode, 0, stopped.stdout + stopped.stderr)
        self.assertIn("claim is retained", stopped.stdout)
        self.assertIn("harbourmaster.py --once", stopped.stdout)
        self.assertEqual(self.checked_git("show", "-s", "--format=%s", "refs/slipwai/claims/ORD",
                                          where=self.forge), "held")
        # A new machine cannot acquire the released claim: publication has not happened yet.
        other = subprocess.run([sys.executable, "scripts/agents/claims.py", "--take", "ORD"],
                               cwd=self.two, capture_output=True, text=True, timeout=30,
                               env={**os.environ, "SLIPWAI_MACHINE": TWO})
        self.assertNotEqual(other.returncode, 0, other.stdout + other.stderr)
        self.assertEqual(self.run_as(ONE).returncode, 0)
        resumed = captain()
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(self.checked_git("show", "-s", "--format=%s", "refs/slipwai/claims/ORD",
                                          where=self.forge), "released")
        self.assertIn("waiting for a person", self.carried("refs/slipwai/logs/ORD"))

    def test_greenfield_two_captains_finish_both_fairways_through_the_forge(self) -> None:
        stage = """import pathlib, subprocess, sys
subprocess.run(["git", "fetch", "--quiet", "origin", "main"], check=True)
subprocess.run(["git", "checkout", "--quiet", "-b", "slice/" + sys.argv[1], "origin/main"], check=True)
path = pathlib.Path("work-" + sys.argv[1] + ".txt")
path.write_text("implemented " + sys.argv[1] + "\\n", encoding="utf-8")
subprocess.run(["git", "add", str(path)], check=True)
subprocess.run(["git", "commit", "--quiet", "-m", "implement " + sys.argv[1]], check=True)
""" + WORKS
        (self.root / "greenfield.py").write_text(stage, encoding="utf-8")
        self.checked_git("add", "greenfield.py")
        self.checked_git("commit", "--quiet", "-m", "the explicit greenfield ladder stand-in")
        self.checked_git("push", "--quiet", "origin", "main")
        self.checked_git("pull", "--quiet", "--ff-only", where=self.two)

        # No stopped state, claim, completed rung or merged log is seeded in this exercise.
        for machine, clone, fairway in ((ONE, self.root, "ORD"), (TWO, self.two, "BIL")):
            environment = {**os.environ, "SLIPWAI_MACHINE": machine,
                           "SLIPWAI_SAIL": f"{sys.executable} {clone / 'greenfield.py'}"}
            with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output, subprocess.Popen(
                    [sys.executable, "scripts/agents/harbourmaster.py", "--interval", "1"],
                    cwd=clone, env=environment, stdout=output, stderr=output) as keeper:
                try:
                    for _ in range(2):
                        done = subprocess.run(
                            [sys.executable, "scripts/agents/captain.py", fairway, "--once"],
                            cwd=clone, capture_output=True, text=True, timeout=90, env=environment)
                        output.seek(0)
                        diagnostic = done.stdout + done.stderr + output.read()
                        self.assertEqual(done.returncode, 0, diagnostic)
                        self.assertIn("is through its gate and merged", done.stdout, diagnostic)
                finally:
                    keeper.terminate()
                    keeper.wait(timeout=30)
            entries = logs.fold((clone / logs.deck_path("ordering", fairway)).read_text(
                encoding="utf-8").splitlines())
            expected = [f"{fairway}-01", f"{fairway}-02"]
            self.assertEqual([e.fields["slice"] for e in entries if e.kind == "claimed"], expected)
            self.assertEqual([e.fields["slice"] for e in entries if e.kind == "merged"], expected)
            self.assertFalse(any(e.kind == "taken-over" for e in entries))
            self.assertIn('"kind": "merged"', self.carried(f"refs/slipwai/logs/{fairway}"))
            self.assertEqual(self.checked_git("show", "-s", "--format=%s",
                                             f"refs/slipwai/claims/{fairway}", where=self.forge), "released")

        arrived = self.run_as(ONE)
        self.assertEqual(arrived.returncode, 0, arrived.stdout + arrived.stderr)
        board = fleet.board(self.root)
        self.assertEqual(board["unreadable"], {})
        rows = board["berths"]
        assert isinstance(rows, list)
        self.assertEqual({(r["fairway"], r["merged"], r["state"], r["waiting"]) for r in rows},
                         {("ORD", 2, "finished", 0), ("BIL", 2, "finished", 0)})
        fairways, faults = fleet.fairways(self.root)
        self.assertEqual(faults, {})
        self.assertFalse(any(e.kind == "told" for f in fairways for e in f.entries))
        for slice_id in ("ORD-01", "ORD-02", "BIL-01", "BIL-02"):
            self.assertEqual(self.checked_git("show", f"main:work-{slice_id}.txt", where=self.forge),
                             f"implemented {slice_id}")

    def test_takeover_merges_the_resumed_work_and_the_first_board_discovers_it(self) -> None:
        made = self.stopped_mid_slice()
        with subprocess.Popen(
                [sys.executable, "scripts/agents/harbourmaster.py", "--interval", "1"],
                cwd=self.two, env={**os.environ, "SLIPWAI_MACHINE": TWO},
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as keeper:
            try:
                done = subprocess.run(
                    [sys.executable, "scripts/agents/captain.py", "ORD", "--once"],
                    cwd=self.two, capture_output=True, text=True, timeout=90,
                    env={**os.environ, "SLIPWAI_MACHINE": TWO,
                         "SLIPWAI_SAIL": f"{sys.executable} {self.two / 'resume.py'}"})
            finally:
                keeper.terminate()
                keeper.wait(timeout=30)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        path = self.two / logs.deck_path("ordering", "ORD")
        found = logs.fold(path.read_text(encoding="utf-8").splitlines())
        merged = [entry for entry in found if entry.kind == "merged"]
        self.assertEqual(len(merged), 1, done.stdout + done.stderr)
        self.assertEqual(merged[0].fields["slice"], "ORD-01")
        over = [entry for entry in found if entry.kind == "taken-over"]
        self.assertEqual([entry.fields["from"] for entry in over], [ONE])
        commit = str(merged[0].fields["commit"])
        self.assertEqual(self.checked_git("rev-parse", "main", where=self.forge), commit)
        self.checked_git("merge-base", "--is-ancestor", made, commit, where=self.forge)
        self.assertEqual(self.checked_git("show", "main:rungs.txt", where=self.forge),
                         "one\ntwo\nthree\nfour\nfive")
        # The final line is already durable when the captain releases: a following machine cannot
        # acquire a free claim while the authoritative log still reports this slice as in flight.
        self.assertIn('"kind": "merged"', self.carried("refs/slipwai/logs/ORD"))
        claim = self.checked_git("show", "-s", "--format=%s", "refs/slipwai/claims/ORD", where=self.forge)
        self.assertEqual(claim, "released")
        # The last writer's harbourmaster may retry its final publication after release as well.
        later = subprocess.run([sys.executable, "scripts/agents/harbourmaster.py", "--once"],
                               cwd=self.two, capture_output=True, text=True, timeout=30,
                               env={**os.environ, "SLIPWAI_MACHINE": TWO})
        self.assertEqual(later.returncode, 0, later.stdout + later.stderr)
        self.assertIn('"kind": "merged"', self.carried("refs/slipwai/logs/ORD"))
        arrived = self.run_as(ONE)
        self.assertEqual(arrived.returncode, 0, arrived.stdout + arrived.stderr)
        board, faults = fleet.fairways(self.root)
        self.assertEqual(faults, {})
        self.assertEqual(len(board), 1)
        self.assertEqual(board[0].merged, ["ORD-01"])
        observed = fleet.board(self.root)
        self.assertEqual(observed["unreadable"], {})
        rows = observed["berths"]
        assert isinstance(rows, list)
        row = rows[0]
        assert isinstance(row, dict)
        self.assertEqual((row["merged"], row["state"], row["waiting"]), (1, "idle", 1))
        # No notification or hand-written status was supplied to the first machine.
        self.assertFalse(any(entry.kind == "told" for entry in board[0].entries))


if __name__ == "__main__":
    import unittest
    unittest.main()
