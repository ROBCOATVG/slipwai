"""A language somebody spoke brings its own toolchain (#74; brownfield adoption, experimental).

The survey reads each directory once, by the first ecosystem that recognises it, so a directory with a
`package.json` beside a `requirements.txt` is Node and its toolchain says `kind: node`. Saying that the
directory is Python says which of the two builds is the application's — and the first repository taken end to
end kept `kind: node` under `language: python` for ever after, because only the language moved. `kind` is
what CI installs, so the record was describing a pipeline that cannot run.

Both ways of speaking are here: the flag on `adopt`, and `--confirm --language`, which is how `/ground`
records what it read. So is the refresh afterwards, which is where the wrong value used to come back.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import repository, slipwai
from test_candidates import adopted, commit

# A directory that two ecosystems recognise: npm builds the front end, and the service itself is Python.
# The survey reads it as Node, because that is the order the table is tried in, and says so.
BOTH = {
    "package.json": json.dumps({"name": "shop", "scripts": {"lint": "eslint ."}}),
    "svc/package.json": json.dumps({"name": "svc-assets", "scripts": {"lint": "eslint ."}}),
    "svc/requirements.txt": "flask\n",
}


def entry(repo: Path, name: str) -> dict:
    return json.loads((repo / "project.json").read_text())["deployables"][name]


class SpokenToolchainTest(FactoryTestCase):
    def test_the_survey_alone_reads_the_directory_as_node(self) -> None:
        """The premise: without anybody speaking, the record says Node, and that is not a bug."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", BOTH)
            self.assertEqual(slipwai(repo, "adopt", "--yes", "--no-init").returncode, 0)
            self.assertEqual(entry(repo, "svc")["language"], "javascript")
            self.assertEqual(entry(repo, "svc")["toolchain"]["kind"], "node")

    def test_a_language_given_on_the_command_line_brings_its_toolchain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", BOTH)
            result = slipwai(repo, "adopt", "--yes", "--no-init", "--language", "svc=python")
            self.assertEqual(result.returncode, 0, result.stderr)
            svc = entry(repo, "svc")
            self.assertEqual(svc["language"], "python")
            self.assertEqual(svc["toolchain"]["kind"], "python", "what CI installs follows what was said")
            self.assertEqual(svc["toolchain"]["ecosystem"], "python")
            self.assertEqual(svc["provenance"]["toolchain"], "overridden")

    def test_a_confirmed_candidate_takes_the_toolchain_of_the_language_it_was_confirmed_as(self) -> None:
        """How `/ground` speaks: it reads the directory and confirms the candidate under the right language."""
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory), files=BOTH)
            result = slipwai(repo, "adopt", "--confirm", "svc", "--language", "svc=python")
            self.assertEqual(result.returncode, 0, result.stderr)
            svc = entry(repo, "svc")
            self.assertEqual(svc["language"], "python")
            self.assertEqual(svc["toolchain"]["kind"], "python")
            self.assertEqual(svc["provenance"]["toolchain"], "overridden")

    def test_a_refresh_leaves_a_spoken_toolchain_where_it_was(self) -> None:
        """The other half of the same bug: the refresh used to keep only the version, so the next `/survey`
        put `kind: node` back under a language a person had settled."""
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory), files=BOTH)
            self.assertEqual(slipwai(repo, "adopt", "--confirm", "svc", "--language", "svc=python").returncode, 0)
            commit(repo)
            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertEqual(entry(repo, "svc")["toolchain"]["kind"], "python")
            self.assertIn("svc: language was overridden", refreshed.stdout, "and the tree's reading is said")

    def test_a_language_nothing_here_builds_leaves_the_toolchain_alone(self) -> None:
        """No ecosystem for `rust` reads this directory, so there is no toolchain to bring and none is
        invented: the record keeps what was read, and the disagreement is what a later survey reports."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", BOTH)
            result = slipwai(repo, "adopt", "--yes", "--no-init", "--language", "svc=rust")
            self.assertEqual(result.returncode, 0, result.stderr)
            svc = entry(repo, "svc")
            self.assertEqual(svc["language"], "rust")
            self.assertEqual(svc["toolchain"]["kind"], "node", "read, not chosen")
            self.assertNotIn("toolchain", svc["provenance"], "nobody spoke about it")

    def test_a_language_that_changes_nothing_is_not_recorded_as_a_decision_about_the_toolchain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory), files=BOTH)
            self.assertEqual(slipwai(repo, "adopt", "--confirm", "svc", "--language", "svc=javascript").returncode, 0)
            self.assertNotIn("toolchain", entry(repo, "svc")["provenance"])
