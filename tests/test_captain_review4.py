"""The fourth review of the captain agent: each finding held by a test that goes red without its fix.

What is proved, by finding:
1. a captain slower than the last slice in flight — late, or never answering — does not hang the stream;
2. a person's pause, heard and not yet honoured, is neither lost nor taken over by a captain's stop or pause;
3. an order or message file no signature could have been made over is refused, never raised on, and what the
   loop asks in the background is always answered;
4. a person's words can be routed only by the event that put them to the captain, once, and reach the slice
   apart from the captain's own;
5. only a person's proved word resets a slice's runs: not a `decision`, not a `told` nobody can tie to a
   message a person sent;
6. a project that says nothing about `captain.answers` has a captain that answers nothing;
7. the captain session runs only this project's `orders.py` under this program's own interpreter, read from
   the real command;
8. no key file is read through a captain, and no key is said in a message;
9. a `headless_bound` left in an older `harbour.json` is read by nothing.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from typing import Any

import checkout_packages  # noqa: F401
from test_captain_abreast import Abreast
from test_captain_agent import CAPTAIN
from test_captain_helm import HelmBase, loaded
from test_drive import AGENT
from test_drive import loaded as loaded_drive

from slipwai import logs, talk


class SlowCaptainTest(Abreast):
    """Finding 1: the reviewer's repro — slots for two, three slices cleared, the captain slower than a run."""

    def sailed(self, mode: str, delay: str = "4", **env: str) -> tuple[subprocess.CompletedProcess, float]:
        self.settings(attempts=0, captain={"agent": True, "bound": 6})
        self.skeleton_merged()
        self.slots(2)
        self.granted("L02", "L03", "L04")
        began = time.monotonic()
        done = subprocess.run([sys.executable, str(self.script), "LVR", "--once"], cwd=self.root, capture_output=True,
                              text=True, timeout=90,
                              env=self.environment(ABREAST_SLEEP="2", SLIPWAI_CAPTAIN=CAPTAIN, STAND_IN_CAPTAIN=mode,
                                                   STAND_IN_DELAY=delay, **env))
        return done, time.monotonic() - began

    def test_a_captain_that_never_answers_does_not_hang_the_stream(self) -> None:
        done, took = self.sailed("silent")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertLess(took, 80)
        self.assertIn("L02", [str(e.fields["slice"]) for e in self.kinds("merged")], done.stdout)

    def test_a_choice_answered_after_the_stream_parked_does_not_hang_it(self) -> None:
        """The stream is parked — by a person, say — while a choice is with the captain: the answer, when it
        comes, finds nothing it may start, and the turn must still end."""
        self.settings(attempts=0, captain={"agent": True, "bound": 6})
        self.skeleton_merged()
        self.slots(2)
        self.granted("L02", "L03", "L04")
        captain = subprocess.Popen([sys.executable, str(self.script), "LVR", "--once"], cwd=self.root, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   env=self.environment(ABREAST_SLEEP="2", SLIPWAI_CAPTAIN=CAPTAIN,
                                                        STAND_IN_CAPTAIN="silent"))
        self.addCleanup(captain.kill)
        events = logs.run_dir(self.root) / "events" / "LVR"
        ends = time.monotonic() + 60
        while time.monotonic() < ends:
            choices = [path for path in events.glob("*.json") if path.name not in ("state.json", "captain.json")
                       and not path.name.endswith(".closed.json")
                       and not path.with_name(f"{path.stem}.closed.json").exists()]
            if choices and any(e.kind == "claimed" and e.fields.get("slice") != "L01" for e in self.read("LVR")):
                break
            time.sleep(0.1)
        self.deck("LVR", logs.entry("parked", fairway="LVR", why="the stream is parked by a person for a while"))
        try:
            said, _ = captain.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            captain.kill()
            said, _ = captain.communicate()
            self.fail(f"the turn never ended once the stream was parked with a choice out:\n{said[-2000:]}")
        self.assertEqual(captain.returncode, 0, said)

    def test_a_captain_that_answers_after_the_last_run_ended_does_not_hang_the_stream(self) -> None:
        done, took = self.sailed("late", delay="4")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertLess(took, 80)


