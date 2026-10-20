"""The project a harbourmaster runs in. Not a test module, so it asserts nothing itself.

`unittest discover` collects `test_*.py` only, which is why the shared fixture lives here rather than being
inherited across suites — a subclass of a case re-runs every test in it, under a second name.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"


class Fixture(unittest.TestCase):
    """A project laid out the way a generated one is, with the three scripts in it.

    A mixin rather than a base other cases inherit tests from: a subclass of a case re-runs every test in
    it, which costs a second a time and makes a failure appear three times under three names.
    """

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in ("harbourmaster.py", "logs.py", "berths.py", "telegraph.py", "claims.py",
                     "travel.py", "inbox.py"):
            (place / name).write_text((AGENTS / name).read_text(encoding="utf-8"), encoding="utf-8")
        self.script = place / "harbourmaster.py"

    def deck(self, feature: str, fairway: str, *entries: logs.Entry) -> Path:
        path = self.root / logs.deck_path(feature, fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())
        return path

    def run_once(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), "--once", "--no-fetch"],
                              capture_output=True, text=True, cwd=self.root)

    def harbour(self) -> list[logs.Entry]:
        """Every machine's harbour log as one, which is what every reader of it now sees."""
        return logs.harbour_fold(self.root)


class TravelFixture(Fixture):
    """A project with somewhere to push to, which is what makes anything here travel at all.

    A bare repository standing in for the forge, because that is what a forge is as far as a push is
    concerned, and a second clone standing in for a second machine. Nothing reaches a network and nothing
    is pushed anywhere real — `origin` is a directory beside the project.
    """

    def setUp(self) -> None:
        super().setUp()
        self.forge = self.root.parent / f"{self.root.name}.git"
        self.git("init", "--quiet", "--bare", "--initial-branch=main", str(self.forge), where=self.root)
        self.git("init", "--quiet", "--initial-branch=main")
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@local")
        (self.root / ".gitignore").write_text(".slipwai/\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "the skeleton")
        self.git("remote", "add", "origin", str(self.forge))
        self.git("push", "--quiet", "origin", "main")

    def git(self, *argv: str, where: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                              cwd=where or self.root, capture_output=True, text=True, check=False)

    def run_as(self, machine: str, *extra: str) -> subprocess.CompletedProcess:
        """One pass, as a named machine, reaching the forge — which is what `--no-fetch` turns off."""
        return subprocess.run([sys.executable, str(self.script), "--once", *extra],
                              capture_output=True, text=True, cwd=self.root,
                              env={**os.environ, "SLIPWAI_MACHINE": machine})

    def refs(self, namespace: str) -> list[str]:
        found = self.git("for-each-ref", "--format=%(refname)", namespace, where=self.forge)
        return sorted(line.strip() for line in found.stdout.splitlines() if line.strip())

    def carried(self, ref: str) -> str:
        """What a log ref holds, read out of the forge itself rather than out of any clone."""
        listed = self.git("ls-tree", "-r", "--name-only", ref, where=self.forge).stdout.split()
        return self.git("show", f"{ref}:{listed[0]}", where=self.forge).stdout if listed else ""


class MergeFixture(Fixture):
    """A real repository, because a merge is the one thing here that is entirely git.

    No remote: the single-machine case is the one that has to work with no forge at all, and it is also the
    one where moving trunk can disturb somebody's checkout — so it is what the harbourmaster is held to
    here. The repository is left on a branch that is not trunk, which is what a project with berths looks
    like while a captain is working.
    """

    GATE = "verify:\n\t@echo 'verify: all gates passed'\n"

    def setUp(self) -> None:
        super().setUp()
        (self.root / "project.json").write_text(json.dumps({"layout": {"delivery": "."}}), encoding="utf-8")
        (self.root / "harbour.json").write_text(json.dumps({"trunk": "main"}), encoding="utf-8")
        self.git("init", "--quiet", "--initial-branch=main")
        # The repository's own identity, as any repository somebody has committed in has. Without it a
        # rebase that replays a commit cannot write one, and git only guesses from the hostname where the
        # hostname has a domain — so this passed on a laptop and refused every replayed merge in CI.
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@local")
        # As a generated project has it: the logs are a run's own working state and never trunk's history.
        (self.root / ".gitignore").write_text(".slipwai/\n", encoding="utf-8")
        (self.root / "Makefile").write_text(self.GATE, encoding="utf-8")
        (self.root / "service.txt").write_text("one\n", encoding="utf-8")
        self.commit("the skeleton")
        self.trunk_was = self.head()

    def git(self, *argv: str, where: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                              cwd=where or self.root, capture_output=True, text=True, check=False)

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", message)

    def head(self, revision: str = "HEAD") -> str:
        return self.git("rev-parse", revision).stdout.strip()

    def slice_branch(self, slice_id: str, path: str, body: str) -> None:
        """A slice branch with one commit on it, then back to a branch that is not trunk — the state a
        harbour is actually in, where trunk is nobody's checked-out branch."""
        self.git("checkout", "--quiet", "-b", f"slice/{slice_id}", "main")
        (self.root / path).write_text(body, encoding="utf-8")
        self.commit(slice_id)
        self.git("checkout", "--quiet", "-b", "parked-elsewhere", f"slice/{slice_id}")

    def ask(self, slice_id: str, fairway: str = "ORD", t: str = "") -> None:
        entry = logs.entry("request", fairway=fairway, id=f"merge-{slice_id}", what="merge", slice=slice_id,
                           detail=f"merge slice/{slice_id} into trunk after the full gate")
        self.deck("ordering", fairway, replace(entry, t=t) if t else entry)

    def answer(self) -> logs.Entry:
        found = [e for e in self.harbour() if e.kind in ("granted", "refused")]
        self.assertEqual(len(found), 1, [e.fields for e in self.harbour()])
        return found[0]
