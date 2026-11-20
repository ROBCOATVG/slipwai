"""A workspace's lock is the slice's to write, and written again where two slices' locks meet.

One dependency cost a slice a hand-back, a mender run and a stop for a person, because the workspace's lock
sits at the root and the root was the host's. A lock is derived, so nobody has to choose what is in it.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT


def toolkit(name: str) -> Any:
    found = importlib.util.spec_from_file_location(f"toolkit_{Path(name).stem.replace('-', '_')}",
                                                   TOOLKIT_ROOT / "scripts" / name)
    assert found is not None and found.loader is not None
    made = importlib.util.module_from_spec(found)
    found.loader.exec_module(made)
    return made


lockfiles = toolkit("agents/lockfiles.py")


class LockfilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())

    def test_a_lock_is_known_by_its_name_wherever_the_workspace_keeps_it(self) -> None:
        self.assertTrue(lockfiles.is_lock("package-lock.json"))
        self.assertTrue(lockfiles.is_lock("delivery/uv.lock"))
        self.assertFalse(lockfiles.is_lock("package.json"))
        self.assertFalse(lockfiles.is_lock("Cargo.lock"), "not one this knows how to write again")

    def test_the_scope_gate_opens_exactly_the_locks_this_can_write_again(self) -> None:
        text = (TOOLKIT_ROOT / "scripts/check-slice-scope.py").read_text(encoding="utf-8")
        for name in lockfiles.REGENERATED:
            self.assertIn(f'"{name}"', text.split("WORKSPACE_LOCKS = ")[1].split("\n")[0])

    def test_a_lock_is_written_again_by_its_own_tool_in_the_directory_it_is_in(self) -> None:
        writer = [sys.executable, "-c", "open('uv.lock', 'w').write('again')"]
        (self.root / "delivery").mkdir()
        with mock.patch.dict(lockfiles.REGENERATED, {"uv.lock": writer}):
            self.assertEqual(lockfiles.regenerate(self.root, "delivery/uv.lock"), "")
        self.assertEqual((self.root / "delivery/uv.lock").read_text(encoding="utf-8"), "again")

    def test_a_tool_that_is_not_here_or_fails_says_so_and_writes_nothing(self) -> None:
        with mock.patch.dict(lockfiles.REGENERATED, {"uv.lock": ["no-such-tool-on-this-path", "lock"]}):
            self.assertIn("is not on this machine's PATH", lockfiles.regenerate(self.root, "uv.lock"))
        failing = [sys.executable, "-c", "import sys; print('registry down', file=sys.stderr); sys.exit(3)"]
        with mock.patch.dict(lockfiles.REGENERATED, {"uv.lock": failing}):
            self.assertIn("registry down", lockfiles.regenerate(self.root, "uv.lock"))
        self.assertIn("nothing here knows", lockfiles.regenerate(self.root, "Cargo.lock"))


if __name__ == "__main__":
    unittest.main()
