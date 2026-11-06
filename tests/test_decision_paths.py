"""A path the decision record names is in the project, or it is refused.

recap's LB9 demo log named its walk recordings by an absolute path into a folder Git ignores: `check-decisions`
passed on the machine that walked it, because the folder is there, and failed on every other checkout — CI's was
the first.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT


def load():
    spec = importlib.util.spec_from_file_location("check_decisions_paths", TOOLKIT_ROOT / "scripts/check-decisions.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


class PathTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load()
        self.root = Path(tempfile.mkdtemp())
        self.outside = Path(tempfile.mkdtemp())
        (self.root / "specs/f/slices/LB9/demo").mkdir(parents=True)
        (self.root / "specs/f/slices/LB9/demo/walk.txt").write_text("walked\n", encoding="utf-8")
        (self.outside / "walk.webm").write_text("bytes\n", encoding="utf-8")
        self.module.ROOT = self.root
        self.base = self.root / "specs/f/slices/LB9"

    def found(self, value: str) -> list[str]:
        return self.module.path_findings("demo-log.md:1", "Evidence", value, self.base)

    def test_a_path_in_the_project_passes(self) -> None:
        self.assertEqual(self.found("`demo/walk.txt`"), [])

    def test_an_absolute_path_that_exists_on_this_machine_is_refused(self) -> None:
        said = self.found(f"`{self.outside / 'walk.webm'}`")
        self.assertEqual(len(said), 1, said)
        self.assertIn("outside the project", said[0])

    def test_a_path_that_climbs_out_of_the_project_is_refused(self) -> None:
        said = self.found(f"`../../../../../{self.outside.name}/walk.webm`")
        self.assertEqual(len(said), 1, said)
        self.assertIn("outside the project", said[0])


if __name__ == "__main__":
    unittest.main()
