"""Every order a captain gives, through the real captain program, to the deck lines it leaves.

A crash survived six reviews because no test ran the order that caused it through `captain.py`: each piece was
proved alone. Here each event kind a captain is woken for is raised the way a run raises it, the stand-in
captain (`fixtures/captain_stand_in.py`, mode `script`) gives the orders a case lists through `orders.py`, and
the case reads what the program did — the deck log, the conversations, the results — and that the deck still
folds. Where `STAND_IN_ASKS=1`, the stand-in asks permission for every order it runs, as an agent does, so
the captain session's own policy (`captain_agent.permit`) is in the loop.
"""
# budget: 450 — every event kind and every order verb through one real program, in one place a reader can scan
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import checkout_packages  # noqa: F401
from test_captain_agent import CAPTAIN, SAIL, AgentBase
from test_drive import STAND_IN

from slipwai import logs, talk

#: The words a captain would quote from a gate's `why`, each of which the policy once refused unquoted.
PROSE = "the third run failed the same way; read `demo` — $0.01, draft -> sent, yes|no, it's (a) [b] *c? #d"


class Through(AgentBase):
    def go(self, script: dict, *argv: str, acp: bool = False, timeout: float = 150, once: str = "",
           **env: str) -> str:
        """One run of the captain program with the scripted stand-in captain; what it printed."""
        self.log = self.root / "script.log"
        clean = {key: value for key, value in os.environ.items()
                 if key not in ("SLIPWAI_ACP", "SLIPWAI_CAPTAIN", "SLIPWAI_SAIL")}
        environment = {**clean, "SLIPWAI_CAPTAIN": CAPTAIN, "STAND_IN_CAPTAIN": "script",
                       "SCRIPT": json.dumps(script), "SCRIPT_LOG": str(self.log), "SCRIPT_ONCE": once, **env}
        environment.update({"SLIPWAI_ACP": STAND_IN} if acp else {"SLIPWAI_SAIL": self.sail(SAIL)})
        done = subprocess.run([sys.executable, str(self.script), "ORD", *(argv or ("--once",))], cwd=self.root,
                              capture_output=True, text=True, timeout=timeout, env=environment)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.read("ORD")  # the deck still folds, whatever was ordered
        return done.stdout + done.stderr

    def given(self) -> list[dict]:
        """What the stand-in ran, and how each order came out."""
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()
                if '"order"' in line] if self.log.is_file() else []

    def lines(self, kind: str) -> list[dict]:
        return [dict(e.fields) for e in self.read("ORD") if e.kind == kind]

    def thread(self, slice_id: str) -> list[dict]:
        return talk.thread(talk.place(logs.run_dir(self.root), "ORD", slice_id))


class PolicyInTheLoopTest(Through):
    """H1: the captain session's policy parses an order command as a shell would, and refuses only what a shell
    would read as more than words."""

    def test_an_order_whose_prose_holds_punctuation_is_allowed_when_single_quoted_and_carried_out(self) -> None:
        (self.root / "no-demo").write_text("", encoding="utf-8")
        self.budget(minutes=5, attempts=0)
        self.settings(bound=20)
        said = self.go({"gate-failed": [{"verb": "park", "slice": "$slice", "why": PROSE, "needs": "a person's look"}]},
                       acp=False, STAND_IN_ASKS="1")
        self.assertEqual([(one["order"]["verb"], one["exit"]) for one in self.given()], [("start", 0), ("park", 0)],
                         said)
        parked = self.lines("parked")
        self.assertEqual([str(one.get("why")) for one in parked], [f"ORD-01: {PROSE}"], said)
        self.assertIn("a person's look", json.dumps(parked[0].get("needs")))
        self.assertEqual(self.lines("noted"), [], "nothing was refused")

    def test_a_command_a_shell_would_read_as_more_than_words_is_refused_and_the_noted_line_says_why(self) -> None:
        self.granted("ORD-01")
        attempts = ["start ORD-01 ; touch pwned", "start ORD-01 && touch pwned", 'say --text "$(touch pwned)"',
                    "say --text x\ntouch pwned", "start ORD-01 --event x | touch pwned"]
        said = self.go({"choose-next": [{"verb": "start", "raw": raw} for raw in attempts]}, STAND_IN_ASKS="1")
        self.assertFalse((self.root / "pwned").exists(), said)
        self.assertEqual([one["out"] for one in self.given()], ["refused permission"] * len(attempts))
        noted = [str(one.get("what")) for one in self.lines("noted")]
        self.assertEqual(len(noted), 1, noted)
        self.assertIn("refused 5 commands", noted[0])
        self.assertIn("for a `;` outside quotes", noted[0])
        self.assertIn("`<order command> start ORD-01 ; touch pwned`", noted[0], "what it added, not two paths")
        self.assertIn("single quotes", noted[0])
        self.assertEqual([one["by"] for one in self.closed()], ["rule"])
        self.assertIn("ORD-01 is through its gate and merged", said, "the rule decided instead")


