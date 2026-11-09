"""What a route needs on the machine, and the board installing it only where the machine has none.

What is proved: a tool is found by asking it its version on the `PATH` given, too old against its floor, and
missing where it is absent or will not answer; macOS's developer-tools shims are not run without the tools;
each route needs what the audit found, Node only on the event-modelling profile or a Node language; the
installer refuses wherever the machine has a good copy and fetches nothing, and puts one installed over an
old copy ahead of it; Node, PortableGit and Python archives are
picked with their publishers' checksums; an install unpacks under the board's tools and lands on the end of a
child's `PATH`; and the floors agree with what the keel declares. On Windows, with the platform pretended:
Git counts only with bash beside it, and Git's `usr/bin` goes first on a child's `PATH`; Python is `python`
and never the Store's stub; Make is ezwinports' pinned build; bash gets a `python3` shim that goes first;
and the card offers Git Bash in the project, with the board's `PATH`, in place of WSL.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import machine_card, prerequisites, shell_environment, tool_install
from slipwai.prerequisites import BY_KEY, Found, found, lacking, needs, version_of

ROOT = Path(__file__).resolve().parents[1]


def fake(folder: Path, command: str, said: str, code: int = 0) -> Path:
    """A command on `folder` that prints `said` for its version and exits `code`."""
    folder.mkdir(parents=True, exist_ok=True)
    one = folder / command
    one.write_text(f"#!/bin/sh\necho '{said}'\nexit {code}\n", encoding="utf-8")
    one.chmod(0o755)
    return one


@unittest.skipIf(os.name == "nt", "the fakes are shell scripts")
class FoundTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bin = Path(tempfile.mkdtemp()) / "bin"
        self.bin.mkdir()

    def test_a_tool_that_answers_is_found_with_its_version(self) -> None:
        fake(self.bin, "git", "git version 2.39.5")
        one = found(BY_KEY["git"], str(self.bin))
        self.assertEqual((one.state, one.version), ("found", "2.39.5"))

    def test_a_tool_older_than_its_floor_is_old(self) -> None:
        fake(self.bin, "python3", "Python 3.9.6")
        self.assertEqual(found(BY_KEY["python3"], str(self.bin)).state, "old")

    def test_absent_or_refusing_is_missing(self) -> None:
        self.assertEqual(found(BY_KEY["node"], str(self.bin)).state, "missing")
        fake(self.bin, "node", "broken", code=1)
        self.assertEqual(found(BY_KEY["node"], str(self.bin)).state, "missing")

    def test_go_is_asked_the_way_go_answers(self) -> None:
        go = self.bin / "go"
        go.write_text('#!/bin/sh\n[ "$1" = version ] && echo "go version go1.26.5 darwin/arm64" && exit 0\nexit 2\n',
                      encoding="utf-8")
        go.chmod(0o755)
        self.assertEqual(found(BY_KEY["go"], str(self.bin)).version, "1.26.5")

    def test_apples_shim_is_not_run_without_the_developer_tools(self) -> None:
        with mock.patch.object(sys, "platform", "darwin"), \
                mock.patch("slipwai.prerequisites.shutil.which", return_value="/usr/bin/git"), \
                mock.patch("slipwai.prerequisites.developer_tools", return_value=False), \
                mock.patch("slipwai.prerequisites.subprocess.run") as ran:
            self.assertEqual(found(BY_KEY["git"], "/usr/bin").state, "missing")
        ran.assert_not_called()


class RoutesTest(unittest.TestCase):
    def test_every_project_route_needs_git_make_and_python(self) -> None:
        for route in ("/generate", "/adopt"):
            self.assertEqual(needs(route)[:3], ["git", "make", "python3"])
        self.assertEqual(needs("/brief"), [])

    def test_node_only_on_the_event_profile_or_a_node_language(self) -> None:
        self.assertIn("node", needs("/generate"))
        self.assertNotIn("node", needs("/generate", {"profile": "standard", "language": "go"}))
        self.assertIn("node", needs("/generate", {"profile": "standard", "language": "typescript"}))
        self.assertIn("uv", needs("/generate", {"language": "python"}))

    def test_a_machine_with_everything_lacks_nothing(self) -> None:
        def look(tool: prerequisites.Tool) -> Found:
            return Found(tool, "found", "/x", "1")
        self.assertEqual(lacking("/generate", {}, look), [])

    def test_the_python_floor_is_the_keels_own(self) -> None:
        declared = re.search(r'requires-python = ">=(\d+)\.(\d+)"', (ROOT / "pyproject.toml").read_text())
        assert declared is not None
        self.assertEqual(prerequisites.PYTHON_FLOOR, (int(declared.group(1)), int(declared.group(2))))

    def test_version_of_reads_the_first_dotted_number(self) -> None:
        self.assertEqual(version_of('openjdk version "26.0.2" 2026-01-20'), (26, 0, 2))
        self.assertEqual(version_of("nothing"), ())


class ArchiveTest(unittest.TestCase):
    def test_node_is_the_newest_lts_with_its_published_checksum(self) -> None:
        index: list[dict[str, Any]] = [{"version": "v25.1.0", "lts": False},
                                       {"version": "v24.11.0", "lts": "Krypton"}]
        sums = "abc123  node-v24.11.0-darwin-arm64.tar.gz\nfff  node-v24.11.0-linux-x64.tar.xz\n"
        got = tool_install.node_archive(index, sums, "darwin", "arm64")
        self.assertEqual(got["url"], "https://nodejs.org/dist/v24.11.0/node-v24.11.0-darwin-arm64.tar.gz")
        self.assertEqual((got["sha256"], got["bin"]), ("abc123", "node-v24.11.0-darwin-arm64/bin"))
        with self.assertRaises(ValueError):
            tool_install.node_archive(index, sums, "win32", "x64")

    def test_portable_git_not_mingit_and_needs_githubs_checksum(self) -> None:
        asset = {"name": "PortableGit-2.51.0-64-bit.7z.exe", "browser_download_url": "https://x/PortableGit.7z.exe",
                 "digest": "sha256:beef"}
        mingit = {**asset, "name": "MinGit-2.51.0-64-bit.zip", "digest": "sha256:dead"}
        got = tool_install.portable_git_archive({"tag_name": "v2.51.0.windows.1", "assets": [mingit, asset]},
                                                "64-bit")
        self.assertEqual((got["sha256"], got["bin"]), ("beef", "cmd"))
        with self.assertRaises(ValueError):
            tool_install.portable_git_archive({"assets": [{**asset, "digest": None}]}, "64-bit")
        with self.assertRaises(ValueError):
            tool_install.portable_git_archive({"assets": [mingit]}, "64-bit")

    def test_make_on_windows_is_the_pinned_build(self) -> None:
        self.assertRegex(tool_install.MAKE_W32["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(tool_install.MAKE_W32["name"].endswith(".zip"))
        with mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(tool_install.way("make"), "archive")
        with mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(tool_install.way("make"), "")

    def test_python_on_windows_keeps_python_exe_at_the_top(self) -> None:
        name = "cpython-3.13.9+20261101-x86_64-pc-windows-msvc-install_only.tar.gz"
        got = tool_install.python_archive({"assets": [{"name": name, "browser_download_url": "https://x/p",
                                                       "digest": "sha256:ab"}]}, "x86_64-pc-windows-msvc")
        self.assertEqual(got["bin"], "python")

    def test_python_is_the_newest_313_for_this_machine(self) -> None:
        def asset(version: str) -> dict:
            return {"name": f"cpython-{version}+20261101-aarch64-apple-darwin-install_only.tar.gz",
                    "browser_download_url": f"https://x/{version}", "digest": f"sha256:{version}"}
        got = tool_install.python_archive({"assets": [asset("3.13.2"), asset("3.13.10"), asset("3.12.9")]},
                                          "aarch64-apple-darwin")
        self.assertEqual((got["version"], got["bin"]), ("3.13.10", "python/bin"))


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tools = Path(tempfile.mkdtemp()) / "tools"

    def test_a_good_copy_on_the_machine_means_no_install(self) -> None:
        with mock.patch("slipwai.tool_install.Installing") as made:
            said = tool_install.begin("node", self.tools, look=lambda tool: Found(tool, "found", "/n", "24.1"))
        made.assert_not_called()
        self.assertIn("already on this machine", str(said))
        self.assertFalse(self.tools.exists())

    def test_a_copy_too_old_gets_a_newer_one_that_goes_first(self) -> None:
        with mock.patch("slipwai.tool_install.Installing") as made, \
                mock.patch.object(tool_install, "way", return_value="archive"):
            tool_install.begin("python3", self.tools, look=lambda tool: Found(tool, "old", "/usr/bin/python3", "3.9.6"))
        self.assertTrue(made.call_args.kwargs["first"])

    def test_apples_installer_is_the_system_dialog_and_no_download(self) -> None:
        asked = []
        with mock.patch.object(sys, "platform", "darwin"):
            said = tool_install.begin("make", self.tools, look=lambda tool: Found(tool, "missing"),
                                      run=lambda command, **_: asked.append(command))
        self.assertIsInstance(said, tool_install.Opened)
        self.assertEqual(asked, [["xcode-select", "--install"]])

    def archive(self) -> tuple[str, str]:
        file = Path(tempfile.mkdtemp()) / "node-v24.0.0-darwin-arm64.tar.gz"
        with tarfile.open(file, "w:gz") as held:
            info = tarfile.TarInfo("node-v24.0.0-darwin-arm64/bin/node")
            info.size, info.mode = 2, 0o755
            held.addfile(info, io.BytesIO(b"#!"))
        return file.as_uri(), hashlib.sha256(file.read_bytes()).hexdigest()

    def run_install(self, sha: str, url: str, first: bool = False) -> tool_install.Installing:
        installing = tool_install.Installing("node", self.tools, first)
        archive = {"url": url, "sha256": sha, "version": "24.0.0", "bin": "node-v24.0.0-darwin-arm64/bin"}
        with mock.patch.object(installing, "archive", return_value=archive):
            installing.run()
        return installing

    def test_an_install_unpacks_under_the_tools_and_joins_the_end_of_path(self) -> None:
        url, sha = self.archive()
        self.run_install(sha, url)
        record = json.loads((self.tools / "node/tool.json").read_text())
        self.assertTrue(Path(record["bin"], "node").is_file())
        env = shell_environment.with_tools({"PATH": "/usr/bin"}, self.tools)
        self.assertEqual(env["PATH"].split(os.pathsep), ["/usr/bin", record["bin"]])

    def test_one_installed_over_an_old_copy_comes_ahead_of_it(self) -> None:
        url, sha = self.archive()
        self.run_install(sha, url, first=True)
        record = json.loads((self.tools / "node/tool.json").read_text())
        env = shell_environment.with_tools({"PATH": "/usr/bin"}, self.tools)
        self.assertEqual(env["PATH"].split(os.pathsep), [record["bin"], "/usr/bin"])

    def test_a_wrong_checksum_installs_nothing(self) -> None:
        url, _ = self.archive()
        said = self.run_install("0" * 64, url).state()["lines"]
        self.assertTrue(said[-1].startswith("! the archive's sha256"))
        self.assertFalse((self.tools / "node/tool.json").exists())


class WindowsTest(unittest.TestCase):
    """Windows, pretended: what can be proved without one. The windows-latest job runs the rest for real."""

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def git(self, name: str, bash: bool) -> Path:
        """A Git tree as Git for Windows lays one out: `cmd/git.exe`, and `usr/bin/bash.exe` unless MinGit."""
        root = self.area / name
        (root / "cmd").mkdir(parents=True)
        (root / "cmd/git.exe").write_bytes(b"")
        if bash:
            (root / "usr/bin").mkdir(parents=True)
            (root / "usr/bin/bash.exe").write_bytes(b"")
        return root

    def test_git_bash_is_the_first_git_on_the_path_that_carries_bash(self) -> None:
        mingit, full = self.git("MinGit", bash=False), self.git("Git", bash=True)
        self.assertEqual(shell_environment.git_bash(f"{mingit / 'cmd'};{full / 'cmd'}"), full / "usr/bin")
        self.assertIsNone(shell_environment.git_bash(str(mingit / "cmd")))

    def test_gits_usr_bin_goes_ahead_of_system32(self) -> None:
        full = self.git("Git", bash=True)
        env = shell_environment.with_tools({"PATH": os.pathsep.join(["/windows/system32", str(full / "cmd")])},
                                           self.area / "tools", system="win32")
        self.assertEqual(env["PATH"].split(os.pathsep)[0], str(full / "usr/bin"))
        mac = shell_environment.with_tools({"PATH": str(full / "cmd")}, self.area / "tools", system="darwin")
        self.assertEqual(mac["PATH"], str(full / "cmd"))

    def test_git_without_bash_is_named_for_what_it_lacks(self) -> None:
        mingit = self.git("MinGit", bash=False)
        answered = mock.Mock(returncode=0, stdout="git version 2.51.0.windows.1", stderr="")
        with mock.patch("slipwai.prerequisites.shutil.which", return_value=str(mingit / "cmd/git.exe")), \
                mock.patch("slipwai.prerequisites.subprocess.run", return_value=answered):
            one = found(BY_KEY["git"], str(mingit / "cmd"), system="win32")
        self.assertEqual((one.state, one.lacks), ("old", "bash"))
        with mock.patch.object(tool_install, "way", return_value="archive"):
            self.assertIn("Install Git with bash", machine_card.card([one]))
        with mock.patch("slipwai.tool_install.Installing") as made, \
                mock.patch.object(tool_install, "way", return_value="archive"):
            tool_install.begin("git", self.area, look=lambda tool: one)
        self.assertFalse(made.call_args.kwargs["first"])

    def test_python_is_python_and_never_the_stores_stub(self) -> None:
        asked = []

        def which(command: str, path: str = "") -> None:
            asked.append((command, path))

        with mock.patch("slipwai.prerequisites.shutil.which", side_effect=which):
            prerequisites.located("python3", r"C:\Python313;C:\Users\a\AppData\Local\Microsoft\WindowsApps", "win32")
        self.assertEqual(asked, [("python", r"C:\Python313")])

    def test_bash_gets_a_python3_that_goes_first(self) -> None:
        python = self.area / "Python313/python.exe"
        with mock.patch.object(sys, "platform", "win32"):
            shim = tool_install.windows_shims(self.area / "tools",
                                              look=lambda tool: Found(tool, "found", str(python), "3.13.1"))
        assert shim is not None
        self.assertEqual(shim.read_text(), f'#!/bin/sh\nexec "{python.as_posix()}" "$@"\n')
        self.assertTrue(json.loads((shim.parents[1] / "tool.json").read_text())["first"])
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertIsNone(tool_install.windows_shims(self.area / "tools",
                                                         look=lambda tool: Found(tool, "found", str(python), "3")))

    def test_a_python_script_is_started_with_python3_and_on_windows_with_python_exe(self) -> None:
        self.assertEqual(shell_environment.python3("darwin"), "python3")
        self.assertEqual(shell_environment.python3("linux"), "python3")
        with mock.patch.object(shell_environment, "windows_python", return_value=r"C:\Python313\python.exe"):
            self.assertEqual(shell_environment.python3("win32"), r"C:\Python313\python.exe")
        with mock.patch.object(shell_environment, "windows_python", return_value=None):
            self.assertEqual(shell_environment.python3("win32"), sys.executable)

    def test_nothing_the_keel_or_the_toolkit_starts_names_python3_itself(self) -> None:
        """Every site goes through `python3()` or the toolkit's `PYTHON`, which keep `python3` off Windows."""
        named = re.compile(r'\[\s*"python3"\s*,')
        sites = [*(ROOT / "src/slipwai").rglob("*.py"), *(ROOT / "assets/toolkit").rglob("*.py")]
        offenders = [str(one.relative_to(ROOT)) for one in sites if named.search(one.read_text(encoding="utf-8"))]
        self.assertEqual(offenders, [])

    def test_a_terminal_is_offered_where_git_has_bash_and_opened_in_the_project(self) -> None:
        full = self.git("Git", bash=True)
        (full / "git-bash.exe").write_bytes(b"")
        window = machine_card.git_bash_window(str(full / "cmd"))
        self.assertEqual(window, full / "git-bash.exe")
        self.assertIsNone(machine_card.git_bash_window(str(self.git("MinGit", bash=False) / "cmd")))
        self.assertIn("data-terminal", machine_card.terminal_row(window))
        self.assertNotIn("data-terminal", machine_card.terminal_row(None))
        with mock.patch.object(machine_card.subprocess, "Popen") as opened, \
                mock.patch.object(machine_card, "login_environment", return_value={}):
            machine_card.open_terminal(self.area / "shop", window)
        self.assertEqual(opened.call_args.args[0], [str(window), f"--cd={self.area / 'shop'}"])

    def test_the_card_on_windows_names_no_wsl(self) -> None:
        with mock.patch.object(sys, "platform", "win32"), \
                mock.patch.object(machine_card, "git_bash_window", return_value=None):
            card = machine_card.card([])
        self.assertNotIn("WSL", card)
        self.assertIn("Install Git with bash above", card)

