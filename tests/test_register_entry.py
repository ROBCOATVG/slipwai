"""Registering by hand lists the file that was published, not a second build of it (#117).

A package's CI builds the release off its tag and attaches the file and its entry to the tag. Where it has no token
for the channel it says how to finish by hand, and what it said was `package register . --channel …`: a rebuild, in
whatever clone the publisher had, whose digest was then written beside a URL pointing at CI's file. `--entry` takes
the entry CI wrote instead, so nothing is built and nothing can differ.
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import channel, channel_new, package_new, package_release
from slipwai.cli_package import package_main
from slipwai.errors import GenerationError

CORE = "9.0"
URL = "https://example.invalid/lens/releases/download/v1.0.0/lens-1.0.0.tar.gz"
ROOT = Path(__file__).resolve().parents[1]


class EntryCase(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.channel = self.area / "channel"
        channel_new.write("a channel", self.channel)
        self.root = self.area / "lens"
        package_new.write("extension", "lens", self.area, CORE)
        (self.root / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        _, self.entry_file, self.entry = package_release.release(self.root, self.area / "dist", "ACME", URL)

    def listed(self) -> dict:
        return json.loads((self.channel / "entries/lens-1.0.0.json").read_text(encoding="utf-8"))


class RegisterEntryTest(EntryCase):
    def test_the_entry_a_release_wrote_is_listed_as_it_stands_and_nothing_is_built(self) -> None:
        """The clone has moved on since the release: what is listed is still the file that was published."""
        (self.root / "README.md").write_text("edited since the tag\n", encoding="utf-8")
        (self.root / "left-empty").mkdir()
        archive, entry_file, _ = package_release.register(self.root, self.channel, entry_file=self.entry_file)
        self.assertIsNone(archive)
        self.assertEqual(entry_file.read_bytes(), self.entry_file.read_bytes())
        self.assertEqual(self.listed()["sha256"], self.entry["sha256"])
        self.assertEqual(list(self.channel.rglob("*.tar.gz")), [])
        self.assertEqual(channel.check(self.channel), [])

    def test_without_it_the_same_clone_lists_a_digest_nobody_published(self) -> None:
        """What the fallback did. A directory in no repository is still walked, so there a rebuild can still differ
        from the file CI built — which is why the fallback no longer says to rebuild."""
        (self.root / "left-empty").mkdir()
        package_release.register(self.root, self.channel, "ACME", file_url=URL)
        self.assertNotEqual(self.listed()["sha256"], self.entry["sha256"])

    def test_an_entry_for_another_package_is_refused(self) -> None:
        package_new.write("extension", "other", self.area, CORE)
        with self.assertRaises(GenerationError) as refused:
            package_release.register(self.area / "other", self.channel, entry_file=self.entry_file)
        self.assertIn("is not an entry for other", str(refused.exception))

    def test_an_entry_naming_a_file_beside_the_index_is_refused_because_the_file_was_not_given(self) -> None:
        _, beside, _ = package_release.release(self.root, self.area / "beside")
        with self.assertRaises(GenerationError) as refused:
            package_release.register(self.root, self.channel, entry_file=beside)
        self.assertIn("--file-url", str(refused.exception))
        self.assertFalse((self.channel / "entries/lens-1.0.0.json").exists())

    def test_an_entry_with_no_digest_or_that_is_not_json_is_refused(self) -> None:
        for body in (json.dumps({"name": "lens", "version": "1.0.0", "file": URL}), "not json"):
            self.entry_file.write_text(body, encoding="utf-8")
            with self.assertRaises(GenerationError):
                package_release.register(self.root, self.channel, entry_file=self.entry_file)

    def test_a_version_already_listed_with_another_file_is_still_refused(self) -> None:
        package_release.register(self.root, self.channel, entry_file=self.entry_file)
        package_release.register(self.root, self.channel, entry_file=self.entry_file)  # the same bytes: nothing new
        self.entry_file.write_text(json.dumps({"name": "lens", **self.entry, "sha256": "0" * 64}), encoding="utf-8")
        with self.assertRaises(GenerationError) as refused:
            package_release.register(self.root, self.channel, entry_file=self.entry_file)
        self.assertIn("already lists lens 1.0.0", str(refused.exception))


class VerbTest(EntryCase):
    def said(self, *argv: str) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try:
                package_main(list(argv))
            except SystemExit as stopped:
                out.write(f"\nexit {stopped.code}")
        return out.getvalue()

    def test_the_verb_takes_the_entry_and_says_which_file_it_listed(self) -> None:
        said = self.said("register", str(self.root), "--entry", str(self.entry_file), "--channel", str(self.channel))
        self.assertIn(URL, said)
        self.assertIn(self.entry["sha256"], said)
        self.assertEqual(self.listed()["sha256"], self.entry["sha256"])

    def test_what_the_entry_already_says_cannot_be_said_again_beside_it(self) -> None:
        said = self.said("register", str(self.root), "--entry", str(self.entry_file), "--channel", str(self.channel),
                         "--file-url", URL)
        self.assertIn("--entry", said)
        self.assertIn("exit", said)
        self.assertFalse((self.channel / "entries/lens-1.0.0.json").exists())

    def test_a_release_given_a_url_says_to_register_its_entry(self) -> None:
        said = self.said("release", str(self.root), "--out", str(self.area / "again"), "--file-url", URL)
        self.assertIn("--entry", said)

    def test_a_rebuild_listed_beside_a_url_says_what_proves_it(self) -> None:
        said = self.said("register", str(self.root), "--channel", str(self.channel), "--file-url", URL)
        self.assertIn("channel check", said)
        self.assertIn("--fetch", said)


class FallbackTest(unittest.TestCase):
    """What a package's CI tells its publisher to run where it could not offer the release itself."""

    def test_the_workflow_names_the_command_that_registers_what_it_built(self) -> None:
        text = (ROOT / ".github/workflows/package.yml").read_text(encoding="utf-8")
        said = text[text.index("no chandlery_token"):text.index("exit 0", text.index("no chandlery_token"))]
        self.assertIn("slipwai package register . --entry", said)
        self.assertIn("gh release download", said)
        self.assertEqual([line for line in said.splitlines() if "package register" in line and "--entry" not in line],
                         [])


if __name__ == "__main__":
    unittest.main()