class StuckTest(Through):
    """A `stuck` event raised by `look_stuck` from a slice going in circles, its turn lingering over the protocol
    until the stage's silence bound ends it, and each order a captain may give for it."""

    def stuck(self, orders: list[dict], minutes: float = 0.4) -> str:
        self.granted("ORD-01", "ORD-02", "ORD-03")
        self.budget(minutes=minutes, attempts=1)
        self.settings(bound=20)
        (self.root / ".linger").write_text("", encoding="utf-8")
        place = logs.run_dir(self.root) / "activity" / "ORD"
        place.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        (place / "ORD-01.jsonl").write_text("".join(json.dumps({"t": stamp, "kind": "failed", "what": "make test"})
                                                    + "\n" for _ in range(3)), encoding="utf-8")
        return self.go({"stuck": orders}, acp=True, timeout=150, once="stuck")

    def woken(self, kind: str) -> list[dict]:
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()
                if json.loads(line).get("woken") == kind]

    def test_park_with_needs_ends_the_slice_and_its_park_carries_the_needs(self) -> None:
        said = self.stuck([{"verb": "park", "slice": "$slice", "why": "it is going in circles",
                            "needs": "a person looks at make test"}])
        self.assertTrue(self.woken("stuck"), said)
        parked = [one for one in self.lines("parked") if "going in circles" in str(one.get("why"))]
        self.assertEqual(len(parked), 1, said)
        self.assertEqual(parked[0].get("cause"), "other")
        self.assertEqual([need.get("what") for need in parked[0].get("needs") or []], ["a person looks at make test"],
                         "L1: the needs a captain's park names are carried on the park")
        self.assertNotIn("ORD-01", [one.get("slice") for one in self.lines("merged")])
        self.assertIn(("done", "carried out"), [(one["state"], one.get("carried")) for one in self.results()],
                      "L2: the park was carried out, and its result says so")

    def test_a_captain_s_pause_holds_the_slice_even_when_the_bound_ends_the_turn_it_waited_for(self) -> None:
        said = self.stuck([{"verb": "pause", "slice": "$slice", "why": "going in circles; I will look"}])
        self.assertTrue(self.woken("stuck"), said)
        self.assertNotIn("ORD-01", [one.get("slice") for one in self.lines("merged")], said)
        stopped = [one for one in self.lines("stopped") if one.get("slice") == "ORD-01"]
        self.assertEqual([(one.get("by"), one.get("paused")) for one in stopped], [("captain:ORD", True)], said)
        home = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")
        self.assertEqual(talk.halted(home)[:2], ("paused", "captain:ORD"))
        self.assertIn("paused", [one["kind"] for one in talk.thread(home)])
        dispatched = [one for one in self.lines("dispatched") if one.get("slice") == "ORD-01"]
        self.go({}, acp=True, timeout=90)
        self.assertEqual([one for one in self.lines("dispatched") if one.get("slice") == "ORD-01"], dispatched,
                         "17a: no rule lifts a captain's pause; the next turn does not run the slice")
        receipts = [one for one in self.results() if one.get("state") != "refused"]
        self.assertTrue(receipts)

    def test_stop_ends_the_turn_and_puts_the_slice_back_in_the_queue(self) -> None:
        said = self.stuck([{"verb": "stop", "slice": "$slice", "why": "going in circles"}])
        stopped = [one for one in self.lines("stopped") if one.get("slice") == "ORD-01"]
        self.assertEqual([(one.get("by"), one.get("paused")) for one in stopped], [("captain:ORD", None)], said)
        self.assertEqual(talk.halted(talk.place(logs.run_dir(self.root), "ORD", "ORD-01"))[0], "",
                         "a captain's stop holds nothing past this turn")

    def test_an_interrupting_message_and_a_say_reach_the_slice_and_the_person(self) -> None:
        said = self.stuck([{"verb": "message", "slice": "$slice", "text": "stop running make test, read the failure",
                            "interrupt": True}, {"verb": "say", "text": "nudged ORD-01"}])
        lines = self.thread("ORD-01")
        delivered = [one for one in lines if one["kind"] == "delivered"]
        self.assertEqual([one.get("mode") for one in delivered][:1], ["interrupt"], said)
        captain = self.thread(talk.CAPTAIN)
        self.assertIn("nudged ORD-01", json.dumps(captain))
        self.assertEqual({one["by"] for one in self.closed() if True}, {"captain", "rule"} & {one["by"] for one in
                                                                                          self.closed()})

    def test_an_ask_reaches_the_person_and_the_stream_goes_on(self) -> None:
        said = self.stuck([{"verb": "ask", "text": "ORD-01 is circling; stop it?", "options": "stop,leave"}])
        captain = self.thread(talk.CAPTAIN)
        self.assertIn("ORD-01 is circling; stop it?", json.dumps(captain), said)


