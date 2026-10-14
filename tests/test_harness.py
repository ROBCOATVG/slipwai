"""Which harness a headless session runs through, and what it is asked.

This is the module `captain.py` fell back from. Its fallback was `scripts/agents/sail.py`, the *settings
reader* for `/sail`, which handed a slice and a fairway prints its table and exits 0 — and a whole real
run was reported through on the strength of it. The refusals matter as much as the choice: "no harness" has
three causes and three different things a person does about them.

Run as a module here rather than as a script: it is a library in the toolkit, and the keel's suite is where
its arithmetic is held.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

SOURCE = TOOLKIT_ROOT / "scripts/agents/harness.py"


def loaded(root: Path) -> Any:
    """The module as it runs inside a project: `ROOT` is that project, not this checkout.

    Loaded from its path rather than imported, because it lives in the toolkit and is a file a generated
    project gets a copy of — importing it would make the keel's suite depend on a project runtime being on
    the path, which is the thing `make shared` exists to avoid having to do.
    """
    spec = importlib.util.spec_from_file_location(f"harness_{root.name}", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    setattr(module, "ROOT", root)  # noqa: B010 - the module is Any, and mypy reads a literal attribute
    setattr(module, "INTEGRATION", root / ".specify/integration.json")  # noqa: B010
    return module


class Fixture(unittest.TestCase):
    harness: Any

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        (self.root / "commands").mkdir()
        (self.root / "commands/sail.md").write_text("# sail\n", encoding="utf-8")
        self.harness = loaded(self.root)
        # The tests below stand in for `shutil.which`, and the module's `shutil` is everybody's: put it back,
        # or every suite that runs after this one finds the stand-in.
        self.addCleanup(setattr, self.harness.shutil, "which", self.harness.shutil.which)

    def installed(self, *keys: str) -> None:
        (self.root / ".specify").mkdir(exist_ok=True)
        (self.root / ".specify/integration.json").write_text(
            json.dumps({"installed_integrations": list(keys)}), encoding="utf-8")


class RegistryTest(Fixture):
    def test_every_harness_with_a_headless_row_has_a_command_with_a_prompt_in_it(self) -> None:
        """A template with no `{prompt}` is a session that is started and asked nothing."""
        for key, row in self.harness.registry().items():
            headless = self.harness.headless_row(row)
            if headless is None:
                continue
            with self.subTest(harness=key):
                self.assertIn("{prompt}", str(headless["command"]))
                self.assertTrue(self.harness.binary_of(row), "a command has to start with something")

    def test_a_row_with_no_headless_column_records_why(self) -> None:
        """Null is not an oversight here: it means nobody has verified how that harness runs one prompt
        non-interactively, and the difference between that and `{}` is what stops a guess being made."""
        for key, row in self.harness.registry().items():
            if self.harness.headless_row(row) is None:
                with self.subTest(harness=key):
                    self.assertTrue(row.get("headlessReason"), f"{key} has no headless row and no reason")


class ChoosingTest(Fixture):
    def test_nothing_installed_is_refused_by_name_and_not_guessed_at(self) -> None:
        with self.assertRaises(self.harness.NoHarness) as refused:
            self.harness.choose()
        self.assertIn("no harness is initialised here", str(refused.exception))

    def test_an_installed_harness_whose_binary_is_absent_says_which_binary(self) -> None:
        """Not "no harness": the thing to do about a missing binary is install it, and a run that did not
        say which one would send somebody to read the registry."""
        self.installed("claude")
        self.harness.shutil.which = lambda _name: None
        with self.assertRaises(self.harness.NoHarness) as refused:
            self.harness.choose()
        said = str(refused.exception)
        self.assertIn("Claude Code", said)
        self.assertIn("is not on PATH", said)

    def test_a_harness_on_path_that_init_never_ran_for_is_named_with_the_init_that_adds_it(self) -> None:
        """It is deliberately not driven. A harness `./init` never initialised has no projected commands,
        no delegate types and no hooks, so the command being asked for is unknown to it and the session
        ends having done nothing."""
        self.installed("codex")
        self.harness.shutil.which = lambda name: "/usr/bin/claude" if name == "claude" else None
        with self.assertRaises(self.harness.NoHarness) as refused:
            self.harness.choose()
        said = str(refused.exception)
        self.assertIn("never initialised here", said)
        self.assertIn("./init --integration claude", said)

    def test_the_first_installed_harness_that_can_be_run_is_the_one(self) -> None:
        self.installed("claude")
        self.harness.shutil.which = lambda _name: "/usr/bin/anything"
        chosen, said = self.harness.choose()
        self.assertEqual(chosen["key"], "claude")
        self.assertIn("Claude Code", said)


class PromptTest(Fixture):
    def row(self, prompt: str | None) -> dict:
        headless: dict[str, object] = {"command": "x -p {prompt}"}
        if prompt:
            headless["prompt"] = prompt
        return {"key": "k", "name": "A harness", "headless": headless}

    def test_a_harness_whose_print_mode_resolves_slash_commands_is_asked_the_slash_command(self) -> None:
        said = self.harness.prompt_for(self.row("slash"), "sail", self.root / "commands/sail.md",
                                       "BOK-01 fairway=booking")
        self.assertEqual(said, "/sail BOK-01 fairway=booking")

    def test_every_other_harness_is_asked_to_read_the_file(self) -> None:
        """Which needs nothing of a harness beyond reading a file, and is the same words whatever it is."""
        said = self.harness.prompt_for(self.row(None), "sail", self.root / "commands/sail.md",
                                       "BOK-01 fairway=booking")
        self.assertIn("commands/sail.md", said)
        self.assertIn("BOK-01 fairway=booking", said)
        self.assertNotIn("/sail BOK-01", said)

    def test_the_slice_and_the_fairway_both_reach_the_prompt(self) -> None:
        """One slice per dispatch, named — the captain's gate is per slice, and a dispatch handed a whole
        fairway makes the completion lines unattributable."""
        for row in (self.row("slash"), self.row(None)):
            with self.subTest(prompt=row["headless"].get("prompt")):
                said = self.harness.prompt_for(row, "sail", self.root / "commands/sail.md",
                                               "BOK-01 fairway=booking")
                self.assertIn("BOK-01", said)
                self.assertIn("fairway=booking", said)


class EnvironmentTest(Fixture):
    def test_a_parent_session_s_identity_does_not_reach_the_child(self) -> None:
        """A session started from inside another reads the parent's transcript as its own, or refuses to
        start as a nested copy of it."""
        self.harness.os.environ["CLAUDECODE"] = "1"
        self.addCleanup(self.harness.os.environ.pop, "CLAUDECODE", None)
        self.assertNotIn("CLAUDECODE", self.harness.child_environment(None))


if __name__ == "__main__":
    unittest.main()
