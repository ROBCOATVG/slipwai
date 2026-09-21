"""How `/drive` delegates implementation: the boundary and the cycle, set once in `.specify/drive.json`, changed
through `/drive-settings`, said in the stage line and put on the record.

Measured downstream: twenty-three fresh implement delegates on one slice each re-read the same four files, and ten
of its tasks were proofs with nothing to turn green. Alongside, a `make format` that exited 0 on files `make lint`
then failed, and an `./init` that upgraded Spec Kit while restoring projections.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_benchmark import bench, clean

from slipwai.assets import ROOT
from slipwai.project.drive_settings import CONFIG, CYCLES, DEFAULT_CYCLE, DEFAULT_DELEGATE, DELEGATES
from slipwai.project.pins import SPECKIT_SOURCE


def drive(repo: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", "scripts/agents/drive.py", *arguments], cwd=repo, text=True, capture_output=True)


def record(repo: Path, slice_: str, *shapes: tuple[str, str]) -> None:
    """A slice whose implement entries ran under the given delegate/cycle pairs — none, one, or two."""
    stages = [{"stage": "implement", "ended": "now", "seconds": 60, "signals": {"delegate": d, "cycle": c}}
              for d, c in shapes] or [{"stage": "implement", "ended": "now", "seconds": 60, "signals": {}}]
    path = repo / "specs/f/slices" / slice_
    path.mkdir(parents=True)
    (path / "benchmark.json").write_text(json.dumps({"feature": "f", "slice": slice_, "stages": stages}))


class DriveSettingsTest(FactoryTestCase):
    def test_the_ladder_reads_two_settings_and_the_brief_takes_both(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "axes", "event-modelling", "go")
            settings = json.loads((repo / CONFIG).read_text())
            self.assertEqual((settings["delegate"], settings["cycle"]), (DEFAULT_DELEGATE, DEFAULT_CYCLE))
            drive_ = (repo / "commands/drive.md").read_text()
            section = drive_.split("### How implementation is delegated")[1].split("## Once inside the slice")[0]
            for value in (*DELEGATES, *CYCLES):
                self.assertIn(f"`{value}`", section)
            self.assertIn("A story is never a cycle unit", section)
            self.assertIn("written as vetoes", section)
            self.assertIn("**Parallelism is this session's duty at every boundary.**", section)
            self.assertIn("as `delegate=`, `cycle=` and `split=N` on the implement", section)
            self.assertIn("| `implement` | `delegate=…` and `cycle=…`", drive_)
            self.assertIn("story/rule`)", drive_)
            implement = (repo / "agents/drive-implement.md").read_text()
            self.assertIn("or every rule of one user story", implement)
            self.assertIn("the cycle unit — `rule` or `example`", implement)
            self.assertIn("the boundary you were given and the cycle unit you ran", implement)
            self.assertIn("a sub-delegate's manifest is a subset of yours, never wider", implement)
            command = (repo / "commands/drive-settings.md").read_text()
            self.assertIn("python3 scripts/agents/drive.py --set $ARGUMENTS", command)
            self.assertIn("refuses `cycle=story`", command)
            self.assertIn("- `/drive-settings` — `commands/drive-settings.md`",
                          (repo / "docs/skills-and-commands.md").read_text())
            self.assertIn("python3 scripts/agents/drive.py --check", (repo / "Makefile").read_text())

    def test_the_settings_change_through_the_checked_script_and_a_story_cycle_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "settings", "standard", "python")
            shown = drive(repo)
            self.assertEqual(shown.returncode, 0, shown.stderr)
            self.assertIn("delegate: story — every rule of one user story", shown.stdout)
            self.assertIn("cycle: rule — a rule's examples written together", shown.stdout)
            self.assertIn("vetoes:", shown.stdout)
            self.assertIn("check-drive: .specify/drive.json delegates per story and cycles per rule",
                          drive(repo, "--check").stdout)

            changed = drive(repo, "--set", "delegate=task", "cycle=example")
            self.assertEqual(changed.returncode, 0, changed.stderr)
            self.assertIn("takes effect at the next implementation stage", changed.stdout)
            settings = json.loads((repo / CONFIG).read_text())
            self.assertEqual((settings["delegate"], settings["cycle"]), ("task", "example"))

            refused = drive(repo, "--set", "cycle=story")
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("batch Principle V prohibits", refused.stderr)
            self.assertIn("not written", refused.stderr)
            self.assertEqual(json.loads((repo / CONFIG).read_text())["cycle"], "example")
            bogus = drive(repo, "--set", "delegate=feature")
            self.assertIn("must be one of story, rule, task", bogus.stderr)

            (repo / CONFIG).write_text(json.dumps({"delegate": "story"}))
            broken = drive(repo, "--check")
            self.assertNotEqual(broken.returncode, 0)
            self.assertIn("`cycle` must be one of", broken.stderr)
            (repo / CONFIG).unlink()
            self.assertIn("the defaults", drive(repo).stdout)

    def test_the_record_carries_how_each_slice_was_implemented(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "recorded", "event-modelling", "python")
            env = clean()
            record(repo, "S1", ("story", "rule"))
            record(repo, "S2", ("task", "example"), ("story", "rule"))
            record(repo, "S3")
            aggregate = bench(repo, env=env).stdout
            self.assertIn("delegate/cycle", aggregate)
            self.assertIn("S2: implemented as story/rule and task/example — its wall compares with neither", aggregate)
            self.assertNotIn("S1: implemented as", aggregate)
            slice_ = "specs/f/slices/S4"
            self.assertEqual(bench(repo, "start", slice_, "implement", env=env).returncode, 0)
            ended = bench(repo, "end", slice_, "implement", "delegate=story", "cycle=rule", "split=2", env=env)
            self.assertEqual(ended.returncode, 0, ended.stderr)
            entry = json.loads((repo / slice_ / "benchmark.json").read_text())["stages"][-1]
            self.assertEqual(entry["signals"], {"delegate": "story", "cycle": "rule", "split": 2})

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
            self.assertIn(f"${{recorded:-{SPECKIT_SOURCE}}}", init)
            self.assertNotIn("spec-kit.git}", init)
            # The recorded source is what the shell actually extracts, not only what the script names.
            line = next(text for text in init.splitlines() if text.strip().startswith("recorded="))
            shown = subprocess.run(["sh", "-c", f'{line}; printf %s "$recorded"'], cwd=repo, text=True,
                                   capture_output=True)
            self.assertEqual(shown.stdout, SPECKIT_SOURCE, shown.stderr)
            self.assertIn("merge target, never a write target", (ROOT / "docs/extensions.md").read_text())
