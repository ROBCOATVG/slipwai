"""A snapshot's installed base is the actual stable release below it, never its future release."""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.errors import GenerationError
from slipwai.migration_legacy import selected


class SelectionTest(unittest.TestCase):
    def test_an_exact_release_stays_exact(self) -> None:
        self.assertEqual(selected("1.4.0", ["1.5.1"]), "1.4.0")

    def test_a_snapshot_chooses_the_newest_stable_release_below_it(self) -> None:
        self.assertEqual(selected("1.5.2.dev4", ["1.4.0", "1.5.0", "1.5.1", "1.5.2", "1.6.0.dev1"]), "1.5.1")

    def test_numeric_version_order_does_not_sort_lexically(self) -> None:
        self.assertEqual(selected("1.11.0.dev2", ["1.9.0", "1.10.0", "1.11.0"]), "1.10.0")

    def test_no_earlier_release_refuses_with_the_installed_interpreter_remedy(self) -> None:
        with self.assertRaisesRegex(GenerationError, "SLIPWAI_LEGACY_PYTHON"):
            selected("1.0.0.dev1", ["1.0.0"])

    def test_an_unreadable_or_nonlegacy_version_is_not_guessed(self) -> None:
        for value in ("unknown", "2.0.0", "1.2.0rc1"):
            with self.subTest(version=value), self.assertRaises(GenerationError):
                selected(value, ["1.1.0"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
