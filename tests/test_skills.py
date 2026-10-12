"""The skills are one catalogue, in version 2's words, and the rename table says only what is true.

Three things are held here, and each cost the first attempt something.

**One catalogue.** Phase 0 copied all 53 skills into `.claude/skills/` so that every session in this fork
had `tdd`, `testing` and the rest from its first commit, and slice 3.2 brought the same files back under
`assets/toolkit/skills/`, which is what a generated project receives. Two tracked copies of one catalogue
drift: a rename lands in whichever one the session had open, and nothing afterwards says which is right.
From slice 5.1 the toolkit is the only tracked copy; `make skills` materialises the other locally, and
`.gitignore` keeps it out of the history.

**Version 2's words.** The plan's rule is that nothing in version 2 is called a workstation, a workstream,
a lane or a runner. Those words also mean other things in English, and the skills use them in those other
senses — a test runner, an event model's lanes — so `ANOTHER_SENSE` allows a word to one named skill at a
time, with the sense it means there. A skill not named may not use the word at all, which is what holds
the next skill, and the next edit to an existing one, to the vocabulary.

**A rename table that cannot lie.** `docs/rename.json` is what `migrate` applies to a version 1 project
(slice 8.3). A row claiming a rename nobody made would move a person's file to a name version 2 has not
got, so every row is checked here in both directions: the old name is gone, and the new one is there.
"""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "assets/toolkit/skills"
RENAMES = ROOT / "docs/rename.json"

# Whole words, so "swimlanes" is not read as "lanes" and "forerunner" is not read as "runner".
RETIRED = {"workstation": r"workstations?", "workstream": r"workstreams?", "lane": r"lanes?",
           "runner": r"runners?"}

# Which skills may use a retired word, because there it means something version 1 never meant. The key is
# the directory under `assets/toolkit/skills`, or the file name for the two files at its root.
ANOTHER_SENSE: dict[str, set[str]] = {
    # The thing that runs tests — Vitest, Jest, Playwright, Stryker, the CI job — and in the last two a
    # projection's catch-up runner beside its checkpoint store. Never version 1's `cruise.py`, which
    # started one iteration after another and is retired at slice 7.7.
    "runner": {
        "adversarial-testing", "bff-entry-points", "characterisation-tests", "ci-debugging",
        "codebase-design", "debugging", "front-end-testing", "mutation-testing", "react-testing",
        "tdd", "test-design-reviewer", "testing", "web-interface-guidelines",
        "event-sourcing", "global-event-model",
    },
    # A row of an event model, or a row of a table. Never version 1's word for a berth.
    "lane": {"REFERENCES.md", "acceptance-review", "bff-design", "event-modeling", "event-sourcing"},
    # A developer's own machine, in a note about where a reviewer runs.
    "workstation": {"double-check"},
}

KINDS = {"file", "make-target", "command", "setting", "field", "skill"}


def skill_files() -> list[Path]:
    """Every readable file in the catalogue: the skills and the two files beside them."""
    return [path for path in sorted(SKILLS.rglob("*")) if path.is_file() and path.suffix in {".md", ".txt", ""}]


def owner(path: Path) -> str:
    """Which skill a file belongs to, or the file's own name where it sits at the catalogue's root."""
    return path.relative_to(SKILLS).parts[0]


