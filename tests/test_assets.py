"""The asset trees, and the modules that read them.

Four trees arrived together — the toolkit, the profiles, the frontends and the adoption ratchet — because
`toolkit.py`, `examples.py` and `harness.py` cannot be asked anything without them. Their own suites in
the experiment generate a project to check the answer, which needs the scaffold and comes back in slice
3.3b. What is here is what can be asked of a tree directly: that it is there, that reading it is faithful
to the bytes, and that a path leaving it is refused.

The last of those is the one that matters. A package supplies code the keel runs and files the keel
copies, and `inside` is the whole of what stops one reading somebody else's.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import harness, toolkit
from slipwai.assets import (
    ADOPTION_ROOT,
    FRONTEND_ROOT,
    PAGE_ROOT,
    PROFILE_ROOT,
    ROOT,
    TOOLKIT_ROOT,
    asset_tree,
    inside,
    located,
    read_faithfully,
)


class TreesTest(unittest.TestCase):
    def test_every_tree_the_keel_names_is_there(self) -> None:
        """A root naming a directory that does not exist is a generation that fails halfway through."""
        for name, root in (("toolkit", TOOLKIT_ROOT), ("profiles", PROFILE_ROOT),
                           ("frontends", FRONTEND_ROOT), ("adoption", ADOPTION_ROOT),
                           ("pages", PAGE_ROOT)):
            with self.subTest(tree=name):
                self.assertTrue(root.is_dir(), root)

    def test_the_toolkit_is_read_as_a_tree_of_paths_to_text(self) -> None:
        tree = asset_tree(TOOLKIT_ROOT)
        self.assertGreater(len(tree), 100)
        self.assertTrue(all(not path.startswith("/") for path in tree), "paths are relative to the root")

    def test_no_interpreter_cache_is_read_as_an_asset(self) -> None:
        """A script under `assets/` that something imported leaves a `__pycache__` beside it, and a
        generated project does not want one."""
        self.assertFalse([path for path in asset_tree(TOOLKIT_ROOT) if "__pycache__" in path])


class FaithfulReadTest(unittest.TestCase):
    """An asset is copied into a generated project byte for byte, line endings included."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_crlf_survives_being_read(self) -> None:
        """`mvnw.cmd` is CRLF throughout and re-reads itself with `Get-Content -Raw`; flattening it is not
        a cosmetic difference, it is a script Windows cannot run."""
        path = self.root / "mvnw.cmd"
        path.write_bytes(b"@echo off\r\nexit /b 0\r\n")
        self.assertEqual(read_faithfully(path), "@echo off\r\nexit /b 0\r\n")

    def test_lf_survives_too(self) -> None:
        path = self.root / "mvnw"
        path.write_bytes(b"#!/bin/sh\nexit 0\n")
        self.assertEqual(read_faithfully(path), "#!/bin/sh\nexit 0\n")

    def test_an_asset_is_utf_8_whatever_the_machine_reading_it_thinks(self) -> None:
        """Without an explicit encoding Python uses the platform's locale codec, which on Windows is
        cp1252 and cannot decode the first em dash in the toolkit. An asset is bytes the keel copies
        into somebody's repository, and the machine it is copied on must not change them."""
        path = self.root / "prose.md"
        path.write_bytes("a — dash, a ✓ tick, a £ sign\n".encode())
        self.assertEqual(read_faithfully(path), "a — dash, a ✓ tick, a £ sign\n")

    def test_the_whole_toolkit_reads_on_this_machine(self) -> None:
        """The regression itself: one non-ASCII byte anywhere in 250 files was enough to stop a build."""
        self.assertGreater(len(asset_tree(TOOLKIT_ROOT)), 100)


