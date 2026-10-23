"""The conformance suite and the matrix, run against the package this keel holds.

A package proves itself against the keel it is built for, and the keel proves that the suite doing the
proving works. Those are different jobs and this is the second: `python -m slipwai.conformance` is run
against `packages/toy` here, on every commit, so that a package's own CI is running something known to
work rather than something nobody has tried.

The toy is inert by design — one backend, no transport, nothing to serve — which is what makes it a
fixture rather than a language. So conformance runs against it and the matrix cannot: the matrix
generates variants and runs each one's native gate, and there is nothing to run. That refusal is held
here too, because "the matrix declined to plan anything" and "the matrix planned nothing" look the same
from outside and only one of them is correct.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

import checkout_packages

from slipwai.catalog import CATALOG
from slipwai.conformance import run
from slipwai.matrix import rows

REPOSITORY = Path(__file__).resolve().parents[1]
TOY = "toy"


def entry_point(module: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    """One of the keel's `python -m` entry points, run as a package's own CI runs it."""
    return subprocess.run(
        [sys.executable, "-m", module, str(checkout_packages.PACKAGES), *arguments],
        cwd=REPOSITORY, capture_output=True, text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(REPOSITORY / "src")},
    )


class EntryPointTest(unittest.TestCase):
    def test_the_conformance_suite_runs_against_the_toy_and_reports_every_check(self) -> None:
        done = entry_point("slipwai.conformance", TOY)
        printed = done.stdout + done.stderr
        for check in ("protocol", "markers", "targets", "prune rows", "version"):
            with self.subTest(check=check):
                self.assertIn(check, printed)

    def test_every_check_passes_for_the_toy(self) -> None:
        """Including the two generation probes, which were red until `generate` came back in 4.1: the
        suite was reporting that the keel could not generate, because it could not."""
        done = entry_point("slipwai.conformance", TOY)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("toy passed", done.stdout)

    def test_a_package_the_directory_has_not_got_is_refused_rather_than_passing_empty(self) -> None:
        done = entry_point("slipwai.conformance", "a-package-nobody-wrote")
        self.assertNotEqual(done.returncode, 0)

    def test_the_matrix_plans_the_toys_variants(self) -> None:
        """Once the toy brought a transport of its own there were variants to generate, so the matrix
        plans them — the ones it can actually be generated with.

        This asserted the store and production rows too, which is the bug it was written over: the toy
        implements neither store, no identity and no cloud target, and generation refuses each of those
        with `a half-ported version is deliberately not emitted`. Nothing noticed until the template
        repository ran its own matrix for the first time, because every real language implements all of
        them.
        """
        done = entry_point("slipwai.matrix", TOY, "--list")
        printed = done.stdout + done.stderr
        self.assertEqual(done.returncode, 0, printed)
        for row in ("verify-standard-toy-plain-none", "verify-event-modelling-toy-plain-none"):
            with self.subTest(row=row):
                self.assertIn(row, printed)
        for refused in ("verify-toy-plain-postgres", "verify-toy-plain-sqlite",
                        "verify-production-event-modelling-toy-plain"):
            with self.subTest(refused=refused):
                self.assertNotIn(refused, printed)


class RowsTest(unittest.TestCase):
    def test_a_backend_with_no_transport_has_no_variants_to_generate(self) -> None:
        """A package that serves nothing has no native gate to run, and the matrix says so rather than
        planning an empty run that passes."""
        import copy

        serves_nothing = copy.deepcopy(CATALOG)
        serves_nothing["default"]["http"] = {"toy-plain": "none"}
        with self.assertRaises(ValueError) as raised:
            rows.native_rows(serves_nothing, "toy-plain")
        self.assertIn("no variants to generate", str(raised.exception))
        self.assertIn("slipwai.conformance", str(raised.exception))

    def test_the_toy_does_have_one_now(self) -> None:
        self.assertTrue(rows.native_rows(CATALOG, "toy-plain"))

    def test_the_diagonals_still_cover_every_profile_and_frontend_the_catalogue_has(self) -> None:
        """A profile added to the catalogue and not to the diagonals is a variant nobody generates."""
        rows.covered(CATALOG)


class PlannableTest(unittest.TestCase):
    """A row generation would refuse is never planned.

    The store and identity rows were hard-coded, and every real language implements both stores and
    Keycloak, so nothing noticed. The language template's toy implements none of them — and its first
    matrix run planned four rows whose own refusals say `a half-ported version is deliberately not
    emitted`. A row that cannot generate is not a failing matrix; it is a matrix written down wrong, and
    the two look identical in a CI log.
    """

    def test_a_backend_that_implements_nothing_gets_the_two_rows_that_name_nothing(self) -> None:
        planned = [row.name for row in rows.native_rows(CATALOG, "toy-plain")]
        # No installed language ships a browser app, so the event-modelling diagonal has none either.
        self.assertEqual(planned, ["verify-standard-toy-plain-none",
                                   "verify-event-modelling-toy-plain-none"])

    def test_a_row_naming_an_option_this_backend_has_not_got_is_not_plannable(self) -> None:
        row = rows.Row("x", "event-modelling", "toy-plain", "none", (("persistence", "sqlite"),))
        self.assertFalse(rows.plannable(CATALOG, row))

    def test_a_row_naming_nothing_is_always_plannable(self) -> None:
        self.assertTrue(rows.plannable(CATALOG, rows.Row("x", "standard", "toy-plain", "none")))

    def test_an_option_is_judged_against_the_target_the_row_names(self) -> None:
        """`takes` asks both of `selection.py`'s questions — implemented for this backend, offered under
        this target — because a row refused for the second reason reads exactly like one refused for the
        first."""
        self.assertFalse(rows.takes(CATALOG, "persistence", "sqlite", "toy-plain", "aws"))


class ImageToolTest(unittest.TestCase):
    """A tool the matrix has no binary name for is said and skipped, never a `KeyError`.

    `image_builder`'s `tool` is the package's own word — the language template's inert placeholder calls
    its builder `toy` — and `NEEDS` is the keel's list of what each one it knows is called on a PATH. The
    lookup was a subscript, so the template's first matrix run ended in `KeyError: 'toy'` rather than in a
    sentence anybody could act on.
    """

    def tool_lookup(self, tool: str) -> str | None:
        from slipwai.matrix.case import MatrixCase
        return MatrixCase.image_tools.get(tool)

    def test_the_tools_the_matrix_knows_are_named(self) -> None:
        from slipwai.matrix import images
        self.assertEqual(set(images.NEEDS), {"pack", "ko", ""})

    def test_a_tool_it_does_not_know_reads_as_absent_rather_than_raising(self) -> None:
        self.assertIsNone(self.tool_lookup("toy"))

    def test_the_case_reads_the_table_without_subscripting_it(self) -> None:
        """Read as source: the lookup runs only inside a real matrix run, which needs Docker and minutes.
        What is held here is that it cannot raise."""
        from pathlib import Path as P
        source = (P(__file__).resolve().parents[1] / "src/slipwai/matrix/case.py").read_text(encoding="utf-8")
        self.assertIn("self.image_tools.get(image.tool)", source)
        self.assertNotIn("self.image_tools[image.tool]", source)


class RunTest(unittest.TestCase):
    """A package is named by its directory name in the package directory, and by nothing else."""

    def test_a_plain_directory_name_is_accepted(self) -> None:
        run.require_package_name("toy")

    def test_a_name_that_is_a_path_is_refused(self) -> None:
        """A path would let a run reach a directory outside the one it was pointed at."""
        for bad in ("", ".", "..", "a/b", "../toy", "a\\b"):
            with self.subTest(name=bad), self.assertRaises(ValueError):
                run.require_package_name(bad)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
