"""What a conversation believes, and the setting that says whether a fleet's sessions take the protocol.

What is proved: a signed message copied into another slice's inbox, or back out of `done/`, is refused; a
control message has a receipt as a message does; a message waiting on a paused, stopped or merged slice
says why; the key is made private from its first byte, made again where it was emptied, and refused —
loudly, and never used — where it is anybody else's; and a project that says nothing about `sessions`
stays in print mode, where `auto` takes the protocol on a proven launch.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from test_drive import loaded

from slipwai import talk


class TrustTest(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.home = talk.place(self.folder, "ORD", "ORD-01")
        self.other = talk.place(self.folder, "ORD", "ORD-02")

    def state(self, home: Path, ident: str) -> dict:
        return next(one for one in talk.receipts(home) if one["id"] == ident)

    def test_a_signed_message_copied_to_another_slice_or_back_out_of_done_is_refused(self) -> None:
        sent = talk.send(self.home, "resume")
        copied = self.other / "inbox" / f"{sent['id']}.json"
        copied.parent.mkdir(parents=True)
        shutil.copy(self.home / "inbox" / f"{sent['id']}.json", copied)
        self.assertEqual(talk.pending(self.other), [], "signed for ORD-01, so nothing to ORD-02")
        self.assertEqual([why for _, why in talk.refused(self.other)], [talk.UNSIGNED])
        talk.settle(self.home, sent["id"])
        shutil.copy(self.home / "inbox" / "done" / f"{sent['id']}.json", self.home / "inbox" / f"{sent['id']}.json")
        self.assertEqual(talk.pending(self.home), [], "an id handled already is not handled twice")
        self.assertEqual([why for _, why in talk.refused(self.home)], ["it was handled already"])

    def test_a_control_has_a_receipt_and_a_waiting_message_says_why(self) -> None:
        pause = talk.send(self.home, "pause", "lunch")
        said = talk.send(self.home, "say", "when you are back")
        self.assertEqual(self.state(self.home, pause["id"])["state"], "queued")
        talk.note(self.home, "seen", id=pause["id"])
        talk.note(self.home, "paused", by="person", why="lunch")
        self.assertEqual((self.state(self.home, pause["id"])["kind"], self.state(self.home, pause["id"])["state"]),
                         ("pause", "done"))
        self.assertEqual(self.state(self.home, said["id"])["why"], "paused: delivered when it is resumed")
        talk.note(self.home, "stopped", by="person")
        self.assertEqual(self.state(self.home, said["id"])["why"], "stopped by you: resume it to deliver this")
        talk.note(self.home, "merged")
        self.assertEqual(self.state(self.home, said["id"])["why"], "this slice has merged")

    def test_the_key_is_private_from_its_first_byte_and_made_again_where_it_was_emptied(self) -> None:
        self.assertEqual(talk.ready(self.folder), "")
        path = self.folder / "talk" / ".key"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        sent = talk.send(self.home, "say", "hello")
        path.write_bytes(b"")
        self.assertFalse(talk.genuine(self.home, sent), "an emptied key believes nothing")
        self.assertEqual(talk.ready(self.folder), "")
        self.assertEqual(len(path.read_bytes()), talk.KEY_BYTES, "and is made again")

    def test_a_key_somebody_else_wrote_is_said_and_never_used(self) -> None:
        path = self.folder / "talk" / ".key"
        path.parent.mkdir(parents=True)
        path.write_bytes(os.urandom(32))
        os.chmod(path, 0o644)
        self.assertIn("can be read by others", talk.ready(self.folder))
        with self.assertRaises(ValueError) as refused:
            talk.send(self.home, "say", "hello")
        self.assertIn("Remove", str(refused.exception))
        os.chmod(path, 0o000)
        if os.access(path, os.R_OK):
            self.skipTest("this user reads a file whatever its mode")
        with self.assertRaises(ValueError) as unreadable:
            talk.send(self.home, "say", "hello")
        self.assertIn("cannot be read", str(unreadable.exception))
        os.chmod(path, 0o600)


class SettingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.drive = loaded(self.root)
        self.was = os.environ.pop("SLIPWAI_ACP", None)
        self.addCleanup(self.restore)
        self.drive.proven = lambda: (["agent"], {"name": "proven"}, "agent: proven")  # a proven launch, here

    def restore(self) -> None:
        if self.was is not None:
            os.environ["SLIPWAI_ACP"] = self.was

    def setting(self, held: dict) -> None:
        (self.root / ".specify").mkdir(exist_ok=True)
        (self.root / ".specify" / "cruise.json").write_text(json.dumps(held), encoding="utf-8")

    def test_a_project_that_says_nothing_about_sessions_stays_in_print_mode(self) -> None:
        self.setting({"enabled": False})
        self.assertIsNone(self.drive.protocol(), "migrating never switches a project")
        self.setting({"sessions": "print"})
        self.assertIsNone(self.drive.protocol())
        self.setting({"sessions": "auto"})
        self.assertEqual(self.drive.protocol()[0], ["agent"], "auto takes the proven launch")


if __name__ == "__main__":
    unittest.main()
