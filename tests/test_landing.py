"""A stage's commit lands on the forge's trunk through the harbourmaster, and never on local trunk.

The board's triage ran in the person's checkout while it was on `main` and committed twice onto local
`main`, pushing nothing. Every merge after went to the forge's `main`; the harbourmaster could not bring
local `main` forward without dropping those commits, rightly would not, and said so only in a `note`. The
checkout fell 1168 commits behind in a night and the board drew the old project. These cases hold each half:
triage leaves local trunk alone and pushes its own branch; the harbourmaster lands it and still brings the
checkout level over the records the board left untracked; the board names unpushed commits once and drops
the item when they are gone; and `migrate` names them and moves nothing.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT
from slipwai.board_read import unlanded
from slipwai.checkout_level import level
from slipwai.deck import harbour_said
from slipwai.logs import entry
from slipwai.migration_stranded import section, unpushed
from slipwai.trunk_card import checkout_band, stranded_item, unlanded_item

AGENTS = TOOLKIT_ROOT / "scripts/agents"
RECORD = "docs/feedback/0001-the-date-is-wrong.md"
WORDS = "---\nslice: L01\nfeature: f\n---\nThe date is wrong.\n"
PROPOSED = "---\nslice: L01\nfeature: f\nroute: defect\nproposed: 2026-11-27T10:00:00Z\n---\nThe date is wrong.\n"
#: The modules the toolkit loads by bare name; popped so each case loads this project's copies.
BARE = ("triage", "landing", "harness", "logs", "need_check", "fleet", "clearance", "harbourmaster", "claims",
        "mender", "conflicts", "lockfiles", "telegraph", "need_owner", "talk", "travel", "published", "abreast")


def run(root: Path, *argv: str) -> str:
    done = subprocess.run(["git", *argv], cwd=root, capture_output=True, text=True, check=True)
    return done.stdout.strip()


class Harbour(unittest.TestCase):
    """A project with an `origin`, on `main`, with the toolkit's scripts where a project has them."""

    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.origin, self.root = self.base / "origin.git", self.base / "project"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        for argv in (["config", "user.name", "t"], ["config", "user.email", "t@local"],
                     ["remote", "add", "origin", str(self.origin)]):
            run(self.root, *argv)
        place = self.root / "scripts/agents"
        shutil.copytree(AGENTS, place, ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        (self.root / "commands").mkdir()
        (self.root / "commands/triage.md").write_text("# Triage\n", encoding="utf-8")
        (self.root / "Makefile").write_text("verify:\n\t@echo 'verify: all gates passed'\n", encoding="utf-8")
        (self.root / ".gitignore").write_text(".slipwai/\n", encoding="utf-8")
        (self.root / "harbour.json").write_text(json.dumps({"trunk": "main", "ci": "off"}), encoding="utf-8")
        run(self.root, "add", "-A")
        run(self.root, "commit", "-q", "-m", "the project")
        run(self.root, "push", "-q", "origin", "main")
        run(self.root, "fetch", "-q", "origin")
        record = self.root / RECORD
        record.parent.mkdir(parents=True)
        record.write_text(WORDS, encoding="utf-8")  # the board writes it and never commits it

    def load(self, name: str) -> Any:
        place = self.root / "scripts/agents"
        for one in BARE:
            sys.modules.pop(one, None)
        sys.path.insert(0, str(place))
        try:
            spec = importlib.util.spec_from_file_location(name, place / f"{name}.py")
            assert spec and spec.loader
            module: ModuleType = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            return module
        finally:
            sys.path.remove(str(place))

    def triage(self, commits_on_main: bool = False) -> tuple[int, Any]:
        """The real `triage.py`, its session a stand-in that writes the proposal the way a session does."""
        triage = self.load("triage")
        root = self.root

        def session(argv: list[str], cwd: Path | str, env: dict[str, str]) -> int:
            (root / RECORD).write_text(PROPOSED, encoding="utf-8")
            if commits_on_main:  # what commands/triage.md used to ask for
                run(root, "add", "--", RECORD)
                run(root, "commit", "-q", "-m", "Triage feedback 0001")
            return 0

        triage.harness.choose = lambda: ({"name": "stand-in"}, "harness: stand-in")
        triage.harness.template = lambda chosen: ("stand-in {prompt}", "")
        triage.harness.prompt_for = lambda *_: "triage"
        triage.harness.child_environment = lambda chosen: {}
        triage.harness.run_session = session
        return triage.main([]), triage

    def head(self, ref: str) -> str:
        return run(self.root, "rev-parse", ref)

    def slice_branch(self, slice_id: str) -> None:
        run(self.root, "branch", f"slice/{slice_id}", "origin/main")
        worktree = self.base / slice_id
        run(self.root, "worktree", "add", "-q", str(worktree), f"slice/{slice_id}")
        (worktree / f"{slice_id}.txt").write_text(slice_id + "\n", encoding="utf-8")
        run(worktree, "add", "-A")
        run(worktree, "commit", "-q", "-m", f"implement {slice_id}")
        run(self.root, "worktree", "remove", "--force", str(worktree))


class TriageTest(Harbour):
    def test_triage_on_main_leaves_local_main_alone_and_pushes_its_own_branch(self) -> None:
        main = self.head("refs/heads/main")
        exited, _ = self.triage()
        self.assertEqual(exited, 0)
        self.assertEqual(self.head("refs/heads/main"), main, "triage moved local main")
        self.assertEqual(run(self.root, "branch", "--show-current"), "main")
        pushed = run(self.origin, "show", f"refs/heads/triage/0001:{RECORD}")
        self.assertIn("route: defect", pushed)
        self.assertEqual(run(self.origin, "log", "-1", "--format=%s", "triage/0001"), "Triage feedback 0001")
        self.assertEqual((self.root / RECORD).read_text(encoding="utf-8"), PROPOSED)  # the board still sees it
        queued = list((self.root / ".slipwai/landing").glob("*.json"))
        self.assertEqual(len(queued), 1)
        self.assertEqual(json.loads(queued[0].read_text(encoding="utf-8"))["branch"], "triage/0001")

    def test_a_session_that_commits_onto_main_anyway_is_reported_and_left_alone(self) -> None:
        exited, _ = self.triage(commits_on_main=True)
        self.assertEqual(exited, 1)
        self.assertEqual(run(self.root, "log", "-1", "--format=%s", "main"), "Triage feedback 0001")


class HarbourTest(Harbour):
    """End to end: triage on main, the harbourmaster lands it, two slices merge, local main ends level."""

    def test_triage_then_two_merges_leave_local_main_level_with_the_triage_commit_on_the_forge(self) -> None:
        exited, _ = self.triage()
        self.assertEqual(exited, 0)
        self.slice_branch("L01")
        self.slice_branch("L02")
        harbourmaster = self.load("harbourmaster")
        harbourmaster.gate = lambda: [sys.executable, "-c", "print('verify: all gates passed')"]
        landed = harbourmaster.landings("green")
        self.assertEqual([entry.kind for entry in landed], ["landed"], [entry.fields for entry in landed])
        for slice_id in ("L01", "L02"):
            commit, fault, _, note = harbourmaster.merge_branch(f"slice/{slice_id}")
            self.assertTrue(commit, fault)
            self.assertEqual(note, "", f"local main was not brought level: {note}")
        run(self.root, "fetch", "-q", "origin")
        self.assertEqual(self.head("refs/heads/main"), self.head("refs/remotes/origin/main"))
        subjects = run(self.root, "log", "--format=%s", "origin/main").splitlines()
        self.assertIn("Triage feedback 0001", subjects)
        self.assertIn("implement L02", subjects)
        self.assertEqual((self.root / RECORD).read_text(encoding="utf-8"), PROPOSED)
        self.assertEqual(level(self.root, "main")["stranded"], [])


class BoardTest(Harbour):
    """The card a person sees, once whatever the merges, gone once main and the forge agree; and the band."""

    def test_unpushed_commits_are_one_item_until_landed_and_the_band_says_how_far_behind(self) -> None:
        run(self.root, "add", "--", RECORD)
        run(self.root, "commit", "-q", "-m", "Triage feedback 0001")
        run(self.root, "commit", "-q", "--allow-empty", "-m", "Triage feedback 0002")
        other = self.base / "elsewhere"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(other)], check=True)
        for n in range(3):
            run(other, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "--allow-empty",
                "-m", f"merge {n}")
        run(other, "push", "-q", "origin", "main")
        run(self.root, "fetch", "-q", "origin")
        found = level(self.root, "main")
        items = stranded_item({"checkout": found})
        self.assertEqual(len(items), 1)
        self.assertIn("2 commits", items[0]["text"])
        band = checkout_band({"checkout": found})
        self.assertIn("3 commits behind", band)
        self.assertIn("git switch -C main origin/main", band)
        run(self.root, "push", "-q", "origin", "main:refs/heads/keep-local")
        run(self.origin, "update-ref", "refs/heads/main", run(self.root, "rev-parse", "main"))  # PR merged
        run(self.root, "fetch", "-q", "origin")
        self.assertEqual(stranded_item({"checkout": level(self.root, "main")}), [])


