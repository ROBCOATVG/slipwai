"""The catch-up notes a migration leaves: what the versions crossed ask of code the factory never wrote.

`test_migrate.py` holds the merge and `test_replay.py` the generation. This is about the half of an upgrade
neither of them carries — a new answer the project has to give, a tool to re-run, a step in the account it
deploys to, a gate that now judges code written before the rule existed. Every version's `CHANGELOG.md`
entry already carries that sentence, written by whoever made the change in the commit that made it, and for
a long time nothing read it. Nothing could: the changelog is the factory's file, a generated project has no
copy of it, and where `slipwai` is the frozen executable there is no copy to reach.

So `migrate` writes them into the project before it returns and `/catch-up` reads them there. Three
properties are worth gating and all are here. The notes are *verbatim* — this selects and quotes, it never summarises,
and a version whose author wrote no catch-up paragraph is reported as having written none rather than as
having asked nothing, which would be a promise it cannot make. And the file is *disposable* — git-ignored,
because the durable record is the changelog and a committed copy in every project is the same words in a
second place, free to disagree with the first. And the file is *always there* once the merge changed
anything — a project whose manifest records no version, which is every one scaffolded before 1.6.0, is the
one that crossed the most, and an absent file would tell it nothing is owed.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_migrate import migrate
from test_replay import NEWER, git, newer_factory

from slipwai.assets import NOTES, VERSION
from slipwai.catch_up import FIRST, crossed, notes, parts, shared
from slipwai.versions import base

# What a version says for itself and what it asks of somebody else's repository, in the two shapes
# `CHANGELOG.md` writes them and this reads them back.
HEADLINE = "A newer factory asks for one thing it could not simply write."
NOTE = "Move the one line this could not move, in `apps/`, by hand."


def entry(version: str, owed: str | None = NOTE) -> str:
    """One changelog entry in the shape `AGENTS.md` asks for it."""
    body = (
        f"\n## {version} — MINOR\n\n"
        f"**{HEADLINE}** Some paragraphs of detail that the notes have no room for and do not carry.\n"
    )
    return body + (f"\n**Catch-up for a project generated before this.** {owed}\n" if owed else "")


def factory_with_entry(into: Path, owed: str | None = NOTE) -> Path:
    """A newer factory whose changelog has an entry for the version it claims to be."""
    factory = newer_factory(into, "\n## A newer factory's line\n")
    changelog = factory / "CHANGELOG.md"
    text = changelog.read_text()
    first = text.find("\n## ")
    changelog.write_text(
        text[:first] + entry(NEWER, owed) + text[first:]
        if first >= 0
        else text.rstrip() + entry(NEWER, owed)
    )
    return factory


class NotesTest(FactoryTestCase):
    def test_a_migration_leaves_the_notes_for_the_versions_it_crossed(self) -> None:
        """The range needs no searching: `migrate` reads `updatedWith` before it merges and knows the
        version it is merging, so both bounds are already in its hands."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "noted", "event-modelling", "python")
            factory = factory_with_entry(Path(directory))

            result = migrate(repo, factory)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(NOTES, result.stdout)
            page = (repo / NOTES).read_text()
            self.assertIn(f"# Catch up: noted, {VERSION} to {NEWER}", page)
            self.assertIn(f"### {NEWER} — MINOR", page)
            self.assertIn(HEADLINE, page)
            self.assertIn(f"**Owes:** {NOTE}", page)
            self.assertIn("/catch-up", page)

    def test_the_notes_are_git_ignored_so_they_are_never_committed(self) -> None:
        """Disposable on purpose. The record that lasts is the factory's changelog; a copy committed into
        every project is the same words in a second place, free to disagree, and left behind when spent."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "ignored", "event-modelling", "go")
            factory = factory_with_entry(Path(directory))

            self.assertEqual(migrate(repo, factory).returncode, 0)

            self.assertTrue((repo / NOTES).is_file())
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "", "the notes dirty the tree")
            self.assertTrue(git(repo, "check-ignore", NOTES).stdout.strip())

    def test_a_version_that_recorded_no_note_is_said_to_have_recorded_none(self) -> None:
        """Printed as though it asked nothing, an entry whose author simply did not write one would read as
        a promise this cannot make."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "unrecorded", "event-modelling", "go")
            factory = factory_with_entry(Path(directory), owed=None)

            self.assertEqual(migrate(repo, factory).returncode, 0)

            page = (repo / NOTES).read_text()
            self.assertIn(HEADLINE, page)
            self.assertIn("**Owes:** nothing recorded for a repository that already existed.", page)

    def test_a_conflicted_migration_still_leaves_them(self) -> None:
        """The notes are what the *versions* asked for, which a conflict does not change — and a merge left
        in progress is exactly when somebody wants to know what they are resolving towards."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "conflicted", "event-modelling", "typescript")
            factory = factory_with_entry(Path(directory))
            skill = repo / "skills/tdd/SKILL.md"
            skill.write_text(skill.read_text() + "\n## The product's section, in the same place\n")
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-qm", "Its own section")

            result = migrate(repo, factory)

            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("conflict(s)", result.stdout)
            self.assertTrue((repo / NOTES).is_file(), "a conflicted migration left no notes")
            self.assertIn(NOTES, result.stdout)

    def test_a_snapshot_is_read_as_the_release_it_is_heading_for(self) -> None:
        """A project generated from `1.13.0.dev4` has had what the `1.13.0` entry described that day, so it
        takes that entry when migrating past it and nothing when migrating to the release itself."""
        self.assertEqual(parts(f"{NEWER}.dev4"), parts(NEWER))
        self.assertEqual(parts("snapshot"), ())
        self.assertEqual(crossed(f"{NEWER}.dev4", NEWER), [])

    def test_a_project_with_no_recorded_version_is_given_everything_and_told_why(self) -> None:
        """Every project scaffolded before 1.6.0: no factory before that wrote `generator`, so nothing in the
        project says which one made it. That is the project that crossed the most, and the one an absent file
        would tell that nothing is owed — so the file is written, opens with why the bound is unknown, and
        lists every entry above the first for the reader to pick up from the one that made their project."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "ancient", "event-modelling", "python")
            manifest = repo / "project.json"
            document = json.loads(manifest.read_text())
            del document["generator"]
            manifest.write_text(json.dumps(document, indent=2) + "\n")
            # Into the scaffold commit itself, as such a factory left it, so the manifest is not a file both
            # sides changed; `--amend` keeps the factory as the author, which is how `replay` finds its base.
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "--amend", "--no-edit")
            factory = factory_with_entry(Path(directory))

            result = migrate(repo, factory)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Next: /catch-up", result.stdout)
            self.assertNotIn("Next: make verify", result.stdout)
            page = (repo / NOTES).read_text()
            self.assertIn(f"# Catch up: ancient, an unrecorded version to {NEWER}", page)
            self.assertIn("records no `generator.updatedWith`", page)
            self.assertIn("before 1.6.0", page)
            self.assertIn(f"## Every version above {FIRST}", page)
            self.assertIn(f"**Owes:** {NOTE}", page, "the newest entry is missing from the list of everything")
            self.assertNotIn(f"### {FIRST}", page, "the first entry is not above itself")

    def test_a_page_is_written_even_when_nothing_was_crossed_and_says_why(self) -> None:
        """An absent file reads as "nothing owed", which is the one thing this must never say by accident.
        So each way of crossing nothing is a page with its reason first, and what can be listed under it."""
        self.assertEqual(crossed(VERSION, VERSION), [])
        release = base(VERSION)
        assert release is not None
        same = notes("still", f"{release}.dev3", VERSION)
        self.assertIn(f"both {release}", same)
        self.assertIn("not told apart", same)
        self.assertIn(f"## The one entry both versions belong to, {release}", same)
        self.assertIn(shared(VERSION)[0][2], same, "the shared entry's headline is not shown")
        unreadable = notes("odd", "snapshot")
        self.assertIn("`snapshot`, which is not a version this can read", unreadable)
        self.assertIn(f"## Every version above {FIRST}", unreadable)
        self.assertIn("which is newer than the slipwai", notes("ahead", "999.0.0"))
        self.assertIn(f"has no entry between {VERSION} and 999.0.0", notes("gap", VERSION, "999.0.0"))
        for page in (same, unreadable):
            self.assertIn("## Why the versions crossed could not be listed as such", page)
            self.assertIn("/catch-up", page)

    def test_the_notes_quote_the_changelog_rather_than_rewriting_it(self) -> None:
        """The one property that makes them worth reading: the sentence in the project is the sentence its
        author wrote. Anything paraphrased here would be a second version of the fact."""
        page = notes("verbatim", "0.9.0", VERSION)
        self.assertNotIn("## Why the versions crossed", page)
        for _number, _level, headline, owed in crossed("0.9.0", VERSION):
            self.assertIn(headline, page)
            if owed is not None:
                self.assertIn(owed, page)
