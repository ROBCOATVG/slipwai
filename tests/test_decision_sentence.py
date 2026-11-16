"""A decision entry says what was decided in one plain sentence, and the gate asks it only of new entries.

The entries were written by agents for agents, and a product owner could not tell from one what had been
decided. So the shape gained `**In short:**`, written by whoever decides, and `check-decisions` holds every
entry written since the rule to it. A project migrating across the rule has dozens of entries without one;
`migrate` writes the instant it brought the rule in, once, and the gate forgives what came before it.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT
from slipwai.decision_entry import SENTENCE, parse
from slipwai.migration_sentence import date_sentence_rule
from slipwai.project.cruise_record import DECISION_ENTRY, SENTENCE_FROM


def entry(number: int, when: str, sentence: str | None = None) -> str:
    said = f"- **In short:** {sentence}\n" if sentence is not None else ""
    return (f"## D{number} — Does a pasted link join a club?\n"
            f"- **Stage:** example map · **Slice:** CL2 · **When:** {when} · **Stream:** clubs\n"
            "- **Question:** FR-010 gives each club a code and a link.\n"
            "- **Options:** (a) **code only (recommended)**; (b) accept the link\n"
            f"- **Decision:** (a).\n{said}"
            "- **Why:** nobody has a link yet. · **Read against:** the specification (FR-010)\n"
            "- **Decided by:** host (stage recommendation)\n"
            "- **Confidence:** high · **Would reverse if:** organisers hand out links first.\n"
            "- **Written to:** decisions.md\n"
            "- **Status:** awaiting human confirmation\n\n")


def gate():
    spec = importlib.util.spec_from_file_location("check_decisions_sentence",
                                                  TOOLKIT_ROOT / "scripts/check-decisions.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


class SentenceTest(unittest.TestCase):
    def test_the_entry_shape_asks_for_the_sentence_after_the_decision(self) -> None:
        lines = DECISION_ENTRY.splitlines()
        decision = next(n for n, line in enumerate(lines) if line.startswith("- **Decision:**"))
        self.assertTrue(lines[decision + 1].startswith("- **In short:**"))
        self.assertIn("no requirement, decision or event ids", DECISION_ENTRY)

    def test_the_sentence_is_parsed_with_the_rest_of_the_entry(self) -> None:
        found = parse(entry(45, "2026-11-20T10:00:00Z", "A pasted invite link is refused until a page shows it."))
        self.assertEqual(found["D45"][SENTENCE], "A pasted invite link is refused until a page shows it.")

    def test_an_entry_without_one_parses_as_it_did(self) -> None:
        self.assertNotIn(SENTENCE, parse(entry(3, "2026-11-12T12:56:03Z"))["D3"])


class GateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "specs/f").mkdir(parents=True)
        (self.root / "decisions.md").write_text("x\n", encoding="utf-8")
        self.module = gate()
        self.module.ROOT = self.root

    def check(self, *entries: str, since: str | None = None, begun: tuple[str, ...] = ()) -> list[str]:
        path = self.root / "specs/f/decisions.md"
        path.write_text("# Decisions\n\n" + "".join(entries), encoding="utf-8")
        if since:
            (self.root / ".specify").mkdir(exist_ok=True)
            (self.root / SENTENCE_FROM).write_text(json.dumps({"from": since, "in_flight": list(begun)}),
                                                   encoding="utf-8")
        return self.module.check_decisions(path, self.module.sentence_from())

    def test_a_migrated_project_of_old_entries_passes(self) -> None:
        old = [entry(n, f"2026-11-12T12:{n:02d}:00Z") for n in range(1, 40)]
        self.assertEqual(self.check(*old, since="2026-11-16T09:00:00Z"), [])

    def test_a_new_entry_without_one_fails_beside_old_ones_that_pass(self) -> None:
        found = self.check(entry(1, "2026-11-12T12:00:00Z"), entry(2, "2026-11-17T08:00:00Z"),
                           since="2026-11-16T09:00:00Z")
        self.assertEqual(len(found), 1, found)
        self.assertIn("D2 has no **In short:**", found[0])
        self.assertIn(f"after the instant in {SENTENCE_FROM}", found[0], "a person who hits it is told why")

    def test_a_slice_in_flight_when_the_rule_came_in_is_not_asked(self) -> None:
        self.assertEqual(self.check(entry(2, "2026-11-17T08:00:00Z"), since="2026-11-16T09:00:00Z",
                                    begun=("CL2",)), [])
        self.assertEqual(len(self.check(entry(2, "2026-11-17T08:00:00Z"), since="2026-11-16T09:00:00Z",
                                        begun=("CL1",))), 1)

    def test_a_date_with_no_time_on_the_rules_day_is_held_and_one_before_is_not(self) -> None:
        self.assertEqual(len(self.check(entry(2, "2026-11-16"), since="2026-11-16T09:00:00Z")), 1)
        self.assertEqual(self.check(entry(2, "2026-11-15"), since="2026-11-16T09:00:00Z"), [])

    def test_a_new_entry_with_one_passes(self) -> None:
        self.assertEqual(self.check(entry(2, "2026-11-17T08:00:00Z", "A pasted link is refused for now."),
                                    since="2026-11-16T09:00:00Z"), [])

    def test_a_project_made_under_the_rule_holds_every_entry(self) -> None:
        found = self.check(entry(1, "2026-01-01T00:00:00Z"))
        self.assertEqual(len(found), 1, found)
        self.assertIn(f"no {SENTENCE_FROM}", found[0])

    def test_an_old_entry_with_an_impossible_second_is_read_to_the_minute_and_passes(self) -> None:
        """game-club-manager's D13 was written at `13:10:60Z`."""
        self.assertEqual(self.check(entry(13, "2026-11-12T13:10:60Z"), since="2026-11-16T09:00:00Z"), [])

    def test_a_when_that_cannot_be_read_is_reported_as_that_and_not_as_a_missing_sentence(self) -> None:
        for said in ("later", "2026-11-17T25:00:00Z", "16 Nov 2026"):
            with self.subTest(when=said):
                found = self.check(entry(2, said), since="2026-11-16T09:00:00Z")
                self.assertEqual(len(found), 1, found)
                self.assertIn("is not an instant this can read", found[0])

    def test_a_sentence_that_leans_on_an_id_or_a_file_is_refused(self) -> None:
        for leaned in ("Joins by code only, as D-CLB-07 says.", "FR-010 is met by the code alone.",
                       "SC-3 holds.", "Example GN2-1 is what happens.", "Written in specs/f/examples.md.",
                       "The `JoinWithCode` check refuses it."):
            with self.subTest(sentence=leaned):
                found = self.check(entry(2, "2026-11-17T08:00:00Z", leaned))
                self.assertEqual(len(found), 1, found)
                self.assertIn("without requirement, decision or example ids", found[0])

    def test_plain_words_that_look_like_ids_or_files_are_accepted(self) -> None:
        """This project's own test bed is a game club, where a D20 is a die."""
        for word in ("D20", "D6", "DOTA2", "SC2", "R2 bucket", "R5", "DDR4", "US-1", "Node.js", "next.js",
                     "Pay.go", "shelf.json", "and/or"):
            with self.subTest(word=word):
                self.assertEqual(self.check(entry(2, "2026-11-17T08:00:00Z", f"A member may bring a {word}.")), [])

    def test_a_placeholder_is_no_sentence(self) -> None:
        self.assertEqual(len(self.check(entry(2, "2026-11-17T08:00:00Z", "<one sentence>"))), 1)

    def test_an_unreadable_instant_file_is_said_rather_than_forgiving_everything(self) -> None:
        (self.root / ".specify").mkdir()
        (self.root / SENTENCE_FROM).write_text("{}", encoding="utf-8")
        with self.assertRaises(OSError):
            self.module.sentence_from()


class MigrateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def test_a_project_with_decisions_gets_the_instant_once_and_staged(self) -> None:
        (self.root / "specs/f").mkdir(parents=True)
        (self.root / "specs/f/decisions.md").write_text(entry(1, "2026-11-12T12:00:00Z"), encoding="utf-8")
        self.assertTrue(date_sentence_rule(self.root, datetime(2026, 11, 16, 9, tzinfo=UTC)))
        held = json.loads((self.root / SENTENCE_FROM).read_text(encoding="utf-8"))
        self.assertEqual(held["from"], "2026-11-16T09:00:00Z")
        staged = subprocess.run(["git", "-C", str(self.root), "diff", "--cached", "--name-only"],
                                capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(staged, [SENTENCE_FROM])
        self.assertFalse(date_sentence_rule(self.root, datetime(2027, 1, 1, tzinfo=UTC)))
        self.assertEqual(json.loads((self.root / SENTENCE_FROM).read_text(encoding="utf-8"))["from"],
                         "2026-11-16T09:00:00Z")

    def git(self, *words: str) -> None:
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t", *words],
                       capture_output=True, check=True)

    def test_decisions_only_in_a_berth_count_and_its_slice_is_named_in_flight(self) -> None:
        (self.root / "README.md").write_text("x\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "start")
        berth = self.root.parent / f"{self.root.name}-CL2"
        self.git("worktree", "add", "-q", "-b", "slice/CL2", str(berth))
        (berth / "specs/f").mkdir(parents=True)
        (berth / "specs/f/decisions.md").write_text(entry(1, "2026-11-12T12:00:00Z"), encoding="utf-8")
        self.assertTrue(date_sentence_rule(self.root, datetime(2026, 11, 16, 9, tzinfo=UTC)))
        self.assertEqual(json.loads((self.root / SENTENCE_FROM).read_text(encoding="utf-8"))["in_flight"], ["CL2"])

    def test_a_project_with_no_decision_gets_nothing_and_is_held_from_its_first(self) -> None:
        self.assertFalse(date_sentence_rule(self.root))
        self.assertFalse((self.root / SENTENCE_FROM).exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
