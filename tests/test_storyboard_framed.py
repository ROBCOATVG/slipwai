"""How much a further feature's storyboard frames: what it touches and its neighbours, stated where it is drawn.

The rule did not change. What changed is that it is exact where the drawing agent reads it — what a neighbour
is, and that a neighbour's neighbour is not framed — and that the part of it a name can settle is noted. No
gate counts frames: it neither asks for more than touched plus neighbours nor can tell that there are fewer,
because which screen is one step from another is recorded nowhere a script can read. These tests hold both.
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

ROOT = Path(__file__).resolve().parents[1]
TOOLKIT = ROOT / "assets/toolkit"
ORIGINAL = '<iframe src="../../../apps/web/screens/deal-console-deals.html" data-surface="built"></iframe>'


def existing() -> Any:
    spec = importlib.util.spec_from_file_location("existing_framed", TOOLKIT / "scripts/agents/existing.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # Python 3.11's dataclasses look a module up by name
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


class RuleTest(unittest.TestCase):
    def test_the_rule_is_exact_where_the_drawing_agent_reads_it(self) -> None:
        page = " ".join((TOOLKIT / "commands/mockups.md").read_text(encoding="utf-8").split())
        skill = " ".join((TOOLKIT / "skills/storyboard/SKILL.md").read_text(encoding="utf-8").split())
        for said in ("what this feature touches, and its neighbours. No more, and no fewer.",
                     "**one step either side** of a touched one in the flow", "One step is **one navigation**",
                     "in the same actor's lane of `docs/event-model/model.yaml`",
                     "**A neighbour's neighbour is not framed.**", "**One frame per framed surface**",
                     "under `## Framed` in `research.md`", "it counts no frames and refuses no storyboard"):
            self.assertIn(said, page)
        for said in ("no more and no fewer", "one step either side of a touched one",
                     "A neighbour's neighbour is not framed", "`## Framed`"):
            self.assertIn(said, skill)


class CheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = crossed(Path(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.module = existing()
        self.home = storyboard(self.root)

    def rewrite(self, old: str, new: str) -> None:
        board = self.home / "storyboard.html"
        text = board.read_text(encoding="utf-8")
        self.assertIn(old, text)
        board.write_text(text.replace(old, new), encoding="utf-8")

    def test_touched_plus_neighbours_is_enough_however_much_the_app_has(self) -> None:
        """Two built frames beside two touched surfaces, in an app of sixty previews: nothing asks for more."""
        for at in range(60):
            write(self.root, f"apps/web/screens/report-{at:02}-shown.html", f"<title>Report {at:02} — shown</title>")
        self.assertEqual(self.module.listing(FURTHER, self.root)["counts"]["built"], 63)
        self.assertEqual(self.module.held(FURTHER, self.root), ([], []))

    def test_a_changed_surface_without_its_original_is_noted_and_not_refused(self) -> None:
        self.rewrite(ORIGINAL, "")
        faults, notes = self.module.held(FURTHER, self.root)
        self.assertEqual(faults, [], "the rule stands as it was: nothing is refused for how much is framed")
        self.assertEqual(len(notes), 1, notes)
        self.assertIn("Deal console is marked `changed` and its original is not framed beside it", notes[0])

    def test_an_original_with_no_picture_is_its_box(self) -> None:
        self.rewrite(ORIGINAL, '<div data-surface="built" data-picture="none" data-frame="DealConsoleScreen">'
                     "DealConsoleScreen — built, no picture</div>")
        self.assertEqual(self.module.held(FURTHER, self.root), ([], []))

    def test_fewer_neighbours_cannot_be_told_and_are_not_guessed_at(self) -> None:
        """Sign in leads to the deal console and is not framed: no file says so, so no script says so."""
        self.rewrite('<iframe data-surface="built" src="../../../apps/web/screens/sign-in.html"></iframe>', "")
        self.assertEqual(self.module.held(FURTHER, self.root), ([], []))


if __name__ == "__main__":
    unittest.main()
