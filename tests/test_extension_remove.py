"""An extension can take back what it wrote, and what it left behind is named (#119).

`codegraph` 1.0.1 writes `scripts/codegraph` at `init`. Nothing recorded that it had, there was no point at which
it could remove it, and no way to un-elect an extension at all: `slipwai extension remove` took the package off
the machine and every project kept the election, the block and the file. The runner ships inside a project, so it
is run here as a project runs it — a script, with python3, in a directory laid out as a project is — which is
why this is in the Makefile's SLOW list.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import cli_extension, hooks, toolkit
from slipwai.assets import TOOLKIT_ROOT, this_command
from slipwai.extension_directory import Extension
from slipwai.extension_removal import taken_back
from slipwai.extension_shape import validate

SCRIPTS = TOOLKIT_ROOT / "scripts/extensions"
MANIFEST = {"key": "indexer", "name": "Indexer", "description": "A test extension", "kind": "extension",
            "core": ">=9.0,<10", "hooks": {"init": "init.py", "remove": "hooks/remove.py"},
            "writes": ["scripts/indexer", ".indexer/config.json"]}
BLOCK = "<!-- extension:indexer:begin -->\n## Indexer\nAsk the index.\n<!-- extension:indexer:end -->"
#: A `remove` hook as a publisher writes one: it takes back the one file that is wholly its own.
TAKES_BACK = ("from pathlib import Path\nPath('scripts/indexer').unlink(missing_ok=True)\n"
              "print('took scripts/indexer back')\n")


class DeclarationTest(unittest.TestCase):
    def test_remove_is_a_point_of_the_closed_set_and_nothing_is_attached_to_it_by_default(self) -> None:
        point = hooks.point("remove")
        self.assertEqual(point.given, ("root",))
        self.assertIn("hooks.py --remove <key>", point.when)
        self.assertEqual(hooks.NAMES[:4], ("init", "project", "check", "remove"))
        bare = {key: value for key, value in MANIFEST.items() if key not in ("hooks", "writes")}
        self.assertNotIn("remove", hooks.declared(bare), "taking back is the extension's to offer, never assumed")
        self.assertEqual(hooks.declared(MANIFEST)["remove"], {"run": "hooks/remove.py", "budget": "30s"})

    def test_writes_is_a_list_of_paths_inside_the_project_and_outside_the_extensions_own_directory(self) -> None:
        validate(MANIFEST)
        for wrong in ("scripts/indexer", [""], [7], ["../elsewhere"], ["/etc/hosts"], ["a\\b"],
                      ["scripts/extensions/indexer/state.json"]):
            with self.assertRaises(ValueError, msg=repr(wrong)) as raised:
                validate({**MANIFEST, "writes": wrong})
            self.assertIn("writes", str(raised.exception))

    def test_a_generated_project_is_given_what_each_offered_extension_says_it_writes(self) -> None:
        area = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, area, True)
        (area / "init.py").write_text("", encoding="utf-8")
        quiet = {key: value for key, value in MANIFEST.items() if key != "writes"} | {"key": "quiet"}
        with mock.patch.object(toolkit, "EXTENSIONS", [Extension("indexer", area, MANIFEST),
                                                       Extension("quiet", area, quiet)]):
            written = toolkit.extension_files()
        self.assertEqual(json.loads(written["scripts/extensions/available-writes.json"]),
                         {"indexer": [".indexer/config.json", "scripts/indexer"], "quiet": []})


class Project(unittest.TestCase):
    """A project that elected `indexer`, which wrote two files outside its own directory."""

    hook = TAKES_BACK

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        self.scripts = self.root / "scripts/extensions"
        (self.scripts / "indexer/hooks").mkdir(parents=True)
        (self.scripts / "other").mkdir()
        for name in ("hooks.py", "guidance.py"):
            shutil.copy2(SCRIPTS / name, self.scripts / name)
        both = {"init": {"run": "init.py", "budget": "30s"}, "project": {"run": "init.py", "budget": "30s"}}
        available = {"indexer": {**both, "remove": {"run": "hooks/remove.py", "budget": "30s"}}, "other": both}
        (self.scripts / "available.json").write_text(json.dumps(available), encoding="utf-8")
        (self.scripts / "available-tools.json").write_text(json.dumps({"indexer": ["mcp__indexer__*"]}),
                                                           encoding="utf-8")
        (self.scripts / "available-writes.json").write_text(
            json.dumps({"indexer": MANIFEST["writes"], "other": []}), encoding="utf-8")
        for key in ("indexer", "other"):
            (self.scripts / key / "init.py").write_text("", encoding="utf-8")
        (self.scripts / "indexer/hooks/remove.py").write_text(self.hook, encoding="utf-8")
        (self.root / "scripts/indexer").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.root / ".indexer").mkdir()
        (self.root / ".indexer/config.json").write_text("{}", encoding="utf-8")
        (self.root / ".slipwai").mkdir()
        self.state = self.root / ".slipwai/extensions.json"
        self.state.write_text(json.dumps({"schemaVersion": 1, "extensions": ["indexer", "other"]}), encoding="utf-8")
        self.agents = self.root / "AGENTS.md"
        self.agents.write_text(f"# Guidance\n\nThe project's own words.\n\n{BLOCK}\n\nAnd after.\n", encoding="utf-8")
        self.invoke("--elect", "indexer", "other")

    def invoke(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.scripts / "hooks.py"), *argv], capture_output=True,
                              text=True, cwd=self.root, check=False)

    def registry(self) -> dict:
        return json.loads((self.root / ".slipwai/hooks.json").read_text(encoding="utf-8"))

    def elected(self) -> list[str]:
        return json.loads(self.state.read_text(encoding="utf-8"))["extensions"]


class RemoveTest(Project):
    def test_electing_records_what_each_elected_extension_says_it_writes(self) -> None:
        self.assertEqual(self.registry()["writes"], {"indexer": [".indexer/config.json", "scripts/indexer"]})
        self.invoke("--elect", "other")
        self.assertNotIn("writes", self.registry(), "and a project electing none that writes has no such key")

    def test_un_electing_fires_its_hook_and_names_what_is_still_here(self) -> None:
        done = self.invoke("--remove", "indexer")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("took scripts/indexer back", done.stdout)
        self.assertFalse((self.root / "scripts/indexer").exists(), "the hook took back what was its own")
        self.assertIn("hooks: indexer un-elected. It wrote outside scripts/extensions/indexer/ and this is still "
                      "here: .indexer/config.json. Nothing removed it: delete each, or keep it on purpose.",
                      done.stdout)
        self.assertTrue((self.root / ".indexer/config.json").is_file(), "named, never removed by the runner")

    def test_it_is_un_elected_everywhere_an_election_is_read(self) -> None:
        self.invoke("--remove", "indexer")
        registry = self.registry()
        attached = {body["extension"] for bodies in registry["points"].values() for body in bodies}
        self.assertEqual(attached, {"other"})
        self.assertEqual(registry["tools"], [])
        self.assertNotIn("writes", registry)
        self.assertEqual(self.elected(), ["other"])
        text = self.agents.read_text(encoding="utf-8")
        self.assertNotIn("extension:indexer", text, "or the next `make agents` reads the block as an election")
        self.assertEqual(text, "# Guidance\n\nThe project's own words.\n\nAnd after.\n")
        self.assertTrue((self.scripts / "indexer/init.py").is_file(), "the copy stays: it is still offered")

    def test_a_second_time_and_one_never_elected_change_nothing_and_say_so(self) -> None:
        self.invoke("--remove", "indexer")
        before = self.registry()
        for key in ("indexer", "absent"):
            done = self.invoke("--remove", key)
            self.assertEqual(done.returncode, 0)
            self.assertIn(f"hooks: {key} is not elected here; elected: other", done.stdout)
        self.assertEqual(self.registry(), before)

    def test_one_only_the_election_record_names_is_un_elected_too(self) -> None:
        """A project that elected before `.slipwai/hooks.json` was written has the record and no registry."""
        (self.root / ".slipwai/hooks.json").unlink()
        done = self.invoke("--remove", "indexer")
        self.assertIn("hooks: indexer un-elected.", done.stdout)
        self.assertEqual(self.elected(), ["other"])
        self.assertNotIn("extension:indexer", self.agents.read_text(encoding="utf-8"))

    def test_an_extension_that_declares_no_path_says_that_nothing_can_be_named(self) -> None:
        done = self.invoke("--remove", "other")
        self.assertIn("hooks: other un-elected. It declares no path it writes outside scripts/extensions/other/, "
                      "so nothing here can name what it left.", done.stdout)

    def test_one_elected_before_the_record_existed_is_named_from_what_the_package_declares_now(self) -> None:
        registry = self.registry()
        del registry["writes"]
        (self.root / ".slipwai/hooks.json").write_text(json.dumps(registry), encoding="utf-8")
        (self.scripts / "indexer/hooks/remove.py").write_text("", encoding="utf-8")
        said = self.invoke("--remove", "indexer").stdout
        self.assertIn("these are still here: .indexer/config.json, scripts/indexer.", said)


class CrashTest(Project):
    hook = "raise SystemExit('the index is locked')\n"

    def test_a_hook_that_crashes_is_reported_and_the_extension_is_un_elected_all_the_same(self) -> None:
        done = self.invoke("--remove", "indexer")
        self.assertEqual(done.returncode, 0)
        self.assertIn("hook indexer remove: exited 1; the index is locked", done.stderr)
        self.assertEqual(self.elected(), ["other"])
        self.assertIn("these are still here: .indexer/config.json, scripts/indexer.", done.stdout)


class KeelTest(Project):
    """`slipwai extension remove`, run where the package is going and a project elected it."""

    def setUp(self) -> None:
        super().setUp()
        self.packages = self.root.parent / f"{self.root.name}-packages"
        (self.packages / "indexer").mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.packages, True)
        (self.packages / "indexer/extension.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
        (self.packages / "indexer/init.py").write_text("", encoding="utf-8")

    def removed(self, where: Path) -> str:
        said = io.StringIO()
        previous = Path.cwd()
        os.chdir(where)
        try:
            with mock.patch.object(cli_extension, "directory", lambda: self.packages), \
                    contextlib.redirect_stdout(said):
                cli_extension.extension_main(["remove", "indexer"])
        finally:
            os.chdir(previous)
        return said.getvalue()

    def test_in_a_project_that_elected_it_the_project_takes_it_back_first(self) -> None:
        said = self.removed(self.root)
        self.assertIn("took scripts/indexer back", said)
        self.assertIn("hooks: indexer un-elected.", said)
        self.assertIn("indexer removed", said)
        self.assertLess(said.index("un-elected"), said.index("indexer removed"))
        self.assertEqual(self.elected(), ["other"])
        self.assertFalse((self.packages / "indexer").exists())

    def test_anywhere_else_it_says_what_each_project_that_elected_it_still_has_to_do(self) -> None:
        said = self.removed(self.packages)
        self.assertIn("indexer removed", said)
        self.assertIn("python3 scripts/extensions/hooks.py --remove indexer", said)
        self.assertEqual(self.elected(), ["indexer", "other"], "no project was touched from outside it")

    def test_a_project_whose_runner_cannot_un_elect_does_not_block_the_removal(self) -> None:
        (self.scripts / "hooks.py").write_text("raise SystemExit(3)\n", encoding="utf-8")
        said = taken_back(self.root, "indexer")
        self.assertEqual(len(said), 1)
        self.assertIn("could not be un-elected here", said[0])
        self.assertIn(f"{this_command()} migrate", said[0].replace("`", ""))
        self.assertIn("indexer removed", self.removed(self.root))


if __name__ == "__main__":
    unittest.main()
