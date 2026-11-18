"""The eval runner, proved with stand-in captains: it reports what each did, and scores a saved run again.

These stand-ins prove the runner and the scorer, not any model. One always gives the order a person would
accept, one a wrong one, one nothing, one an order in a shape `orders.py` would never write, and one that
changes its mind between runs; a command stands in for the agent where the runner is handed one, and a slow
one for an agent that runs past its bound. No harness is started anywhere here: that would spend a person's
tokens, which is what `make evals` is for.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from eval_captains import Ran, command_captain, tokens_in  # noqa: E402

import evals  # noqa: E402

CASE: dict[str, Any] = {
    "situation": "S1's gate failed twice with the same words.", "source": "made for the suite",
    "snapshot": {"feature": "001-f", "fairway": "tables", "slices": {"S1": "claimed, in flight"},
                 "deck": [{"t": "2026-11-13T12:00:00Z", "kind": "claimed", "slice": "S1"}], "harbour": [],
                 "gate": "no mark-set for M1 this turn"},
    "event": {"id": "e1", "t": "2026-11-13T12:01:00Z", "kind": "gate-failed", "slice": "S1"},
    "label": {"accept": [{"verb": "park", "slice": "S1"}], "wrong": [{"verb": "retry", "slice": "S1"}],
              "why": "the same refusal twice", "signed_off": ""},
}
Seen = list[Path]


def alive(pid: int) -> bool:
    """Whether a process is still there and not a zombie waiting to be reaped."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    status = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, check=False)
    return bool(status.stdout.strip()) and not status.stdout.strip().startswith("Z")


def give(*bodies: object) -> Callable[[Path, Path, float], Ran]:
    """A captain that writes these orders where the real one's `orders.py` would, and remembers where it ran."""
    seen: Seen = []

    def captain(project: Path, event: Path, bound: float) -> Ran:
        seen.append(project)
        folder = project / ".slipwai/run/orders" / event.parent.name
        for number, body in enumerate(bodies, 1):
            text = body if isinstance(body, str) else json.dumps(body)
            (folder / f"{number}.json").write_text(text, encoding="utf-8")
        return Ran(0, False, 1200)

    captain.seen = seen  # type: ignore[attr-defined]
    return captain


def changing() -> Callable[[Path, Path, float], Ran]:
    """A captain that parks on its first run and retries on every other: inconsistent across runs."""
    runs = [0]

    def captain(project: Path, event: Path, bound: float) -> Ran:
        runs[0] += 1
        verb = "park" if runs[0] == 1 else "retry"
        (project / ".slipwai/run/orders" / event.parent.name / "1.json").write_text(
            json.dumps({"verb": verb, "slice": "S1", "why": "w"}), encoding="utf-8")
        return Ran(0, False)

    return captain


