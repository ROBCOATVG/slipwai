"""A person heard by a stream with no one but the program to hear them: through the real harbourmaster and captain.

The board used to write what a person said into a stream's deck log as a `told` line, which the harbourmaster
cleared a park on with no captain running at all. It now drops it in a conversation's inbox, and these cases
hold that nothing a person could do before is lost: the harbourmaster lights a captain because a word waits,
the captain's first act is to read it into the stream's `told`, the harbourmaster clears the park on that, and
the stream carries on. Nothing is hand-written but the state each case starts from — no `cleared`, no
`decision`, no captain started by the case. Each with the captain agent off; the first two again with a
stand-in captain agent on.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import checkout_packages  # noqa: F401
from captain_fixture import AGENTS
from test_captain_abreast import Abreast

from slipwai import logs, talk

CHART = "feature: ordering\nslices:\n  L01: {fairway: LVR, sets: [Opened], steers_by: []}\n"
OLD = "2026-10-01T09:00:00Z"
STAND_IN = f"{sys.executable} {Path(__file__).resolve().parent / 'fixtures' / 'captain_stand_in.py'}"


class HeardTest(Abreast):
    agent = ""

    def setUp(self) -> None:
        super().setUp()
        (self.root / "specs/ordering/chart.yaml").write_text(CHART, encoding="utf-8")
        self.settings()
        for name in ("harbourmaster.py", "telegraph.py", "mender.py"):
            shutil.copy(AGENTS / name, self.root / "scripts/agents" / name)
        self.run_dir = logs.run_dir(self.root)
        self.addCleanup(self.end_captains)

    def end_captains(self) -> None:
        """The captains the harbourmaster lit in this throwaway project, which nothing else will end."""
        for path in (self.run_dir / "running").glob("captain-*.pid"):
            with contextlib.suppress(OSError, ValueError, subprocess.SubprocessError):
                pid = int(path.read_text(encoding="utf-8").strip())
                if os.name == "nt":  # no process groups: the tree by its root, as `taskkill` ends one
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, check=False)
                else:
                    os.killpg(pid, signal.SIGKILL)

    def sail_on(self, until: Callable[[], bool], timeout: float = 150) -> str:
        """The harbourmaster, passing every second and lighting the captains its plan wants, until `until`."""
        env = self.environment(ABREAST_SLEEP="0", SLIPWAI_CAPTAIN=self.agent or "off", STAND_IN_CAPTAIN="today")
        keeper = subprocess.Popen([sys.executable, str(self.root / "scripts/agents/harbourmaster.py"),
                                   "--interval", "1"],
                                  cwd=self.root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        ends = time.monotonic() + timeout
        try:
            while not until():
                if time.monotonic() > ends:
                    keeper.kill()
                    said, _ = keeper.communicate()
                    out = "".join(path.read_text(encoding="utf-8")
                                  for path in (self.run_dir / "running").glob("captain-*.out"))
                    raise AssertionError(f"it did not carry on.\nharbourmaster: {said[-3000:]}\ncaptain: {out[-3000:]}"
                                         f"\ndeck: {[(e.kind, e.fields) for e in self.read('LVR')]}")
                time.sleep(0.5)
        finally:
            keeper.kill()
            keeper.wait()
        return ""

    def merged(self) -> bool:
        return any(e.kind == "merged" for e in self.read("LVR"))

    def receipt(self, home: object, ident: str) -> dict:
        return next(one for one in talk.receipts(home) if one["id"] == ident)  # type: ignore[arg-type]

    def test_a_person_tells_a_parked_stream_and_it_carries_on(self) -> None:
        self.deck("LVR", logs.entry("claimed", fairway="LVR", slice="L01", t=OLD),
                  logs.entry("parked", fairway="LVR", why="L01: a host change only a person may make", cause="host",
                             t="2026-10-01T09:01:00Z"))
        home = talk.place(self.run_dir, "LVR", talk.CAPTAIN)
        sent = talk.send(home, "say", "Sorted, carry on")
        self.sail_on(self.merged)
        told = [e for e in self.read("LVR") if e.kind == "told"]
        self.assertEqual([(e.fields["by"], e.fields["inbox"], e.fields["message"]) for e in told],
                         [("person", sent["id"], "Sorted, carry on")])
        self.assertTrue(any(e.kind == "cleared" for e in logs.harbour_fold(self.root)))
        if not self.agent:
            self.assertEqual(self.receipt(home, sent["id"])["state"], "delivered")
        else:
            woken = [path.name for path in (self.run_dir / "events" / "LVR").glob("*.json")
                     if not path.name.endswith(".closed.json") and path.name != "state.json"]
            self.assertTrue(woken, "the agent was put the message as an event as well")

    def question(self) -> None:
        self.deck("LVR", logs.entry("claimed", fairway="LVR", slice="L01", t=OLD),
                  logs.entry("question", fairway="LVR", slice="L01", id="Q1", what="Which currency?",
                             t="2026-10-01T09:01:00Z"),
                  logs.entry("parked", fairway="LVR", slice="L01", why="L01: awaiting Q1", cause="question",
                             t="2026-10-01T09:02:00Z"))

    def test_an_answer_given_while_no_captain_is_lit_is_carried_and_the_slice_merges(self) -> None:
        self.question()
        talk.send(talk.place(self.run_dir, "LVR", "L01"), "say", "euros")
        self.sail_on(self.merged)
        decisions = [e for e in self.read("LVR") if e.kind == "decision"]
        self.assertEqual([(e.fields["id"], e.fields["what"], e.fields["decided_by"]) for e in decisions],
                         [("Q1", "euros", "human")])

    def test_try_now_lifts_a_pause_on_the_harness(self) -> None:
        if self.agent:
            self.skipTest("the agent's half is the two cases above")
        self.deck("LVR", logs.entry("claimed", fairway="LVR", slice="L01", t=OLD),
                  logs.entry("parked", fairway="LVR", why="L01: the harness would not run it", cause="limit",
                             until="2099-01-01T00:00:00Z", t="2026-10-01T09:01:00Z"))
        talk.send(talk.place(self.run_dir, "LVR", talk.CAPTAIN), "resume")
        self.sail_on(self.merged)
        self.assertEqual([e.fields["message"] for e in self.read("LVR") if e.kind == "told"],
                         ["try the paused slices now"])

    def test_a_second_answer_before_the_first_is_carried_replaces_it(self) -> None:
        if self.agent:
            self.skipTest("the agent's half is the two cases above")
        self.question()
        home = talk.place(self.run_dir, "LVR", "L01")
        talk.send(home, "say", "euros")
        time.sleep(1.1)  # a message's instant is to the second, and two in one second have no order between them
        later = talk.send(home, "say", "pounds, sorry")
        self.sail_on(self.merged)
        decisions = [e for e in self.read("LVR") if e.kind == "decision"]
        self.assertEqual([e.fields["what"] for e in decisions], ["pounds, sorry"], "one decision, the later answer")
        self.assertIn(later["id"], [e.fields.get("inbox") for e in self.read("LVR") if e.kind == "told"])

    def test_an_answer_after_the_first_was_carried_is_an_ordinary_message(self) -> None:
        if self.agent:
            self.skipTest("the agent's half is the two cases above")
        self.question()
        self.deck("LVR", logs.entry("told", fairway="LVR", slice="L01", message="euros", by="person", inbox="x",
                                    t="2026-10-01T09:03:00Z"),
                  logs.entry("decision", fairway="LVR", id="Q1", what="euros", slice="L01", decided_by="human",
                             t="2026-10-01T09:04:00Z"),
                  logs.entry("claimed", fairway="LVR", slice="L01", t="2026-10-01T09:04:00Z"))
        self.harbour(logs.entry("cleared", harbour=True, fairway="LVR", parked="2026-10-01T09:02:00Z", what="euros"))
        home = talk.place(self.run_dir, "LVR", "L01")
        sent = talk.send(home, "say", "actually pounds")
        self.sail_on(self.merged)
        self.assertEqual(len([e for e in self.read("LVR") if e.kind == "decision"]), 1)
        self.assertNotIn(sent["id"], [e.fields.get("inbox") for e in self.read("LVR") if e.kind == "told"])
        self.assertEqual(self.receipt(home, sent["id"])["state"], "delivered", "handed to the slice's next run")


class HeardByAnAgentTest(HeardTest):
    """The same, with a stand-in captain agent: the `told` is still the program's, so the park clears."""

    agent = STAND_IN


if __name__ == "__main__":
    import unittest
    unittest.main()
