"""Installing an agent from the registry's archive, from the settings page.

What is proved: an archive for this platform is fetched, its sha256 checked and its command unpacked under
the board's folder, and the launch then finds it there; a wrong checksum throws the archive away; an archive
that reaches outside itself is not unpacked; a manifest with no checksum is a link on the page and never a
fetch; and a machine with no archive for it is told so.
"""
from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import agent_install, board_settings, harness
from slipwai.board_settings import Launch, read


def tarred(root: Path, name: str, members: dict[str, bytes]) -> tuple[str, str]:
    """A .tar.gz with these members, as a file URL, and its sha256."""
    file = root / name
    with tarfile.open(file, "w:gz") as held:
        for path, body in members.items():
            info = tarfile.TarInfo(path)
            info.size = len(body)
            info.mode = 0o644
            held.addfile(info, io.BytesIO(body))
    return file.as_uri(), hashlib.sha256(file.read_bytes()).hexdigest()


def settled(installing: agent_install.Installing, seconds: float = 20) -> dict:
    for _ in range(int(seconds / 0.05)):
        state = installing.state()
        if state["done"]:
            return state
        time.sleep(0.05)
    raise AssertionError("never done")


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.file = self.root / "board.json"
        for patched in (mock.patch.object(board_settings, "SETTINGS", self.file),
                        mock.patch.object(agent_install, "HOME", self.root / "agents"),
                        mock.patch.object(harness, "INSTALLED", self.root / "agents"),
                        mock.patch.dict(agent_install.RUNNING, clear=True)):
            patched.start()
            self.addCleanup(patched.stop)

    def test_the_archive_is_fetched_checked_unpacked_and_then_launched_from(self) -> None:
        url, digest = tarred(self.root, "goose.tar.gz", {"bin/goose": b"#!/bin/sh\necho acp\n"})
        archive = {"url": url, "sha256": digest, "cmd": "./bin/goose", "args": ["acp"]}
        with mock.patch.object(agent_install, "archive_for", return_value=archive):
            begun = agent_install.begin("goose")
        assert isinstance(begun, agent_install.Installing)
        lines = settled(begun)["lines"]
        self.assertIn("Checksum matches the registry's.", lines)
        self.assertTrue(lines[-1].startswith("Installed: "), lines)
        put = agent_install.installed("goose")
        assert put is not None
        self.assertTrue(Path(put["cmd"]).is_file())
        self.assertTrue(Path(put["cmd"]).stat().st_mode & 0o100, "made executable")
        self.assertEqual(read(self.file).ready["goose"]["install"]["fault"], "")
        argv, said = harness.acp_launch("goose", path="/nowhere")
        self.assertEqual(argv, [put["cmd"], "acp"])
        self.assertIn("installed by the board", said)
        self.assertTrue(next(one for one in board_settings.launches("/nowhere") if one.key == "goose").able)

    def test_a_wrong_checksum_throws_the_archive_away_and_a_reach_outside_is_not_unpacked(self) -> None:
        url, _ = tarred(self.root, "bad.tar.gz", {"bin/goose": b"x"})
        archive = {"url": url, "sha256": "0" * 64, "cmd": "./bin/goose", "args": []}
        with mock.patch.object(agent_install, "archive_for", return_value=archive):
            begun = agent_install.begin("goose")
        assert isinstance(begun, agent_install.Installing)
        self.assertIn("not the 000000000000… the registry gives", settled(begun)["lines"][-1])
        self.assertFalse((self.root / "agents" / "goose" / "bad.tar.gz").exists())
        self.assertIn("sha256", read(self.file).ready["goose"]["install"]["fault"])
        self.assertIsNone(agent_install.installed("goose"))
        file = self.root / "evil.zip"
        with zipfile.ZipFile(file, "w") as held:
            held.writestr("../escaped", b"x")
        archive = {"url": file.as_uri(), "sha256": hashlib.sha256(file.read_bytes()).hexdigest(), "cmd": "./x",
                   "args": []}
        with mock.patch.object(agent_install, "archive_for", return_value=archive):
            begun = agent_install.begin("goose")
        assert isinstance(begun, agent_install.Installing)
        self.assertIn("reaches outside itself", settled(begun)["lines"][-1])

    def test_no_checksum_no_archive_and_no_such_agent_are_each_said(self) -> None:
        with mock.patch.object(agent_install, "archive_for", return_value={"url": "https://x/y.zip", "cmd": "./y"}):
            self.assertIn("gives no checksum", str(agent_install.begin("goose")))
        with mock.patch.object(agent_install, "archive_for", return_value=None):
            self.assertIn("no archive for this machine", str(agent_install.begin("goose")))
        self.assertEqual(agent_install.begin("zed"), "zed is not a harness the registry can launch")
        self.assertIn(agent_install.target(), ("darwin-aarch64", "darwin-x86_64", "linux-aarch64", "linux-x86_64",
                                               "windows-aarch64", "windows-x86_64", ""))
        found = agent_install.archive_for("goose", "linux-x86_64")
        assert found is not None
        self.assertTrue(found["url"].endswith(".tar.bz2"))
        self.assertEqual(len(found["sha256"]), 64)
        self.assertIsNone(agent_install.archive_for("cursor-agent", "nowhere-x"))
        self.assertNotIn("sha256", agent_install.archive_for("cursor-agent", "darwin-aarch64") or {})


class InstallPageTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.file = self.root / "board.json"
        for patched in (mock.patch.object(board_settings, "SETTINGS", self.file),
                        mock.patch.object(agent_install, "HOME", self.root / "agents"),
                        mock.patch.object(harness, "INSTALLED", self.root / "agents"),
                        mock.patch.dict(agent_install.RUNNING, clear=True)):
            patched.start()
            self.addCleanup(patched.stop)

    def test_the_page_offers_install_where_the_archive_is_checked_and_the_link_where_it_is_not(self) -> None:
        rows = [Launch("goose", "Goose", (), "not on PATH"), Launch("cursor-agent", "Cursor", (), "not on PATH")]
        with mock.patch("slipwai.settings_page.launches", return_value=rows), \
                mock.patch.object(agent_install, "target", return_value="darwin-aarch64"):
            page = self.get("/settings")[1]
        self.assertIn('data-install="goose">Install 1.57.0</button>', page)
        self.assertIn("checked against the registry's sha256", page)
        self.assertIn("gives no checksum for this platform", page)
        self.assertIn('href="https://downloads.cursor.com/', page)
        self.assertEqual(self.post("/settings/install", {"key": "zed"})[0], 400)
        url, digest = tarred(self.root, "goose.tar.gz", {"goose": b"#!/bin/sh\n"})
        archive = {"url": url, "sha256": digest, "cmd": "./goose", "args": ["acp"]}
        with mock.patch.object(agent_install, "archive_for", return_value=archive):
            self.assertEqual(self.post("/settings/install", {"key": "goose"}), (200, "Installing Goose…"))
        for _ in range(400):
            state = json.loads(self.get("/settings/install.json?key=goose")[1])
            if state["done"]:
                break
            time.sleep(0.05)
        self.assertTrue(state["lines"][-1].startswith("Installed: "), state)
        self.assertIn("installed by the board", self.get("/settings")[1])


if __name__ == "__main__":
    unittest.main()
