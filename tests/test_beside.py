"""One meaning for `—` in the slice graph, and no fairway held to one slice at a time without a reason.

A split stage with nobody present wrote `—` in `parallel_ok_with` on every row of a 38-slice fairway: the
template offered `—` for "none" in `depends_on`, and `clearance.py` read `—` in the next column as "runs
beside nothing". The fairway ran serially all night. Nothing caught it because the two halves were only ever
tested apart — the template as text, the reader with hand-written tables. These cases run the template's
own words through the real reader, the real `ready`, the real gate, the real filler, `migrate`'s section and
the board, so the two cannot drift apart again without a test going red.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

import checkout_packages  # noqa: F401
from captain_fixture import CARRIED

from slipwai import fleet, logs
from slipwai.assets import ROOT, TOOLKIT_ROOT
from slipwai.bridge_page import berth_rows
from slipwai.migration_beside import section

AGENTS = TOOLKIT_ROOT / "scripts/agents"
SKILL = TOOLKIT_ROOT / "skills/story-splitting/SKILL.md"
EVENT_TEMPLATES = ROOT / "assets/profiles/event-modelling/.specify/presets/event-modelling/templates"
SLICES = ("L01", "L02", "L03", "L04")
CONTEXT = ("## D1 — Which bounded contexts does f touch?\n- **Question:** which bounded context\n\n"
           "| candidate | entities | evidence | crosses | confidence |\n|---|---|---|---|---|\n"
           "| ledger | Entry | spec | nothing | high |\n")


def template_rows() -> list[tuple[str, str, str]]:
    """(where, the `depends_on` legend cell, the `parallel_ok_with` legend cell) of every slice-graph template
    a split- or plan-writing stage fills in."""
    found = []
    for path in (SKILL, EVENT_TEMPLATES / "plan-template.md", EVENT_TEMPLATES / "tasks-template.md"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if line.replace(" ", "").startswith("|Slice|depends_on|parallel_ok_with|"):
                cells = [cell.strip() for cell in lines[index + 2].strip().strip("|").split("|")]
                found.append((path.name, cells[1], cells[2]))
    return found


def none_of(legend: str) -> str:
    """The placeholder a template's `depends_on` legend offers for "none": the cell an agent writes there."""
    said = re.search(r"[—–-]", legend)
    assert said, f"the legend {legend!r} offers no placeholder for none"
    return said.group(0)


class Project(unittest.TestCase):
    """A generated project in miniature: the toolkit's own scripts, copied where a project has them."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in {*CARRIED, "beside.py", "feedback.py", "hooks.py"}:
            if (AGENTS / name).is_file():
                shutil.copy(AGENTS / name, place / name)
        shutil.copy(TOOLKIT_ROOT / "scripts/check-chart.py", self.root / "scripts/check-chart.py")
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        (self.root / "specs/f").mkdir(parents=True)
        self.chart()

    def chart(self, fairways: dict[str, tuple[str, ...]] | None = None) -> None:
        fairways = fairways or {"LED": SLICES}
        body = "v: 1\nfeature: f\nmarks: {}\nfairways:\n" + "".join(
            f"  {name}: {{owns: [src/{name.lower()}]}}\n" for name in fairways) + "slices:\n" + "".join(
            f"  {one}: {{fairway: {name}, capability: keep, sets: [], steers_by: []}}\n"
            for name, ones in fairways.items() for one in ones)
        (self.root / "specs/f/chart.yaml").write_text(body, encoding="utf-8")

    def split(self, rows: str, before: str = "") -> None:
        (self.root / "specs/f/story-split.md").write_text(
            f"# Split\n\n{before}## Slice graph\n\n| Slice | depends_on | parallel_ok_with | Notes |\n"
            f"|---|---|---|---|\n{rows}\n## Parking Lot\n", encoding="utf-8")

    def decisions(self, text: str = "") -> None:
        (self.root / "specs/f/decisions.md").write_text(f"# Decisions\n\n{CONTEXT}\n{text}", encoding="utf-8")

    def load(self, name: str) -> ModuleType:
        """A toolkit script from this project, fresh: they resolve the project from where they sit."""
        place = self.root / "scripts/agents"
        for one in ("beside", "clearance", "logs", "abreast", "captain", "ids", "talk"):
            sys.modules.pop(one, None)
        sys.path.insert(0, str(place))
        try:
            spec = importlib.util.spec_from_file_location(name, place / f"{name}.py")
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            return module
        finally:
            sys.path.remove(str(place))

    def gate(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.root / "scripts/check-chart.py")], cwd=self.root,
                              capture_output=True, text=True, check=False)

    def deck(self, *entries: logs.Entry) -> None:
        path = self.root / ".slipwai/logs/f/LED.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())


class TemplateAgreesWithClearance(Project):
    """The live failure, from the template's own words: the "none" it offers, written in both columns."""

    def test_the_placeholder_the_template_offers_restricts_nothing_in_either_column(self) -> None:
        rows = template_rows()
        self.assertGreaterEqual(len(rows), 3, "a slice-graph template went missing")
        for where, depends_legend, _ in rows:
            with self.subTest(template=where):
                none = none_of(depends_legend)
                self.split("".join(f"| {one} | {none} | {none} | |\n" for one in SLICES))
                clearance = self.load("clearance")
                depends, parallel = clearance.slice_graph(json.loads(json.dumps(
                    {"feature": "f", "slices": {one: {"fairway": "LED"} for one in SLICES}})))
                self.assertEqual(depends, {one: [] for one in SLICES})
                for one in SLICES:
                    for other in SLICES:
                        if one != other:
                            self.assertTrue(clearance.independent(parallel, one, other),
                                            f"{where}: `{none}` in parallel_ok_with barred {one} from {other}")

    def test_runs_beside_nothing_is_a_word_the_template_names_and_the_reader_reads(self) -> None:
        for where, _, parallel_legend in template_rows():
            with self.subTest(template=where):
                self.assertIn("alone", parallel_legend)
        self.split("| L01 | — | alone | |\n| L02, L03, L04 | — | each other | |\n")
        clearance = self.load("clearance")
        _, parallel = clearance.slice_graph({"feature": "f", "slices": {one: {"fairway": "LED"} for one in SLICES}})
        self.assertEqual(parallel["L01"], set())
        self.assertFalse(clearance.independent(parallel, "L01", "L02"))
        self.assertTrue(clearance.independent(parallel, "L02", "L04"))


