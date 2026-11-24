"""A file's reading is kept until the file changes (`file_memo`)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import file_memo


class MemoTest(unittest.TestCase):
    def test_a_file_is_read_once_until_it_changes(self) -> None:
        path = Path(tempfile.mkdtemp()) / "D1.md"
        path.write_text("one", encoding="utf-8")
        calls: list[str] = []

        def reading(text: str) -> str:
            calls.append(text)
            return text.upper()

        self.assertEqual(file_memo.read(path, reading, "t"), "ONE")
        self.assertEqual(file_memo.read(path, reading, "t"), "ONE")
        self.assertEqual(calls, ["one"], "an unchanged file is not read again")
        path.write_text("two!", encoding="utf-8")
        stamp = path.stat().st_mtime_ns + 1_000_000
        os.utime(path, ns=(stamp, stamp))
        self.assertEqual(file_memo.read(path, reading, "t"), "TWO!")
        self.assertEqual(file_memo.read(path, str.lower, "other"), "two!", "each reading keeps its own")

    def test_a_file_that_cannot_be_read_raises_as_reading_it_would(self) -> None:
        with self.assertRaises(OSError):
            file_memo.read(Path(tempfile.mkdtemp()) / "gone.md", str, "t")


if __name__ == "__main__":
    unittest.main()
