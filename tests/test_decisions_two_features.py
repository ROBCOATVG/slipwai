"""Two features' decisions, each listed: the first feature's D3 does not hide a later feature's D3.

Decisions are numbered across the project now, but features that each counted from one have a number in
common. The log keyed its entries by the number alone, so only the first feature's was ever on a card; and
the fold of the fairways' own files rendered the first feature's `decisions.md` and no other.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT
from slipwai.decision_log import decisions, mark

FIRST, FURTHER, THIRD = "001-first", "002-further", "003-third"


def book(title: str, piece: str) -> str:
    return (f"# Decisions\n\n## D3 — {title}\n- **Stage:** plan · **Slice:** {piece} · "
            f"**When:** 2026-11-20T09:00:00Z · **Stream:** intake\n- **Decision:** the answer for {piece}\n")


class LogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        for feature, title, piece in ((FIRST, "The first feature's third", "S1"),
                                      (FURTHER, "A later feature's third", "S45"),
                                      (THIRD, "And a third feature's", "S60")):
            (self.root / "specs" / feature).mkdir(parents=True)
            (self.root / "specs" / feature / "decisions.md").write_text(book(title, piece), encoding="utf-8")
        (self.root / "specs" / FIRST / "chart.yaml").write_text("slices: {}\n", encoding="utf-8")

    def test_each_feature_s_entry_of_one_number_is_listed(self) -> None:
        found = {one.key: (one.number, one.title, one.feature) for one in decisions(self.root)}
        self.assertEqual(found, {"md:D3": ("D3", "The first feature's third", FIRST),
                                 f"md:{FURTHER}/D3": ("D3", "A later feature's third", FURTHER),
                                 f"md:{THIRD}/D3": ("D3", "And a third feature's", THIRD)})

    def test_reading_one_is_not_reading_the_others(self) -> None:
        mark(self.root, [f"md:{FURTHER}/D3"])
        self.assertEqual({one.key for one in decisions(self.root) if one.read}, {f"md:{FURTHER}/D3"})
        mark(self.root, ["md:D3"])
        self.assertEqual({one.key for one in decisions(self.root) if not one.read}, {f"md:{THIRD}/D3"})

    def test_a_deck_line_is_shown_as_the_entry_written_for_its_slice(self) -> None:
        deck = logs.deck_path(self.root, FIRST, "intake")
        deck.parent.mkdir(parents=True)
        deck.write_text(logs.entry("decision", fairway="intake", slice="S45", id="S45-Q1", what="D3 (a): so",
                                   decided_by="sail-decide-skipper").line(), encoding="utf-8")
        found = decisions(self.root)
        on_deck = next(one for one in found if one.key.startswith("deck:"))
        self.assertEqual((on_deck.title, on_deck.feature), ("A later feature's third", FURTHER))
        self.assertEqual(sorted(one.key for one in found if one.key.startswith("md:")),
                         [f"md:{THIRD}/D3", "md:D3"], "and the other two are still listed")


class FoldTest(unittest.TestCase):
    """`render-fairways.py` in a project with two features that each have fairway files."""

    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(TOOLKIT_ROOT / "scripts/render-fairways.py", self.tree / "scripts/render-fairways.py")
        (self.tree / "project.json").write_text("{}", encoding="utf-8")
        for feature in (FIRST, FURTHER, THIRD):
            (self.tree / "specs" / feature / "slices").mkdir(parents=True)
        spec = importlib.util.spec_from_file_location("render_two", self.tree / "scripts/render-fairways.py")
        assert spec is not None and spec.loader is not None
        self.module = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(self.module)

    def source(self, where: str, ident: str) -> None:
        path = self.tree / "fairways" / where / "decisions.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"## {ident} — which\n- **When:** 2026-11-20T09:00:00Z\n- **Decision:** that\n",
                        encoding="utf-8")

    def folded(self, feature: str) -> str:
        path = self.tree / "specs" / feature / "decisions.md"
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def test_each_feature_with_fairway_files_is_folded_from_its_own(self) -> None:
        self.source("intake", "D1")
        self.source(f"intake/{FIRST}", "D2")
        self.source(f"intake/{FURTHER}", "D3")
        self.assertEqual(self.module.main([]), 0)
        self.assertIn("## D1 —", self.folded(FIRST))
        self.assertIn("## D2 —", self.folded(FIRST))
        self.assertNotIn("## D3 —", self.folded(FIRST))
        self.assertIn("## D3 —", self.folded(FURTHER))
        self.assertNotIn("## D1 —", self.folded(FURTHER), "a file naming no feature is the first feature's")
        self.assertEqual(self.folded(THIRD), "", "a feature with no fairway files has nothing rendered over it")
        self.assertEqual(self.module.main(["--check"]), 0)

    def test_a_further_feature_s_rendered_file_edited_by_hand_is_refused(self) -> None:
        self.source(f"intake/{FURTHER}", "D3")
        self.module.main([])
        (self.tree / "specs" / FURTHER / "decisions.md").write_text("edited\n", encoding="utf-8")
        self.assertEqual(self.module.main(["--check"]), 1)


if __name__ == "__main__":
    unittest.main()
