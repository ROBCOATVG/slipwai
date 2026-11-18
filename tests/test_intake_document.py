"""A document posted to the Next features tab is a stranger's: its name, its size and its text are checked
before a byte of it is written, and it is written in one folder and nowhere else."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.intake_document import LIMIT, MOST, held, named, staged, text_of

#: Names that climb, hide, or stand in for a file intake reads as an answer.
HOSTILE = ("../../evil.md", "..\\evil.md", "/etc/passwd", "a/b.md", "a\\b.md", ".hidden", "..", ".", "",
           "confirmed", "Confirmed", "brief.md", "BRIEF.MD", "specified.json", "conversation.md", "CON.txt", "nul",
           "evil.md\x00", "evil\n.md", "notes.md.", "x" * 200 + ".md", "spéc.md", "a..b.md")


class NameTest(unittest.TestCase):
    def test_a_plain_file_name_is_kept_as_it_was_given(self) -> None:
        for name in ("billing.md", "Billing requirements (v2).txt", "gap-analysis_2026.md", "notes"):
            self.assertEqual(named(f"  {name} "), name)

    def test_a_name_that_is_a_path_or_one_of_intakes_own_is_refused(self) -> None:
        for name in HOSTILE:
            with self.subTest(name=name), self.assertRaises(ValueError):
                named(name)


class TextTest(unittest.TestCase):
    def test_text_up_to_the_limit_is_text(self) -> None:
        self.assertEqual(text_of("# Billing\n\n\tA tab, a form feed\f and a return\r\n"),
                         "# Billing\n\n\tA tab, a form feed\f and a return\r\n")
        self.assertEqual(len(text_of("a" * LIMIT)), LIMIT)

    def test_more_than_the_limit_is_refused_by_its_bytes_and_says_the_limit(self) -> None:
        with self.assertRaises(ValueError) as refused:
            text_of("a" * (LIMIT + 1))
        self.assertIn("256 KB", str(refused.exception))
        with self.assertRaises(ValueError):
            text_of("é" * (LIMIT // 2 + 1))  # two bytes each: under the limit in characters, over in bytes

    def test_what_does_not_read_as_text_is_refused(self) -> None:
        for binary in ("\x89PNG\r\n\x1a\n\x00\x00", "ok until\x00here", "a file read as text: ��"):
            with self.subTest(binary=binary), self.assertRaises(ValueError) as refused:
                text_of(binary)
            self.assertIn("does not read as text", str(refused.exception))


class StagedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.folder = self.home / "run" / "documents"

    def test_a_document_is_written_under_its_name_with_its_text_unchanged(self) -> None:
        path = staged(self.folder, "billing.md", "# Billing\r\n\nMembers pay.\n")
        self.assertEqual(path, (self.folder / "billing.md").resolve())
        self.assertEqual(path.read_bytes(), b"# Billing\r\n\nMembers pay.\n")
        self.assertEqual([one.name for one in held(self.folder)], ["billing.md"])

    def test_a_hostile_name_writes_nothing_anywhere(self) -> None:
        for name in HOSTILE:
            with self.subTest(name=name), self.assertRaises(ValueError):
                staged(self.folder, name, "# Evil\n")
        self.assertEqual([one for one in self.home.rglob("*") if one.is_file()], [])
        self.assertFalse((self.home.parent / "evil.md").exists())

    def test_an_empty_one_a_second_by_the_same_name_and_one_too_many_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            staged(self.folder, "empty.md", "  \n")
        staged(self.folder, "billing.md", "one\n")
        with self.assertRaises(ValueError) as refused:
            staged(self.folder, "Billing.MD", "two\n")
        self.assertIn("attached already", str(refused.exception))
        self.assertEqual((self.folder / "billing.md").read_text(encoding="utf-8"), "one\n")
        for number in range(MOST - 1):
            staged(self.folder, f"more-{number}.md", "more\n")
        with self.assertRaises(ValueError) as refused:
            staged(self.folder, "last.md", "one too many\n")
        self.assertIn(f"{MOST} documents at most", str(refused.exception))


if __name__ == "__main__":
    unittest.main()