class CatalogueTest(unittest.TestCase):
    def test_every_skill_has_a_skill_file(self) -> None:
        """A directory with no `SKILL.md` is a skill no harness can load, and `toolkit.py` ships it anyway."""
        directories = sorted(path for path in SKILLS.iterdir() if path.is_dir())
        self.assertGreater(len(directories), 50, "the catalogue should not have shrunk")
        for directory in directories:
            with self.subTest(skill=directory.name):
                self.assertTrue((directory / "SKILL.md").is_file(), f"{directory.name} has no SKILL.md")

    def test_the_catalogue_is_tracked_once(self) -> None:
        """`.claude/skills/` is a local copy from `make skills`; tracking it too is how the two drift."""
        listed = subprocess.run(
            ["git", "ls-files", "--", ".claude/skills"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        if listed.returncode != 0:  # pragma: no cover - a checkout without git, which CI never is
            self.skipTest("not a git checkout")
        tracked = [line for line in listed.stdout.splitlines() if line.strip()]
        self.assertEqual(tracked, [], f"{len(tracked)} skill files are tracked twice; `make skills` writes them")


class VocabularyTest(unittest.TestCase):
    def test_no_skill_names_a_slipwai_thing_in_version_1s_words(self) -> None:
        """The plan's rule, applied where an agent reads it rather than only where the plan says it."""
        for path in skill_files():
            text = path.read_text(encoding="utf-8", errors="ignore")
            for word, pattern in RETIRED.items():
                if not re.search(rf"\b{pattern}\b", text, re.IGNORECASE):
                    continue
                with self.subTest(file=path.relative_to(ROOT).as_posix(), word=word):
                    self.assertIn(
                        owner(path), ANOTHER_SENSE[word],
                        f"{path.relative_to(ROOT).as_posix()} uses the retired name {word!r}; "
                        f"use version 2's word, or name the sense in ANOTHER_SENSE",
                    )

    def test_an_allowance_with_nothing_behind_it_is_refused(self) -> None:
        """An allowance outlives the text it was written for, and then it is a hole nobody can see."""
        for word, pattern in RETIRED.items():
            using = {owner(path) for path in skill_files()
                     if re.search(rf"\b{pattern}\b", path.read_text(encoding="utf-8", errors="ignore"), re.I)}
            for skill in sorted(ANOTHER_SENSE.get(word, set()) - using):
                with self.subTest(word=word, skill=skill):
                    self.fail(f"{skill} is allowed {word!r} and no longer uses it; drop the allowance")


class RenameTableTest(unittest.TestCase):
    def setUp(self) -> None:
        self.table = json.loads(RENAMES.read_text(encoding="utf-8"))

    def test_the_table_says_what_it_is_for_and_what_may_go_in_it(self) -> None:
        """`migrate` reads this years after it was written; a bare list of pairs would not say from what."""
        self.assertEqual(self.table["v"], 1)
        self.assertIn("migrate", self.table["reads"])
        self.assertEqual(set(self.table["kinds"]), KINDS)

    def test_every_row_is_whole(self) -> None:
        for row in self.table["renames"]:
            with self.subTest(row=row):
                self.assertEqual({"kind", "from", "to", "slice"} - set(row), set(), "a row is missing a field")
                self.assertIn(row["kind"], KINDS)
                self.assertNotEqual(row["from"], row["to"])

    def test_no_name_is_renamed_twice(self) -> None:
        """Two rows for one old name make the merge depend on which `migrate` reads first."""
        pairs = [(row["kind"], row["from"]) for row in self.table["renames"]]
        self.assertEqual(sorted(pairs), sorted(set(pairs)), "one old name has two rows")

    def test_a_rename_the_fork_has_not_made_is_refused(self) -> None:
        """The table is `migrate`'s instructions. A row ahead of the code moves a file to a name
        version 2 has not got, and the person who ran it finds out at the merge."""
        for row in self.table["renames"]:
            if row["kind"] not in {"file", "command", "skill"}:
                continue
            with self.subTest(row=row):
                self.assertFalse((ROOT / row["from"]).exists(), f"{row['from']} is still here, not renamed")
                self.assertTrue((ROOT / row["to"]).exists(), f"{row['to']} is not here; the row is ahead of the code")



class OwnProseTest(unittest.TestCase):
    """The ban holds this repository's own pages too, not only the catalogue it ships.

    It did not, and the gap cost exactly what the rule exists to stop: two guide pages and the README
    explained a fairway by calling it a lane — "A **fairway** is a lane of work" — which is the retired word
    teaching the new one, on the pages a first-time reader meets first. The skills were held to this from
    their first commit and the prose beside them never was.

    Allowed the same way a skill is allowed one: by name, with a reason, and refused when the allowance has
    nothing behind it. `AGENTS.md` states the ban and must say the words to state it; the plan records every
    rename and therefore says both names; `GLOSSARY.md` is written from the plan and its third column is
    version 1's own names. The rest of `runner`'s allowances are the senses version 2 never claimed — the
    thing a CI job runs on, a cloud product called App Runner, and version 1's own loop named as version 1's,
    which `AGENTS.md` expressly permits.
    """

    #: Page → the retired words it may use, and why. A path prefix, matched from the repository root.
    ALLOWED: dict[str, set[str]] = {
        # States the ban, so it says the words.
        "AGENTS.md": {"workstation", "workstream", "lane", "runner"},
        # Records every rename, and therefore says both names.
        "docs/slipwai-2-plan.md": {"workstation", "workstream", "lane", "runner"},
        # Written from the plan's vocabulary table; its third column is version 1's own names.
        "GLOSSARY.md": {"workstation", "workstream", "lane", "runner"},
        # The page whose whole subject is what changed since version 1, and which therefore names version
        # 1's words as version 1's — "version 1 called this a value stream, or a workstream" — and ends on
        # a table of them. The same case as the glossary's third column.
        "docs/whats-new.md": {"workstation", "workstream", "lane", "runner"},
        # Version 1's loop, named as version 1's — which `AGENTS.md` permits in as many words.
        "README.md": {"runner"},
        "docs/guide/let-it-cruise.md": {"runner"},
        "docs/guide/a-second-person.md": {"runner"},
        # The machine a CI job runs on.
        "docs/extensions.md": {"runner"},
        # AWS's App Runner, the product of that name, which the page says it is.
        "docs/reference/the-skiff-and-the-liner.md": {"runner"},
    }

    def pages(self) -> list[Path]:
        return sorted([*ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md")])

    def allowance(self, path: Path) -> set[str]:
        # `as_posix`, because the keys below are written with forward slashes and `str(PurePath)` on
        # Windows is backslashed — so every allowance missed and every page this test exists to permit
        # failed there, while the platform that wrote the rule passed.
        name = path.relative_to(ROOT).as_posix()
        for prefix, words in self.ALLOWED.items():
            if name == prefix or name.startswith(f"{prefix}/"):
                return words
        return set()

    def test_no_page_of_our_own_uses_a_retired_word(self) -> None:
        for path in self.pages():
            text, allowed = path.read_text(encoding="utf-8"), self.allowance(path)
            for word, pattern in RETIRED.items():
                if word in allowed:
                    continue
                shown = path.relative_to(ROOT).as_posix()
                with self.subTest(page=shown, word=word):
                    found = re.findall(rf"\b{pattern}\b", text, re.I)
                    self.assertEqual(found, [], f"{shown} says {found}; use the slipway's word")

    def test_an_allowance_with_nothing_behind_it_is_refused(self) -> None:
        """An allowance outlives the text it was written for, and is then a hole nobody can see."""
        for name, words in self.ALLOWED.items():
            place = ROOT / name
            pages = sorted(place.rglob("*.md")) if place.is_dir() else [place]
            for word in sorted(words):
                with self.subTest(page=name, word=word):
                    text = "".join(path.read_text(encoding="utf-8") for path in pages if path.is_file())
                    self.assertTrue(re.search(rf"\b{RETIRED[word]}\b", text, re.I),
                                    f"{name} is allowed {word} and does not use it")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
