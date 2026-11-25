"""The person's checkout kept level with the forge's trunk after a merge, where that is a fast-forward (#166).

`advance` pushed to the remote and returned, on the grounds that every checkout catches up on its next fetch.
None does: a fetch moves `origin/main` and nothing else, so manda's checkout sat on a day-old `main` while 493
commits landed on the forge, the board drew that day-old project, and three commits made on that `main` were
never pushed or mentioned. Each case here is a real repository with a bare one beside it as the forge.
"""
from __future__ import annotations

import checkout_packages  # noqa: F401
from harbourmaster_fixture import Fixture, MergeFixture  # noqa: F401


class LevelTest(MergeFixture):
    def setUp(self) -> None:
        super().setUp()
        self.forge = self.root.parent / f"{self.root.name}.git"
        self.git("init", "--quiet", "--bare", "--initial-branch=main", str(self.forge))
        self.git("remote", "add", "origin", str(self.forge))
        self.git("push", "--quiet", "origin", "main")
        self.git("fetch", "--quiet", "origin")

    def forge_head(self) -> str:
        return self.git("rev-parse", "main", where=self.forge).stdout.strip()

    def granted(self) -> dict:
        answer = self.answer()
        self.assertEqual(answer.kind, "granted", answer.fields)
        self.assertEqual(answer.fields["commit"], self.forge_head(), "the merge was pushed to the forge")
        return answer.fields

    def test_a_clean_checkout_on_trunk_is_fast_forwarded_with_its_working_tree(self) -> None:
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.git("checkout", "--quiet", "main")
        self.ask("ORD-01")
        self.run_once()
        said = self.granted()
        self.assertNotIn("note", said)
        self.assertEqual(self.head("main"), said["commit"])
        self.assertEqual(self.git("symbolic-ref", "--short", "HEAD").stdout.strip(), "main")
        self.assertTrue((self.root / "ordering.txt").is_file(), "the working tree moved with the ref")

    def test_uncommitted_changes_a_fast_forward_would_overwrite_are_left_alone_and_said(self) -> None:
        """Never detached, never reset: trunk has already moved on the forge, so the checkout stays as it is."""
        self.slice_branch("ORD-01", "service.txt", "the slice's version\n")
        self.git("checkout", "--quiet", "main")
        (self.root / "service.txt").write_text("edited and not committed\n", encoding="utf-8")
        self.ask("ORD-01")
        done = self.run_once()
        said = self.granted()
        self.assertEqual(self.head("main"), self.trunk_was, "the local trunk was moved under uncommitted work")
        self.assertEqual(self.git("symbolic-ref", "--short", "HEAD").stdout.strip(), "main", "it was detached")
        self.assertEqual((self.root / "service.txt").read_text(encoding="utf-8"), "edited and not committed\n")
        self.assertIn("left exactly where it stood", str(said["note"]))
        self.assertIn("git merge --ff-only origin/main", str(said["note"]))
        self.assertIn("left exactly where it stood", done.stdout)

    def test_commits_only_the_local_trunk_has_are_named_and_never_moved(self) -> None:
        self.git("checkout", "--quiet", "main")
        (self.root / "decision.md").write_text("D499\n", encoding="utf-8")
        self.commit("D499: the person's own decision")
        own = self.head("main")
        self.git("checkout", "--quiet", "-b", "slice/ORD-01", "origin/main")
        (self.root / "ordering.txt").write_text("ordering\n", encoding="utf-8")
        self.commit("ORD-01")
        self.git("checkout", "--quiet", "main")
        self.ask("ORD-01")
        done = self.run_once()
        said = self.granted()
        self.assertEqual(self.head("main"), own, "the person's own commit was moved")
        self.assertNotEqual(self.forge_head(), own)
        self.assertIn("D499: the person's own decision", str(said["note"]))
        self.assertIn("git branch keep-local main", str(said["note"]))
        self.assertIn("D499: the person's own decision", done.stdout, "said at start as well as at the merge")

    def test_a_checkout_on_another_branch_has_its_trunk_ref_moved_as_a_fast_forward(self) -> None:
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.ask("ORD-01")
        self.run_once()
        said = self.granted()
        self.assertNotIn("note", said)
        self.assertEqual(self.head("main"), said["commit"])
        self.assertEqual(self.git("symbolic-ref", "--short", "HEAD").stdout.strip(), "parked-elsewhere")

    def test_a_trunk_ref_with_commits_of_its_own_is_not_moved_from_another_branch(self) -> None:
        self.git("checkout", "--quiet", "-b", "slice/ORD-01", "main")
        (self.root / "ordering.txt").write_text("ordering\n", encoding="utf-8")
        self.commit("ORD-01")
        self.git("checkout", "--quiet", "main")
        (self.root / "adr.md").write_text("0027\n", encoding="utf-8")
        self.commit("ADR 0027, made here")
        own = self.head("main")
        self.git("checkout", "--quiet", "-b", "parked-elsewhere", "slice/ORD-01")
        self.ask("ORD-01")
        self.run_once()
        said = self.granted()
        self.assertEqual(self.head("main"), own)
        self.assertIn("ADR 0027, made here", str(said["note"]))

    def test_a_trunk_checked_out_in_another_worktree_is_left_where_it_stands(self) -> None:
        """`fetch origin main:main` semantics: git refuses to move a branch under a worktree that has it."""
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        elsewhere = self.root.parent / f"{self.root.name}-main"
        self.git("worktree", "add", "--quiet", str(elsewhere), "main")
        self.ask("ORD-01")
        self.run_once()
        said = self.granted()
        self.assertEqual(self.head("main"), self.trunk_was)
        self.assertIn("left where it stood", str(said["note"]))
        self.assertFalse((elsewhere / "ordering.txt").exists())

    def test_a_merge_that_moves_the_harbourmasters_own_scripts_says_it_runs_older_code(self) -> None:
        self.slice_branch("ORD-01", "scripts/agents/spend.py",
                          (self.root / "scripts/agents/spend.py").read_text(encoding="utf-8") + "# moved\n")
        self.git("checkout", "--quiet", "main")
        self.ask("ORD-01")
        done = self.run_once()
        self.granted()
        self.assertIn("changed on disk since it started (spend.py)", done.stdout)

    def test_a_checkout_behind_the_forge_says_so_at_start(self) -> None:
        self.git("checkout", "--quiet", "-b", "ahead", "main")
        (self.root / "later.txt").write_text("later\n", encoding="utf-8")
        self.commit("a commit only the forge has")
        self.git("push", "--quiet", "origin", "ahead:main")
        self.git("checkout", "--quiet", "main")
        self.git("branch", "--quiet", "-D", "ahead")
        done = self.run_once()
        self.assertIn("1 commit behind the forge's main", done.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