class TheRunner(unittest.TestCase):

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.cases = self.root / "cases"
        (self.cases / "gate-failed").mkdir(parents=True)
        (self.cases / "gate-failed/s1-twice.json").write_text(json.dumps(CASE), encoding="utf-8")
        self.out = self.root / "runs/now"

    def run_with(self, captain: Callable[[Path, Path, float], Ran], runs: int = 3, bound: float = 5.0) -> dict:
        evals.run(evals.chosen_cases(self.cases, None), captain, "a stand-in", runs, bound, self.out)
        return json.loads((self.out / "report.json").read_text(encoding="utf-8"))

    def test_a_captain_that_gives_the_accepted_order_is_right_every_run_and_agrees_with_itself(self) -> None:
        held = self.run_with(give({"verb": "park", "slice": "S1", "why": "twice the same"}))["decisions"]["gate-failed"]
        self.assertEqual((3, 3, 0, 1.0), (held["runs"], held["right"], held["fallback"], held["agreement"]))
        self.assertEqual((3600, 3), (held["tokens"], held["costed"]))

    def test_the_reason_the_captain_wrote_is_kept_beside_the_score(self) -> None:
        row = self.run_with(give({"verb": "park", "slice": "S1", "why": "twice the same"}), runs=1)["cases"][0]
        self.assertEqual([["park S1: twice the same"]], row["texts"])

    def test_a_captain_that_gives_a_wrong_order_is_wrong(self) -> None:
        held = self.run_with(give({"verb": "retry", "slice": "S1", "note": "again"}))["decisions"]["gate-failed"]
        self.assertEqual((3, 0), (held["wrong"], held["right"]))

    def test_a_captain_that_gives_nothing_is_counted_as_the_fallback(self) -> None:
        held = self.run_with(give())["decisions"]["gate-failed"]
        self.assertEqual((3, 3), (held["silent"], held["fallback"]))

    def test_a_captain_that_gives_a_malformed_order_is_counted_as_the_fallback_with_why(self) -> None:
        report = self.run_with(give({"verb": "park"}, "not json"), runs=1)
        self.assertEqual(["malformed"], report["cases"][0]["outcomes"])
        self.assertEqual(2, len(report["cases"][0]["faults"][0]))

    def test_a_captain_inconsistent_across_runs_shows_in_its_agreement(self) -> None:
        report = self.run_with(changing())
        self.assertEqual(["right", "wrong", "wrong"], report["cases"][0]["outcomes"])
        self.assertAlmostEqual(2 / 3, report["decisions"]["gate-failed"]["agreement"])

    def test_every_run_is_laid_out_under_a_temporary_directory_and_taken_away(self) -> None:
        captain = give({"verb": "park", "slice": "S1"})
        self.run_with(captain, runs=2)
        seen: Seen = captain.seen  # type: ignore[attr-defined]
        self.assertEqual(2, len(set(seen)))
        for project in seen:
            self.assertTrue(project.parent.name.startswith("slipwai-eval-"))
            self.assertTrue(project.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()))
            self.assertFalse(project.parent.exists())

    def test_each_run_has_a_parent_of_its_own_holding_nothing_but_its_project(self) -> None:
        held: list[tuple[Path, list[str]]] = []

        def captain(project: Path, event: Path, bound: float) -> Ran:
            held.append((project.parent, sorted(one.name for one in project.parent.iterdir())))
            return Ran(0, False)

        self.run_with(captain, runs=2)
        self.assertEqual([["project"], ["project"]], [listing for _, listing in held])
        self.assertNotEqual(held[0][0], held[1][0])

    def test_tokens_are_said_with_how_many_runs_reported_them(self) -> None:
        runs = [0]

        def captain(project: Path, event: Path, bound: float) -> Ran:
            runs[0] += 1
            return Ran(0, False, 1000 if runs[0] % 2 else None)

        self.run_with(captain, runs=4)
        self.assertIn("2000 from 2 of 4 runs", (self.out / "report.txt").read_text(encoding="utf-8"))

    def test_the_report_reads_the_score_against_a_fixed_order_and_silence(self) -> None:
        self.run_with(give(), runs=1)
        text = (self.out / "report.txt").read_text(encoding="utf-8")
        self.assertIn("after a failed gate: retry or park: always `park` is right on 1 of 1; always silent is right "
                      "on none", text)

    @unittest.skipIf(os.name == "nt", "what an exited command left behind cannot be found on Windows without a job object")
    def test_what_a_captain_command_left_running_is_ended_when_it_exits(self) -> None:
        marker = self.root / "child.pid"
        script = self.root / "spawner.py"
        script.write_text(
            "import subprocess, sys, pathlib\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],"
            " stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
            f"pathlib.Path({str(marker)!r}).write_text(str(child.pid), encoding='utf-8')\n", encoding="utf-8")
        self.run_with(command_captain(f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"), runs=1)
        pid = int(marker.read_text(encoding="utf-8"))
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and alive(pid):
            time.sleep(0.05)
        self.assertFalse(alive(pid))

    @unittest.skipIf(os.name == "nt", "what an exited command left behind cannot be found on Windows without a job object")
    def test_a_leftover_that_would_have_outlived_the_run_s_folder_is_ended_with_the_command(self) -> None:
        """The case above cannot tell on its own: a Python started in the run's folder dies as the folder is
        taken away, ended or not. This one starts outside it, and waits to be told it is up."""
        marker = self.root / "child.pid"
        script = self.root / "spawner.py"
        script.write_text(
            "import subprocess, sys, pathlib\n"
            "child = subprocess.Popen([sys.executable, '-c', 'print(1, flush=True); import time; time.sleep(60)'],"
            f" cwd={str(self.root)!r}, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)\n"
            "child.stdout.readline()\n"
            f"pathlib.Path({str(marker)!r}).write_text(str(child.pid), encoding='utf-8')\n", encoding="utf-8")
        self.run_with(command_captain(f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"), runs=1)
        pid = int(marker.read_text(encoding="utf-8"))
        self.addCleanup(lambda: os.kill(pid, 9) if alive(pid) else None)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and alive(pid):
            time.sleep(0.05)
        self.assertFalse(alive(pid))

    def test_the_runner_judges_against_the_snapshot_s_slices_and_says_the_fault_it_found(self) -> None:
        row = self.run_with(give({"verb": "ask", "why": "w"}, {"verb": "park", "slice": "S9", "why": "w"}),
                            runs=1)["cases"][0]
        self.assertEqual(["wrong"], row["outcomes"], "S9 is no slice of this stream, whatever the label lists")
        self.assertEqual([["`park S9` names a slice this stream does not have"]], row["faults"])

    def test_a_baseline_is_scored_against_the_snapshot_s_free_slots_too(self) -> None:
        case = {**CASE, "snapshot": {**CASE["snapshot"], "slots": 0},
                "event": {"id": "e2", "t": "2026-11-13T12:01:00Z", "kind": "choose-next", "slice": "S1"},
                "label": {"accept": [{"verb": "start", "slice": "S1"}], "why": "the only one", "signed_off": ""}}
        (self.cases / "choose-next").mkdir()
        (self.cases / "choose-next/no-slot.json").write_text(json.dumps(case), encoding="utf-8")
        rows = {row["case"]: row for row in self.run_with(give(), runs=1)["cases"]}
        self.assertEqual({"start": "wrong", "none": "unjudged"}, rows["choose-next/no-slot"]["fixed"])

    def test_the_orders_and_the_report_are_written_where_a_person_reads_them(self) -> None:
        self.run_with(give({"verb": "park", "slice": "S1"}), runs=1)
        kept = self.out / "gate-failed/s1-twice/1"
        self.assertTrue((kept / "orders/1.json").is_file())
        self.assertEqual("gate-failed", json.loads((kept / "run.json").read_text(encoding="utf-8"))["decision"])
        text = (self.out / "report.txt").read_text(encoding="utf-8")
        self.assertIn("after a failed gate: retry or park", text)
        self.assertIn("This score is advice, not a gate. 0 of 1 labels are signed off", text)

    def test_a_command_named_as_the_captain_is_run_with_the_event_and_its_orders_read(self) -> None:
        script = self.root / "captain.py"
        script.write_text(
            "import json, sys, pathlib\n"
            "event = pathlib.Path(sys.argv[1])\n"
            "kind = json.loads(event.read_text(encoding='utf-8'))['kind']\n"
            "folder = event.parents[2] / 'orders' / event.parent.name\n"
            "(folder / 'a.json').write_text(json.dumps({'verb': 'park', 'slice': 'S1', 'why': kind}),"
            " encoding='utf-8')\n", encoding="utf-8")
        report = self.run_with(command_captain(f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"), runs=1)
        self.assertEqual(["right"], report["cases"][0]["outcomes"])
        self.assertEqual([["park S1: gate-failed"]], report["cases"][0]["texts"])

    def test_a_command_still_running_at_the_bound_is_ended_and_gave_no_order(self) -> None:
        captain = command_captain(f"{shlex.quote(sys.executable)} -c 'import time; time.sleep(30)'")
        report = self.run_with(captain, runs=1, bound=0.5)
        self.assertEqual(["silent"], report["cases"][0]["outcomes"])
        record = json.loads((self.out / "gate-failed/s1-twice/1/run.json").read_text(encoding="utf-8"))
        self.assertTrue(record["timed_out"])
        self.assertLess(record["seconds"], 10)

    def test_a_saved_run_is_scored_again_against_a_changed_label_without_calling_a_captain(self) -> None:
        self.run_with(give({"verb": "park", "slice": "S1"}), runs=2)
        changed = dict(CASE, label={**CASE["label"], "accept": [{"verb": "ask"}],
                                    "wrong": [{"verb": "park", "slice": "S1"}], "signed_off": "a reviewer"})
        (self.cases / "gate-failed/s1-twice.json").write_text(json.dumps(changed), encoding="utf-8")
        text = evals.rescore(self.out, self.cases)
        rescored = json.loads((self.out / "rescored.json").read_text(encoding="utf-8"))
        self.assertEqual(["wrong", "wrong"], rescored["cases"][0]["outcomes"])
        self.assertIn("signed off by a reviewer", text)
        self.assertIn("scored again at", text)

    def test_a_case_the_runner_cannot_read_stops_the_run_before_any_captain_is_called(self) -> None:
        broken = dict(CASE, label={"accept": []})
        (self.cases / "gate-failed/broken.json").write_text(json.dumps(broken), encoding="utf-8")
        with self.assertRaises(SystemExit) as stopped:
            evals.chosen_cases(self.cases, None)
        self.assertIn("gate-failed/broken cannot be run", str(stopped.exception))


class TokensWhereTheHarnessSaysThem(unittest.TestCase):

    def test_a_result_lines_usage_is_counted_and_plain_output_is_unknown(self) -> None:
        said = "\n".join([json.dumps({"type": "assistant"}),
                          json.dumps({"type": "result", "usage": {"input_tokens": 10, "output_tokens": 5,
                                                                  "cache_read_input_tokens": 100}})])
        self.assertEqual(115, tokens_in(said))
        self.assertIsNone(tokens_in("parked S1: the same refusal twice"))


if __name__ == "__main__":
    unittest.main()
