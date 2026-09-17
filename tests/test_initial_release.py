"""The public 1.0.0 release starts without inventing a predecessor."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from slipwai.assets import ROOT

SCRIPT = ROOT / "scripts/tag-release.py"


def git(repo: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *arguments],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


class InitialReleaseTest(unittest.TestCase):
    def test_the_first_public_release_needs_no_fake_predecessor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            forge, repo = root / "forge.git", root / "checkout"
            subprocess.run(
                ["git", "init", "--bare", "--initial-branch=main", str(forge)],
                check=True,
                capture_output=True,
            )
            repo.mkdir()
            git(repo, "init", "--initial-branch=main")
            git(repo, "config", "user.email", "release@example.com")
            git(repo, "config", "user.name", "Release Test")
            (repo / "VERSION").write_text("1.0.0.dev0\n")
            (repo / "CHANGELOG.md").write_text(
                "# Changelog\n\nThe public version line begins at 1.0.0.\n"
            )
            (repo / "changelog.d").mkdir()
            (repo / "changelog.d/README.md").write_text("# The entry being written\n")
            (repo / "changelog.d/initial.md").write_text(
                "MAJOR\n\n**The first public release.** Nothing preceded it.\n"
            )
            git(repo, "add", "-A")
            git(repo, "commit", "-m", "prepare the first public release")
            git(repo, "remote", "add", "gitea", str(forge))
            git(repo, "push", "gitea", "main")

            command = ["python3", str(SCRIPT), "--repository", str(repo)]
            dry = subprocess.run([*command, "--dry-run"], text=True, capture_output=True)
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertIn("would assemble: `## 1.0.0`", dry.stdout)
            self.assertIn("would tag: v1.0.0 (slipwai 1.0.0)", dry.stdout)

            done = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(git(forge, "show", "main:VERSION"), "1.0.1.dev0")
            changelog = git(forge, "show", "main:CHANGELOG.md")
            self.assertIn("## 1.0.0\n\n**The first public release.**", changelog)
            self.assertNotIn("## 1.0.0 —", changelog)


if __name__ == "__main__":
    unittest.main()
