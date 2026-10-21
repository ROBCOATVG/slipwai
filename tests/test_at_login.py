"""The login service: what is written, where, and what is run to load it.

Nothing here loads anything. `run` is a seam the suite fills with a recorder, and `home` is a temporary
directory, so a test run leaves this machine exactly as it found it — which matters more than usual for a
module whose whole job is to change what a machine does at login.

All three platforms are rendered here whatever this one is. A unit file that only its own platform's CI
ever looks at is a file that is wrong on the other two for a year.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.at_login import (
    LABEL,
    MAY_FAIL,
    argv,
    board_install,
    install,
    launchd,
    ran,
    remove,
    startup,
    systemd,
)


class Recorder:
    """Every command it was asked to run, and the answer it gave to each."""

    def __init__(self, code: int = 0) -> None:
        self.seen: list[list[str]] = []
        self.code = code

    def __call__(self, line: list[str], **_: object) -> subprocess.CompletedProcess:
        self.seen.append(line)
        return subprocess.CompletedProcess(line, self.code, "", "it would not" if self.code else "")


@unittest.skipIf(sys.platform == "win32",
                 "the shapes are read in POSIX path spelling; Windows spells /projects its own way")
class ShapeTest(unittest.TestCase):
    """What each platform's file says."""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.line = argv(Path("/projects"), "127.0.0.1", 8099)

    def test_what_it_runs_is_this_copy_serving_and_opening_nothing(self) -> None:
        """`--serve`, because nobody is at the machine when a login service starts."""
        self.assertEqual(self.line[-8:],
                         ["bridge", "--serve", "--root", "/projects",
                          "--host", "127.0.0.1", "--port", "8099"])

    def test_the_launchd_agent_is_started_at_login_and_restarted_only_when_it_falls_over(self) -> None:
        """It ends cleanly when a board is already serving, and `KeepAlive: true` would then start another
        one every ten seconds for as long as the first was up."""
        one = launchd(self.line, self.home)
        self.assertEqual(one.path, self.home / f"Library/LaunchAgents/{LABEL}.plist")
        self.assertIn("<key>RunAtLoad</key><true/>", one.text)
        self.assertIn("<key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>", one.text)
        self.assertIn(f"<string>{LABEL}</string>", one.text)
        self.assertIn(str(self.home / ".slipwai/board.log"), one.text)

    def test_a_restart_of_the_board_leaves_the_fleet_it_cast_off_running(self) -> None:
        """Every board restart stopped hr-test-2's captains mid-slice: launchd and systemd both end every
        process a service started, unless told the service's children are not theirs to end."""
        self.assertIn("<key>AbandonProcessGroup</key><true/>", launchd(self.line, self.home).text)
        self.assertIn("KillMode=process\n", systemd(self.line, self.home).text)

    def test_the_launchd_agent_is_started_in_the_directory_it_serves(self) -> None:
        """launchd starts an agent in `/`, and a board whose process holds `/` proposed it as the output
        parent and read it wherever a verb reads where it is — which, on macOS, is a read-only filesystem."""
        one = launchd(self.line, self.home, Path("/projects"))
        self.assertIn("<key>WorkingDirectory</key><string>/projects</string>", one.text)
        self.assertNotIn("WorkingDirectory", launchd(self.line, self.home).text)

    def test_the_launchd_agent_replaces_one_that_is_already_there(self) -> None:
        """`bootout` before `bootstrap`, and it is an error when there was nothing to boot out — which is
        every first install, so that step is allowed to fail and nothing else is."""
        one = launchd(self.line, self.home)
        self.assertEqual(one.load[0][1], "bootout")
        self.assertEqual(one.load[0][-1], MAY_FAIL)
        self.assertEqual(one.load[1][1], "bootstrap")

    def test_the_systemd_unit_is_enabled_started_and_restarted(self) -> None:
        one = systemd(self.line, self.home)
        self.assertEqual(one.path, self.home / f".config/systemd/user/{LABEL}.service")
        self.assertIn("Restart=on-failure", one.text)
        self.assertIn("WantedBy=default.target", one.text)
        self.assertIn(["systemctl", "--user", "enable", "--now", f"{LABEL}.service"],
                      [list(step) for step in one.load])

    def test_the_systemd_unit_is_started_in_the_directory_it_serves(self) -> None:
        one = systemd(self.line, self.home, Path("/projects"))
        self.assertIn("WorkingDirectory=/projects\n", one.text)
        self.assertIn('WorkingDirectory="/My Projects"\n',
                      systemd(self.line, self.home, Path("/My Projects")).text)

    def test_an_exec_start_argument_with_a_space_in_it_is_quoted(self) -> None:
        """systemd splits that line on spaces, and a path with a space in it is a path somebody has."""
        one = systemd(argv(Path("/My Projects"), "127.0.0.1", 8099), self.home)
        self.assertIn('"/My Projects"', one.text)

    def test_windows_gets_a_file_in_the_startup_folder_and_says_when_it_takes_effect(self) -> None:
        """No service manager and no administrator: the one shape that needs neither."""
        one = startup(self.line, self.home, Path("C:/projects"))
        self.assertEqual(one.path.name, "slipwai-board.cmd")
        self.assertIn("cd /d C:/projects\r\n", one.text)
        self.assertIn("Startup", str(one.path))
        self.assertIn("bridge", one.text)
        self.assertIn("next sign-in", one.at_next)


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.root = Path(tempfile.mkdtemp())

    def test_installing_writes_the_file_and_loads_it(self) -> None:
        run = Recorder()
        said = install(self.root, "127.0.0.1", 8099, self.home, run)
        written = [path for path in self.home.rglob("*") if path.is_file()]
        self.assertEqual(len(written), 1, written)
        self.assertTrue(written[0].read_text(encoding="utf-8").strip())
        self.assertIn(str(self.root.resolve()), written[0].read_text(encoding="utf-8"))
        # The Startup folder needs no loader: Windows reads it at sign-in, so nothing is run to load it there.
        self.assertEqual(bool(run.seen), sys.platform != "win32", "nothing was run to load it")
        self.assertIn("http://127.0.0.1:8099/", " ".join(said))

    def test_it_says_where_it_starts_and_how_to_undo_it(self) -> None:
        said = " ".join(install(self.root, "127.0.0.1", 8099, self.home, Recorder()))
        self.assertIn(str(self.root.resolve()), said)
        self.assertIn("bridge uninstall", said)


