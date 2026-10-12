"""`slipwai target install|remove|list|check`: putting a cloud in the package directory and taking it out.

The third of the three things 10.1 did not build. An extension's install is a stage and a rename, because an
extension collides with nothing but its own name; a target's is a stage, an *admission* and a rename, because
a target that cannot be imported or does not answer the protocol is one a project would be generated against
and fail at `make bootstrap` — with half a stack in somebody's account, which is the moment this factory
refuses everywhere else to leave a person at.

Nothing is installed half-way: staged under a hidden name the loader skips, admitted, then renamed into place.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import cli_target
from slipwai.errors import GenerationError
from slipwai.target_install import catalogue, install, remove

MANIFEST = {
    "name": "cumulus", "label": "Cumulus — one box per app", "description": "Where a project goes",
    "kind": "target", "core": ">=9.0,<10", "managed": True, "requires": ["http"],
}

MODULE = '''from slipwai.target_protocol import (
    ADD_COMMANDS, AGENT_RULES, DOCS_PAGES, IMAGE_REGISTRY, PIPELINE, README_WORDS, SCRIPTS, SHAPES, TOOLS,
    Target,
)

TARGET = Target(
    name="cumulus",
    answers={
        SHAPES: {"bootstrap": ("bootstrap/main.tf",), "service": ("service/main.tf",)},
        SCRIPTS: {"scripts/deploy.py": "scripts/deploy.py"},
        DOCS_PAGES: {"docs/deployment.md": lambda project, apps: "# Deployment\\n"},
        TOOLS: (("tofu", "what applies the stacks", "https://opentofu.org/"),),
        IMAGE_REGISTRY: {"cloud": "Cumulus", "registry": "CR", "example": "cumulus.invalid/",
                         "runtime": "Boxes"},
        PIPELINE: {"cli": "", "credentials": "      - uses: cumulus/login@v1\\n", "build_cli": "",
                   "registry_login": "      - run: cumulus registry login\\n",
                   "environment": "  CUMULUS_REGION: ${{ vars.CUMULUS_REGION }}\\n"},
        README_WORDS: {"runtime": "one box per app", "site": " The site is a bucket.",
                       "credentials": "a sign-in the `cumulus` CLI can find"},
        AGENT_RULES: "- This project deploys to Cumulus from the pipeline.\\n",
        ADD_COMMANDS: {"service": "- one more box\\n", "web": "- the site is behind the edge\\n"},
    },
)
'''


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.area, True)
        self.directory = self.area / "packages"
        self.directory.mkdir()

    def source(self, name: str = "cumulus", manifest: dict | None = None, module: str | None = None) -> Path:
        """A target package in a directory of its own, as a person would hand one to `install`."""
        root = self.area / f"src-{name}"
        (root / f"slipwai_target_{name}").mkdir(parents=True, exist_ok=True)
        (root / "target.json").write_text(json.dumps(MANIFEST if manifest is None else manifest), encoding="utf-8")
        (root / f"slipwai_target_{name}" / "__init__.py").write_text(
            MODULE if module is None else module, encoding="utf-8")
        (root / "bootstrap").mkdir(exist_ok=True)
        (root / "bootstrap" / "main.tf").write_text("# the account's stack\n", encoding="utf-8")
        return root

    def test_a_package_directory_is_installed_under_the_name_its_manifest_gives(self) -> None:
        said = install([str(self.source())], self.directory)
        self.assertEqual(len(said), 1)
        self.assertIn("cumulus", said[0])
        self.assertTrue((self.directory / "cumulus" / "target.json").is_file())
        self.assertTrue((self.directory / "cumulus" / "slipwai_target_cumulus" / "__init__.py").is_file())

    def test_what_the_package_ships_beside_its_manifest_comes_too(self) -> None:
        """The keel does not model a target's internals, so it does not choose which of its files matter."""
        install([str(self.source())], self.directory)
        self.assertTrue((self.directory / "cumulus" / "bootstrap" / "main.tf").is_file())

    def test_a_target_whose_python_will_not_import_is_refused_and_nothing_lands(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            install([str(self.source(module="raise RuntimeError('no')"))], self.directory)
        self.assertIn("failed to import", str(raised.exception))
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_a_managed_target_that_does_not_answer_the_protocol_is_refused(self) -> None:
        """At install, not at generate: a project written against a cloud that cannot be deployed is one
        somebody finds out about with half a stack in their account."""
        module = 'from slipwai.target_protocol import Target\n\nTARGET = Target(name="cumulus")\n'
        with self.assertRaises(GenerationError) as raised:
            install([str(self.source(module=module))], self.directory)
        self.assertIn("shapes", str(raised.exception))
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_a_target_json_the_keel_cannot_read_is_refused(self) -> None:
        bare = {key: value for key, value in MANIFEST.items() if key != "label"}
        with self.assertRaises(GenerationError) as raised:
            install([str(self.source(manifest=bare))], self.directory)
        self.assertIn("label", str(raised.exception))

    def test_a_name_a_language_already_holds_is_refused_rather_than_replacing_it(self) -> None:
        (self.directory / "cumulus").mkdir()
        (self.directory / "cumulus" / "language.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(GenerationError) as raised:
            install([str(self.source())], self.directory)
        self.assertIn("language", str(raised.exception))
        self.assertTrue((self.directory / "cumulus" / "language.json").is_file())

    def test_installing_over_an_installed_target_replaces_it_whole(self) -> None:
        install([str(self.source())], self.directory)
        (self.directory / "cumulus" / "left-over.tf").write_text("stale\n", encoding="utf-8")
        install([str(self.source())], self.directory)
        self.assertFalse((self.directory / "cumulus" / "left-over.tf").exists())

    def test_nothing_asked_for_is_refused_with_what_the_verb_takes(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            install([], self.directory)
        self.assertIn("target install", str(raised.exception))

    def test_no_staging_directory_is_left_behind(self) -> None:
        install([str(self.source())], self.directory)
        self.assertEqual([entry.name for entry in self.directory.iterdir()], ["cumulus"])


class RemoveTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.area, True)
        self.directory = self.area / "packages"
        (self.directory / "cumulus").mkdir(parents=True)
        (self.directory / "cumulus" / "target.json").write_text(json.dumps(MANIFEST), encoding="utf-8")

    def test_an_installed_target_is_taken_out(self) -> None:
        self.assertEqual(remove(["cumulus"], self.directory), ["cumulus removed"])
        self.assertFalse((self.directory / "cumulus").exists())

    def test_a_name_that_is_not_an_installed_target_is_refused_with_what_is(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            remove(["stratus"], self.directory)
        self.assertIn("cumulus", str(raised.exception))

    def test_a_language_is_not_removed_by_the_target_verb(self) -> None:
        (self.directory / "go").mkdir()
        (self.directory / "go" / "language.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(GenerationError):
            remove(["go"], self.directory)
        self.assertTrue((self.directory / "go").is_dir())


class CatalogueTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.area, True)

    def test_every_installed_target_is_listed_whether_or_not_the_loader_admits_it(self) -> None:
        """What is installed is the directory's to say: a refused target can still be removed or replaced."""
        for name, text in (("cumulus", json.dumps(MANIFEST)), ("stratus", "{not json")):
            (self.area / name).mkdir()
            (self.area / name / "target.json").write_text(text, encoding="utf-8")
        found = catalogue(self.area)
        self.assertEqual([name for name, _ in found], ["cumulus", "stratus"])
        self.assertEqual(found[1][1], {})

    def test_a_directory_that_is_not_a_target_is_not_listed(self) -> None:
        (self.area / "go").mkdir()
        (self.area / "go" / "language.json").write_text("{}", encoding="utf-8")
        self.assertEqual(catalogue(self.area), [])

    def test_nothing_installed_lists_nothing(self) -> None:
        self.assertEqual(catalogue(self.area / "absent"), [])


if __name__ == "__main__":
    unittest.main()


class VerbTest(unittest.TestCase):
    """`slipwai target` as a person meets it: the verb is registered, and `list` says what is there."""

    def test_target_is_one_of_the_verbs_the_command_line_offers(self) -> None:
        from slipwai.cli import VERBS
        self.assertIn("target", VERBS)

    def test_listing_nothing_installed_says_what_a_project_can_still_do(self) -> None:
        with mock.patch("slipwai.cli_target.catalogue", return_value=[]):
            said = "\n".join(cli_target.rows())
        self.assertIn("none installed", said)
        self.assertIn("target install", said)

    def test_listing_an_installed_target_shows_the_row_and_what_it_brings(self) -> None:
        manifest = {**MANIFEST, "axes": {"auth": {"cirrus-id": {"label": "Cirrus ID"}}}}
        with mock.patch("slipwai.cli_target.catalogue", return_value=[("cumulus", manifest)]):
            said = "\n".join(cli_target.rows())
        self.assertIn("cumulus", said)
        self.assertIn(MANIFEST["label"], said)
        self.assertIn("cirrus-id", said)
        self.assertIn("managed", said)

    def test_a_target_whose_manifest_cannot_be_read_is_still_listed(self) -> None:
        """What is installed is the directory's to say: one nobody can list is one nobody can remove."""
        with mock.patch("slipwai.cli_target.catalogue", return_value=[("stratus", {})]):
            said = "\n".join(cli_target.rows())
        self.assertIn("stratus", said)
        self.assertIn("unreadable", said)
