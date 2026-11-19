"""`project.json` across a migration: a key order is not a change, and a migration does not stop on one.

The fixture is the shape manda-pir had three migrations running: the factory's last commit holds the manifest
in the order the factory assembles it, the project's copy holds the same answers sorted (a crossing from
version 1 writes it so) with a `releaseMode` of its own, and the replay differs from the base in
`generator.updatedWith` alone. Git sees every line changed by both sides. Shells out to git, so it is in the
Makefile's SLOW list.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import migrate
from slipwai.migration_manifest import merged, ordered_like
from slipwai.replay import Replay
from slipwai.scaffold import FACTORY_IDENTITY

FACTORY = {
    "schema": 2,
    "generator": {"name": "slipwai", "languages": {"typescript": "1.2.1"}, "generatedWith": "1.5.1",
                  "updatedWith": "2.1.0.dev60"},
    "name": "pir", "profile": "event-modelling", "target": "aws", "state": "pre-launch",
    "deployables": {"app": {"kind": "service", "path": "apps/app", "port": 3000,
                            "selection": {"write-model": "events", "persistence": "postgres"}}},
}


def written(document: dict, sort_keys: bool = False) -> str:
    return json.dumps(document, indent=2, sort_keys=sort_keys) + "\n"


def stamped(document: dict, version: str) -> dict:
    return {**document, "generator": {**document["generator"], "updatedWith": version}}


class MergedTest(unittest.TestCase):
    """The merge of three records, with no git anywhere."""

    def setUp(self) -> None:
        self.base = written(FACTORY)
        self.ours = written({**FACTORY, "releaseMode": "dark"}, sort_keys=True)
        self.theirs = written(stamped(FACTORY, "2.1.0.dev66"))

    def test_only_the_stamp_moves_and_the_project_keeps_its_order_and_its_own_key(self) -> None:
        result = merged(self.base, self.ours, self.theirs) or ""
        self.assertEqual(result, self.ours.replace("2.1.0.dev60", "2.1.0.dev66"))
        self.assertEqual(json.loads(result)["releaseMode"], "dark")

    def test_a_key_the_factory_adds_arrives_and_one_the_project_deleted_stays_deleted(self) -> None:
        ours = json.loads(self.ours)
        del ours["target"]
        theirs = {**json.loads(self.theirs), "shape": "liner"}
        result = json.loads(merged(self.base, written(ours), written(theirs)) or "")
        self.assertEqual(result["shape"], "liner")
        self.assertNotIn("target", result)
        self.assertEqual(list(result)[-1], "shape", "what the project has not got follows what it has")

    def test_a_value_both_sides_changed_differently_is_still_a_conflict(self) -> None:
        ours = written({**FACTORY, "state": "launched"})
        theirs = written({**FACTORY, "state": "retired"})
        self.assertIsNone(merged(self.base, ours, theirs))

    def test_a_copy_that_is_not_json_is_left_to_the_person(self) -> None:
        self.assertIsNone(merged(self.base, "<<<<<<< ours\n{}\n", self.theirs))

    def test_the_replay_is_written_in_the_order_the_project_has(self) -> None:
        project = json.loads(self.ours)
        offered = ordered_like(stamped({**FACTORY, "shape": "liner"}, "2.1.0.dev66"), project)
        self.assertEqual(offered, stamped({**FACTORY, "shape": "liner"}, "2.1.0.dev66"), "nothing but order")
        self.assertEqual([key for key in offered if key != "shape"],
                         [key for key in project if key != "releaseMode"])
        self.assertEqual(list(offered["generator"]), sorted(offered["generator"]))


class MigrationTest(unittest.TestCase):
    """`migrate.merge_offered` over a real repository: the merge every ordinary migration makes."""

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name) / "pir"
        self.root.mkdir()
        self.git("init", "--quiet", "--initial-branch=main")
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@local")
        self.commit({"project.json": written(FACTORY), "README.md": "# pir\n\nGenerated.\n"}, factory=True)
        self.base = self.git("rev-parse", "HEAD")

    def git(self, *argv: str, factory: bool = False) -> str:
        return subprocess.run(["git", "-c", "maintenance.auto=false", "-c", "gc.auto=0", *argv], cwd=self.root,
                              capture_output=True, text=True, check=True,
                              env=FACTORY_IDENTITY if factory else None).stdout.strip()

    def commit(self, files: dict[str, str], *, factory: bool = False) -> None:
        for name, text in files.items():
            (self.root / name).write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "t", factory=factory)

    def offer(self, files: dict[str, str]) -> Replay:
        """What a replay leaves in the project's object store: one factory commit on the base, as FETCH_HEAD."""
        self.git("switch", "--quiet", "--detach", self.base)
        self.commit(files, factory=True)
        self.git("branch", "--force", "offered", "HEAD")
        self.git("switch", "--quiet", "main")
        self.git("fetch", "--quiet", ".", "offered")
        return Replay(self.root, self.root, "pir", 2, "1.5.1", self.base, True)

    def test_a_migration_that_moves_only_the_stamp_merges_whatever_order_the_keys_are_in(self) -> None:
        self.commit({"project.json": written({**FACTORY, "releaseMode": "dark"}, sort_keys=True)})
        offered = self.offer({"project.json": written(stamped(FACTORY, "2.1.0.dev66")),
                              "README.md": "# pir\n\nGenerated, by a newer factory.\n"})

        stat, conflicts, fast_forward = migrate.merge_offered(self.root, offered, "Migrate pir")

        self.assertEqual(conflicts, ())
        self.assertFalse(fast_forward)
        self.assertIn("2 files changed", stat or "")
        self.assertEqual(self.git("status", "--porcelain"), "", "the merge is concluded, not left in progress")
        self.assertEqual(len(self.git("rev-list", "--parents", "-1", "HEAD").split()), 3, "one merge commit")
        self.assertEqual(self.git("log", "-1", "--format=%s"), "Migrate pir")
        text = (self.root / "project.json").read_text(encoding="utf-8")
        self.assertEqual(text, written(stamped({**FACTORY, "releaseMode": "dark"}, "2.1.0.dev66"), sort_keys=True))
        self.assertIn("newer factory", (self.root / "README.md").read_text(encoding="utf-8"))

    def test_another_file_in_conflict_is_still_named_and_the_manifest_is_not(self) -> None:
        self.commit({"project.json": written(FACTORY, sort_keys=True), "README.md": "# pir\n\nOurs.\n"})
        offered = self.offer({"project.json": written(stamped(FACTORY, "2.1.0.dev66")),
                              "README.md": "# pir\n\nTheirs.\n"})

        _, conflicts, _ = migrate.merge_offered(self.root, offered, "Migrate pir")

        self.assertEqual(conflicts, ("README.md",))
        self.assertTrue(self.git("rev-parse", "--verify", "MERGE_HEAD"), "the merge is the person's to finish")
        self.assertEqual(json.loads((self.root / "project.json").read_text(encoding="utf-8")),
                         stamped(FACTORY, "2.1.0.dev66"))

    def test_a_real_disagreement_in_the_manifest_is_left_as_git_left_it(self) -> None:
        self.commit({"project.json": written({**FACTORY, "state": "launched"}, sort_keys=True)})
        offered = self.offer({"project.json": written({**FACTORY, "state": "retired"})})

        _, conflicts, _ = migrate.merge_offered(self.root, offered, "Migrate pir")

        self.assertEqual(conflicts, ("project.json",))
        self.assertIn("<<<<<<<", (self.root / "project.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
