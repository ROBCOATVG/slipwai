"""The prune script a project runs, on the one question nothing else asks it: what it leaves behind.

`scripts/backing-services.py` strips the regions of features a project did not keep. A file whose every
region was dropped has nothing left, and writing it back that way leaves a zero-byte file in the tree for
ever — invisible in a diff, carried through every replay, and renamed along with everything else. One of
them crossed two factory versions and a rename before anybody noticed it had been empty the whole time.

`tests/test_services.py` holds the same rule over a whole generated project, where the languages are
installed. This holds it over the one file, everywhere.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import ROOT

SOURCE = ROOT / "assets/backing-services/prune.py"
_spec = importlib.util.spec_from_file_location("backing_services_prune", SOURCE)
assert _spec is not None and _spec.loader is not None
prune_script = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = prune_script
_spec.loader.exec_module(prune_script)


class EmptyFileTest(unittest.TestCase):
    """What a dropped region leaves at the path that held it."""

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        # A language's rows are written into this script by the keel when a project is generated, so the
        # tracked copy carries none and would refuse any service. One row, with nothing of its own marked:
        # what is under test is a file the *repository* owns, which every language's project has.
        self.addCleanup(prune_script.ROWS.pop, "python", None)
        prune_script.ROWS["python"] = {"marked_files": (), "owned_files": {}, "manifest": None,
                                       "package_edits": {}, "dependencies": {}}
        (self.root / "project.json").write_text(json.dumps({
            "name": "demo",
            "deployables": {"service": {"kind": "service", "path": "apps/service", "language": "python"}},
        }), encoding="utf-8")
        self.marked = self.root / "infra/service/cognito_external.tf"
        self.marked.parent.mkdir(parents=True)

    def prune(self, keep: set[str]) -> None:
        prune_script.prune(self.root, keep, log=lambda *_: None)

    def test_a_file_that_was_only_a_dropped_region_is_removed_not_emptied(self) -> None:
        self.marked.write_text("# backing-service:users-keycloak:begin\n"
                               'resource "x" "y" {}\n'
                               "# backing-service:users-keycloak:end\n", encoding="utf-8")
        self.prune(set())
        self.assertFalse(self.marked.exists(), "the prune left a file with nothing in it")

    def test_a_file_with_anything_else_in_it_stays(self) -> None:
        """Only the region goes: the rest of the file is somebody's, whoever wrote it."""
        self.marked.write_text("# a line that is nobody's region\n"
                               "# backing-service:users-keycloak:begin\n"
                               'resource "x" "y" {}\n'
                               "# backing-service:users-keycloak:end\n", encoding="utf-8")
        self.prune(set())
        self.assertTrue(self.marked.is_file())
        self.assertNotIn("resource", self.marked.read_text(encoding="utf-8"))

    def test_a_region_that_was_kept_keeps_its_file(self) -> None:
        self.marked.write_text("# backing-service:users-keycloak:begin\n"
                               'resource "x" "y" {}\n'
                               "# backing-service:users-keycloak:end\n", encoding="utf-8")
        self.prune({"users-keycloak"})
        self.assertIn("resource", self.marked.read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
