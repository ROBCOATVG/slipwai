"""Deciding a strategy on the board: the questions each strategy needs, and the stack a new home is proposed on."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import stack_proposal
from slipwai.stack_proposal import Proposal, proposed
from slipwai.strategy_form import form


def adopted(root: Path, kind: str = "java", **more: object) -> dict:
    (root / "web").mkdir(parents=True, exist_ok=True)
    return {"name": "shop", "deployables": {"shop": {"path": "web", "toolchain": {"kind": kind}}}, **more}


class ProposalTest(unittest.TestCase):
    def test_the_old_language_pages_and_database_make_the_first_answer(self) -> None:
        root = Path(tempfile.mkdtemp())
        document = adopted(root, database={"schema": "unmanaged", "drivers": ["hibernate"]})
        (root / "web/index.jsp").write_text("<html/>")
        (root / "web/lib").mkdir()
        (root / "web/lib/spring-core-3.1.jar").write_bytes(b"")
        with mock.patch.object(stack_proposal, "families", return_value={"java": ["java-quarkus", "java-spring"]}), \
                mock.patch.object(stack_proposal, "CATALOG", {"frontends": {"none": {}, "a-browser-app": {}}}):
            found = proposed(root, document)
        self.assertEqual((found.backend, found.persistence, found.missing), ("java-spring", "postgres", ()))
        self.assertEqual(found.frontend, "a-browser-app", "the catalogue's first browser app")
        self.assertIn("`web` is java, so the new home stays in java", found.because)

    def test_a_language_this_machine_has_no_package_for_is_said_not_swapped(self) -> None:
        root = Path(tempfile.mkdtemp())
        with mock.patch.object(stack_proposal, "families", return_value={"typescript": ["typescript"]}):
            found = proposed(root, adopted(root, kind="python"))
        self.assertEqual((found.backend, found.missing), ("python", ("python",)))

    def test_an_ecosystem_with_no_package_at_all_asks_for_one(self) -> None:
        root = Path(tempfile.mkdtemp())
        found = proposed(root, adopted(root, kind="dotnet"))
        self.assertIsNone(found.backend)
        self.assertIn("pick one", " ".join(found.because))


class FormTest(unittest.TestCase):
    def test_the_recommendation_is_picked_and_each_strategy_asks_only_its_own(self) -> None:
        page = form("in-place")
        self.assertIn('value="in-place" checked', page)
        self.assertIn('data-for="leave-it"', page)
        self.assertIn('name="risk_owner"', page)
        self.assertIn('data-for="strangler-fig rewrite"', page)

    def test_a_rewrite_is_offered_the_strangler_fig_that_reaches_the_same_place(self) -> None:
        page = form("rewrite")
        self.assertIn('id="use-strangler"', page)
        self.assertIn('name="why_cutover"', page)

    def test_the_stack_is_shown_proposed_and_a_missing_package_with_its_command(self) -> None:
        page = form("strangler-fig", Proposal("python", "none", "postgres", ("reason",), ("python",)))
        self.assertIn("slipwai language install python", page)
        self.assertIn('<option value="postgres" selected>', page)


if __name__ == "__main__":
    unittest.main()
