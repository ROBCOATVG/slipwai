"""The implementation boundary and experiments on the method, as the ladder, the brief and the record carry them.

Measured downstream: twenty-three fresh implement delegates on one slice each re-read the same four files, an
experiment to test the remedy had to be hand-rolled, its off switch decayed at the next commit, an arm's licence
lived in another arm's text, and a default arm starved the comparison with nothing announcing it. Alongside, a
`make format` that exited 0 on files `make lint` then failed, and an `./init` that upgraded Spec Kit while
restoring projections.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_benchmark import bench, clean

from slipwai.assets import ROOT
from slipwai.project.experiments import BOUNDARIES, EXPERIMENT
from slipwai.project.pins import SPECKIT_SOURCE


def record(repo: Path, slice_: str, *arms: str) -> None:
    """A slice whose implement entries ran under the given arms — none, one, or two for a slice that switched."""
    stages = [{"stage": "implement", "ended": "now", "seconds": 60, "signals": {"arm": arm}} for arm in arms]
    stages = stages or [{"stage": "implement", "ended": "now", "seconds": 60, "signals": {}}]
    path = repo / "specs/f/slices" / slice_
    path.mkdir(parents=True)
    (path / "benchmark.json").write_text(json.dumps({"feature": "f", "slice": slice_, "stages": stages}))


class ExperimentsTest(FactoryTestCase):
    def test_the_ladder_names_the_boundary_and_reads_a_declared_experiment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "arms", "event-modelling", "go")
            drive = (repo / "commands/drive.md").read_text()
            self.assertIn("### The implementation boundary: task, rule or story", drive)
            for boundary in BOUNDARIES:
                self.assertIn(f"**`{boundary}`**", drive)
            self.assertIn("The increment is always one rule (Principle V)", drive)
            self.assertIn("as `arm=<boundary>` and `split=N` on the implement entry", drive)
            self.assertIn("### Running an experiment on the method", drive)
            self.assertIn(f"`{EXPERIMENT}`, where it exists", drive)
            self.assertIn("`python3 scripts/agents/benchmark.py arms`", drive)
            self.assertIn("An arm that moves two variables is refused", drive)
            self.assertIn("**A switch, not a revert.**", drive)
            self.assertIn("wall time per rule proved, at equal quality", drive)
            # The record's table of signals names the two new ones.
            self.assertIn("| `implement` | `arm=…`", drive)
            self.assertIn("| `implement` | `split=N`", drive)
            implement = (repo / "agents/drive-implement.md").read_text()
            self.assertIn("or every rule of one user story", implement)
            self.assertIn("a story is never one batch of tests", implement)
            self.assertIn("the boundary you were given", implement)

    def test_the_record_carries_the_arm_and_says_when_one_has_gone_unrun(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "stale", "event-modelling", "python")
            env = clean()
            record(repo, "S1", "A")
            record(repo, "S2", "C")
            record(repo, "S3", "B", "C")
            record(repo, "S4")
            aggregate = bench(repo, env=env).stdout
            # Counted in slices that ran under some arm: S4 recorded none, so it is outside the experiment.
            self.assertIn("arm A has not run since S1, 2 slice(s) ago", aggregate)
            self.assertNotIn("arm B has not run", aggregate)
            self.assertNotIn("arm C has not run", aggregate)
            self.assertIn("S3: ran as arms B and C — its wall compares with neither", aggregate)
            arms = bench(repo, "arms", env=env)
            self.assertEqual(arms.returncode, 0, arms.stderr)
            self.assertIn("f · arm C: 2 slice(s), last S3, the latest slice", arms.stdout)
            self.assertIn("f · arm B: 1 slice(s), last S3, the latest slice", arms.stdout)
            self.assertIn("f · arm A: 1 slice(s), last S1, 2 slice(s) ago", arms.stdout)
            self.assertIn("f · no arm recorded: S4", arms.stdout)
            # And the signals are accepted where the stage is closed.
            slice_ = "specs/f/slices/S5"
            self.assertEqual(bench(repo, "start", slice_, "implement", env=env).returncode, 0)
            ended = bench(repo, "end", slice_, "implement", "arm=story", "split=2", env=env)
            self.assertEqual(ended.returncode, 0, ended.stderr)
            entry = json.loads((repo / slice_ / "benchmark.json").read_text())["stages"][-1]
            self.assertEqual(entry["signals"], {"arm": "story", "split": 2})

    def test_go_lint_and_format_read_one_module_list_and_spec_kit_is_pinned_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "pinned", "standard", "go")
            makefile = (repo / "Makefile").read_text()
            self.assertIn("GO_MODULES := apps/service\n", makefile)
            self.assertIn('test -z "$$(gofmt -l $(GO_MODULES))"', makefile)
            self.assertIn("gofmt -w $(GO_MODULES)", makefile)
            self.assertIn("A Go\n# module added under packages/ belongs on this line", makefile)
            manifest = json.loads((repo / "project.json").read_text())
            self.assertEqual(manifest["speckitSource"], SPECKIT_SOURCE)
            self.assertIn("@v", SPECKIT_SOURCE)
            init = (repo / "init").read_text()
            self.assertIn('"speckitSource"', init)
            self.assertIn(f"${{recorded:-{SPECKIT_SOURCE}}}", init)
            # The recorded source is what the shell actually extracts, not only what the script names.
            line = next(text for text in init.splitlines() if text.strip().startswith("recorded="))
            shown = subprocess.run(["sh", "-c", f'{line}; printf %s "$recorded"'], cwd=repo, text=True,
                                   capture_output=True)
            self.assertEqual(shown.stdout, SPECKIT_SOURCE, shown.stderr)
            self.assertNotIn("spec-kit.git}", init)
            self.assertIn("merge target, never a write target", (ROOT / "docs/extensions.md").read_text())
