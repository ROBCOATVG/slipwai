"""The app opened from a download: placed, the board registered from the placed copy, the board opened.

What is proved: a copy is placed only in an Applications folder on macOS, never on a translocated path, and in
the per-user programs folder on Windows; a declined move serves the board from this process and registers
nothing; a placed copy registers the login service once and leaves an identical one alone; `slipwai` is linked
for the board's children only where the machine has none of its own; the app with any argument is the command;
and the strip says a newer version once and nothing without one.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import app, first_run, update_strip


class PlacedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())

    def test_macos_wants_an_applications_folder(self) -> None:
        inside = "Slipwai.app/Contents/MacOS/slipwai"
        self.assertTrue(first_run.placed(Path("/Applications") / inside, "darwin", self.home))
        self.assertTrue(first_run.placed(self.home / "Applications" / inside, "darwin", self.home))
        self.assertFalse(first_run.placed(self.home / "Downloads" / inside, "darwin", self.home))
        self.assertFalse(first_run.placed(Path("/private/var/folders/x/AppTranslocation/ab12/d") / inside,
                                          "darwin", self.home))
        self.assertFalse(first_run.placed(Path("/usr/local/bin/slipwai"), "darwin", self.home))

    def test_windows_wants_the_per_user_programs_folder(self) -> None:
        local = {"LOCALAPPDATA": str(self.home / "Local")}
        self.assertTrue(first_run.placed(self.home / "Local/Programs/slipwai/slipwai-board.exe", "win32",
                                         environ=local))
        self.assertFalse(first_run.placed(self.home / "Downloads/slipwai-board.exe", "win32", environ=local))

    def test_a_declined_move_serves_here_and_registers_nothing(self) -> None:
        app_path = self.home / "Downloads/Slipwai.app"
        with mock.patch.object(first_run, "placed", return_value=False), \
                mock.patch.object(first_run, "bundle", return_value=app_path), \
                mock.patch.object(first_run, "ask_move", return_value=False), \
                mock.patch.object(first_run, "serve_here") as served, \
                mock.patch.object(first_run, "register") as registered:
            self.assertEqual(first_run.start(self.home, "darwin"), "here")
        served.assert_called_once()
        registered.assert_not_called()

    def test_an_accepted_move_starts_the_placed_copy(self) -> None:
        app_path = self.home / "Downloads/Slipwai.app"
        moved = self.home / "Applications/Slipwai.app"
        with mock.patch.object(first_run, "placed", return_value=False), \
                mock.patch.object(first_run, "bundle", return_value=app_path), \
                mock.patch.object(first_run, "ask_move", return_value=True), \
                mock.patch.object(first_run, "move_app", return_value=moved), \
                mock.patch.object(first_run.subprocess, "Popen") as started:
            self.assertEqual(first_run.start(self.home, "darwin"), "moved")
        self.assertEqual(started.call_args.args[0], ["open", "-n", str(moved)])

    def test_a_placed_copy_registers_and_opens_the_board(self) -> None:
        opened: list[str] = []
        with mock.patch.object(first_run, "placed", return_value=True), \
                mock.patch.object(first_run, "link_command"), \
                mock.patch.object(first_run, "register", return_value=["written"]), \
                mock.patch.object(first_run, "running", return_value=True):
            self.assertEqual(first_run.start(self.home, "darwin", open_page=opened.append), "registered")
        self.assertEqual(opened, ["http://127.0.0.1:8099/"])


class RegisterTest(unittest.TestCase):
    def test_the_service_is_written_once_and_an_identical_one_left_alone(self) -> None:
        home = Path(tempfile.mkdtemp())
        written = []

        def install(root, host, port, at):
            one = first_run.at_login.service(root, host, port, at)
            one.path.parent.mkdir(parents=True, exist_ok=True)
            one.path.write_text(one.text, encoding="utf-8")
            written.append(one.path)
            return ["written"]

        self.assertEqual(first_run.register(home, home, install), ["written"])
        self.assertEqual(first_run.register(home, home, install), [])
        self.assertEqual(len(written), 1)


@unittest.skipIf(os.name == "nt", "the link is a shell wrapper here")
class LinkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tools = Path(tempfile.mkdtemp()) / "tools"
        self.exe = Path(tempfile.mkdtemp()) / "slipwai"
        self.exe.write_text("", encoding="utf-8")

    def test_linked_for_the_children_where_the_machine_has_none(self) -> None:
        link = first_run.link_command(self.exe, self.tools, path="/nowhere", system="darwin")
        assert link is not None
        self.assertIn(str(self.exe.resolve()), link.read_text())
        record = json.loads((self.tools / "slipwai/tool.json").read_text())
        self.assertEqual(record["bin"], str(link.parent))

    def test_on_windows_a_cmd_and_a_wrapper_bash_can_start(self) -> None:
        link = first_run.link_command(self.exe, self.tools, path="/nowhere", system="win32")
        assert link is not None
        self.assertEqual(link.name, "slipwai")
        self.assertTrue((link.parent / "slipwai.cmd").is_file())
        self.assertTrue(link.read_text().startswith("#!/bin/sh\n"))

    def test_a_slipwai_of_their_own_means_no_link(self) -> None:
        theirs = Path(tempfile.mkdtemp())
        (theirs / "slipwai").write_text("#!/bin/sh\n", encoding="utf-8")
        (theirs / "slipwai").chmod(0o755)
        self.assertIsNone(first_run.link_command(self.exe, self.tools, path=str(theirs), system="darwin"))
        self.assertFalse(self.tools.exists())


class AppTest(unittest.TestCase):
    def test_with_any_argument_it_is_the_command(self) -> None:
        with mock.patch.object(app, "command") as command, mock.patch.object(app.first_run, "start") as start, \
                mock.patch.object(sys, "argv", ["slipwai"]):
            app.main(["bridge", "--serve"])
        command.assert_called_once()
        start.assert_not_called()

    def test_with_nothing_it_is_the_first_launch(self) -> None:
        with mock.patch.object(app, "command") as command, mock.patch.object(app.first_run, "start") as start:
            app.main(["-psn_0_12345"])
        start.assert_called_once()
        command.assert_not_called()


class StripTest(unittest.TestCase):
    def test_a_newer_version_is_said_with_the_way_to_it(self) -> None:
        self.assertIn("releases/latest", update_strip.banner("9.0.0", frozen=True))
        self.assertIn("slipwai upgrade", update_strip.banner("9.0.0", frozen=False))
        self.assertEqual(update_strip.banner("", frozen=True), "")

    def test_no_network_is_no_strip_and_asked_once_a_day(self) -> None:
        asked = []

        def ask() -> str | None:
            asked.append(1)
            raise OSError("no network")

        newer = update_strip.Newer(ask, clock=lambda: 1000.0)
        self.assertIsNone(newer.now(background=False))
        self.assertIsNone(newer.now(background=False))
        self.assertEqual(len(asked), 1)


if __name__ == "__main__":
    unittest.main()