class MessageTest(Through):
    """Words a person says to the stream, put to its captain as a `message` event."""

    def said(self, text: str) -> dict:
        return talk.send(talk.place(logs.run_dir(self.root), "ORD", talk.CAPTAIN), "say", text)

    def test_routed_with_of_quoted_unaltered_and_the_told_it_became_is_read(self) -> None:
        self.granted("ORD-01")
        sent = self.said("tell ORD-01 to mind the rounding")
        said = self.go({"message": [{"verb": "message", "slice": "ORD-01", "of": "$inbox", "text": "from your captain"},
                                    {"verb": "say", "text": "routed it to ORD-01"}]})
        routed = [one for one in talk.inbox(talk.place(logs.run_dir(self.root), "ORD", "ORD-01"))
                  if one.get("of") == sent["id"]]
        self.assertEqual([(one["from"], one.get("via"), one.get("quote")) for one in routed],
                         [("captain:ORD", "captain:ORD", "tell ORD-01 to mind the rounding")], said)
        self.assertIn("routed to ORD-01", json.dumps(self.thread(talk.CAPTAIN)))
        told = [one for one in self.lines("told") if one.get("inbox") == sent["id"]]
        self.assertEqual(len(told), 1)
        self.assertEqual([one.get("inbox") for one in self.lines("read")], [sent["id"]],
                         "M6: the captain acted on it, so the `told` it became is read, tied to it by its id")
        inbox = loaded_inbox(self.root)
        self.assertEqual(inbox.owed("ORD")["unread"], [], "nothing parks the stream an hour later over it")

    def test_an_order_that_does_not_address_the_words_leaves_them_unaddressed_and_unread(self) -> None:
        """M-B: the captain's only order is an unrelated pause."""
        self.granted("ORD-01", "ORD-02", "ORD-03")
        sent = self.said("which store does ORD-01 use?")
        self.go({"message": [{"verb": "pause", "slice": "ORD-03", "why": "holding it"}]})
        self.assertEqual(self.lines("read"), [])
        self.assertIn(("unaddressed", sent["id"]), [(one["kind"], one.get("id")) for one in self.thread(talk.CAPTAIN)])
        self.assertEqual(len(loaded_inbox(self.root).owed("ORD")["unread"]), 1)

    def test_words_the_rule_closes_leave_their_told_unread(self) -> None:
        self.granted("ORD-01")
        self.said("what are you doing?")
        self.go({"message": [{"verb": "none", "why": "the rule"}]})
        self.assertEqual(self.lines("read"), [])
        self.assertEqual(len(loaded_inbox(self.root).owed("ORD")["unread"]), 1)

    def test_a_pause_holds_a_slice_not_yet_started_and_a_resume_lets_it_run(self) -> None:
        self.granted("ORD-01", "ORD-02", "ORD-03")
        self.said("hold ORD-02 a while")
        # The pause, and a word to the person: only words answer words (M-B), and unanswered ones park the stream.
        said = self.go({"message": [{"verb": "pause", "slice": "ORD-02", "why": "the person asked"},
                                    {"verb": "say", "text": "ORD-02 is paused"}]}, "--interval", "0.2")
        merged = [one.get("slice") for one in self.lines("merged")]
        self.assertEqual(merged, ["ORD-01", "ORD-03"], said)
        self.assertEqual(talk.halted(talk.place(logs.run_dir(self.root), "ORD", "ORD-02"))[:2],
                         ("paused", "captain:ORD"))
        # M-C: the board lists it and its card says so, though it never started.
        from slipwai.talk_card import held_html
        from slipwai.talk_waits import items, summaries
        rows = [{"slice": f"ORD-0{n}", "state": state, "fairway": "ORD", "title": "", "feature": "ordering", "why": ""}
                for n, state in ((1, "merged"), (2, "todo"), (3, "merged"))]
        self.assertEqual([one["text"] for one in items(self.root, rows)[1]],
                         ["ORD-02 is paused by captain:ORD, and no rule lifts it: resume it when you are ready"])
        card = held_html({**rows[1], "talk": json.dumps(summaries(self.root, rows)["ORD-02"])})
        self.assertIn("Paused by captain:ORD", card)
        self.said("let ORD-02 go")
        said = self.go({"message": [{"verb": "resume", "slice": "ORD-02", "why": "the person said go"},
                                    {"verb": "say", "text": "ORD-02 goes on"}]}, "--interval", "0.2")
        self.assertIn("captain: nothing to start in ORD — every slice that may start is held; ORD-02 is paused by its "
                      "captain (captain:ORD) until its captain or a person resumes it: the person asked", said)
        # The captain answers while that turn ends with nothing to start; its resume is read at the next one.
        said = self.go({}, "--interval", "0.2")
        self.assertEqual([one.get("slice") for one in self.lines("merged")], ["ORD-01", "ORD-03", "ORD-02"], said)

    def test_a_message_to_another_stream_s_captain_lands_in_its_conversation(self) -> None:
        chart = self.root / "specs/ordering/chart.yaml"
        chart.write_text(chart.read_text(encoding="utf-8") + "  BIL-01:\n    fairway: BIL\n    sets: []\n"
                         "    steers_by: []\n", encoding="utf-8")
        self.granted("ORD-01")
        self.said("tell billing ORD-01 is nearly done")
        said = self.go({"message": [{"verb": "message", "slice": "captain:BIL", "text": "ORD-01 is nearly done"}]})
        landed = talk.inbox(talk.place(logs.run_dir(self.root), "BIL", talk.CAPTAIN))
        self.assertEqual([(one["from"], one["text"]) for one in landed],
                         [("captain:ORD", "ORD-01 is nearly done")], said)


