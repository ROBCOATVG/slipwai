"""The changelog: that it says what this version is, and that nothing has been shipped unrecorded.

Two files hold one record. `CHANGELOG.md` is released prose, appended to by `make release` alone; the entry
being written is `changelog.d/`, a file per change, so no two branches in flight ever touch the same line —
`changelog.d/README.md` says why that matters more than a merge driver could. What can be checked
mechanically is: `main` carries a snapshot, the released entries descend without repeating and each names
its level, every release this repository ever tagged has one, and — the one that catches the real mistake —
the fragments and `VERSION` agree about which release is being written. The level is no longer only a claim
in a heading: the highest one the fragments make is arithmetic on the last release, and that is the number
`main` has to carry.

`scripts/changelog-draft.py` is proved here too, because a tool that exists to stop an omission is only
worth having if it is right about what has landed.
"""
from __future__ import annotations

import re
import subprocess
import unittest

from slipwai.assets import ROOT, VERSION
from slipwai.changelog import FRAGMENTS, LEVELS, fragments, implied, level
from slipwai.versions import base, is_release, is_snapshot

CHANGELOG = ROOT / "CHANGELOG.md"
# `## 1.4.0 — MINOR`, or `## 1.0.0` for the first version, which nothing preceded to bump from.
ENTRY = re.compile(r"(?m)^## (\d+\.\d+\.\d+)(?: — (MAJOR|MINOR|PATCH))?$")
# The first line of a block: a bold lead sentence, `**Catch-up.** …` or `**A project is given …**`. A bold
# word mid-paragraph (`**shared** mode`, `**One:** a Go service`) does not end its bold with a full stop.
LEAD = re.compile(r"^\*\*[^*]+[.!?]\*\*")


def entries() -> list[tuple[str, str | None]]:
    return [(match.group(1), match.group(2)) for match in ENTRY.finditer(CHANGELOG.read_text())]


def parts(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def git(*arguments: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(ROOT), *arguments], text=True, capture_output=True, check=False
    )
    return done.stdout.strip() if done.returncode == 0 else ""


