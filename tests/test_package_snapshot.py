"""Real publisher commands agree on a scaffold's snapshot and its first release.

Shells out to package new/check/version, so this module belongs to Makefile's SLOW list.
A language scaffold intentionally leaves protocol answers TODO; its version check must still pass.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import relaunch
from slipwai.conformance.version_rule import problems

KINDS = {"language": "rust", "extension": "lens", "target": "cumulus"}


class PublisherSnapshotTest(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.area = Path(scratch.name)

    def command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([*relaunch(), "package", *arguments], cwd=self.area,
                              env=os.environ.copy(), capture_output=True, text=True)

    def scaffold(self, kind: str, name: str) -> Path:
        done = self.command("new", name, "--kind", kind, "--into", str(self.area))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return self.area / name

    def check(self, kind: str, root: Path) -> None:
        done = self.command("check", str(root))
        printed = done.stdout + done.stderr
        if kind == "language":
            self.assertEqual(done.returncode, 1, printed)
            self.assertRegex(printed, r"version\s+ok")
            self.assertRegex(printed, r"protocol\s+FAILED")
        else:
            self.assertEqual(done.returncode, 0, printed)
        self.assertEqual(problems(root), [])

    def test_fresh_scaffolds_open_the_same_conforming_first_snapshot(self) -> None:
        for kind, name in KINDS.items():
            with self.subTest(kind=kind):
                root = self.scaffold(kind, name)
                self.assertEqual((root / "VERSION").read_text(encoding="utf-8"), "1.0.0.dev0\n")
                self.check(kind, root)

    def test_default_cut_releases_the_snapshot_base_and_passes_the_version_rule(self) -> None:
        for kind, name in KINDS.items():
            with self.subTest(kind=kind):
                root = self.scaffold(kind, name)
                (root / "VERSION").write_text("1.0.0.dev7\n", encoding="utf-8")
                done = self.command("version", str(root))
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertEqual((root / "VERSION").read_text(encoding="utf-8"), "1.0.0\n")
                changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
                self.assertIn("## 1.0.0\n", changelog)
                self.assertNotIn("## 1.0.0.dev", changelog)
                self.assertEqual([p.name for p in (root / "changelog.d").iterdir()], ["README.md"])
                self.check(kind, root)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
