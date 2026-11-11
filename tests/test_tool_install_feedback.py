"""What the board says while it installs a tool, and what it does about one it has just installed.

What is proved: a download reports how far it has come; the state the card polls names the step under way,
how far through it, and for how long where it cannot be counted; a failure is marked as one; an archive that
will not be thrown away does not undo the install it came from; the card follows an install it did not begin
and keeps a failure on the page; and a tool installed since the board started is on the path the board looks
for agents on, without starting it again.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import board_settings, machine_card, tool_install
from slipwai.agent_install import fetched


def archive() -> tuple[str, str, int]:
    file = Path(tempfile.mkdtemp()) / "node-v24.0.0-darwin-arm64.tar.gz"
    with tarfile.open(file, "w:gz") as held:
        info = tarfile.TarInfo("node-v24.0.0-darwin-arm64/bin/node")
        body = os.urandom(700_000)  # more than one read of the download, so progress is more than its end
        info.size, info.mode = len(body), 0o755
        held.addfile(info, io.BytesIO(body))
    return file.as_uri(), hashlib.sha256(file.read_bytes()).hexdigest(), file.stat().st_size


class FeedbackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tools = Path(tempfile.mkdtemp())

    def installing(self) -> tuple[tool_install.Installing, dict[str, str]]:
        url, sha, _ = archive()
        return (tool_install.Installing("node", self.tools),
                {"url": url, "sha256": sha, "version": "24.0.0", "bin": "node-v24.0.0-darwin-arm64/bin"})

    def test_a_download_says_how_far_it_has_come(self) -> None:
        url, _, size = archive()
        seen: list[tuple[int, int]] = []
        fetched(url, self.tools / "node", lambda line: None, lambda got, total: seen.append((got, total)))
        self.assertGreater(len(seen), 2, "told as it comes, not once at the end")
        self.assertEqual(seen[-1], (size, size))
        self.assertEqual(sorted(seen), seen)

    def test_the_state_names_the_step_and_how_far_through_it(self) -> None:
        held, _ = self.installing()
        held.step("Downloading")
        held.progress(23_000_000, 60_000_000)
        state = held.state()
        self.assertEqual((state["now"], state["fraction"], state["done"]), ("Downloading: 23 of 60 MB", 0.383, False))
        held.progress(5_000_000, 0)
        self.assertEqual(held.state()["now"], "Downloading: 5 MB so far", "a publisher that gives no length")
        held.step("Unpacking")
        self.assertEqual((held.state()["now"], held.state()["fraction"]), ("Unpacking…", None))
        held.since -= 42
        self.assertEqual(held.state()["now"], "Unpacking… 42 s", "a step that cannot be counted says for how long")

    def test_every_step_of_an_install_is_named_while_it_is_under_way(self) -> None:
        held, found = self.installing()
        steps: list[str] = []
        said = held.step

        def noted(words: str) -> None:
            steps.append(words)
            said(words)

        with mock.patch.object(held, "archive", return_value=found), mock.patch.object(held, "step", noted):
            held.run()
        self.assertEqual(steps, ["Asking the publisher for its newest release", "Downloading",
                                 "Checking it against the publisher's checksum", "Unpacking", "Finishing"])
        state = held.state()
        self.assertEqual((state["done"], state["failed"], state["now"]), (True, False, ""))

    def test_a_failure_is_marked_as_one(self) -> None:
        held, found = self.installing()
        with mock.patch.object(held, "archive", return_value={**found, "sha256": "0" * 64}):
            held.run()
        state = held.state()
        self.assertEqual((state["done"], state["failed"]), (True, True))
        self.assertEqual(tool_install.state("never-asked")["failed"], False)

    def test_an_archive_that_will_not_go_does_not_undo_the_install(self) -> None:
        """Windows refused to delete PortableGit a moment after its extractor ended, and that was reported
        as the install's failure: Git sat unpacked, unrecorded, and the board went on saying it had none."""
        held, found = self.installing()
        with mock.patch.object(held, "archive", return_value=found), \
                mock.patch.object(Path, "unlink", side_effect=PermissionError(13, "Access is denied")), \
                mock.patch.object(tool_install.time, "sleep"):
            held.run()
        self.assertFalse(held.state()["failed"], held.state()["lines"])
        self.assertTrue(Path(json.loads((self.tools / "node/tool.json").read_text())["bin"], "node").is_file())

    def test_a_refusal_that_passes_is_waited_out(self) -> None:
        file = self.tools / "archive.zip"
        file.write_bytes(b"x")
        gone = Path.unlink
        tries: list[int] = []

        def refuses_twice(self: Path, missing_ok: bool = False) -> None:
            tries.append(1)
            if len(tries) < 3:
                raise PermissionError(13, "Access is denied")
            gone(self, missing_ok=missing_ok)

        with mock.patch.object(Path, "unlink", refuses_twice), mock.patch.object(tool_install.time, "sleep"):
            tool_install.discard(file)
        self.assertEqual((len(tries), file.exists()), (3, False))

    def test_the_card_follows_an_install_it_did_not_begin_and_keeps_a_failure(self) -> None:
        script = machine_card.SCRIPT
        self.assertIn("if (!state.done) poll(); else if (state.failed) show(state);", script,
                      "asked on load: a reload in the middle of an install is not the end of its progress")
        self.assertIn("if (state.failed) { one.disabled = false; return; }", script,
                      "a failure stays on the page: reloading on every ending took the reason with it")
        self.assertIn("if (!answer.ok && (await asked()).done)", script,
                      "refused as already being installed: that install is followed, not a dead end")
        self.assertIn("document.createElement('progress')", script)

    def test_a_tool_installed_since_the_board_started_is_on_the_path_it_looks_on(self) -> None:
        """The board installed Node and went on saying there was no `npx`, until it was started again."""
        board_settings.login_once.cache_clear()
        self.addCleanup(board_settings.login_once.cache_clear)
        with mock.patch.object(board_settings, "login_environment", return_value={"PATH": "/usr/bin"}), \
                mock.patch("slipwai.shell_environment.TOOLS", self.tools):
            self.assertEqual(board_settings.shell_path().split(os.pathsep)[:1], ["/usr/bin"])
            self.assertNotIn(str(self.tools), board_settings.shell_path())
            where = self.tools / "node/unpacked"
            where.mkdir(parents=True)
            (self.tools / "node/tool.json").write_text(json.dumps({"bin": str(where), "first": False}))
            self.assertIn(str(where), board_settings.shell_path().split(os.pathsep))
