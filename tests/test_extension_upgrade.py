"""`slipwai upgrade` moves an installed extension as it moves a language, and says why where it does not (#119).

It listed each extension against what was published and ended the line with a command to run, while a language a
compatible release reached was moved. Here against a `file:` index and the release files it lists: no network,
no child process but a stand-in, and a home of its own so no publisher this machine accepted is read.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import extension_upkeep, trust
from slipwai.assets import this_command
from slipwai.errors import GenerationError
from slipwai.language_index import READ
from slipwai.upgrade import LanguagesNotUpgraded

PUBLISHER = "a-publisher"


def manifest(key: str, core: str = ">=9.0,<10") -> dict:
    return {"key": key, "name": key.title(), "description": "A test extension", "kind": "extension", "core": core,
            "publisher": PUBLISHER}


def package(root: Path, key: str, version: str, core: str = ">=9.0,<10") -> Path:
    place = root / key
    place.mkdir(parents=True, exist_ok=True)
    (place / "extension.json").write_text(json.dumps(manifest(key, core)), encoding="utf-8")
    (place / "init.py").write_text(f"GUIDANCE = '{version}'\n", encoding="utf-8")
    (place / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    return place


class Case(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.area, True)
        self.packages = self.area / "packages"
        self.listed: dict[str, list[dict]] = {}
        channel = self.area / "channel/slipwai-languages"
        channel.mkdir(parents=True)
        self.index = channel / "index.json"
        environment = mock.patch.dict(os.environ, {"SLIPWAI_INDEX": channel.parent.as_uri(),
                                                   "SLIPWAI_HOME": str(self.area / "home")})
        environment.start()
        self.addCleanup(environment.stop)
        self.addCleanup(READ.clear)
        trust.accept(PUBLISHER)

    def publish(self, key: str, version: str, core: str = ">=9.0,<10") -> None:
        source = package(self.area / f"source-{version}", key, version, core)
        archive = self.index.parent / f"{key}-{version}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(source, arcname=key)
        self.listed.setdefault(key, []).append({
            "version": version, "file": archive.name, "kind": "extension", "publisher": PUBLISHER,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "description": "A fake",
            "extension": manifest(key, core)})
        self.index.write_text(json.dumps({"index": 2, "packages": self.listed}), encoding="utf-8")
        READ.clear()

    def version(self, key: str) -> str:
        return (self.packages / key / "VERSION").read_text(encoding="utf-8").strip()

    def step(self, check: bool = False, moved: bool = False, prerelease: bool = False, run=None) -> list[str]:
        return extension_upkeep.after_languages(check, prerelease, moved, self.packages,
                                                run=run or subprocess.run)


class UpgradeTest(Case):
    def setUp(self) -> None:
        super().setUp()
        package(self.packages, "ux-gates", "1.0.0")
        package(self.packages, "codegraph", "1.0.0")
        for version in ("1.0.0", "1.0.1", "1.1.0.dev2"):
            self.publish("ux-gates", version)
        self.publish("codegraph", "1.0.0")
        self.finish = f"{this_command()} extension upgrade ux-gates"

    def test_check_says_what_would_run_and_moves_nothing(self) -> None:
        self.assertEqual(self.step(check=True), [
            "extensions:",
            "  codegraph 1.0.0 (newest compatible)",
            "  ux-gates 1.0.0 → 1.0.1 available",
            f"would run: {self.finish}",
            f"  a project takes the installed package at its next `{this_command()} migrate`"])
        self.assertEqual(self.version("ux-gates"), "1.0.0")

    def test_an_extension_a_compatible_release_reaches_is_moved(self) -> None:
        said = self.step()
        self.assertEqual(said[:3], ["extensions:", "  codegraph 1.0.0 (newest compatible)",
                                    "  ux-gates 1.0.0 → 1.0.1 available"])
        self.assertTrue(said[3].startswith("upgraded ux-gates 1.0.0 → 1.0.1 from "), said[3])
        self.assertIn("migrate", said[-1])
        self.assertEqual(self.version("ux-gates"), "1.0.1")
        self.assertEqual(self.version("codegraph"), "1.0.0")
        self.assertEqual(self.step()[1:], ["  codegraph 1.0.0 (newest compatible)",
                                           "  ux-gates 1.0.1 (newest compatible)"], "and a second run finds nothing")

    def test_a_snapshot_is_moved_to_only_by_somebody_following_them(self) -> None:
        self.assertIn("  ux-gates 1.0.0 → 1.1.0.dev2 available", self.step(check=True, prerelease=True))
        self.step(prerelease=True)
        self.assertEqual(self.version("ux-gates"), "1.1.0.dev2")

    def test_a_release_for_another_core_schema_is_held_back_in_the_words_a_language_gets(self) -> None:
        self.publish("codegraph", "2.0.0", core=">=10,<11")
        said = self.step(check=True)
        self.assertIn(f"  codegraph 1.0.0 held back: 2.0.0 needs another core schema than 9.0 — {this_command()} "
                      "upgrade, once a slipwai that speaks it is published", said)
        self.assertEqual([line for line in said if line.startswith("would run")], [f"would run: {self.finish}"])

    def test_a_keel_that_was_just_replaced_moves_them_as_the_copy_that_will_load_them(self) -> None:
        ran: list[list[str]] = []

        def child(command: list[str], **_: object) -> subprocess.CompletedProcess:
            ran.append(command)
            return subprocess.CompletedProcess(command, 0, "upgraded ux-gates 1.0.0 → 1.0.1 from there\n", "")
        said = self.step(moved=True, prerelease=True, run=child)
        self.assertEqual(ran[0][-4:], ["extension", "upgrade", "--pre", "ux-gates"])
        self.assertIn("upgraded ux-gates 1.0.0 → 1.0.1 from there", said)
        self.assertEqual(self.version("ux-gates"), "1.0.0", "this process moved nothing itself")

    def test_a_new_keel_that_could_not_move_them_is_an_upgrade_that_failed(self) -> None:
        def child(command: list[str], **_: object) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(command, 2, "", "no\n")
        with self.assertRaises(LanguagesNotUpgraded) as raised:
            self.step(moved=True, run=child)
        self.assertEqual(raised.exception.lines[-2:], [
            "no", f"core moved and the extensions did not — its extension upgrade exited 2. Finish the job: "
                  f"{self.finish}"])

    def test_a_publisher_nobody_accepted_is_not_accepted_on_a_persons_behalf(self) -> None:
        shutil.rmtree(self.area / "home")
        with self.assertRaises(LanguagesNotUpgraded) as raised:
            self.step()
        said = raised.exception.lines
        self.assertIn("the extensions were not upgraded: ux-gates is published by a-publisher, which this machine "
                      "has not accepted", said[-2])
        self.assertEqual(said[-1], f"finish the job: {self.finish}")
        self.assertEqual(self.version("ux-gates"), "1.0.0")
        self.assertFalse(trust.trusted(PUBLISHER), "and it is still not accepted")

    def test_a_release_this_keel_would_not_load_never_replaces_the_one_that_works(self) -> None:
        """The admission an install makes, made here too: the index's entry reads as loadable and the file is not."""
        broken = package(self.area / "broken", "ux-gates", "1.0.2")
        (broken / "extension.json").write_text(json.dumps({**manifest("ux-gates"), "kind": "language"}),
                                               encoding="utf-8")
        archive = self.index.parent / "ux-gates-1.0.2.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(broken, arcname="ux-gates")
        self.listed["ux-gates"].append({**self.listed["ux-gates"][1], "version": "1.0.2", "file": archive.name,
                                        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()})
        self.index.write_text(json.dumps({"index": 2, "packages": self.listed}), encoding="utf-8")
        READ.clear()
        with self.assertRaises(LanguagesNotUpgraded) as raised:
            self.step()
        self.assertIn("the extensions were not upgraded: ", raised.exception.lines[-2])
        self.assertEqual(self.version("ux-gates"), "1.0.0")


