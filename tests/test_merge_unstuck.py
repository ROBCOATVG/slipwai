"""Three ways a merge parked a fairway for a person when nothing about it needed one.

Each was a refusal with `resolve: false`, which a captain reads as *nobody in a berth can change this* and
parks on — and a park waits for a person. A red trunk that had since gone green, a push that lost a race to
somebody else's push, and a merge ref still held by a machine that had died: each is something this process
can see resolve, so each now resolves without anybody being asked.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import unittest
from datetime import UTC, datetime, timedelta

import checkout_packages  # noqa: F401
from harbourmaster_fixture import MergeFixture  # noqa: F401

from slipwai import logs


class RedTrunkTest(MergeFixture):
    """A merge refused because trunk was red said the queue drains the moment trunk is green, and nothing
    drained it: the captain parked, and `fleet.relight` skips a parked fairway."""

    def forge_says(self, conclusion: str, sha: str) -> None:
        runs = [{"status": "completed", "conclusion": conclusion, "headSha": sha,
                 "workflowName": "verify", "url": "https://forge/runs/verify"}]
        answer = self.root / "forge.py"
        answer.write_text(f"import json\nprint(json.dumps({runs!r}))\n", encoding="utf-8")
        (self.root / "harbour.json").write_text(
            json.dumps({"trunk": "main", "ci": [sys.executable, str(answer)]}), encoding="utf-8")

    def park(self, fairway: str, why: str) -> logs.Entry:
        """The `parked` line a captain writes on reading a refusal, in its own deck log."""
        entry = logs.entry("parked", fairway=fairway, why=why)
        stamped = logs.Entry(kind=entry.kind, fields=entry.fields, t=logs.now())
        self.deck("ordering", fairway, stamped)
        return stamped

    def cleared(self) -> list[logs.Entry]:
        return [e for e in self.harbour() if e.kind == "cleared"]

    def test_a_park_on_a_red_trunk_refusal_is_cleared_once_trunk_is_green(self) -> None:
        self.forge_says("failure", "redredred")
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.ask("ORD-01")
        self.run_once()
        refused = self.answer()
        self.assertEqual(refused.fields.get("waiting"), "green-trunk", refused.fields)
        parked = self.park("ORD", "ORD-01: the merge was refused: trunk is red")
        self.run_once()
        self.assertEqual(self.cleared(), [], "cleared while trunk was still red")
        self.forge_says("success", "greengreen")
        self.run_once()
        self.run_once()
        receipts = self.cleared()
        self.assertEqual(len(receipts), 1, [e.fields for e in self.harbour()])
        self.assertEqual(receipts[0].fields["fairway"], "ORD")
        self.assertEqual(receipts[0].fields["parked"], parked.t)

    def test_a_park_written_after_trunk_turned_green_is_cleared_too(self) -> None:
        """A captain can read the refusal and park after trunk has already turned, so the receipt cannot
        be written only on the pass that said `trunk-green`."""
        self.forge_says("failure", "redredred")
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.ask("ORD-01")
        self.run_once()
        self.forge_says("success", "greengreen")
        self.run_once()
        self.assertIn("trunk-green", [e.kind for e in self.harbour()])
        self.park("ORD", "ORD-01: the merge was refused: trunk is red")
        self.run_once()
        self.assertEqual(len(self.cleared()), 1)

    def test_a_park_for_any_other_reason_is_still_a_person_s(self) -> None:
        self.forge_says("success", "greengreen")
        self.ask("ORD-02")  # no branch, so refused for a reason no berth and no green trunk can fix
        self.run_once()
        self.assertEqual(self.answer().kind, "refused")
        self.park("ORD", "ORD-02: the merge was refused: there is no branch slice/ORD-02 to merge")
        self.run_once()
        self.assertEqual(self.cleared(), [])


class ForgeFixture(MergeFixture):
    """The merge fixture with a bare repository as `origin`, so trunk is advanced by a push — and a gate
    that, while it runs, has somebody else push to trunk the first `races` times it is run. `raced` counts
    every time the gate ran, raced or not."""

    def setUp(self) -> None:
        super().setUp()
        self.forge = self.root.parent / f"{self.root.name}-forge.git"
        self.git("init", "--quiet", "--bare", "--initial-branch=main", str(self.forge))
        self.git("remote", "add", "origin", str(self.forge))
        self.raced = self.root.parent / f"{self.root.name}-raced"
        racer = self.root.parent / f"{self.root.name}-racer.py"
        racer.write_text(textwrap.dedent(f"""\
            import pathlib, subprocess, sys, tempfile
            raced = pathlib.Path({str(self.raced)!r})
            count = int(raced.read_text()) if raced.exists() else 0
            if count < int(sys.argv[1]):
                with tempfile.TemporaryDirectory() as other:
                    run = lambda *argv: subprocess.run(
                        ["git", "-c", "user.name=o", "-c", "user.email=o@local", *argv],
                        cwd=other, check=True, capture_output=True)
                    run("clone", "--quiet", {str(self.forge)!r}, ".")
                    pathlib.Path(other, f"pushed-{{count}}.txt").write_text("somebody else\\n")
                    run("add", "-A")
                    run("commit", "--quiet", "-m", "a push while the gate ran")
                    run("push", "--quiet", "origin", "HEAD:main")
            raced.write_text(str(count + 1))
            print("verify: all gates passed")
            """), encoding="utf-8")
        self.racer = racer

    def races(self, times: int) -> None:
        (self.root / "Makefile").write_text(f"verify:\n\t@{sys.executable} {self.racer} {times}\n",
                                            encoding="utf-8")
        self.commit("a gate somebody pushes during")
        self.git("push", "--quiet", "origin", "main")

    def on_the_forge(self, path: str) -> str:
        return self.git("show", f"main:{path}", where=self.forge).stdout


class PushRaceTest(ForgeFixture):
    def test_a_push_that_lost_the_race_is_gated_again_on_the_new_trunk_and_lands(self) -> None:
        self.races(1)
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.ask("ORD-01")
        done = self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "granted", f"{answer.fields}\n{done.stdout}{done.stderr}")
        self.assertEqual(self.on_the_forge("ordering.txt"), "ordering\n")
        self.assertEqual(self.on_the_forge("pushed-0.txt"), "somebody else\n",
                         "the slice was pushed over the commit that won the race")
        self.assertEqual(self.raced.read_text(), "2", "the gate did not run again on the new trunk")

    def test_a_trunk_that_outruns_every_retry_is_refused_as_worth_asking_again(self) -> None:
        self.races(100)
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused", answer.fields)
        self.assertTrue(answer.fields["resolve"], "a park for a slice nothing is wrong with")
        self.assertIn("4 times", str(answer.fields["why"]))
        self.assertEqual(self.on_the_forge("ordering.txt"), "")


class MergeLeaseTest(MergeFixture):
    """The merge ref had no lease, so a machine killed mid-merge stopped every other machine's merges for
    the wait bound and then parked whichever fairway asked."""

    def hold(self, machine: str, since: datetime) -> None:
        done = subprocess.run([sys.executable, str(self.root / "scripts/agents/claims.py"), "--take",
                               "refs/slipwai/merge"], cwd=self.root, capture_output=True, text=True,
                              env={**os.environ, "SLIPWAI_MACHINE": machine,
                                   "GIT_AUTHOR_DATE": since.strftime("%Y-%m-%dT%H:%M:%SZ")})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_holder_past_its_lease_is_taken_over_and_the_harbour_log_says_from_whom(self) -> None:
        self.hold("harbour_two", datetime.now(UTC) - timedelta(hours=2))
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted", [e.fields for e in self.harbour()])
        over = [e for e in self.harbour() if e.kind == "merge-taken-over"]
        self.assertEqual(len(over), 1)
        self.assertEqual(over[0].fields["from"], "harbour_two")

    def test_a_holder_inside_its_lease_is_waited_on_rather_than_taken_over(self) -> None:
        """The hour a real harbour waits, so the half-hour lease: a hold renewed ten minutes ago is alive."""
        (self.root / "harbour.json").write_text(json.dumps({"trunk": "main", "wait_bound": 0.02}),
                                                encoding="utf-8")
        self.hold("harbour_two", datetime.now(UTC) + timedelta(days=1))
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "refused")
        self.assertNotIn("merge-taken-over", [e.kind for e in self.harbour()])

    def test_the_holder_renews_the_ref_while_a_long_gate_runs(self) -> None:
        """A slow `make verify` writes nothing anywhere, and without a renewal would look exactly like a
        dead machine to the next harbourmaster that wanted the ref."""
        (self.root / "harbour.json").write_text(json.dumps({"trunk": "main", "wait_bound": 0.02}),
                                                encoding="utf-8")
        (self.root / "Makefile").write_text(
            f"verify:\n\t@{sys.executable} -c 'import time; time.sleep(1.2)'\n", encoding="utf-8")
        self.commit("a slow gate")
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted")
        said = self.git("log", "--format=%s", "refs/slipwai/merge").stdout.split()
        self.assertEqual(said[0], "released")
        self.assertGreaterEqual(said.count("held"), 3, said)


if __name__ == "__main__":
    unittest.main()
