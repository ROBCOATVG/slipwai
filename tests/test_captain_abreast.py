"""One fairway's ready slices, run abreast — each in its own berth — rather than one after another.

The evidence was a fairway of twenty-three slices whose slice graph said L01 first and the other twenty-two
independent of each other, and a captain that dispatched `/sail <slice>` once a turn: the single-slice form,
"that slice, and nothing else". A person typing `/sail` had the twenty-two fanned out; the fleet ran them
serially. These cases are that fairway in miniature — L01, then three slices the split says are parallel
with each other — run by the real captain and, where merges are the question, the real harbourmaster.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from captain_fixture import AGENTS, Fixture

from slipwai import logs
from slipwai.process_alive import alive

CHART = ("feature: ordering\nslices:\n  L01: {fairway: LVR, sets: [Opened], steers_by: []}\n"
         + "".join(f"  L0{n}: {{fairway: LVR, sets: [], steers_by: []}}\n" for n in (2, 3, 4)))
SPLIT = ("## Slice graph\n\n| Slice | depends_on | parallel_ok_with | Notes |\n|---|---|---|---|\n"
         "| L01 | — | — | the walking skeleton |\n| L02–L04 | L01 | each other | |\n")
#: A `/sail` that says when it ran and where, commits its slice's work on the branch it was started on, and
#: writes the lines its gate is: `Opened` for L01, and a demo for every slice.
DRIVE = """import datetime, json, os, pathlib, subprocess, sys, time
slice_id, fairway = sys.argv[1], sys.argv[2]
record = pathlib.Path(os.environ["ABREAST_RECORD"])
def note(**fields):
    with record.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"slice": slice_id, "pid": os.getpid(), **fields}) + "\\n")
note(event="start", at=time.time(), cwd=str(pathlib.Path.cwd().resolve()))
time.sleep(float(os.environ.get("ABREAST_SLEEP", "2")))
if slice_id in os.environ.get("ABREAST_FAIL", "").split(","):
    note(event="end", at=time.time())
    sys.exit(3)
branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
if branch != "slice/" + slice_id:  # in the checkout, as one slice at a time is: the ladder makes its branch
    subprocess.run(["git", "checkout", "--quiet", "-B", "slice/" + slice_id, "main"], check=True, capture_output=True)
pathlib.Path("work-" + slice_id + ".txt").write_text(slice_id + "\\n", encoding="utf-8")
subprocess.run(["git", "add", "work-" + slice_id + ".txt"], check=True, capture_output=True)
subprocess.run(["git", "commit", "--quiet", "-m", "implement " + slice_id], check=True, capture_output=True)
now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
lines = [{"kind": "mark-set", "fairway": fairway, "slice": slice_id, "mark": "Opened"}] if slice_id == "L01" else []
lines.append({"kind": "demo", "fairway": fairway, "slice": slice_id, "verdict": "accepted"})
with (pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")).open("a", encoding="utf-8") as handle:
    for body in lines:
        handle.write(json.dumps({"v": 1, "t": now, **body}) + "\\n")
note(event="end", at=time.time())
"""
OLD = "2026-10-01T09:00:00Z"


class Abreast(Fixture):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "specs/ordering/chart.yaml").write_text(CHART, encoding="utf-8")
        (self.root / "specs/ordering/story-split.md").write_text(SPLIT, encoding="utf-8")
        (self.root / "Makefile").write_text("verify:\n\t@echo 'verify: all gates passed'\n", encoding="utf-8")
        (self.root / ".gitignore").write_text(".slipwai/\nfake-sail.py\nrecord.jsonl\n", encoding="utf-8")
        for argv in (["config", "user.name", "t"], ["config", "user.email", "t@local"], ["add", "-A"],
                     ["commit", "--quiet", "-m", "the chart"]):
            subprocess.run(["git", *argv], cwd=self.root, check=True, capture_output=True)
        for slice_id in ("L01", "L02", "L03", "L04"):
            self.addCleanup(shutil.rmtree, self.berth(slice_id), ignore_errors=True)
        self.record = self.root / "record.jsonl"
        self.drive = self.sail(DRIVE)

    def berth(self, slice_id: str) -> Path:
        return (self.root.parent / f"{self.root.name}-{slice_id}").resolve()

    def settings(self, **held: object) -> None:
        (self.root / "harbour.json").write_text(json.dumps({
            "stages": {"default": {"minutes": 1, "tokens": 400}}, "wait_bound": 1, "trunk": "main",
            "ci": [sys.executable, "-c", "print('[]')"], "boilers": 3, **held}), encoding="utf-8")

    def skeleton_merged(self) -> None:
        self.deck("LVR", logs.entry("claimed", fairway="LVR", slice="L01", t=OLD),
                  logs.entry("mark-set", fairway="LVR", slice="L01", mark="Opened", t=OLD),
                  logs.entry("merged", fairway="LVR", slice="L01", commit="a1b2c3d", t=OLD))

    def slots(self, count: int) -> None:
        """The harbourmaster's word that this fairway may run `count` at once, written now."""
        self.harbour(logs.entry("slots", harbour=True, fairway="LVR", slots=count, running=0))

    def granted(self, *slices: str) -> None:
        for slice_id in slices:
            self.harbour(logs.entry("granted", harbour=True, fairway="LVR", request=f"merge-{slice_id}",
                                    what="merge", slice=slice_id, commit=f"c0ffee{slice_id[-1]}"))

    def turn(self, *argv: str, timeout: float = 120, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), "LVR", *argv], capture_output=True, text=True,
                              cwd=self.root, timeout=timeout, env=self.environment(**env))

    def environment(self, **env: str) -> dict[str, str]:
        return {**os.environ, "SLIPWAI_SAIL": self.drive, "SLIPWAI_MACHINE": "harbour_one",
                "ABREAST_RECORD": str(self.record), **env}

    def windows(self) -> dict[str, tuple[float, float, str]]:
        """Each slice's last run: (started, ended, where)."""
        found: dict[str, dict] = {}
        for line in self.record.read_text(encoding="utf-8").splitlines() if self.record.is_file() else []:
            row = json.loads(line)
            found.setdefault(row["slice"], {})[row["event"]] = row
        return {one: (rows["start"]["at"], rows.get("end", {}).get("at", float("inf")), rows["start"]["cwd"])
                for one, rows in found.items()}

    def kinds(self, kind: str) -> list[logs.Entry]:
        return [e for e in self.read("LVR") if e.kind == kind]


