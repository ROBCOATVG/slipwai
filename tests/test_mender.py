"""The trunk mender: a red trunk stops the line and an agent is sent to fix it, and a need a slice handed back
is landed on trunk by the same agent while trunk is green (phase 25, `docs/stop-the-line-plan.md`).

game-club-manager's trunk went red at 13:49 from the scaffold's own workflow and stayed red overnight with
four slices built and waiting: the order to fix it was never written, because the reader of `merged` ran
eighteen minutes before the captain wrote the line. These cases run a real repository and a fake mender — a
script `SLIPWAI_MENDER` names, which does what its case says in the worktree it is given — so every rule
about what may land is held against git itself.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
import unittest
from typing import Any, ClassVar
from unittest import mock

import checkout_packages  # noqa: F401
from harbourmaster_fixture import AGENTS
from test_trunk import TrunkFixture, run

from slipwai import logs

#: A fake mender: `<job> <told.json>`, in the worktree it was given. `FAKE_MEND` says what it does.
FAKE = """import json, os, subprocess, sys
told = json.load(open(sys.argv[2]))
what = os.environ.get("FAKE_MEND", "fix")
if what == "fix":
    open("service.txt", "w").write("fixed\\n")
elif what == "gate":
    os.makedirs("scripts", exist_ok=True)
    open("scripts/check-x.py", "w").write("print('passed')\\n")
elif what == "need":
    open(".env.example", "a").write("DISCORD_CLIENT_ID=\\n")
if what != "nothing":
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "-c", "user.name=m", "-c", "user.email=m@local", "commit", "-qm", "mend"], check=True)
"""


class MenderFixture(TrunkFixture):
    MENDER = "on"

    def setUp(self) -> None:
        super().setUp()
        fake = self.root.parent / f"{self.root.name}-mender.py"
        fake.write_text(FAKE, encoding="utf-8")
        self.addCleanup(fake.unlink, True)
        # Run before the unlink above (cleanups run last-in, first-out): a case that ends while the fake it
        # started is still going would leave a script Windows will not delete while it runs.
        self.addCleanup(self.wait_for_mender)
        os.environ["SLIPWAI_MENDER"] = f"{sys.executable} {fake}"
        self.addCleanup(os.environ.pop, "SLIPWAI_MENDER", None)
        self.does("fix")

    def does(self, what: str) -> None:
        os.environ["FAKE_MEND"] = what
        self.addCleanup(os.environ.pop, "FAKE_MEND", None)

    @staticmethod
    def mender_alive(pid: int) -> bool:
        """The mender's own question, which asks Windows through the process handle: `os.kill(pid, 0)`
        there is `TerminateProcess`, and the suite's first Windows run failed on it."""
        return bool(WorkflowRuleTest.load().alive(pid))

    def wait_for_mender(self) -> None:
        """Until the fake mender in flight, if any, has ended.

        Waited on by pid, not `waitpid`: the mender is the exited harbourmaster's child, not this process's,
        and `waitpid` on it raises at once — which on a quick runner let the pass run before the commit."""
        import time
        record = self.root / ".slipwai/run/running/mender.json"
        if not record.is_file():
            record = self.root / ".slipwai/running/mender.json"
        pid = json.loads(record.read_text(encoding="utf-8"))["pid"] if record.is_file() else 0
        until = time.monotonic() + 30
        while pid and time.monotonic() < until:
            if not self.mender_alive(pid):
                break
            time.sleep(0.05)

    def settle(self) -> None:
        """Let the fake mender finish, then one pass to hold its branch to the rules and land it."""
        self.wait_for_mender()
        done = self.run_once()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


