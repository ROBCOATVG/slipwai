"""An extension as a package: read off disk, installed into the package directory, and taken out again.

Every package here is a fake the test writes into a temporary directory, so what is proved is the loader and
the installer and nothing of any extension. The refusals are the one line `extension <key> (<dir>): <fault>`.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import extension_install, package_new
from slipwai.errors import GenerationError
from slipwai.extension_directory import Extension, files, read

CORE = "9.0"
MANIFEST = {"key": "thing", "name": "A Thing", "description": "What it is for", "kind": "extension",
            "core": ">=9.0,<10", "hooks": {"init": "init.py"}}


def written(root: Path, key: str, manifest: dict | None = None, body: str = "print('hello')\n") -> Path:
    """One fake package on disk: its manifest and one file for its entry point to be."""
    place = root / key
    place.mkdir(parents=True, exist_ok=True)
    whole = {**MANIFEST, "key": key} if manifest is None else manifest
    (place / "extension.json").write_text(json.dumps(whole), encoding="utf-8")
    (place / "init.py").write_text(body, encoding="utf-8")
    return place


class ReadTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_a_whole_package_is_read_with_its_entry_and_its_hooks(self) -> None:
        written(self.area, "thing")
        found, refusals = read(self.area, CORE)
        self.assertEqual(refusals, [])
        self.assertEqual([one.name for one in found], ["thing"])
        self.assertEqual(found[0].entry, {"name": "A Thing", "description": "What it is for"})
        # Both default declarations, filled in by `hooks.DEFAULTS`: a manifest naming only `init` is
        # attached to `project` too, because every extension re-projects its block.
        self.assertEqual(sorted(found[0].hooks), ["init", "project"])

    def test_a_language_directory_is_skipped_rather_than_refused(self) -> None:
        """The two halves walk one directory. "Has no extension.json" about a language is noise."""
        (self.area / "go").mkdir()
        (self.area / "go" / "language.json").write_text("{}", encoding="utf-8")
        found, refusals = read(self.area, CORE)
        self.assertEqual((found, refusals), ([], []))

    def test_a_key_that_is_not_its_directory_is_refused_naming_both(self) -> None:
        written(self.area, "thing", {**MANIFEST, "key": "other"})
        _, refusals = read(self.area, CORE)
        self.assertEqual(len(refusals), 1)
        self.assertIn("other", refusals[0])
        self.assertIn("thing", refusals[0])

    def test_a_package_for_a_newer_keel_names_the_upgrade(self) -> None:
        written(self.area, "thing", {**MANIFEST, "core": ">=10.0,<11"})
        _, refusals = read(self.area, CORE)
        self.assertIn("upgrade", refusals[0])

    def test_a_refusal_is_one_line_whatever_the_manifest_holds(self) -> None:
        """A fault quotes what the manifest said. A manifest does not get to write the second line."""
        written(self.area, "thing", {**MANIFEST, "kind": "exten\nsion"})
        _, refusals = read(self.area, CORE)
        self.assertEqual(len(refusals), 1)
        self.assertNotIn("\n", refusals[0])

    def test_one_bad_package_does_not_take_the_others_with_it(self) -> None:
        written(self.area, "good")
        written(self.area, "bad", {**MANIFEST, "key": "bad", "kind": "language"})
        found, refusals = read(self.area, CORE)
        self.assertEqual([one.name for one in found], ["good"])
        self.assertEqual(len(refusals), 1)

    def test_the_manifest_is_not_among_the_files_a_project_gets(self) -> None:
        """A project is not where a manifest is read, so shipping it there would be shipping a decoy."""
        place = written(self.area, "thing")
        self.assertEqual([path.as_posix() for path in files(place)], ["init.py"])

    def test_the_files_are_in_one_order_on_every_platform(self) -> None:
        """Sorted as `Path` objects they were not: Windows compares a path without case, so `README.md` came after
        `bin/` there and before it everywhere else, and a path is compared part by part, so `hooks/check.py` came
        before `hooks.py`. The order is the POSIX string's, which no platform reads differently (#117)."""
        place = written(self.area, "thing")
        for name in ("README.md", "bin/tool", "hooks/check.py", "hooks.py", "Zed.md", "a-b/c.py", "a/b.py"):
            (place / name).parent.mkdir(parents=True, exist_ok=True)
            (place / name).write_text("", encoding="utf-8")
        self.assertEqual([path.as_posix() for path in files(place)],
                         ["README.md", "Zed.md", "a-b/c.py", "a/b.py", "bin/tool", "hooks.py", "hooks/check.py",
                          "init.py"])


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.home = Path(tempfile.mkdtemp())

    def test_a_directory_installs_under_the_key_its_manifest_declares(self) -> None:
        """Not under the directory's own name: a clone is `slipwai-extension-uipro` and the key is `uipro`."""
        source = written(self.area, "slipwai-extension-thing", MANIFEST)
        extension_install.install([str(source)], self.home)
        self.assertTrue((self.home / "thing" / "init.py").is_file())

    def test_installing_again_replaces_what_was_there(self) -> None:
        source = written(self.area, "thing", body="print('one')\n")
        extension_install.install([str(source)], self.home)
        written(self.area, "thing", body="print('two')\n")
        extension_install.install([str(source)], self.home)
        self.assertEqual((self.home / "thing" / "init.py").read_text(encoding="utf-8"), "print('two')\n")

    def test_a_package_the_loader_would_refuse_never_lands(self) -> None:
        source = written(self.area, "thing", {**MANIFEST, "core": ">=10.0,<11"})
        with self.assertRaises(GenerationError):
            extension_install.install([str(source)], self.home)
        self.assertEqual(sorted(path.name for path in self.home.iterdir()), [])

    def test_a_manifest_and_nothing_else_is_refused(self) -> None:
        place = self.area / "empty"
        place.mkdir()
        (place / "extension.json").write_text(json.dumps({**MANIFEST, "key": "empty"}), encoding="utf-8")
        with self.assertRaises(GenerationError) as refused:
            extension_install.install([str(place)], self.home)
        self.assertIn("files its hooks name", str(refused.exception))

    def test_a_name_a_language_already_holds_is_refused_with_the_way_out(self) -> None:
        (self.home / "thing").mkdir()
        (self.home / "thing" / "language.json").write_text("{}", encoding="utf-8")
        source = written(self.area, "thing")
        with self.assertRaises(GenerationError) as refused:
            extension_install.install([str(source)], self.home)
        self.assertIn("language remove thing", str(refused.exception))

    def test_removing_one_that_is_not_installed_says_what_is(self) -> None:
        extension_install.install([str(written(self.area, "thing"))], self.home)
        with self.assertRaises(GenerationError) as refused:
            extension_install.remove(["other"], self.home)
        self.assertIn("thing", str(refused.exception))

    def test_removing_takes_the_whole_directory(self) -> None:
        extension_install.install([str(written(self.area, "thing"))], self.home)
        extension_install.remove(["thing"], self.home)
        self.assertFalse((self.home / "thing").exists())

    def test_what_is_installed_is_what_the_list_reads(self) -> None:
        extension_install.install([str(written(self.area, "thing"))], self.home)
        self.assertEqual([key for key, _ in extension_install.catalogue(self.home)], ["thing"])


