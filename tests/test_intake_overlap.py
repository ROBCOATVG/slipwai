"""Requirement ids a handed-over document names that the project's specifications already hold: a match on the
ids, said as one, and silence where there is nothing to match."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.intake_overlap import held_ids, overlap, warning

SPEC = """# Feature Specification: Billing

### Functional Requirements

- **FR-001**: System MUST take a card payment.
- **FR-002**: System MUST send a receipt, as UTF-8, citing ISO-8601 dates.
* FR-010: an unbolded one.

| Id | Criterion |
|---|---|
| SC-001 | Nine in ten members pay in under a minute |

### NFR-3 Availability
"""


class OverlapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.documents = self.root / "held"
        self.documents.mkdir()

    def spec(self, feature: str, text: str = SPEC) -> None:
        (self.root / "specs" / feature).mkdir(parents=True)
        (self.root / "specs" / feature / "spec.md").write_text(text, encoding="utf-8")

    def document(self, name: str, text: str) -> Path:
        path = self.documents / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_an_id_is_held_where_a_specification_lists_it_and_not_where_it_only_mentions_one(self) -> None:
        self.spec("001-billing")
        self.assertEqual(sorted(held_ids(self.root)), ["FR-001", "FR-002", "FR-010", "NFR-3", "SC-001"],
                         "UTF-8 and ISO-8601 are words in a sentence, not ids the specification holds")

    def test_the_ids_a_document_shares_are_listed_with_the_document_and_the_specification(self) -> None:
        self.spec("001-billing")
        self.spec("002-export", "- **FR-001**: System MUST export.\n")
        found = overlap(self.root, [self.document("b.md", "FR-002 again, and FR-001. Not FR-0011 or XFR-001."),
                                    self.document("a.md", "See fr-001, FR-099 and SC-001, in UTF-8.")])
        self.assertEqual(found, [
            {"id": "FR-001", "documents": ["b.md"], "specifications": ["specs/001-billing", "specs/002-export"]},
            {"id": "FR-002", "documents": ["b.md"], "specifications": ["specs/001-billing"]},
            {"id": "SC-001", "documents": ["a.md"], "specifications": ["specs/001-billing"]}])
        said = warning(found)
        self.assertIn("FR-001 (b.md; in specs/001-billing, specs/002-export)", said)
        self.assertIn("a match on the ids only", said)
        self.assertIn("You can still capture", said)

    def test_no_ids_no_specification_or_no_document_is_no_warning_and_no_error(self) -> None:
        self.assertEqual(overlap(self.root, [self.document("a.md", "FR-001")]), [], "no specification")
        self.spec("001-billing")
        self.assertEqual(overlap(self.root, [self.document("b.md", "Members pay by card.")]), [], "no ids")
        self.assertEqual(overlap(self.root, []), [])
        self.assertEqual(overlap(self.root, [self.documents / "gone.md"]), [], "a document that went away")
        self.spec("003-empty", "")
        (self.root / "specs/004-odd").mkdir()
        (self.root / "specs/004-odd/spec.md").write_bytes(b"\xff\xfe- **FR-077**: \x00")
        self.assertEqual(warning([]), "")

    def test_a_document_is_matched_as_text_and_reaches_no_path_or_pattern(self) -> None:
        self.spec("001-billing")
        hostile = self.document("c.md", "../../specs/001-billing/spec.md (FR-001|.*) $(rm -rf) **FR-002**")
        self.assertEqual([one["id"] for one in overlap(self.root, [hostile])], ["FR-001", "FR-002"])


if __name__ == "__main__":
    unittest.main()
