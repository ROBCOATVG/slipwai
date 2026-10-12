"""The adopted repository's pages as assets: that moving them changed no byte anybody receives.

`tests/fixtures/adopted-pages.sha256` is what `project/adopted.py` and `project/sail_adoption.py`
rendered at the commit slice 16.6 was written on top of, and this module is the only reason that file
exists: `docs/adoption.md`, the three marked blocks appended to files the repository owns, the hooks the
adoption adds to `.specify/extensions.yml` and `.specify/cruise.json` all have to come back byte for byte
across the six repositories `tests/adopted_pages.py` names.

Six because these pages branch on more than one thing at once — the forge that runs CI, how a change
reaches production, whether the repository had a `Makefile`, whether it has converged, where the delivery
material sits, what was wrapped — and a record taken at one repository would pass with half the branches
stubbed out to the empty string.

The substitution's two directions are held in `tests/test_generated_prose.py`, over every templated asset
tree there is, which is where the adoption-pages row was added. What is held here is the part that is this
slice's alone: that nothing a repository receives changed.
"""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import adopted_pages
import checkout_packages

RECORD = Path(__file__).resolve().parent / "fixtures/adopted-pages.sha256"


def recorded() -> dict[tuple[str, str], str]:
    """The record, as `(case, path) -> digest`, with its header read as the comment it is."""
    rows = {}
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        digest, case, path = line.split()
        rows[(case, path)] = digest
    return rows


@unittest.skipUnless(checkout_packages.installed("toy"), "needs the toy package: slice 3.8")
class ByteForByteTest(unittest.TestCase):
    """What an adopted repository received before the prose left the modules, and what it receives now."""

    def test_every_page_is_what_it_was_before_the_prose_left_the_modules(self) -> None:
        rows = recorded()
        for case in adopted_pages.CASES:
            rendered = adopted_pages.pages(case)
            for (held, path), digest in sorted(rows.items()):
                if held != case:
                    continue
                with self.subTest(repository=case, file=path):
                    self.assertIn(path, rendered, f"{path} is recorded in {RECORD.name} and no longer rendered")
                    self.assertEqual(hashlib.sha256(rendered[path].encode("utf-8")).hexdigest(), digest,
                                     f"{path} is no longer the text recorded in {RECORD.name} for {case}")

    def test_the_record_covers_every_repository_and_every_page_each_receives(self) -> None:
        """A record that lost a row would pass by not asking about the page that changed."""
        rows = recorded()
        self.assertEqual(sorted({case for case, _path in rows}), sorted(adopted_pages.CASES))
        for case in adopted_pages.CASES:
            with self.subTest(repository=case):
                self.assertEqual(sorted(path for held, path in rows if held == case),
                                 sorted(adopted_pages.pages(case)))

    def test_the_matrix_reaches_both_sides_of_every_branch_the_moved_pages_make(self) -> None:
        """The record is only a gate on the branches it was taken across. A page that renders the same
        text in all six repositories is one whose branch this matrix does not reach, and a section marker
        dropped from it would be recorded as the only thing it ever was."""
        rows = recorded()
        for path in ("docs/adoption.md", ".specify/extensions.yml", "AGENTS.md#delivery",
                     "Makefile#delivery", ".gitignore#delivery"):
            with self.subTest(file=path):
                digests = {digest for (_case, held), digest in rows.items() if held == path}
                self.assertGreater(len(digests), 1, f"{path} is recorded at one text only")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
