"""The folder the board reads, against the forge's trunk: behind it, and holding commits only it has (#166).

manda's board read the person's checkout, which sat on a day-old `main` while the forge's took 493 commits,
so it drew none of the day's slices and said nothing; and three commits on that `main` were never pushed
and never mentioned. Each case is a real repository with a bare one beside it as the forge, read through
the board's own poll.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai.checkout_level import level


class CheckoutTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.forge = self.root.parent / f"{self.root.name}.git"
        self.git("init", "--quiet", "--bare", "--initial-branch=main", str(self.forge))
        self.git("init", "--quiet", "--initial-branch=main")
        (self.root / ".gitignore").write_text(".slipwai/\n", encoding="utf-8")
        self.commit("the skeleton")
        self.git("remote", "add", "origin", str(self.forge))
        self.git("push", "--quiet", "origin", "main")
        self.git("fetch", "--quiet", "origin")

    def git(self, *argv: str) -> str:
        done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv], cwd=self.root,
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def commit(self, message: str, path: str = "") -> None:
        if path:
            (self.root / path).write_text(message + "\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "--quiet", "--allow-empty", "-m", message)

    def forge_moves(self, count: int) -> None:
        """Trunk on the forge takes `count` commits this checkout does not have, as the fleet's merges do."""
        self.git("switch", "--quiet", "-c", "elsewhere", "origin/main")
        for n in range(count):
            self.commit(f"merged on the forge {n}")
        self.git("push", "--quiet", "origin", "elsewhere:main")
        self.git("switch", "--quiet", "main")
        self.git("branch", "--quiet", "-D", "elsewhere")
        self.git("fetch", "--quiet", "origin")

    def live(self) -> dict:
        return json.loads(self.get("/live.json")[1])

    def test_a_level_checkout_says_nothing(self) -> None:
        self.assertEqual(level(self.root), {"trunk": "main", "behind": 0, "stranded": []})
        found = self.live()
        self.assertNotIn('id="checkout"', found["bands"]["trunk"]["html"])
        self.assertEqual(found["waiting"]["count"], 0)

    def test_a_checkout_behind_the_forge_says_so_at_the_top_with_the_count(self) -> None:
        self.forge_moves(3)
        band = self.live()["bands"]["trunk"]["html"]
        self.assertIn("This checkout is 3 commits behind the forge's main", band)
        self.assertIn("git pull --ff-only", band)
        page = self.get("/voyage")[1]
        self.assertLess(page.index('id="checkout"'), page.index('<nav class="tabs" role="tablist"'))

    def test_commits_only_the_local_trunk_has_are_waiting_on_you_by_subject(self) -> None:
        self.commit("D499: <b>a decision</b> made here", "decision.md")
        self.forge_moves(2)
        found = self.live()
        listed = found["waiting"]
        self.assertEqual(listed["holding"][0]["href"], "#checkout")
        self.assertIn("Local main has 1 commit the forge's main does not", listed["holding"][0]["text"])
        self.assertIn("D499: <b>a decision</b> made here", listed["holding"][0]["text"])
        band = found["bands"]["trunk"]["html"]
        self.assertIn("2 commits behind", band)
        self.assertIn("D499: &lt;b&gt;a decision&lt;/b&gt; made here", band, "escaped, never markup")
        self.assertIn("git branch keep-local main", band)
        self.assertNotIn("git pull --ff-only", band, "a pull does not land a diverged trunk")

    def test_commits_ahead_of_a_level_forge_are_still_named(self) -> None:
        self.commit("ADR 0027", "adr.md")
        found = self.live()
        self.assertIn("ADR 0027", found["waiting"]["holding"][0]["text"])
        self.assertIn("This checkout has commits trunk does not", found["bands"]["trunk"]["html"])

    def test_no_forge_trunk_is_nothing_to_be_behind(self) -> None:
        self.git("remote", "remove", "origin")
        self.assertEqual(level(Path(self.root)), {})
