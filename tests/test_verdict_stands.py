"""A verdict stands for the pages it was given on, and a drawing says what it left to discuss.

`record_verdict` writes, above each surface's block in `mock-states.md`, the page and a digest of what it said.
A page that says something else since — changed in a conversation, by hand, renamed or gone — is a verdict
nobody gave, and is said as withdrawn; one block per page, however many pages share a title. And the drawing
stage, run headless by `make surfaces`, refuses a drawing that does not declare its open counts.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai.drawn import fingerprints, record_verdict, withdraw, withdrawn

ROOT = Path(__file__).resolve().parents[1]


class StandsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.home = self.root / "specs/001-boats/mockups"
        self.home.mkdir(parents=True)
        self.page("basket.html", "Basket", "Empty")
        self.page("total.html", "Total", "Shown")
        (self.home / "storyboard.html").write_text("<title>Storyboard</title>", encoding="utf-8")
        record_verdict(self.root, "001-boats", "approved")

    def page(self, name: str, title: str, state: str) -> None:
        (self.home / name).write_text(f'<title>{title}</title><article class="state"><h2>{state}</h2></article>',
                                      encoding="utf-8")

    def verdicts(self) -> str:
        return (self.home / "mock-states.md").read_text(encoding="utf-8")

    def test_a_page_changed_by_hand_renamed_or_gone_no_longer_carries_its_verdict(self) -> None:
        self.assertEqual(withdrawn(self.root, "001-boats"), [])
        self.page("basket.html", "Cart", "Empty")  # renamed, outside any conversation
        (self.home / "total.html").unlink()
        self.assertEqual(withdrawn(self.root, "001-boats"), ["Basket — Empty", "Total — Shown"])

    def test_a_turn_withdraws_each_changed_page_once_and_a_storyboard_change_withdraws_nothing(self) -> None:
        before = fingerprints(self.root)
        (self.home / "storyboard.html").write_text("<title>Storyboard</title><p>the flow, changed</p>",
                                                   encoding="utf-8")
        self.assertEqual(withdraw(self.root, before), [], "the storyboard is the flow, not a surface")
        self.page("basket.html", "Basket", "Full")
        self.assertEqual(withdraw(self.root, before), ["Basket — Empty"])
        self.assertEqual(withdraw(self.root, fingerprints(self.root)), [], "a second turn finds nothing more")
        self.assertEqual(self.verdicts().count("<!-- withdrawn: Basket"), 1)
        self.assertIn("- Shown — approved", self.verdicts(), "the page nobody changed keeps its verdict")

    def test_two_pages_with_one_title_are_two_verdicts(self) -> None:
        self.page("total.html", "Basket", "Shown")
        record_verdict(self.root, "001-boats", "approved")
        before = fingerprints(self.root)
        self.page("total.html", "Basket", "Changed")
        self.assertEqual(withdraw(self.root, before), ["Basket — Shown"])
        self.assertIn("- Empty — approved", self.verdicts(), "the other page called Basket keeps its verdict")

    def test_a_verdict_from_before_pages_were_recorded_is_matched_by_a_name_only_one_page_has(self) -> None:
        (self.home / "mock-states.md").write_text("## Surface: Basket\n- Empty — approved\n\n## Surface: Total\n"
                                                  "- Shown — approved\n", encoding="utf-8")
        before = fingerprints(self.root)
        self.page("basket.html", "Basket", "Full")
        self.assertEqual(withdraw(self.root, before), ["Basket — Empty"])
        self.assertIn("## Surface: Total\n- Shown — approved", self.verdicts())


class HeadlessDrawingTest(unittest.TestCase):
    def test_make_surfaces_refuses_a_drawing_that_does_not_declare_what_is_left(self) -> None:
        tree = Path(tempfile.mkdtemp())
        sys.path.insert(0, str(ROOT / "assets/toolkit/scripts/agents"))
        self.addCleanup(sys.path.remove, str(ROOT / "assets/toolkit/scripts/agents"))
        spec = importlib.util.spec_from_file_location("surfaces_declared",
                                                      ROOT / "assets/toolkit/scripts/agents/surfaces.py")
        assert spec is not None and spec.loader is not None
        module: Any = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.ROOT, module.SPECS = tree, tree / "specs"
        module.PID, module.HARBOUR = tree / ".slipwai/surfaces.pid", tree / "harbour.json"
        (tree / "specs/001-orders").mkdir(parents=True)
        (tree / "specs/001-orders/spec.md").write_text("# Orders\n", encoding="utf-8")
        home = tree / "specs/001-orders/mockups"
        for research, wanted in (("## Questions\n- None\n", 1), ("Blockers open: 0\nQuestions open: 0\n", 0)):
            draws = ("import pathlib, sys; p = pathlib.Path(sys.argv[1]); p.mkdir(parents=True, exist_ok=True); "
                     "(p / 'basket.html').write_text('<title>Basket</title>'); "
                     f"(p / 'research.md').write_text({research!r})")
            command = f"{shlex.quote(sys.executable)} -c {shlex.quote(draws)} {shlex.quote(str(home))} {{prompt}}"
            err = io.StringIO()
            with mock.patch.object(module.harness, "choose", return_value=({}, "a stand-in")), \
                    mock.patch.object(module.harness, "template", return_value=(command, "a test")), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                self.assertEqual(module.main(["001-orders"]), wanted, err.getvalue())
            if wanted:
                self.assertIn("does not declare `Blockers open: N` and `Questions open: N`", err.getvalue())


if __name__ == "__main__":
    unittest.main()
