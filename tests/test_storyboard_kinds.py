"""Built, changed and new: a storyboard says which each surface is, and a person is asked only about what is new.

A further feature is drawn into the flow the project already has. What is built is framed from the real thing
and marked `data-surface="built"`; a surface this feature changes, or adds, is a page beside the storyboard.
The board shows the three apart, its verdict covers the changed and the new only, and `check-surfaces` holds
the split to what was approved without asking after a built surface nobody was asked about.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401
from crossed_project import FURTHER, crossed, storyboard, write

from slipwai.drawn import built_pages, fingerprints, record_verdict, surface_kinds, surface_pages, withdraw
from slipwai.storyboard_card import mockups_card, standing, verdict_form
from slipwai.voyage import mockup_file, mockups

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "assets/toolkit/scripts/check-surfaces.py"
SPLIT = """\
| Slice | Value | Surfaces and states |
|---|---|---|
| EXP-01 | offers the export | Deal console · Export offered |
| EXP-02 | builds the pack | Export pack · Ready; Export pack · Failed |
"""


def gate() -> Any:
    spec = importlib.util.spec_from_file_location("check_surfaces_kinds", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


class KindsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = crossed(Path(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = storyboard(self.root)

    def verdicts(self) -> str:
        return (self.home / "mock-states.md").read_text(encoding="utf-8")

    def test_the_storyboard_says_which_each_surface_is(self) -> None:
        kinds = {path.name: kind for path, kind in surface_kinds(self.home).items()}
        self.assertEqual(kinds, {"sign-in.html": "built", "deal-console-deals.html": "built",
                                 "deal-console.html": "changed", "export-pack.html": "new"})
        self.assertEqual([page.name for page in built_pages(self.home)], ["sign-in.html", "deal-console-deals.html"])

    def test_only_the_changed_and_the_new_are_surfaces_to_judge(self) -> None:
        self.assertEqual([page.name for page in surface_pages(self.home)], ["deal-console.html", "export-pack.html"])

    def test_a_storyboard_of_built_frames_alone_has_nothing_to_judge(self) -> None:
        """Without the mark these would be read as handed-over mock-ups, and approved as if somebody had looked."""
        for name in ("deal-console.html", "export-pack.html"):
            (self.home / name).unlink()
        self.assertEqual(surface_pages(self.home), [])
        said = verdict_form(self.root, FURTHER)
        self.assertNotIn("data-verdict", said)
        self.assertIn("is built already", said)
        with self.assertRaises(ValueError):
            record_verdict(self.root, FURTHER, "approved")

    def test_approving_marks_the_changed_and_the_new_and_says_the_built_were_not_asked_about(self) -> None:
        record_verdict(self.root, FURTHER, "approved")
        said = self.verdicts()
        self.assertIn("## Surface: Deal console\n- Export offered — approved", said)
        self.assertIn("## Surface: Export pack\n- Ready — approved\n- Failed — approved", said)
        self.assertEqual(said.count("— approved"), 3, "nothing built is newly approved")
        self.assertIn("<!-- built: Sign in — apps/web/screens/sign-in.html (", said)
        self.assertIn("<!-- built: Deal console — deals — apps/web/screens/deal-console-deals.html (", said)
        self.assertEqual(standing(self.root, FURTHER), ("approved", ""))

    def test_a_built_preview_that_changes_later_withdraws_no_verdict(self) -> None:
        record_verdict(self.root, FURTHER, "approved")
        before = fingerprints(self.root)
        write(self.root, "apps/web/screens/sign-in.html", "<title>Sign in</title><main>rebuilt</main>")
        self.assertEqual(withdraw(self.root, before), [])
        self.assertEqual(standing(self.root, FURTHER), ("approved", ""))

    def test_the_gate_holds_the_split_to_what_was_approved_and_not_to_what_is_built(self) -> None:
        record_verdict(self.root, FURTHER, "approved")
        module = gate()
        self.assertEqual(module.faults(self.verdicts(), SPLIT, "specs/x/story-split.md"), [])

    def test_a_slice_that_names_a_built_surface_is_told_it_was_never_put_up_for_a_verdict(self) -> None:
        record_verdict(self.root, FURTHER, "approved")
        found = gate().faults(self.verdicts(), SPLIT + "| EXP-03 | restyles sign-in | Sign in · shown |\n", "split")
        self.assertEqual(len(found), 1, found)
        self.assertIn("is shown as built", found[0])
        self.assertIn('data-surface="changed"', found[0])

    def test_the_card_shows_the_three_apart_and_asks_only_about_two(self) -> None:
        card = mockups_card(mockups(self.root), self.root)
        self.assertIn('<span class="chip built">Built · 2</span>', card)
        self.assertIn('<span class="chip changed">Changed · 1</span>', card)
        self.assertIn('<span class="chip new">New · 1</span>', card)
        self.assertIn("Deal console — deals", card)
        form = verdict_form(self.root, FURTHER)
        self.assertIn("Approving marks every changed and new state approved", form)
        self.assertIn("2 built surfaces are shown for the flow and are not asked about", form)

    def test_a_storyboard_that_marks_nothing_reads_as_it_always_did(self) -> None:
        board = self.home / "storyboard.html"
        board.write_text(board.read_text(encoding="utf-8").replace("data-surface", "data-other"), encoding="utf-8")
        self.assertEqual(built_pages(self.home), [])
        self.assertNotIn("chip built", mockups_card(mockups(self.root), self.root))
        self.assertIn("Approving marks every drawn state approved", verdict_form(self.root, FURTHER))

    def test_the_board_serves_the_apps_previews_and_stylesheets_a_storyboard_frames(self) -> None:
        """A storyboard frames the real thing where it lies; refused, every built frame is an empty box."""
        root = self.root.resolve()
        for served in ("apps/web/screens/sign-in.html", "apps/web/src/styles/tokens.css"):
            self.assertEqual(mockup_file(self.root, served), root / served, served)
        for refused in ("apps/web/src/App.tsx", "apps/web/package.json", "apps/api/screens/x.html",
                        "project.json", "apps/web/screens/../package.json"):
            write(self.root, "apps/api/screens/x.html", "<title>x</title>")
            self.assertIsNone(mockup_file(self.root, refused), refused)


if __name__ == "__main__":
    unittest.main()