class HoldTest(HelmBase):
    """Findings 2, 4 and 8 at the helm."""

    def stop(self, verb: str) -> list[tuple[str, str]]:
        helm = self.helm(lambda held, env: self.order(held, env, verb, slice="ORD-01", why="stuck"))
        helm.decide("stuck", "ORD-01", {"slice": "ORD-01"}, ["pause", "stop", "resume", "none"],
                    [{"verb": "none", "why": "rule"}])
        return self.results()

    def test_a_captain_cannot_stop_or_pause_over_a_person_s_pause_still_waiting_for_its_turn(self) -> None:
        home = talk.place(self.run_dir, "ORD", "ORD-01")
        talk.note(home, "pausing", by="person", why="lunch")
        for verb in ("stop", "pause"):
            self.assertEqual(self.stop(verb)[-1][0], "refused", verb)
        self.assertEqual(talk.pending(home), [], "nothing was sent")

    def test_a_captain_cannot_get_ahead_of_a_person_s_pause_still_in_the_inbox(self) -> None:
        home = talk.place(self.run_dir, "ORD", "ORD-01")
        talk.send(home, "pause", "lunch")
        self.assertEqual(self.stop("stop")[-1][0], "refused")

    def test_a_person_s_words_are_routed_only_by_the_event_that_put_them_and_once(self) -> None:
        asked = talk.send(talk.place(self.run_dir, "ORD", talk.CAPTAIN), "say", "yes, go ahead")
        helm = self.helm(lambda held, env: self.order(held, env, "message", slice="ORD-02", of=asked["id"],
                                                      text="On dropping the audit table:"))
        helm.decide("stuck", "ORD-02", {"slice": "ORD-02"}, ["message", "none"], [{"verb": "none", "why": "rule"}])
        self.assertEqual(self.results()[-1], ("refused", f"{asked['id']} is not the message this event put to "
                                                         "the captain"))
        twice = self.helm(lambda held, env: [self.order(held, env, "message", slice=one, of=asked["id"])
                                             for one in ("ORD-01", "ORD-02")])
        twice.decide("message", "", {"inbox": asked["id"], "from": "person", "text": "x"}, ["message", "none"],
                     [{"verb": "none", "why": "rule"}])
        self.assertEqual([state for state, _ in self.results()[-2:]], ["done", "refused"])

    def test_no_key_is_said_in_a_message_or_read_through_a_captain(self) -> None:
        home = talk.place(self.run_dir, "ORD", "ORD-01")
        talk.ready(self.run_dir)
        secret = talk.key(home)
        helm = self.helm(lambda held, env: self.order(held, env, "message", slice="ORD-01", text=f"k {secret.hex()}"))
        helm.decide("stuck", "ORD-01", {"slice": "ORD-01"}, ["message", "none"], [{"verb": "none", "why": "rule"}])
        self.assertIn("conversation key", self.results()[-1][1])
        events = loaded(self.root, "captain_events")
        key_file = str(self.run_dir / "talk" / ".key")
        self.assertFalse(events.readable({"root": str(self.root), "tool": {"kind": "read", "locations": [key_file]}}))
        agent = loaded(self.root, "captain_agent")
        options = [{"optionId": "y", "kind": "allow_once"}, {"optionId": "n", "kind": "reject_once"}]
        self.assertEqual(agent.permit({"kind": "read", "locations": [{"path": key_file}]}, options), "n")


class MalformedTest(HelmBase):
    """Finding 3."""

    def test_an_order_no_signature_could_be_made_over_is_refused_not_raised(self) -> None:
        def act(held: dict, env: dict) -> None:
            for ident, extra in (("aaaaaa", {"sig": "é"}), ("bbbbbb", {"text": "\ud800"})):
                body = {"v": 1, "id": f"20261116T090000Z-{ident}", "t": "2026-11-16T09:00:00Z", "event": held["id"],
                        "fairway": "ORD", "verb": "start", "slice": "ORD-02", **extra}
                (self.folder()).mkdir(parents=True, exist_ok=True)
                (self.folder() / f"{body['id']}.json").write_text(json.dumps(body), encoding="utf-8")
        chosen, by = self.choose(self.helm(act))
        self.assertEqual((chosen[0]["slice"], by), ("ORD-01", "rule"))
        self.assertEqual([state for state, _ in self.results()], ["refused", "refused"])

    def test_a_message_file_with_a_signature_no_key_makes_is_not_genuine(self) -> None:
        home = talk.place(self.run_dir, "ORD", talk.CAPTAIN)
        talk.ready(self.run_dir)
        self.assertFalse(talk.genuine(home, {"id": "x", "from": "person", "kind": "say", "sig": "é"}))

    def test_what_the_loop_asks_in_the_background_is_answered_even_when_deciding_fails(self) -> None:
        helm = self.helm(None, bound=0.3)

        def broken(*_: Any) -> Any:
            raise RuntimeError("an event that could not be written")
        helm.decide = broken
        came: list[tuple[list, str]] = []
        helm.later("choose-next", "", {}, ["start"], [{"verb": "start", "slice": "ORD-01"}],
                   lambda orders, by: came.append((orders, by))).join(timeout=5)
        self.assertEqual(came, [([{"verb": "start", "slice": "ORD-01"}], "rule")])


