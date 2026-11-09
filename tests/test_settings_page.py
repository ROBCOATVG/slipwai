"""The settings page: what runs behind the board, and which answer wins.

Driven through the board with the fixture every page test uses, over a PATH of stand-in binaries so what
this machine really has does not decide a test.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import board_settings
from slipwai.board_settings import AUTO, Settings, chosen, launches, model_options, offered, preferred, read, write


def fake_path() -> str:
    here = Path(tempfile.mkdtemp())
    for name in ("npx", "opencode"):
        (here / name).write_text("#!/bin/sh\n", encoding="utf-8")
        (here / name).chmod(0o755)
        if os.name == "nt":  # `which` on Windows finds what PATHEXT names, and no mode bit
            (here / f"{name}.cmd").write_text("@echo off\n", encoding="utf-8")
    return str(here)


class ChoiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.path = fake_path()
        self.file = Path(tempfile.mkdtemp()) / "board.json"
        installed = mock.patch("slipwai.harness.INSTALLED", Path(tempfile.mkdtemp()) / "agents")
        installed.start()
        self.addCleanup(installed.stop)

    def test_the_file_is_read_and_written_and_absent_means_auto(self) -> None:
        self.assertEqual(read(self.file).runs_on, AUTO)
        write(Settings(runs_on="opencode", models={"opencode": "b"}), self.file)
        again = read(self.file)
        self.assertEqual((again.runs_on, again.models), ("opencode", {"opencode": "b"}))
        self.file.write_text("not json", encoding="utf-8")
        self.assertEqual(read(self.file).runs_on, AUTO, "a broken file is the default, not a crash")

    def test_auto_is_the_first_agent_this_machine_can_launch(self) -> None:
        found = launches(self.path)
        self.assertGreaterEqual(len(found), 24)
        able = [one.key for one in found if one.able]
        self.assertIn("claude", able, "npx is on the path, so every npx package can be launched")
        self.assertIn("opencode", able)
        self.assertNotIn("goose", able)
        self.assertEqual(chosen(Settings(), path=self.path).key, "opencode",  # type: ignore[union-attr]
                         "a binary on the machine before a package npx would fetch")
        self.assertIsNone(chosen(Settings(), path="/nowhere"))

    def test_auto_prefers_an_agent_made_ready_then_a_binary_then_the_first_found(self) -> None:
        found = launches(self.path)
        self.assertEqual(preferred(found, Settings())[1], "on this machine")
        made = Settings(ready={"claude": {"agent": "claude-agent-acp", "fault": ""}})
        chosen = preferred(found, made)[0]
        assert chosen is not None
        self.assertEqual(chosen.key, "claude")
        self.assertEqual(preferred(found, made)[1], "made ready and signed in")
        wanting = Settings(ready={"bob": {"agent": "bob", "fault": "", "auth": [{"id": "key"}]},
                                  "claude": {"agent": "claude-agent-acp", "fault": "", "auth": [{"id": "login"}]}})
        first = preferred(found, wanting)[0]
        self.assertEqual(first.key if first else "", "bob", "neither signed in: the first made ready")
        wanting.ready["claude"]["signed_in"] = {"login": "2026-11-06"}
        self.assertEqual(preferred(found, wanting)[0].key, "claude")  # type: ignore[union-attr]
        broken = Settings(ready={"claude": {"agent": "claude-agent-acp", "fault": "the agent exited 1"}})
        self.assertEqual(preferred(found, broken)[0].key, "opencode")  # type: ignore[union-attr]
        only_npx = [one for one in found if one.key != "opencode"]
        self.assertEqual(preferred(only_npx, Settings())[1], "the first found")
        self.assertEqual(preferred([], Settings()), (None, ""))

    def test_a_choice_that_cannot_be_launched_is_returned_unable_not_replaced(self) -> None:
        now = chosen(Settings(runs_on="goose"), path=self.path)
        assert now is not None
        self.assertEqual((now.key, now.able), ("goose", False))
        self.assertIn("not on PATH", now.said)

    def test_a_project_s_init_answer_wins_where_it_can_be_launched(self) -> None:
        root = Path(tempfile.mkdtemp())
        (root / ".specify").mkdir()
        (root / ".specify/integration.json").write_text(json.dumps({"integration": "opencode"}),
                                                         encoding="utf-8")
        now = chosen(Settings(runs_on="claude"), root=root, path=self.path)
        assert now is not None
        self.assertEqual(now.key, "opencode")
        (root / ".specify/integration.json").write_text(json.dumps({"integration": "goose"}),
                                                         encoding="utf-8")
        now = chosen(Settings(runs_on="claude"), root=root, path=self.path)
        assert now is not None
        self.assertEqual(now.key, "claude", "a recorded harness this machine cannot launch falls to the board's")

    def test_what_an_agent_offered_is_kept_flat(self) -> None:
        options: list[dict[str, Any]] = [
            {"id": "model", "type": "select", "category": "model", "name": "Model", "currentValue": "a",
                    "options": [{"name": "A", "value": "a"},
                                {"group": "big", "name": "Big", "options": [{"name": "B", "value": "b"}]}]},
                   {"id": "mode", "type": "select", "category": "mode", "options": []}]
        self.assertEqual(model_options(options), [{"id": "model", "name": "Model", "current": "a", "values": [
            {"name": "A", "value": "a"}, {"name": "Big: B", "value": "b"}]}])
        settings = Settings()
        offered(settings, "opencode", options, self.file)
        self.assertEqual(read(self.file).offered["opencode"][0]["current"], "a")


class SettingsPageTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.file = Path(tempfile.mkdtemp()) / "board.json"
        for patched in (mock.patch.object(board_settings, "SETTINGS", self.file),
                        mock.patch.object(board_settings, "shell_path", fake_path)):
            patched.start()
            self.addCleanup(patched.stop)
        board_settings.shell_path.cache_clear() if hasattr(board_settings.shell_path, "cache_clear") else None

    def test_the_page_is_on_the_tab_bar_and_lists_what_this_machine_can_launch(self) -> None:
        _, page = self.get("/settings")
        self.assertIn('<a href="/settings" aria-current="page">Settings</a>', page)
        self.assertIn("<b>Auto</b>", page)
        self.assertIn("<b>Claude Code</b>", page)
        self.assertIn("over `npx`", page)
        self.assertIn("<b>Goose</b>", page)
        self.assertIn("not on PATH", page)
        self.assertIn("The board&#x27;s conversations run on", page)

    def test_saving_writes_the_file_and_the_page_says_so(self) -> None:
        self.assertEqual(self.post("/settings/save", {"runs_on": "opencode"}), (200, "saved"))
        self.assertEqual(read(self.file).runs_on, "opencode")
        self.assertIn("run on opencode", self.get("/settings")[1])
        self.assertEqual(self.post("/settings/save", {"runs_on": "zed"})[0], 400)
        self.assertEqual(self.post("/settings/save", {"runs_on": "goose"})[0], 200)
        self.assertIn("cannot launch", self.get("/settings")[1])

    def test_the_model_is_only_what_the_agent_offered(self) -> None:
        write(Settings(runs_on="opencode", offered={"opencode": [
            {"id": "model", "name": "Model", "current": "a", "values": [{"name": "A", "value": "a"},
                                                                       {"name": "B", "value": "b"}]}]}), self.file)
        page = self.get("/settings")[1]
        self.assertIn('<select id="model" name="model">', page)
        self.assertIn('<option value="a" selected>A</option>', page)
        self.assertEqual(self.post("/settings/save", {"runs_on": "opencode", "model": "b"})[0], 200)
        self.assertEqual(read(self.file).models, {"opencode": "b"})
        self.assertIn('<option value="b" selected>B</option>', self.get("/settings")[1])


if __name__ == "__main__":
    unittest.main()
