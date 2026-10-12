"""The loop, end to end, in a project the keel generated.

Every other suite proves one link. This drives the chain: generate a project, write a model into it, render
the chart, run its gate, run a captain over it with a stand-in for `/sail`, carry the lines with the
harbourmaster, and read the board back.

It exists because three faults were found by hand in ten minutes doing exactly this, and none of them could
have been found by the other suites — each was a *disagreement between two things* that are tested apart:
the renderer against its own gate, the model schema against the gate's demands, the renderer against a
project that has a web app as well as a service.

The claim it is really here to hold is the one version 2 rests on: **a sibling is cleared by a mark being
set, not by anything merging.** If that ever stops being true the method has no parallelism in it, and
nothing else in the suite would notice.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages

REPOSITORY = Path(__file__).resolve().parents[1]
TOY = "toy-plain"
#: Two streams, and the second steers by a mark the first sets. The whole point in six lines of YAML.
SLICES = """\
slices:
  - id: ORD-01
    name: Place an order
    capability: Ordering and billing
    context: ordering
    pattern: state-change
    status: planned
    stream: order-{orderId}
    frames:
      - type: ui
        name: OrderForm
      - type: cmd
        name: PlaceOrder
      - type: evt
        name: OrderPlaced
  - id: BIL-01
    name: Charge for an order
    capability: Ordering and billing
    context: billing
    pattern: automation
    status: planned
    materialisation: async
    reads: [OrderPlaced]
    stream: invoice-{invoiceId}
    frames:
      - type: rmo
        name: UnbilledOrders
      - type: pcr
        name: Biller
      - type: cmd
        name: ChargeOrder
      - type: evt
        name: OrderCharged