class TemplateThroughReady(Project):
    """End to end: the real template's rows, filled the way an agent with nobody present fills them, through
    the real `ready` and the real harbourmaster plan with three boilers. More than one slice starts."""

    def test_more_than_one_slice_of_one_fairway_starts(self) -> None:
        _, depends_legend, _ = template_rows()[0]
        none = none_of(depends_legend)
        self.split("".join(f"| {one} | {none} | {none} | |\n" for one in SLICES))
        abreast = self.load("abreast")
        clearance = abreast.clearance
        charted, feature = clearance.chart()
        folded_logs = clearance.with_evidence(charted, clearance.folded(clearance.lines(feature)))
        started = abreast.ready(charted, folded_logs, clearance.done_marked(feature), "LED", [])
        self.assertGreater(len(started), 1, f"only {started} may start: the template and the reader disagree")
        config = self.root / "harbour.json"
        config.write_text(json.dumps({"boilers": 3}), encoding="utf-8")
        self.assertGreaterEqual(abreast.harbour_plan(set(), config)["LED"][0], 2)


class GateTest(Project):
    def test_an_all_placeholder_split_with_no_decision_is_refused_naming_fairway_rows_and_fix(self) -> None:
        self.split("".join(f"| {one} | — | — | |\n" for one in SLICES))
        self.decisions()
        done = self.gate()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("fairway `LED`", done.stderr)
        self.assertIn("L01 | — | —", done.stderr)
        self.assertIn("beside.py --fill --feature f", done.stderr)

    def test_a_fairway_every_slice_of_which_runs_alone_is_refused_without_a_decision(self) -> None:
        self.split("".join(f"| {one} | — | alone | |\n" for one in SLICES))
        self.decisions()
        done = self.gate()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("no two of its slices may run together", done.stderr)

    def test_the_gate_passes_when_a_decision_records_the_choice(self) -> None:
        self.split("".join(f"| {one} | — | alone | |\n" for one in SLICES))
        self.decisions("## D2 — Which slices may run beside which (`parallel_ok_with`)?\n"
                       "- **Why:** one ledger, every slice rewrites its totals\n")
        done = self.gate()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_one_slice_fairways_and_filled_columns_owe_nothing(self) -> None:
        self.split("| L01 | — | L02 | |\n| L02 | — | L01 | |\n| L03 | — | — | |\n| L04 | — | — | |\n")
        self.decisions()
        self.assertEqual(self.gate().returncode, 0)


