"""What the keel answers before it can do anything: which keel this is.

The version is read from the `VERSION` file rather than repeated in code, and where that file sits depends
on how slipwai is being run — a checkout, an installed wheel, or a frozen executable. Only the checkout
case can be gated from here, so what this file holds is the part that is the same in all three: the string
the command prints is the string the file holds, and `--version` is a clean exit rather than an error.
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest

from slipwai.assets import ROOT, VERSION
from slipwai.cli import main


class VersionTest(unittest.TestCase):
    def test_the_version_is_the_file_rather_than_a_copy_of_it(self) -> None:
        """A number repeated in two places is a number that will disagree with itself at a release."""
        self.assertEqual(VERSION, (ROOT / "VERSION").read_text(encoding="utf-8").strip())

    def test_the_root_of_a_checkout_is_the_repository_root(self) -> None:
        """`src/slipwai/assets.py` is two directories below the root; an installed wheel reads `_bundle`."""
        self.assertTrue((ROOT / "pyproject.toml").is_file())

    def test_version_prints_the_command_and_the_version_and_exits_clean(self) -> None:
        """A tool asked what it is answers on stdout and exits 0, so a script can read it. It names
        itself as well as its number, which is argparse's convention and what the packages' CI reads."""
        out = io.StringIO()
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(out):
            main_with(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), f"slipwai {VERSION}")

    def test_no_arguments_says_which_verbs_there_are(self) -> None:
        """And names exactly the verbs this copy has, so the list cannot promise one that is absent —
        which it did, until `generate` arrived and the hardcoded line was still version 1's. It is
        built from VERBS now, which is also what argparse checks, so the two cannot disagree."""
        from slipwai.cli import VERBS

        err = io.StringIO()
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(err):
            main_with([])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("a verb is required: " + ", ".join(VERBS), err.getvalue())

    def test_brief_alone_says_that_check_is_its_verb(self) -> None:
        err = io.StringIO()
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(err):
            main_with(["brief"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("check", err.getvalue())

    def test_a_verb_this_copy_has_not_got_is_refused_rather_than_half_run(self) -> None:
        err = io.StringIO()
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(err):
            main_with(["teleport"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice", err.getvalue())


def main_with(arguments: list[str]) -> None:
    """`main` reads `sys.argv`; this runs it against a given argument list and puts `sys.argv` back."""
    argv = sys.argv
    sys.argv = ["slipwai", *arguments]
    try:
        main()
    finally:
        sys.argv = argv


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
