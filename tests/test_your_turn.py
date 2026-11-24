"""The one next step at the top of the Voyage: a verb, where it stands, and what follows (`your_turn`)."""
from __future__ import annotations

import unittest
from dataclasses import replace

import checkout_packages  # noqa: F401

from slipwai.passage import Stage
from slipwai.your_turn import box, classes, turn


def stage(key: str, state: str, elsewhere: bool = False) -> Stage:
    return Stage(key, key.title(), state, "", "", f"{key} detail", f"What {key} does. And more.", elsewhere)


class TurnTest(unittest.TestCase):
    def test_a_storyboard_waiting_is_its_verdict_and_what_comes_after(self) -> None:
        found = [stage("specification", "done"), stage("storyboard", "waiting"), stage("model", "todo"),
                 stage("chart", "todo")]
        said = turn(found)
        self.assertEqual((said["mode"], said["heading"]), ("you", "Give the storyboard its verdict"))
        self.assertEqual([step["when"] for step in said["then"]],
                         ["Then · Model the feature", "Then · Continue the build"])
        self.assertEqual(said["then"][0]["what"], "What model does.", "the first sentence, not the whole expectation")

    def test_a_held_launch_is_locked_and_an_earlier_feature_s_fleet_still_comes_next(self) -> None:
        found = [stage("model", "done"), stage("chart", "todo"), stage("slices", "waiting", elsewhere=True)]
        said = turn(found, held="the storyboard for 002 has changed")
        self.assertEqual((said["mode"], said["heading"]), ("locked", "Unlock Continue the build"))
        self.assertEqual(said["then"][0]["when"], "Then · Cast off the fleet")
        self.assertIn("Meanwhile, the earlier features' slices", said["line"])

    def test_running_is_said_as_running_with_nothing_to_press(self) -> None:
        said = turn([stage("storyboard", "working")])
        self.assertEqual((said["mode"], said["heading"]), ("running", "Storyboard is running"))

    def test_the_strip_marks_the_stage_the_person_is_on_and_the_earlier_feature_s(self) -> None:
        found = [stage("chart", "todo"), replace(stage("slices", "waiting"), elsewhere=True)]
        self.assertEqual(classes(found), {"chart": "current", "slices": "elsewhere"})
        drawn = box(found, "Now: …", "<button>Go</button>", "")
        self.assertIn('class="turn you" id="turn"', drawn)
        self.assertIn("<h3>Continue the build</h3>", drawn)


if __name__ == "__main__":
    unittest.main()