class SaidTest(unittest.TestCase):
    """Two warnings that lived only in a log field nobody drew."""

    def test_a_granted_lines_note_and_withheld_are_in_its_sentence(self) -> None:
        said = harbour_said(entry("granted", harbour=True, fairway="LED", request="merge-L01", what="merge",
                                  commit="abc12345", note="local main has 2 commits the forge's main does not",
                                  withheld="infra/main.tf"))
        self.assertIn("local main has 2 commits", said)
        self.assertIn("still owed by a person: infra/main.tf", said)

    def test_a_refused_landing_is_waiting_on_you_until_it_lands(self) -> None:
        refused = entry("land-refused", harbour=True, branch="triage/0001", why="the full gate failed. Fix it.")
        items = unlanded_item({"unlanded": unlanded([refused])})
        self.assertEqual(len(items), 1)
        self.assertIn("triage/0001 was not landed on trunk", items[0]["text"])
        landed = entry("landed", harbour=True, branch="triage/0001", commit="c0ffee00")
        self.assertEqual(unlanded([refused, landed]), [])


class MigrateTest(Harbour):
    def test_migrate_names_unpushed_commits_with_the_safe_fix_and_moves_nothing(self) -> None:
        run(self.root, "add", "--", RECORD)
        run(self.root, "commit", "-q", "-m", "Triage feedback 0001")
        main = self.head("refs/heads/main")
        name, commits = unpushed(self.root)
        said = "\n".join(section(name, commits))
        self.assertIn("## Local main has commits the forge's main has not got", said)
        self.assertIn("Triage feedback 0001", said)
        self.assertIn("git switch -C main origin/main", said)
        self.assertIn("never resets, rebases or drops", said.replace("nothing here resets", "never resets"))
        self.assertEqual(self.head("refs/heads/main"), main)
        self.assertEqual(section(*unpushed(self.root)) != [], True)
        run(self.root, "push", "-q", "origin", "main")
        run(self.root, "fetch", "-q", "origin")
        self.assertEqual(section(*unpushed(self.root)), [])


if __name__ == "__main__":
    unittest.main()
