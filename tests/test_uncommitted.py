"""`/ground` records its answers one at a time and commits them once (#74; brownfield adoption, experimental).

`adopt --confirm`, the rows in `project.json`, `adopt --refresh`: each refused any uncommitted change, so the
first answer was refused by what `./init` had just left for the person to read, the second by the first, and the
refresh by the rows it exists to follow. The first repository taken end to end committed after every answer to
get through. What is gated here is the sequence working as `/ground` describes it, and the one thing the refusal
is still for: a person's uncommitted change to a file the run is about to write over.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import slipwai
from test_candidates import adopted, record
from test_replay import git


def settle_a_row(repo: Path) -> None:
    """What `/ground` does for a row: edit `project.json` by hand and say who said so."""
    manifest = repo / "project.json"
    document = json.loads(manifest.read_text())
    document["convergence"][0] = {**document["convergence"][0], "provenance": "confirmed"}
    manifest.write_text(json.dumps(document, indent=2) + "\n")


class GroundSequenceTest(FactoryTestCase):
    def test_answers_are_recorded_one_at_a_time_and_committed_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            # What `./init` leaves for the person to read, uncommitted: files of its own and an edit to a shared one.
            (repo / ".specify/integration.json").write_text('{"ai": "claude"}\n')
            with (repo / "AGENTS.md").open("a") as agents:
                agents.write("\n<!-- speckit -->\n")
            for step in (("--confirm", "shop"), ("--decline", "themes"), ("--confirm", "tests-ui")):
                result = slipwai(repo, "adopt", *step)
                self.assertEqual(result.returncode, 0, f"{step}: {result.stderr}")
            settle_a_row(repo)
            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertEqual(sorted(record(repo)["deployables"]), ["shop", "tests-ui"])
            self.assertEqual(record(repo)["convergence"][0]["provenance"], "confirmed", "the row survived the refresh")
            self.assertIn("<!-- speckit -->", (repo / "AGENTS.md").read_text(), "init's writing is left alone")
            self.assertNotEqual(git(repo, "status", "--porcelain").stdout, "", "and all of it is one change to commit")

    def test_a_hand_edit_to_a_file_a_refresh_writes_is_refused_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            self.assertEqual(slipwai(repo, "adopt", "--confirm", "shop").returncode, 0)
            page = repo / "delivery/docs/convergence.md"
            page.write_text(page.read_text() + "\nA note of mine.\n")
            refused = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refused.returncode, 2)
            self.assertIn("`delivery/docs/convergence.md`", refused.stderr)
            self.assertIn("A note of mine.", page.read_text(), "and nothing was written over it")

    def test_what_slipwai_left_is_recognised_as_its_own_even_after_the_record_moves(self) -> None:
        """The regenerated pages from the first answer are no longer what the record renders once a row has
        moved, and that is not somebody's edit: what was left is recorded by digest, not re-derived."""
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            self.assertEqual(slipwai(repo, "adopt", "--confirm", "shop").returncode, 0)
            settle_a_row(repo)
            self.assertEqual(slipwai(repo, "adopt", "--confirm", "themes").returncode, 0)
            self.assertEqual(slipwai(repo, "adopt", "--refresh").returncode, 0)

    def test_answers_are_recorded_one_at_a_time_where_git_is_read_only(self) -> None:
        """Codex runs an agent's commands in a sandbox that makes `.git` read-only. The record of what slipwai
        left was kept there, so it was silently never written, and the second answer was refused as if a
        person had edited the first answer's files. It is kept under `.delivery-tools/` now, already ignored."""
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            dirs = [repo / ".git", *(path for path in (repo / ".git").rglob("*") if path.is_dir())]
            try:
                for path in dirs:
                    os.chmod(path, 0o555)
                for step in (("--confirm", "shop"), ("--decline", "themes"), ("--confirm", "tests-ui")):
                    result = slipwai(repo, "adopt", *step)
                    self.assertEqual(result.returncode, 0, f"{step}: {result.stderr}")
            finally:
                for path in dirs:
                    os.chmod(path, 0o755)
            self.assertTrue((repo / ".delivery-tools/written.json").is_file())
            self.assertNotIn(".delivery-tools", git(repo, "status", "--porcelain").stdout, "it is ignored")