class AskedMidTurnTest(Through):
    """What a slice's session asks mid-turn, over the protocol, put to its captain."""

    def setUp(self) -> None:
        super().setUp()
        self.marks = self.root.parent / f"{self.root.name}-marks"
        self.marks.mkdir()
        self.addCleanup(shutil.rmtree, self.marks, True)

    def asked(self, marker: str) -> dict:
        return json.loads((self.marks / f"{marker}-said").read_text(encoding="utf-8"))

    def test_with_answers_on_an_allowed_question_is_answered_and_written_as_the_captain_s_decision(self) -> None:
        self.granted("ORD-01")
        self.settings(bound=20, answers=True)
        (self.marks / ".askq").write_text("", encoding="utf-8")
        said = self.go({"question": [{"verb": "say", "text": "answering"},
                                     {"verb": "allow", "ask": "$ask", "why": "blue, as the style guide says"}]},
                       acp=True, STAND_IN_MARKS=str(self.marks))
        self.assertTrue(self.asked(".askq")["content"]["answer"].startswith("blue, as the style guide says (the "
                                                                             "captain's answer, recorded as decision"),
                        said)
        decisions = self.lines("decision")
        self.assertEqual([one.get("decided_by") for one in decisions], ["captain:ORD"], said)

    def test_a_read_inside_the_project_from_a_berth_of_its_own_is_the_captain_s_to_allow(self) -> None:
        """A read inside the berth is never asked, so `readable` measured against the berth allowed nothing."""
        (self.root / ".gitignore").write_text(".slipwai/\nfake-sail.py\nscript.log*\n", encoding="utf-8")
        for argv in (["config", "user.name", "t"], ["config", "user.email", "t@local"], ["add", "-A"],
                     ["commit", "--quiet", "-m", "the chart"]):
            subprocess.run(["git", *argv], cwd=self.root, check=True, capture_output=True)
        berth = (self.root.parent / f"{self.root.name}-ORD-01").resolve()
        self.addCleanup(shutil.rmtree, berth, True)
        self.granted("ORD-01")
        (self.marks / ".readin").write_text("", encoding="utf-8")
        (self.marks / ".outside").write_text("", encoding="utf-8")
        said = self.go({"permission": [{"verb": "allow", "ask": "$ask", "why": "reading the project is fine"}]},
                       acp=True, STAND_IN_MARKS=str(self.marks),
                       STAND_IN_READ=str(self.root.resolve() / "specs/ordering/chart.yaml"))
        self.assertTrue(berth.is_dir() or "ORD-01" in said, said)
        self.assertEqual(self.asked(".readin")["outcome"], {"outcome": "selected", "optionId": "yes-once"}, said)
        self.assertFalse(self.asked(".outside"), "a write outside the project is never the captain's to allow")
        refused = [one["why"] for one in self.results() if one["state"] == "refused"]
        self.assertTrue(any("not the captain's to allow" in why for why in refused), refused)

    def test_a_refused_permission_is_refused_and_the_stream_carries_on(self) -> None:
        self.granted("ORD-01")
        (self.marks / ".outside").write_text("", encoding="utf-8")
        said = self.go({"permission": [{"verb": "refuse", "ask": "$ask", "why": "outside the project"}]},
                       acp=True, STAND_IN_MARKS=str(self.marks))
        self.assertFalse(self.asked(".outside"), said)
        self.assertEqual([one["state"] for one in self.results() if one.get("carried") is None or True][-1:],
                         ["done"])
        self.assertIn("ORD-01 is through its gate and merged", said)


