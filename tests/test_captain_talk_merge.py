"""What is said to a slice while it waits on its merge, in a real berth over the stand-in agent.

From the merge request to its answer nothing is delivered: a commit a message's turn made would ride to
trunk on a branch whose gate had already passed. So a message then waits with that reason on its receipt;
a refusal sends it with the slice back to its berth, and a merge that lands answers it `not delivered`,
the driver closed before the berth is taken away. A pause or a stop sent then takes effect on a refusal
and says it came too late on a merge. And a paused slice asks the harbour for no session.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

import checkout_packages  # noqa: F401
from captain_fixture import Fixture
from test_drive import STAND_IN

from slipwai import logs, talk


def until(what: Callable[[], object], timeout: float = 60.0) -> None:
    ends = time.monotonic() + timeout
    while not what():
        if time.monotonic() > ends:
            raise AssertionError("waited and it did not happen")
        time.sleep(0.1)


class MergeWaitTest(Fixture):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "harbour.json").write_text(json.dumps(
            {"stages": {"default": {"minutes": 5, "tokens": 400}}, "wait_bound": 1, "trunk": "main", "ci": "off",
             "boilers": 3}), encoding="utf-8")
        (self.root / ".gitignore").write_text(".slipwai/\nfake-sail.py\n", encoding="utf-8")
        for argv in (["config", "user.name", "t"], ["config", "user.email", "t@local"], ["add", "-A"],
                     ["commit", "--quiet", "-m", "the chart"]):
            subprocess.run(["git", *argv], cwd=self.root, check=True, capture_output=True)
        self.berth = (self.root.parent / f"{self.root.name}-ORD-01").resolve()
        self.addCleanup(shutil.rmtree, self.berth, ignore_errors=True)
        self.home = talk.place(self.root / ".slipwai", "ORD", "ORD-01")

    def over(self) -> subprocess.Popen:
        env = {key: value for key, value in os.environ.items() if key != "SLIPWAI_SAIL"}
        captain = subprocess.Popen([sys.executable, str(self.script), "ORD", "--once"], cwd=self.root, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   env={**env, "SLIPWAI_ACP": STAND_IN})
        self.addCleanup(captain.kill)
        return captain

    def at_merge(self) -> subprocess.Popen:
        captain = self.over()
        until(lambda: any(e.kind == "request" for e in self.read("ORD")))
        return captain

    def finished(self, captain: subprocess.Popen) -> str:
        said, _ = captain.communicate(timeout=150)
        self.assertEqual(captain.returncode, 0, said)
        return said

    def lines(self) -> list[dict]:
        return talk.thread(self.home)

    def receipt(self, ident: str) -> dict:
        return next(one for one in talk.receipts(self.home) if one["id"] == ident)

    def test_a_message_during_the_merge_wait_is_held_and_never_delivered_once_it_lands(self) -> None:
        captain = self.at_merge()
        self.assertTrue(self.berth.is_dir(), "worked in a berth of its own")
        sent = talk.send(self.home, "say", "one more change")
        until(lambda: "held" in [one["kind"] for one in self.lines()])
        self.assertEqual((self.receipt(sent["id"])["state"], self.receipt(sent["id"])["why"]),
                         ("queued", "held: this slice is at its merge"))
        self.grant("ORD-01")
        said = self.finished(captain)
        self.assertIn("ORD-01 is through its gate and merged", said)
        receipt = self.receipt(sent["id"])
        self.assertEqual((receipt["state"], receipt["why"]),
                         ("not delivered", "the slice merged before this was delivered"))
        self.assertNotIn("delivered", [one["kind"] for one in self.lines()])
        self.assertFalse(self.berth.exists(), "the berth was left once the driver had closed")

    def test_a_refused_merge_takes_what_was_held_back_to_the_berth(self) -> None:
        captain = self.at_merge()
        sent = talk.send(self.home, "say", "fix the header too")
        until(lambda: "held" in [one["kind"] for one in self.lines()])
        self.grant("ORD-01", asked=1)
        self.refuse("ORD-01", "a conflict in the header", resolve=True)
        said = self.finished(captain)
        self.assertIn("ORD-01 is through its gate and merged", said)
        self.assertEqual(self.receipt(sent["id"])["state"], "answered", said)

    def test_a_stop_during_the_merge_wait_takes_effect_when_the_merge_is_refused(self) -> None:
        captain = self.at_merge()
        talk.send(self.home, "stop", "not this way")
        until(lambda: "stopped" in [one["kind"] for one in self.lines()])
        self.refuse("ORD-01", "a conflict", resolve=True)
        said = self.finished(captain)
        self.assertNotIn("merged", [e.kind for e in self.read("ORD")], said)
        self.assertEqual([(e.fields.get("by"), e.fields.get("why")) for e in self.read("ORD") if e.kind == "stopped"],
                         [("person", "not this way")])

    def test_a_pause_during_the_merge_wait_says_it_came_too_late_when_the_merge_lands(self) -> None:
        captain = self.at_merge()
        pause = talk.send(self.home, "pause", "lunch")
        until(lambda: "paused" in [one["kind"] for one in self.lines()])
        self.grant("ORD-01")
        said = self.finished(captain)
        self.assertIn("ORD-01 is through its gate and merged", said)
        late = [one for one in self.lines() if one["kind"] == "failed" and one.get("id") == pause["id"]]
        self.assertEqual([one["why"] for one in late], ["the slice merged before this took effect"])
        self.assertFalse(talk.paused(self.home))


class PlanTest(Fixture):
    def plan(self) -> dict[str, Any]:
        """The harbourmaster's plan, read in a process of its own: `abreast` and `clearance` find the project
        they serve from where they are, and a module another suite loaded first would answer for its own."""
        read = ("import json, sys; sys.path.insert(0, 'scripts/agents'); import abreast, pathlib; "
                "print(json.dumps(abreast.harbour_plan(set(), pathlib.Path('harbour.json'))))")
        done = subprocess.run([sys.executable, "-c", read], cwd=self.root, capture_output=True, text=True,
                              check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        return dict(json.loads(done.stdout))

    def test_a_paused_slice_wants_no_session(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("stopped", fairway="ORD", slice="ORD-01", paused=True))
        self.assertEqual(self.plan()["ORD"][0], 1, "a stopped slice is work wanting a session")
        home = talk.place(self.root / ".slipwai", "ORD", "ORD-01")
        talk.note(home, "paused", by="person")
        self.assertEqual(self.plan()["ORD"][0], 0, "a paused one is not, and spends no boiler")


if __name__ == "__main__":
    import unittest
    unittest.main()
