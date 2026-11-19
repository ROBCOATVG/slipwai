"""Every restatement of a rule is recorded against the passage that owns it (`scripts/rule-copies.py`).

The rule for when a slice is converged, walked and attacked was changed where it is owned and thirteen other
sentences went on stating the old one; sessions followed those. These tests hold the record to the tree, and
show the two things the record is for: a changed owner lists every copy, and a new copy is named.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/rule-copies.py"
_spec = importlib.util.spec_from_file_location("rule_copies", SCRIPT)
assert _spec is not None and _spec.loader is not None
rule_copies: Any = importlib.util.module_from_spec(_spec)
sys.modules["rule_copies"] = rule_copies
_spec.loader.exec_module(rule_copies)


class TreeTest(unittest.TestCase):
    def test_every_copy_in_the_tree_is_as_recorded(self) -> None:
        self.assertEqual(rule_copies.problems(), [], "python3 scripts/rule-copies.py --check says what to do")

    def test_every_rule_finds_the_passage_that_owns_it(self) -> None:
        for rule in rule_copies.RULES:
            with self.subTest(rule=rule.key):
                self.assertTrue(rule_copies.passage(rule), f"{rule.key} is not in {rule.owner}")

    def test_the_rule_that_was_missed_is_held_in_the_places_it_was_missed(self) -> None:
        """The files whose sentences outlived the rule in 2026-11: each is a recorded copy of `readings`."""
        held = {line.split("  ")[3] for line in rule_copies.recorded() if line.startswith("readings  ")}
        self.assertLessEqual({"assets/guidance/agents.md", "assets/toolkit/commands/sail.md",
                              "assets/toolkit/.specify/extensions.yml", "docs/guide/first-feature.md",
                              "assets/profiles/event-modelling/.specify/presets/event-modelling/templates/"
                              "tasks-template.md"}, held)


class RecordTest(unittest.TestCase):
    """A small tree of its own: one owner, one copy."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "assets").mkdir()
        (self.root / "tests/fixtures").mkdir(parents=True)
        self.owner = self.root / "assets/ladder.md"
        self.owner.write_text("The rung. START a slice is walked twice END and more.\n", encoding="utf-8")
        self.copy = self.root / "assets/brief.md"
        self.copy.write_text("Remember: a slice is walked twice\nat most.\n", encoding="utf-8")
        rule = rule_copies.Rule("walks", "assets/ladder.md", "START", "END", r"walked twice")
        for name, value in (("ROOT", self.root), ("RECORD", self.root / "tests/fixtures/rule-copies.txt"),
                            ("RULES", (rule,)), ("SCANNED", ("assets",))):
            patched = mock.patch.object(rule_copies, name, value)
            patched.start()
            self.addCleanup(patched.stop)
        rule_copies.reread(["walks"], "a start")

    def test_a_tree_that_has_not_moved_has_nothing_to_say(self) -> None:
        self.assertEqual(rule_copies.problems(), [])

    def test_a_changed_owner_lists_every_file_that_restates_the_rule(self) -> None:
        self.owner.write_text("The rung. START a slice is walked twice, or three times END.\n", encoding="utf-8")
        found = "\n".join(rule_copies.problems())
        self.assertIn("the passage that owns this rule changed", found)
        self.assertIn("assets/brief.md:1: Remember: a slice is walked twice", found)
        self.assertIn("--reread walks", found)

    def test_reading_them_again_with_a_reason_settles_it(self) -> None:
        self.owner.write_text("The rung. START a slice is walked twice, or three times END.\n", encoding="utf-8")
        rule_copies.reread(["walks"], "three where critical; the brief still holds")
        self.assertEqual(rule_copies.problems(), [])
        self.assertIn("# reread: ", rule_copies.RECORD.read_text(encoding="utf-8"))
        self.assertIn("a start", rule_copies.RECORD.read_text(encoding="utf-8"), "earlier reasons are kept")

    def test_a_new_copy_is_named_wherever_its_phrase_wraps(self) -> None:
        (self.root / "assets/template.md").write_text("A slice is walked\ntwice here too.\n", encoding="utf-8")
        found = "\n".join(rule_copies.problems())
        self.assertIn("assets/template.md mentions this rule 1 time(s), and 0 are recorded", found)

    def test_an_owner_that_moved_is_said_and_not_read_as_a_change(self) -> None:
        self.owner.write_text("The rung was rewritten.\n", encoding="utf-8")
        self.assertIn("its owning passage is no longer in assets/ladder.md", rule_copies.problems()[0])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
