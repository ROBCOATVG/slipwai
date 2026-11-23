"""The captain dispatches a capability's gates before it asks to merge the slice that makes it whole.

The harbourmaster refuses that merge until the capability's `gates.md` says `Cleared:` on the slice's branch,
and on manda the captain asked anyway — 23 times — was refused, and only then sent the slice back to run the
gates. The captain now asks the harbourmaster's own predicate, `capabilities.ungated`, first: where it says the
gates are owed, the berth runs them and the merge is asked for once, when it would be granted.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401
from captain_fixture import AGENTS, CARRIED
from test_captain_helm import loaded

from slipwai import logs

CHART = {"slices": {"ORD-01": {"capability": "take-orders", "fairway": "ORD"},
                    "ORD-02": {"capability": "take-orders", "fairway": "ORD"}}}
GATES = "specs/ordering/capabilities/take-orders/gates.md"


class GatesFirstTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        (self.root / "scripts/agents").mkdir(parents=True)
        for name in CARRIED:
            (self.root / "scripts/agents" / name).write_text((AGENTS / name).read_text(encoding="utf-8"),
                                                             encoding="utf-8")
        (self.root / "specs/ordering").mkdir(parents=True)
        (self.root / "specs/ordering/chart.yaml").write_text(json.dumps(CHART), encoding="utf-8")
        (self.root / ".gitignore").write_text(".slipwai/\n", encoding="utf-8")
        self.git("init", "--quiet", "--initial-branch=main")
        self.commit("the chart")
        self.git("branch", "slice/ORD-02")
        # The captain's siblings are imported by bare name, and a copy cached from another case's project
        # would read that project's chart: each case's captain imports its own, and whatever was cached
        # before is put back after, so no later suite is handed a sibling from this deleted project.
        siblings = [Path(name).stem for name in CARRIED if name.endswith(".py")]
        cached = {stem: sys.modules.pop(stem) for stem in siblings if stem in sys.modules}

        def restore() -> None:
            for stem in siblings:
                sys.modules.pop(stem, None)
            sys.modules.update(cached)
        self.addCleanup(restore)
        self.module = loaded(self.root, "captain")
        self.order: list[str] = []

    def git(self, *argv: str) -> None:
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv], cwd=self.root,
                       check=True, capture_output=True)

    def commit(self, subject: str) -> None:
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", subject)

    def merged_before(self, slice_id: str) -> None:
        path = logs.deck_path(self.root, "ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as out:
            out.write(logs.entry("merged", fairway="ORD", slice=slice_id, commit="abc1234").line())

    def clear_on_branch(self) -> None:
        self.git("checkout", "--quiet", "slice/ORD-02")
        (self.root / GATES).parent.mkdir(parents=True, exist_ok=True)
        (self.root / GATES).write_text("# take-orders — gates\n\nCleared: 2026-11-23 · abc1234\n", encoding="utf-8")
        self.commit("ORD-02: the capability gates cleared")
        self.git("checkout", "--quiet", "main")

    def dispatch(self, slice_id: str, feature: str, fairway: str, retry: str = "", **_: Any) -> tuple:
        self.order.append(f"dispatch: {retry}")
        if "gates have not cleared" in retry:
            self.clear_on_branch()  # what the berth's run of the capability gates leaves on the branch
        return True, "", []

    def ask(self, slice_id: str, feature: str, fairway: str, asked: int) -> tuple[bool, str, bool]:
        self.order.append("ask")
        why = self.module.capabilities.ungated(slice_id)
        return (False, f"the merge was refused: {why}", True) if why else (True, "", False)

    def run_merge(self) -> tuple[bool, str]:
        with mock.patch.object(self.module, "dispatch", side_effect=self.dispatch), \
                mock.patch.object(self.module, "ask_to_merge", side_effect=self.ask), \
                mock.patch.object(self.module, "hold_talk"):
            return self.module.merged("ORD-02", "ordering", "ORD", 2)

    def test_the_last_slice_runs_its_capability_gates_before_the_merge_is_asked_for(self) -> None:
        self.merged_before("ORD-01")
        self.assertEqual(self.run_merge(), (True, ""))
        self.assertEqual(len(self.order), 2, self.order)
        self.assertTrue(self.order[0].startswith("dispatch: its merge would be refused: ORD-02 is the last slice "
                                                 "of take-orders"), self.order)
        self.assertIn(GATES, self.order[0])
        self.assertEqual(self.order[1], "ask", "asked once, after the gates, and granted")

    def test_a_slice_that_leaves_its_capability_unfinished_is_asked_for_at_once(self) -> None:
        self.assertEqual(self.run_merge(), (True, ""))
        self.assertEqual(self.order, ["ask"])

    def test_a_last_slice_whose_gates_already_cleared_is_asked_for_at_once(self) -> None:
        self.merged_before("ORD-01")
        self.clear_on_branch()
        self.assertEqual(self.run_merge(), (True, ""))
        self.assertEqual(self.order, ["ask"])

    def test_a_gates_run_that_did_not_finish_stops_before_any_ask(self) -> None:
        self.merged_before("ORD-01")
        with mock.patch.object(self.module, "dispatch", return_value=(False, "the gates run stopped", [])), \
                mock.patch.object(self.module, "ask_to_merge", side_effect=self.ask), \
                mock.patch.object(self.module, "hold_talk"):
            self.assertEqual(self.module.merged("ORD-02", "ordering", "ORD", 2), (False, "the gates run stopped"))
        self.assertEqual(self.order, [])

    def test_the_harbourmaster_and_the_captain_ask_one_predicate(self) -> None:
        """Not a second copy of the rule: the harbourmaster's hold is `capabilities.ungated` itself."""
        source = (AGENTS / "harbourmaster.py").read_text(encoding="utf-8")
        held = source[source.index("def ungated("):source.index("def attempts(")]
        self.assertIn("return capabilities.ungated(slice_id)", held)
        self.assertNotIn("CLEARED", held)


if __name__ == "__main__":
    unittest.main()
