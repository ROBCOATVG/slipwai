"""A wrapped application begins as a candidate (ADR 0003), and the gate refuses until one is confirmed.

What is gated here is the distinction the record gained: `deployables` says what somebody has established,
`candidates` says what was merely found, and nothing moves from one to the other without a person or an
agent saying so. The terminal asks the one question a terminal can answer; `verify` refuses rather than
passing over nothing; `--confirm` builds the entry and regenerates everything that reads it; declining
records nothing in its place. `--yes` is the unattended path it has always been, and says nobody looked.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import repository, slipwai
from test_adopt_next import BARE, in_terminal
from test_replay import git

MONOREPO = {
    "package.json": json.dumps({"name": "shop", "scripts": {"lint": "eslint .", "test": "jest"}}),
    "themes/package.json": json.dumps({"name": "themes", "scripts": {"lint": "eslint ."}}),
    "tests-ui/package.json": json.dumps({"name": "ui", "scripts": {"lint": "eslint ."}}),
}


def adopted(parent: Path, name: str = "shop", files: dict | None = None) -> Path:
    """A repository adopted under the reshaped intro, so its directories are candidates and nothing else."""
    repo = repository(parent, name, files or MONOREPO)
    output = in_terminal(repo, "adopt", "--experimental-intro", "--no-init")
    assert (repo / "project.json").is_file(), output
    return repo


def record(repo: Path) -> dict:
    return json.loads((repo / "project.json").read_text())


def commit(repo: Path) -> None:
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "confirmed")


class CandidateRecordTest(FactoryTestCase):
    def test_nothing_is_wrapped_and_everything_found_is_a_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            written = record(repo)
            self.assertEqual(written["deployables"], {})
            self.assertEqual(
                sorted(row["name"] for row in written["candidates"]), ["shop", "tests-ui", "themes"]
            )

    def test_a_candidate_carries_what_confirming_it_needs_and_the_evidence_that_found_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            themes = next(r for r in record(repo)["candidates"] if r["name"] == "themes")
            self.assertEqual(themes["path"], "themes")
            self.assertEqual(themes["language"], "javascript")
            self.assertEqual(themes["evidence"], "themes/package.json")
            self.assertEqual(themes["commands"]["lint"], "cd themes && npm run lint")
            self.assertEqual(themes["kind"], "application", "nothing in the tree says what it is for")

    def test_the_terminal_asks_the_forge_and_nothing_about_any_application(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", MONOREPO)
            output = in_terminal(repo, "adopt", "--experimental-intro", "--no-init")
            self.assertIn("Where does this repository's CI run?", output)
            for asked in ("Wrap it as the application", "What is `", "Keep these commands?", "What does `",
                          "Where is the database schema versioned?", "Why is this work happening?"):
                self.assertNotIn(asked, output, f"{asked!r} needs the code read, so the agent asks it")

    def test_the_survey_is_shown_as_facts_rather_than_asked_about(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", MONOREPO)
            output = in_terminal(repo, "adopt", "--experimental-intro", "--no-init")
            self.assertIn("3 directories that build", output)
            self.assertIn("themes", output)
            self.assertIn("from themes/package.json", output)

    def test_yes_confirms_every_candidate_unlooked_at_and_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", MONOREPO)
            result = slipwai(repo, "adopt", "--yes", "--experimental-intro", "--no-init", environment=BARE)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(record(repo)["deployables"]), 3)
            self.assertNotIn("candidates", record(repo))
            self.assertIn("Nobody has looked at any of these", result.stdout)

    def test_a_describing_flag_is_refused_rather_than_silently_doing_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", MONOREPO)
            result = in_terminal(repo, "adopt", "--experimental-intro", "--no-init", "--kind", "themes=library")
            self.assertIn("--kind describe(s) an application", result)
            self.assertIn("slipwai adopt --confirm", result)


class RefusesBeforeTheWorkTest(FactoryTestCase):
    """A refusal belongs before the work it refuses. `adopt` checked the repository as it began writing,
    which meant surveying the tree and answering the interview first and only then being told that none of
    it could be kept — on a repository of twelve thousand files, with a stray untracked directory."""

    def test_an_unclean_tree_is_refused_before_anything_is_surveyed_or_asked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", MONOREPO)
            (repo / "untracked.txt").write_text("mine\n")
            output = in_terminal(repo, "adopt", "--experimental-intro", "--no-init")
            self.assertIn("uncommitted changes", output)
            self.assertNotIn("directories that build", output, "nothing is shown before the refusal")
            self.assertNotIn("Where does this repository's CI run?", output, "and nothing is asked")

    def test_a_repository_already_adopted_is_refused_the_same_way(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))  # `adopt` commits its own work, so the tree is already clean
            output = in_terminal(repo, "adopt", "--experimental-intro", "--no-init")
            self.assertIn("already has a project.json", output)
            self.assertNotIn("directories that build", output)


class RefusingGateTest(FactoryTestCase):
    def test_verify_refuses_while_nothing_is_confirmed_and_names_what_confirms_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            gate = subprocess.run(
                ["make", "-f", "delivery/Makefile", "verify"], cwd=repo, text=True, capture_output=True,
            )
            self.assertNotEqual(gate.returncode, 0, "a gate with nothing to hold has not been given its subject")
            self.assertIn("nothing is confirmed as an application here", gate.stdout)
            self.assertIn("slipwai adopt --confirm", gate.stdout)

    def test_the_gate_runs_once_a_candidate_is_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            self.assertEqual(slipwai(repo, "adopt", "--confirm", "shop").returncode, 0)
            makefile = (repo / "delivery/Makefile").read_text()
            self.assertIn("verify: $(VERIFY_GATES_FACTORY)", makefile)
            self.assertNotIn("nothing is confirmed as an application here", makefile)


class ConfirmTest(FactoryTestCase):
    def test_confirming_records_the_application_and_regenerates_what_reads_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            result = slipwai(
                repo, "adopt", "--confirm", "shop", "--as", "shop=storefront", "--kind", "shop=service",
                "--purpose", "shop=The shop itself: catalogue, cart and checkout.",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            written = record(repo)
            entry = written["deployables"]["storefront"]
            self.assertEqual(entry["kind"], "service")
            self.assertEqual(entry["purpose"], "The shop itself: catalogue, cart and checkout.")
            self.assertEqual(entry["provenance"]["kind"], "overridden")
            self.assertEqual(entry["provenance"]["commands"], "confirmed", "taken as found, by somebody who looked")
            self.assertNotIn("storefront", [row["name"] for row in written["candidates"]])
            self.assertIn("storefront", (repo / "delivery/Makefile").read_text())

    def test_declining_records_nothing_in_its_place(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            result = slipwai(repo, "adopt", "--confirm", "shop", "--decline", "themes")
            self.assertEqual(result.returncode, 0, result.stderr)
            written = record(repo)
            self.assertNotIn("themes", written["deployables"])
            self.assertEqual([row["name"] for row in written["candidates"]], ["tests-ui"])
            self.assertIn("nothing is recorded in its place", result.stdout)

    def test_the_last_candidate_answered_for_leaves_no_candidates_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            self.assertEqual(
                slipwai(repo, "adopt", "--confirm", "shop", "--decline", "themes", "--decline", "tests-ui",
                        ).returncode, 0
            )
            written = record(repo)
            self.assertNotIn("candidates", written)
            self.assertEqual(list(written["deployables"]), ["shop"])

    def test_declining_every_candidate_is_refused_because_the_method_wraps_applications(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            result = slipwai(
                repo, "adopt", "--decline", "shop", "--decline", "themes", "--decline", "tests-ui"
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("no application at all", result.stderr)

    def test_a_decline_only_run_says_the_gate_still_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            result = slipwai(repo, "adopt", "--decline", "themes")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Nothing is confirmed as an application yet, so the gate still refuses", result.stdout)

    def test_a_candidate_nobody_recorded_is_refused_with_the_ones_there_are(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            result = slipwai(repo, "adopt", "--confirm", "nonsense")
            self.assertEqual(result.returncode, 2)
            self.assertIn("no candidate is named `nonsense`", result.stderr)
            self.assertIn("shop, tests-ui, themes", result.stderr)

    def test_a_description_that_names_no_confirmed_candidate_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            result = slipwai(repo, "adopt", "--confirm", "shop", "--kind", "themes=library")
            self.assertEqual(result.returncode, 2)
            self.assertIn("themes is described by a flag and not among the candidates being confirmed", result.stderr)

    def test_confirming_and_declining_the_same_candidate_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            result = slipwai(repo, "adopt", "--confirm", "shop", "--decline", "shop")
            self.assertEqual(result.returncode, 2)
            self.assertIn("one of them is the answer", result.stderr)

    def test_it_refuses_an_unclean_tree_so_that_what_it_wrote_can_be_undone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            (repo / "stray.txt").write_text("mine\n")
            result = slipwai(repo, "adopt", "--confirm", "shop")
            self.assertEqual(result.returncode, 2)
            self.assertIn("uncommitted changes", result.stderr)

    def test_a_generated_project_has_no_candidates_to_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.generate(Path(directory), "shop")
            result = slipwai(project, "adopt", "--confirm", "anything")
            self.assertEqual(result.returncode, 2)
            self.assertIn("generated, not adopted", result.stderr)

    def test_confirming_twice_says_there_is_nothing_outstanding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            self.assertEqual(
                slipwai(repo, "adopt", "--confirm", "shop", "--decline", "themes", "--decline", "tests-ui",
                        ).returncode, 0
            )
            commit(repo)
            again = slipwai(repo, "adopt", "--confirm", "shop")
            self.assertEqual(again.returncode, 2)
            self.assertIn("no outstanding candidates", again.stderr)


class CandidateSequenceTest(FactoryTestCase):
    def test_next_names_confirming_before_the_rows_and_the_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            out = slipwai(repo, "adopt", "--next").stdout
            self.assertIn("confirm what the survey found", out)
            self.assertIn("3 buildable directories (shop, tests-ui, themes)", out)
            self.assertLess(
                out.index("confirm what the survey found"), out.index("/ground, in the agent"),
                "nothing the map asks can be answered before it is known what the applications are",
            )

    def test_the_step_is_done_once_every_candidate_is_answered_for(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            self.assertEqual(
                slipwai(repo, "adopt", "--confirm", "shop", "--decline", "themes", "--decline", "tests-ui",
                        ).returncode, 0
            )
            out = slipwai(repo, "adopt", "--next").stdout
            self.assertIn("done: confirm what the survey found", out)
            self.assertIn("every buildable directory the survey found has been answered for", out)

    def test_ground_opens_with_the_candidates_and_says_what_to_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            ground = (repo / "delivery/commands/ground.md").read_text()
            self.assertIn("## What is an application here", ground)
            self.assertIn("`themes` at `themes`", ground)
            self.assertIn("slipwai adopt --confirm", ground)
            self.assertLess(
                ground.index("## What is an application here"), ground.index("## The rows, as they stand")
            )

    def test_ground_drops_the_section_once_there_is_nothing_outstanding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            self.assertEqual(
                slipwai(repo, "adopt", "--confirm", "shop", "--decline", "themes", "--decline", "tests-ui",
                        ).returncode, 0
            )
            self.assertNotIn(
                "## What is an application here", (repo / "delivery/commands/ground.md").read_text()
            )

    def test_the_report_names_the_candidates_rather_than_claiming_none_was_found(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", MONOREPO)
            output = in_terminal(repo, "adopt", "--experimental-intro", "--no-init")
            self.assertNotIn("no buildable directory was found", output)
            self.assertIn("none of them recorded as an application yet", output)
            self.assertIn("`verify` refuses rather than passing over nothing", output)
