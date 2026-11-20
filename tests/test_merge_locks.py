"""Two slices that each wrote the workspace's lock have not disagreed: the lock is written again.

A real rebase in a real repository, with a stand-in for the package manager on the path: it writes the lock
from the manifests the way the real one does, which is all the harbourmaster needs of it.
"""
from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from harbourmaster_fixture import MergeFixture

#: `uv lock`, as far as this test goes: the lock is every service's dependencies, sorted.
UV = "#!/bin/sh\ncat apps/*/deps.txt | sort > uv.lock\n"


@unittest.skipIf(os.name == "nt", "the stand-in package manager is a shell script")
class LockConflictTest(MergeFixture):
    def setUp(self) -> None:
        super().setUp()
        tools = Path(tempfile.mkdtemp())
        (tools / "uv").write_text(UV, encoding="utf-8")
        (tools / "uv").chmod((tools / "uv").stat().st_mode | stat.S_IXUSR)
        patched = mock.patch.dict(os.environ, {"PATH": f"{tools}{os.pathsep}{os.environ.get('PATH', '')}"})
        patched.start()
        self.addCleanup(patched.stop)

    def write(self, path: str, body: str) -> None:
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(body, encoding="utf-8")

    def diverge(self, slice_lock: str) -> None:
        self.git("checkout", "--quiet", "main")
        self.write("apps/a/deps.txt", "x\n")
        self.write("uv.lock", "x\n")
        self.commit("one dependency")
        self.git("checkout", "--quiet", "-b", "slice/ORD-01", "main")
        self.write("apps/a/deps.txt", "x\ny\n")
        self.write("uv.lock", slice_lock)
        self.commit("ORD-01 needs y")
        self.git("checkout", "--quiet", "main")
        self.write("apps/b/deps.txt", "z\n")
        self.write("uv.lock", "x\nz\n")
        self.commit("another slice needed z meanwhile")
        self.git("checkout", "--quiet", "-b", "parked-elsewhere", "slice/ORD-01")

    def test_the_lock_is_written_again_from_both_slices_manifests_and_the_merge_is_granted(self) -> None:
        self.diverge("x\ny\n")
        self.ask("ORD-01")
        done = self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "granted", f"{answer.fields}\n{done.stderr}")
        self.assertEqual(self.git("show", "main:uv.lock").stdout, "x\ny\nz\n")
        self.assertEqual(self.git("show", "main:apps/a/deps.txt").stdout, "x\ny\n")

    def test_a_lock_nothing_here_can_write_again_is_still_a_conflict_for_the_berth(self) -> None:
        self.git("checkout", "--quiet", "main")
        self.write("Cargo.lock", "x\n")
        self.commit("a lock of another kind")
        self.git("checkout", "--quiet", "-b", "slice/ORD-01", "main")
        self.write("Cargo.lock", "x\ny\n")
        self.commit("ORD-01 needs y")
        self.git("checkout", "--quiet", "main")
        self.write("Cargo.lock", "x\nz\n")
        self.commit("another slice needed z meanwhile")
        self.git("checkout", "--quiet", "-b", "parked-elsewhere", "slice/ORD-01")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused")
        self.assertIn("Cargo.lock", str(answer.fields["why"]))


if __name__ == "__main__":
    unittest.main()