class ContainmentTest(unittest.TestCase):
    """What stops a package reading a file that is not its own."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_a_path_inside_the_root_is_returned(self) -> None:
        self.assertEqual(inside(self.root, "a/b.txt"), self.root / "a/b.txt")

    def test_a_path_that_climbs_out_is_refused(self) -> None:
        with self.assertRaises(ValueError) as raised:
            inside(self.root, "../elsewhere.txt")
        self.assertIn("reaches outside its directory", str(raised.exception))

    def test_an_assets_directory_that_is_a_link_out_is_the_same_escape(self) -> None:
        """`root.resolve()` alone would call the link's target home, which is the hole this closes."""
        package = self.root / "package"
        (package / "real").mkdir(parents=True)
        outside = self.root / "outside"
        outside.mkdir()
        link = package / "assets"
        link.symlink_to(outside)
        with self.assertRaises(ValueError):
            inside(link, "x.txt", package)

    def test_located_takes_the_first_root_that_holds_the_file(self) -> None:
        """A framework reads its own files before its family's, which is what the order is for."""
        first, second = self.root / "first", self.root / "second"
        for root in (first, second):
            (root / "assets").mkdir(parents=True)
        (second / "assets/only-in-second.txt").write_text("x", encoding="utf-8")
        (first / "assets/in-both.txt").write_text("first", encoding="utf-8")
        (second / "assets/in-both.txt").write_text("second", encoding="utf-8")
        self.assertEqual(located((first, second), "in-both.txt"), (first, first / "assets/in-both.txt"))
        found = located((first, second), "only-in-second.txt")
        assert found is not None
        self.assertEqual(found[0], second)

    def test_located_answers_none_rather_than_guessing(self) -> None:
        self.assertIsNone(located((self.root,), "nothing-here.txt"))


class ToolkitTest(unittest.TestCase):
    def test_the_canonical_language_is_the_keels_own_and_not_a_package(self) -> None:
        """The toolkit's prose and snippets are written in one language, and it is the keel's material."""
        self.assertEqual(toolkit.CANON, "typescript")

    def test_a_skill_path_is_told_from_any_other_asset(self) -> None:
        self.assertEqual(toolkit.skill_of("skills/tdd/SKILL.md"), "tdd")
        self.assertIsNone(toolkit.skill_of("scripts/verify"))

    def test_the_toolkit_carries_nothing_belonging_to_one_extension(self) -> None:
        """Slice 6.1c. The keel names no extension and ships none, so a project that elected nothing
        carries no file that only an extension would use — and the two that slipped through did it by
        being written before extensions were packages at all: a code index's pinned CLI wrapper and the
        script that kept its database. They live in that index's own package now.

        The rule is read off the names rather than the contents, because a name is what a person adding
        a file chooses: a toolkit script named after a product is a product the keel has taken sides on.
        """
        shipped = [path for path in asset_tree(TOOLKIT_ROOT) if path.startswith("scripts/")]
        self.assertTrue(shipped, "no toolkit scripts were read; the check proved nothing")
        named = sorted(
            path for path in shipped
            # `scripts/extensions/` is where an elected extension's own files land inside a project, so a
            # path under it is the only one entitled to carry a product's name — and nothing is there in
            # the keel's own tree, which this also holds.
            if not path.startswith("scripts/extensions/")
            and any(word in path.lower() for word in ("codegraph", "code_index", "uipro", "ux-gates"))
        )
        self.assertEqual(named, [], "the toolkit ships a file belonging to one extension")


class HarnessTest(unittest.TestCase):
    def test_the_registry_is_read_from_the_toolkit_and_names_the_harnesses(self) -> None:
        keys = harness.keys()
        self.assertIn("claude", keys)
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_harness_has_a_name_a_person_would_recognise(self) -> None:
        # Bound first: `harness.keys()` is a module function, and ruff reads `x.keys()` as a dict's.
        registered = harness.keys()
        for key in registered:
            with self.subTest(harness=key):
                self.assertTrue(harness.name_of(key))

    def test_the_registry_file_is_where_the_module_says_it_is(self) -> None:
        self.assertTrue(harness.REGISTRY.is_file(), harness.REGISTRY.relative_to(ROOT))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
