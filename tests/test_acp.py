"""The protocol's client half, driven over the stand-in agent in `tests/fixtures/acp_agent.py`.

What is proved is the wire: the handshake, a turn's updates in the order the agent sent them, a permission
inside and outside the working directory, a question answered, a cancel while a permission is outstanding,
a session loaded, and an agent that dies mid-turn. The stand-in is the other end of the wire held still;
nothing here reaches a real agent.
"""
from __future__ import annotations

import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from slipwai import acp
from slipwai.acp import Fault, Session, kept_session, once, policy, within

AGENT = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"


class SessionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.updates: list[dict] = []
        self.asked: list[dict] = []
        self.answer: tuple[str, dict | None] = ("accept", {"answer": "blue"})
        self.refuse = True  # what the ask callback says to a call outside the working directory
        self.hold = threading.Event()  # set to let a held permission callback return
        self.hold.set()

    def ask(self, tool_call: dict, options: list[dict]) -> str | None:
        self.asked.append(tool_call)
        self.hold.wait(10)
        return None if self.refuse else once(options)

    def session(self) -> Session:
        one = Session([sys.executable, str(AGENT)], self.home, self.updates.append,
                      policy(self.home, self.ask), lambda params: self.answer)
        self.addCleanup(one.close)
        return one

    def kinds(self) -> list[str]:
        return [str(one.get("sessionUpdate")) for one in self.updates]

    def test_the_handshake_and_a_new_session(self) -> None:
        one = self.session()
        agent = one.start()
        self.assertEqual((agent.name, agent.version, agent.load_session), ("stand-in", "0.1", True))
        self.assertEqual([one["id"] for one in agent.auth_methods], ["login", "setup"])
        self.assertEqual(one.new(), "s-1")
        self.assertEqual(kept_session(self.home / ".acp"), "s-1", "the id is kept beside the log for a later load")
        self.assertEqual([o["category"] for o in one.agent.config_options], ["model"])
        self.assertEqual(one.set_option("model", "b")[0]["currentValue"], "b")

    def test_a_turn_streams_its_updates_and_a_write_inside_the_directory_is_allowed_by_policy(self) -> None:
        one = self.session()
        one.start()
        one.new()
        self.assertEqual(one.prompt("hello"), "end_turn")
        self.assertEqual(self.kinds(), ["agent_thought_chunk", "agent_message_chunk", "tool_call", "tool_call_update"])
        self.assertEqual(self.updates[1]["content"]["text"], "Drawn: hello")
        self.assertEqual(self.updates[3]["status"], "completed")
        self.assertTrue((self.home / "prototype" / "index.html").is_file(), "the agent wrote where it was allowed")
        self.assertEqual(self.asked, [], "nobody was asked about a write inside the working directory")
        self.hold.clear()  # the next turn waits on the person, so a second prompt meanwhile is refused
        running = threading.Thread(target=one.prompt, args=("outside",), daemon=True)
        running.start()
        for _ in range(100):
            if len(self.asked) > 0:
                break
            time.sleep(0.05)
        with self.assertRaises(ValueError):
            one.prompt("twice")
        self.hold.set()
        running.join(10)

    def test_a_call_outside_the_directory_goes_to_the_person(self) -> None:
        one = self.session()
        one.start()
        one.new()
        self.assertEqual(one.prompt("outside"), "end_turn")
        self.assertEqual([c["locations"][0]["path"] for c in self.asked], ["/etc/hosts"])
        self.assertIn("refused outside", [u.get("content", {}).get("text") for u in self.updates])
        self.refuse = False
        one.prompt("outside")
        self.assertIn("wrote outside", [u.get("content", {}).get("text") for u in self.updates])

    def test_a_question_from_the_agent_is_answered_in_the_same_turn(self) -> None:
        one = self.session()
        one.start()
        one.new()
        one.prompt("ask")
        self.assertIn("You said: blue", [u.get("content", {}).get("text") for u in self.updates])
        self.answer = ("decline", None)
        one.prompt("ask")
        self.assertIn("You said: (nothing)", [u.get("content", {}).get("text") for u in self.updates])

    def test_a_cancel_answers_the_open_permission_and_the_turn_ends_cancelled(self) -> None:
        one = self.session()
        one.start()
        one.new()
        self.hold.clear()
        self.refuse = False
        ended: list[str] = []
        threading.Thread(target=lambda: ended.append(one.prompt("slow")), daemon=True).start()
        for _ in range(100):
            if any("slow.txt" in str(c.get("locations")) for c in self.asked):
                break
            time.sleep(0.05)
        else:
            self.fail("the agent never asked about the slow write")
        one.cancel()
        for _ in range(100):
            if ended:
                break
            time.sleep(0.05)
        self.assertEqual(ended, ["cancelled"])
        self.hold.set()  # the held callback returns late; its answer is dropped, not sent twice

    def test_a_session_is_loaded_where_the_agent_can_and_its_history_replayed(self) -> None:
        first = self.session()
        first.start()
        first.new()
        first.close()
        second = self.session()
        second.start()
        self.assertTrue(second.load(kept_session(self.home / ".acp")))
        self.assertEqual(second.session_id, "s-1")
        self.assertEqual(self.updates[-1]["content"]["text"], "earlier: hello again")
        self.assertEqual(second.prompt("after"), "end_turn")

    def test_an_agent_that_dies_mid_turn_is_a_fault_with_its_status(self) -> None:
        one = self.session()
        one.start()
        one.new()
        with self.assertRaises(Fault) as refused:
            one.prompt("die")
        self.assertIn("exited 3", str(refused.exception))
        with self.assertRaises(Fault):
            one.prompt("after")

    def test_a_command_that_cannot_start_is_a_fault(self) -> None:
        one = Session(["/no/such/agent"], self.home, self.updates.append, policy(self.home, self.ask),
                      lambda params: self.answer)
        with self.assertRaises(Fault):
            one.start()


