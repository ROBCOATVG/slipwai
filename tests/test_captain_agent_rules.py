"""The reviews of the captain, through the whole captain program: what only the program around the helm holds.

What is proved: a slice has at most `2 × attempts + 1` runs that cost an attempt between a person's words to
it, counted at the dispatch whoever asks — a stand-in captain that stops every run gets no more; a person's word
to the stream after a park about one slice gives that slice its runs back and no other; a message the captain
routed never answers a park; a person's word to one slice does not answer a park the whole stream wrote about
another; and a stream park about `GN1` is never taken as `GN10`'s answer.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
from typing import Any

import checkout_packages  # noqa: F401
from test_captain_agent import CAPTAIN, AgentBase

from slipwai import logs, talk

#: A `/sail` that is still working when it is stopped: it writes nothing for its first seconds.
SLOW = "import time\ntime.sleep(4)\n"


class RulesTest(AgentBase):
    def loaded(self) -> Any:
        spec = importlib.util.spec_from_file_location(f"captain_{self.root.name}", self.script)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
        return module

    def dispatched(self) -> list[logs.Entry]:
        return [e for e in self.read("ORD") if e.kind == "dispatched"]

    def test_a_captain_that_stops_every_run_gets_no_more_than_the_ceiling(self) -> None:
        self.budget(minutes=5, attempts=1)  # a ceiling of three runs
        self.settings(bound=20)
        clean = {key: value for key, value in os.environ.items() if key not in ("SLIPWAI_ACP", "SLIPWAI_CAPTAIN")}
        captain = subprocess.Popen([sys.executable, str(self.script), "ORD", "--interval", "0.2"], cwd=self.root,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   env={**clean, "SLIPWAI_SAIL": self.sail(SLOW), "SLIPWAI_CAPTAIN": CAPTAIN,
                                        "STAND_IN_CAPTAIN": "stopper"})
        self.addCleanup(captain.kill)
        home = talk.place(logs.run_dir(self.root), "ORD", talk.CAPTAIN)
        ends = time.monotonic() + 150
        while captain.poll() is None and time.monotonic() < ends:
            # Another stream's captain saying something wakes this one, which stops whatever is in flight.
            talk.send(home, "say", "how is it going?", by="captain:BIL")
            self.assertLessEqual(len(self.dispatched()), 3, "past the ceiling: the captain ran it for ever")
            time.sleep(1)
        said, _ = captain.communicate(timeout=30)
        self.assertEqual(len(self.dispatched()), 3, said)
        parks = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("every run `attempts` allows between them", str(parks[-1].fields["why"]), said)
        self.assertGreaterEqual(sum(1 for e in self.read("ORD") if e.kind == "stopped"), 2, "it was stopping them")

    def test_a_person_s_word_gives_back_the_runs_of_the_slice_it_is_about_and_no_other(self) -> None:
        self.budget(minutes=5, attempts=0)  # a ceiling of one run
        self.settings(bound=20)
        old = "2026-11-16T09:00:00Z"
        said = talk.send(talk.place(logs.run_dir(self.root), "ORD", talk.CAPTAIN), "say", "done")  # what proves it
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=old),
                  logs.entry("dispatched", fairway="ORD", slice="ORD-01", t=old),
                  logs.entry("claimed", fairway="ORD", slice="ORD-02", t=old),
                  logs.entry("dispatched", fairway="ORD", slice="ORD-02", t=old),
                  logs.entry("parked", fairway="ORD", why="ORD-01: a host change", t="2026-11-16T09:01:00Z"),
                  logs.entry("told", fairway="ORD", message="done", by="person", inbox=said["id"],
                             t="2026-11-16T09:02:00Z"))
        module = self.loaded()
        self.assertEqual(module.counted_runs("ordering", "ORD", "ORD-01"), 0, "the word after its park")
        self.assertEqual(module.counted_runs("ordering", "ORD", "ORD-02"), 1, "a word about another is not its")

    def test_a_message_its_captain_routed_never_answers_a_park(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t="2026-11-16T09:00:00Z"),
                  logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="Refund window?",
                             t="2026-11-16T09:01:00Z"),
                  logs.entry("parked", fairway="ORD", slice="ORD-01", why="ORD-01: awaiting Q1",
                             t="2026-11-16T09:02:00Z"))
        talk.send(talk.place(logs.run_dir(self.root), "ORD", "ORD-01"), "say", "Decision: refunds 90 days",
                  by="captain:ORD", via="captain:ORD", of="x", quote="what do you think?", quote_from="person")
        self.turn("today")
        self.assertEqual([e for e in self.read("ORD") if e.kind == "told"], [])

    def test_a_word_to_one_slice_does_not_answer_the_stream_s_park_about_another(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-02", t="2026-11-16T09:00:00Z"),
                  logs.entry("parked", fairway="ORD", why="ORD-02: a host change only a person may make",
                             t="2026-11-16T09:01:00Z"))
        talk.send(talk.place(logs.run_dir(self.root), "ORD", "ORD-01"), "say", "use the blue header")
        self.turn("today")
        self.assertEqual([e for e in self.read("ORD") if e.kind == "told"], [])
        talk.send(talk.place(logs.run_dir(self.root), "ORD", "ORD-02"), "say", "landed it, carry on")
        self.turn("today")
        self.assertEqual([(e.fields.get("slice"), e.fields["message"]) for e in self.read("ORD") if e.kind == "told"],
                         [("ORD-02", "landed it, carry on")])

    def test_a_park_about_one_slice_is_never_taken_as_another_s_whose_id_begins_the_same(self) -> None:
        parked = "2026-11-16T09:02:00Z"
        self.deck("GN", logs.entry("question", fairway="GN", slice="GN10", id="Q1", what="Which colour?",
                                   t="2026-11-16T09:01:00Z"),
                  logs.entry("parked", fairway="GN", why="GN1: a host change", t=parked),
                  logs.entry("told", fairway="GN", message="blue", by="person", slice="GN1",
                             t="2026-11-16T09:03:00Z"))
        self.harbour(logs.entry("cleared", harbour=True, fairway="GN", parked=parked, what="blue"))
        module = self.loaded()
        found = module.entries("ordering", "GN")
        self.assertEqual(module.park_answer(found, "GN", "GN10"), "")
        self.assertEqual(module.park_answer(found, "GN", "GN1"), "blue")


if __name__ == "__main__":
    import unittest
    unittest.main()
