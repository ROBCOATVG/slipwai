"""The fifth review of the captain agent: each finding held by a test that goes red without its fix.

A. A person's `told` gives a slice its runs back however it came — the MCP `tell`, `fleet.py tell` — with no
   captain agent at all, so a slice parked at its ceiling and answered is run again.
B. Nothing in the run folder stops the captain program: a file nested past any parser, a name too long for its
   result, a pipe, a link to nowhere — in orders, events, inboxes or a thread — is refused and the stream merges
   as it would with no agent; and where the agent's machinery fails outright, the stream runs on the program
   alone and the deck log says why, once.
C. A person's pause is held by its own line on the thread, however the turn then ends: after a captain's stop,
   when the session dies, when the program ends the drive; in print mode only a person's resume lifts it and
   the resume is written; a person's hold wins over a park its captain ordered, and refuses that park and a
   captain's interrupt.
E. The captain is handed the exact command to give an order with, and a command it was refused is said once.
F. A message routed once is not routed again by a captain started afresh.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Any

import checkout_packages  # noqa: F401
from test_captain_agent import SAIL, AgentBase
from test_captain_helm import HelmBase, loaded
from test_drive import AGENT
from test_drive import loaded as loaded_drive

from slipwai import logs, talk
from slipwai.mcp import a_told


class AloneTest(AgentBase):
    """A: the program alone; a person answers through the routes that write a `told` with no message behind it."""

    def alone(self) -> str:
        clean = {k: v for k, v in os.environ.items() if k not in ("SLIPWAI_ACP", "SLIPWAI_CAPTAIN", "SLIPWAI_FAIRWAY")}
        done = subprocess.run([sys.executable, str(self.script), "ORD", "--once"], cwd=self.root, capture_output=True,
                              text=True, timeout=120, env={**clean, "SLIPWAI_SAIL": self.sail(SAIL),
                                                           "SLIPWAI_CAPTAIN": "off"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout

    def answered(self, tell: Any) -> None:
        self.budget(minutes=5, attempts=0)  # one run between a person's words
        (self.root / "no-demo").write_text("", encoding="utf-8")
        self.alone()
        park = [e for e in self.read("ORD") if e.kind == "parked"][-1]
        time.sleep(1.1)  # the person's word is a second after the park, as it would be
        tell()
        self.harbour(logs.entry("cleared", harbour=True, fairway="ORD", parked=park.t, what="go again"))
        (self.root / "no-demo").unlink()
        self.granted("ORD-01")
        said = self.alone()
        self.assertIn("ORD-01 is through its gate and merged", said)

    def test_a_person_s_mcp_tell_runs_the_slice_again_with_no_agent(self) -> None:
        self.answered(lambda: a_told(self.root, {"fairway": "ORD", "message": "fixed the data, go again"}))

    def test_a_person_s_fleet_tell_runs_the_slice_again_with_no_agent(self) -> None:
        fleet = loaded(self.root, "fleet")
        self.answered(lambda: fleet.tell(["ORD"], ["fixed the data, go again"], slice_id="ORD-01"))


class FolderTest(AgentBase):
    """B: what is planted in the run folder never stops the captain program."""

    def plant_then_sail(self, plant: Any, agent: bool = True) -> str:
        self.granted("ORD-01")
        plant(logs.run_dir(self.root))
        said = self.turn("today") if agent else self.turn("today", captain="off")
        self.assertIn("ORD-01 is through its gate and merged", said)
        return said

    def refused_not_failed(self, said: str) -> None:
        """The file was refused by the reader, and the agent never failed over it: it is still the captain."""
        failed = [e for e in self.read("ORD") if e.kind == "told" and e.fields.get("by") == "captain program"]
        self.assertEqual(failed, [], said)

    def test_an_order_nested_past_any_parser(self) -> None:
        def plant(run: Any) -> None:
            (run / "orders/ORD").mkdir(parents=True, exist_ok=True)
            (run / "orders/ORD/20261116T090000Z-deep00.json").write_text("[" * 200000, encoding="utf-8")
        self.refused_not_failed(self.plant_then_sail(plant))

    def test_an_order_whose_result_name_is_too_long(self) -> None:
        def plant(run: Any) -> None:
            (run / "orders/ORD").mkdir(parents=True, exist_ok=True)
            (run / "orders/ORD" / ("x" * 245 + ".json")).write_text("{}", encoding="utf-8")
        self.refused_not_failed(self.plant_then_sail(plant))

    def test_a_pipe_named_like_an_order(self) -> None:
        def plant(run: Any) -> None:
            (run / "orders/ORD").mkdir(parents=True, exist_ok=True)
            os.mkfifo(run / "orders/ORD/20261116T090000Z-fifo00.json")
        self.refused_not_failed(self.plant_then_sail(plant))

    def test_a_closing_record_that_is_a_link_to_nowhere(self) -> None:
        def plant(run: Any) -> None:
            (run / "events/ORD").mkdir(parents=True, exist_ok=True)
            (run / "events/ORD/old.closed.json").symlink_to(run / "nowhere.json")
        self.refused_not_failed(self.plant_then_sail(plant))

    def test_an_inbox_file_and_a_thread_line_nested_past_any_parser_with_no_agent_too(self) -> None:
        def plant(run: Any) -> None:
            for home in (talk.place(run, "ORD", talk.CAPTAIN), talk.place(run, "ORD", "ORD-01")):
                (home / "inbox").mkdir(parents=True, exist_ok=True)
                (home / "inbox/20261116T090000Z-deep00.json").write_text("{" * 200000, encoding="utf-8")
                (home / "thread.jsonl").write_text("[" * 200000 + "\n", encoding="utf-8")
        for agent in (True, False):
            with self.subTest(agent=agent):
                self.setUp()
                self.plant_then_sail(plant, agent)

    def test_where_the_agent_s_machinery_fails_the_stream_runs_on_the_program_alone_and_says_so(self) -> None:
        def plant(run: Any) -> None:
            (run / "events").mkdir(parents=True, exist_ok=True)
            (run / "events/ORD").write_text("not a folder", encoding="utf-8")  # nothing can be written in it
        said = self.plant_then_sail(plant)
        failed = [e for e in self.read("ORD") if e.kind == "told" and e.fields.get("by") == "captain program"]
        self.assertEqual(len(failed), 1, said)
        self.assertIn("The captain agent failed", str(failed[0].fields["message"]))


class PauseTest(HelmBase):
    """C: a person's pause, held by its own line, through the real driver and print mode's `steered`."""

    def started(self, prompt: str) -> Any:
        drive = loaded_drive(self.root)
        home = drive.talk.place(self.root / ".slipwai", "ORD", "ORD-01")
        env = {**os.environ, "SLIPWAI_FAIRWAY": "ORD", "SLIPWAI_SLICE": "ORD-01"}
        held = drive.Drive([sys.executable, str(AGENT)], self.root, env, prompt,
                           kept=self.root / ".slipwai" / "acp" / "ORD-01", conversation=home)
        self.addCleanup(held.end)
        self.until(lambda: (self.root / ".dawdling").exists())
        return drive, home, held

    def until(self, what: Any, timeout: float = 30) -> None:
        ends = time.monotonic() + timeout
        while not what():
            self.assertLess(time.monotonic(), ends, "waited and it did not happen")
            time.sleep(0.05)

    def kinds(self, drive: Any, home: Any) -> list[str]:
        return [one["kind"] for one in drive.talk.thread(home)]

    def test_c1_a_captain_s_stop_heard_first_does_not_lose_a_person_s_pause_after_it(self) -> None:
        drive, home, held = self.started("dawdle")
        drive.talk.send(home, "stop", "stuck", by="captain:ORD")
        self.until(lambda: "stopped" in self.kinds(drive, home))  # the captain's stop is heard first
        drive.talk.send(home, "pause", "lunch")
        self.until(lambda: "pausing" in self.kinds(drive, home) or held.closed)
        (self.root / ".go").write_text("", encoding="utf-8")
        self.until(lambda: held.closed)
        self.assertEqual(drive.talk.halted(home)[:2], ("paused", "person"), self.kinds(drive, home))

    def test_c2_a_session_that_dies_with_a_person_s_pause_waiting_leaves_the_slice_paused(self) -> None:
        drive, home, held = self.started("dawdle die")
        drive.talk.send(home, "pause", "lunch")
        self.until(lambda: "pausing" in self.kinds(drive, home))
        (self.root / ".go").write_text("", encoding="utf-8")
        self.until(lambda: held.closed)
        self.assertEqual(drive.talk.halted(home)[:2], ("paused", "person"))

    def test_c3_a_drive_the_program_ends_with_a_person_s_pause_waiting_leaves_the_slice_paused(self) -> None:
        drive, home, held = self.started("dawdle")
        drive.talk.send(home, "pause", "lunch")
        self.until(lambda: "pausing" in self.kinds(drive, home))
        held.end()  # the stage bound, say
        self.assertEqual(drive.talk.halted(home)[:2], ("paused", "person"))

    def steering(self) -> tuple[Any, Any, Any]:
        (self.root / "specs/ordering").mkdir(parents=True, exist_ok=True)
        (self.root / "specs/ordering/chart.yaml").write_text("slices:\n  ORD-01: {fairway: ORD}\n", encoding="utf-8")
        captain = loaded(self.root, "captain")
        run = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(run.kill)
        return captain, captain.conversation("ORD", "ORD-01"), run

    def test_c4_in_print_mode_a_person_s_resume_lifts_their_pause_and_is_written(self) -> None:
        captain, home, run = self.steering()
        talk.send(home, "pause", "lunch")
        pausing = captain.steered(home, run, None)
        talk.send(home, "resume")
        self.assertIsNone(captain.steered(home, run, pausing))
        self.assertEqual(talk.halted(home)[0], "", [one["kind"] for one in talk.thread(home)])

    def test_c5_in_print_mode_a_captain_s_resume_does_not_lift_a_person_s_pause(self) -> None:
        captain, home, run = self.steering()
        talk.send(home, "pause", "lunch")
        pausing = captain.steered(home, run, None)
        talk.send(home, "resume", by="captain:ORD")
        self.assertIsNotNone(captain.steered(home, run, pausing))
        self.assertEqual(talk.halted(home)[:2], ("paused", "person"))

    def test_c6_a_person_s_hold_wins_over_a_park_and_refuses_it_and_a_captain_s_interrupt(self) -> None:
        captain, home, _ = self.steering()
        held = {"halted": ("paused", "person", "lunch"), "parking": "stuck for an hour"}
        self.assertEqual(captain.ended(held, False), "held")
        talk.note(home, "pausing", by="person", why="lunch")
        check = captain.stuck_check("ORD", "ORD-01")
        self.assertIn("a person holds", check({"verb": "park", "slice": "ORD-01"}, []))
        helm = self.helm(lambda h, env: self.order(h, env, "message", slice="ORD-01", text="look", interrupt=True))
        helm.decide("stuck", "ORD-01", {"slice": "ORD-01"}, ["message", "none"], [{"verb": "none", "why": "rule"}])
        self.assertEqual(self.results()[-1][0], "refused")


class CommandTest(HelmBase):
    """E and F."""

    def test_e_the_captain_is_handed_the_exact_command_and_a_refused_one_is_said_once(self) -> None:
        agent = loaded(self.root, "captain_agent")
        held = {"id": "e1", "kind": "stuck", "may": ["none"]}
        self.assertIn(agent.order_command(), agent.prompt("ORD", self.root / "e.json", self.root / "s.json", held))
        own = self.root / "scripts/agents/orders.py"
        self.assertTrue(agent.ordering({"rawInput": {"command": f"{sys.executable} {own} none --why x"}}))
        options = [{"optionId": "y", "kind": "allow_once"}, {"optionId": "n", "kind": "reject_once"}]
        for _ in range(2):
            agent.permit({"kind": "execute", "rawInput": {"command": f"python3 {own} none --why x"}}, options)
        runner = agent.Runner("ORD", self.run_dir, agent.settings({}), (["x"], None))
        said = runner.refusals()
        self.assertEqual(len(said), 1)
        self.assertIn(agent.order_command(), said[0])
        noted: list[str] = []
        self.stream.noted = noted.append  # type: ignore[attr-defined]
        helm = self.helm(lambda h, env: None)
        helm.runner.refusals = lambda: ["refused once"]
        self.choose(helm)
        self.assertEqual(noted, ["refused once"])

    def test_f_a_message_routed_once_is_not_routed_again_by_a_captain_started_afresh(self) -> None:
        asked = talk.send(talk.place(self.run_dir, "ORD", talk.CAPTAIN), "say", "use euros")
        for _ in range(2):
            helm = self.helm(lambda h, env: self.order(h, env, "message", slice="ORD-01", of=asked["id"]))
            helm.decide("message", "", {"inbox": asked["id"], "from": "person", "text": "x"}, ["message", "none"],
                        [{"verb": "none", "why": "rule"}])
        self.assertEqual([state for state, _ in self.results()], ["done", "refused"])


if __name__ == "__main__":
    import unittest
    unittest.main()
