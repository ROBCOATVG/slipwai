"""A decision is read against what the project already does, and the record says which authority answered.

`/cruise`'s skipper protocol named three things a decision could be settled by without asking a delegate:
the standing entries, the specification, the constitution. All three are documents this method owns. A
generated project ten slices in, and an adopted repository on its first day, both hold conventions that
none of them names — how this codebase already publishes, how one handler reaches the next, how a
migration is named — and a decision taken without them is how a codebase ends up with two ways of doing
one thing, each defensible on its own. That is the fourth authority, and 15.15 adds it.

Held here rather than in the gate's own tests because it lives in three places that have to agree: the
procedure that says what to read, the entry shape that reserves somewhere to say it, and
`check-decisions.py`, which is what makes it true rather than advisory. Two of the three agreeing is the
failure this file exists for — a shape with a field nobody fills, or a gate asking for a field the shape
never showed.
"""
from __future__ import annotations

import re
import unittest

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT
from slipwai.layout import AT_ROOT
from slipwai.project.cruise import cruise_command
from slipwai.project.cruise_record import DECISION_ENTRY

GATE = TOOLKIT_ROOT / "scripts/check-decisions.py"


class EntryShapeTest(unittest.TestCase):
    def test_the_entry_reserves_somewhere_to_name_the_authority(self) -> None:
        self.assertIn("**Read against:**", DECISION_ENTRY)

    def test_it_is_inside_why_rather_than_a_field_of_its_own(self) -> None:
        """A tenth bullet would lengthen every entry a project has already written, and the gate holds the
        fields in order — so an existing record would fail on its shape rather than on its content."""
        why = next(line for line in DECISION_ENTRY.splitlines() if line.startswith("- **Why:**"))
        self.assertIn("**Read against:**", why)
        self.assertEqual(9, sum(1 for line in DECISION_ENTRY.splitlines() if line.startswith("- **")))

    def test_the_four_authorities_are_named_where_a_writer_will_read_them(self) -> None:
        for authority in ("this project's own", "the specification", "the constitution", "standing D<m>"):
            with self.subTest(authority=authority):
                self.assertIn(authority, DECISION_ENTRY)

    def test_none_of_them_is_an_answer_too(self) -> None:
        """A decision the method's defaults settled is a true decision; hiding it is what makes the field
        worthless, because then every entry names an authority whether or not one was consulted."""
        self.assertIn("the method's", DECISION_ENTRY)


class ProcedureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = cruise_command(True, [], "none", AT_ROOT)

    def test_the_procedure_sends_the_reader_to_what_the_project_already_does(self) -> None:
        self.assertIn("read **what this project already does**", self.text)

    def test_it_says_where_that_is_written_on_either_kind_of_project(self) -> None:
        """An authority nobody can find is advice. A generated project and an adopted one keep it in
        different places, and the procedure names both."""
        self.assertIn("`docs/architecture.md` and the code itself", self.text)
        self.assertIn("`structure.md` and the survey", self.text)

    def test_the_host_may_settle_a_question_the_projects_own_convention_answers(self) -> None:
        """Otherwise the fourth authority is something to cite and never something to decide by, and every
        such question still costs a delegate."""
        self.assertIn("when this project's own", self.text)
        self.assertIn("convention settles it", self.text)


class GateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = GATE.read_text(encoding="utf-8")

    def test_the_gate_asks_for_it(self) -> None:
        self.assertIn("READ_AGAINST", self.source)
        self.assertIn("`Why` names no **Read against:**", self.source)

    def test_the_gate_still_holds_the_nine_fields_in_order(self) -> None:
        """The clause goes inside `Why`; a tenth entry in `DECISION_FIELDS` would refuse every record a
        project wrote before this change."""
        found = re.search(r"DECISION_FIELDS = \((.*?)\)", self.source, re.S)
        self.assertIsNotNone(found)
        fields = re.findall(r'"([^"]+)"', found.group(1))  # type: ignore[union-attr]
        self.assertEqual(
            ["Stage", "Question", "Options", "Decision", "Why", "Decided by", "Confidence", "Written to", "Status"],
            fields,
        )

    def test_the_gates_own_docstring_tells_a_reader_what_it_now_wants(self) -> None:
        self.assertIn("**Why** carries `Read against:`", self.source)


class AwaitingConfirmationTest(unittest.TestCase):
    """A stop meant for a person, answered with nobody there, stands as a proposal and says so.

    A headless `/launch` once took the chart's context question "as confirmed" and recorded nothing; the
    shape now has a status for what that decision really is, and one for a person having read it.
    """

    def setUp(self) -> None:
        source = GATE.read_text(encoding="utf-8")
        found = re.search(r'STATUS = re\.compile\((.*?)\)\n', source, re.S)
        self.assertIsNotNone(found)
        self.status = re.compile("".join(re.findall(r'r"([^"]*)"', found.group(1))))  # type: ignore[union-attr]

    def test_the_gate_accepts_both_new_statuses_and_still_the_old_ones(self) -> None:
        for said in ("standing", "awaiting human confirmation", "confirmed by human 2026-10-19", "overridden by D3",
                     "overridden by human 2026-10-19"):
            self.assertRegex(said, self.status)
        self.assertNotRegex("pending", self.status)

    def test_the_entry_shape_shows_them(self) -> None:
        self.assertIn("awaiting human confirmation | confirmed by human <date>", DECISION_ENTRY)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
