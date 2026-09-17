"""`scripts/tag-release.py`: the pushes it refuses, and the one it makes.

A release has one irreversible step — the registry takes a name and version once, and a tag that has been
fetched must never move — so every check here is proved by handing the script the mistake it exists to
catch. The forge is a bare repository in a temporary directory: `ls-remote`, `push` and the tag and the two
commits landing on the other side are all real git, and none of it needs a network.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from slipwai.assets import ROOT

SCRIPT = ROOT / "scripts/tag-release.py"
# Released prose only, as the file carries: the entry for the version being cut is the fragments below.
CHANGELOG = "# Changelog\n\n## 1.2.2 — PATCH\n\nBefore it.\n\n## 1.2.1 — PATCH\n\nAnd before that.\n"
# PATCH over 1.2.2, which is what makes 1.2.3 the release these fragments justify cutting.
FRAGMENT = "PATCH\n\n**Something a user can read.** With a paragraph under it.\n"


def git(repo: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *arguments], text=True, capture_output=True, check=True
    ).stdout.strip()


class ReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.forge = self.root / "forge.git"
        self.repo = self.root / "checkout"
        subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(self.forge)], check=True,
                       capture_output=True)
        self.repo.mkdir()
        git(self.repo, "init", "--initial-branch=main")
        git(self.repo, "config", "user.email", "release@example.com")
        git(self.repo, "config", "user.name", "Release Test")
        (self.repo / "VERSION").write_text("1.2.3.dev4\n")
        (self.repo / "CHANGELOG.md").write_text(CHANGELOG)
        (self.repo / "changelog.d").mkdir()
        (self.repo / "changelog.d/README.md").write_text("# The entry being written\n")
        (self.repo / "changelog.d/something.md").write_text(FRAGMENT)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "the last change before the release")
        git(self.repo, "remote", "add", "gitea", str(self.forge))
        git(self.repo, "push", "gitea", "main")

    def release(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--repository", str(self.repo), *arguments],
            text=True, capture_output=True,
        )

    def version_at(self, repo: Path, revision: str) -> str:
        return git(repo, "show", f"{revision}:VERSION").strip()

    def test_a_snapshot_becomes_a_release_a_tag_and_the_next_snapshot_in_one_push(self) -> None:
        """The whole point: one push, and the forge has the tag its release workflows fire on and a main
        whose next green push is the first snapshot of the next number."""
        before = git(self.repo, "rev-parse", "HEAD")
        dry = self.release("--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("would commit: Release 1.2.3 (VERSION 1.2.3.dev4 → 1.2.3)", dry.stdout)
        self.assertIn("would assemble: `## 1.2.3 — PATCH` in CHANGELOG.md from something.md", dry.stdout)
        self.assertIn("would tag: v1.2.3 (slipwai 1.2.3 — PATCH)", dry.stdout)
        self.assertIn("would commit: Open 1.2.4.dev0", dry.stdout)
        self.assertIn("would push: main and v1.2.3 to gitea", dry.stdout)
        self.assertEqual(git(self.repo, "tag", "--list"), "", "a dry run made a tag")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), before, "a dry run made a commit")

        done = self.release()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("pushed: main and v1.2.3", done.stdout)
        self.assertIn("main now carries 1.2.4.dev0", done.stdout)
        self.assertIn("package executables", done.stdout)
        self.assertIn("publish package", done.stdout)
        self.assertIn("slipwai upgrade", done.stdout)
        # The forge has the tag, on a commit whose VERSION is the release and whose parent is what was
        # verified; main is one commit past it, carrying the next snapshot.
        self.assertEqual(git(self.forge, "tag", "--list"), "v1.2.3")
        tagged = git(self.forge, "rev-parse", "v1.2.3^{commit}")
        self.assertEqual(self.version_at(self.forge, tagged), "1.2.3")
        self.assertEqual(git(self.forge, "rev-parse", f"{tagged}~1"), before)
        self.assertEqual(git(self.forge, "rev-parse", "main~1"), tagged)
        self.assertEqual(self.version_at(self.forge, "main"), "1.2.4.dev0")
        # The Release commit is the one that publishes the entry: it carries VERSION, the entry it assembled
        # and the fragment it consumed, so the tag names prose already reviewed where it was written. The Open
        # commit after it touches VERSION alone — the next entry is an empty changelog.d/, which needs no
        # placeholder to be true.
        self.assertEqual(
            git(self.forge, "diff", "--name-only", f"{before}", tagged),
            "CHANGELOG.md\nVERSION\nchangelog.d/something.md",
        )
        self.assertEqual(git(self.forge, "diff", "--name-only", f"{tagged}", "main"), "VERSION")
        changelog = git(self.forge, "show", "main:CHANGELOG.md")
        self.assertTrue(
            changelog.startswith(
                "# Changelog\n\n## 1.2.3 — PATCH\n\n**Something a user can read.** With a paragraph under it."
            ),
            changelog,
        )
        self.assertLess(changelog.index("## 1.2.3 — PATCH"), changelog.index("## 1.2.2 — PATCH"))
        released = CHANGELOG.split("# Changelog\n\n")[1].rstrip("\n")
        self.assertTrue(changelog.endswith(released), "the released entries were disturbed")
        # And the fragment is gone with the same commit: left behind, it would go out again in the next entry.
        self.assertEqual(git(self.forge, "ls-tree", "--name-only", "main", "changelog.d/"), "changelog.d/README.md")
        # Annotated, and its message is the level the fragments claimed rather than a second claim about it.
        self.assertEqual(git(self.repo, "tag", "-l", "--format=%(contents:subject)"), "slipwai 1.2.3 — PATCH")
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s", "v1.2.3"), "Release 1.2.3")
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s"), "Open 1.2.4.dev0")
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_a_version_the_forge_already_has_is_spent(self) -> None:
        """The refusal that matters most: the registry takes a name and version once, so the second attempt
        has to be the next number rather than a retry."""
        self.assertEqual(self.release().returncode, 0)
        # Somebody puts the released number back on main, entry and all, and tries again.
        (self.repo / "VERSION").write_text("1.2.3.dev0\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "reopened by mistake")
        git(self.repo, "push", "gitea", "main")
        again = self.release("--dry-run")
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("already has v1.2.3", again.stderr)
        self.assertIn("spent", again.stderr)

    def test_a_bare_version_on_main_is_not_trusted(self) -> None:
        """Only this script writes a release into `VERSION`, on the commit it tags. A bare number that got
        there any other way is either a release nobody cut or a number nobody opened, and either way the
        entry and the snapshot have to be put right first."""
        (self.repo / "VERSION").write_text("1.2.3\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "released by hand")
        git(self.repo, "push", "gitea", "main")
        result = self.release("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("VERSION is 1.2.3, which is not a snapshot", result.stderr)
        self.assertIn("1.2.3.dev0", result.stderr)

    def test_a_dirty_checkout_is_refused(self) -> None:
        (self.repo / "notes.md").write_text("half an edit\n")
        result = self.release("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("uncommitted changes", result.stderr)

    def test_a_branch_that_is_not_main_is_refused(self) -> None:
        git(self.repo, "checkout", "-b", "release-prep")
        result = self.release("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("a release is cut from main", result.stderr)

    def test_a_commit_the_forge_does_not_have_is_refused(self) -> None:
        """The tag has to name a commit the workflows can check out — and the one verify.yml judged."""
        (self.repo / "notes.md").write_text("later\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "unpushed")
        result = self.release("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("push or pull main first", result.stderr)

    def test_a_release_nothing_was_written_for_is_refused(self) -> None:
        """The entry is written while the version is in flight, one fragment per change, so a release with no
        fragment at all is a version nobody can read the meaning of."""
        (self.repo / "changelog.d/something.md").unlink()
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "the entry, deleted")
        git(self.repo, "push", "gitea", "main")
        result = self.release("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("changelog.d/ has no fragment", result.stderr)

    def test_a_number_the_fragments_do_not_justify_is_refused(self) -> None:
        """The number `main` carries is the claim its changes make. A PATCH fragment under a `VERSION` that
        raised the MINOR is one of the two being wrong, and which is not for this to decide."""
        (self.repo / "VERSION").write_text("1.3.0.dev2\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "raised further than anything claimed")
        git(self.repo, "push", "gitea", "main")
        result = self.release("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("claim a PATCH over 1.2.2, which is 1.2.3", result.stderr)
        self.assertIn("VERSION is a snapshot of 1.3.0", result.stderr)
        self.assertEqual(self.version_at(self.repo, "HEAD"), "1.3.0.dev2", "nothing was written")

    def test_a_fragment_that_claims_no_level_is_refused(self) -> None:
        """The entry's level is the highest its fragments claim, so a fragment claiming none leaves the
        release's own level to be guessed."""
        (self.repo / "changelog.d/something.md").write_text("**No level on the first line.** Just prose.\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "a fragment with no level")
        git(self.repo, "push", "gitea", "main")
        result = self.release("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("do not open with a bump level", result.stderr)
        self.assertIn("something.md", result.stderr)

    def test_a_local_tag_naming_another_commit_is_never_moved(self) -> None:
        git(self.repo, "tag", "v1.2.3", "HEAD")
        (self.repo / "notes.md").write_text("after the tag\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "moved on")
        git(self.repo, "push", "gitea", "main")
        result = self.release("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("names a different commit", result.stderr)

    def test_a_release_made_but_never_pushed_is_finished_rather_than_remade(self) -> None:
        """An earlier run whose push failed leaves its two commits and the tag behind, and nothing else;
        pushing them is that run finishing. Two commits ahead in any other shape is somebody's work."""
        # Exactly what a run leaves when `git push` fails: the shape is reproduced rather than the failure.
        (self.repo / "VERSION").write_text("1.2.3\n")
        (self.repo / "CHANGELOG.md").write_text(
            CHANGELOG.replace("# Changelog\n\n", "# Changelog\n\n## 1.2.3 — PATCH\n\n**Assembled.**\n\n")
        )
        (self.repo / "changelog.d/something.md").unlink()
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "Release 1.2.3")
        git(self.repo, "tag", "--annotate", "v1.2.3", "--message", "slipwai 1.2.3 — PATCH")
        (self.repo / "VERSION").write_text("1.2.4.dev0\n")
        git(self.repo, "commit", "-qam", "Open 1.2.4.dev0")
        dry = self.release("--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("made by an earlier run, never pushed", dry.stdout)
        done = self.release()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("release already made here: v1.2.3", done.stdout)
        self.assertEqual(git(self.forge, "tag", "--list"), "v1.2.3")
        self.assertEqual(self.version_at(self.forge, "main"), "1.2.4.dev0")
        self.assertEqual(
            git(self.forge, "log", "--format=%s", "-3"),
            "Open 1.2.4.dev0\nRelease 1.2.3\nthe last change before the release",
        )

    def test_an_open_commit_that_touched_version_alone_is_still_this_scripts_own(self) -> None:
        """Every release before the entry was opened here left that shape, and a run of one of them whose push
        failed is still finished rather than refused."""
        (self.repo / "VERSION").write_text("1.2.3\n")
        git(self.repo, "commit", "-qam", "Release 1.2.3")
        git(self.repo, "tag", "--annotate", "v1.2.3", "--message", "slipwai 1.2.3 — MINOR")
        (self.repo / "VERSION").write_text("1.2.4.dev0\n")
        git(self.repo, "commit", "-qam", "Open 1.2.4.dev0")
        dry = self.release("--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("made by an earlier run, never pushed", dry.stdout)

    def test_two_commits_of_somebodys_own_are_not_mistaken_for_an_unfinished_release(self) -> None:
        """The same two commits with a file of somebody's own in one of them are not this script's, and are
        refused as unpushed work rather than pushed as a release."""
        (self.repo / "VERSION").write_text("1.2.3\n")
        (self.repo / "notes.md").write_text("mine\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "Release 1.2.3")
        git(self.repo, "tag", "v1.2.3")
        (self.repo / "VERSION").write_text("1.2.4.dev0\n")
        git(self.repo, "commit", "-qam", "Open 1.2.4.dev0")
        result = self.release("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("push or pull main first", result.stderr)

    def test_the_forge_remote_is_whichever_one_this_checkout_has(self) -> None:
        """`publish-to-gitea.py` adds `gitea`; a clone of what it pushed calls the same forge `origin`. Both
        are found, a named one that is absent is refused, and a checkout with neither is told so."""
        git(self.repo, "remote", "rename", "gitea", "origin")
        found = self.release("--dry-run")
        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertIn("would push: main and v1.2.3 to origin", found.stdout)

        named = self.release("--dry-run", "--remote", "gitea")
        self.assertNotEqual(named.returncode, 0)
        self.assertIn('no "gitea" remote in this checkout; it has: origin', named.stderr)

        git(self.repo, "remote", "remove", "origin")
        none = self.release("--dry-run")
        self.assertNotEqual(none.returncode, 0)
        self.assertIn("no gitea or origin remote", none.stderr)
        self.assertIn("publish-to-gitea.py", none.stderr)

    def test_the_address_in_the_report_carries_no_credentials(self) -> None:
        """The report is meant to be pasted into a message; a token in it would travel with it."""
        import importlib.util

        specification = importlib.util.spec_from_file_location("tag_release", SCRIPT)
        assert specification is not None and specification.loader is not None
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        self.assertEqual(
            module.web_url("https://someone:a-token@git.example/owner/slipwai.git"),
            "https://git.example/owner/slipwai",
        )
        self.assertEqual(
            module.web_url("git@git.example:owner/slipwai.git"),
            "https://git.example/owner/slipwai",
        )


if __name__ == "__main__":
    unittest.main()
