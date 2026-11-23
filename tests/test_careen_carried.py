"""The careen fed by one writer, and run as its fairway's last slice (issue 154).

On manda the instructions told every slice to write `fairways/<name>/careen.md` and `check-slice-scope`
refused it the file: S62 wrote, was refused, handed the rows back, and conflicted with the mender's landing
of them for five merge attempts. 174 rows were stowed and 41 reached a careen; the modelling fairway had
none at all. And nothing started the careen: the captain said *every slice is claimed or merged* and went
idle. These cases are the three halves of the fix, each against the real script — a merge in a real
repository, the scope gate on a real branch, the captain's own choice of what to start next.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from captain_fixture import Fixture as CaptainFixture
from harbourmaster_fixture import MergeFixture

from slipwai import logs
from slipwai.project.careen import ROW_HEADER

RULE = "|---|---|---|---|---|---|"
ROW_A = "| 2026-11-23 | ORD-01 | converge | MEDIUM | CV-1: a deleted order is still listed; filter it | open |"
ROW_B = "| 2026-11-23 | ORD-02 | adversary | LOW | A-3: the 400 says `id`; say what was missing | open |"
RECORD = "specs/ordering/capabilities/place-an-order/stowed.md"
CAREEN = "fairways/ORD/careen.md"


def stowed(*rows: str) -> str:
    return "\n".join(["# Stowed — place-an-order", "", ROW_HEADER, RULE, *rows]) + "\n"


class HarbourmasterCarriesTest(MergeFixture):
    """The harbourmaster appends what a merge stowed to the careen, on trunk, as part of the merge."""

    def slice_with(self, slice_id: str, body: str) -> None:
        self.git("checkout", "--quiet", "-B", f"slice/{slice_id}", "main")
        (self.root / RECORD).parent.mkdir(parents=True, exist_ok=True)
        (self.root / RECORD).write_text(body, encoding="utf-8")
        (self.root / f"{slice_id}.txt").write_text(slice_id, encoding="utf-8")
        self.commit(slice_id)
        self.git("checkout", "--quiet", "-B", "parked-elsewhere", f"slice/{slice_id}")

    def merged(self, slice_id: str) -> logs.Entry:
        self.ask(slice_id)
        done = self.run_once()
        found = [e for e in self.harbour() if e.kind in ("granted", "refused")
                 and e.fields.get("slice") == slice_id]
        self.assertTrue(found, done.stdout + done.stderr)
        return found[-1]

    def test_a_fairway_with_no_careen_gets_one_holding_what_the_merge_stowed(self) -> None:
        self.slice_with("ORD-01", stowed(ROW_A))
        answer = self.merged("ORD-01")
        self.assertEqual(answer.kind, "granted", answer.fields)
        careen = self.git("show", f"main:{CAREEN}").stdout
        self.assertTrue(careen.startswith("# Careen — ORD"), careen)
        self.assertIn(ROW_A, careen.split("## place-an-order", 1)[1])
        self.assertEqual(self.head("main"), answer.fields["commit"], "trunk moved once, with the careen in it")

    def test_a_record_carried_again_adds_only_its_new_rows(self) -> None:
        self.slice_with("ORD-01", stowed(ROW_A))
        self.assertEqual(self.merged("ORD-01").kind, "granted")
        self.slice_with("ORD-02", stowed(ROW_A, ROW_B))
        self.assertEqual(self.merged("ORD-02").kind, "granted")
        careen = self.git("show", f"main:{CAREEN}").stdout
        self.assertEqual(careen.count(ROW_A), 1, careen)
        self.assertEqual(careen.count(ROW_B), 1, careen)
        self.assertEqual(careen.count("## place-an-order"), 1, careen)

    def test_a_merge_that_stowed_nothing_leaves_the_careen_alone(self) -> None:
        self.slice_branch("ORD-01", "service.txt", "two\n")
        self.assertEqual(self.merged("ORD-01").kind, "granted")
        self.assertNotEqual(self.git("cat-file", "-e", f"main:{CAREEN}").returncode, 0)


GATE = Path(__file__).resolve().parents[1] / "assets/toolkit/scripts/check-slice-scope.py"
CHART = """
v: 1
feature: ordering
fairways:
  ORD: {context: ordering, owns: [apps/orders/**]}
slices:
  ORD-01: {fairway: ORD, capability: place-an-order, sets: [], steers_by: []}
"""


class SliceScopeTest(unittest.TestCase):
    """A slice writes its capability's record and never the careen; the careen slice alone closes its rows."""

    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(GATE, self.tree / "scripts/check-slice-scope.py")
        (self.tree / "specs/ordering").mkdir(parents=True)
        (self.tree / "specs/ordering/chart.yaml").write_text(textwrap.dedent(CHART).lstrip(), encoding="utf-8")
        (self.tree / "project.json").write_text('{"deployables": {}}', encoding="utf-8")
        for argument in ("init -q -b main", "config user.email g@example.com", "config user.name g"):
            subprocess.run(["git", *argument.split()], cwd=self.tree, capture_output=True, check=True)
        from test_slice_scope import gate_module
        self.module = gate_module(self.tree)

    def test_a_slice_may_write_its_capability_s_stowed_record(self) -> None:
        self.assertIsNone(self.module.Scope("ORD-01", "main").violation(RECORD, "A"))

    def test_a_slice_may_not_write_the_careen_and_is_told_where_its_rows_go(self) -> None:
        found = self.module.Scope("ORD-01", "main").violation(CAREEN, "M")
        self.assertIsNotNone(found)
        self.assertIn("stowed.md", found or "")
        self.assertIn("harbourmaster", found or "")

    def test_the_careen_slice_closes_its_own_fairway_s_careen_and_nothing_else_there(self) -> None:
        scope = self.module.Scope("ORD-careen", "main")
        self.assertIsNone(scope.violation(CAREEN, "M"))
        self.assertIsNotNone(scope.violation("fairways/BIL/careen.md", "M"))
        self.assertIsNotNone(scope.violation("fairways/ORD/decisions.md", "M"))


#: Two planned slices in ORD and one `observed` one, which nobody builds and so nothing ever merges.
CAPTAIN_CHART = ("slices:\n"
                 "  ORD-01: {fairway: ORD, sets: [], steers_by: []}\n"
                 "  ORD-02: {fairway: ORD, sets: [], steers_by: []}\n"
                 "  ORD-00: {fairway: ORD, sets: [], steers_by: [], observed: true}\n")
#: What the captain decides, asked of the captain program itself in the project, as a turn asks it.
ASK = ("import json, sys\nsys.path.insert(0, 'scripts/agents')\nimport captain\n"
       "found, why = captain.next_slices('ORD', json.loads(sys.argv[1]))\n"
       "print(json.dumps({'found': found, 'why': why, "
       "'prompt': captain.sail_prompt(None, 'ORD-careen', 'ORD')}))\n")


class CaptainStartsTheCareenTest(CaptainFixture):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "specs/ordering/chart.yaml").write_text(CAPTAIN_CHART, encoding="utf-8")
        (self.root / "commands").mkdir()
        (self.root / "commands/careen.md").write_text("# Careen\n", encoding="utf-8")

    def merged(self, *slices: str) -> None:
        path = logs.deck_path(self.root, "ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for slice_id in slices:
                handle.write(logs.entry("claimed", fairway="ORD", slice=slice_id).line())
                handle.write(logs.entry("merged", fairway="ORD", slice=slice_id, commit="c0ffee").line())

    def careen(self, *rows: str) -> None:
        (self.root / CAREEN).parent.mkdir(parents=True, exist_ok=True)
        (self.root / CAREEN).write_text("\n".join(["# Careen — ORD", "", "## place-an-order", "", ROW_HEADER,
                                                   RULE, *rows]) + "\n", encoding="utf-8")

    def ask(self, beside: list[str] | None = None) -> dict:
        done = subprocess.run([sys.executable, "-c", ASK, json.dumps(beside or [])], cwd=self.root,
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout.strip().splitlines()[-1])

    def test_with_every_planned_slice_merged_and_a_row_open_the_careen_is_next(self) -> None:
        self.merged("ORD-01", "ORD-02")
        self.careen(ROW_A, ROW_B.replace("| open |", "| done |"))
        self.assertEqual(self.ask()["found"], ["ORD-careen"])

    def test_the_careen_runs_its_own_command_for_its_fairway(self) -> None:
        self.merged("ORD-01", "ORD-02")
        self.careen(ROW_A)
        prompt = self.ask()["prompt"]
        self.assertTrue(prompt.startswith("Run the /careen command: read commands/careen.md"), prompt)
        self.assertIn("with `ORD` as its argument", prompt)
        self.assertNotIn("Run the /sail command", prompt)

    def test_with_no_open_row_the_stream_ends_as_before(self) -> None:
        self.merged("ORD-01", "ORD-02")
        self.careen(ROW_A.replace("| open |", "| done |"))
        said = self.ask()
        self.assertEqual(said["found"], [])
        self.assertEqual(said["why"], "every slice of ORD is claimed or merged")

    def test_with_no_careen_at_all_the_stream_ends_as_before(self) -> None:
        self.merged("ORD-01", "ORD-02")
        self.assertEqual(self.ask()["why"], "every slice of ORD is claimed or merged")

    def test_not_while_a_planned_slice_is_unmerged_or_anything_is_in_flight(self) -> None:
        self.merged("ORD-01")
        self.careen(ROW_A)
        self.assertNotIn("ORD-careen", self.ask()["found"])
        self.merged("ORD-02")
        self.assertEqual(self.ask(["ORD-02"])["found"], [])

    def test_a_careen_already_merged_is_not_offered_again(self) -> None:
        self.merged("ORD-01", "ORD-02", "ORD-careen")
        self.careen(ROW_A)
        self.assertEqual(self.ask()["found"], [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
