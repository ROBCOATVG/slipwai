"""Planned: a surface an earlier feature had approved and nobody has built yet has a word of its own.

It was framed as `built`, with its cell saying in words that it was not. `data-surface="planned"` is the fourth
word beside `built`, `changed` and `new`: `existing.py` says which surfaces are planned from the evidence — a
state somebody approved, and nothing that says it is built — and everything that read three words reads four.
A planned frame is treated as a built one is: shown for the flow, not this feature's to approve or to deliver.
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
from crossed_project import FIRST, FURTHER, crossed, storyboard, write

from slipwai.drawn import record_verdict, surface_pages
from slipwai.framed import KINDS, built_pages, planned_pages, surface_kinds
from slipwai.storyboard_card import mockups_card, verdict_form
from slipwai.voyage import mockups

ROOT = Path(__file__).resolve().parents[1]
TOOLKIT = ROOT / "assets/toolkit/scripts"
VERDICTS = ("## Surface: Deal console\n- Export offered — approved\n\n"
            "## Surface: Export pack\n- Ready — approved\n- Failed — parked: which failure?\n")
SPLIT = """\
| Slice | Value | Surfaces and states |
|---|---|---|
| SHR-01 | shares the pack | Share pack · Link ready |
"""


def loaded(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # Python 3.11's dataclasses look a module up by name
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


def further(root: Path) -> Path:
    """`002-export` drawn after `001-deals` was approved and not built: one built frame, the earlier feature's
    export pack framed as planned, and one surface that is new."""
    storyboard(root, FIRST)
    write(root, f"specs/{FIRST}/mockups/mock-states.md", VERDICTS)
    write(root, f"specs/{FURTHER}/mockups/share-pack.html",
          '<title>Share pack</title><article class="state"><h2>Link ready</h2></article>')
    write(root, f"specs/{FURTHER}/mockups/storyboard.html",
          "<title>Storyboard</title>"
          '<iframe data-surface="built" src="../../../apps/web/screens/sign-in.html"></iframe>'
          f'<iframe data-surface="planned" src="../../{FIRST}/mockups/export-pack.html"></iframe>'
          '<a data-surface="new" href="share-pack.html">Share pack</a>')
    return root / "specs" / FURTHER / "mockups"


class ClassifiedTest(unittest.TestCase):
    """What `existing.py` says each surface is, from the evidence."""

    def setUp(self) -> None:
        self.tree = crossed(Path(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.tree, True)
        self.module = loaded(TOOLKIT / "agents/existing.py", "existing_planned")
        storyboard(self.tree, FIRST)
        write(self.tree, f"specs/{FIRST}/mockups/mock-states.md", VERDICTS)

    def surfaces(self) -> dict[str, dict[str, Any]]:
        return {one["name"]: one for one in self.module.listing(FURTHER, self.tree)["surfaces"]}

    def test_an_approved_surface_nothing_says_is_built_is_planned(self) -> None:
        pack = self.surfaces()["Export pack"]
        self.assertEqual((pack["kind"], pack["evidence"], pack["feature"]), ("planned", "approved", FIRST))
        self.assertEqual(pack["picture"], f"specs/{FIRST}/mockups/export-pack.html")
        self.assertEqual(pack["states"], 1, "the parked state is not an approval")

    def test_what_has_a_preview_is_built_whoever_approved_it(self) -> None:
        found = self.surfaces()
        console = found["Deal console"]
        self.assertEqual((console["kind"], console["evidence"]), ("built", "preview"))
        self.assertEqual(console["approved"], [f"{FIRST}: specs/{FIRST}/mockups/deal-console.html"])
        self.assertEqual(console["routes"], ["/ (DealConsole)"])
        self.assertEqual(found["New workspace"]["frames"], ["NewWorkspaceForm (S1 implemented)"])
        self.assertEqual(self.module.listing(FURTHER, self.tree)["counts"],
                         {"built": 3, "unseen": 0, "planned": 1})

    def test_a_planned_surface_is_built_once_there_is_evidence_of_it(self) -> None:
        write(self.tree, "apps/web/screens/export-pack-ready.html", "<title>Export pack — ready</title>")
        pack = self.surfaces()["Export pack"]
        self.assertEqual((pack["kind"], pack["evidence"]), ("built", "preview"))
        self.assertEqual(self.module.listing(FURTHER, self.tree)["counts"]["planned"], 0)

    def test_a_surface_nobody_approved_is_neither(self) -> None:
        """Drawn and parked is a question still open: nothing to frame as settled, in either word."""
        write(self.tree, f"specs/{FIRST}/mockups/mock-states.md",
              "## Surface: Export pack\n- Ready — parked: is there a pack at all?\n")
        self.assertNotIn("Export pack", self.surfaces())

    def test_the_order_is_the_same_whatever_the_platform_lists_first(self) -> None:
        names = [one["name"] for one in self.module.listing(FURTHER, self.tree)["surfaces"]]
        self.assertEqual(names, ["Deal console", "New workspace", "Sign in", "Export pack"])

    def test_the_page_says_the_fourth_word_and_which_surface_it_is(self) -> None:
        said = self.module.said(self.module.listing(FURTHER, self.tree))
        self.assertIn('`data-surface="planned"`', said)
        self.assertIn("3 built, 0 of them with no picture; 1 planned.", said)
        self.assertIn(f"- planned — Export pack — approved for {FIRST} (1 state(s)) and nothing here says it is "
                      f"built: frame specs/{FIRST}/mockups/export-pack.html", said)
        self.assertIn("- built — Deal console — a preview: apps/web/screens/deal-console-deals.html", said)

    def test_the_marks_are_read_as_four_words(self) -> None:
        home = further(self.tree)
        self.assertEqual(sorted(self.module.kinds(home).values()), ["built", "new", "planned"])
        self.assertEqual(self.module.FRAMED, ("built", "planned"))


class FramedTest(unittest.TestCase):
    """A planned frame on the board: shown apart, and treated as a built one is."""

    def setUp(self) -> None:
        self.root = crossed(Path(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = further(self.root)

    def test_there_are_four_words_and_two_of_them_are_framed(self) -> None:
        self.assertEqual(KINDS, ("built", "planned", "changed", "new"))
        kinds = {path.name: kind for path, kind in surface_kinds(self.home).items()}
        self.assertEqual(kinds, {"sign-in.html": "built", "export-pack.html": "planned", "share-pack.html": "new"})
        self.assertEqual([page.name for page in planned_pages(self.home)], ["export-pack.html"])
        self.assertEqual([page.name for page in built_pages(self.home)], ["sign-in.html"])

    def test_a_planned_frame_is_not_this_features_to_approve(self) -> None:
        self.assertEqual([page.name for page in surface_pages(self.home)], ["share-pack.html"])
        record_verdict(self.root, FURTHER, "approved")
        said = (self.home / "mock-states.md").read_text(encoding="utf-8")
        self.assertEqual(said.count("— approved"), 1, "only the new surface's state is approved here")
        self.assertIn(f"<!-- planned: Export pack — specs/{FIRST}/mockups/export-pack.html (shown as planned", said)
        self.assertNotIn("## Surface: Export pack", said)
        self.assertEqual((self.root / f"specs/{FIRST}/mockups/mock-states.md").read_text(encoding="utf-8"),
                         VERDICTS, "the earlier feature's verdicts are not reopened")

    def test_a_storyboard_of_planned_frames_alone_has_nothing_to_judge(self) -> None:
        (self.home / "share-pack.html").unlink()
        board = self.home / "storyboard.html"
        board.write_text(board.read_text(encoding="utf-8").replace('data-surface="built"', 'data-surface="planned"'),
                         encoding="utf-8")
        self.assertEqual(surface_pages(self.home), [])
        said = verdict_form(self.root, FURTHER)
        self.assertNotIn("data-verdict", said)
        self.assertIn("or planned by an earlier feature", said)

    def test_the_card_shows_the_four_apart_and_asks_only_about_two(self) -> None:
        card = mockups_card(mockups(self.root), self.root)
        self.assertIn('<span class="chip built">Built · 1</span> Sign in', card)
        self.assertIn('<span class="chip planned">Planned · 1</span> Export pack', card)
        self.assertIn('<span class="chip new">New · 1</span> Share pack', card)
        self.assertIn("Approving marks every changed and new state approved; the 1 built surface and 1 planned "
                      "surface are shown for the flow and are not asked about.", verdict_form(self.root, FURTHER))

    def test_a_slice_that_names_a_planned_surface_is_told_whose_it_is(self) -> None:
        record_verdict(self.root, FURTHER, "approved")
        said = (self.home / "mock-states.md").read_text(encoding="utf-8")
        gate = loaded(TOOLKIT / "check-surfaces.py", "check_surfaces_planned")
        self.assertEqual(gate.faults(said, SPLIT, "split"), [])
        found = gate.faults(said, SPLIT + "| SHR-02 | builds the pack | Export pack · Ready |\n", "split")
        self.assertEqual(len(found), 1, found)
        self.assertIn("is shown as planned", found[0])
        self.assertIn("that feature's", found[0])

    def test_the_stage_does_not_count_a_planned_frame_as_drawn(self) -> None:
        agents = str(TOOLKIT / "agents")
        sys.path.insert(0, agents)
        self.addCleanup(sys.path.remove, agents)
        module = loaded(TOOLKIT / "agents/surfaces.py", "surfaces_planned")
        module.ROOT, module.SPECS = self.root, self.root / "specs"
        self.assertEqual([page.name for page in module.drawn(FURTHER)], ["share-pack.html"])
        (self.home / "share-pack.html").unlink()
        self.assertEqual(module.drawn(FURTHER), [], "a storyboard that shows only framed pages drew nothing")


if __name__ == "__main__":
    unittest.main()
