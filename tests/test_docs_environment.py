"""Generated guide fixtures use their own git branch, independent of the outer CI job."""
from __future__ import annotations

import os
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

HARNESS = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/test-docs.py"))


class DocumentationEnvironmentTest(unittest.TestCase):
    def test_outer_ci_branch_metadata_cannot_override_the_fixture_branch(self) -> None:
        outer = {"GITHUB_HEAD_REF": "codex/docs-gate-repair", "CI_COMMIT_REF_NAME": "outer-merge-request",
                 "CI": "true"}
        with patch.dict(os.environ, outer, clear=True):
            fixture = HARNESS["keel_env"]()
            self.assertNotIn("GITHUB_HEAD_REF", fixture)
            self.assertNotIn("CI_COMMIT_REF_NAME", fixture)
            self.assertEqual(fixture["CI"], "true")
            self.assertEqual(os.environ["GITHUB_HEAD_REF"], outer["GITHUB_HEAD_REF"])
            self.assertEqual(os.environ["CI_COMMIT_REF_NAME"], outer["CI_COMMIT_REF_NAME"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
