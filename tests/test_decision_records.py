"""`check-decisions` holds each decision where it is now written: a file of its own.

Seven slices of one fairway appended to one `decisions.md`, and their merges were unions of two endings that
dropped the lines two entries share — a record's `- **Status:** standing`, on manda six times, each refused by
this gate at the next merge. So each decision is its own record, `specs/<feature>/decisions/<id>.md`, and the
log is rendered from them. The gate reads the records, holds each to one decision named for its id, and keeps
one numbering across the records and whatever the log still holds that no record does.
"""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from test_decision_sentence import entry, gate


class RecordsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.feature = self.root / "specs/f"
        (self.feature / "decisions").mkdir(parents=True)
        (self.feature / "decisions.md").write_text("x\n", encoding="utf-8")
        self.module = gate()
        self.module.ROOT = self.root
        self.module.SPECS = self.root / "specs"
        (self.root / "decisions.md").write_text("what each entry's Written to names\n", encoding="utf-8")

    def record(self, name: str, *entries: str) -> None:
        (self.feature / f"decisions/{name}.md").write_text("".join(entries), encoding="utf-8")

    def found(self) -> list[str]:
        return self.module.feature_decisions(self.feature)

    def test_a_record_in_the_shape_passes(self) -> None:
        self.record("D1", entry(1, "2026-11-20T10:00:00Z", "A pasted link is refused."))
        self.assertEqual(self.found(), [])

    def test_a_record_missing_its_status_is_named_at_the_record(self) -> None:
        """The defect the records exist for, said where it is to be fixed."""
        held = entry(7, "2026-11-20T10:00:00Z", "A pasted link is refused.")
        self.record("D7", held.replace("- **Status:** awaiting human confirmation\n", ""))
        self.assertEqual(self.found(), ["specs/f/decisions/D7.md:1: D7 is missing **Status:**"])

    def test_a_record_named_for_another_decision_is_refused(self) -> None:
        self.record("D2", entry(3, "2026-11-20T10:00:00Z", "A pasted link is refused."))
        self.assertIn("specs/f/decisions/D2.md: holds D3; a record is named for the decision it holds — move it to "
                      "specs/f/decisions/D3.md", self.found())

    def test_a_record_holding_two_decisions_is_refused(self) -> None:
        self.record("D4", entry(4, "2026-11-20T10:00:00Z", "One."), entry(5, "2026-11-20T10:00:00Z", "Two."))
        self.assertIn("specs/f/decisions/D4.md: holds 2 entries; a record is one decision, in a file named for "
                      "its id", self.found())

    def test_the_log_s_copy_of_a_record_is_the_record_and_one_numbering_spans_both(self) -> None:
        self.record("D6", entry(6, "2026-11-20T10:00:00Z", "One."))
        log = self.feature / "decisions.md"
        log.write_text(entry(8, "2026-11-20T10:00:00Z", "Older.") + entry(6, "2026-11-20T10:00:00Z", "One."),
                       encoding="utf-8")
        self.assertEqual(self.found(), [], "the log's D6 is the record's, rendered")
        log.write_text(log.read_text(encoding="utf-8") + entry(8, "2026-11-20T10:00:00Z", "Again."), encoding="utf-8")
        self.assertEqual(len([one for one in self.found() if "D8 is already the entry at specs/f/decisions.md:1"
                              in one]), 1)

    def test_the_gate_reads_a_feature_that_has_records_and_counts_them(self) -> None:
        self.record("D1", entry(1, "2026-11-20T10:00:00Z", "A pasted link is refused."))
        (self.feature / "decisions.md").unlink()
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            self.assertEqual(self.module.main(), 0)
        self.assertIn("1 decision(s) in 1 feature(s)", said.getvalue())


class AdversaryRecordsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.feature = self.root / "specs/f"
        (self.feature / "slices").mkdir(parents=True)
        (self.feature / "slices/README.md").write_text("| Slice |\n|---|\n| S01 |\n| S02 |\n", encoding="utf-8")
        self.module = gate()
        self.module.ROOT = self.root
        self.module.SPECS = self.root / "specs"

    def test_a_slice_s_row_in_its_own_record_is_its_row(self) -> None:
        (self.feature / "adversary-log").mkdir()
        (self.feature / "adversary-log/S01.md").write_text("## S01 · abc · 2026-11-20 · trigger record\n",
                                                          encoding="utf-8")
        (self.feature / "adversary-log.md").write_text("## S02 · def · 2026-11-20 · trigger record\n",
                                                       encoding="utf-8")
        self.assertEqual(self.module.check_adversary_rows(), [])

    def test_the_baseline_writes_records_where_the_log_is_rendered_from_them(self) -> None:
        (self.feature / "adversary-log").mkdir()
        (self.feature / "adversary-log/S01.md").write_text("## S01 · abc · 2026-11-20 · trigger record\n",
                                                          encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.module.baseline(), 0)
        self.assertIn(f"## S02 · {self.module.PREDATES} · ",
                      (self.feature / "adversary-log/S02.md").read_text(encoding="utf-8"))
        self.assertFalse((self.feature / "adversary-log.md").exists())


if __name__ == "__main__":
    unittest.main()