class TrunkRedTest(Through):
    def test_a_red_trunk_wakes_the_captain_whose_say_and_pause_are_carried_out(self) -> None:
        self.granted("ORD-01")
        self.harbour(logs.entry("trunk-red", harbour=True, commit="deadbeefcafe", job="ci", why="lint failed"))
        said = self.go({"trunk-red": [{"verb": "say", "text": "trunk is red; holding ORD-02"},
                                      {"verb": "pause", "slice": "ORD-02", "why": "trunk is red"}]}, timeout=90)
        self.assertEqual([(one["order"]["verb"], one["exit"]) for one in self.given()], [("say", 0), ("pause", 0)],
                         said)
        self.assertEqual([one["by"] for one in self.closed()], ["captain"])
        home = talk.place(logs.run_dir(self.root), "ORD", "ORD-02")
        self.assertEqual([(one["kind"], one["from"]) for one in talk.inbox(home)], [("pause", "captain:ORD")])
        self.go({}, timeout=90)  # read at the next turn, which trunk being red does not stop
        self.assertEqual(talk.halted(home)[:2], ("paused", "captain:ORD"))


class ResultTest(Through):
    """L2: an order's `done` says the program accepted it; a start or a stuck park says what became of it."""

    def test_a_start_the_loop_carried_out_says_so_on_its_result(self) -> None:
        self.granted("ORD-01")
        self.go({})
        starts = [one for one in self.results() if one.get("why") == "accepted: the program starts it"
                  or one.get("carried") is not None]
        self.assertEqual([(one["state"], one.get("carried")) for one in starts], [("done", "carried out")])