class RedTrunkTest(MenderFixture):
    def test_a_red_trunk_sends_the_mender_and_its_fix_lands(self) -> None:
        self.forge_says(run("failure", sha=self.head("main"), workflow="event model"))
        self.run_once()
        sent = self.of_kind("mend")
        self.assertEqual(len(sent), 1, self.kinds())
        self.assertEqual((sent[0].fields["job"], sent[0].fields["attempt"]), ("trunk", 1))
        self.assertEqual(self.of_kind("park"), [], "nobody is asked while the mender has attempts left")
        self.settle()
        mended = self.of_kind("mended")
        self.assertEqual(len(mended), 1, self.kinds())
        self.assertEqual(self.git("show", "main:service.txt").stdout, "fixed\n")

    def test_the_grant_names_who_broke_it_before_the_captain_writes_merged(self) -> None:
        """CL1 was granted at 13:48:55 and its `merged` came at 14:06; the order has to go in between."""
        self.ask_to_merge("ORD-01")
        self.forge_says(run("success", sha=self.head("main")))
        self.run_once()
        granted = self.of_kind("granted")[0]
        self.assertTrue(granted.fields.get("onto"), "the grant says what it landed on, for a revert")
        self.forge_says(run("failure", sha=str(granted.fields["commit"])))
        self.run_once()
        self.assertEqual(self.of_kind("mend")[0].fields.get("slice"), "ORD-01", self.kinds())

    def test_a_mend_that_touches_a_gate_is_refused_and_parks_once_attempts_are_spent(self) -> None:
        self.does("gate")
        self.forge_says(run("failure", sha=self.head("main")))
        self.harbour_config(ci=self.ci, attempts=2)
        for _ in range(3):
            self.settle()
        failed = self.of_kind("mend-failed")
        self.assertEqual(len(failed), 2, self.kinds())
        self.assertIn("never the mender's", str(failed[0].fields["why"]))
        self.assertEqual(self.git("show", "main:scripts/check-x.py").returncode, 128, "nothing landed")
        parked = [e for e in self.of_kind("park") if e.fields.get("mend")]
        self.assertEqual(len(parked), 1, self.kinds())
        self.settle()
        self.assertEqual(len(self.of_kind("mend")), 2, "a spent red sends nobody again")

    def test_a_mender_that_commits_nothing_is_a_failed_attempt(self) -> None:
        self.does("nothing")
        self.forge_says(run("failure", sha=self.head("main")))
        self.run_once()
        self.settle()
        self.assertIn("without committing", str(self.of_kind("mend-failed")[0].fields["why"]))

    def test_mender_off_parks_a_red_for_a_person_at_once(self) -> None:
        self.forge_says(run("failure"))
        self.harbour_config(ci=self.ci, mender="off")
        self.run_once()
        self.assertEqual(self.of_kind("mend"), [])
        self.assertIn("mender: off", str(self.of_kind("park")[0].fields["why"]))

    def forge_says(self, *runs: dict) -> None:
        super().forge_says(*runs)
        self.ci = json.loads((self.root / "harbour.json").read_text(encoding="utf-8"))["ci"]


class NeedTest(MenderFixture):
    def told_a_need(self, by: str = "fleet") -> None:
        need = {"what": "land the sign-in lines", "by": by,
                "check": {"kind": "text", "path": ".env.example", "has": "DISCORD_CLIENT_ID="}}
        self.deck("ordering", "ORD", logs.entry("told", fairway="ORD", slice="ORD-01", by="session",
                                                message="ORD-01 needs its lines on main", needs=[need]))

    def test_a_fleet_need_on_a_shared_surface_is_landed_and_then_ticked(self) -> None:
        self.does("need")
        self.forge_says(run("success", sha=self.head("main")))
        self.told_a_need()
        self.run_once()
        self.assertEqual(self.of_kind("mend")[0].fields["job"], "need", self.kinds())
        self.settle()
        self.assertEqual(len(self.of_kind("mended")), 1, self.kinds())
        self.run_once()
        self.assertEqual(len(self.of_kind("told-met")), 1, self.kinds())

    def test_a_need_that_landed_is_not_sent_a_second_mender(self) -> None:
        """Its tick is written a pass after it lands, and until then it read as open: every landed need
        got a second attempt that found nothing to do and was recorded as a failure."""
        self.does("need")
        self.forge_says(run("success", sha=self.head("main")))
        self.told_a_need()
        self.run_once()
        self.settle()
        self.run_once()
        self.run_once()
        self.assertEqual((len(self.of_kind("mend")), len(self.of_kind("mended")), self.of_kind("mend-failed")),
                         (1, 1, []), self.kinds())

    def test_a_landed_branch_is_deleted_and_the_next_hand_back_s_first_need_starts(self) -> None:
        """`clubs-0` was three needs, one per hand-back. The first one's branch outlived its landing —
        git will not delete a branch its worktree still holds — and the other two could never start."""
        self.does("need")
        self.forge_says(run("success", sha=self.head("main")))
        self.told_a_need()
        self.run_once()
        self.settle()
        branches = subprocess.run(["git", "branch", "--list", "mend/*"], cwd=self.root, capture_output=True,
                                  text=True, check=True).stdout
        self.assertEqual(branches.strip(), "", "a landed mend's branch is only a second name for trunk")
        self.run_once()
        time.sleep(1.1)  # a hand-back is named by its second
        need = {"what": "land the flag line", "by": "fleet",
                "check": {"kind": "text", "path": ".env.example", "has": "VITE_FLAG_JOIN="}}
        self.deck("ordering", "ORD", logs.entry("told", fairway="ORD", slice="ORD-02", by="session",
                                                message="ORD-02 needs its flag on main", needs=[need]))
        self.run_once()
        self.assertEqual(len(self.of_kind("mend")), 2, self.kinds())
        self.assertNotIn("no worktree could be made", " ".join(str(e.fields.get("why", ""))
                                                                for e in self.of_kind("mend-failed")))

    def test_a_persons_need_waits_for_the_person_outside_cruise(self) -> None:
        self.forge_says(run("success", sha=self.head("main")))
        self.told_a_need(by="person")
        self.run_once()
        self.assertEqual(self.of_kind("mend"), [])