class HandshakeTest(unittest.TestCase):
    def test_a_package_launch_waits_longer_for_its_handshake(self) -> None:
        """The first `npx` launch fetches the package; a cold fetch is minutes on a slow line."""
        home = Path(tempfile.mkdtemp())
        seen: list[float] = []

        def calls(method: str, params: dict, timeout: float = 0) -> dict:
            seen.append(timeout)
            return {"protocolVersion": 1}
        one = Session(["/usr/bin/npx", "--yes", "some-agent"], home, lambda u: None, lambda t, o: None,
                      lambda p: ("decline", None))
        with mock.patch.object(one, "call", side_effect=calls), mock.patch("subprocess.Popen"), \
                mock.patch("threading.Thread"):
            one.start()
        self.assertEqual(seen, [acp.FETCHING])
        two = Session([sys.executable, str(AGENT)], home, lambda u: None, lambda t, o: None,
                      lambda p: ("decline", None))
        seen.clear()
        with mock.patch.object(two, "call", side_effect=calls), mock.patch("subprocess.Popen"), \
                mock.patch("threading.Thread"):
            two.start()
        self.assertEqual(seen, [acp.TIMEOUT])

    def packaged(self, home: Path) -> Session:
        return Session(["/usr/bin/npx", "--yes", "some-agent"], home, lambda u: None, lambda t, o: None,
                       lambda p: ("decline", None))

    def test_a_package_launch_that_fell_over_is_tried_once_more_and_only_a_package_launch(self) -> None:
        """Two captains launching one agent in the same second met in npm's cache: `ENOTEMPTY … rename`, the
        runner exited, and the slice ran in print mode for its whole run."""
        home, tried = Path(tempfile.mkdtemp()), []

        def falls_over_once(one: Session) -> object:
            def shaken(waits: float) -> dict:
                tried.append(waits)
                if len(tried) == 1:
                    one.exited = 190
                    raise acp.Fault("the agent exited 190; the last it said: npm error ENOTEMPTY")
                return {"protocolVersion": 1}
            return shaken
        one = self.packaged(home)
        with mock.patch.object(one, "shaken", side_effect=falls_over_once(one)), mock.patch.object(acp, "AGAIN", 0):
            one.start()
        self.assertEqual(len(tried), 2)
        self.assertIsNone(one.exited, "the second launch starts from nothing")
        tried.clear()
        plain = Session([sys.executable, str(AGENT)], home, lambda u: None, lambda t, o: None,
                        lambda p: ("decline", None))
        with mock.patch.object(plain, "shaken", side_effect=falls_over_once(plain)), self.assertRaises(acp.Fault):
            plain.start()
        self.assertEqual(len(tried), 1, "an agent that is a binary and died is not launched twice")
        tried.clear()
        slow = self.packaged(home)
        with mock.patch.object(slow, "shaken", side_effect=acp.Fault("did not answer initialize")), \
                self.assertRaises(acp.Fault):
            slow.start()  # still running and silent: not the runner falling over, so not tried again

    @unittest.skipIf(acp.fcntl is None, "no flock on this platform")
    def test_package_launches_on_one_machine_take_turns_and_others_do_not_queue(self) -> None:
        order: list[str] = []

        def launch(name: str, held: float) -> None:
            with acp.one_at_a_time(True):
                order.append(f"{name} in")
                time.sleep(held)
                order.append(f"{name} out")
        first = threading.Thread(target=launch, args=("a", 0.4))
        first.start()
        time.sleep(0.1)
        second = threading.Thread(target=launch, args=("b", 0))
        second.start()
        with acp.one_at_a_time(False):  # not a package launch: straight through while `a` holds the turn
            order.append("plain")
        first.join()
        second.join()
        self.assertEqual(order, ["a in", "plain", "a out", "b in", "b out"])


class PolicyTest(unittest.TestCase):
    def test_within_wants_every_location_under_the_directory(self) -> None:
        home = Path(tempfile.mkdtemp())
        self.assertTrue(within(home, {"locations": [{"path": str(home / "a.txt")}]}))
        self.assertFalse(within(home, {"locations": [{"path": str(home / "a.txt")}, {"path": "/etc/hosts"}]}))
        self.assertFalse(within(home, {"locations": [{"path": str(home.parent / "b.txt")}]}))
        self.assertFalse(within(home, {}), "a call that names no file is asked about, not allowed")

    def test_once_is_the_allow_once_option_or_nothing(self) -> None:
        offered = [{"optionId": "r", "kind": "reject_once"}, {"optionId": "a", "kind": acp.ALLOW_ONCE}]
        self.assertEqual(once(offered), "a")
        self.assertIsNone(once([{"optionId": "always", "kind": "allow_always"}]))


if __name__ == "__main__":
    unittest.main()
