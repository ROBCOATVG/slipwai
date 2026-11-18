"""The sixth review of the captain agent, through the whole program: each finding held by a test that goes red
without its fix. The helm's own parts, and the reader's, are `test_captain_review6_parts`; the allow-list of
every read of the run folder is `test_captain_run_reads`.

1. A stop is never swallowed: SIGTERM while the main thread waits on a decision ends as a stop, nothing claimed
   or parked after it; and a stop while a file is read goes through the reader.
2. What the program says about its own agent is a `noted` line, which nothing counts as owed: after the agent
   fails, and after it is refused commands, the stream never parks on its own note, and nothing else is read.
3. What is planted in the run folder — an activity log, a saved session, an agent's pid record, a thread, a
   `.working` file and a pid file that are pipes — never stops or hangs the program, with an agent or without.
5. The agent let go leaves `captain.json` saying so, with why and when, and no file half written.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import unittest
from datetime import UTC, datetime, timedelta
from typing import Any

import checkout_packages  # noqa: F401
from test_captain_abreast import Abreast
from test_captain_agent import CAPTAIN, SAIL, AgentBase
from test_captain_agent_rules import RulesTest
from test_captain_helm import loaded

from slipwai import logs, talk


class StopTest(Abreast):
    """1: a stop while the main thread waits on its captain's choice."""

    def test_a_stop_during_a_decision_on_the_main_thread_ends_as_a_stop(self) -> None:
        self.settings(attempts=0, captain={"agent": True, "bound": 20})
        self.skeleton_merged()
        self.slots(1)
        self.granted("L02", "L03", "L04")
        began = logs.now()
        child = subprocess.Popen([sys.executable, str(self.script), "LVR", "--once"], cwd=self.root, text=True,
                                 env=self.environment(ABREAST_SLEEP="3", STAND_IN_CAPTAIN="silent",
                                                      SLIPWAI_CAPTAIN=CAPTAIN),
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.addCleanup(child.kill)
        events = logs.run_dir(self.root) / "events" / "LVR"
        ends = time.monotonic() + 60
        while not [one for one in events.glob("*.json") if one.name not in ("state.json", "captain.json")
                   and not one.name.endswith(".closed.json")]:
            self.assertLess(time.monotonic(), ends, "no choice was ever put to the captain")
            time.sleep(0.05)
        time.sleep(0.5)  # the main thread is waiting on the silent captain
        child.send_signal(signal.SIGTERM)
        said, _ = child.communicate(timeout=120)
        self.assertIn("stopped between slices", said)
        after = [e.kind for e in self.read("LVR") if e.t >= began]
        self.assertFalse({"claimed", "parked", "noted", "told"} & set(after), said)
        self.assertNotIn("captain agent failed", said)


class NotedTest(RulesTest):
    """2: the program's word about its agent is news, never a wait."""

    def owed(self, inbox: Any, hours: float) -> dict:
        return inbox.owed("ORD", now=datetime.now(UTC) + timedelta(hours=hours))

    def test_the_failure_and_refused_commands_are_noted_and_never_park_the_stream(self) -> None:
        captain = self.loaded()
        captain.ON.update(feature="ordering", fairway="ORD")
        while time.time() % 1 > 0.5:
            time.sleep(0.01)  # a person's word in the very second the program writes its own
        self.deck("ORD", logs.entry("told", fairway="ORD", by="person", message="the rounding is wrong"))
        captain.agent_failed(RuntimeError("the protocol went away"), "deciding choose-next")
        options = [{"kind": "allow_once", "optionId": "y"}, {"kind": "reject_once", "optionId": "n"}]
        captain.captain_agent.REFUSED.update(count=0, first="")
        for count in range(40):
            captain.captain_agent.permit({"kind": "execute", "rawInput": {"command": f"ls {'x' * 300} {count}"}},
                                         options)
        runner = captain.captain_agent.Runner("ORD", logs.run_dir(self.root), {"bound": 1}, (["x"], None))
        captain.Stream("ordering", "ORD").noted(runner.refusals())
        self.assertEqual(runner.refusals(), "")  # once an event: nothing more until it is refused again
        lines = self.read("ORD")
        noted = [e for e in lines if e.kind == "noted"]
        self.assertEqual(len(noted), 2, [(e.kind, e.fields) for e in lines])
        self.assertIn("refused 40 commands", str(noted[1].fields["what"]))
        self.assertLess(len(str(noted[1].fields["what"])), 400)
        self.assertEqual([e for e in lines if e.kind in ("read", "told") and e.fields.get("by") != "person"], [])
        inbox = loaded(self.root, "inbox")
        late = self.owed(inbox, 48)
        self.assertEqual([one.get("by") for one in late["unread"]], ["person"])  # only the person's is owed
        self.deck("ORD", logs.entry("read", fairway="ORD", told=[e for e in lines if e.kind == "told"][0].t))
        self.assertFalse(self.owed(inbox, 48)["forced"], self.owed(inbox, 48))


class FolderTest(AgentBase):
    """3 and 5: what is planted in the run folder, and what a failure leaves behind."""

    def run_once(self, agent: bool, sail: str = SAIL, **env: str) -> subprocess.CompletedProcess:
        clean = {key: value for key, value in os.environ.items() if key not in ("SLIPWAI_ACP", "SLIPWAI_CAPTAIN")}
        child = subprocess.Popen([sys.executable, str(self.script), "ORD", "--once"], cwd=self.root, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 env={**clean, "SLIPWAI_SAIL": self.sail(sail),
                                      "SLIPWAI_CAPTAIN": CAPTAIN if agent else "off", "STAND_IN_CAPTAIN": "today",
                                      **env})
        try:
            said, _ = child.communicate(timeout=150)
        except subprocess.TimeoutExpired:
            child.kill()
            said, _ = child.communicate()
            self.fail(f"the captain hung on a planted file:\n{said[-3000:]}")
        return subprocess.CompletedProcess(child.args, child.returncode, said, "")

    def plant(self) -> None:
        run = logs.run_dir(self.root)
        deep = "[" * 200000
        (run / "activity/ORD").mkdir(parents=True, exist_ok=True)
        odd = "".join(json.dumps({"kind": kind, "t": 5, "agent": 1, "what": [1], "tool": {"a": 1}}) + "\n"
                      for kind in ("start", "ran", "failed", "done", "link")) * 3
        for slice_id in ("ORD-01", "ORD-02", "ORD-03"):
            (run / f"activity/ORD/{slice_id}.jsonl").write_text(deep + "\n" + odd, encoding="utf-8")
            home = talk.place(run, "ORD", slice_id)
            home.mkdir(parents=True, exist_ok=True)
            (home / "session.json").write_text(deep, encoding="utf-8")
            (home / "thread.jsonl").write_text(deep + "\n" + json.dumps({"kind": 5, "t": []}) + "\n",
                                               encoding="utf-8")
        captain = talk.place(run, "ORD", talk.CAPTAIN)
        captain.mkdir(parents=True, exist_ok=True)
        (talk.place(run, "ORD", "ORD-02") / "agent.pid").write_text(deep, encoding="utf-8")
        (talk.place(run, "ORD", "ORD-03") / "agent.pid").write_text(
            json.dumps({"pid": True, "captain": True, "identity": 5}), encoding="utf-8")
        running = run / "running"
        running.mkdir(parents=True, exist_ok=True)
        os.mkfifo(running / "captain-ORD--ORD-01.working")  # read when the claimed slice is carried on
        os.mkfifo(running / "harbourmaster.pid")  # read at every look for a harbourmaster gone
        (run / "activity/ORD/ORD-01.jsonl").unlink()
        os.mkfifo(run / "activity/ORD/ORD-01.jsonl")  # the slice in flight's, read at every look for it stuck
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "a named pipe is POSIX's; Windows has none to plant")
    def test_planted_files_never_stop_the_program_with_an_agent_or_without(self) -> None:
        for agent in (True, False):
            with self.subTest(agent=agent):
                self.setUp()
                self.granted("ORD-01")
                self.plant()
                done = self.run_once(agent, "import time\ntime.sleep(3)\n" + SAIL)
                self.assertEqual(done.returncode, 0, done.stdout[-3000:])
                self.assertIn("ORD-01 is through its gate and merged", done.stdout)
                self.assertNotIn("captain agent failed", done.stdout)

    def test_an_agent_let_go_says_so_in_its_status_and_leaves_nothing_half_written(self) -> None:
        self.granted("ORD-01")
        events = logs.run_dir(self.root) / "events" / "ORD"
        (events / "state.json").mkdir(parents=True)  # the first event cannot be put: the agent fails
        done = self.run_once(True)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("ORD-01 is through its gate and merged", done.stdout)
        status = json.loads((events / "captain.json").read_text(encoding="utf-8"))
        self.assertIs(status["agent"], False, status)
        self.assertIn("the captain agent failed", status["why"])
        self.assertTrue(status.get("t"), status)
        self.assertEqual(sorted(path.name for path in events.iterdir() if path.name.endswith(".part")), [])
        noted = [e for e in self.read("ORD") if e.kind == "noted"]
        self.assertEqual(len(noted), 1, done.stdout)
        inbox = loaded(self.root, "inbox")
        self.assertFalse(inbox.owed("ORD", now=datetime.now(UTC) + timedelta(days=3))["forced"])


if __name__ == "__main__":
    import unittest
    unittest.main()