class ScaffoldTest(unittest.TestCase):
    """What `slipwai package new` writes has to be what this keel loads, or its first lesson is wrong."""

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_a_scaffolded_extension_reads_as_a_whole_package(self) -> None:
        package_new.write("extension", "thing", self.area, CORE)
        found, refusals = read(self.area, CORE)
        self.assertEqual(refusals, [])
        self.assertEqual([one.name for one in found], ["thing"])

    def test_a_scaffolded_extension_installs(self) -> None:
        package_new.write("extension", "thing", self.area, CORE)
        home = Path(tempfile.mkdtemp())
        extension_install.install([str(self.area / "thing")], home)
        self.assertTrue((home / "thing" / "init.py").is_file())

    def test_its_entry_point_is_idempotent_and_leaves_what_a_person_wrote(self) -> None:
        """Obligations 1, 3 and 6, proved rather than described: the scaffold meets its own list."""
        package_new.write("extension", "thing", self.area, CORE)
        project = Path(tempfile.mkdtemp())
        (project / "scripts/extensions/thing").mkdir(parents=True)
        (project / "project.json").write_text("{}", encoding="utf-8")
        (project / "AGENTS.md").write_text("# A project\n\nhand written\n", encoding="utf-8")
        entry = project / "scripts/extensions/thing/init.py"
        entry.write_text((self.area / "thing/init.py").read_text(encoding="utf-8"), encoding="utf-8")
        import subprocess
        for _ in range(2):
            run = subprocess.run([__import__("sys").executable, str(entry)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
        text = (project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("hand written", text)
        self.assertEqual(text.count("extension:thing:begin"), 1)

    def test_a_scaffolded_language_declares_the_schema_this_keel_speaks(self) -> None:
        package_new.write("language", "rust", self.area, CORE)
        fragment = json.loads((self.area / "rust/language.json").read_text(encoding="utf-8"))
        self.assertEqual(fragment["core"], ">=9.0,<10")
        self.assertTrue((self.area / "rust/slipwai_language_rust/__init__.py").is_file())

    def test_a_name_that_is_not_a_slug_is_refused_saying_what_it_becomes(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            package_new.write("extension", "UI Pro", self.area, CORE)
        self.assertIn("directory", str(refused.exception))

    def test_a_directory_that_already_holds_something_is_refused(self) -> None:
        package_new.write("extension", "thing", self.area, CORE)
        with self.assertRaises(GenerationError):
            package_new.write("extension", "thing", self.area, CORE)


class EntryTest(unittest.TestCase):
    def test_an_extension_reads_its_own_catalogue_entry(self) -> None:
        one = Extension("thing", Path("/nowhere"), MANIFEST)
        self.assertEqual(one.entry["name"], "A Thing")


if __name__ == "__main__":
    unittest.main()


class IndexInstallTest(unittest.TestCase):
    """`extension install <name>` against a `file:` index, which is how a private channel is tried."""

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.home = Path(tempfile.mkdtemp())

    def channel(self, manifest: dict | None = None) -> Path:
        """An index document and the release file it lists, written where `SLIPWAI_INDEX` can name them."""
        import hashlib
        import tarfile
        whole = {**MANIFEST, **(manifest or {})}
        package = written(self.area / "src", whole["key"], whole)
        channel = self.area / "channel"
        (channel / "slipwai-languages").mkdir(parents=True)
        archive = channel / "slipwai-languages/thing-1.0.0.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(package, arcname=whole["key"])
        (channel / "slipwai-languages/index.json").write_text(json.dumps({
            "index": 2,
            "packages": {whole["key"]: [{"version": "1.0.0", "file": "thing-1.0.0.tar.gz", "kind": "extension",
                                         "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                                         "publisher": "ROBCOATVG", "description": "A fake",
                                         "extension": whole}]},
        }), encoding="utf-8")
        return channel

    def install(self, name: str) -> None:
        import os
        from unittest import mock

        from slipwai.language_index import READ
        READ.clear()
        with mock.patch.dict(os.environ, {"SLIPWAI_INDEX": self.channel().as_uri()}):
            extension_install.install([name], self.home)
        READ.clear()

    def test_a_bare_name_is_looked_up_fetched_and_installed(self) -> None:
        self.install("thing")
        self.assertTrue((self.home / "thing/init.py").is_file())
        self.assertTrue((self.home / "thing/extension.json").is_file())

    def test_a_name_the_channel_has_not_got_says_what_lists_what_it_has(self) -> None:
        import os
        from unittest import mock

        from slipwai.language_index import READ
        READ.clear()
        with mock.patch.dict(os.environ, {"SLIPWAI_INDEX": self.channel().as_uri()}), \
                self.assertRaises(GenerationError) as refused:
            extension_install.install(["absent"], self.home)
        READ.clear()
        self.assertIn("search --kind extension", str(refused.exception))

    def test_something_with_a_separator_is_a_path_and_is_never_looked_up(self) -> None:
        """Otherwise a mistyped path becomes a silent network call for a package nobody meant to install."""
        with self.assertRaises(GenerationError) as refused:
            extension_install.install(["./not-here"], self.home)
        self.assertIn("release file", str(refused.exception))
