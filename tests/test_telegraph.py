"""The telegraph: one lever, eight numbers, and what the clock does with it when nobody is watching.

A run has a dozen numbers that all mean "go slower" in different units. Changing one position to another by
hand is eight edits, and anybody doing it in a hurry gets some of them.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import cli_telegraph, logs, telegraph
from slipwai.assets import TOOLKIT_ROOT
from slipwai.cli_telegraph import ring, set_one, shown
from slipwai.project.harbour import START, harbour_config

AGENTS = TOOLKIT_ROOT / "scripts/agents"


class TableTest(unittest.TestCase):
    def test_the_positions_are_in_the_order_the_fires_are_banked(self) -> None:
        self.assertEqual(telegraph.POSITIONS[0], "full-ahead")
        self.assertEqual(telegraph.POSITIONS[-1], "stop")

    def test_every_position_sets_every_number(self) -> None:
        """A position that left one out would be a lever that half-works, which is worse than no lever."""
        for name in telegraph.POSITIONS:
            with self.subTest(name=name):
                self.assertEqual(sorted(telegraph.settings(name)), sorted(telegraph.NUMBERS))

    def test_each_notch_spends_no_more_than_the_one_above_it(self) -> None:
        for faster, slower in zip(telegraph.POSITIONS, telegraph.POSITIONS[1:], strict=False):
            with self.subTest(step=f"{faster}->{slower}"):
                for number in ("boilers", "fanout", "bunker_per_slice", "bunker_per_day", "stage_scale",
                               "browsers"):
                    self.assertLessEqual(float(telegraph.settings(slower)[number]),  # type: ignore[arg-type]
                                         float(telegraph.settings(faster)[number]))  # type: ignore[arg-type]

    def test_stop_spends_nothing(self) -> None:
        self.assertEqual(telegraph.settings("stop")["boilers"], 0)
        self.assertEqual(telegraph.settings("stop")["browsers"], 0)

    def test_browser_runs_are_bounded_separately_from_delegates(self) -> None:
        """Several worktrees are still one machine's CPU, and a delegate that is not in a browser costs nothing
        here — so the bound is its own number, and never wider than the berths that could be lit."""
        for name in telegraph.POSITIONS:
            with self.subTest(name=name):
                held = telegraph.settings(name)
                self.assertLessEqual(int(held["browsers"]), max(1, int(held["boilers"])))  # type: ignore[call-overload]
        self.assertEqual(telegraph.settings("stop")["bunker_per_day"], 0)

    def test_slower_steps_one_notch_and_stops_at_stop(self) -> None:
        """One notch, because a run that stops dead loses what is in flight."""
        self.assertEqual(telegraph.slower("full-ahead"), "half-ahead")
        self.assertIsNone(telegraph.slower("stop"))

    def test_a_position_that_is_not_one_is_refused_with_the_list(self) -> None:
        with self.assertRaises(telegraph.Refused) as refused:
            telegraph.position("flank")
        self.assertIn("full-ahead", str(refused.exception))

    def test_a_fresh_harbour_reads_as_its_position_and_not_as_adjusted(self) -> None:
        """A board reporting a position its numbers do not match is a board that is lying."""
        held = json.loads(harbour_config())
        self.assertEqual(held["position"], START)
        self.assertFalse(telegraph.adjusted(START, held))

    def test_a_changed_number_reads_as_adjusted_and_not_as_another_position(self) -> None:
        held = {**telegraph.settings("half-ahead"), "boilers": 1}
        self.assertEqual(telegraph.described("half-ahead", held), "half-ahead, adjusted")


class SettingTest(unittest.TestCase):
    def test_a_name_the_telegraph_does_not_set_is_refused_with_what_it_does(self) -> None:
        with self.assertRaises(telegraph.Refused) as refused:
            telegraph.parse_setting("speed=9")
        self.assertIn("boilers", str(refused.exception))

    def test_a_value_that_is_not_a_number_says_what_the_name_means(self) -> None:
        with self.assertRaises(telegraph.Refused) as refused:
            telegraph.parse_setting("boilers=lots")
        self.assertIn("berths lit", str(refused.exception))

    def test_the_bar_is_a_word_and_is_taken_as_one(self) -> None:
        self.assertEqual(telegraph.parse_setting("bar=high"), ("bar", "HIGH"))


class FairwayOrderSettingTest(unittest.TestCase):
    """Slice 18.2. Which stream goes first is a priority a person has while a run is going, so it is set
    the way every other number under the lever is — and it is a list of names, which no other is."""

    def test_the_names_are_taken_as_a_list_in_the_order_they_were_typed(self) -> None:
        self.assertEqual(telegraph.parse_setting("fairways=billing,ordering"),
                         ("fairways", ["billing", "ordering"]))

    def test_spaces_around_the_commas_are_a_persons_typing_and_not_a_refusal(self) -> None:
        self.assertEqual(telegraph.parse_setting("fairways=billing, ordering")[1], ["billing", "ordering"])

    def test_none_clears_it_so_a_priority_can_be_put_back(self) -> None:
        """A setting that can be set and not unset is a trap: the chart's own order has to be reachable."""
        self.assertEqual(telegraph.parse_setting("fairways=none"), ("fairways", []))

    def test_it_is_not_a_number_and_says_so_rather_than_failing_as_one(self) -> None:
        with self.assertRaises(telegraph.Refused) as refusal:
            telegraph.parse_setting("fairways=2")
        self.assertIn("name", str(refusal.exception).lower())

    def test_a_name_the_chart_has_not_got_is_refused_while_the_person_is_still_here(self) -> None:
        """Two moments, two answers. Here a person has just typed it, so a typo that quietly did nothing
        would be the worst outcome and it is refused. At read time the fleet ignores an unknown name
        instead, because the chart moves under a setting that outlives it and a stale name must never park
        a run."""
        self.assertEqual(cli_telegraph.not_on_the_chart(["ordering", "billing"], ["billing"]), [])
        self.assertEqual(cli_telegraph.not_on_the_chart(["ordering", "billing"], ["billign"]), ["billign"])

    def test_a_project_with_no_readable_chart_refuses_nothing(self) -> None:
        """Before the chart stage there is nothing to check against, and a priority set then is a person
        saying what they want first — not a mistake."""
        self.assertEqual(cli_telegraph.not_on_the_chart([], ["billing"]), [])

    def test_no_position_rings_it_because_pace_and_priority_are_different_questions(self) -> None:
        """Ringing resets every number, which is what makes a hurried `--set` safe. It must not also throw
        away which stream somebody put first — slowing a run down is not saying the order was wrong."""
        for position in telegraph.POSITIONS:
            with self.subTest(position=position):
                self.assertNotIn("fairways", telegraph.settings(position))
        kept = telegraph.applied("stop", {"fairways": ["billing"]})
        self.assertEqual(kept["fairways"], ["billing"])


class FileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")

    def held(self) -> dict:
        return json.loads((self.root / "harbour.json").read_text(encoding="utf-8"))

    def test_ringing_sets_every_number_together(self) -> None:
        ring(self.root, "dead-slow")
        held = self.held()
        self.assertEqual(held["position"], "dead-slow")
        self.assertFalse(telegraph.adjusted("dead-slow", held))

    def test_ringing_scales_the_stage_budgets_with_it(self) -> None:
        before = self.held()["stages"]["implement-shipwright"]["minutes"]
        ring(self.root, "dead-slow")
        self.assertLess(self.held()["stages"]["implement-shipwright"]["minutes"], before)

    def test_no_stage_budget_ever_scales_to_nothing(self) -> None:
        """Zero is a budget no stage can meet, which reads as every stage failing rather than as `stop`."""
        ring(self.root, "stop")
        for stage, row in self.held()["stages"].items():
            with self.subTest(stage=stage):
                self.assertGreaterEqual(row["minutes"], 1)

    def test_setting_one_leaves_the_others_and_says_how_to_put_it_back(self) -> None:
        ring(self.root, "slow-ahead")
        said = set_one(self.root, ["boilers=1"])
        held = self.held()
        self.assertEqual(held["boilers"], 1)
        self.assertEqual(held["fanout"], telegraph.settings("slow-ahead")["fanout"])
        self.assertIn("slow-ahead, adjusted", said[0])
        self.assertIn("telegraph slow-ahead", said[-1])

    def test_a_fairway_order_is_written_where_the_fleet_reads_it(self) -> None:
        said = set_one(self.root, ["fairways=billing,ordering"])
        self.assertEqual(self.held()["fairways"], ["billing", "ordering"])
        self.assertIn("billing", said[1])
        set_one(self.root, ["fairways=none"])
        self.assertEqual(self.held()["fairways"], [])

    def test_ringing_again_resets_an_adjusted_number(self) -> None:
        """Which is what makes a hurried `--set` safe: there is one action that puts everything back."""
        set_one(self.root, ["boilers=1"])
        ring(self.root, START)
        self.assertFalse(telegraph.adjusted(START, self.held()))

    def test_a_width_that_belongs_to_drive_is_written_where_drive_reads_it(self) -> None:
        (self.root / ".specify").mkdir()
        (self.root / ".specify/sail.json").write_text(json.dumps({"delegate": "task"}), encoding="utf-8")
        set_one(self.root, ["delegate=rule"])
        self.assertEqual(json.loads((self.root / ".specify/sail.json").read_text())["delegate"], "rule")
        self.assertNotIn("delegate", self.held())

    def test_the_two_mirrored_settings_take_their_own_words_and_not_numbers(self) -> None:
        """They were described here as numbers and parsed as numbers, so the only values either takes were
        both refused and a meaningless number was accepted. `delegate` is how much of a slice one delegate
        is handed; `cycle` is how many failing tests one RED-GREEN-REFACTOR cycle opens with."""
        for pair in ("delegate=story", "delegate=rule", "delegate=task", "cycle=rule", "cycle=example"):
            with self.subTest(pair=pair):
                name, value = telegraph.parse_setting(pair)
                self.assertEqual(f"{name}={value}", pair)
        for pair in ("delegate=2", "cycle=3", "cycle=story"):
            with self.subTest(pair=pair), self.assertRaises(telegraph.Refused):
                telegraph.parse_setting(pair)

    def test_the_mirrored_values_are_the_ones_drive_itself_takes(self) -> None:
        """A project has no slipwai to import, so `scripts/agents/sail.py` has its own copy of these sets
        and this is the second. Held as an equality rather than left to drift, which is what put a count in
        the description of a setting whose values are words."""
        source = (pathlib.Path(__file__).resolve().parents[1]
                  / "assets/toolkit/scripts/agents/sail.py").read_text(encoding="utf-8")
        for name, key in (("delegate", "DELEGATES"), ("cycle", "CYCLES")):
            with self.subTest(name=name):
                found = re.search(key + r" = \{(.*?)\n\}", source, re.S)
                if found is None:
                    self.fail(f"sail.py no longer declares {key} as a literal mapping")
                self.assertEqual(tuple(re.findall(r'^\s*"([^"]+)":', found.group(1), re.M)),
                                 telegraph.MIRRORED[name][1])

    def test_showing_names_what_every_number_means(self) -> None:
        said = "\n".join(shown(self.held()))
        for number in telegraph.NUMBERS:
            self.assertIn(number, said)


