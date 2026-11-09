"""The fence: a file a generated project runs on macOS or Linux changes only with a reason.

What is proved: today's tree generates the files the record holds, byte for byte; a file that changed is
named with what it was and what it is now; and a record whose digests were edited by hand, rather than
moved with `--why`, no longer matches its last reason. Generates four projects, so it is in the
Makefile's `SLOW` list.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/fence.py"
_spec = importlib.util.spec_from_file_location("fence_script", SCRIPT)
assert _spec is not None and _spec.loader is not None
fence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fence)


@unittest.skipIf(os.name == "nt", "the fence holds what macOS and Linux run")
class FenceTest(unittest.TestCase):
    now: list[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.now = fence.digests()

    def setUp(self) -> None:
        self.record = Path(tempfile.mkdtemp()) / "run-files.sha256"
        patched = mock.patch.object(fence, "RECORD", self.record)
        patched.start()
        self.addCleanup(patched.stop)

    def test_the_tree_is_as_recorded(self) -> None:
        with mock.patch.object(fence, "RECORD", Path(SCRIPT).parents[1] / "tests/fixtures/run-files.sha256"):
            self.assertEqual(fence.problems(self.now), [])

    def test_every_project_has_its_makefile_init_verify_and_hook(self) -> None:
        for profile, keeps, serves in fence.MATRIX:
            paths = {line.split("  ")[2] for line in self.now if line.split("  ")[1] == f"{profile}-{keeps}-{serves}"}
            self.assertLessEqual({"Makefile", "init", "scripts/verify", ".githooks/pre-push"}, paths)

    def test_a_changed_file_is_named_and_asks_for_its_reason(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            fence.write(self.now, "a start")
        moved = [line.replace(line[:64], "0" * 64) if line.endswith("  Makefile") else line for line in self.now]
        found = fence.problems(moved)
        self.assertTrue(any(line.startswith("now   " + "0" * 64) for line in found))
        self.assertIn("--why", found[-1])

    def test_a_digest_edited_by_hand_breaks_the_reason(self) -> None:
        fence.write(self.now, "a start")
        text = self.record.read_text(encoding="utf-8")
        first = self.now[0]
        self.record.write_text(text.replace(first, "f" * 64 + first[64:]), encoding="utf-8")
        found = fence.problems(self.now)
        self.assertIn("edited by hand", found[0])

    def test_a_move_with_its_reason_is_recorded(self) -> None:
        fence.write(self.now, "a start")
        moved = sorted(["0" * 64 + "  standard-memory-none  scripts/new", *self.now])
        fence.write(moved, "a new script, run nowhere yet")
        self.assertEqual(fence.problems(moved), [])
        self.assertEqual(len(fence.read()[1]), 2)


if __name__ == "__main__":
    unittest.main()
