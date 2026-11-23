"""The captain's session is never carried: fresh at every start, and closed for a fresh one once it has grown.

manda's intake captain held one session from 11-20 to 11-23 and loaded it again at the next fleet start: 45k
tokens on its first call, 655k on its 634th, every call paying for a history the brief says not to believe
(slipwai#154, item 7). The session's agent is a stand-in here; what is held is when the runner opens one.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"


def captain_agent() -> Any:
    sys.path.insert(0, str(AGENTS))
    found = importlib.util.spec_from_file_location("toolkit_captain_agent", AGENTS / "captain_agent.py")
    assert found is not None and found.loader is not None
    made = importlib.util.module_from_spec(found)
    found.loader.exec_module(made)
    return made


class StandIn:
    """A held session that answers every prompt and reports what it is told to."""

    made: list[StandIn] = []

    def __init__(self, argv: list[str], cwd: Any, env: dict[str, str], text: str, **given: Any) -> None:
        self.given, self.env = given, env
        self.prompts = [text]
        self.alive, self.unlaunched, self.ended = True, "", False
        self.context: int | None = None
        StandIn.made.append(self)

    def prompt(self, text: str) -> None:
        self.prompts.append(text)

    def end(self) -> None:
        self.ended, self.alive = True, False


class CeilingTest(unittest.TestCase):
    agent: Any = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.agent = captain_agent()

    def setUp(self) -> None:
        StandIn.made = []
        real = self.agent.drive.Drive
        self.agent.drive.Drive = StandIn
        self.addCleanup(setattr, self.agent.drive, "Drive", real)
        self.run_dir = Path(tempfile.mkdtemp())

    def runner(self, **harbour: Any) -> Any:
        return self.agent.Runner("ORD", self.run_dir, self.agent.settings({"captain": harbour}), (["x"], None))

    def wake(self, runner: Any, number: int) -> None:
        held = {"id": f"e{number}", "kind": "stuck", "may": ["none"]}
        runner.wake(self.run_dir / f"e{number}.json", self.run_dir / "state.json", held, {"SLIPWAI_STAGE": "captain"})

    def test_a_captain_s_first_session_is_fresh_whatever_was_saved_beside_its_conversation(self) -> None:
        home = self.run_dir / "talk/ORD/_captain"
        home.mkdir(parents=True)
        (home / "session.json").write_text(json.dumps({"v": 1, "id": "the-last-run-s", "harness": ""}),
                                           encoding="utf-8")
        self.wake(self.runner(), 1)
        self.assertIs(StandIn.made[0].given.get("fresh"), True, "the last run's session was loaded")

    def test_the_session_is_held_across_events_while_it_is_under_its_ceiling(self) -> None:
        runner = self.runner()
        for number in range(3):
            self.wake(runner, number)
        StandIn.made[0].context = 149_000
        self.wake(runner, 4)
        self.assertEqual(len(StandIn.made), 1)
        self.assertEqual(len(StandIn.made[0].prompts), 4)

    def test_a_session_past_its_context_ceiling_is_closed_at_the_next_event_and_a_fresh_one_answers_it(self) -> None:
        runner = self.runner(context_ceiling=1000)
        self.wake(runner, 1)
        StandIn.made[0].context = 1001
        self.wake(runner, 2)
        first, second = StandIn.made
        self.assertTrue(first.ended, "the grown session was left open")
        self.assertEqual(len(first.prompts), 1, "the grown session was handed the next event")
        self.assertIs(second.given.get("fresh"), True)
        self.assertIn("e2", second.prompts[0])

    def test_where_the_agent_never_says_its_size_the_wake_ups_stand_in_for_it(self) -> None:
        runner = self.runner(wake_ceiling=3)
        for number in range(4):
            self.wake(runner, number)
        self.assertEqual([len(one.prompts) for one in StandIn.made], [3, 1])
        self.assertTrue(StandIn.made[0].ended)

    def test_a_reported_size_is_believed_over_the_wake_count(self) -> None:
        runner = self.runner(wake_ceiling=2)
        self.wake(runner, 1)
        StandIn.made[0].context = 10
        for number in range(2, 6):
            self.wake(runner, number)
        self.assertEqual(len(StandIn.made), 1)

    def test_the_ceilings_default_and_refuse_nonsense(self) -> None:
        said = self.agent.settings({"captain": {"context_ceiling": -1, "wake_ceiling": "many"}})
        self.assertEqual((said["context_ceiling"], said["wake_ceiling"]),
                         (self.agent.CONTEXT_CEILING, self.agent.WAKE_CEILING))
        self.assertEqual(self.agent.settings({"captain": {"context_ceiling": 80_000}})["context_ceiling"], 80_000)


class UsageTest(unittest.TestCase):
    """The driver keeps what the agent last said its context holds (`usage_update`, ACP's session usage)."""

    def test_a_usage_update_is_kept_and_a_malformed_one_is_not(self) -> None:
        drive = captain_agent().drive
        held = SimpleNamespace(replaying=False, context=None)
        drive.Drive.update(held, {"sessionUpdate": "usage_update", "used": 53_000, "size": 200_000})
        self.assertEqual(held.context, 53_000)
        for wrong in ("lots", -5, True, None):
            drive.Drive.update(held, {"sessionUpdate": "usage_update", "used": wrong})
        self.assertEqual(held.context, 53_000)


if __name__ == "__main__":
    unittest.main()