class SharedSurfaceTest(unittest.TestCase):
    """Which hand-backs the mender may land: anything a slice may not write, but for four things."""

    def setUp(self) -> None:
        self.mender = WorkflowRuleTest.load()

    def need(self, path: str, by: str = "fleet") -> dict:
        return {"what": "x", "by": by, "check": {"kind": "text", "path": path, "has": "x"}}

    def test_the_local_services_own_files_are_shared(self) -> None:
        """lean-coffee-club's MT1 stood parked for eighteen hours on a client missing from the local realm."""
        self.assertEqual(self.mender.eligible(self.need("docker/keycloak/realms/app.json"), False),
                         "docker/keycloak/realms/app.json")

    def test_what_lean_coffee_club_s_slices_handed_back_and_nobody_could_land(self) -> None:
        """Sixteen needs stood on its board for a person after two days, because the list of places a need
        might land was six entries long and these were not on it."""
        for path in ("docker-compose.yml", "fairways/invitations/careen.md", "apps/club/pom.xml",
                     "infra/service/flags.auto.tfvars", "skills/run-the-app/SKILL.md", "package.json",
                     ".env.example", "docs/design.md", "specs/001-meetings/mockups/board.html"):
            with self.subTest(path=path):
                self.assertEqual(self.mender.eligible(self.need(path), False), path)

    def test_a_gate_the_cloud_and_a_slice_s_own_work_are_not(self) -> None:
        for path in ("Makefile", "scripts/check-flags.py", "scripts/agents/try_it.py", "harbour.json",
                     ".github/workflows/verify.yml", "skills/tdd/SKILL.md", "agents/sail-review-mate.md",
                     "infra/service/main.tf", "infra/platform/network.tf",
                     "apps/club/src/main/java/Wiring.java", "apps/web/tests/Board.test.tsx",
                     "specs/001-meetings/slices/MT1/plan.md"):
            with self.subTest(path=path):
                self.assertEqual(self.mender.eligible(self.need(path), False), "")

    def test_a_need_s_branch_is_held_to_the_same_places(self) -> None:
        with mock.patch.object(self.mender, "changed", return_value=["fairways/meetings/careen.md"]):
            self.assertEqual(self.mender.refusal("need", "a", "b", [], "fairways/meetings/careen.md"), "")
        with mock.patch.object(self.mender, "changed", return_value=["skills/run-the-app/SKILL.md"]):
            self.assertEqual(self.mender.refusal("need", "a", "b", [], "skills/run-the-app/SKILL.md"), "")
        with mock.patch.object(self.mender, "changed", return_value=["docs/x.md", "infra/service/main.tf"]):
            self.assertIn("the cloud is a person's", self.mender.refusal("need", "a", "b", [], "docs/x.md"))
        with mock.patch.object(self.mender, "changed", return_value=["docs/x.md", "Makefile"]):
            self.assertIn("never the mender's", self.mender.refusal("need", "a", "b", [], "docs/x.md"))
        with mock.patch.object(self.mender, "changed", return_value=["skills/run-the-app/SKILL.md"]):
            self.assertIn("never the mender's", self.mender.refusal("trunk", "a", "b", []),
                          "a red trunk is not mended in a skill")

    def test_a_person_s_need_is_taken_only_under_cruise(self) -> None:
        self.assertEqual(self.mender.eligible(self.need("docker/x.json", by="person"), False), "")
        self.assertEqual(self.mender.eligible(self.need("docker/x.json", by="person"), True), "docker/x.json")


class WorkflowRuleTest(unittest.TestCase):
    """A workflow is the mender's only to move an action's `uses:` to another ref of the same action."""

    mender: ClassVar[Any]

    @staticmethod
    def load() -> Any:
        sys.path.insert(0, str(AGENTS))
        spec = importlib.util.spec_from_file_location("mender_rule", AGENTS / "mender.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @classmethod
    def setUpClass(cls) -> None:
        cls.mender = cls.load()

    def refused(self, *lines: str) -> str:
        return self.mender.workflow_refusal("\n".join(lines), ".github/workflows/x.yml")

    def test_moving_an_action_to_another_ref_is_allowed(self) -> None:
        self.assertEqual(self.refused("-      - uses: actions/upload-artifact@v3",
                                      "+      - uses: actions/upload-artifact@v4"), "")

    def test_swapping_the_action_is_refused(self) -> None:
        self.assertIn("not one action", self.refused("-  - uses: actions/upload-artifact@v3",
                                                     "+  - uses: someone/else@v1"))

    def test_removing_a_step_is_refused(self) -> None:
        self.assertIn("more than an action's ref", self.refused("-      - run: make audit"))

    def test_skipping_a_step_is_refused(self) -> None:
        self.assertIn("more than", self.refused("+        if: false"))
        self.assertIn("not one action", self.refused("-  - run: make audit", "+  - run: true"))


if __name__ == "__main__":
    unittest.main()
