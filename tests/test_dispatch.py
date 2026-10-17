"""What a commit may name: work a plan knows, and work a dispatch accounts for.

The run this came from pushed eighteen commits to trunk in one chain. Six of them named `UI1` through
`UI9` — items invented mid-run, in no chart, no `model.yaml` and no `slices/` directory — and every gate
in the project reported green, each one correctly, because none of them was looking at commit messages.

So the cases here are that run's own subject lines. A gate that passes a synthetic `SLICE1: thing` and
fails `036 UI1-UI4, UI6, UI7: game view rebuilt from the Codex mockup` would be a gate written against the
test rather than against what happened.

The gate runs as a subprocess against a real repository, because what is being proved is which commits git
reports for a range and a fake of `git log` would prove the fake.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from slipwai.assets import TOOLKIT_ROOT

GATE = TOOLKIT_ROOT / "scripts/check-dispatch.py"
#: The subjects that run actually pushed, in the order it pushed them.
PUSHED = (
    "SB2V: read the current shared game from the starter's side",
    "SB1 T018: Play opens or starts the setup's live battle",
    "036: complete the D47 decision record",
    "036 SB4-SB7 browser: cards' models lost follow the shared game; handover button",
    "036 D49: players read both armies' pinned lists, for the Both players screens",
    "036 UI1-UI4, UI6, UI7: game view rebuilt from the Codex mockup (flag off)",
    "036 UI9: one-list and both-lists play, find opponent unit, add their list (flag off)",
)


def loaded(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = loaded("check_dispatch", GATE)


class Naming(unittest.TestCase):
    """Which tokens a subject claims. Narrow on purpose: a wrong refusal here blocks somebody's push."""

    def test_it_takes_the_slice_ids_before_the_colon(self) -> None:
        self.assertEqual(gate.named("036 UI9: one-list and both-lists play"), ["UI9"])
        self.assertEqual(gate.named("SB2V: read the current shared game"), ["SB2V"])

    def test_a_range_of_slices_is_every_slice_in_it(self) -> None:
        self.assertEqual(gate.named("036 SB4-SB7 browser: bounded losses"), ["SB4", "SB7"])
        self.assertEqual(gate.named("036 UI1-UI4, UI6, UI7: game view rebuilt"), ["UI1", "UI4", "UI6", "UI7"])

    def test_decisions_and_tasks_are_not_slices(self) -> None:
        """`D49` is a decision and `T018` a task. Both are id-shaped and neither is ever dispatched."""
        self.assertEqual(gate.named("036 D49: players read both armies' pinned lists"), [])
        self.assertEqual(gate.named("SB1 T018: Play opens or starts the setup's live battle"), ["SB1"])

    def test_nothing_after_the_colon_is_read(self) -> None:
        """A sentence that says HTTP2 is a sentence, not a claim about a slice."""
        self.assertEqual(gate.named("Fix the parser: HTTP2 frames with SB1 in the body"), [])

    def test_a_subject_with_no_colon_claims_nothing(self) -> None:
        """Conservative where the shape is not the project's: a miss costs less than a wrong refusal."""
        self.assertEqual(gate.named("The Windows gate runs the loop suite alone first"), [])


