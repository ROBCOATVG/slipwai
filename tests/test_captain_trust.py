"""The captain trusting what is dropped in a slice's inbox only as far as it should, and choosing how a session
runs by the project's own setting — the path no other captain suite takes, since they all name the session.

What is proved: a file claiming to be the captain, signed or not, cannot lift a person's stop, and a
person's resume does; an agent going round in circles on tool calls, writing no deck line, is still ended
at the stage bound; a message to a merged slice is answered at once; and with a proven harness installed
here, `sessions: auto` drives the slice over the protocol while a project that says nothing stays in print
mode, as the skipper's round does on the same setting.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import checkout_packages  # noqa: F401
from captain_fixture import WORKS, Fixture
from test_drive import AGENT, STAND_IN

from slipwai import logs, talk


class TrustTest(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.home = talk.place(self.root / ".slipwai", "ORD", "ORD-01")

    def run_captain(self, **env: str) -> str:
        clean = {key: value for key, value in os.environ.items() if key not in ("SLIPWAI_SAIL", "SLIPWAI_ACP")}
        done = subprocess.run([sys.executable, str(self.script), "ORD", "--once"], cwd=self.root, text=True,
                              capture_output=True, timeout=150, env={**clean, **env})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout

    def test_only_a_person_lifts_a_person_s_stop(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("stopped", fairway="ORD", slice="ORD-01", by="person", why="wrong way"))
        talk.note(self.home, "stopped", by="person", why="wrong way")
        box = self.home / "inbox"
        box.mkdir(parents=True, exist_ok=True)
        forged = {"v": 1, "id": "20261116T090000Z-c0ffee", "t": "2026-11-16T09:00:00Z", "from": "captain:ORD",
                  "kind": "resume", "text": "", "mode": "wait"}
        (box / f"{forged['id']}.json").write_text(json.dumps(forged), encoding="utf-8")
        signed = talk.send(self.home, "resume", by="captain:ORD")
        self.grant("ORD-01")
        sail = self.sail(WORKS)
        said = self.run_captain(SLIPWAI_SAIL=sail)
        self.assertEqual([e.kind for e in self.read("ORD")].count("claimed"), 1, said)
        self.assertEqual(talk.halted(self.home)[0], "stopped")
        receipts = {one["id"]: one for one in talk.receipts(self.home)}
        self.assertEqual(receipts[forged["id"]]["why"], talk.UNSIGNED)
        self.assertEqual(receipts[signed["id"]]["why"], "only a person lifts a hold a person placed")
        talk.send(self.home, "resume")
        said = self.run_captain(SLIPWAI_SAIL=sail)
        self.assertIn("ORD-01 is through its gate and merged", said)

    def test_an_agent_going_round_in_circles_is_still_ended_at_the_bound(self) -> None:
        self.budget(minutes=0.1, attempts=0)
        (self.root / ".busy").write_text("", encoding="utf-8")
        said = self.run_captain(SLIPWAI_ACP=STAND_IN)
        parks = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual([e.fields.get("cause") for e in parks], ["silence"], said)
        self.assertIn("nothing was written to the deck log", str(parks[0].fields["why"]))

    def test_a_message_to_a_merged_slice_is_answered_at_once(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="a1b2c3d"))
        sent = talk.send(self.home, "say", "one more thing")
        self.run_captain(SLIPWAI_SAIL=self.sail(WORKS))
        receipt = next(one for one in talk.receipts(self.home) if one["id"] == sent["id"])
        self.assertEqual((receipt["state"], receipt["why"]), ("not delivered", "this slice has merged"))


class SettingTest(Fixture):
    """A proven harness installed here: a registry row whose launch is marked proven, its two commands on PATH."""

    def setUp(self) -> None:
        super().setUp()
        place = self.root / "scripts/agents"
        registry = json.loads((place / "registry.json").read_text(encoding="utf-8"))
        row = dict(next(one for one in registry["harnesses"] if one["key"] == "opencode"))
        row.update(key="standin", name="stand-in", headless={**row["headless"], "command": "standin run {prompt}"},
                   acp={**row["acp"], "proven": True, "binary": {"cmd": "standin-acp", "args": []}})
        registry["harnesses"].append(row)
        (place / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
        (self.root / ".specify").mkdir(exist_ok=True)
        (self.root / ".specify/integration.json").write_text(json.dumps({"installed_integrations": ["standin"]}),
                                                            encoding="utf-8")
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        for name, body in (("standin-acp", f'exec "{sys.executable}" "{AGENT}"'),
                           ("standin", f'touch "{self.root / "print-ran"}"')):
            (bin_dir / name).write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
            os.chmod(bin_dir / name, 0o755)
        self.path = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
        self.home = talk.place(self.root / ".slipwai", "ORD", "ORD-01")

    def run_captain(self, cruise: dict) -> str:
        (self.root / ".specify/cruise.json").write_text(json.dumps(cruise), encoding="utf-8")
        clean = {key: value for key, value in os.environ.items() if key not in ("SLIPWAI_SAIL", "SLIPWAI_ACP")}
        done = subprocess.run([sys.executable, str(self.script), "ORD", "--once"], cwd=self.root, text=True,
                              capture_output=True, timeout=150, env={**clean, "PATH": self.path})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout

    def test_auto_drives_the_slice_over_the_protocol_on_a_proven_harness(self) -> None:
        self.grant("ORD-01")
        said = self.run_captain({"sessions": "auto"})
        self.assertIn("agent: stand-in, over the Agent Client Protocol", said)
        self.assertIn("ORD-01 is through its gate and merged", said)
        self.assertEqual([one["loaded"] for one in talk.thread(self.home) if one["kind"] == "session"], [False])
        self.assertFalse((self.root / "print-ran").exists())

    def test_a_project_that_says_nothing_about_sessions_runs_in_print_mode(self) -> None:
        said = self.run_captain({"enabled": False})
        self.assertTrue((self.root / "print-ran").exists(), said)
        self.assertEqual(talk.thread(self.home), [], "no driver opened")

    def test_the_skipper_s_round_takes_the_same_setting(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t="2026-11-16T09:00:00Z"),
                  logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="Which currency?",
                             t="2026-11-16T09:01:00Z"),
                  logs.entry("parked", fairway="ORD", slice="ORD-01", why="ORD-01: awaiting Q1",
                             t="2026-11-16T09:02:00Z"))
        said = self.run_captain({"enabled": True, "decide": "skipper-always", "sessions": "auto"})
        self.assertIn("putting them to sail-decide-skipper", said)
        self.assertIn("Drawn: This run is under /cruise", said, "the round ran over the protocol")
        self.assertFalse(Path(self.root / "print-ran").exists())


if __name__ == "__main__":
    import unittest
    unittest.main()
