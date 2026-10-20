"""The release machinery: what the fragments imply, and what refuses to be released.

A release is four things that have to agree — the number in `VERSION`, the entry at the top of
`CHANGELOG.md`, the tag, and the fragments being gone. Doing them by hand means doing three of them and
finding out about the fourth from somebody's bug report.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import ROOT
from slipwai.changelog import GUIDE, LEVELS, Fragment, fragments, implied, level

SCRIPT = ROOT / "scripts/tag-release.py"


class FragmentTest(unittest.TestCase):
    def test_this_repository_s_own_fragments_each_claim_a_level(self) -> None:
        for path, claim, _body in fragments(ROOT):
            with self.subTest(path=path.name):
                self.assertIn(claim, LEVELS)

    def test_and_each_says_something_under_it(self) -> None:
        for path, _claim, body in fragments(ROOT):
            with self.subTest(path=path.name):
                self.assertTrue(body.strip(), path.name)

    def test_the_guide_is_not_read_as_one(self) -> None:
        self.assertNotIn(GUIDE, [path.name for path, _, _ in fragments(ROOT)])

    def test_the_level_is_the_highest_claimed_and_not_the_last(self) -> None:
        """A release carrying a fix and a new option is a MINOR, not both."""
        found: list[Fragment] = [(Path("a.md"), "PATCH", "x"), (Path("b.md"), "MINOR", "y"),
                                 (Path("c.md"), "PATCH", "z")]
        self.assertEqual(level(found), "MINOR")

    def test_the_number_is_derived_from_the_last_release_and_the_level(self) -> None:
        found: list[Fragment] = [(Path("a.md"), "MINOR", "x")]
        self.assertEqual(implied("1.14.2", found), "1.15.0")


    def test_after_a_candidate_the_number_is_the_candidate_s_until_a_claim_outgrows_it(self) -> None:
        """2.0.0rc1 did not spend 2.0.0: a fix after it is still on its way to 2.0.0, not to 2.0.1."""
        fix: list[Fragment] = [(Path("a.md"), "PATCH", "x")]
        self.assertEqual(implied("2.0.0rc1", fix, "1.5.1"), "2.0.0")
        self.assertEqual(implied("1.6.0rc1", [(Path("b.md"), "MAJOR", "y")], "1.5.1"), "2.0.0",
                         "a claim bigger than the candidate's own bump moves past it")
        self.assertEqual(implied("2.0.0rc1", fix), "2.0.0", "with no release before it, the candidate's number")


class GateTest(unittest.TestCase):
    """`make check-release` runs in `make verify`, so it has to pass on this tree, whatever state it is in."""

    def run_it(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *argv], capture_output=True, text=True)

    def test_the_gate_passes_on_this_repository(self) -> None:
        done = self.run_it("--check")
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_dry_run_writes_nothing(self) -> None:
        before = (ROOT / "VERSION").read_text(encoding="utf-8")
        self.run_it("--dry-run")
        self.assertEqual((ROOT / "VERSION").read_text(encoding="utf-8"), before)

    def test_the_changelog_this_release_carries_is_in_the_wheel(self) -> None:
        """`slipwai upgrade` prints the entries crossed, and an installed keel has no checkout to read."""
        said = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('"CHANGELOG.md" = "slipwai/_bundle/CHANGELOG.md"', said)
        self.assertIn('"changelog.d" = "slipwai/_bundle/changelog.d"', said)

    def test_and_in_the_executable(self) -> None:
        self.assertIn("CHANGELOG.md", (ROOT / "slipwai.spec").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
