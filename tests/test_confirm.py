"""`slipwai adopt --confirm` and `--decline`: a candidate becomes an application, or stops being a question.

Split from `test_candidates`, which gates the state itself — what `adopt` records, what the gate does while
nothing is confirmed, and where the sequence says you are. This is the command that settles one: what it
writes, what provenance it carries, what it refuses, and what it leaves alone.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import slipwai
from test_candidates import adopted, commit, record


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

    def test_a_flag_that_describes_the_adoption_is_refused_rather_than_thrown_away(self) -> None:
        """`adopt --confirm shop --integration cursor` looked like it recorded a harness and recorded
        nothing: the flag was read, ignored, and never mentioned. The same rule the reshaped intro already
        applies to flags that describe an application."""
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            result = slipwai(repo, "adopt", "--confirm", "shop", "--integration", "cursor-agent")
            self.assertEqual(result.returncode, 2)
            self.assertIn("--integration", result.stderr)
            self.assertIn("would be read and thrown away", result.stderr)
            self.assertIn("belongs to `./init`", result.stderr)
            self.assertEqual(record(repo)["deployables"], {}, "refused before anything was settled")

    def test_the_flags_a_settling_run_does_take_are_not_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = adopted(Path(directory))
            result = slipwai(
                repo, "adopt", "--confirm", "shop", "--as", "shop=storefront", "--kind", "shop=service",
                "--purpose", "shop=The shop.", "--command", "shop:test=npm test", "--decline", "themes",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("storefront", record(repo)["deployables"])

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
