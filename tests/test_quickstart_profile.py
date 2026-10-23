"""A profile you typed decides which of a quickstart's answers still apply."""
from __future__ import annotations

import contextlib
import io
import unittest
from types import SimpleNamespace
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import cli_quickstart, quickstart


class ProfileYouChoseTest(unittest.TestCase):
    """A profile you typed decides which of the quickstart's answers still apply. One for an axis your profile
    does not ask is not given, and says so — carrying it over ended the run on a refusal of a question nobody
    was asked, which is what `--quickstart typescript-ui --profile standard` did with its persistence answer."""

    def test_an_axis_your_profile_does_not_ask_is_left_out_and_said(self) -> None:
        one = quickstart.Quickstart("demo", "a demo", axes={"write-model": "events", "persistence": "postgres"})
        args = SimpleNamespace(quickstart="demo", backend=None, language=None, framework=None,
                               profile="standard", target=None, frontend=None)
        named: dict[str, str | None] = {"write-model": None, "persistence": None}
        said = io.StringIO()
        with (mock.patch.object(quickstart, "find", lambda _name: one),
              mock.patch.object(cli_quickstart, "refuse_missing", lambda _one: None),
              contextlib.redirect_stdout(said)):
            cli_quickstart.applied(args, named, ["demo", "--quickstart", "demo", "--profile", "standard"])
        self.assertIsNone(named["write-model"])
        self.assertIn("  write-model   events  (not given: the standard profile does not ask it)",
                      said.getvalue().splitlines())
        self.assertEqual(named["persistence"], "postgres", "a store is a standard project's question too")


if __name__ == "__main__":
    unittest.main()
