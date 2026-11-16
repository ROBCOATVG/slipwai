"""What a third review of the held driver found, each held by a test: whose hold a slice is under, receipts
that outlive a remade key, a key on a platform with no modes, a resume with nothing to lift, the reaper's
reading of `ps`, a key that cannot be placed, and a message delivered ahead of the captain's prompt.

What is proved: a person's pause or stop stands through anybody else's stop until a person resumes it; a
message handled before the key was made again keeps its receipt, and one still queued says the key changed,
with its text; the key's mode is not asked where the platform has none; a resume with nothing held is done
without a failure; `ps` is read in the C locale, a record whose agent cannot be read is kept, and a captain's
pid reused by a stranger does not shelter the agent it left; a key the file system will not place is said,
not raised; and only a message answered after the captain's turn makes the gate be read again.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import checkout_packages  # noqa: F401
from test_drive import loaded

from slipwai import talk


class HoldTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = talk.place(Path(tempfile.mkdtemp()), "ORD", "ORD-01")

    def test_a_person_s_pause_stands_through_a_captain_s_stop_until_a_person_resumes(self) -> None:
        talk.note(self.home, "paused", by="person", why="lunch")
        talk.note(self.home, "stopped", by="captain:ORD", why="stuck")
        self.assertEqual(talk.halted(self.home), ("paused", "person", "lunch"))
        talk.note(self.home, "resumed", by="captain:ORD")
        self.assertEqual(talk.halted(self.home)[0], "paused", "a captain's resume lifts nothing a person placed")
        talk.note(self.home, "resumed", by="person")
        self.assertEqual(talk.halted(self.home)[0], "")

    def test_a_person_s_stop_stands_through_another_stop(self) -> None:
        talk.note(self.home, "stopped", by="person", why="wrong way")
        talk.note(self.home, "stopped", by="captain:ORD")
        talk.note(self.home, "paused", by="captain:ORD")
        self.assertEqual(talk.halted(self.home), ("stopped", "person", "wrong way"))

    def test_a_captain_s_own_stop_still_hands_the_slice_back(self) -> None:
        talk.note(self.home, "paused", by="captain:ORD")
        talk.note(self.home, "stopped", by="captain:ORD")
        self.assertEqual(talk.halted(self.home)[0], "")


class RekeyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.home = talk.place(self.folder, "ORD", "ORD-01")

    def remake_key(self) -> None:
        key = self.folder / "talk" / ".key"
        key.unlink()
        talk.ready(self.folder)
        later = time.time() + 2
        os.utime(key, (later, later))

    def test_history_keeps_its_receipts_after_the_key_is_made_again(self) -> None:
        answered = talk.send(self.home, "say", "use euros")
        talk.note(self.home, "seen", id=answered["id"])
        talk.note(self.home, "delivered", id=answered["id"], mode="wait")
        talk.note(self.home, "reply", to=answered["id"], text="Done.")
        talk.settle(self.home, answered["id"])
        waiting = talk.send(self.home, "say", "and round down")
        self.remake_key()
        states = {one["id"]: one for one in talk.receipts(self.home)}
        self.assertEqual(states[answered["id"]]["state"], "answered")
        self.assertEqual((states[waiting["id"]]["state"], states[waiting["id"]]["why"]),
                         ("not delivered", talk.REKEYED))
        for path, why in talk.refused(self.home):
            talk.reject(self.home, path, why)
        refused = [one for one in talk.receipts(self.home) if one["id"] == waiting["id"] and not one["kind"]]
        self.assertEqual([(one["why"], one["text"]) for one in refused], [(talk.REKEYED, "and round down")])

    def test_a_signed_message_copied_in_after_the_key_is_still_a_forgery(self) -> None:
        other = talk.place(self.folder, "ORD", "ORD-02")
        sent = talk.send(other, "say", "hello")
        (self.home / "inbox").mkdir(parents=True, exist_ok=True)
        (self.home / "inbox" / f"{sent['id']}.json").write_text(
            (other / "inbox" / f"{sent['id']}.json").read_text(encoding="utf-8"), encoding="utf-8")
        self.assertEqual([why for _, why in talk.refused(self.home)], [talk.UNSIGNED])


class KeyTest(unittest.TestCase):
    def test_a_platform_with_no_modes_is_not_asked_for_one(self) -> None:
        folder = Path(tempfile.mkdtemp())
        path = folder / "talk" / ".key"
        path.parent.mkdir(parents=True)
        path.write_bytes(os.urandom(talk.KEY_BYTES))
        os.chmod(path, 0o644)
        self.assertIn("can be read by others", talk.key_trouble(path))
        with mock.patch.object(talk.os, "name", "nt"):
            self.assertEqual(talk.key_trouble(path), "")

    def test_a_key_the_file_system_will_not_place_is_said_and_not_raised(self) -> None:
        folder = Path(tempfile.mkdtemp())
        with mock.patch.object(talk.os, "link", side_effect=PermissionError("no hard links here")):
            said = talk.ready(folder)
        self.assertIn("could not be placed", said)
        self.assertIn("no hard links here", said)


class DriverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.drive = loaded(self.root)
        self.home = self.drive.talk.place(self.root / ".slipwai", "ORD", "ORD-01")

    def driver(self, **held: object) -> SimpleNamespace:
        return SimpleNamespace(home=self.home, pausing=None, turning=False, holding="", interrupting="",
                               cond=threading.Condition(), end_soon=lambda: None, **held)

    def test_a_resume_with_nothing_held_is_done_without_a_failure(self) -> None:
        sent = self.drive.talk.send(self.home, "resume")
        self.drive.Drive.heard(self.driver(), sent)
        kinds = [one["kind"] for one in self.drive.talk.thread(self.home)]
        self.assertEqual(kinds, ["seen"])
        receipt = next(one for one in self.drive.talk.receipts(self.home) if one["id"] == sent["id"])
        self.assertEqual(receipt["state"], "done")

    def test_ps_is_read_in_the_c_locale(self) -> None:
        said = subprocess.CompletedProcess([], 0, "Mon Nov 16 09:00:00 2026 agent", "")
        with mock.patch.object(self.drive.subprocess, "run", return_value=said) as ran:
            self.drive.identity(1)
        self.assertEqual(ran.call_args.kwargs["env"]["LC_ALL"], "C")

    def record(self, pid: int, captain: int, captain_identity: str = "") -> Path:
        path = self.home / self.drive.AGENT_PID
        path.parent.mkdir(parents=True, exist_ok=True)
        import json
        path.write_text(json.dumps({"pid": pid, "captain": captain, "identity": "agent-then",
                                    "captain_identity": captain_identity}), encoding="utf-8")
        return path

    def test_an_agent_that_cannot_be_read_keeps_its_record(self) -> None:
        gone = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True)
        path = self.record(os.getpid() + 0, int(gone.stdout))  # the agent's pid is this process: alive
        with mock.patch.object(self.drive, "identity", return_value=""):
            self.assertEqual(self.drive.reap(self.root / ".slipwai" / "talk" / "ORD"), [])
        self.assertTrue(path.exists(), "nothing could be told, so the next captain looks again")

    def test_a_captain_s_pid_reused_by_a_stranger_does_not_shelter_its_agent(self) -> None:
        agent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
        self.addCleanup(agent.kill)
        stranger = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(stranger.kill)
        path = self.record(agent.pid, stranger.pid, captain_identity="the captain that died")
        seen = {agent.pid: "agent-then", stranger.pid: "somebody else"}
        with mock.patch.object(self.drive, "identity", side_effect=lambda pid: seen.get(pid, "")):
            self.assertEqual(self.drive.reap(self.root / ".slipwai" / "talk" / "ORD"), [agent.pid])
        agent.wait(timeout=10)
        self.assertFalse(path.exists())

    def test_only_a_message_answered_after_the_captain_s_turn_reads_the_gate_again(self) -> None:
        heads = iter(["a", "b", "c"])
        held = self.driver(outcome=None, message_since=None, message_commits=False, message_commits_person=False,
                           silent="", text="Reply", cwd=self.root, turn=lambda text, about: "end_turn")
        with mock.patch.object(self.drive, "branch_head", side_effect=lambda cwd: next(heads)):
            sent = self.drive.talk.send(self.home, "say", "before the prompt")
            self.drive.Drive.deliver(held, sent)
            self.assertFalse(held.message_commits, "delivered ahead of the captain's prompt")
            held.outcome = 0
            sent = self.drive.talk.send(self.home, "say", "after the turn")
            self.drive.Drive.deliver(held, sent)
        self.assertTrue(held.message_commits)
        self.assertTrue(held.message_commits_person, "a person's message: its re-read is free")

    def test_a_captain_s_message_that_commits_earns_no_free_run(self) -> None:
        heads = iter(["a", "b"])
        held = self.driver(outcome=0, message_since=None, message_commits=False, message_commits_person=False,
                           silent="", text="Reply", cwd=self.root, turn=lambda text, about: "end_turn")
        with mock.patch.object(self.drive, "branch_head", side_effect=lambda cwd: next(heads)):
            sent = self.drive.talk.send(self.home, "say", "rename it", by="captain:ORD")
            self.drive.Drive.deliver(held, sent)
        self.assertEqual((held.message_commits, held.message_commits_person), (True, False))


if __name__ == "__main__":
    unittest.main()
