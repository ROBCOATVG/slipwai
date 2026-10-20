"""The harbourmaster: what reaches the harbour log, which berth a fairway gets, and what is never done.

It runs inside a generated project, so it is run here the way a project runs it — as a script, against a
directory laid out the way a project is — rather than imported into the keel's process.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

import checkout_packages  # noqa: F401
from harbourmaster_fixture import Fixture, MergeFixture, TravelFixture  # noqa: F401

from slipwai import logs


class ClearParkTest(Fixture):
    def test_the_harbourmaster_records_a_specific_answer_once_and_refuses_a_wrong_timestamp(self) -> None:
        at = "2026-10-12T09:00:00Z"
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", why="decide", t=at))
        command = [sys.executable, str(self.script), "--clear", "ORD", "--parked", at,
                   "--what", "keep the existing store", "--once", "--no-fetch"]
        for _ in range(2):
            done = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        receipts = [entry for entry in self.harbour() if entry.kind == "cleared"]
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].fields, {"fairway": "ORD", "parked": at, "what": "keep the existing store"})
        command[command.index(at)] = "2026-10-12T08:00:00Z"
        wrong = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(wrong.returncode, 0)
        self.assertIn("Run `slipwai fleet ORD`", wrong.stdout)


class ToldAfterParkTest(Fixture):
    """A person answers a park by telling the stream something, from the board or `/cruise-tell`."""

    def test_a_message_after_a_park_clears_it_with_the_message_as_the_answer(self) -> None:
        parked, told = "2026-10-12T09:00:00Z", "2026-10-12T10:00:00Z"
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", why="decide", t=parked),
                  logs.entry("told", fairway="ORD", message="go", t=told, by="person"))
        for _ in range(2):
            done = self.run_once()
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        receipts = [entry for entry in self.harbour() if entry.kind == "cleared"]
        self.assertEqual([receipt.fields for receipt in receipts], [{"fairway": "ORD", "parked": parked, "what": "go"}])

    def test_every_park_the_message_came_after_is_cleared_and_none_it_came_before(self) -> None:
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", why="first", t="2026-10-12T09:00:00Z"),
                  logs.entry("parked", fairway="ORD", why="second", t="2026-10-12T09:01:00Z"),
                  logs.entry("told", fairway="ORD", message="fixed trunk", t="2026-10-12T10:00:00Z",
                             by="person"),
                  logs.entry("parked", fairway="ORD", why="third", t="2026-10-12T11:00:00Z"))
        self.run_once()
        cleared = sorted(str(entry.fields["parked"]) for entry in self.harbour() if entry.kind == "cleared")
        self.assertEqual(cleared, ["2026-10-12T09:00:00Z", "2026-10-12T09:01:00Z"])

    def test_a_message_from_before_the_park_answers_nothing(self) -> None:
        self.deck("ordering", "ORD", logs.entry("told", fairway="ORD", message="go", t="2026-10-12T08:00:00Z",
                                                by="person"),
                  logs.entry("parked", fairway="ORD", why="decide", t="2026-10-12T09:00:00Z"))
        self.run_once()
        self.assertEqual([entry for entry in self.harbour() if entry.kind == "cleared"], [])


class PerMachineTest(Fixture):
    """One harbourmaster per machine: it writes its own file and reads everybody's.

    Not an elected writer, which needs an election, and not three writers on one file, which breaks the
    rule the whole log design rests on. The same answer the deck logs already use, one step out.
    """

    def run_as(self, machine: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), "--once", "--no-fetch"],
                              capture_output=True, text=True, cwd=self.root,
                              env={**os.environ, "SLIPWAI_MACHINE": machine})

    def test_it_writes_its_own_machine_s_log_and_no_other_file(self) -> None:
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.run_as("harbour_one")
        self.assertEqual([path.name for path in logs.harbour_logs(self.root)], ["harbour_one.jsonl"])

    def test_three_machines_write_three_logs_that_read_as_one(self) -> None:
        for index, machine in enumerate(("harbour_one", "harbour_two", "harbour_three")):
            self.deck(f"feature{index}", f"F{index}",
                      logs.entry("mark-set", fairway=f"F{index}", slice=f"F{index}-01", mark=f"M{index}"))
            self.run_as(machine)
        self.assertEqual(len(logs.harbour_logs(self.root)), 3)
        marks = sorted(str(e.fields["mark"]) for e in self.harbour() if e.kind == "mark-set")
        self.assertEqual(marks, ["M0", "M1", "M2"])

    def test_a_second_machine_does_not_re_carry_what_the_first_already_did(self) -> None:
        """The cursors are this machine's bookmark into somebody else's file, which is what they always
        were — the harbour log it writes into is the thing that changed, not what it reads."""
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.run_as("harbour_one")
        self.run_as("harbour_one")
        self.assertEqual(len([e for e in self.harbour() if e.kind == "mark-set"]), 1)

    def test_a_berth_index_is_counted_from_this_machine_s_own_allocations(self) -> None:
        """Berths are local: the ports are this machine's and the database carries its name, so a machine
        that skipped the indices another had taken would leave ports nobody is using behind berths nobody
        has, for a collision that cannot happen."""
        self.deck("ordering", "ORD", logs.entry("berth-request", fairway="ORD"))
        self.run_as("harbour_one")
        self.deck("billing", "BIL", logs.entry("berth-request", fairway="BIL"))
        self.run_as("harbour_two")
        allocated = [str(e.fields["berth"]) for e in self.harbour() if e.kind == "berth-allocated"]
        self.assertEqual(sorted(allocated), ["bil", "ord"])


class HarbourTest(Fixture):
    def test_two_captains_marks_reach_each_other_through_the_harbour_log(self) -> None:
        """The slice's whole point: a fairway reads one file, not every other fairway's."""
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.deck("billing", "BIL", logs.entry("mark-set", fairway="BIL", slice="BIL-01", mark="Charged"))
        self.assertEqual(self.run_once().returncode, 0)
        marks = [(e.fields["fairway"], e.fields["mark"]) for e in self.harbour() if e.kind == "mark-set"]
        self.assertEqual(sorted(marks), [("BIL", "Charged"), ("ORD", "Placed")])

    def test_a_line_no_other_fairway_needs_stays_in_its_own_log(self) -> None:
        """The harbour log is read on every turn by every captain: a line nobody needs is one everybody pays for."""
        self.deck("ordering", "ORD", logs.entry("heartbeat", fairway="ORD"),
                  logs.entry("told", fairway="ORD", message="anything"))
        self.run_once()
        self.assertEqual(self.harbour(), [])

    def test_a_park_is_carried_because_it_is_what_a_sibling_waits_on(self) -> None:
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", why="the gate stayed red"))
        self.run_once()
        parks = [e for e in self.harbour() if e.kind == "park"]
        self.assertEqual(parks[0].fields["why"], "the gate stayed red")

    def test_a_second_pass_carries_nothing_twice(self) -> None:
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.run_once()
        self.run_once()
        self.assertEqual(len([e for e in self.harbour() if e.kind == "mark-set"]), 1)

    def test_a_line_written_after_a_pass_is_carried_by_the_next(self) -> None:
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.run_once()
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-02", mark="Paid"))
        self.run_once()
        self.assertEqual(len([e for e in self.harbour() if e.kind == "mark-set"]), 2)

    def test_one_fairway_writing_a_bad_line_does_not_stop_the_others_being_heard(self) -> None:
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        (self.root / logs.deck_path("billing", "BIL")).parent.mkdir(parents=True, exist_ok=True)
        (self.root / logs.deck_path("billing", "BIL")).write_text("not json\n", encoding="utf-8")
        done = self.run_once()
        self.assertEqual(done.returncode, 0)
        self.assertIn("cannot be read", done.stderr)
        self.assertEqual(len([e for e in self.harbour() if e.kind == "mark-set"]), 1)


class BerthTest(Fixture):
    def test_a_request_is_answered_with_an_allocation(self) -> None:
        self.deck("ordering", "ORD", logs.entry("berth-request", fairway="ORD"))
        self.run_once()
        found = [e for e in self.harbour() if e.kind == "berth-allocated"]
        self.assertEqual(found[0].fields["fairway"], "ORD")
        self.assertEqual(found[0].fields["berth"], "ord")

    def test_two_fairways_never_get_one_block(self) -> None:
        from slipwai.berths import allocate, collisions
        self.deck("ordering", "ORD", logs.entry("berth-request", fairway="ORD"))
        self.deck("billing", "BIL", logs.entry("berth-request", fairway="BIL"))
        self.run_once()
        names = [str(e.fields["berth"]) for e in self.harbour() if e.kind == "berth-allocated"]
        self.assertEqual(len(set(names)), 2)
        self.assertEqual(collisions(allocate(names, logs.machine())), [])

    def test_a_restart_does_not_allocate_a_block_twice(self) -> None:
        """The cursor is a bookmark; what was allocated is read back out of the harbour log itself."""
        self.deck("ordering", "ORD", logs.entry("berth-request", fairway="ORD"))
        self.run_once()
        (self.root / ".slipwai/harbourmaster.json").unlink()
        self.deck("billing", "BIL", logs.entry("berth-request", fairway="BIL"))
        self.run_once()
        names = [str(e.fields["berth"]) for e in self.harbour() if e.kind == "berth-allocated"]
        self.assertEqual(sorted(set(names)), ["bil", "ord"])


class RequestTest(Fixture):
    def ask(self, detail: str, what: str = "push") -> list[logs.Entry]:
        self.deck("ordering", "ORD",
                  logs.entry("request", fairway="ORD", id="r1", what=what, detail=detail))
        self.run_once()
        return [e for e in self.harbour() if e.kind in ("granted", "refused")]

    def test_an_ordinary_push_is_granted(self) -> None:
        found = self.ask("git push --force-with-lease=refs/heads/slice/ORD-01: origin HEAD:main")
        self.assertEqual(found[0].kind, "granted")

    def test_a_plain_force_push_is_refused_saying_what_it_would_do(self) -> None:
        found = self.ask("git push --force origin main")
        self.assertEqual(found[0].kind, "refused")
        self.assertIn("discards somebody's commits", str(found[0].fields["why"]))

    def test_every_never_is_refused_and_says_which_rule(self) -> None:
        for detail, expected in (("git reset --hard origin/main", "not yours to discard"),
                                 ("drop table orders", "destroys data"),
                                 ("rm -rf /var/data", "destroys data"),
                                 ("git filter-branch --all", "rewrites history"),
                                 ("AWS_SECRET=abc123 deploy", "secret"),
                                 ("curl --disable-tls-verification https://x", "weakens security"),
                                 ("git commit --no-verify", "skips the gate")):
            with self.subTest(detail=detail):
                self.setUp()
                found = self.ask(detail)
                self.assertEqual(found[0].kind, "refused", detail)
                self.assertIn(expected, str(found[0].fields["why"]))

    def test_an_action_nobody_wrote_down_is_refused_with_the_list(self) -> None:
        found = self.ask("anything at all", what="rewrite-history")
        self.assertEqual(found[0].kind, "refused")
        self.assertIn("push, merge, deploy, flag, publish", str(found[0].fields["why"]))

    def test_a_refusal_is_always_written_so_nobody_waits_on_silence(self) -> None:
        self.assertEqual(len(self.ask("git push --force origin main")), 1)


if __name__ == "__main__":
    unittest.main()


class CursorTest(Fixture):
    """A cursor that outlives its log. Found by the end-to-end suite, where one test's logs were wiped
    and the next pass carried nothing while reporting that it ran."""

    def test_a_log_shorter_than_the_cursor_is_read_from_the_start(self) -> None:
        """A fresh clone, a reset, a rotated log — and keeping the cursor means that stream is never
        carried again, for ever, with nothing saying so."""
        self.deck("ordering", "ORD",
                  logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"),
                  logs.entry("heartbeat", fairway="ORD"),
                  logs.entry("heartbeat", fairway="ORD"))
        self.run_once()
        (self.root / logs.deck_path("ordering", "ORD")).write_text("", encoding="utf-8")
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-02", mark="Paid"))
        done = self.run_once()
        self.assertIn("shorter than it was", done.stderr)
        self.assertIn("Paid", [str(e.fields.get("mark")) for e in self.harbour()])

    def test_an_unchanged_log_is_still_not_carried_twice(self) -> None:
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.run_once()
        self.run_once()
        self.assertEqual(len([e for e in self.harbour() if e.kind == "mark-set"]), 1)


class TravelTest(TravelFixture):
    """What leaves this machine on a pass, and what arrives.

    Section 14's fourth broken link: both this process and the captain fetched `refs/slipwai/logs/*` and
    neither ever wrote them, so a second machine saw nothing the first did. This is the pass that writes
    them — and the shape is one ref per writer, so a harbour log travels under its machine's name and a
    deck log under its fairway's, and this machine pushes only what it is the writer of.
    """

    def claim(self, fairway: str, machine: str) -> None:
        subprocess.run([sys.executable, str(self.root / "scripts/agents/claims.py"), "--take", fairway],
                       capture_output=True, text=True, cwd=self.root,
                       env={**os.environ, "SLIPWAI_MACHINE": machine}, check=True)

    def test_this_machines_harbour_log_leaves_on_its_own_ref(self) -> None:
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.run_as("harbour_one")
        self.assertIn("refs/slipwai/logs/harbour/harbour_one", self.refs("refs/slipwai/logs"))
        self.assertIn("Placed", self.carried("refs/slipwai/logs/harbour/harbour_one"))

    def test_a_deck_log_leaves_only_where_this_machine_holds_the_fairway(self) -> None:
        """One ref per writer is the whole rule, and the writer of a fairway's deck log is whichever
        captain holds the claim. A machine pushing a fairway it does not hold is a second writer."""
        self.claim("ORD", "harbour_one")
        self.deck("ordering", "ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        self.deck("billing", "BIL", logs.entry("claimed", fairway="BIL", slice="BIL-01"))
        self.run_as("harbour_one")
        self.assertIn("refs/slipwai/logs/ORD", self.refs("refs/slipwai/logs"))
        self.assertNotIn("refs/slipwai/logs/BIL", self.refs("refs/slipwai/logs"))
        self.assertIn("ORD-01", self.carried("refs/slipwai/logs/ORD"))

    def test_the_in_flight_branch_leaves_with_it(self) -> None:
        """A captain holds no credential, so a slice branch lives only on the machine that built it — and
        a lapsed claim would leave the work not merely unclaimed but unreachable."""
        self.claim("ORD", "harbour_one")
        self.deck("ordering", "ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        self.git("checkout", "--quiet", "-b", "slice/ORD-01")
        (self.root / "rungs.txt").write_text("one\ntwo\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "four rungs in")
        made = self.git("rev-parse", "HEAD").stdout.strip()
        self.run_as("harbour_one")
        self.assertEqual(self.refs("refs/slipwai/wip"), ["refs/slipwai/wip/ORD"])
        self.assertEqual(self.git("rev-parse", "refs/slipwai/wip/ORD", where=self.forge).stdout.strip(),
                         made)

    def test_a_slice_that_has_merged_leaves_no_in_flight_branch_behind(self) -> None:
        """What travels is work that is still in flight. A merged slice's branch is in trunk, and pushing
        it every pass afterwards would be a ref nobody reads growing for ever."""
        self.claim("ORD", "harbour_one")
        self.deck("ordering", "ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc1234"))
        self.git("checkout", "--quiet", "-b", "slice/ORD-01")
        self.run_as("harbour_one")
        self.assertEqual(self.refs("refs/slipwai/wip"), [])

    def test_another_machines_harbour_log_arrives_as_its_own_file(self) -> None:
        """One file per machine, folded on read — which is what 11.3 built the directory for, and this is
        what finally puts a second machine's file in it without a person carrying it."""
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.run_as("harbour_one")
        elsewhere = self.root / ".slipwai/logs/harbour/harbour_one.jsonl"
        was = elsewhere.read_text(encoding="utf-8")
        elsewhere.unlink()
        self.run_as("harbour_two")
        self.assertEqual(elsewhere.read_text(encoding="utf-8"), was)
        self.assertIn("Placed", [str(e.fields.get("mark", "")) for e in self.harbour()])

    def test_a_harbour_with_nothing_to_push_to_says_nothing_and_carries_on(self) -> None:
        """A harbour on one machine with no forge is the case that has to keep working with no network at
        all, and it is also the common one."""
        self.git("remote", "remove", "origin")
        self.deck("ordering", "ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        done = self.run_as("harbour_one")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("Placed", [str(e.fields.get("mark", "")) for e in self.harbour()])
