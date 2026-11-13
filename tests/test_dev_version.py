"""A dev build of main is numbered by its commits past the last release, so no two builds share a version.

Every build of main published `VERSION`'s `2.1.0.dev0`. A project migrated by one could not be told from one
migrated by the next: catch-up read "both are 2.1.0" and the app's release check saw them as the same.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai.versions import key

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/dev-version.py"


def load() -> Any:
    spec = importlib.util.spec_from_file_location("dev_version", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NumberedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.script = load()

    def answers(self, tag: str, count: int) -> Any:
        said = {"describe": tag, "rev-list": str(count)}
        return mock.patch.object(self.script, "git", side_effect=lambda *argv: said[argv[0]])

    def test_a_snapshot_is_numbered_by_the_commits_past_the_last_release(self) -> None:
        with self.answers("v2.0.1", 52):
            self.assertEqual(self.script.numbered("2.1.0.dev0"), "2.1.0.dev52")

    def test_each_build_of_main_sorts_above_the_last_and_below_the_release(self) -> None:
        with self.answers("v2.0.1", 52):
            earlier = self.script.numbered("2.1.0.dev0")
        with self.answers("v2.0.1", 53):
            later = self.script.numbered("2.1.0.dev0")
        self.assertLess(key(earlier), key(later))
        self.assertLess(key(later), key("2.1.0"))

    def test_a_release_is_left_as_it_is_and_asks_git_nothing(self) -> None:
        with mock.patch.object(self.script, "git") as asked:
            self.assertEqual(self.script.numbered("2.1.0"), "2.1.0")
        asked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
