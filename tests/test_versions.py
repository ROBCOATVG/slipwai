"""How a version string reads, and how a snapshot of `main` gets its number.

Two shapes — `1.13.0` and `1.13.0.dev4` — and everything that reads them agrees through `slipwai.versions`:
the upgrade verb sorts and filters by it, the catch-up notes take a snapshot as its release through it, and
the release and snapshot scripts import it. So the properties gated here are the ones a mistake in it would
spread everywhere at once: a snapshot sorts below its release and above the release before, the next
snapshot after a release is the next PATCH, and `snapshot-version.py` counts from the last release tag.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import ROOT
from slipwai.versions import (
    base,
    is_prerelease,
    is_release,
    is_snapshot,
    key,
    next_snapshot,
    parse_range,
    satisfies,
    snapshot,
)

SCRIPT = ROOT / "scripts/snapshot-version.py"


class VersionsTest(unittest.TestCase):
    def test_a_number_past_the_digit_limit_is_not_a_version_and_never_raises(self) -> None:
        for text in ("1." + "9" * 5000 + ".0", "1.0.0.dev" + "1" * 5000):
            self.assertIsNone(base(text))
            self.assertFalse(is_release(text) or is_snapshot(text))
            self.assertEqual(key(text), (0,))

    def test_a_snapshot_is_its_release_not_yet_there(self) -> None:
        self.assertEqual(base("1.13.0.dev4"), "1.13.0")
        self.assertEqual(base("1.13.0"), "1.13.0")
        self.assertIsNone(base("snapshot"))
        self.assertTrue(is_snapshot("1.13.0.dev0"))
        self.assertFalse(is_snapshot("1.13.0"))
        self.assertTrue(is_release("1.13.0"))
        self.assertFalse(is_release("1.13.0.dev0"))
        self.assertFalse(is_release("1.13.0rc1"))
        self.assertTrue(is_prerelease("1.13.0rc1"))
        self.assertFalse(is_prerelease("not a version"), "an unreadable string is not a pre-release either")

    def test_versions_sort_the_way_an_installer_sorts_them(self) -> None:
        """Numerically, and with every pre-release of a number below the number itself."""
        self.assertGreater(key("1.5.10"), key("1.5.9"))
        self.assertLess(key("1.13.0.dev4"), key("1.13.0"))
        self.assertGreater(key("1.13.0.dev4"), key("1.12.0"))
        self.assertLess(key("1.13.0.dev4"), key("1.13.0.dev12"))
        self.assertLess(key("1.13.0.dev12"), key("1.13.0rc1"))
        self.assertLess(key("1.13.0rc1"), key("1.13.0"))
        self.assertLess(key("garbage"), key("0.0.1"), "a stray file in the registry sorts below every release")
        ordered = ["1.12.0", "1.12.1.dev3", "1.13.0.dev1", "1.13.0.dev2", "1.13.0"]
        self.assertEqual(sorted(reversed(ordered), key=key), ordered)

    def test_the_next_snapshot_after_a_release_is_the_next_patch(self) -> None:
        """The smallest claim: the first change that lands raises it to whatever it needs."""
        self.assertEqual(next_snapshot("1.13.0"), "1.13.1.dev0")
        self.assertEqual(next_snapshot("1.13.9"), "1.13.10.dev0")
        self.assertEqual(snapshot("1.13.0.dev0", 7), "1.13.0.dev7")
        with self.assertRaises(ValueError):
            next_snapshot("snapshot")


@unittest.skipUnless(SCRIPT.is_file(), "scripts/snapshot-version.py comes back with the release machinery in slice 8.1")
class SnapshotVersionTest(unittest.TestCase):
    """`scripts/snapshot-version.py`, against a history with a release tag in it."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name)
        # The script reads ROOT from its own location, so it runs against a copy of itself beside the
        # module it imports — the same two files the real one has.
        (self.repo / "scripts").mkdir()
        (self.repo / "src/slipwai").mkdir(parents=True)
        (self.repo / "scripts/snapshot-version.py").write_text(SCRIPT.read_text(encoding="utf-8"))
        (self.repo / "src/slipwai/versions.py").write_text(
            (ROOT / "src/slipwai/versions.py").read_text(encoding="utf-8"), encoding="utf-8")
        (self.repo / "src/slipwai/__init__.py").write_text("", encoding="utf-8")
        self.git("init", "--initial-branch=main")
        self.git("config", "user.email", "snapshot@example.com")
        self.git("config", "user.name", "Snapshot Test")
        self.write_version("1.2.3")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Release 1.2.3")
        self.git("tag", "-a", "v1.2.3", "-m", "slipwai 1.2.3")

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repo), *arguments], text=True, capture_output=True, check=True
        ).stdout.strip()

    def write_version(self, version: str) -> None:
        (self.repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")

    def commit(self, subject: str) -> None:
        (self.repo / subject).write_text("\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject)

    def run_script(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(self.repo / "scripts/snapshot-version.py"), *arguments],
            text=True, capture_output=True,
            # No `__pycache__` beside the copied module, so `git status` below shows only what the script wrote.
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_the_number_counts_the_commits_since_the_last_release(self) -> None:
        self.write_version("1.2.4.dev0")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Open 1.2.4.dev0")
        self.commit("one")
        self.commit("two")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "1.2.4.dev3")
        self.assertEqual((self.repo / "VERSION").read_text(encoding="utf-8").strip(), "1.2.4.dev0",
            "printing does not write")

    def test_the_count_keeps_rising_when_the_number_is_raised_mid_cycle(self) -> None:
        """Counted from the tag rather than from the commit that opened the number, so raising `1.2.4.dev0`
        to `1.3.0.dev0` cannot make a later snapshot sort below an earlier one."""
        self.write_version("1.2.4.dev0")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Open 1.2.4.dev0")
        self.commit("one")
        self.write_version("1.3.0.dev0")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "MINOR: something new")
        result = self.run_script()
        self.assertEqual(result.stdout.strip(), "1.3.0.dev3")
        self.assertGreater(key("1.3.0.dev3"), key("1.2.4.dev2"))

    def test_write_puts_the_number_in_version_for_one_build_and_commits_nothing(self) -> None:
        self.write_version("1.2.4.dev0")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Open 1.2.4.dev0")
        result = self.run_script("--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.repo / "VERSION").read_text(encoding="utf-8"), "1.2.4.dev1\n")
        self.assertEqual(self.git("status", "--porcelain").split(), ["M", "VERSION"], "written, never committed")

    def test_a_release_commit_is_not_a_snapshot_and_says_so_with_its_own_exit_code(self) -> None:
        """The `Release 1.2.3` commit: the tag publishes it, and the snapshot job has to know to stand down
        without that being a failure."""
        result = self.run_script("--write")
        self.assertEqual(result.returncode, 3)
        self.assertIn("a release rather than a snapshot", result.stderr)
        self.assertEqual((self.repo / "VERSION").read_text(encoding="utf-8"), "1.2.3\n", "nothing written")

    def test_a_history_that_has_never_released_counts_from_its_root(self) -> None:
        self.git("tag", "-d", "v1.2.3")
        self.write_version("0.1.0.dev0")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Open 0.1.0.dev0")
        result = self.run_script()
        self.assertEqual(result.stdout.strip(), "0.1.0.dev2")


@unittest.skipUnless((ROOT / "scripts/publish-wheel.py").is_file(),
                     "scripts/publish-wheel.py comes back with the release machinery in slice 8.1")
class RetiringSnapshotsTest(unittest.TestCase):
    """`scripts/publish-wheel.py`: which of the registry's versions a publish retires — every snapshot below
    it, and never a release."""

    def setUp(self) -> None:
        import importlib.util

        specification = importlib.util.spec_from_file_location("publish_wheel", ROOT / "scripts/publish-wheel.py")
        assert specification is not None and specification.loader is not None
        self.module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(self.module)

    def test_a_snapshot_retires_the_snapshots_before_it_and_a_release_retires_them_all(self) -> None:
        held = self.module.versions_of({
            "slipwai-1.12.0-py3-none-any.whl", "slipwai-1.12.0.tar.gz", "slipwai-1.12.1.dev2-py3-none-any.whl",
            "slipwai-1.13.0.dev5-py3-none-any.whl", "slipwai-1.13.0.dev5.tar.gz",
            "slipwai-1.13.0.dev9-py3-none-any.whl",
        })
        self.assertEqual(held, {"1.12.0", "1.12.1.dev2", "1.13.0.dev5", "1.13.0.dev9"})
        self.assertEqual(self.module.superseded(held, "1.13.0.dev9"), ["1.12.1.dev2", "1.13.0.dev5"])
        self.assertEqual(self.module.superseded(held, "1.13.0"), ["1.12.1.dev2", "1.13.0.dev5", "1.13.0.dev9"])
        self.assertEqual(self.module.superseded(held, "1.12.1.dev1"), [], "nothing below it is a snapshot")
        self.assertNotIn("1.12.0", self.module.superseded(held, "2.0.0"), "a release is spent, and spent means kept")


class RangeGrammarTest(unittest.TestCase):
    """A language package says which the keel it loads on as comma-joined `>=`, `<` and `==` clauses."""

    def test_a_range_admits_what_is_inside_it_and_refuses_what_is_outside(self) -> None:
        for admitted in ("9.0", "9.7", "9"):
            self.assertTrue(satisfies(admitted, ">=9.0,<10"), admitted)
        for refused in ("8", "10.0", "10"):
            self.assertFalse(satisfies(refused, ">=9.0,<10"), refused)

    def test_a_missing_part_reads_as_zero(self) -> None:
        self.assertTrue(satisfies("9.0", "==9.0"))
        self.assertTrue(satisfies("9", "==9.0"))
        self.assertTrue(satisfies("9.0", "==9"))
        self.assertTrue(satisfies("9.0", ">=9"))
        self.assertFalse(satisfies("9.1", "==9"))

    def test_only_the_three_operators_over_dotted_integers_parse(self) -> None:
        for text in (">9.0", "<=10", "~=9.0", "!=9.1", ">=9.0.x", "", ">=9.0,", ">=9.0,,<10", ">= 9.0", "9.0"):
            with self.assertRaises(ValueError, msg=repr(text)) as caught:
                parse_range(text)
            self.assertEqual(str(caught.exception), f"core range {text!r} is not >=, < or == over dotted integers")

    def test_a_range_that_does_not_parse_is_never_a_pass(self) -> None:
        with self.assertRaises(ValueError):
            satisfies("9.0", ">9.0")

    def test_spaces_around_a_clause_are_stripped(self) -> None:
        self.assertTrue(satisfies("9.5", " >=9.0 , <10 "))


if __name__ == "__main__":
    unittest.main()
