"""A release is what the tag holds (#117): in a git repository, the files `HEAD` tracks and nothing else.

`codegraph` 1.0.1 was registered by hand from a clone holding an empty `changelog.d/`. Git tracks no empty directory,
so CI's archive had twenty members and the clone's twenty-one, and the digest written into the index was of a file
nobody had published. The first case here is that clone.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import package_new, package_release
from slipwai.errors import GenerationError
from slipwai.language_release import pack

CORE = "9.0"
#: No identity, hook or setting of the person running the suite: the repository under test is the case's own.
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
SET = ("-c", "user.name=t", "-c", "user.email=t@local", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false",
       "-c", "protocol.file.allow=always")


def git(where: Path, *argv: str) -> str:
    return subprocess.run(["git", *SET, *argv], cwd=where, env=ENV, text=True, capture_output=True, check=True).stdout


def committed(where: Path, message: str = "a package") -> None:
    git(where, "add", "-A")
    git(where, "commit", "-q", "-m", message)


def repository(area: Path, key: str = "lens", inside: str = "") -> Path:
    """A scaffolded package committed to a repository of its own, or under `inside` in a larger one."""
    top = area / (key if not inside else "repository")
    root = top / inside / key if inside else top
    root.parent.mkdir(parents=True, exist_ok=True)
    package_new.write("extension", key, root.parent, CORE)
    git(area, "init", "-q", "-b", "main", str(top))
    committed(top)
    return root


def members(archive: Path) -> list[str]:
    with tarfile.open(archive, "r:gz") as tar:
        return tar.getnames()


class GitCase(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.area, True)
        environment = mock.patch.dict(os.environ, ENV)
        environment.start()
        self.addCleanup(environment.stop)


class TrackedTest(GitCase):
    def test_a_clone_holding_what_a_clean_checkout_does_not_builds_the_same_file(self) -> None:
        root = repository(self.area)
        (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        committed(root, "what is ignored")
        clean = pack(root, self.area / "clean").read_bytes()
        (root / "notes.txt").write_text("a scratch note nobody committed\n", encoding="utf-8")
        (root / "ignored.txt").write_text("a local setting\n", encoding="utf-8")
        (root / "changelog.d").mkdir(exist_ok=True)
        (root / "left-empty").mkdir()
        archive = pack(root, self.area / "again")
        self.assertEqual(archive.read_bytes(), clean)
        self.assertEqual([name for name in members(archive) if "notes" in name or "ignored.txt" in name
                          or "left-empty" in name], [])

    def test_a_clean_checkout_builds_the_file_the_directory_built_before(self) -> None:
        """Releases already published keep their digest: what a walk of a clean checkout held is what `HEAD` holds."""
        root = repository(self.area)
        (root / "hooks/deep").mkdir(parents=True)
        (root / "hooks/deep/a-b.py").write_text("pass\n", encoding="utf-8")
        (root / "hooks/deep.py").write_text("pass\n", encoding="utf-8")
        (root / "Zed.md").write_text("capitals sort first on one platform and not another\n", encoding="utf-8")
        committed(root, "more")
        outside = self.area / "unpacked/lens"
        shutil.copytree(root, outside, ignore=shutil.ignore_patterns(".git"))
        walked = pack(outside, self.area / "walked").read_bytes()
        self.assertEqual(pack(root, self.area / "tracked").read_bytes(), walked)

    def test_outside_a_repository_the_directory_is_walked_as_it_was(self) -> None:
        package_new.write("extension", "lens", self.area, CORE)
        (self.area / "lens/left-empty").mkdir()
        self.assertIn("lens/left-empty", members(pack(self.area / "lens", self.area / "dist")))

    def test_a_package_that_is_a_directory_of_a_larger_repository_holds_its_own_files_only(self) -> None:
        root = repository(self.area, inside="packages")
        (root.parents[1] / "beside.txt").write_text("the repository's, not the package's\n", encoding="utf-8")
        committed(root.parents[1], "beside")
        (root / "untracked.txt").write_text("\n", encoding="utf-8")
        names = members(pack(root, self.area / "dist"))
        self.assertIn("lens/extension.json", names)
        self.assertEqual([name for name in names if "beside" in name or "untracked" in name], [])

    def test_a_tracked_link_refuses_the_release_as_a_link_in_a_directory_does(self) -> None:
        """Recorded in the index by mode, so the case needs no platform that can make a link."""
        root = repository(self.area)
        blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=root, env=ENV, input="extension.json",
                              text=True, capture_output=True, check=True).stdout.strip()
        git(root, "update-index", "--add", "--cacheinfo", f"120000,{blob},alias.json")
        git(root, "commit", "-q", "-m", "a link")
        with self.assertRaises(GenerationError) as refused:
            pack(root, self.area / "dist")
        self.assertIn("alias.json is a link", str(refused.exception))

    def test_a_submodule_is_released_as_the_commit_the_package_records(self) -> None:
        shared = self.area / "shared"
        shared.mkdir()
        (shared / "rule.md").write_text("a rule\n", encoding="utf-8")
        git(self.area, "init", "-q", "-b", "main", str(shared))
        committed(shared, "a rule")
        root = repository(self.area)
        git(root, "submodule", "--quiet", "add", shared.as_posix(), "vendor/shared")
        committed(root, "a submodule")
        (root / "vendor/shared/untracked.md").write_text("\n", encoding="utf-8")
        names = members(pack(root, self.area / "dist"))
        self.assertIn("lens/vendor/shared/rule.md", names)
        self.assertIn("lens/.gitmodules", names)
        self.assertEqual([name for name in names if ".git/" in name or name.endswith("/.git") or "untracked" in name],
                         [])

    def test_a_submodule_not_checked_out_refuses_with_the_command_that_checks_it_out(self) -> None:
        shared = self.area / "shared"
        shared.mkdir()
        (shared / "rule.md").write_text("a rule\n", encoding="utf-8")
        git(self.area, "init", "-q", "-b", "main", str(shared))
        committed(shared, "a rule")
        root = repository(self.area)
        git(root, "submodule", "--quiet", "add", shared.as_posix(), "vendor/shared")
        committed(root, "a submodule")
        clone = self.area / "clone"
        git(self.area, "clone", "-q", str(root), str(clone))
        with self.assertRaises(GenerationError) as refused:
            pack(clone, self.area / "dist")
        self.assertIn("git submodule update --init", str(refused.exception))
        self.assertIn("shared", str(refused.exception))


class SameBytesTest(unittest.TestCase):
    def test_the_file_is_compressed_at_a_level_that_is_said_rather_than_an_interpreter_s_default(self) -> None:
        """`codegraph` 1.0.1 from a clean clone was `ea64e2f6…` on Python 3.11 to 3.13, which is what CI published,
        and `72d09975…` on one whose `gzip` defaults to a lower level: the same tar inside, another file. The header
        says which level wrote it."""
        area = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, area, True)
        package_new.write("extension", "lens", area, CORE)
        self.assertEqual(pack(area / "lens", area / "dist").read_bytes()[8], 2, "not written at level 9")


class RefusalTest(GitCase):
    """`release` and `register` say where the working tree is not what `HEAD` holds, before they build anything."""

    def setUp(self) -> None:
        super().setUp()
        self.root = repository(self.area)
        self.channel = self.area / "channel"

    def refused(self, verb: str = "release") -> str:
        with self.assertRaises(GenerationError) as refused:
            if verb == "release":
                package_release.release(self.root, self.area / "dist")
            else:
                package_release.register(self.root, self.channel)
        self.assertFalse((self.area / "dist").exists() or self.channel.exists(), "something was built")
        return str(refused.exception)

    def test_a_clean_checkout_releases(self) -> None:
        archive, _, _ = package_release.release(self.root, self.area / "dist")
        self.assertIn("lens/extension.json", members(archive))

    def test_an_uncommitted_change_is_refused_by_name_with_what_gets_past_it(self) -> None:
        (self.root / "README.md").write_text("edited and not committed\n", encoding="utf-8")
        for verb in ("release", "register"):
            said = self.refused(verb)
            self.assertIn("README.md (uncommitted change)", said)
            self.assertIn("git stash --include-untracked", said)

    def test_an_untracked_file_is_refused_by_name(self) -> None:
        (self.root / "hooks").mkdir(exist_ok=True)
        (self.root / "hooks/scratch.py").write_text("pass\n", encoding="utf-8")
        for verb in ("release", "register"):
            self.assertIn("hooks/scratch.py (untracked)", self.refused(verb))

    def test_an_ignored_file_and_an_empty_directory_are_no_difference(self) -> None:
        (self.root / ".gitignore").write_text("dist/\n.DS_Store\n", encoding="utf-8")
        committed(self.root, "what is ignored")
        (self.root / ".DS_Store").write_bytes(b"\x00")
        (self.root / "changelog.d").mkdir(exist_ok=True)
        archive, _, _ = package_release.release(self.root, self.root / "dist")
        again, _, _ = package_release.release(self.root, self.root / "dist")
        self.assertEqual(members(archive), members(again))
        self.assertEqual([name for name in members(again) if "dist" in name or "DS_Store" in name], [])

    def test_a_change_beside_the_package_in_a_larger_repository_is_not_the_package_s(self) -> None:
        root = repository(self.area, "scope", inside="packages")
        (root.parents[1] / "beside.txt").write_text("not committed, and not the package's\n", encoding="utf-8")
        package_release.release(root, self.area / "out")

    def test_a_package_its_repository_tracks_nothing_of_is_refused_with_the_command_that_commits_it(self) -> None:
        self.root = repository(self.area, "scope", inside="scratch")
        top = self.root.parents[1]
        git(top, "rm", "-r", "-q", "--cached", "scratch")
        (top / ".gitignore").write_text("scratch/\n", encoding="utf-8")
        committed(top, "a scratch directory, ignored")
        said = self.refused()
        self.assertIn("tracks none of it", said)
        self.assertIn("git add", said)


if __name__ == "__main__":
    unittest.main()
