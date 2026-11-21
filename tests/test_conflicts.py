"""A conflict in the harbourmaster's rebase is settled where it stopped, where it can be.

manda's second feature was refused 27 times for a conflict in a day and a half: 20 in the feature's own
record files, where two slices had each added an entry, and 7 in code. A record file is woven; anything else
is the mender's first, held mechanically, and the slice's only where the mender could not.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest

import checkout_packages  # noqa: F401
from harbourmaster_fixture import AGENTS, MergeFixture

#: A fake mender: `conflict <told.json>`, in the scratch worktree, mid-rebase. `FAKE_MEND` says what it does.
FAKE = """import json, os, subprocess, sys
told = json.load(open(sys.argv[2]))
assert sys.argv[1] == "conflict" and told["paths"] == ["service.txt"], (sys.argv, told)
what = os.environ.get("FAKE_MEND", "both")
if what in ("both", "strays"):
    open("service.txt", "w").write("one\\ntrunk's\\nthe slice's\\n")
if what == "strays":
    open("other.txt", "w").write("not asked for\\n")
if what == "aborts":
    subprocess.run(["git", "rebase", "--abort"], check=True)
if what == "fails":
    sys.exit(3)
"""


def conflicts():
    found = importlib.util.spec_from_file_location("toolkit_conflicts", AGENTS / "conflicts.py")
    assert found is not None and found.loader is not None
    sys.path.insert(0, str(AGENTS))
    try:
        module = importlib.util.module_from_spec(found)
        found.loader.exec_module(module)
    finally:
        sys.path.remove(str(AGENTS))
    return module


class WovenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.woven = conflicts().woven

    def test_two_additions_at_the_end_are_both_kept_trunk_s_first(self) -> None:
        self.assertEqual(self.woven("a\n", "a\nT\n", "a\nS\n"), "a\nT\nS\n")

    def test_a_slice_that_also_reworded_its_own_entry_has_still_not_disagreed(self) -> None:
        """What the first rule missed: the commit added an entry and changed a line of an earlier one."""
        before = "# Log\n\n## S1\nstatus: open\n"
        commit = "# Log\n\n## S1\nstatus: closed\n\n## S3\nmine\n"
        self.assertEqual(self.woven(before, before + "\n## S2\ntrunk's\n", commit),
                         "# Log\n\n## S1\nstatus: closed\n\n## S2\ntrunk's\n\n## S3\nmine\n")

    def test_a_change_beside_an_addition_is_ordered_not_refused(self) -> None:
        self.assertEqual(self.woven("a\nb\n", "a\nb\nT\n", "a\nB\n"), "a\nB\nT\n")
        self.assertEqual(self.woven("a\nb\n", "T\na\nb\n", "A\nb\n"), "T\nA\nb\n")

    def test_the_same_lines_changed_two_ways_is_a_conflict(self) -> None:
        self.assertIsNone(self.woven("a\nb\n", "a\ntrunk\n", "a\nslice\n"))
        self.assertIsNone(self.woven("a\nb\nc\n", "a\nc\n", "a\nb2\nc\n"))

    def test_the_same_change_on_both_sides_is_made_once(self) -> None:
        self.assertEqual(self.woven("a\nb\n", "a\nB\n", "a\nB\n"), "a\nB\n")
        self.assertEqual(self.woven("a\n", "a\nE\n", "a\nE\n"), "a\nE\n")

    def test_an_entry_trunk_already_holds_is_not_put_in_twice(self) -> None:
        self.assertEqual(self.woven("a\n", "a\nT\nE\nU\n", "a\nE\n"), "a\nT\nE\nU\n")

    def test_a_file_with_no_newline_at_its_end_keeps_its_lines_apart(self) -> None:
        self.assertEqual(self.woven("a", "a\nT", "a\nS\n"), "a\nT\nS\n")


@unittest.skipIf(os.name == "nt", "the scenario is the same on every platform, and the fake is started by path")
class ConflictAtTheMergeTest(MergeFixture):
    def diverge(self, path: str = "service.txt") -> None:
        self.slice_branch("ORD-01", path, "one\nthe slice's\n")
        self.git("checkout", "--quiet", "main")
        (self.root / path).write_text("one\ntrunk's\n", encoding="utf-8")
        self.commit("trunk moved meanwhile")
        self.git("checkout", "--quiet", "parked-elsewhere")
        self.ask("ORD-01")

    def mender(self, what: str) -> None:
        fake = self.root.parent / f"{self.root.name}-conflict.py"
        fake.write_text(FAKE, encoding="utf-8")
        self.addCleanup(fake.unlink, True)
        for name, value in (("SLIPWAI_MENDER", f"{sys.executable} {fake}"), ("FAKE_MEND", what)):
            os.environ[name] = value
            self.addCleanup(os.environ.pop, name, None)

    def lines(self, kind: str) -> list[dict]:
        return [entry.fields for entry in self.harbour() if entry.kind == kind]

    def test_a_record_file_two_slices_added_to_and_one_reworded_is_woven(self) -> None:
        path = "specs/ordering/adversary-log.md"
        (self.root / path).parent.mkdir(parents=True)
        (self.root / path).write_text("# Log\n\n## S1\nstatus: open\n", encoding="utf-8")
        self.git("checkout", "--quiet", "main")
        self.commit("the log so far")
        self.git("checkout", "--quiet", "-b", "slice/ORD-01", "main")
        (self.root / path).write_text("# Log\n\n## S1\nstatus: closed\n\n## S3\nmine\n", encoding="utf-8")
        self.commit("ORD-01 closes S1 and adds S3")
        self.git("checkout", "--quiet", "main")
        (self.root / path).write_text("# Log\n\n## S1\nstatus: open\n\n## S2\ntrunk's\n", encoding="utf-8")
        self.commit("trunk gained S2 meanwhile")
        self.git("checkout", "--quiet", "-b", "parked-elsewhere", "slice/ORD-01")
        self.ask("ORD-01")
        done = self.run_once()
        self.assertEqual(self.answer().kind, "granted", done.stderr)
        self.assertEqual(self.git("show", f"main:{path}").stdout,
                         "# Log\n\n## S1\nstatus: closed\n\n## S2\ntrunk's\n\n## S3\nmine\n")
        self.assertEqual(self.lines("mend"), [], "nothing was the mender's")

    def test_a_conflict_in_code_is_the_mender_s_first_and_the_gate_runs_on_what_it_left(self) -> None:
        self.mender("both")
        self.diverge()
        done = self.run_once()
        self.assertEqual(self.answer().kind, "granted", done.stderr)
        self.assertEqual(self.git("show", "main:service.txt").stdout, "one\ntrunk's\nthe slice's\n")
        self.assertEqual([(line["job"], line["paths"]) for line in self.lines("mend")], [("conflict", ["service.txt"])])
        self.assertEqual(len(self.lines("mended")), 1)

    def test_a_resolution_git_recorded_once_does_not_hide_the_conflict(self) -> None:
        """manda's checkout had `rerere` on with `autoupdate`: git staged the file from an old resolution
        and still stopped, no path was left unmerged, and the refusal was for "files git did not name"."""
        for name in ("rerere.enabled", "rerere.autoupdate"):
            self.git("config", name, "true")
        self.diverge()
        self.git("checkout", "--quiet", "main")
        self.assertNotEqual(self.git("merge", "slice/ORD-01").returncode, 0)
        (self.root / "service.txt").write_text("one\nsomebody's answer once\n", encoding="utf-8")
        self.commit("resolved by hand, which rerere records")
        self.git("reset", "--quiet", "--hard", "HEAD~1")
        self.git("checkout", "--quiet", "parked-elsewhere")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused")
        self.assertIn("service.txt", str(answer.fields["why"]))

    def test_a_failed_gate_s_refusal_carries_what_the_check_said(self) -> None:
        """S91 was told `make[1]: *** [check-decisions] Error 1`, and the check had named the decision."""
        gate = ("verify:\n\t@$(MAKE) check-decisions\ncheck-decisions:\n"
                "\t@echo 'decisions.md:2213: D444 names no Read against'; exit 1\n")
        self.slice_branch("ORD-01", "Makefile", gate)
        self.ask("ORD-01")
        self.run_once()
        why = str(self.answer().fields["why"])
        self.assertIn("the full gate failed", why)
        self.assertIn("check-decisions", why)
        self.assertIn("D444 names no Read against", why)

    def test_a_refusal_carries_the_failure_and_not_what_was_printed_round_it(self) -> None:
        """manda: a failed `test` was refused with eight lines of `npm error` and none of the test."""
        gate = ("verify:\n\t@echo 'check-benchmark: warning: S96 was never closed'\n"
                "\t@echo ' FAIL  tests/share.test.tsx > shows the sender'\n\t@echo '⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯'\n"
                "\t@echo 'npm error Lifecycle script `test` failed with error:'\n\t@echo 'npm error code 1'; exit 1\n")
        self.slice_branch("ORD-01", "Makefile", gate)
        self.ask("ORD-01")
        self.run_once()
        why = str(self.answer().fields["why"])
        self.assertIn("shows the sender", why)
        for noise in ("npm error", "⎯⎯", "warning"):
            self.assertNotIn(noise, why)

    def test_with_no_mender_to_send_the_slice_resolves_it_as_before(self) -> None:
        self.diverge()
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused")
        self.assertNotIn("mender", str(answer.fields["why"]))
        self.assertEqual(self.lines("mend"), [])

    def test_a_project_can_turn_the_session_off(self) -> None:
        self.mender("both")
        held = json.loads((self.root / "harbour.json").read_text(encoding="utf-8"))
        (self.root / "harbour.json").write_text(json.dumps({**held, "conflict_minutes": 0}), encoding="utf-8")
        self.git("checkout", "--quiet", "main")
        self.commit("no session at a conflict")
        self.diverge()
        self.run_once()
        self.assertEqual(self.answer().kind, "refused")
        self.assertEqual(self.lines("mend"), [])

    def test_a_mender_that_does_not_settle_it_leaves_the_slice_its_conflict(self) -> None:
        for what, said in (("nothing", "conflict marker"), ("strays", "other.txt"), ("aborts", "moved the rebase"),
                           ("fails", "exited 3")):
            with self.subTest(what):
                self.setUp()
                self.mender(what)
                self.diverge()
                self.run_once()
                answer = self.answer()
                self.assertEqual(answer.kind, "refused")
                self.assertIn(said, str(answer.fields["why"]))
                self.assertTrue(answer.fields["resolve"])
                self.assertEqual(self.head("main"), self.git("rev-parse", "main").stdout.strip())
                self.assertEqual(len(self.lines("mend-failed")), 1)
                self.assertEqual(self.git("worktree", "list").stdout.count("\n"), 1, "the scratch worktree is gone")


if __name__ == "__main__":
    unittest.main()
