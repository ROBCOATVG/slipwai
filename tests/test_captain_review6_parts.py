"""The sixth review of the captain agent, part by part: the reader, the helm, and the captain program's seams.

1. A stop raised while a file is read goes through the reader.
3. A saved session, an activity log, a thread nested past any parser or of the wrong types: read as nothing.
4. The reader opens a path once and asks the handle: a pipe, a link, a file swapped for a pipe between a look
   and a read — at the worst moment, and racing — are refused, and nothing waits.
5. One path lets the agent go, from the main thread or one of its own: a failure in a background ask does
   it; what is out is answered — a message marked unaddressed — and every event opened gets its closing record;
   a choice put while it is let go is the rule's; a fault in the program's own facts is the program's.
6. The command the captain is handed is accepted in a project whose path has a space, and is its only spelling.
7. A message over the limit is refused when it is sent, and one planted is refused saying why; what the helm
   remembers of refused orders is bounded by what is on disk.
8. A slice that merges with a person's pause standing is resumed by the merge; a person's pause that lands
   after a captain's park was checked wins over it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401
from captain_fixture import AGENTS, CARRIED
from test_captain_agent import AgentBase
from test_captain_helm import HelmBase, Runner, loaded

from slipwai import logs, talk
from slipwai.assets import TOOLKIT_ROOT


def within(call: Any, seconds: float = 10) -> list[Any]:
    """`call()` in a thread: [its result] where it returned in time, [] where it is still waiting."""
    got: list[Any] = []
    worker = threading.Thread(target=lambda: got.append(call()), daemon=True)
    worker.start()
    worker.join(seconds)
    return got


class ReaderTest(HelmBase):
    def test_a_stop_while_a_file_is_read_goes_through(self) -> None:
        captain = loaded(self.root, "captain")
        path = self.root / "message.json"
        path.write_text("{}", encoding="utf-8")
        with mock.patch.object(captain.talk.json, "loads", side_effect=captain.Stopped()), \
                self.assertRaises(captain.Stopped):
            captain.talk.read_json(path)

    def test_files_nested_past_any_parser_or_of_the_wrong_types_are_read_as_nothing(self) -> None:
        reader, stuck = loaded(self.root, "talk"), loaded(self.root, "stuck")
        home = reader.place(self.run_dir, "ORD", "ORD-01")
        home.mkdir(parents=True)
        (home / "session.json").write_text("[" * 200000, encoding="utf-8")
        self.assertEqual(reader.saved_session(home), {})
        (home / "session.json").write_text(json.dumps({"id": 5, "harness": []}), encoding="utf-8")
        self.assertEqual(reader.saved_session(home), {})
        (home / "thread.jsonl").write_text("[" * 200000 + "\n" + json.dumps({"kind": 5}) + "\n", encoding="utf-8")
        self.assertEqual(reader.thread(home), [])
        odd = "".join(json.dumps({"kind": kind, "t": 5, "agent": 1, "what": [1], "title": [1]}) + "\n"
                      for kind in stuck.KINDS) * 3
        self.assertEqual(stuck.parsed(("[" * 200000 + "\n" + odd).encode(), False), [])
        activity = self.run_dir / "activity/ORD/ORD-01.jsonl"
        activity.parent.mkdir(parents=True)
        activity.write_text("[" * 200000 + "\n" + odd, encoding="utf-8")
        self.assertEqual(stuck.stuck(stuck.tail_lines(activity), "ORD-01"), [])

    def test_a_pipe_and_a_link_are_refused_and_nothing_waits(self) -> None:
        reader = loaded(self.root, "talk")
        pipe, link = self.root / "pipe.json", self.root / "link.json"
        os.mkfifo(pipe)
        (self.root / "real.json").write_text("{}", encoding="utf-8")
        link.symlink_to(self.root / "real.json")
        self.assertEqual(within(lambda: reader.read_json(pipe)), [None])
        self.assertEqual(within(lambda: reader.read_json(link)), [None])

    def test_a_file_swapped_for_a_pipe_after_any_look_at_its_path_is_not_waited_on(self) -> None:
        """Every look at the path by name — a stat, an lstat — is followed at once by the file being swapped for
        a pipe: the worst moment a racer could pick. A reader that looks twice opens the pipe and waits."""
        reader = loaded(self.root, "talk")
        target = self.root / "order.json"
        target.write_text("{}", encoding="utf-8")
        real_stat, real_lstat = os.stat, os.lstat
        swapped: list[int] = []

        def swap(found: Any) -> Any:
            if not swapped:
                swapped.append(1)
                target.unlink()
                os.mkfifo(target)
            return found

        def stat(path: Any, *args: Any, **kwargs: Any) -> Any:
            found = real_stat(path, *args, **kwargs)
            return swap(found) if str(path) == str(target) else found

        def lstat(path: Any, *args: Any, **kwargs: Any) -> Any:
            found = real_lstat(path, *args, **kwargs)
            return swap(found) if str(path) == str(target) else found
        with mock.patch.object(os, "stat", stat), mock.patch.object(os, "lstat", lstat):
            got = within(lambda: reader.read_json(target), 5)
        if not got:  # release the reader that is waiting, so the thread ends
            os.close(os.open(target, os.O_WRONLY | os.O_NONBLOCK))
        self.assertTrue(got, "the reader opened a pipe swapped in after it looked, and waited on it")

    def test_a_racer_swapping_a_file_and_a_pipe_never_holds_the_reader(self) -> None:
        reader = loaded(self.root, "talk")
        target = self.root / "x.json"
        racer = subprocess.Popen([sys.executable, "-c", f"""