class Fixture(unittest.TestCase):
    """A real repository with a chart, a ledger, and commits whose subjects are the ones that shipped."""

    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name) / "project"
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "specs/036-shared/slices/SB1").mkdir(parents=True)
        (self.root / "project.json").write_text(json.dumps({"name": "t"}), encoding="utf-8")
        shutil.copy(GATE, self.root / "scripts/check-dispatch.py")
        self.chart(["SB1", "SB2V", "SB4", "SB7"])
        self.git("init", "--initial-branch=main")
        self.commit("the first commit")
        self.git("branch", "-f", "origin/main", "HEAD")

    def git(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                              cwd=self.root, capture_output=True, text=True, check=False)

    def chart(self, slices: list[str]) -> None:
        body = "v: 1\nfeature: 036-shared\nmarks: {}\nslices:\n" + "".join(
            f"  {one}:\n    fairway: f\n" for one in slices)
        (self.root / "specs/036-shared/chart.yaml").write_text(body, encoding="utf-8")

    def ledger(self, slices: list[str], at: str = ".slipwai/dispatch/036-shared.jsonl") -> None:
        text = "".join(json.dumps({"v": 1, "slice": one, "outcome": "dispatched"}) + "\n" for one in slices)
        (self.root / at).parent.mkdir(parents=True, exist_ok=True)
        (self.root / at).write_text(text, encoding="utf-8")

    def commit(self, subject: str) -> None:
        (self.root / "work.txt").write_text(subject, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-m", subject)

    def run_gate(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "scripts/check-dispatch.py", *argv],
                              cwd=self.root, capture_output=True, text=True, check=False)

    def test_it_refuses_a_slice_no_plan_knows(self) -> None:
        """The six UI commits. This is the half a rule keyed on known ids would have let through."""
        self.ledger(["SB1"])
        self.commit("036 UI9: one-list and both-lists play, find opponent unit")
        done = self.run_gate()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("UI9", done.stderr)
        self.assertIn("no plan knows", done.stderr + done.stdout)

    def test_it_refuses_a_planned_slice_no_dispatch_accounts_for(self) -> None:
        self.ledger(["SB1"])
        self.commit("036 SB4: bounded losses, recording handover")
        done = self.run_gate()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("SB4", done.stderr)
        self.assertIn("make dispatch", done.stderr)

    def test_it_passes_a_planned_and_dispatched_slice(self) -> None:
        self.ledger(["SB1", "SB4"])
        self.commit("036 SB4: bounded losses, recording handover")
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_ledger_line_that_says_it_could_not_delegate_still_accounts_for_the_slice(self) -> None:
        """Running one at a time is not the failure. Running one at a time with no reason written is."""
        text = json.dumps({"v": 1, "slice": "SB4", "outcome": "taken-here",
                           "why": "harness cannot delegate: .claude/agents/ holds none"}) + "\n"
        (self.root / ".slipwai/dispatch").mkdir(parents=True)
        (self.root / ".slipwai/dispatch/036-shared.jsonl").write_text(text, encoding="utf-8")
        self.commit("036 SB4: bounded losses")
        self.assertEqual(self.run_gate().returncode, 0)

    def test_a_ledger_still_at_its_old_home_counts_until_migrate_moves_it(self) -> None:
        """A checkout that has not migrated yet is never refused for where its ledger sits."""
        self.ledger(["SB1"])
        self.ledger(["SB4"], at="specs/036-shared/dispatch-ledger.jsonl")
        self.commit("036 SB4: bounded losses, recording handover")
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_slices_own_ledger_file_accounts_for_it_in_the_tree_and_in_the_push(self) -> None:
        """The line travels in the slice's own pull request, so it never has to reach trunk first."""
        base = self.git("rev-parse", "HEAD").stdout.strip()
        self.ledger(["SB4"], at=".slipwai/dispatch/036-shared/SB4.jsonl")
        self.commit("036 SB4: bounded losses, recording handover")
        self.assertEqual(self.run_gate().returncode, 0)
        head = self.git("rev-parse", "HEAD").stdout.strip()
        done = subprocess.run([sys.executable, "scripts/check-dispatch.py", "--stdin"], cwd=self.root,
                              input=f"refs/heads/slice/SB4 {head} refs/heads/slice/SB4 {base}\n",
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_decisions_and_prose_commits_pass_untouched(self) -> None:
        self.ledger([])
        self.commit("036 D49: players read both armies' pinned lists")
        self.commit("036: complete the D47 decision record")
        self.commit("The Windows gate runs the loop suite alone first")
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_project_with_no_plan_at_all_is_not_held(self) -> None:
        """An adopted repository before its first chart. A gate that refused it would block adoption."""
        (self.root / "specs/036-shared/chart.yaml").unlink()
        shutil.rmtree(self.root / "specs/036-shared/slices")
        self.commit("036 UI9: one-list and both-lists play")
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("nothing to hold", done.stdout)

    def test_the_whole_push_is_judged_and_every_fault_named(self) -> None:
        """Not the first fault: a run told one at a time is a run that pushes eight times to learn eight."""
        self.ledger(["SB1"])
        for subject in PUSHED:
            self.commit(subject)
        done = self.run_gate()
        self.assertEqual(done.returncode, 1)
        for token in ("UI1", "UI4", "UI6", "UI7", "UI9", "SB4", "SB7", "SB2V"):
            self.assertIn(token, done.stderr, f"{token} was not named in the refusal")
        self.assertNotIn("D49", done.stderr)
        self.assertNotIn("T018", done.stderr)

    def test_a_pre_push_range_is_read_from_stdin(self) -> None:
        """git's own `pre-push` protocol: `<local ref> <local sha> <remote ref> <remote sha>` per line."""
        self.ledger(["SB1"])
        base = self.git("rev-parse", "HEAD").stdout.strip()
        self.commit("036 UI9: one-list and both-lists play")
        head = self.git("rev-parse", "HEAD").stdout.strip()
        done = subprocess.run([sys.executable, "scripts/check-dispatch.py", "--stdin"], cwd=self.root,
                              input=f"refs/heads/main {head} refs/heads/main {base}\n",
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("UI9", done.stderr)

    def test_a_push_is_judged_by_the_ledger_it_carries_not_the_one_left_uncommitted(self) -> None:
        """The hook read the working tree, so a ledger nobody committed passed it and failed CI."""
        self.ledger(["SB1"])
        self.commit("the ledger as it was")
        base = self.git("rev-parse", "HEAD").stdout.strip()
        (self.root / "work.txt").write_text("SB4", encoding="utf-8")
        self.git("add", "work.txt")
        self.git("commit", "-m", "036 SB4: bounded losses, recording handover")
        head = self.git("rev-parse", "HEAD").stdout.strip()
        self.ledger(["SB1", "SB4"])
        push = f"refs/heads/main {head} refs/heads/main {base}\n"
        done = subprocess.run([sys.executable, "scripts/check-dispatch.py", "--stdin"], cwd=self.root,
                              input=push, capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("SB4", done.stderr)
        self.git("add", "-A")
        self.git("commit", "--amend", "--no-edit")
        head = self.git("rev-parse", "HEAD").stdout.strip()
        done = subprocess.run([sys.executable, "scripts/check-dispatch.py", "--stdin"], cwd=self.root,
                              input=f"refs/heads/main {head} refs/heads/main {base}\n",
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_branch_being_deleted_carries_nothing_to_judge(self) -> None:
        done = subprocess.run([sys.executable, "scripts/check-dispatch.py", "--stdin"], cwd=self.root,
                              input=f"(delete) {'0' * 40} refs/heads/gone "
                                    f"{self.git('rev-parse', 'HEAD').stdout.strip()}\n",
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_new_branch_is_judged_against_trunk_not_the_whole_history(self) -> None:
        """`pre-push` gives forty zeros for a branch the remote has never seen.

        The fallback used to be bare `local`, and `git rev-list` expands that to every ancestor — including
        commits already on trunk that name slices no plan knows. The commits being pushed are
        `trunk..local`, which is what a push with no range already judges.
        """
        self.ledger(["SB1"])
        self.commit("036 UI9: already on trunk, and in no plan")
        self.git("branch", "-f", "origin/main", "HEAD")
        self.git("checkout", "-b", "slice/SB1")
        self.commit("036 SB1: the work this push actually carries")
        head = self.git("rev-parse", "HEAD").stdout.strip()
        done = subprocess.run(
            [sys.executable, "scripts/check-dispatch.py", "--stdin"], cwd=self.root,
            input=f"refs/heads/slice/SB1 {head} refs/heads/slice/SB1 {'0' * 40}\n",
            capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("UI9", done.stderr + done.stdout)


if __name__ == "__main__":
    unittest.main()