class RulesTest(HelmBase):
    """Findings 5, 6, 7 and 9, on the program's own functions."""

    def captain(self) -> Any:
        (self.root / "specs/ordering").mkdir(parents=True, exist_ok=True)
        (self.root / "specs/ordering/chart.yaml").write_text("slices:\n  ORD-01: {fairway: ORD}\n", encoding="utf-8")
        return loaded(self.root, "captain")

    def deck(self, *entries: logs.Entry) -> None:
        path = logs.deck_path(self.root, "ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as out:
            for entry in entries:
                out.write(entry.line())

    def test_a_decision_gives_a_slice_no_runs_back_and_a_person_s_told_does(self) -> None:
        module = self.captain()
        old, later = "2026-11-16T09:00:00Z", "2026-11-16T09:05:00Z"
        self.deck(logs.entry("dispatched", fairway="ORD", slice="ORD-01", t=old),
                  logs.entry("decision", fairway="ORD", id="Q1", what="x", slice="ORD-01",
                             decided_by="sail-decide-skipper", t=later))
        self.assertEqual(module.counted_runs("ordering", "ORD", "ORD-01"), 1, "a skipper's decision resets nothing")
        self.deck(logs.entry("told", fairway="ORD", message="carry on", by="person", slice="ORD-01",
                             t="2026-11-16T09:06:00Z"))
        self.assertEqual(module.counted_runs("ordering", "ORD", "ORD-01"), 0, "a person's word, however it came")

    def test_a_project_that_says_nothing_has_a_captain_that_answers_nothing(self) -> None:
        agent = loaded(self.root, "captain_agent")
        self.assertFalse(agent.settings({})["answers"])
        self.assertFalse(agent.settings({"captain": {"agent": True}})["answers"])
        module = self.captain()
        module.HELM = type("Helm", (), {"settings": agent.settings({"captain": {"agent": True}})})()
        self.assertNotIn("answered by this stream's captain", module.sail_prompt(None, "ORD-01", "ORD"))

    def test_the_captain_runs_only_its_own_orders_script_under_this_interpreter(self) -> None:
        agent = loaded(self.root, "captain_agent")
        own = self.root / "scripts/agents/orders.py"
        self.assertTrue(agent.ordering({"rawInput": {"command": f"{sys.executable} {own} none --why x"}}))
        evil = self.root / "python-evil"
        evil.write_text("", encoding="utf-8")
        self.assertFalse(agent.ordering({"rawInput": {"command": f"{evil} {own} none --why x"}}))
        self.assertFalse(agent.ordering({"title": f"{sys.executable} {own} none", "rawInput": {"cmd": "rm -rf /"}}))

    def test_a_headless_bound_left_in_an_older_harbour_json_is_read_by_nothing(self) -> None:
        agent = loaded(self.root, "captain_agent")
        held = agent.settings({"captain": {"agent": True, "headless_bound": 1}})
        self.assertNotIn("headless_bound", held)
        self.assertEqual(held["bound"], 60.0)


class DriverHoldTest(HelmBase):
    """Finding 2, in the slice's driver: a captain's stop meets a person's pause still waiting for the turn."""

    def test_a_person_s_pending_pause_survives_a_captain_s_stop(self) -> None:
        drive = loaded_drive(self.root)
        home = drive.talk.place(self.root / ".slipwai", "ORD", "ORD-01")
        env = {**dict(__import__("os").environ), "SLIPWAI_FAIRWAY": "ORD", "SLIPWAI_SLICE": "ORD-01"}
        held = drive.Drive([sys.executable, str(AGENT)], self.root, env, "dawdle",
                           kept=self.root / ".slipwai" / "acp" / "ORD-01", conversation=home)
        self.addCleanup(held.end)
        ends = time.monotonic() + 30
        while not (self.root / ".dawdling").exists() and time.monotonic() < ends:
            time.sleep(0.05)
        drive.talk.send(home, "pause", "lunch")
        while not any(one.get("kind") == "pausing" for one in drive.talk.thread(home)) and time.monotonic() < ends:
            time.sleep(0.05)
        stop = drive.talk.send(home, "stop", "stuck", by="captain:ORD")
        while not any(one.get("id") == stop["id"] and one.get("kind") == "failed" for one in drive.talk.thread(home)) \
                and time.monotonic() < ends:
            time.sleep(0.05)
        (self.root / ".go").write_text("", encoding="utf-8")
        while not held.closed and time.monotonic() < ends:
            time.sleep(0.05)
        self.assertEqual(held.halted, ("paused", "person", "lunch"))
        self.assertEqual(drive.talk.halted(home)[:2], ("paused", "person"))


if __name__ == "__main__":
    import unittest
    unittest.main()
