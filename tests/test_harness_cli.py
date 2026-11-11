"""The harness's own command, installed by the board where the machine has none.

What is proved: the registry names a package and a command for the harnesses it was read for, and the
command is the one `headless` runs; the install is a step before `./init` only where the machine lacks the
command and has `npm`; a finished install is recorded as a tool of the board's, so its children find the
command; one that failed is said and `./init` is still tried.
"""
from __future__ import annotations

import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import bridge, harness, harness_cli, init_run, shell_environment


class HarnessCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.tools = self.root / "tools"
        self.bin = self.root / "bin"
        self.bin.mkdir()

    def on_path(self, *names: str) -> str:
        for name in names:
            file = self.bin / name
            file.write_text("#!/bin/sh\n", encoding="utf-8")
            file.chmod(0o755)
        return str(self.bin)

    def test_the_registry_names_the_package_and_the_command_headless_runs(self) -> None:
        """`./init --integration claude` ended *claude not found* on a machine that had the agent: the
        agent `npx` fetches is an adapter, and the command is another package's."""
        self.assertEqual((harness_cli.row("claude") or {}).get("npm"), "@anthropic-ai/claude-code")
        self.assertEqual((harness_cli.row("codex") or {}).get("npm"), "@openai/codex")
        self.assertEqual((harness_cli.row("gemini") or {}).get("npm"), "@google/gemini-cli", "its own package")
        every = harness.keys()
        named = [key for key in every if harness_cli.row(key)]
        self.assertGreaterEqual(len(named), 15)
        for key in named:
            first = str((harness.row_of(key).get("headless") or {}).get("command") or "").split(" ")[0]
            held = harness_cli.row(key) or {}
            if first:
                self.assertEqual(held["cmd"], first, f"{key}: the command a captain runs")
            self.assertTrue(held.get("source"), f"{key}: read from where, and when")
        self.assertIsNone(harness_cli.row("zed"), "a harness nobody read a package for is left to say so itself")

    def test_it_is_a_step_only_where_the_command_is_missing_and_npm_is_there(self) -> None:
        argv = harness_cli.install_argv("claude", self.on_path("npm"), self.tools)
        self.assertEqual(argv[:3] + argv[-1:], ["npm", "install", "--prefix", "@anthropic-ai/claude-code"])
        self.assertEqual(argv[3], str(self.tools / "claude-cli"))
        self.assertEqual(harness_cli.install_argv("claude", self.on_path("npm", "claude"), self.tools), [],
                         "a machine that has the command is left exactly as it is")
        (self.bin / "npm").unlink()
        (self.bin / "claude").unlink()
        self.assertEqual(harness_cli.install_argv("claude", str(self.bin), self.tools), [], "nothing to install with")
        self.assertEqual(harness_cli.parts("zed", self.on_path("npm"), self.tools), [])
        self.assertEqual(harness_cli.parts(None), [])

    def test_the_run_installs_it_before_init(self) -> None:
        part = (["npm", "install"], "Installing…", lambda code: "done")
        with mock.patch.object(harness_cli, "parts", return_value=[part]), \
                mock.patch.object(init_run.Fitting, "run"):
            fitting = init_run.start(self.root, "claude", installs=True)
            plain = init_run.start(self.root, "claude")
        first = [step.argv[:2] for step in fitting.steps[:2]]
        self.assertEqual(first, [["npm", "install"], ["./init", "--integration"]])
        self.assertFalse(fitting.steps[0].stops, "an install that failed leaves `./init` to say what it finds")
        self.assertEqual(plain.steps[0].argv[:1], ["./init"], "only where the board asks: a run is not an install")
        self.assertIn("installs=True", inspect.getsource(bridge.Bridge.land), "and the board asks")

    def test_a_finished_install_is_a_tool_the_board_s_children_find(self) -> None:
        folder = self.tools / "claude-cli"
        where = folder / "node_modules" / ".bin"
        where.mkdir(parents=True)
        (where / "claude").write_text("", encoding="utf-8")
        package = folder / "node_modules" / "@anthropic-ai" / "claude-code"
        package.mkdir(parents=True)
        (package / "package.json").write_text(json.dumps({"version": "2.1.322"}), encoding="utf-8")
        own = {"PATH": "/usr/bin"}
        with mock.patch.object(harness_cli, "adopt_tools", lambda home: shell_environment.adopt_tools(own, home)):
            said = harness_cli.installed("claude", 0, self.tools)
        self.assertEqual(said, f"Installed `claude` 2.1.322 in {where}.")
        self.assertEqual(json.loads((folder / "tool.json").read_text())["bin"], str(where))
        given = shell_environment.with_tools({"PATH": "/usr/bin"}, self.tools)["PATH"]
        self.assertIn(str(where), given.split(os.pathsep))
        self.assertIn(str(where), own["PATH"], "and the board itself, from now")

    def test_an_install_that_failed_is_said_and_nothing_is_recorded(self) -> None:
        said = harness_cli.installed("claude", 1, self.tools)
        self.assertIn("`claude` could not be installed (npm ended 1)", said)
        self.assertFalse((self.tools / "claude-cli" / "tool.json").exists())
        (self.tools / "claude-cli" / "node_modules" / ".bin").mkdir(parents=True)
        self.assertIn("could not be installed", harness_cli.installed("claude", 0, self.tools),
                      "an npm that said yes and left no command is not an install")


if __name__ == "__main__":
    unittest.main()
