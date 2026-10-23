"""The voyage's adoption card: the sequence `adopt --next` reads, for a repository that was adopted."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import adoption_card as card
from slipwai.next_steps import Step


class AdoptionCardTest(unittest.TestCase):
    def test_a_generated_project_has_no_card(self) -> None:
        root = Path(tempfile.mkdtemp())
        self.assertEqual(card.adoption_card(root), "")
        (root / "project.json").write_text(json.dumps({"name": "made"}))
        with mock.patch.object(card, "adoption_of", return_value=None):
            self.assertEqual(card.adoption_card(root), "")

    def test_the_first_step_not_done_is_the_one_to_do_now(self) -> None:
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text(json.dumps({"name": "kept"}))
        said = [Step("./adopt/init", "installs", True), Step("/ground, in the agent", "asks", False),
                Step("/verify", "the gate", False)]
        with mock.patch.object(card, "read_manifest", return_value={}), \
                mock.patch.object(card, "adoption_of", return_value=object()), \
                mock.patch.object(card, "layout_of"), mock.patch.object(card, "apps_from_manifest"), \
                mock.patch.object(card.next_steps, "steps", return_value=said):
            page = card.adoption_card(root)
        self.assertIn('<li class="done"><b>done</b> ./adopt/init', page)
        self.assertIn('<li class="now"><b>now</b> /ground, in the agent', page)
        self.assertIn('<li class="then"><b>then</b> /verify', page)

    def test_from_the_first_specification_the_strip_takes_over(self) -> None:
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text(json.dumps({"name": "kept"}))
        said = [Step("/speckit-specify, in the agent", "the first feature", True),
                Step("/sail, in the agent", "", False)]
        with mock.patch.object(card, "read_manifest", return_value={}), \
                mock.patch.object(card, "adoption_of", return_value=object()), \
                mock.patch.object(card, "layout_of"), mock.patch.object(card, "apps_from_manifest"), \
                mock.patch.object(card.next_steps, "steps", return_value=said):
            self.assertEqual(card.adoption_card(root), "")


if __name__ == "__main__":
    unittest.main()
