"""The command pages as assets: that the substitution is closed, and that moving them changed no byte.

`tests/fixtures/command-pages.sha256` is what the generator rendered at 074aa35, the commit before the
standing text of `commands.py`, `add_commands.py`, `pin_commands.py`, `ground_command.py` and
`sail_section.py` left their string literals, and this module is the only reason that file exists: every
`commands/*.md` page, across the eight projects `tests/command_pages.py` names, has to come back byte for
byte. Eight because these pages branch on more than one thing at once — the profile, a service's rung, a
browser app, no application at all, a managed destination, the delivery layout, an adopted repository — and
a record taken at one project would pass with half the branches stubbed out to the empty string.

The pages the five modules only *assemble* are recorded too. `cruise.md`, `benchmark.md` and `mutation.md`
come from modules this slice does not touch, so a row of theirs that moved is this slice having disturbed
something it was not moving — which is the failure a digest notices and a reviewer does not.

The substitution's two directions are held in `tests/test_generated_prose.py`, over every templated asset
tree there is, which is where the commands row was added. What is held here is the part that is this
slice's alone: that nothing a project receives changed, and that a page carrying a section marker renders
on both sides of its branch.
"""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import command_pages

from slipwai.project import commands, ground_command

RECORD = Path(__file__).resolve().parent / "fixtures/command-pages.sha256"


def recorded() -> dict[tuple[str, str], str]:
    """The record, as `(case, path) -> digest`, with its header read as the comment it is."""
    rows = {}
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        digest, case, path = line.split()
        rows[(case, path)] = digest
    return rows


class ByteForByteTest(unittest.TestCase):
    """What the generator rendered before the pages moved, and what it renders now."""

    def test_every_page_is_what_it_was_before_the_prose_left_the_modules(self) -> None:
        rows = recorded()
        for case in command_pages.CASES:
            rendered = command_pages.pages(case)
            for path, digest in sorted((path, digest) for (held, path), digest in rows.items()
                                       if held == case):
                with self.subTest(project=case, file=path):
                    self.assertIn(path, rendered, f"{path} is recorded in {RECORD.name} and no longer rendered")
                    self.assertEqual(hashlib.sha256(rendered[path].encode("utf-8")).hexdigest(), digest,
                                     f"{path} is no longer the text recorded in {RECORD.name}")

    def test_the_record_covers_every_project_and_every_page_each_receives(self) -> None:
        """A record that lost a row would pass by not asking about the page that changed."""
        rows = recorded()
        self.assertEqual(sorted({case for case, _path in rows}), sorted(command_pages.CASES))
        for case in command_pages.CASES:
            with self.subTest(project=case):
                self.assertEqual(sorted(path for held, path in rows if held == case),
                                 sorted(command_pages.pages(case)))

    def test_the_matrix_reaches_both_sides_of_every_branch_the_moved_pages_make(self) -> None:
        """The record is only a gate on the branches it was taken across. A page that renders the same text
        in all eight projects is one whose branch this matrix does not reach, and a section marker dropped
        from it would be recorded as the only thing it ever was."""
        rows = recorded()
        for path in ("commands/sail.md", "commands/gaps.md", "commands/constitution-coverage.md",
                     "commands/add-service.md", "commands/add-frontend.md", "commands/characterise.md",
                     "commands/survey.md", "commands/ground.md", "commands/model-delegation-settings.md"):
            with self.subTest(file=path):
                digests = {digest for (_case, held), digest in rows.items() if held == path}
                self.assertGreater(len(digests), 1, f"{path} is recorded at one text only")


class WhereTheyLandTest(unittest.TestCase):
    """Which tree each page belongs in, which is the one thing the digests cannot see."""

    def test_every_templated_toolkit_page_is_also_written_by_the_generator(self) -> None:
        """The quiet direction. Every file under `assets/toolkit/` is copied into a project at the path it
        sits at, and only the ones the generator also writes are written over. A templated page here that
        the generator does not write would ship into somebody's repository raw, with its `{{make}}` still
        in it — which is what sent the three adoption-only pages to `assets/adoption/` instead."""
        written = set(command_pages.pages("standard")) | set(command_pages.pages("event"))
        for path in sorted(commands.COMMANDS.glob("*.md")):
            if "{{" not in path.read_text(encoding="utf-8"):
                continue  # one of the three that never varied, copied verbatim and written over by nothing
            with self.subTest(page=path.name):
                self.assertIn(f"commands/{path.name}", written)

    def test_no_page_only_an_adopted_repository_receives_sits_in_the_toolkit(self) -> None:
        """`assets/adoption/` is read by name and copied nowhere, so a page a greenfield project has no
        generated version of belongs there and only there."""
        adoption = {path.name for path in ground_command.COMMANDS.glob("*.md")}
        self.assertEqual(adoption, {"characterise.md", "survey.md", "ground.md"})
        self.assertEqual(adoption & {path.name for path in commands.COMMANDS.glob("*.md")}, set())
        written = set(command_pages.pages("adopted"))
        for name in sorted(adoption):
            with self.subTest(page=name):
                self.assertIn(f"commands/{name}", written)


class SectionTest(unittest.TestCase):
    """The branches that are a whole section, rendered from both sides, read rather than hashed."""

    def page(self, case: str, path: str) -> str:
        return command_pages.pages(case)[path]

    def test_the_event_paragraph_of_gaps_is_there_on_one_profile_and_gone_on_the_other(self) -> None:
        self.assertIn("Compare event names", self.page("event", "commands/gaps.md"))
        self.assertNotIn("Compare event names", self.page("standard", "commands/gaps.md"))

    def test_the_push_check_is_there_for_a_managed_destination_and_gone_without_one(self) -> None:
        self.assertIn("Before you push, name the release constraint",
                      self.page("standard-managed", "commands/sail.md"))
        self.assertNotIn("Before you push, name the release constraint",
                         self.page("standard", "commands/sail.md"))

    def test_the_event_model_section_of_survey_follows_the_profile(self) -> None:
        self.assertIn("## The event model", self.page("adopted", "commands/survey.md"))
        self.assertNotIn("## The event model", self.page("adopted-settled", "commands/survey.md"))

    def test_the_candidates_section_of_ground_is_gone_once_there_are_none(self) -> None:
        self.assertIn("## What is an application here", self.page("adopted", "commands/ground.md"))
        self.assertNotIn("## What is an application here", self.page("adopted-settled", "commands/ground.md"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