class SaidTodayTest(AgentBase):
    def test_what_it_decided_today_tells_accepted_from_carried_out(self) -> None:
        from slipwai.captain_files import decided_today
        folder = logs.run_dir(self.root) / "orders" / "ORD"
        folder.mkdir(parents=True)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for ident, result in (("a", {"state": "done", "carried": "accepted"}),
                              ("b", {"state": "done", "carried": "not carried out",
                                     "carried_why": "a person holds it"}),
                              ("c", {"state": "done", "carried": "carried out"}), ("d", {"state": "done"})):
            (folder / f"{stamp.replace('-', '').replace(':', '')}-{ident}.json").write_text(json.dumps(
                {"v": 1, "id": f"{stamp.replace('-', '').replace(':', '')}-{ident}", "t": stamp, "event": "e",
                 "fairway": "ORD", "verb": "start", "slice": f"ORD-0{ident}", "sig": ""}), encoding="utf-8")
            (folder / f"{stamp.replace('-', '').replace(':', '')}-{ident}.result.json").write_text(
                json.dumps({"v": 1, **result}), encoding="utf-8")
        said = {one["text"].split()[-1]: (one["after"], one["tone"]) for one in decided_today(self.root, "ORD")}
        self.assertEqual(said, {"ORD-0a": ("accepted, not carried out yet", "wait"),
                                "ORD-0b": ("accepted, and not carried out: a person holds it", "bad"),
                                "ORD-0c": ("done", "good"), "ORD-0d": ("done", "good")}, said)


