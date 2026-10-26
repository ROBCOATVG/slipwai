"""The build floor: a row on the map read off the tree, and the steps that move a build up it."""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.convergence import build_row
from slipwai.origin import Adoption
from slipwai.programme import target_steps
from slipwai.services import App


def old(ecosystem: str = "maven", version: str = "17", **commands: str) -> App:
    return App("shop", "web", "service", "java", None, 0, generated=False,
               toolchain={"kind": "java", "ecosystem": ecosystem, "version": version}, commands=commands)


def surveyed(*kinds: str, gate: str | None = "ci.yml") -> Adoption:
    return Adoption(survey={"quickWins": [{"kind": kind} for kind in kinds]}, ci={"gate": gate})


class RowTest(unittest.TestCase):
    def test_each_rung_is_the_lowest_any_build_stands_on(self) -> None:
        self.assertEqual(build_row(surveyed(), [old("ant", "6")])["rung"], "undeclared")
        self.assertEqual(build_row(surveyed("archive-tracked"), [old()])["rung"], "undeclared")
        self.assertEqual(build_row(surveyed(), [old(version="")])["rung"], "declared", "no compile target stated")
        self.assertEqual(build_row(surveyed("no-lockfile"), [old()])["rung"], "declared")
        self.assertEqual(build_row(surveyed("ide-or-build-output-tracked"), [old()])["rung"], "pinned")
        self.assertEqual(build_row(surveyed(gate=None), [old()])["rung"], "pinned", "nothing builds it from clean")
        self.assertEqual(build_row(surveyed(), [old()])["rung"], "reproducible")
        self.assertEqual(build_row(surveyed(), [old(sbom="./mvnw cyclonedx:makeBom")])["rung"], "inventoried")

    def test_an_all_generated_repository_is_at_the_floor_from_day_one(self) -> None:
        self.assertEqual(build_row(surveyed(), [])["rung"], "inventoried")


class TargetTest(unittest.TestCase):
    def test_a_target_no_current_jdk_accepts_names_the_newest_that_still_can(self) -> None:
        said = target_steps(old("ant", "6"), "strangler-fig")
        self.assertEqual(said[0]["kind"], "build")
        self.assertIn("JDK 11 is the newest that still can", said[0]["step"])
        self.assertIn("JDK 8 is the newest", target_steps(old(version="5"), None)[0]["step"])

    def test_a_missing_target_is_a_step_and_a_current_one_is_not(self) -> None:
        self.assertIn("states no compile target", target_steps(old(version=""), None)[0]["step"])
        self.assertEqual(target_steps(old(version="21"), None), [])


if __name__ == "__main__":
    unittest.main()