class CardTest(unittest.TestCase):
    """The card offers Install for a tool the machine lacks or has only too old, never over a good copy."""

    def rows(self, state: str) -> list[Found]:
        return [Found(BY_KEY["node"], state, "/usr/local/bin/node" if state != "missing" else "", "20.1")]

    def test_a_good_copy_offers_nothing_and_an_old_one_a_newer_one(self) -> None:
        self.assertNotIn("data-tool", machine_card.card(self.rows("found")))
        with mock.patch.object(tool_install, "way", return_value="archive"):
            old = machine_card.card(self.rows("old"))
        self.assertIn("Install a newer Node", old)
        self.assertIn("needs 22 or newer", old)

    def test_missing_offers_install_where_the_board_has_a_way(self) -> None:
        with mock.patch.object(tool_install, "way", return_value="archive"):
            self.assertIn('data-tool="node"', machine_card.card(self.rows("missing")))
        with mock.patch.object(tool_install, "way", return_value=""):
            card = machine_card.card(self.rows("missing"))
        self.assertNotIn("data-tool", card)
        self.assertIn("nodejs.org", card)

    def test_a_start_page_says_nothing_where_the_machine_has_everything(self) -> None:
        def everything(tool: prerequisites.Tool) -> Found:
            return Found(tool, "found", "/x", "99")

        def no_make(tool: prerequisites.Tool) -> Found:
            return Found(tool, "missing" if tool.key == "make" else "found", "", "99")

        self.assertEqual(machine_card.lacking_line("/adopt", look=everything), "")
        self.assertIn("Make (not installed)", machine_card.lacking_line("/adopt", look=no_make))


if __name__ == "__main__":
    unittest.main()
