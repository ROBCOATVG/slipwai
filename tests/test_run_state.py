"""What the logs say happened, folded for the model page to colour.

The browsable model already badges each slice with `model.yaml`'s `status`, written by a person at plan
time — and that is the field that failed: MANDA's model said `planned` for eight slices that were built
and merged, because nobody went back. So the page shows two bands, and this is the one nobody writes.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in ("run-state.py", "logs.py"):
            (place / name).write_text((AGENTS / name).read_text(encoding="utf-8"), encoding="utf-8")
        self.script = place / "run-state.py"

    def deck(self, fairway: str, *written: logs.Entry, feature: str = "ordering") -> None:
        path = logs.deck_path(self.root, feature, fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in written:
                handle.write(entry.line())

    def state(self) -> dict:
        done = subprocess.run([sys.executable, str(self.script), "--print"],
                              capture_output=True, text=True, cwd=self.root)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)


class StateTest(Fixture):
    def test_a_slice_the_logs_do_not_mention_is_not_in_it_at_all(self) -> None:
        """Absent, so the page can say `not started` for it rather than this inventing a row."""
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        self.assertEqual(sorted(self.state()["slices"]), ["ORD-01"])

    def test_a_slice_walks_claimed_then_marks_set_then_demoed_then_merged(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        self.assertEqual(self.state()["slices"]["ORD-01"]["state"], "claimed")
        self.deck("ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.assertEqual(self.state()["slices"]["ORD-01"]["state"], "marks set")
        self.deck("ORD", logs.entry("demo", fairway="ORD", slice="ORD-01", verdict="accepted"))
        self.assertEqual(self.state()["slices"]["ORD-01"]["state"], "demoed")
        self.deck("ORD", logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc"))
        self.assertEqual(self.state()["slices"]["ORD-01"]["state"], "merged")

    def test_the_marks_a_slice_set_are_named(self) -> None:
        self.deck("ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"),
                  logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Paid"))
        self.assertEqual(self.state()["slices"]["ORD-01"]["marks"], ["Paid", "Placed"])

    def test_every_mark_set_anywhere_is_listed(self) -> None:
        """What makes the arrows mean something: a mark that is set is what clears the slices
        steering by it, and that is the thing a picture can show and a row cannot."""
        self.deck("ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.deck("BIL", logs.entry("mark-set", fairway="BIL", slice="BIL-01", mark="Charged"),
                  feature="ordering")
        self.assertEqual(self.state()["marks"], ["Charged", "Placed"])

    def test_a_parked_fairway_parks_the_slice_it_was_working(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("parked", fairway="ORD", why="the gate stayed red"))
        held = self.state()["slices"]["ORD-01"]
        self.assertEqual(held["state"], "parked")
        self.assertEqual(held["why"], "the gate stayed red")

    def test_a_merged_slice_is_not_unmerged_by_a_later_park(self) -> None:
        """What happened to it already happened; the park is about what comes next."""
        self.deck("ORD", logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc"),
                  logs.entry("claimed", fairway="ORD", slice="ORD-02"),
                  logs.entry("parked", fairway="ORD", why="a person has to look"))
        found = self.state()["slices"]
        self.assertEqual(found["ORD-01"]["state"], "merged")
        self.assertEqual(found["ORD-02"]["state"], "parked")

    def test_a_fairway_that_started_again_is_no_longer_parked(self) -> None:
        self.deck("ORD", logs.entry("parked", fairway="ORD", why="was stuck"),
                  logs.entry("claimed", fairway="ORD", slice="ORD-02"))
        self.assertEqual(self.state()["slices"]["ORD-02"]["state"], "claimed")


class ToleranceTest(Fixture):
    def test_one_unreadable_log_does_not_stop_the_others_colouring(self) -> None:
        """This is an overlay on a picture. A picture missing one stream's colour beats no picture — the
        opposite of a board, where a hole makes the whole thing confidently wrong."""
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        bad = logs.deck_path(self.root, "ordering", "BIL")
        bad.write_text("not json\n", encoding="utf-8")
        found = self.state()
        self.assertIn("ORD-01", found["slices"])
        self.assertEqual(len(found["unreadable"]), 1)

    def test_no_logs_at_all_is_an_empty_overlay_and_not_a_fault(self) -> None:
        found = self.state()
        self.assertEqual((found["slices"], found["marks"]), ({}, []))

    def test_it_declares_its_format_so_a_newer_one_can_be_refused(self) -> None:
        self.assertEqual(self.state()["v"], 1)

    def test_it_writes_where_git_ignores_and_never_near_the_model(self) -> None:
        """Folding back into the field you are folding against leaves one band again — the one that lies."""
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        subprocess.run([sys.executable, str(self.script)], capture_output=True, text=True, cwd=self.root,
                       check=True)
        self.assertTrue((self.root / ".slipwai/run-state.json").is_file())
        self.assertFalse((self.root / "docs/event-model").exists())


class PageTest(unittest.TestCase):
    """The page's half, read off its source: the overlay is optional and the two bands never merge."""

    def setUp(self) -> None:
        self.text = (TOOLKIT_ROOT / "scripts/event-model/page.ts").read_text(encoding="utf-8")

    def test_the_run_badge_is_absent_where_there_is_no_run(self) -> None:
        """A page that needed it would be a model nobody could draw before driving it."""
        self.assertIn("if (run === undefined) return '';", self.text)

    def test_the_two_bands_are_drawn_apart(self) -> None:
        """They are different claims and one of them can be wrong, so they may not read as one."""
        self.assertIn(".badge.run", self.text)
        self.assertIn("dashed", self.text)

    def test_the_renderer_reads_the_overlay_and_never_model_yaml_for_it(self) -> None:
        render = (TOOLKIT_ROOT / "scripts/event-model/render.ts").read_text(encoding="utf-8")
        self.assertIn(".slipwai/run/run-state.json", render)
        self.assertIn("no run shown", render)

    def test_the_committed_canvas_is_not_coloured(self) -> None:
        """`model.drawio` is committed and `check-drawio` holds it current: a heartbeat would dirty the
        tree on every pass."""
        drawio = (TOOLKIT_ROOT / "scripts/event-model/render-drawio.ts").read_text(encoding="utf-8")
        self.assertNotIn("run-state", drawio)


class IgnoredTest(unittest.TestCase):
    """`logs.py` has said since 5.13 that the logs are ignored by git. Since 2.1 one line ignores the run."""

    def test_the_run_s_own_state_is_ignored(self) -> None:
        from slipwai.project.gitignore import RUN_STATE
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / ".gitignore").write_text(f"{RUN_STATE}\n", encoding="utf-8")
        for name in ("logs", "run-state.json", "running", "harbourmaster.json", "berths"):
            with self.subTest(name=name):
                self.assertTrue((logs.run_dir(root) / name).as_posix().startswith((root / RUN_STATE).as_posix()))

    def test_and_the_records_beside_it_are_not(self) -> None:
        """`extensions.json` is the election record, `hooks.json` is a controlled file that has to be
        diffable, and `packages/` is a project's own pinned packages."""
        from slipwai.project.gitignore import RUN_STATE
        for name in ("extensions.json", "hooks.json", "packages/"):
            with self.subTest(name=name):
                self.assertIn(name, logs.COMMITTED)
                self.assertNotIn(name, RUN_STATE)


if __name__ == "__main__":
    unittest.main()
