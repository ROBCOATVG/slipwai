"""The two roles that run the loop, as briefs rather than as a Python programme.

Eleven briefs described a delegate *inside* a slice. The captain and the harbourmaster — the two roles
`GLOSSARY.md` defines as running the loop — had none, because they were a script. When the script goes, the
brief is what is left, and a loop a persona drives is what "native to the harness" means.

What these tests hold is the part a brief gets wrong quietly: the vocabulary. A captain that paraphrases the
deck log writes lines the board cannot fold, and a board that is wrong about what happened is worse than no
board, because it is believed.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import plugin
from slipwai.layout import AT_ROOT
from slipwai.logs import DECK_KINDS, HARBOUR, HARBOUR_KINDS
from slipwai.project.agents import agent_files, types
from slipwai.project.briefs import read

CAPTAIN = "drive-captain"
HARBOURMASTER = "harbour-harbourmaster"


class TypesTest(unittest.TestCase):
    """Both are canonical types, so the frontmatter a harness enforces is generated like every other."""

    def names(self) -> list[str]:
        return [agent.name for agent in types()]

    def test_the_captain_is_a_type(self) -> None:
        self.assertIn(CAPTAIN, self.names())

    def test_the_harbourmaster_is_a_type(self) -> None:
        self.assertIn(HARBOURMASTER, self.names())

    def test_neither_takes_a_stages_model(self) -> None:
        """A captain resolves each stage's model inside itself, as `/sail`'s slice delegate does; a
        harbourmaster runs no stage at all. Resolving one here would pick a model for the whole ladder."""
        for name in (CAPTAIN, HARBOURMASTER):
            agent = next(one for one in types() if one.name == name)
            self.assertEqual(agent.stage, "none", name)

    def test_both_are_written_into_a_project_beside_the_eleven(self) -> None:
        files = agent_files(AT_ROOT)
        for name in (CAPTAIN, HARBOURMASTER):
            self.assertIn(f"agents/{name}.md", files)

    def test_both_travel_with_the_plugin(self) -> None:
        """A persona somebody has to copy is a persona most sessions do not have."""
        rendered = plugin.files("standard")
        for name in (CAPTAIN, HARBOURMASTER):
            self.assertIn(f"agents/{name}.md", rendered)


class VocabularyTest(unittest.TestCase):
    """The deck-log vocabulary in the captain's brief is `DECK_KINDS`, not a paraphrase of it."""

    def body(self, name: str) -> str:
        return read(name).body

    def test_the_captain_names_every_deck_kind_it_may_write(self) -> None:
        said = self.body(CAPTAIN)
        for kind in DECK_KINDS:
            self.assertIn(f"`{kind}`", said, kind)

    def test_the_captain_names_the_fields_of_the_lines_it_writes_most(self) -> None:
        """A line short a field is refused by `logs.entry`, which a session finds out at the first write."""
        said = self.body(CAPTAIN)
        for kind in ("claimed", "mark-set", "request", "parked"):
            for field in DECK_KINDS[kind]:
                self.assertIn(field, said, f"{kind}.{field}")

    def test_the_captain_names_no_kind_the_keel_has_not_got(self) -> None:
        """An invented kind is a line the board refuses and a captain that thinks it reported something."""
        said = self.body(CAPTAIN)
        for kind in HARBOUR_KINDS:
            if kind not in DECK_KINDS:
                self.assertNotIn(f"writes `{kind}`", said, kind)


class WhatItMayNotDoTest(unittest.TestCase):
    """The thing the eleven do well: each brief says what it may not do, not only what it is for."""

    def body(self, name: str) -> str:
        return read(name).body

    def test_the_captain_holds_no_credential_and_asks_with_a_request_line(self) -> None:
        said = self.body(CAPTAIN)
        self.assertIn("no credential", said)
        self.assertIn("`request`", said)

    def test_the_captain_never_merges_to_trunk(self) -> None:
        """Rule 10 of the plan: people hold the merge to trunk."""
        said = self.body(CAPTAIN).lower()
        self.assertIn("never merges to trunk", said)

    def test_the_captain_does_not_write_the_harbour_log(self) -> None:
        said = self.body(CAPTAIN)
        self.assertIn(HARBOUR, said)

    def test_the_harbourmaster_is_the_only_writer_of_the_harbour_log(self) -> None:
        said = self.body(HARBOURMASTER)
        self.assertIn(HARBOUR, said)
        self.assertIn("only writer", said)

    def test_the_harbourmaster_is_not_a_merge_queue(self) -> None:
        """`GLOSSARY.md` says so in those words, and the brief is held to the row."""
        self.assertIn("not a merge queue", self.body(HARBOURMASTER))

    def test_the_harbourmaster_never_writes_another_fairways_deck_log(self) -> None:
        """One writer per deck log is the whole reason two captains never conflict over one file."""
        self.assertIn("deck log", self.body(HARBOURMASTER))


if __name__ == "__main__":
    unittest.main()