"""
#: A stand-in for `/sail`: it writes what the chart says this slice sets, and nothing it does not.
SAIL = '''\
import sys, json, pathlib, datetime, yaml
slice_id, fairway = sys.argv[1], sys.argv[2]
chart = yaml.safe_load(pathlib.Path("specs/model/chart.yaml").read_text(encoding="utf-8"))
sets = ((chart.get("slices") or {}).get(slice_id) or {}).get("sets") or []
path = pathlib.Path(".slipwai/logs/model") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
def line(**fields):
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"v": 1, "t": now, **fields}) + "\\n")
for mark in sets:
    line(kind="mark-set", fairway=fairway, slice=slice_id, mark=mark)
line(kind="heartbeat", fairway=fairway, tokens=7)
line(kind="demo", fairway=fairway, slice=slice_id, verdict="accepted")
'''


def has_yaml() -> bool:
    try:
        import yaml  # type: ignore[import-untyped] # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(checkout_packages.installed("toy"), "needs the toy package: slice 3.8")
@unittest.skipUnless(has_yaml(), "the chart renderer and the stand-in both read YAML")
class LoopTest(unittest.TestCase):
    """One generation, driven. Generated once for the class: it is the slow part, and five subclasses
    would be five generations and five copies of every test."""

    project: Path
    scratch: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        # `ignore_cleanup_errors` because what is being removed is a git repository: loose objects are mode
        # 444, and Windows refuses to unlink a read-only file, so the tear-down of a directory nothing reads
        # again was failing the suite under the name of the case that happened to run last. A scratch
        # directory that will not delete is a fact about the filesystem and not a claim about the loop.
        cls.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        done = subprocess.run(
            [sys.executable, "-m", "slipwai", "generate", "demo", "--backend", TOY,
             "--frontend", "none", "--target", "none", "--profile", "event-modelling",
             "--output", cls.scratch.name],
            cwd=REPOSITORY, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(REPOSITORY / "src"),
                 "SLIPWAI_LANGUAGES": str(checkout_packages.PACKAGES)},
        )
        if done.returncode != 0:
            raise AssertionError(done.stdout + done.stderr)
        cls.project = Path(cls.scratch.name) / "demo"
        model = cls.project / "docs/event-model/model.yaml"
        held = model.read_text(encoding="utf-8")
        assert "slices: []" in held, "the seeded model no longer ends on an empty slice list"
        model.write_text(held.replace("slices: []\n", SLICES), encoding="utf-8")
        (cls.project / "sail-stand-in.py").write_text(SAIL, encoding="utf-8")
        # A captain waits for the harbourmaster's answer to its merge request, bounded by `wait_bound` —
        # which is a bound on the harbour log going *silent*, not on elapsed time. Most of these cases run a
        # captain with no harbourmaster behind it at all, so the harbour is silent from the first instant
        # and the bound is the whole wait: seconds here rather than the hour a real harbour allows. The one
        # case that runs a harbourmaster sets its own, below, because the quantity there is a different one.
        harbour = cls.project / "harbour.json"
        config = json.loads(harbour.read_text(encoding="utf-8"))
        harbour.write_text(json.dumps({**config, "wait_bound": 0.05}, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.scratch.cleanup()

    def setUp(self) -> None:
        """The generation is shared because it is slow; the run is not, because it is the thing being
        tested. A test that inherited the last one's logs would be a test whose result depends on the
        order they ran in — which is how a suite goes green on a claim nobody is making any more."""
        import shutil
        shutil.rmtree(self.project / ".slipwai", ignore_errors=True)
        (self.project / "specs/model/chart.yaml").unlink(missing_ok=True)

    def run_in(self, *argv: str, sail: bool = False) -> subprocess.CompletedProcess:
        env = {**os.environ}
        if sail:
            env["SLIPWAI_SAIL"] = f"{sys.executable} {self.project / 'sail-stand-in.py'}"
        return subprocess.run([sys.executable, *argv], cwd=self.project, capture_output=True, text=True,
                              env=env, timeout=180)

    def entries(self, fairway: str) -> list[dict]:
        path = self.project / f".slipwai/logs/model/{fairway}.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def kinds(self, fairway: str) -> list[str]:
        return [entry["kind"] for entry in self.entries(fairway)]

    def git(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                              cwd=self.project, capture_output=True, text=True, check=False)


    def test_the_chart_renders_from_the_model(self) -> None:
        done = self.run_in("scripts/event-model/chart.py")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("2 slices", done.stdout)

    def test_and_the_chart_gate_accepts_what_the_renderer_wrote(self) -> None:
        """The pairing rule. A generator whose output fails its own gate is the worst of the two."""
        self.run_in("scripts/event-model/chart.py")
        done = self.run_in("scripts/check-chart.py")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_single_service_project_still_gets_its_fairways(self) -> None:
        """One service and a web app is two deployables and nothing to decide, and that left the chart
        with no fairways at all and every slice naming one it had not got."""
        self.run_in("scripts/event-model/chart.py")
        chart = (self.project / "specs/model/chart.yaml").read_text(encoding="utf-8")
        self.assertIn("billing:", chart)
        self.assertIn("ordering:", chart)

    def test_only_the_slice_that_waits_on_nothing_may_start(self) -> None:
        self.run_in("scripts/event-model/chart.py")
        done = self.run_in("scripts/agents/clearance.py")
        self.assertIn("ORD-01", done.stdout)
        self.assertNotIn("BIL-01", done.stdout)

    def test_a_sibling_is_cleared_by_a_mark_being_set_and_not_by_a_merge(self) -> None:
        """The claim the whole method rests on. Nothing merges in this test, and billing still clears."""
        self.run_in("scripts/event-model/chart.py")
        self.run_in("scripts/agents/captain.py", "ordering", "--once", sail=True)
        self.run_in("scripts/agents/harbourmaster.py", "--once", "--no-fetch")
        done = self.run_in("scripts/agents/clearance.py")
        self.assertIn("BIL-01", done.stdout)
        self.assertNotIn("merged", "".join(self.kinds("ordering")))

    def test_a_captain_claims_dispatches_and_asks_for_the_merge(self) -> None:
        self.run_in("scripts/event-model/chart.py")
        done = self.run_in("scripts/agents/captain.py", "ordering", "--once", sail=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.kinds("ordering")[0], "claimed")
        self.assertIn("mark-set", self.kinds("ordering"))
        self.assertIn("request", self.kinds("ordering"))

    def test_a_merge_nobody_answers_parks_rather_than_waiting_for_ever(self) -> None:
        """Nothing merges without the harbourmaster, and a wait with no end is indistinguishable from a run
        that has stopped. With none running, the fairway says so in its own log."""
        self.run_in("scripts/event-model/chart.py")
        self.run_in("scripts/agents/captain.py", "ordering", "--once", sail=True)
        parked = [one for one in self.entries("ordering") if one["kind"] == "parked"]
        self.assertEqual(len(parked), 1)
        self.assertIn("did not answer", parked[0]["why"])

    def test_the_whole_loop_reaches_trunk_with_no_person_in_the_path(self) -> None:
        """7.9's claim, end to end in a generated project, with both processes actually running.

        A captain claims, drives, holds the slice to its gate and asks; a harbourmaster rebases, gates,
        advances trunk and answers with the commit; the captain writes `merged`. Nobody is asked anything.

        Two stand-ins, both named: `/sail` is the one above, and the project's gate is one line. What is
        being proved is that the merge happens and trunk moves — that a real `make verify` passes on a
        fresh generation is `make test-docs`'s job, and running it per case would make this suite minutes
        long.
        """
        # The one case with a harbourmaster behind the captain, so the one where `wait_bound` is a bound on
        # something that exists. What has to fit inside it is the harbourmaster's *first* pass — a Python
        # start, a `git fetch`, a rebase in a fresh worktree and the project's gate — before it has written
        # any line to restart the bound. The three seconds the harbourmaster-less cases want is less than
        # that start costs on a loaded CI runner, and this case failed one Windows run in two reporting a
        # slice parked whose merge was being gated at that moment. A minute is sixty of the harbourmaster's
        # own `--interval` below: what it still catches is a harbourmaster that never starts or never
        # writes, and `run_in`'s 180-second timeout is the backstop behind that.
        harbour = self.project / "harbour.json"
        was = harbour.read_text(encoding="utf-8")
        self.addCleanup(harbour.write_text, was, encoding="utf-8")
        harbour.write_text(json.dumps({**json.loads(was), "wait_bound": 1.0}, indent=2) + "\n",
                           encoding="utf-8")

        gate = self.project / "gate"
        gate.mkdir(exist_ok=True)
        (gate / "Makefile").write_text("verify:\n\t@echo 'verify: all gates passed'\n", encoding="utf-8")
        manifest = self.project / "project.json"
        held = json.loads(manifest.read_text(encoding="utf-8"))
        manifest.write_text(json.dumps({**held, "layout": {**held["layout"], "delivery": "gate"}},
                                       indent=2) + "\n", encoding="utf-8")
        self.addCleanup(manifest.write_text, json.dumps(held, indent=2) + "\n", encoding="utf-8")

        self.run_in("scripts/event-model/chart.py")
        # The repository's own identity, as any repository somebody has committed in has. The merge rebases,
        # a rebase that replays writes a commit, and a commit needs a committer — the harbourmaster refuses
        # by name without one, which is what this generation does on a machine with no global identity.
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@local")
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "the chart, and a gate that is one line")
        trunk_was = self.git("rev-parse", "HEAD").stdout.strip()
        # The berth's branch, made here because no berth is allocated in this test.
        self.git("checkout", "--quiet", "-b", "slice/ORD-01")
        (self.project / "placed.txt").write_text("ORD-01\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "ORD-01")
        self.git("checkout", "--quiet", "main")

        with subprocess.Popen(
                [sys.executable, "scripts/agents/harbourmaster.py", "--no-fetch", "--interval", "1"],
                cwd=self.project, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as keeper:
            try:
                done = self.run_in("scripts/agents/captain.py", "ordering", "--once", sail=True)
            finally:
                keeper.terminate()
        self.assertIn("merged", self.kinds("ordering"), done.stdout + done.stderr)
        landed = [one for one in self.entries("ordering") if one["kind"] == "merged"][0]
        self.assertEqual(landed["commit"], self.git("rev-parse", "main").stdout.strip())
        self.assertNotEqual(landed["commit"], trunk_was)
        self.assertTrue((self.project / "placed.txt").is_file(),
                        "trunk moved, and the checkout sitting on it moved with it")

    def test_it_holds_no_credential_and_the_merge_is_asked_for(self) -> None:
        """A berth with a token in it is a sandbox with a way out."""
        self.run_in("scripts/event-model/chart.py")
        self.run_in("scripts/agents/captain.py", "ordering", "--once", sail=True)
        asked = [one for one in self.entries("ordering") if one["kind"] == "request"]
        self.assertEqual([one["what"] for one in asked], ["merge"])

    def test_a_stream_named_by_its_slice_prefix_is_told_it_is_the_context(self) -> None:
        self.run_in("scripts/event-model/chart.py")
        done = self.run_in("scripts/agents/captain.py", "ORD", "--once", sail=True)
        self.assertIn("no slices", done.stdout)

    def test_it_carries_a_mark_and_answers_the_request(self) -> None:
        """Both outcomes are written. There is no `slice/ORD-01` branch in this case, so the answer is a
        refusal that says so — which is the point: a request that left no line is one the captain waits on
        for ever and nobody can explain afterwards."""
        self.run_in("scripts/event-model/chart.py")
        self.run_in("scripts/agents/captain.py", "ordering", "--once", sail=True)
        self.run_in("scripts/agents/harbourmaster.py", "--once", "--no-fetch")
        harbour = (self.project / ".slipwai/logs/harbour.jsonl").read_text(encoding="utf-8")
        lines = [json.loads(line) for line in harbour.splitlines() if line.strip()]
        self.assertIn("mark-set", [one["kind"] for one in lines])
        answers = [one for one in lines if one["kind"] in ("granted", "refused")]
        self.assertEqual(len(answers), 1, lines)
        self.assertIn("no branch slice/ORD-01", answers[0]["why"])

    def test_the_board_folds_what_the_run_wrote(self) -> None:
        self.run_in("scripts/event-model/chart.py")
        self.run_in("scripts/agents/captain.py", "ordering", "--once", sail=True)
        done = subprocess.run(
            [sys.executable, "-m", "slipwai", "fleet", "--root", str(self.project)],
            cwd=REPOSITORY, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(REPOSITORY / "src"),
                 "SLIPWAI_LANGUAGES": str(checkout_packages.PACKAGES)}, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("ordering", done.stdout)
        self.assertIn("ORD-01", done.stdout)

    def test_the_run_state_overlay_is_folded_from_the_same_lines(self) -> None:
        """The model page's colour, from the lines and from nothing else. The merge is answered here by a
        stand-in for the harbourmaster, so the slice reaches the last state there is."""
        self.run_in("scripts/event-model/chart.py")
        harbour = self.project / ".slipwai/logs/harbour.jsonl"
        harbour.parent.mkdir(parents=True, exist_ok=True)
        harbour.write_text(json.dumps({"v": 1, "t": "2026-10-08T09:00:00Z", "kind": "granted",
                                       "fairway": "ordering", "request": "merge-ORD-01", "what": "merge",
                                       "slice": "ORD-01", "commit": "a1b2c3d"}) + "\n", encoding="utf-8")
        self.run_in("scripts/agents/captain.py", "ordering", "--once", sail=True)
        done = self.run_in("scripts/agents/run-state.py", "--print")
        held = json.loads(done.stdout)
        self.assertEqual(held["slices"]["ORD-01"]["state"], "merged")
        self.assertIn("OrderPlaced", held["marks"])


if __name__ == "__main__":
    unittest.main()
