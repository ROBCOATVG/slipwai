"""The seed door's Make target: on the durable store, on the event-sourced rung, and nowhere else.

A given is an event a slice's `try-it.json` appends to a log before its first step. A state-stored service keeps
no log, so the languages ship no seed script on that rung — and a target there would be one with nothing behind
it, which Try it would run and report as a broken door rather than as none.
"""
from __future__ import annotations

import unittest
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai.project import makefile
from slipwai.selection import Selection
from slipwai.services import App

DOOR = {"seed": "run seed -- $(FILE)", "install": ""}


def service(write_model: str) -> App:
    selection = Selection({"persistence": "postgres", "write-model": write_model})
    return App("service", "apps/service", "service", "toy", "plain", 3000, selection, first=True)


class SeedTargetTest(unittest.TestCase):
    def targets(self, write_model: str) -> str:
        one = service(write_model)
        with mock.patch.object(makefile, "app_tooling", return_value=DOOR), \
                mock.patch.object(makefile, "install_step", return_value=("", "")):
            return makefile.seed_targets([one], [one])

    def test_an_event_sourced_service_on_the_durable_store_has_its_door(self) -> None:
        self.assertIn("seed-service:", self.targets("events"))

    def test_a_state_stored_service_has_none(self) -> None:
        self.assertEqual(self.targets("state"), "")


if __name__ == "__main__":
    unittest.main()