class VoyageTest(Abreast):
    """The real harbourmaster beside the real captain: it shares the boilers out and serialises the merges."""

    def voyage(self, **held: object) -> dict[str, tuple[float, float, str]]:
        self.settings(**held)
        place = self.root / "scripts/agents"
        for name in ("harbourmaster.py", "telegraph.py"):
            shutil.copy(AGENTS / name, place / name)
        # Captains here are the ones this case runs; a harbourmaster lighting detached ones beside them, with
        # no `SLIPWAI_SAIL`, would be a different exercise. The allocation it writes is the one under test.
        with (place / "fleet.py").open("a", encoding="utf-8") as handle:
            handle.write("\n\ndef relight(limit: object, say: bool = False, wanted: object = None) -> int:\n"
                         "    return 0\n")
        keeper = subprocess.Popen([sys.executable, str(place / "harbourmaster.py"), "--interval", "1"],
                                  cwd=self.root, env=self.environment(), stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
        self.addCleanup(keeper.wait)
        self.addCleanup(keeper.kill)
        # Each run long enough that the harbourmaster's next pass — the one that re-offers the sessions L01's
        # merge freed — lands while the first of the three is still going.
        captain = subprocess.Popen([sys.executable, str(self.script), "LVR", "--interval", "0.5"], cwd=self.root,
                                   env=self.environment(ABREAST_SLEEP="6"), stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        self.addCleanup(captain.kill)
        running = self.root / ".slipwai/running"
        running.mkdir(parents=True, exist_ok=True)
        (running / "captain-LVR.pid").write_text(f"{captain.pid}\n", encoding="utf-8")
        said, _ = captain.communicate(timeout=240)
        self.assertEqual([e.fields["slice"] for e in self.kinds("merged")].count("L01"), 1, said)
        self.assertEqual(sorted(e.fields["slice"] for e in self.kinds("merged")), ["L01", "L02", "L03", "L04"], said)
        # Merged one at a time: each granted commit is on the trunk the next one was gated against.
        commits = [str(e.fields["commit"]) for e in logs.harbour_fold(self.root) if e.kind == "granted"]
        self.assertEqual(len(commits), 4, said)
        for earlier, later in zip(commits, commits[1:], strict=False):
            ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", earlier, later], cwd=self.root)
            self.assertEqual(ancestry.returncode, 0, f"{earlier} is not under {later}: {said}")
        return self.windows()

    def test_the_skeleton_alone_then_its_three_dependants_abreast_in_three_berths(self) -> None:
        ran = self.voyage()
        rest = ("L02", "L03", "L04")
        self.assertLess(ran["L01"][1], min(ran[one][0] for one in rest), "L01 did not run alone and first")
        self.assertLess(max(ran[one][0] for one in rest), min(ran[one][1] for one in rest),
                        f"the three did not run at the same time: {ran}")
        self.assertEqual({ran[one][2] for one in rest}, {str(self.berth(one)) for one in rest})
        self.assertNotIn(str(self.root.resolve()), {ran[one][2] for one in rest})
        self.assertTrue(any(e.kind == "slots" and e.fields.get("slots") == 3 for e in logs.harbour_fold(self.root)))
        self.assertFalse(any(self.berth(one).exists() for one in rest), "a merged slice's berth was kept")

    def test_abreast_one_is_one_slice_at_a_time(self) -> None:
        ran = self.voyage(abreast=1)
        order = sorted(ran.values())
        for (_, ended, _), (started, _, _) in zip(order, order[1:], strict=False):
            self.assertLessEqual(ended, started, f"two slices overlapped with abreast 1: {ran}")


class ParkTest(Abreast):
    def test_a_park_on_one_slice_leaves_its_siblings_running_and_the_fairway_unparked(self) -> None:
        self.settings(attempts=0)
        self.skeleton_merged()
        self.slots(3)
        self.granted("L02", "L04")
        done = self.turn("--once", ABREAST_FAIL="L03")
        self.assertIn("L02 is through its gate and merged", done.stdout, done.stdout + done.stderr)
        self.assertIn("L04 is through its gate and merged", done.stdout)
        parks = self.kinds("parked")
        self.assertEqual([e.fields.get("slice") for e in parks], ["L03"], done.stdout)
        ran = self.windows()
        self.assertLess(ran["L03"][0], ran["L02"][1], "L03 did not run beside its siblings")
        again = self.turn("--once")
        self.assertNotIn("is parked", again.stdout)
        self.assertIn("nothing to start", again.stdout)

    def test_a_park_cleared_mid_turn_takes_the_free_slot_without_waiting_for_the_turn_to_end(self) -> None:
        """hr-test-2 ran two slots of three for an hour: nine claimed slices had their parks cleared while
        two siblings worked, every unclaimed slice waited on marks those nine set, and the refill read only
        unclaimed slices — so a cleared park waited for every slice in flight to end."""
        self.settings(attempts=0)
        self.skeleton_merged()
        for slice_id, at in (("L02", "2026-10-01T09:01:00Z"), ("L03", "2026-10-01T09:02:00Z")):
            self.deck("LVR", logs.entry("claimed", fairway="LVR", slice=slice_id, t=OLD),
                      logs.entry("parked", fairway="LVR", slice=slice_id, why="logged out", t=at))
        self.slots(2)
        self.granted("L02", "L03", "L04")
        captain = subprocess.Popen([sys.executable, str(self.script), "LVR", "--once"], cwd=self.root,
                                   env=self.environment(ABREAST_SLEEP="20"), stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        self.addCleanup(captain.kill)
        until = time.monotonic() + 60
        while "L04" not in self.windows():
            self.assertLess(time.monotonic(), until, "L04 never started")
            time.sleep(0.2)
        self.assertEqual(sorted(self.windows()), ["L04"], "a held slice started before its park was cleared")
        for at in ("2026-10-01T09:01:00Z", "2026-10-01T09:02:00Z"):
            self.harbour(logs.entry("cleared", harbour=True, fairway="LVR", parked=at, what="go"))
        said, _ = captain.communicate(timeout=240)
        ran = self.windows()
        self.assertIn("L02", ran, said)
        self.assertLess(ran["L02"][0], ran["L04"][1], f"L02 waited for L04 to end: {said}")
        for slice_id in ("L02", "L04"):
            self.assertIn(f"{slice_id} is through its gate and merged", said)


class WorkersTest(Abreast):
    """hr-test-2 at three berths on eighteen cores sat at a load of eighty: its runner starts a worker per core in
    every session, so three sessions testing at once were three machines' worth. Each is told its share."""

    def told(self, boilers: int, **env: str) -> str | None:
        self.settings(attempts=0, boilers=boilers)
        drive = self.sail("import json, os, pathlib\n"
                          "pathlib.Path(os.environ['ABREAST_RECORD']).write_text("
                          "json.dumps(os.environ.get('SLIPWAI_TEST_WORKERS')))\n")
        self.turn("--once", SLIPWAI_SAIL=drive, **env)
        return json.loads(self.record.read_text(encoding="utf-8"))

    def test_each_session_is_given_its_share_of_the_cores(self) -> None:
        self.assertEqual(self.told(3), str(max(1, (os.cpu_count() or 1) // 3)))

    def test_one_boiler_is_the_whole_machine(self) -> None:
        self.assertIsNone(self.told(1))

    def test_a_persons_own_setting_stands(self) -> None:
        self.assertEqual(self.told(3, SLIPWAI_TEST_WORKERS="2"), "2")


class LedgerTest(Abreast):
    def test_a_slice_in_its_berth_carries_its_own_dispatch_line_on_its_branch(self) -> None:
        """`make dispatch` refused a slice the captain had just claimed, so its commits had no line and
        `check-dispatch` refused them all. The captain writes the line, on the slice's branch."""
        self.settings(attempts=0)
        self.skeleton_merged()
        self.slots(3)
        self.granted("L02", "L03", "L04")
        done = self.turn("--once")
        self.assertIn("L02 is through its gate and merged", done.stdout, done.stdout + done.stderr)
        for slice_id in ("L02", "L03", "L04"):
            shown = subprocess.run(["git", "show", f"slice/{slice_id}:.slipwai/dispatch/ordering/{slice_id}.jsonl"],
                                   cwd=self.root, capture_output=True, text=True)
            self.assertEqual(shown.returncode, 0, shown.stderr + done.stdout)
            row = json.loads(shown.stdout)
            self.assertEqual((row["slice"], row["outcome"]), (slice_id, "dispatched"))
            subject = subprocess.run(["git", "log", "--format=%s", f"main..slice/{slice_id}"], cwd=self.root,
                                     capture_output=True, text=True).stdout
            self.assertIn("Dispatch ledger: the captain's line for this slice", subject)


@unittest.skipIf(sys.platform == "win32", "a stop is SIGTERM handled by the captain; Windows has no signal to "
                 "send another process but TerminateProcess, which nothing can handle")
class StopTest(Abreast):
    def test_a_stop_ends_every_slice_in_flight_and_the_next_captain_resumes_them_all(self) -> None:
        self.settings()
        self.skeleton_merged()
        self.slots(3)
        captain = subprocess.Popen([sys.executable, str(self.script), "LVR", "--once"], cwd=self.root,
                                   env=self.environment(ABREAST_SLEEP="600"), stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        self.addCleanup(captain.kill)
        until = time.monotonic() + 60
        while len(self.windows()) < 3:
            self.assertLess(time.monotonic(), until, "the three never started")
            time.sleep(0.2)
        pids = [json.loads(line)["pid"] for line in self.record.read_text(encoding="utf-8").splitlines()]
        captain.send_signal(signal.SIGTERM)
        said, _ = captain.communicate(timeout=90)
        self.assertEqual(captain.returncode, 0, said)
        self.assertEqual(sorted(e.fields["slice"] for e in self.kinds("stopped")), ["L02", "L03", "L04"], said)
        self.assertEqual(self.kinds("parked"), [])
        self.assertEqual(self.claimed_by("LVR"), "")
        bound = time.monotonic() + 10
        while any(alive(pid) for pid in pids) and time.monotonic() < bound:
            time.sleep(0.1)
        self.assertFalse(any(alive(pid) for pid in pids), "a session outlived the stop")
        # Relit: every slice claimed and not merged is carried on, not only the last one claimed.
        self.slots(3)
        self.granted("L02", "L03", "L04")
        again = self.turn("--once", ABREAST_SLEEP="0.5")
        for slice_id in ("L02", "L03", "L04"):
            self.assertIn(f"{slice_id} is through its gate and merged", again.stdout, again.stdout + again.stderr)
        claims = [e.fields["slice"] for e in self.kinds("claimed")]
        self.assertEqual({one: claims.count(one) for one in ("L02", "L03", "L04")}, {"L02": 2, "L03": 2, "L04": 2})


if __name__ == "__main__":
    unittest.main()


class OrderTest(Abreast):
    def test_the_claimed_slice_furthest_along_is_carried_on_first(self) -> None:
        """hr-test-2's L11 had its review done and sat idle while slots went to slices still planning: the
        claimed slices were carried on in claim order. With one slot, the one nearest its merge goes first."""
        self.settings(attempts=0)
        self.skeleton_merged()
        for slice_id in ("L02", "L03", "L04"):
            self.deck("LVR", logs.entry("claimed", fairway="LVR", slice=slice_id, t=OLD),
                      logs.entry("stopped", fairway="LVR", slice=slice_id, t=OLD))
        review: dict = {"from": "review"}
        self.deck("LVR", logs.entry("stowed", fairway="LVR", slice="L04", what="2 LOW", t=OLD, **review))
        self.granted("L02", "L03", "L04")
        done = self.turn("--once")
        ran = self.windows()
        self.assertEqual(sorted(ran), ["L04"], done.stdout + done.stderr)
        self.assertIn("L04 is through its gate and merged", done.stdout)