class BoardInstallTest(unittest.TestCase):
    """`bridge install`: the service, and then the window — which only a person can actually install."""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.root = Path(tempfile.mkdtemp())
        self.opened: list[str] = []

    def install(self, up: bool) -> str:
        return " ".join(board_install(self.root, "127.0.0.1", 8099, self.home, Recorder(),
                                      self.opened.append, lambda: up))

    def test_it_opens_the_board_so_the_browser_can_be_asked(self) -> None:
        """No command can install a page: that is a gesture a person makes, by browser rule."""
        said = self.install(up=True)
        self.assertEqual(self.opened, ["http://127.0.0.1:8099/"])
        self.assertIn("Install this board", said)

    def test_a_board_that_never_came_up_opens_nothing_and_says_so(self) -> None:
        """A browser sent to a port nothing is listening on is a blank tab and a person who concludes the
        command is broken."""
        said = self.install(up=False)
        self.assertEqual(self.opened, [])
        self.assertIn("did not come up", said)

    def test_a_step_that_failed_is_said_rather_than_swallowed(self) -> None:
        """The file is written either way: a person who was told it worked and finds no board has nothing
        to go on, which is the one outcome worth preventing here."""
        said = " ".join(install(self.root, "127.0.0.1", 8099, self.home, Recorder(code=2)))
        if sys.platform == "win32":  # the Startup folder runs no step, so there is nothing to fail
            self.assertNotIn("exited", said)
        else:
            self.assertIn("exited 2", said)

    def test_a_step_allowed_to_fail_is_not_reported(self) -> None:
        self.assertEqual(ran([("anything", MAY_FAIL)], Recorder(code=1)), [])

    def test_removing_unloads_it_and_deletes_the_file(self) -> None:
        run = Recorder()
        install(self.root, "127.0.0.1", 8099, self.home, run)
        said = remove(self.home, run)
        self.assertEqual([path for path in self.home.rglob("*") if path.is_file()], [])
        self.assertIn("no longer starts with you", " ".join(said))

    def test_removing_what_was_never_installed_is_not_a_failure(self) -> None:
        """Somebody running this wants to know the board will not come back, not whether there was a file."""
        self.assertIn("no longer starts with you", " ".join(remove(self.home, Recorder())))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
