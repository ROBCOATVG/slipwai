"""The remote a person gave is published: created on GitHub where it is missing, and main pushed to it.

game-club-manager-new was given `https://github.com/luke-gee/game-club-manager` on the board, and nothing ever
created it. The cloud targets' bootstrap creates the repository and pushes at the end of `./init`; a target
that deploys nothing only had `origin` added. A forge with no such repository is one the harbourmaster
cannot read trunk's CI on, so the fleet's first merge would have been refused after a slice's worth of work.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import trunk_remote

URL = "https://github.com/me/demo"


@unittest.skipIf(sys.platform == "win32", "the stand-in `gh` is a shell script, which Windows does not run "
                 "by that name: it finds the runner's own gh.exe instead, which would ask the real GitHub")
class PublishTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        home = Path(self.dir.name)
        self.root, self.forge, self.bin = home / "demo", home / "forge.git", home / "bin"
        self.root.mkdir()
        self.bin.mkdir()
        self.git("init", "--quiet", "--initial-branch=main")
        (self.root / "README.md").write_text("demo\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "scaffold")
        self.calls = home / "gh-calls"
        # A `gh` that answers `repo view` as GitHub does for a repository that is not there, and makes the
        # repository on `repo create` — as a bare one that the GitHub URL is rewritten to.
        gh = self.bin / "gh"
        gh.write_text(f"""#!/bin/sh
echo "$@" >> {self.calls}
case "$2" in
  view) [ -d {self.forge} ] || {{ echo 'GraphQL: Could not resolve to a Repository' >&2; exit 1; }} ;;
  create) git init --quiet --bare --initial-branch=main {self.forge} ;;
esac
""", encoding="utf-8")
        gh.chmod(0o755)
        self.git("config", f"url.{self.forge}.insteadOf", URL)
        env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}"}
        patched = mock.patch.object(trunk_remote, "login_environment", return_value=env)
        patched.start()
        self.addCleanup(patched.stop)

    def git(self, *argv: str, where: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                              cwd=where or self.root, capture_output=True, text=True, check=False)

    def test_a_github_remote_that_is_not_there_is_created_private_and_main_is_pushed(self) -> None:
        said = trunk_remote.add_remote(self.root, URL)
        self.assertIn("repo create me/demo --private", self.calls.read_text(encoding="utf-8"))
        self.assertEqual(self.git("rev-parse", "main", where=self.forge).stdout, self.git("rev-parse", "main").stdout)
        self.assertIn("Created me/demo on GitHub, private.", said)
        self.assertIn("Pushed main", said)

    def test_a_remote_that_is_there_is_pushed_to_and_not_created(self) -> None:
        subprocess.run(["git", "init", "--quiet", "--bare", "--initial-branch=main", str(self.forge)], check=True)
        said = trunk_remote.add_remote(self.root, URL)
        self.assertNotIn("create", self.calls.read_text(encoding="utf-8"))
        self.assertIn("Pushed main", said)

    def test_a_remote_given_while_the_project_is_made_is_published_after_init_s_commit(self) -> None:
        """`given` runs before `./init`: pushing then would publish a scaffold `./init` is about to add to."""
        trunk_remote.given(self.root, URL)
        self.assertFalse(self.forge.exists(), "published before ./init's work was committed")
        steps = trunk_remote.publishing(self.root)
        self.assertEqual(len(steps), 1)
        lines: list[str] = []
        session = steps[0].session
        assert session is not None
        self.assertEqual(session(mock.Mock(say=lines.append)), 0)
        self.assertTrue(any(line.startswith("Pushed main") for line in lines), lines)

    def test_a_push_that_cannot_happen_is_said_and_never_fails_the_run(self) -> None:
        (self.bin / "gh").write_text("#!/bin/sh\necho 'HTTP 403: no' >&2\nexit 1\n", encoding="utf-8")
        said = trunk_remote.add_remote(self.root, URL)
        self.assertIn("could not be created (HTTP 403: no)", said)
        self.assertIn("git push -u origin main", said)

    def test_no_origin_is_nothing_to_publish(self) -> None:
        self.assertEqual(trunk_remote.publishing(self.root), ())


if __name__ == "__main__":
    unittest.main()