class BankingTest(unittest.TestCase):
    """The same lever, pulled by the clock. The harbourmaster runs it, so it runs as a project runs it."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in ("harbourmaster.py", "logs.py", "berths.py", "telegraph.py", "claims.py", "travel.py"):
            (place / name).write_text((AGENTS / name).read_text(encoding="utf-8"), encoding="utf-8")
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")
        self.script = place / "harbourmaster.py"

    def run_once(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), "--once", "--no-fetch"],
                              capture_output=True, text=True, cwd=self.root)

    def spend(self, thousands: int) -> None:
        path = self.root / logs.deck_path("ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(logs.entry("heartbeat", fairway="ORD", tokens=thousands).line())

    def harbour(self) -> list[logs.Entry]:
        return logs.harbour_fold(self.root)

    def position(self) -> str:
        return json.loads((self.root / "harbour.json").read_text(encoding="utf-8"))["position"]

    def test_a_day_inside_its_bunker_banks_nothing(self) -> None:
        self.spend(10)
        self.run_once()
        self.assertEqual([e for e in self.harbour() if e.kind == "fires-banked"], [])
        self.assertEqual(self.position(), START)

    def test_a_spent_bunker_steps_the_position_down_one_notch_and_says_why(self) -> None:
        self.spend(999_999)
        self.run_once()
        banked = [e for e in self.harbour() if e.kind == "fires-banked"]
        self.assertEqual(len(banked), 1)
        self.assertEqual(banked[0].fields["step"], telegraph.slower(START))
        self.assertIn("bunker", str(banked[0].fields["why"]))
        self.assertEqual(self.position(), telegraph.slower(START))

    def test_it_never_goes_straight_to_stop(self) -> None:
        """A run that stops dead at the end of the day loses whatever was in flight."""
        self.spend(999_999)
        self.run_once()
        self.assertNotEqual(self.position(), "stop")

    def test_a_person_ringing_it_is_told_to_the_captains_once(self) -> None:
        ring(self.root, "dead-slow")
        self.run_once()
        self.run_once()
        rung = [e for e in self.harbour() if e.kind == "telegraph"]
        self.assertEqual(len(rung), 1)
        self.assertEqual(rung[0].fields["position"], "dead-slow")


if __name__ == "__main__":
    unittest.main()