import os
p = {str(target)!r}; a = p + '.a'
while True:
    try:
        open(a, 'w').write('{{}}'); os.replace(a, p)
        os.mkfifo(a); os.replace(a, p)
    except OSError:
        pass
"""])
        self.addCleanup(racer.kill)
        done = within(lambda: [reader.read_json(target) for _ in range(3000)], 60)
        racer.kill()
        if not done:
            os.close(os.open(target, os.O_WRONLY | os.O_NONBLOCK))
        self.assertTrue(done, "a read waited on the pipe")


class SizeTest(HelmBase):
    def test_a_message_over_the_limit_is_refused_when_sent_and_one_planted_says_why(self) -> None:
        home = talk.place(self.run_dir, "ORD", "ORD-01")
        with self.assertRaises(ValueError) as refused:
            talk.send(home, "say", "the log:\n" + "x" * (talk.LARGEST + 1))
        self.assertIn(f"{talk.LARGEST:,}", str(refused.exception))
        (home / "inbox").mkdir(parents=True, exist_ok=True)
        (home / "inbox/20261116T090000Z-big000.json").write_text("x" * (talk.LARGEST + 10), encoding="utf-8")
        refusals = talk.refused(home)
        self.assertEqual([why for _, why in refusals], [talk.TOO_LARGE])
        for path, why in refusals:
            talk.reject(home, path, why)
        self.assertEqual([one["why"] for one in talk.receipts(home)], [talk.TOO_LARGE])

    def test_the_orders_a_helm_has_refused_are_remembered_only_while_they_are_on_disk(self) -> None:
        def act(held: dict, env: dict) -> None:
            self.folder().mkdir(parents=True, exist_ok=True)
            for count in range(5):
                (self.folder() / f"20261116T090000Z-bad{count:03}.json").write_text("{", encoding="utf-8")
        helm = self.helm(act)
        self.choose(helm)
        self.assertEqual(len(helm.refused), 5)
        shutil.rmtree(self.folder())
        helm.waiting()
        self.assertEqual(helm.refused, set())


class HelmTest(HelmBase):
    def test_an_event_whose_decision_raised_after_it_was_opened_is_closed_by_the_rule(self) -> None:
        helm = self.helm(lambda held, env: (_ for _ in ()).throw(RuntimeError("the session broke")))
        with self.assertRaises(RuntimeError):
            self.choose(helm)
        self.assertEqual([one["by"] for one in self.closed()], ["rule"])


class ProgramTest(AgentBase):
    """The captain program's seams, loaded in a project with one stream."""

    def setUp(self) -> None:
        super().setUp()
        spec_root = self.root
        self.program = loaded(spec_root, "captain")
        self.program.ON.update(feature="ordering", fairway="ORD")
        self.addCleanup(setattr, self.program, "HELM", None)

    def helm(self, act: Any, bound: float = 30) -> Any:
        found = self.program.captain_events.Helm(logs.run_dir(self.root), "ORD", Runner(act, bound),
                                                 self.program.Stream("ordering", "ORD"), say=lambda line: None,
                                                 failed=self.program.agent_failed)
        self.program.HELM = found
        return found

    def until(self, what: Any, seconds: float = 10) -> bool:
        ends = time.monotonic() + seconds
        while not what() and time.monotonic() < ends:
            time.sleep(0.05)
        return bool(what())

    def test_a_failure_in_a_background_ask_lets_the_agent_go_as_one_on_the_main_thread_does(self) -> None:
        def broken(held: dict, env: dict) -> None:
            raise RuntimeError("the session broke")
        self.helm(broken)
        pending: dict = {}
        self.program.ask_choice("ordering", ["ORD-01", "ORD-02"], 1, [], pending)
        self.assertTrue(self.until(lambda: pending.get("done")), pending)
        self.assertTrue(self.until(lambda: self.program.HELM is None), "the agent was not let go")
        self.assertEqual([e.kind for e in self.read("ORD") if e.kind == "noted"], ["noted"])

    def test_a_message_out_when_the_agent_is_let_go_is_answered_at_once(self) -> None:
        helm = self.helm(None)  # silent for its whole bound
        asked = talk.send(talk.place(logs.run_dir(self.root), "ORD", talk.CAPTAIN), "say", "use euros")
        self.program.heard_captain("ORD")
        self.assertTrue(self.until(lambda: helm.live), "the message was never put")
        self.program.agent_failed(RuntimeError("gone"), "deciding stuck")
        home = talk.place(logs.run_dir(self.root), "ORD", talk.CAPTAIN)
        self.assertTrue(self.until(lambda: "unaddressed" in [one["kind"] for one in talk.thread(home)], 5),
                        talk.thread(home))
        self.assertFalse((home / "inbox" / f"{asked['id']}.json").exists())
        closed = list((logs.run_dir(self.root) / "events/ORD").glob("*.closed.json"))
        self.assertEqual([json.loads(path.read_text(encoding="utf-8"))["by"] for path in closed], ["rule"])

    def test_a_choice_put_while_the_agent_is_let_go_is_the_rule_s(self) -> None:
        self.program.HELM = None
        pending: dict = {}
        self.program.ask_choice("ordering", ["ORD-01", "ORD-02"], 1, [], pending)
        self.assertEqual(pending.get("chosen"), ["ORD-01"])

    def test_a_fault_in_the_program_s_own_facts_is_the_program_s(self) -> None:
        helm = self.helm(None, bound=0.2)

        def facts() -> dict:
            raise KeyError("a fold the program got wrong")
        chosen = self.program.decided("choose-next", "", facts, ["start"], [{"verb": "start", "slice": "ORD-01"}])
        self.assertEqual(chosen, [{"verb": "start", "slice": "ORD-01"}])
        self.assertIs(self.program.HELM, helm)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "noted"], [])

    def test_a_slice_merged_with_a_person_s_pause_standing_is_resumed_by_the_merge(self) -> None:
        home = self.program.conversation("ORD", "ORD-01")
        talk.note(home, "pausing", by="person", why="lunch")
        self.program.landed_talk("ORD", "ORD-01")
        self.assertEqual(talk.halted(home)[0], "", [one["kind"] for one in talk.thread(home)])

    def test_a_person_s_pause_after_the_park_was_checked_wins_over_it(self) -> None:
        held = {"halted": ("stopped", "captain:ORD", "circles"), "parking": "going in circles"}
        self.assertEqual(self.program.ended(held, False, ("paused", "person", "lunch")), "held")
        self.assertEqual(held["halted"][:2], ("paused", "person"))
        self.assertEqual(self.program.ended({"parking": "circles"}, False, ("", "", "")), "parked")


