"""The one refusal shape, held as one table instead of nine files of wording.

The experiment needed `test_refusals_verbs.py`, `test_refusals_loader.py`, `test_refusals_name_the_fix.py`
and six more, because nothing but a test could tell whether a hand-written refusal had remembered to name
the fix. The type remembers now, so what is left to hold is the type: every rendering is one line, every
rendering that has a fix ends with it, and every fault found is said rather than only the first.
"""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr

import checkout_packages  # noqa: F401

from slipwai.errors import Fault, GenerationError, Refusal, blame, failure, one_line, refuse, said

# Each row is what a refusal is built from and the one line it must say.
RENDERINGS: tuple[tuple[str, tuple[Fault, ...], str], ...] = (
    (
        "one fault ends with its command",
        (Fault("package go is not installed", "slipwai install go"),),
        "package go is not installed. Run: slipwai install go",
    ),
    (
        "faults that share a fix name it once, at the end",
        (Fault("package go is not installed", "slipwai install java go"),
         Fault("package java is not installed", "slipwai install java go")),
        "package go is not installed; package java is not installed. Run: slipwai install java go",
    ),
    (
        "faults with different fixes each carry their own",
        (Fault("package go is not installed", "slipwai install go"),
         Fault("import-surface.txt lists slipwai.registryy", "python3 scripts/check-structure.py")),
        "package go is not installed. Run: slipwai install go; "
        "import-surface.txt lists slipwai.registryy. Run: python3 scripts/check-structure.py",
    ),
    (
        "a fault no command fixes says so in its own words",
        (Fault("two packages both declare family java; one of them has to go"),),
        "two packages both declare family java; one of them has to go",
    ),
    (
        "a newline in a name is written out rather than breaking the line",
        (Fault("backend bad\nname is declared twice", "slipwai show bad\nname"),),
        r"backend bad\nname is declared twice. Run: slipwai show bad\nname",
    ),
)


class RenderingTest(unittest.TestCase):
    def test_each_rendering_is_what_the_table_says(self) -> None:
        for why, faults, expected in RENDERINGS:
            with self.subTest(why):
                self.assertEqual(str(Refusal(*faults)), expected)

    def test_no_rendering_is_more_than_one_line(self) -> None:
        """A log parser and a reader both depend on this, and a package's name is not the keel's to trust."""
        for why, faults, _ in RENDERINGS:
            with self.subTest(why):
                self.assertEqual(len(str(Refusal(*faults)).splitlines()), 1)

    def test_a_refusal_whose_faults_all_share_a_fix_ends_with_it(self) -> None:
        for why, faults, line in RENDERINGS:
            fixes = {fault.fix for fault in faults}
            if len(fixes) == 1 and (fix := faults[0].fix) is not None:
                with self.subTest(why):
                    self.assertTrue(line.endswith(one_line(fix)), line)

    def test_a_bare_string_is_a_fault_with_no_fix(self) -> None:
        """So a caller with nothing to suggest is not made to write `Fault(..., None)`."""
        self.assertEqual(str(Refusal("the disk is full")), "the disk is full")

    def test_every_fault_is_said_rather_than_only_the_first(self) -> None:
        """A reader who fixes one and is handed the next has paid for a round trip the keel could save."""
        line = str(Refusal(*(Fault(f"fault {n}") for n in range(5))))
        for n in range(5):
            self.assertIn(f"fault {n}", line)

    def test_a_refusal_with_no_faults_says_so_rather_than_saying_nothing(self) -> None:
        self.assertEqual(str(Refusal()), "refused, with no fault given")

    def test_a_refusal_is_a_generation_error(self) -> None:
        """So a verb catches one kind of thing, not two."""
        self.assertIsInstance(Refusal(Fault("wrong")), GenerationError)


class ReportingTest(unittest.TestCase):
    def test_refuse_writes_one_line_to_stderr_and_exits_two(self) -> None:
        err = io.StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stderr(err):
            refuse("slipwai install", Refusal(Fault("package go is not installed", "slipwai search go")))
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(
            err.getvalue().strip(),
            "slipwai install: error: package go is not installed. Run: slipwai search go",
        )

    def test_refuse_says_no_usage_block(self) -> None:
        """A refusal about the machine or the project is not about the command line, and a usage block says
        it was. argparse's own errors keep theirs; these are not those."""
        err = io.StringIO()
        with self.assertRaises(SystemExit), redirect_stderr(err):
            refuse("slipwai generate", Fault("the directory exists", "rm -rf demo"))
        self.assertNotIn("usage:", err.getvalue())

    def test_refuse_holds_the_shape_even_for_a_caller_that_built_its_own_string(self) -> None:
        err = io.StringIO()
        with self.assertRaises(SystemExit), redirect_stderr(err):
            refuse("slipwai install", "a two\nline message")
        self.assertEqual(len(err.getvalue().strip().splitlines()), 1)


class BlameTest(unittest.TestCase):
    def test_an_exception_a_package_raised_is_named_by_type_and_text(self) -> None:
        self.assertEqual(failure(ValueError("no")), "ValueError: no")

    def test_an_exception_whose_text_cannot_be_made_is_named_by_type_alone(self) -> None:
        class Unprintable(RuntimeError):
            def __str__(self) -> str:
                raise RuntimeError("not even this")

        self.assertIsNone(said(Unprintable()))
        self.assertEqual(failure(Unprintable()), "Unprintable")

    def test_the_user_s_interrupt_is_never_blamed_on_a_package(self) -> None:
        with self.assertRaises(KeyboardInterrupt):
            blame(KeyboardInterrupt())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