class VerbTest(Case):
    """`slipwai extension upgrade`, which is what `upgrade` says it would run."""

    def setUp(self) -> None:
        super().setUp()
        package(self.packages, "ux-gates", "1.0.0")
        self.publish("ux-gates", "1.0.0")

    def test_one_already_the_newest_says_so_and_one_not_installed_is_refused_naming_what_is(self) -> None:
        self.assertEqual(extension_upkeep.upgrade(["ux-gates"], self.packages),
                         ["ux-gates 1.0.0 is the newest compatible release"])
        with self.assertRaises(GenerationError) as refused:
            extension_upkeep.upgrade(["absent"], self.packages)
        self.assertEqual(str(refused.exception), "absent is not an installed extension; installed: ux-gates")

    def test_no_name_is_every_installed_extension(self) -> None:
        self.publish("ux-gates", "1.0.1")
        said = extension_upkeep.upgrade([], self.packages)
        self.assertTrue(said[0].startswith("upgraded ux-gates 1.0.0 → 1.0.1 from "), said)


class TogetherTest(unittest.TestCase):
    def test_the_extensions_follow_the_languages_and_either_failing_is_the_upgrade_failing(self) -> None:
        def languages(check: bool, pre: bool, moved: bool) -> list[str]:
            return ["languages:"]

        def failed(check: bool, pre: bool, moved: bool) -> list[str]:
            raise LanguagesNotUpgraded(["extensions:", "not moved"])
        with self.assertRaises(LanguagesNotUpgraded) as raised:
            extension_upkeep.with_extensions(languages, failed)(False, False, False)
        self.assertEqual(raised.exception.lines, ["languages:", "extensions:", "not moved"])
        with self.assertRaises(LanguagesNotUpgraded) as raised:
            extension_upkeep.with_extensions(failed, failed)(False, False, False)
        self.assertEqual(raised.exception.lines, ["extensions:", "not moved", "extensions:", "not moved"])


if __name__ == "__main__":
    unittest.main()
