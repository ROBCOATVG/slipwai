"""The migration gate's choice of which release to generate from.

On a snapshot of `main` that is the newest tag. On the tagged Release commit it cannot be, or the gate
migrates a project to the factory that just made it, reports `nothing to migrate`, and fails for want of
catch-up notes — which is what the `v1.13.0` run did. The functions are imported from the script so the
choice is tested without generating a project.
"""
from __future__ import annotations

import importlib.util
import unittest

from slipwai.assets import ROOT

SPEC = importlib.util.spec_from_file_location("test_migration", ROOT / "scripts/test-migration.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourceRevisionTest(unittest.TestCase):
    TAGS = ["v1.13.0", "v1.12.1", "v1.12.0"]
    NEWEST = "daae9f0"

    def test_a_snapshot_generates_from_the_newest_release(self) -> None:
        self.assertEqual(MODULE.source_revision(self.TAGS, "c491db8", self.NEWEST), "v1.13.0")

    def test_the_tagged_commit_generates_from_the_release_before_it(self) -> None:
        self.assertEqual(MODULE.source_revision(self.TAGS, self.NEWEST, self.NEWEST), "v1.12.1")

    def test_the_first_release_has_nothing_older_to_migrate_from(self) -> None:
        self.assertIsNone(MODULE.source_revision(["v1.0.0"], "abc", "abc"))

    def test_no_tags_is_a_mistake_not_a_skip(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.source_revision([], "abc", "abc")
        with self.assertRaises(ValueError):
            MODULE.generate_from([], "abc", "abc", "1.0.1.dev0")

    def test_the_first_public_snapshot_has_nothing_older_to_migrate_from(self) -> None:
        self.assertIsNone(MODULE.generate_from([], "abc", "", "1.0.0.dev0"))


if __name__ == "__main__":
    unittest.main()