class CommandTest(HelmBase):
    def test_the_one_command_the_captain_is_handed_is_accepted_in_a_project_with_a_space(self) -> None:
        spaced = Path(tempfile.mkdtemp()) / "My Project"
        (spaced / "scripts/agents").mkdir(parents=True)
        (spaced / "project.json").write_text("{}", encoding="utf-8")
        for name in CARRIED:
            shutil.copy(AGENTS / name, spaced / "scripts/agents" / name)
        agent, events = loaded(spaced, "captain_agent"), loaded(spaced, "captain_events")
        command = agent.order_command()
        self.assertTrue(agent.ordering({"rawInput": {"command": f"{command} none --why x --event e"}}))
        held = {"id": "e1", "kind": "stuck", "may": ["none"]}
        self.assertIn(command, agent.prompt("ORD", spaced / "e.json", spaced / "s.json", held))
        env = events.Helm(spaced / ".slipwai", "ORD", Runner(None), self.stream).environment()
        offered = [value for value in env.values()
                   if "orders.py" in value and " " in value.replace(str(spaced.resolve()), "")]
        self.assertEqual(offered, [], "a second spelling of the command, which the captain could be told to use")
        self.assertNotIn("SLIPWAI_CAPTAIN_ORDERS_CMD", (TOOLKIT_ROOT / "agents/drive-captain.md").read_text("utf-8"))


if __name__ == "__main__":
    import unittest
    unittest.main()
