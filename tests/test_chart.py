"""`check-chart`, run against hand-written charts: one fixture per way a chart can be wrong.

The chart is the one file a captain and a gate both read on either profile, and every rule in the gate is
there because its absence fails quietly. A mark nobody set leaves a slice uncleared with nothing saying on
what. A mark set twice is two schemas for one name, resolved by whichever merged last. A withdrawn mark is
a contract taken from under whoever steered by it. A slice with no capability is never demoed, and a loop
that stops nobody looks exactly like a loop with nothing to show.

So each is written here as a chart that should be refused, beside one that should pass, because a gate
proven only against good input is a gate proven against nothing. The script is run the way a generated
project runs it — a subprocess, from a tree laid out like a project — rather than imported, since that is
the thing a project's `make verify` actually calls.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from test_chart_contexts import decided

from slipwai import toolkit

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "assets/toolkit/scripts/check-chart.py"

WHOLE = """
v: 1
feature: ordering
fairways:
  ORD: {context: ordering, service: apps/orders, owns: [apps/orders/**]}
  BIL: {context: billing, service: apps/billing, owns: [apps/billing/**]}
marks:
  OrderPlaced: {kind: event, schema: contracts/events/OrderPlaced.json}
  InvoiceRaised: {kind: event, schema: contracts/events/InvoiceRaised.json}
slices:
  ORD-01: {fairway: ORD, capability: place-an-order, sets: [OrderPlaced], steers_by: []}
  BIL-01: {fairway: BIL, capability: bill-an-order, sets: [InvoiceRaised], steers_by: [OrderPlaced]}
"""

class ChartGateTest(unittest.TestCase):
    """Each case writes a whole project tree, because the gate reads files the chart names."""

    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(GATE, self.tree / "scripts/check-chart.py")
        (self.tree / "specs/ordering").mkdir(parents=True)
        (self.tree / "contracts/events").mkdir(parents=True)
        for event in ("OrderPlaced", "InvoiceRaised"):
            (self.tree / f"contracts/events/{event}.json").write_text("{}", encoding="utf-8")
        decided(self.tree)

    def run_gate(self, chart: str | None = WHOLE) -> subprocess.CompletedProcess[str]:
        if chart is not None:
            (self.tree / "specs/ordering/chart.yaml").write_text(textwrap.dedent(chart).lstrip(), encoding="utf-8")
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        return subprocess.run([sys.executable, "scripts/check-chart.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False, env=environment)

    def refused_for(self, chart: str, reason: str) -> None:
        done = self.run_gate(chart)
        self.assertEqual(done.returncode, 1, f"the gate passed this chart:\n{done.stdout}")
        self.assertIn(reason, done.stderr)
        self.assertIn("Run: python3 scripts/check-chart.py", done.stderr,
                      "a refusal that does not end on the command that fixes it costs the reader a search")

    def test_a_whole_chart_passes_and_says_what_it_held(self) -> None:
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("2 marks", done.stdout)

    def test_no_chart_at_all_is_not_a_failure(self) -> None:
        """`make verify` runs this everywhere, including a project with no feature in flight."""
        done = self.run_gate(chart=None)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("no chart yet", done.stdout)

    def test_a_mark_whose_contract_is_not_in_the_tree_is_refused(self) -> None:
        """A promise discovered at the far end, by the fairway that believed it."""
        self.refused_for(WHOLE.replace("contracts/events/InvoiceRaised.json",
                                       "contracts/events/NotWrittenYet.json"), "which is not in the tree")

    def test_a_mark_nobody_sets_is_refused(self) -> None:
        """Otherwise the slice waits forever and nothing says on what."""
        self.refused_for(WHOLE.replace("steers_by: [OrderPlaced]", "steers_by: [ShipmentBooked]"),
                         "which no slice sets")

    def test_a_mark_two_slices_set_is_refused(self) -> None:
        """Two schemas for one name, resolved by whichever merged last."""
        self.refused_for(WHOLE.replace("sets: [InvoiceRaised]", "sets: [InvoiceRaised, OrderPlaced]"),
                         "One mark has one setter")

    def test_a_slice_with_no_capability_is_refused(self) -> None:
        """The rule added on 2026-10-07: a slice in no capability is never demoed."""
        self.refused_for(WHOLE.replace("capability: bill-an-order, ", ""), "names no `capability`")

    def test_an_untyped_mark_is_refused_before_the_rules_run(self) -> None:
        self.refused_for(WHOLE.replace("kind: event, schema:", "schema:"), "has no kind")

    def test_a_slice_in_a_fairway_the_chart_has_not_got_is_refused(self) -> None:
        self.refused_for(WHOLE.replace("fairway: BIL,", "fairway: SHP,"), "which the chart has not got")

    def test_a_missing_block_is_one_fault_and_not_five(self) -> None:
        """A malformed chart would otherwise have every rule report the same damage in its own words."""
        done = self.run_gate(WHOLE.replace("marks:", "notmarks:"))
        self.assertEqual(done.returncode, 1)
        self.assertEqual(done.stderr.count("no `marks` block"), 1)
        self.assertNotIn("which no slice sets", done.stderr)


class WholenessTest(unittest.TestCase):
    """What the gate could not tell apart, and now can.

    `/chart` writes the fairways and the marks; the split writes the slices. The gate runs in `make verify`
    between the two, so it cannot simply demand slices — a gate that refuses the state it tells you to be
    in is a gate people learn to skip. The signal is the split's own file: once `story-split.md` is there,
    the second pass is owed.
    """

    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(GATE, self.tree / "scripts/check-chart.py")
        (self.tree / "specs/ordering").mkdir(parents=True)
        (self.tree / "contracts/events").mkdir(parents=True)
        for event in ("OrderPlaced", "InvoiceRaised"):
            (self.tree / f"contracts/events/{event}.json").write_text("{}", encoding="utf-8")
        decided(self.tree)

    def run_gate(self, chart: str) -> subprocess.CompletedProcess[str]:
        (self.tree / "specs/ordering/chart.yaml").write_text(textwrap.dedent(chart).lstrip(), encoding="utf-8")
        return subprocess.run([sys.executable, "scripts/check-chart.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False)

    def split_has_run(self) -> None:
        (self.tree / "specs/ordering/story-split.md").write_text("# split\n", encoding="utf-8")

    def test_pass_one_alone_passes_while_the_split_has_not_run(self) -> None:
        """The state the stage tells you to be in, between its two passes."""
        done = self.run_gate(WHOLE.replace("""slices:
  ORD-01: {fairway: ORD, capability: place-an-order, sets: [OrderPlaced], steers_by: []}
  BIL-01: {fairway: BIL, capability: bill-an-order, sets: [InvoiceRaised], steers_by: [OrderPlaced]}""",
                                          "slices: {}"))
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_once_the_split_has_run_a_chart_with_no_slices_is_refused(self) -> None:
        """This passed green before. The sentence the stage ends on was prose, not a gate."""
        self.split_has_run()
        done = self.run_gate(WHOLE.replace("""slices:
  ORD-01: {fairway: ORD, capability: place-an-order, sets: [OrderPlaced], steers_by: []}
  BIL-01: {fairway: BIL, capability: bill-an-order, sets: [InvoiceRaised], steers_by: [OrderPlaced]}""",
                                          "slices: {}"))
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("the split has run and the chart names no slices", done.stderr)

    def test_a_mark_the_split_dropped_is_refused(self) -> None:
        """A promise pass one made that no slice picked up. Rule 2 from the other side."""
        self.split_has_run()
        done = self.run_gate(WHOLE.replace("sets: [InvoiceRaised]", "sets: []")
                                  .replace("steers_by: [OrderPlaced]", "steers_by: []"))
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("mark `InvoiceRaised` is declared and no slice sets or steers by it", done.stderr)

    def test_a_slice_that_does_not_say_sets_is_refused_once_the_split_has_run(self) -> None:
        """An empty list is an answer; an absent key is not.

        The captain holds a slice to the marks its `sets` names, so a slice that simply left the key out
        would take a demo-only gate by omission — the quietest way there is to pass a gate. On the event
        profile the renderer always writes both keys; on the standard profile the split authors them, and
        this gate read them with `body.get("sets") or []`, under which the two are the same thing.
        """
        self.split_has_run()
        done = self.run_gate(WHOLE.replace(
            "ORD-01: {fairway: ORD, capability: place-an-order, sets: [OrderPlaced], steers_by: []}",
            "ORD-01: {fairway: ORD, capability: place-an-order, sets: [OrderPlaced]}"))
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("slice ORD-01 does not say `steers_by`", done.stderr)
        self.assertIn("gate taken by omission", done.stderr)

    def test_an_empty_list_is_an_answer_and_passes(self) -> None:
        self.split_has_run()
        self.assertEqual(self.run_gate(WHOLE).returncode, 0)

    def test_both_keys_are_only_owed_once_the_split_has_run(self) -> None:
        """Pass one has no slices block to carry them, so demanding them before it is the gate refusing the
        state the stage tells you to be in."""
        done = self.run_gate(WHOLE.replace(
            "ORD-01: {fairway: ORD, capability: place-an-order, sets: [OrderPlaced], steers_by: []}",
            "ORD-01: {fairway: ORD, capability: place-an-order, sets: [OrderPlaced]}"))
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_fairway_that_owns_nothing_is_refused(self) -> None:
        """`owns` is the whole of the boundary check-slice-scope holds, so an empty one protects nothing."""
        done = self.run_gate(WHOLE.replace(", owns: [apps/billing/**]", ""))
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("fairway `BIL` names no `owns`", done.stderr)
        self.assertIn("a fairway no gate protects", done.stderr)


class AdoptedRootTest(unittest.TestCase):
    def test_the_gate_finds_a_chart_in_an_adopted_repository(self) -> None:
        """The method's material sits under `layout.delivery` there, and `specs/` stays at the root. One
        level up from `scripts/` found a directory that does not exist, so the gate reported `no chart yet`
        and exited 0 on every adopted project — green because it was looking in the wrong place."""
        tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tree, True)
        (tree / "delivery/scripts").mkdir(parents=True)
        shutil.copy(GATE, tree / "delivery/scripts/check-chart.py")
        (tree / "project.json").write_text('{"layout": {"delivery": "delivery"}}', encoding="utf-8")
        (tree / "specs/ordering").mkdir(parents=True)
        (tree / "specs/ordering/chart.yaml").write_text(
            textwrap.dedent(WHOLE).lstrip().replace("kind: event, schema: contracts/events/OrderPlaced.json",
                                                    "kind: event, schema: nowhere.json"), encoding="utf-8")
        done = subprocess.run([sys.executable, "delivery/scripts/check-chart.py"], cwd=tree,
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 1, f"the gate did not find the chart: {done.stdout}")
        self.assertIn("nowhere.json", done.stderr)


class FrozenChartTest(unittest.TestCase):
    """The deletion rule needs a trunk to compare against, so this one builds a repository."""

    def test_a_mark_withdrawn_from_the_frozen_chart_is_refused(self) -> None:
        tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tree, True)
        (tree / "scripts").mkdir()
        shutil.copy(GATE, tree / "scripts/check-chart.py")
        (tree / "specs/ordering").mkdir(parents=True)
        (tree / "contracts/events").mkdir(parents=True)
        for event in ("OrderPlaced", "InvoiceRaised"):
            (tree / f"contracts/events/{event}.json").write_text("{}", encoding="utf-8")
        decided(tree)
        chart = tree / "specs/ordering/chart.yaml"
        chart.write_text(textwrap.dedent(WHOLE).lstrip(), encoding="utf-8")

        def git(*arguments: str) -> None:
            subprocess.run(["git", *arguments], cwd=tree, capture_output=True, text=True, check=True)

        git("init", "-q", "-b", "main")
        git("config", "user.email", "gate@example.com")
        git("config", "user.name", "gate")
        git("add", "-A")
        git("commit", "-qm", "the frozen chart")

        # Withdraw a mark and the slice that set it, so nothing else fails first.
        chart.write_text(textwrap.dedent(WHOLE).lstrip()
                         .replace("  InvoiceRaised: {kind: event, schema: contracts/events/InvoiceRaised.json}\n", "")
                         .replace("  BIL-01: {fairway: BIL, capability: bill-an-order, sets: [InvoiceRaised],"
                                  " steers_by: [OrderPlaced]}\n", ""), encoding="utf-8")
        done = subprocess.run([sys.executable, "scripts/check-chart.py"], cwd=tree,
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("was on the frozen chart and is not here now", done.stderr)
        self.assertIn("chart.d/", done.stderr)


class ChartStageTest(unittest.TestCase):
    """`/chart`, the standard profile's answer to what the event model is on the other one."""

    COMMAND = ROOT / "assets/toolkit/commands/chart.md"
    SPLIT = ROOT / "assets/toolkit/skills/story-splitting/SKILL.md"

    def text(self) -> str:
        return " ".join(self.COMMAND.read_text(encoding="utf-8").split())

    def test_it_ships_and_is_documented_on_both_profiles(self) -> None:
        """It ships everywhere and is a rung only where there is no model; a reader of either may open it."""
        self.assertTrue(self.COMMAND.is_file())
        for profile in ("event-modelling", "standard"):
            with self.subTest(profile=profile):
                self.assertEqual(toolkit.toolkit_treatment("commands/chart.md", profile, set()), "copied")

    def test_it_types_all_four_mark_kinds_and_says_what_each_names(self) -> None:
        text = self.text()
        for kind in ("`event`", "`schema`", "`route`", "`port`"):
            with self.subTest(kind=kind):
                self.assertIn(kind, text)
        self.assertIn("a contract a reader cannot open is not a contract", text)

    def test_it_says_a_mark_is_set_once_and_never_moved(self) -> None:
        """Which is why it is a stop with a person rather than a form."""
        text = self.text()
        self.assertIn("set once and never moved", text)
        self.assertIn("fairways/<name>/chart.d/", text)

    def test_the_two_passes_are_named_and_so_is_what_before_the_split_means(self) -> None:
        """The slices do not exist when this stage runs, so the chart is written in two passes."""
        text = self.text()
        self.assertIn("This stage writes `fairways` and `marks`", text)
        self.assertIn("The split writes `slices`", text)
        self.assertIn("no slice is claimed until the whole chart is there", text)

    def test_the_split_fills_in_the_slices_block_and_names_the_capability_as_a_judgement(self) -> None:
        split = " ".join(self.SPLIT.read_text(encoding="utf-8").split())
        self.assertIn("specs/<feature>/chart.yaml`'s `slices` block", split)
        self.assertIn("It is a product judgement, taken here because a person is present", split)
        self.assertIn("One mark has exactly one setter", split)

    def test_the_split_says_the_event_profile_does_not_write_this_block(self) -> None:
        """It is rendered there, and a split that wrote it too would be a second answer."""
        split = " ".join(self.SPLIT.read_text(encoding="utf-8").split())
        self.assertIn("rendered by `make chart` from `model.yaml` and is not written here", split)

    def test_facing_a_person_the_words_are_paired_with_the_ordinary_ones(self) -> None:
        self.assertIn("the slipwai word and the ordinary one", self.text())

    def test_the_stage_works_the_answers_out_before_it_stops_anyone(self) -> None:
        """A blank question spends a person's attention on work a careful reading would have done."""
        text = self.text()
        self.assertIn("Bring a proposal, not a questionnaire", text)
        self.assertIn("Do the whole of pass one yourself before anyone is stopped", text)
        self.assertIn("confirm it or amend it", text)

    def test_every_proposal_carries_what_it_was_read_off(self) -> None:
        """Otherwise it is a conclusion handed down, which a person cannot disagree with."""
        text = self.text()
        self.assertIn("carries what it was read off", text)
        self.assertIn("a guess wearing a conclusion's clothes", text)

    def test_confidence_is_said_per_item_and_before_the_list_is_read(self) -> None:
        """A proposal offered as confidently as every other is confirmed as quickly as every other."""
        self.assertIn("Say which ones you are unsure about, and why, before the person reads the list",
                      self.text())

    def test_where_the_evidence_runs_out_the_question_stays_a_question(self) -> None:
        """A product decision taken by inference is the failure this stage exists to prevent."""
        text = self.text()
        self.assertIn("Genuinely undecidable things stay questions", text)
        self.assertIn("worse than a blank, because a blank gets thought about", text)

    def test_the_service_question_is_asked_rather_than_proposed_where_two_could_hold_it(self) -> None:
        self.assertIn("Where none does, or two could, that is a question and not a proposal", self.text())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