class ChangelogTest(unittest.TestCase):
    def test_main_carries_a_snapshot(self) -> None:
        """`1.3.0.dev0`, never `1.3.0`: a release is written into `VERSION` by `make release` alone, on the
        commit it tags, and the very next commit opens the next snapshot.

        The tag's own `verify` run checks out that tagged commit, so a released `VERSION` is allowed there —
        and only there. Anywhere else it is a release sitting unpublished on a branch."""
        if is_release(VERSION):
            self.need_history()
            head = git("rev-parse", "HEAD")
            tagged = git("rev-parse", f"v{VERSION}^{{commit}}")
            self.assertEqual(
                tagged,
                head,
                f"VERSION is {VERSION}, a release, but HEAD is not v{VERSION}: main carries `<release>.dev0`",
            )
            return
        self.assertTrue(is_snapshot(VERSION), f"VERSION is {VERSION}; main carries `<release>.dev0`")

    def test_the_changelog_holds_released_entries_only(self) -> None:
        """The release in flight has no entry here until it is cut. `make release` assembles one from the
        fragments in the commit it tags, so an entry in this file is a version somebody can install."""
        if is_release(VERSION):
            self.skipTest("this is the tagged commit, where the entry has just been assembled")
        found = entries()
        written = base(VERSION)
        assert written is not None
        if not found:
            self.assertEqual(
                "1.0.0",
                written,
                "only the first public release may be in flight without an earlier changelog entry",
            )
            return
        self.assertLess(
            parts(found[0][0]), parts(written),
            f"CHANGELOG.md's newest entry is {found[0][0]} and VERSION is a snapshot of {written}: the entry "
            f"being written belongs in changelog.d/, and `make release` is what moves it here",
        )

    def test_the_entries_descend_and_none_is_written_twice(self) -> None:
        versions = [version for version, _level in entries()]
        self.assertEqual(len(versions), len(set(versions)), f"a version is entered twice: {versions}")
        ordered = sorted(versions, key=parts, reverse=True)
        self.assertEqual(versions, ordered, "the entries are not newest-first")

    def test_every_entry_but_the_first_version_names_its_bump_level(self) -> None:
        """The level is the claim the rule is about — that a new option is a MINOR and a fixed asset a PATCH
        — so an entry without one is an entry that dodged the question."""
        found = entries()
        if not found:
            return
        for version, level_named in found[:-1]:
            self.assertIn(level_named, LEVELS, f"{version} names no bump level")
        self.assertIsNone(found[-1][1], "the first version was bumped from nothing, so it has no level")

    def test_every_fragment_opens_with_a_level_and_says_something(self) -> None:
        """A fragment is a level and the prose: the level because the entry's is the highest of them, the
        prose because a file that claims a level and says nothing raises the number for no reason."""
        found = fragments()
        for path, claim, body in found:
            named = path.relative_to(ROOT).as_posix()
            self.assertIn(claim, LEVELS, f"{named} does not open with PATCH, MINOR or MAJOR alone on a line")
            self.assertTrue(body.strip(), f"{named} claims {claim} and says nothing")
            self.assertRegex(body, LEAD, f"{named} does not open with a bold sentence saying what changed")

    def test_the_fragments_are_the_number_main_carries(self) -> None:
        """The rule `AGENTS.md` states, as arithmetic: the number on `main` is the claim the changes since the
        last release make. A MINOR fragment under a `VERSION` that only raised the PATCH is a release
        understating what it contains, and the commit that writes the fragment is where that is cheap to fix."""
        if is_release(VERSION):
            self.skipTest("this is the tagged commit, where the fragments have just been consumed")
        found = fragments()
        written = base(VERSION)
        if not found:
            self.assertEqual(
                [], list(FRAGMENTS.glob("*.md") if FRAGMENTS.is_dir() else []),
                "changelog.d/ holds files that are not fragments",
            )
            return
        released = entries()
        if not released:
            self.assertEqual(
                "1.0.0",
                written,
                "fragments with no released predecessor may only describe the first public release",
            )
            return
        self.assertEqual(
            implied(released[0][0], found), written,
            f"the fragments in changelog.d/ claim a {level(found)} over {released[0][0]}, and VERSION is a "
            f"snapshot of {written}: raise the number the claim needs, or claim what the changes are",
        )

    def test_the_guide_to_the_directory_stays_with_it(self) -> None:
        """A convention with nowhere to read it is a convention until the first person who has not seen it —
        and the file is also what keeps the directory in the repository between releases."""
        guide = FRAGMENTS / "README.md"
        self.assertTrue(guide.is_file(), "changelog.d/ has no README.md saying what belongs in it")
        text = guide.read_text()
        self.assertIn("make release", text)
        self.assertIn("AGENTS.md", text)

    def test_every_block_starts_after_a_blank_line(self) -> None:
        """Two paragraphs with no blank line between them render as one, which turns a block's lead sentence
        into the tail of the paragraph above it. Cheap to check, and invisible until the page is read."""
        fused = []
        for path in [CHANGELOG, *(path for path, _claim, _body in fragments())]:
            lines = path.read_text().split("\n")
            fused += [
                f"{path.relative_to(ROOT).as_posix()} line {number}: {line[:50]}…"
                for number, line in enumerate(lines, start=1)
                if LEAD.match(line)
                and number > 1
                and lines[number - 2].strip()
                and not lines[number - 2].startswith("#")
            ]
        self.assertEqual(
            [], fused, "a block's lead sentence follows another paragraph with no blank line between, so the "
            "two render as one paragraph; add it back:\n  " + "\n  ".join(fused),
        )

    def need_history(self) -> None:
        """Skip, with the reason, where the history these read is not here: an unpacked sdist has no `.git`
        at all, and CI's `actions/checkout` clones one commit deep unless it is told otherwise."""
        if git("rev-parse", "--is-inside-work-tree") != "true":
            self.skipTest("not a git checkout, so there is no history to hold the changelog to")
        if not git("rev-parse", "--verify", "HEAD"):
            self.skipTest("the clean public export has not made its first commit yet")
        if git("rev-parse", "--is-shallow-repository") == "true":
            self.skipTest("the checkout is shallow, so the versions before its tip are not in it")

    def test_every_release_this_repository_has_ever_tagged_has_an_entry(self) -> None:
        """`tag-release.py` refuses a release without an entry, so this is the same rule read off the
        history — and it catches an entry edited away after the fact, which the script never sees."""
        self.need_history()
        tags = git("tag", "--list", "v*").split()
        if not tags:
            self.skipTest("no release tag is fetched here, so there is no release to hold to an entry")
        recorded = {version for version, _level in entries()}
        self.assertEqual({tag[1:] for tag in tags} - recorded, set(), "a release was tagged and never entered")

    def test_every_number_main_ever_carried_before_snapshots_has_an_entry(self) -> None:
        """Before snapshots every user-visible commit set `VERSION` to a release, and each of those numbers
        owes an entry still. A snapshot opened after a release (`1.3.1.dev0`) owes none: it is a claim
        about nothing until a change lands, and that change may raise it."""
        self.need_history()
        carried = {
            git("show", f"{sha}:VERSION").strip()
            for sha in git("log", "--format=%H", "--", "VERSION").splitlines()
        }
        releases = {version for version in carried if not is_snapshot(version)}
        recorded = {version for version, _level in entries()}
        self.assertEqual(releases - recorded, set(), "a release was set in VERSION and never entered here")

    def test_the_draft_script_lists_what_has_landed_since_a_version(self) -> None:
        """What it is for: the author writing a fragment is handed the commits rather than asked to remember
        them, split by whether they reached a user — the same split the bump level is decided by — with the
        fragments already written beside them."""
        self.need_history()
        versions = [version for version, _level in entries()]
        if len(versions) < 2:
            self.skipTest("only one version, so there is no earlier one to draft from")
        # The oldest, which predates the release tags and so exercises the fallback to the commit that set
        # `VERSION`; from the newest release there may be nothing landed yet, which the script reports.
        done = subprocess.run(
            ["python3", "scripts/changelog-draft.py", versions[-1]],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("Reached a user", done.stdout)
        self.assertIn(f"belongs in the {base(VERSION)} entry", done.stdout)
        self.assertIn("changelog.d/", done.stdout)
        self.assertNotIn("(none)", done.stdout.split("## Did not")[0], "no user-visible commit since 1.0.0?")

    def test_the_draft_script_refuses_a_version_this_history_never_set(self) -> None:
        self.need_history()
        done = subprocess.run(
            ["python3", "scripts/changelog-draft.py", "9.9.9"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("no v9.9.9 tag and no commit set VERSION to 9.9.9", done.stderr)

    def test_the_rule_and_the_files_point_at_each_other(self) -> None:
        """`AGENTS.md` is where the versioning rule lives, and a fragment nobody is told to write is a
        fragment nobody writes."""
        rule = (ROOT / "AGENTS.md").read_text()
        self.assertIn("CHANGELOG.md", rule)
        self.assertIn("changelog.d/", rule)
        self.assertIn("make changelog", (ROOT / "docs/maintaining.md").read_text())
        self.assertIn("CHANGELOG.md", (ROOT / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