class ModeTest(AgentBase):
    """The stand-in's misbehaviours, each through the real program (whole-branch review, L14)."""

    def test_an_unsigned_or_forged_order_is_refused_and_the_rule_decides(self) -> None:
        for mode in ("unsigned", "forged"):
            with self.subTest(mode=mode):
                self.setUp()
                self.granted("ORD-01")
                said = self.turn(mode)
                self.assertIn("ORD-01 is through its gate and merged", said)
                self.assertEqual({(one["state"], one["why"][:30]) for one in self.results()},
                                 {("refused", "it is not signed by this strea")})
                self.assertEqual([one["by"] for one in self.closed()], ["rule"])

    def test_a_file_that_is_not_json_and_an_order_no_captain_gives_are_refused_never_raised_on(self) -> None:
        for mode, why in (("malformed", "it is not an order this reads"), ("merge", "'merge' is not an order")):
            with self.subTest(mode=mode):
                self.setUp()
                self.granted("ORD-01")
                said = self.turn(mode)
                self.assertIn("ORD-01 is through its gate and merged", said)
                self.assertTrue(all(one["state"] == "refused" for one in self.results()))
                self.assertIn(why, json.dumps(self.results()))

    def test_a_flood_of_orders_is_read_to_the_ceiling_and_no_further(self) -> None:
        self.granted("ORD-01")
        said = self.turn("flood")
        self.assertIn("ORD-01 is through its gate and merged", said)
        states = [one["state"] for one in self.results()]
        self.assertEqual(states.count("done"), 12, said)
        self.assertEqual(len(states), 40)

    def test_a_resume_of_a_slice_a_person_paused_is_refused(self) -> None:
        self.granted("ORD-01", "ORD-02")
        talk.send(talk.place(logs.run_dir(self.root), "ORD", "ORD-02"), "pause", "lunch")
        talk.send(talk.place(logs.run_dir(self.root), "ORD", talk.CAPTAIN), "say", "carry on")  # a `message` event
        self.turn("lift", STAND_IN_TARGET="ORD-02")
        self.assertIn("only a person lifts a hold a person placed", json.dumps(self.results()))
        self.assertNotIn("ORD-02", [str(e.fields.get("slice")) for e in self.read("ORD") if e.kind == "merged"])

    def test_a_message_the_captain_sends_a_slice_lands_in_its_inbox_signed_as_the_captain(self) -> None:
        self.granted("ORD-01", "ORD-02")
        talk.send(talk.place(logs.run_dir(self.root), "ORD", talk.CAPTAIN), "say", "nudge ORD-02")  # a `message` event
        self.turn("message", STAND_IN_TARGET="ORD-02")
        landed = talk.inbox(talk.place(logs.run_dir(self.root), "ORD", "ORD-02"))
        self.assertEqual([(one["from"], one["text"]) for one in landed][:1],
                         [("captain:ORD", "the captain says: mind the rounding")])

    def test_an_answer_after_its_bound_is_refused_and_the_rule_had_decided(self) -> None:
        self.settings(bound=2)
        self.granted("ORD-01")
        said = self.turn("late", STAND_IN_DELAY="4")
        self.assertIn("ORD-01 is through its gate and merged", said)
        self.assertEqual(self.closed()[0]["by"], "rule")
        self.assertTrue(all(one["state"] == "refused" for one in self.results()), self.results())


class EnvironmentTest(AgentBase):
    def test_slipwai_captain_in_the_environment_overriding_harbour_json_is_said_once(self) -> None:
        """L9: a variable left in a shell is otherwise invisible."""
        self.granted("ORD-01")
        said = self.turn("today", captain="off")
        self.assertEqual(said.count("SLIPWAI_CAPTAIN=off in the environment turns this stream's captain agent off"),
                         1, said)
        self.assertEqual([e.kind for e in self.read("ORD")][:1], ["claimed"], "the deck is the program alone's")
        self.assertEqual([e for e in self.read("ORD") if e.kind == "noted"], [])
        status = json.loads((logs.run_dir(self.root) / "events/ORD/captain.json").read_text(encoding="utf-8"))
        self.assertEqual(status["agent"], False)
        self.assertIn("whatever harbour.json says", status["why"], "the board's captain window and strip say why")
        self.assertEqual(self.closed(), [], "the program alone: nothing is put to an agent")

    def test_slipwai_captain_agreeing_with_harbour_json_says_nothing(self) -> None:
        self.budget(minutes=5)  # no `captain` block at all: `off` changes nothing
        self.granted("ORD-01")
        said = self.turn("today", captain="off")
        self.assertNotIn("in the environment turns", said)
        self.assertFalse((logs.run_dir(self.root) / "events/ORD/captain.json").exists())


def loaded_inbox(root: Path):  # noqa: ANN201 — the project's own carried module
    sys.path.insert(0, str(root / "scripts/agents"))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"inbox_{root.name}", root / "scripts/agents/inbox.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(root / "scripts/agents"))


if __name__ == "__main__":
    import unittest
    unittest.main()
