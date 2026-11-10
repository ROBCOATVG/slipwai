"""The app opened from a download: placed, the board registered from the placed copy, the board opened.

What is proved: a copy is placed only in an Applications folder on macOS, never on a translocated path, and in
the per-user programs folder on Windows; a declined move serves the board from this process and registers
nothing; a placed copy registers the login service once and leaves an identical one alone; `slipwai` is linked
for the board's children only where the machine has none of its own; a board answering from this copy's path
but another file — the one an install replaced — is stopped and its service loaded again before the board is
opened, and a board from another path is left alone; on Windows the running file is moved aside for the new
one; the board names the file it runs on every answer; the app with any argument is the command;
the strip says a newer version once and nothing without one; and on a Mac, asked, `slipwai` goes into the
shell's profile as one marked block at the end of the `PATH`, comes out again leaving the profile as it was,
and is never offered over a `slipwai` of the person's own.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import app, board_build, cli_start, first_run, machine_card, terminal_command, update_strip
from slipwai.board_build import Build


class PlacedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())

    @unittest.skipIf(os.name == "nt", "a POSIX path resolves onto a drive on Windows")
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
                mock.patch.object(first_run, "serving", return_value=(True, Build("/elsewhere/slipwai", "1"))), \
                mock.patch.object(first_run, "running", return_value=True):
            self.assertEqual(first_run.start(self.home, "darwin", open_page=opened.append), "registered")
        self.assertEqual(opened, ["http://127.0.0.1:8099/"])

    def launched(self, board: Build | None, system: str = "darwin") -> tuple[str, mock.MagicMock]:
        with mock.patch.object(first_run, "placed", return_value=True), \
                mock.patch.object(first_run, "link_command"), \
                mock.patch.object(first_run, "register", return_value=[]), \
                mock.patch.object(first_run, "serving", return_value=(True, board)), \
                mock.patch.object(first_run, "renew", return_value=["loaded"]) as renewed, \
                mock.patch.object(first_run, "running", return_value=True):
            return first_run.start(self.home, system, open_page=lambda url: None), renewed

    def test_a_board_this_install_replaced_is_renewed_before_it_is_opened(self) -> None:
        here = board_build.executable()
        went, renewed = self.launched(Build(str(here), "an-older-file", 4242))
        self.assertEqual(went, "renewed")
        renewed.assert_called_once()

    def test_the_installed_board_and_someone_elses_are_left_alone(self) -> None:
        here = board_build.executable()
        for board in (Build(str(here), board_build.build_of(here)), Build("/opt/their/slipwai", "x")):
            went, renewed = self.launched(board)
            self.assertEqual(went, "opened")
            renewed.assert_not_called()

    def test_a_board_too_old_to_say_is_renewed_on_a_mac_only(self) -> None:
        self.assertEqual(self.launched(None, "darwin")[0], "renewed")
        went, renewed = self.launched(None, "win32")
        self.assertEqual(went, "opened")
        renewed.assert_not_called()


class RenewTest(unittest.TestCase):
    def renew(self, system: str) -> tuple[list[int], list[str]]:
        stopped: list[int] = []
        said = first_run.renew(Path("/home"), Build("x", "y", 4242), system, install=lambda *_: ["loaded"],
                               stop=stopped.append, gone=lambda: True)
        return stopped, said

    def test_on_windows_the_board_is_stopped_by_its_process_then_the_service_written(self) -> None:
        self.assertEqual(self.renew("win32"), ([4242], ["loaded"]))

    def test_on_a_mac_reloading_the_service_is_what_stops_it(self) -> None:
        self.assertEqual(self.renew("darwin"), ([], ["loaded"]))


class PlaceWindowsTest(unittest.TestCase):
    def test_the_running_copy_is_moved_aside_for_the_new_one(self) -> None:
        local = Path(tempfile.mkdtemp())
        environ = {"LOCALAPPDATA": str(local), "APPDATA": str(local)}
        folder = first_run.programs(environ)
        folder.mkdir(parents=True)
        (folder / "slipwai-board.exe").write_text("old", encoding="utf-8")
        (folder / "slipwai-board.1.old").write_text("older", encoding="utf-8")
        new = local / "download.exe"
        new.write_text("new", encoding="utf-8")
        where = first_run.place_windows(new, environ, run=mock.MagicMock())
        self.assertEqual(where.read_text(encoding="utf-8"), "new")
        self.assertEqual([one.read_text(encoding="utf-8") for one in folder.glob("slipwai-board.*.old")], ["old"])


class BoardBuildTest(unittest.TestCase):
    def test_every_answer_names_the_file_the_board_runs(self) -> None:
        server = cli_start.serve(Path(tempfile.mkdtemp()), "127.0.0.1", 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            up, board = cli_start.serving("127.0.0.1", server.server_address[1], timeout=5)
        finally:
            server.shutdown()
            server.server_close()
        self.assertTrue(up)
        self.assertEqual(board, Build(str(board_build.executable()), board_build.STARTED.build, os.getpid()))

    def test_the_same_path_holding_another_file_is_replaced(self) -> None:
        here = Path(tempfile.mkdtemp()) / "slipwai"
        here.write_text("old", encoding="utf-8")
        board = Build(str(here), board_build.build_of(here))
        self.assertFalse(board_build.replaced(board, here))
        (here.parent / "new").write_text("newer", encoding="utf-8")
        os.replace(here.parent / "new", here)
        self.assertTrue(board_build.replaced(board, here))
        self.assertFalse(board_build.replaced(Build("/somewhere/else", "x"), here))
        self.assertFalse(board_build.replaced(None, here))


class RegisterTest(unittest.TestCase):
    def test_the_service_is_written_once_and_an_identical_one_left_alone(self) -> None:
        home = Path(tempfile.mkdtemp())
        written = []

        def install(root, host, port, at):
            one = first_run.at_login.service(root, host, port, at)
            one.path.parent.mkdir(parents=True, exist_ok=True)
            one.path.write_text(one.text, encoding="utf-8", newline="")
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



class TerminalCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.tools = self.home / ".slipwai/tools"
        (self.tools / "slipwai/bin").mkdir(parents=True)
        (self.tools / "slipwai/bin/slipwai").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.tools / "slipwai/bin/slipwai").chmod(0o755)
        self.profile = self.home / ".zprofile"
        self.mine = 'eval "$(/opt/homebrew/bin/brew shellenv)"\n'
        self.profile.write_text(self.mine, encoding="utf-8")

    def state(self, path: str = "/usr/bin") -> str:
        with mock.patch.object(sys, "platform", "darwin"):
            return terminal_command.state(self.home, "/bin/zsh", self.tools, path)

    def test_added_at_the_end_of_path_and_removed_leaving_the_profile_as_it_was(self) -> None:
        self.assertEqual(self.state(), "absent")
        terminal_command.add(self.home, "/bin/zsh")
        text = self.profile.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(self.mine))
        self.assertIn('export PATH="$PATH:$HOME/.slipwai/tools/slipwai/bin"', text)
        self.assertEqual(self.state(), "added")
        terminal_command.add(self.home, "/bin/zsh")
        self.assertEqual(self.profile.read_text(encoding="utf-8"), text, "asked twice, added once")
        terminal_command.remove(self.home, "/bin/zsh")
        self.assertEqual(self.profile.read_text(encoding="utf-8"), self.mine)

    def test_bash_has_its_own_profile_and_another_shell_is_told_the_line(self) -> None:
        terminal_command.add(self.home, "/bin/bash")
        self.assertTrue(terminal_command.added(self.home / ".bash_profile"))
        self.assertIn("add this line", terminal_command.add(self.home, "/opt/homebrew/bin/fish"))

    def test_never_offered_over_their_own_slipwai_or_off_a_mac(self) -> None:
        theirs = Path(tempfile.mkdtemp())
        (theirs / "slipwai").write_text("#!/bin/sh\n", encoding="utf-8")
        (theirs / "slipwai").chmod(0o755)
        self.assertEqual(self.state(str(theirs)), "theirs")
        with mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(terminal_command.state(self.home, "/bin/zsh", self.tools, "/usr/bin"), "none")

    def test_the_card_offers_add_then_remove(self) -> None:
        self.assertIn('data-command="add"', machine_card.command_row("absent", self.profile))
        self.assertIn('data-command="remove"', machine_card.command_row("added", self.profile))
        self.assertEqual(machine_card.command_row("theirs", self.profile), "")
        self.assertIn(machine_card.esc(terminal_command.LINE), machine_card.command_row("unsupported", None))


if __name__ == "__main__":
    unittest.main()
