"""Observation ships only with adopted Event Modeling and precedes changes to an unobserved capability."""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.layout import Layout
from slipwai.origin import Adoption
from slipwai.project.ladder import sail_ladder
from slipwai.project.pin_commands import pin_command_files
from slipwai.services import App

DELIVERY = Layout("delivery")
APP = App("orders", "apps/orders", "service", "python", None, 0, generated=False,
          provenance={"kind": "confirmed", "language": "confirmed"})


class ObservationCommandTest(unittest.TestCase):
    def command(self) -> str:
        return pin_command_files([APP], DELIVERY, event=True)["commands/observe.md"]

    def test_the_profile_without_a_model_has_no_observation_command(self) -> None:
        self.assertNotIn("commands/observe.md", pin_command_files([APP], DELIVERY, event=False))

    def test_the_command_requires_capability_source_and_characterisation_before_writing(self) -> None:
        before = self.command().split("## Step 1:")[0]
        for required in ("the whole system", "generated: false", "provenance.kind", "provenance.language",
                         "slipwai adopt --confirm", "/characterise", "actual inputs", "test name"):
            with self.subTest(required=required):
                self.assertIn(required, before)

    def test_each_of_the_nine_steps_is_separate_and_each_fact_has_its_write(self) -> None:
        command = self.command()
        self.assertEqual([line.split(":")[0] for line in command.splitlines() if line.startswith("## Step")],
                         [f"## Step {number}" for number in range(1, 10)])
        for required in ("one block per table", "one row per actual transition", "draft → confirmed",
                         "Write read off", "confirmed `events`", "status columns", "existing events module",
                         "status: observed", "white boxes", "state-view", "retirement.md"):
            with self.subTest(required=required):
                self.assertIn(required, command)

    def test_the_existing_model_does_not_excuse_an_unobserved_capability(self) -> None:
        adopted = sail_ladder(True, [APP], layout=DELIVERY, adoption=Adoption())
        stage = adopted[adopted.index("**Event model**"):adopted.index("**Split**")]
        self.assertIn("some other capability does not satisfy", stage)
        self.assertIn("/observe <capability> <service> <handler>", stage)
        self.assertIn("**before**", stage)
        self.assertIn("delivery/survey/structure.md", stage)
        self.assertNotIn("/observe", sail_ladder(True, [APP], layout=DELIVERY))
        self.assertNotIn("/observe", sail_ladder(False, [APP], layout=DELIVERY, adoption=Adoption()))


if __name__ == "__main__":
    unittest.main()
