"""A capability's record under `specs/<feature>/capabilities/` is its own slices' to write.

The harbourmaster holds the merge that makes a capability whole until `gates.md` says `Cleared:` on that
slice's branch, and `check-slice-scope` refused the file to every slice. So a slice cleared its gates, could
not commit the record, handed it back, and was refused until the mender had landed it on trunk.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from test_slice_scope import CHART, GATE, gate_module


class CapabilityRecordTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(GATE, self.tree / "scripts/check-slice-scope.py")
        (self.tree / "specs/ordering").mkdir(parents=True)
        (self.tree / "project.json").write_text('{"deployables": {}}', encoding="utf-8")
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.tree, capture_output=True, check=True)
        self.module = gate_module(self.tree)

    def scope(self, chart: str = CHART):
        (self.tree / "specs/ordering/chart.yaml").write_text(textwrap.dedent(chart).lstrip(), encoding="utf-8")
        return self.module.Scope("ORD-01", "main")

    def test_a_capability_s_record_is_its_own_slices_to_write_where_it_is_read(self) -> None:
        """manda: the harbourmaster refused a capability's last merge until `gates.md` said `Cleared:` on
        the slice's branch, and this refused the file to every slice — sixteen refusals in a day and a half."""
        scope = self.scope()
        for name in ("gates.md", "demo-log.md"):
            self.assertIsNone(scope.violation(f"specs/ordering/capabilities/place-an-order/{name}", "A"))
        another = scope.violation("specs/ordering/capabilities/bill-an-order/gates.md", "A")
        assert another is not None
        self.assertIn("place-an-order", another)
        self.assertIsNotNone(scope.violation("specs/ordering/capabilities/README.md", "A"))

    def test_a_further_feature_s_capability_is_recorded_under_that_feature(self) -> None:
        """S50 cleared its gates and wrote the record under the chart's feature; it is read under its own."""
        chart = CHART.replace("capability: place-an-order,", "capability: place-an-order, feature: 002-more,")
        scope = self.scope(chart)
        self.assertIsNone(scope.violation("specs/002-more/capabilities/place-an-order/gates.md", "A"))
        wrong = scope.violation("specs/ordering/capabilities/place-an-order/gates.md", "A")
        assert wrong is not None
        self.assertIn("specs/002-more/capabilities/place-an-order/", wrong)


class CodeMovedTest(CapabilityRecordTest):
    """Another slice's `code` list follows a file this branch moved; nothing else of its block may change."""

    def test_only_a_code_list_that_follows_the_tree(self) -> None:
        moved = self.module.code_moved
        (self.tree / "new.ts").write_text("", encoding="utf-8")
        (self.tree / "kept.ts").write_text("", encoding="utf-8")
        was = {"id": "S1", "status": "implemented", "code": ["kept.ts", "old.ts"]}
        self.assertTrue(moved(was, {**was, "code": ["kept.ts", "new.ts"]}))
        self.assertTrue(moved(was, {**was, "code": ["kept.ts"]}), "deleted, and so only removed")
        self.assertFalse(moved(was, {**was, "code": ["old.ts", "new.ts"]}), "kept.ts is still in the tree")
        self.assertFalse(moved(was, {**was, "code": ["kept.ts", "nowhere.ts"]}), "what it adds must be there")
        self.assertFalse(moved(was, {**was, "status": "modelled", "code": ["kept.ts", "new.ts"]}))
        self.assertFalse(moved(was, {**was, "code": ["old.ts", "kept.ts"]}), "a reordering moved nothing")


if __name__ == "__main__":
    unittest.main()