class FillTest(Project):
    """Migrate's section, then `/catch-up`'s fill, then the gate, then the captain starting two slices."""

    def setUp(self) -> None:
        super().setUp()
        model = self.root / "docs/event-model/model.yaml"
        model.parent.mkdir(parents=True)
        model.write_text(
            "slices:\n"
            "  - {id: L01, stream: entry, code: [src/main.ts, src/entry.ts]}\n"
            "  - {id: L02, stream: entry, code: [src/main.ts]}\n"
            "  - {id: L03, stream: total, code: [src/main.ts],"
            " frames: [{mockups: [{at: docs/event-model/mockups/total.html}]}]}\n"
            "  - {id: L04, stream: report, code: [src/main.ts],"
            " frames: [{mockups: [{at: docs/event-model/mockups/total.html}]}]}\n", encoding="utf-8")
        self.split("".join(f"| {one} | — | — | |\n" for one in SLICES))
        self.decisions()
        self.deck(logs.entry("claimed", fairway="LED", slice="L01", t="2026-11-01T09:00:00Z"),
                  logs.entry("merged", fairway="LED", slice="L01", commit="a1b2c3d", t="2026-11-01T10:00:00Z"))

    def test_migrate_names_the_split_and_changes_nothing(self) -> None:
        before = (self.root / "specs/f/story-split.md").read_text(encoding="utf-8")
        said = "\n".join(section(self.root, {}))
        self.assertIn("`LED` in `specs/f/story-split.md`: 4 slices", said)
        self.assertIn("beside.py --fill --feature f", said)
        self.assertEqual((self.root / "specs/f/story-split.md").read_text(encoding="utf-8"), before)

    def test_catch_up_fills_from_collisions_records_a_decision_and_the_gate_and_captain_follow(self) -> None:
        self.assertEqual(self.gate().returncode, 1)
        beside = self.load("beside")
        said = beside.fill("f")
        self.assertIn("filled parallel_ok_with for 3 slice(s)", said)
        clearance = self.load("clearance")
        charted, _ = clearance.chart()
        _, parallel = clearance.slice_graph(charted)
        self.assertIsNone(parallel["L01"])  # merged: kept as written
        self.assertEqual(parallel["L02"], {"L03", "L04"})  # main.ts is a seam, not a collision
        self.assertEqual(parallel["L03"], {"L02"})  # L03 and L04 build one screen
        self.assertEqual(parallel["L04"], {"L02"})
        log = (self.root / "specs/f/decisions.md").read_text(encoding="utf-8")
        self.assertRegex(log, r"## D\d+ — Which slices may run beside which")
        self.assertIn("**Status:** awaiting human confirmation", log)
        self.assertIn("`src/main.ts`", log)
        self.assertEqual(self.gate().returncode, 0, self.gate().stderr)
        self.assertEqual(section(self.root, {}), [])  # repaired: migrate owes nothing more
        captain = self.load("captain")
        started, why = captain.next_slices("LED", [])
        self.assertGreaterEqual(len(started), 2, why)
        config = self.root / "harbour.json"
        config.write_text(json.dumps({"boilers": 3}), encoding="utf-8")
        self.assertGreaterEqual(captain.abreast.harbour_plan(set(), config)["LED"][0], 2)


class BoardTest(Project):
    def berths(self) -> list[dict]:
        found = fleet.board(self.root, {"boilers": 3})["berths"]
        assert isinstance(found, list)
        return found

    def test_a_fairway_the_split_holds_to_one_says_so_instead_of_working(self) -> None:
        self.split("".join(f"| {one} | — | alone | |\n" for one in SLICES))
        self.deck(logs.entry("claimed", fairway="LED", slice="L01"), logs.entry("heartbeat", fairway="LED",
                                                                                 slice="L01"))
        berths = self.berths()
        row = next(one for one in berths if one["fairway"] == "LED")
        self.assertEqual(row["state"], "working")
        self.assertIn("can only run one slice at a time because the split says so", row["alone"])
        self.assertIn("L02", row["alone"])
        drawn = berth_rows(berths, {})
        self.assertIn("one at a time", drawn)
        self.assertIn("because the split says so", drawn)

    def test_an_ordinary_fairway_says_nothing_extra(self) -> None:
        self.split("".join(f"| {one} | — | — | |\n" for one in SLICES))
        self.deck(logs.entry("claimed", fairway="LED", slice="L01"), logs.entry("heartbeat", fairway="LED",
                                                                                 slice="L01"))
        row = next(one for one in self.berths() if one["fairway"] == "LED")
        self.assertEqual(row["alone"], "")


if __name__ == "__main__":
    unittest.main()
