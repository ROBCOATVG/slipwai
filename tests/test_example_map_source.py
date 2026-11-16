"""Where a slice's example map is read from: its `slice/<id>` branch in flight, trunk once merged.

Each case stands up a small repository, so this module is in the Makefile's `SLOW`.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from slipwai import example_map_source
from slipwai.example_map_source import card_line, found_map
from slipwai.live_page import window, window_payload

FOLDER = "specs/001-demo/slices/S01"
MAPPED = ("## Story\nA thing.\n\n## R1 — It holds\n\n### Scenario: It holds (S01-1)\n"
          "**Given** a · **When** b · **Then** c\n")


class SourceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        for held in (example_map_source.SEEN, example_map_source.FOLDERS, example_map_source.DONE,
                     example_map_source.FLIGHT):
            held.clear()
        self.git("init", "-q", "-b", "main")
        (self.root / "README.md").write_text("x\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "scaffold")

    def git(self, *argv: str) -> None:
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv], cwd=self.root,
                       check=True, capture_output=True)

    def on_branch(self, text: str, proof: str = "") -> None:
        self.git("checkout", "-q", "-B", "slice/S01")
        (self.root / FOLDER).mkdir(parents=True, exist_ok=True)
        (self.root / FOLDER / "examples.md").write_text(text, encoding="utf-8")
        if proof:
            (self.root / FOLDER / "tasks.md").write_text(proof, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "S01: examples")
        self.git("checkout", "-q", "main")

    def test_a_slice_in_flight_is_read_off_its_branch(self) -> None:
        self.on_branch(MAPPED, "## Examples proven\n| S01-1 | `a.test.ts` |\n")
        self.assertFalse((self.root / FOLDER).exists(), "trunk has nothing yet")
        found = found_map(self.root, "S01")
        assert found is not None
        self.assertEqual(([one.id for one in found.examples], found.examples[0].proven), (["S01-1"], True))
        self.assertEqual(card_line(self.root, "001-demo", "S01"), "1 rule · 1 example · no questions open")

    def test_a_merged_slice_is_read_from_trunk_s_working_tree(self) -> None:
        self.on_branch(MAPPED)
        self.git("merge", "-q", "--no-ff", "-m", "merge S01", "slice/S01")
        (self.root / FOLDER / "examples.md").write_text(MAPPED + "## R2 — Edited on trunk\n", encoding="utf-8")
        found = found_map(self.root, "S01")
        assert found is not None
        self.assertEqual([rule.id for rule in found.rules], ["R1", "R2"])

    def test_a_slice_with_no_examples_file_has_no_map(self) -> None:
        self.assertIsNone(found_map(self.root, "S01"))
        self.assertEqual(card_line(self.root, "001-demo", "S01"), "")
        self.assertIsNone(found_map(self.root, "../S01"), "a slice id is never a path")

    def test_a_poll_with_the_branch_where_it_was_reads_nothing_again(self) -> None:
        self.on_branch(MAPPED)
        first = found_map(self.root, "S01")
        with mock.patch.object(example_map_source, "read", side_effect=AssertionError("read again")):
            self.assertIs(found_map(self.root, "S01"), first)
        self.on_branch(MAPPED + "## R2 — Another\n")
        moved = found_map(self.root, "S01")
        assert moved is not None
        self.assertEqual(len(moved.rules), 2, "a moved branch is read again")

    def test_the_window_draws_both_tabs_and_its_payload_carries_the_map(self) -> None:
        self.on_branch(MAPPED)
        page = window(self.root, "F", "S01")
        self.assertIn('<section data-panel="where">', page)
        self.assertIn('<section data-panel="map" hidden><div id="slice-map"', page)
        self.assertIn("<b>R1 · </b>It holds", page)
        payload = json.loads(window_payload(self.root, "F", "S01"))
        self.assertTrue(payload["map_said"])
        self.assertIn('id="slice-map"', payload["map_html"])
        self.assertIn('id="slice-live"', payload["html"])

    def head(self) -> str:
        return subprocess.run(["git", "rev-parse", "slice/S01"], cwd=self.root, capture_output=True, text=True,
                              check=True).stdout.strip()

    def spawns(self) -> Any:
        return mock.patch.object(example_map_source, "git", wraps=example_map_source.git)

    def test_the_card_reads_with_the_head_the_board_already_has_and_spawns_nothing_more(self) -> None:
        self.on_branch(MAPPED)
        head = self.head()
        card_line(self.root, "001-demo", "S01", head)
        with self.spawns() as spawned:
            self.assertEqual(card_line(self.root, "001-demo", "S01", head), "1 rule · 1 example · no questions open")
        self.assertEqual(spawned.call_count, 0)

    def test_a_done_slice_spawns_nothing_at_all(self) -> None:
        self.on_branch(MAPPED)
        self.git("merge", "-q", "--no-ff", "-m", "merge S01", "slice/S01")
        with self.spawns() as spawned:
            self.assertEqual(card_line(self.root, "001-demo", "S01", done=True),
                             "1 rule · 1 example · no questions open")
            card_line(self.root, "001-demo", "S01", done=True)
        self.assertEqual(spawned.call_count, 0)

    def test_the_card_then_the_window_share_one_read(self) -> None:
        self.on_branch(MAPPED)
        first = found_map(self.root, "S01", "001-demo", self.head())
        with mock.patch.object(example_map_source, "read", side_effect=AssertionError("read again")), \
                self.spawns() as spawned:
            self.assertIs(found_map(self.root, "S01"), first)
            self.assertIs(found_map(self.root, "S01", "001-demo", self.head()), first)
        self.assertEqual(spawned.call_count, 1, "the window's one rev-parse, and nothing for the card")

    def test_a_done_slice_whose_branch_was_rebased_as_it_merged_is_read_from_trunk(self) -> None:
        self.on_branch(MAPPED)
        (self.root / FOLDER).mkdir(parents=True)
        (self.root / FOLDER / "examples.md").write_text(MAPPED + "## R2 — Landed on trunk\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "S01 rebased onto trunk")
        self.assertEqual(card_line(self.root, "001-demo", "S01", done=True), "2 rules · 1 example · no questions open")
        found = found_map(self.root, "S01")
        assert found is not None
        self.assertEqual(len(found.rules), 2, "its window reads trunk too, though the branch is no ancestor")

    def test_a_card_in_flight_is_drawn_with_the_head_its_rung_already_read_and_then_asks_git_nothing(self) -> None:
        from slipwai.slice_rungs import rung

        self.on_branch(MAPPED)
        self.assertEqual(rung(self.root, "001-demo", "S01", [])["examples"], "1 rule · 1 example · no questions open",
                         "read off the branch: trunk has no examples yet")
        with self.spawns() as spawned:
            rung(self.root, "001-demo", "S01", [])
        self.assertEqual(spawned.call_count, 0, "a poll with the branch where it was spawns nothing for the map")

    def test_a_done_slice_s_row_is_folded_without_asking_git_where_its_map_is(self) -> None:
        from types import SimpleNamespace

        from slipwai import voyage

        self.on_branch(MAPPED)
        self.git("merge", "-q", "--no-ff", "-m", "merge S01", "slice/S01")
        owner = SimpleNamespace(name="ORD", claimed=set(), merged={"S01"}, entries=[])
        asked = ("001-demo", {"states": {"S01": {"state": "done", "why": ""}}}, "")
        with mock.patch.object(voyage, "clearance_query", return_value=asked), \
                mock.patch.object(voyage, "fairways", return_value=([owner], None)), self.spawns() as spawned:
            rows, _ = voyage.folded(self.root)
        self.assertEqual([(row["slice"], row["state"], row["examples"]) for row in rows],
                         [("S01", "done", "1 rule · 1 example · no questions open")])
        self.assertEqual(spawned.call_count, 0, "the board said it merged, so nothing asks git")

    def test_the_window_reads_a_moved_branch_from_the_folder_the_card_named_without_listing_it(self) -> None:
        self.on_branch(MAPPED)
        found_map(self.root, "S01", "001-demo", self.head())
        self.on_branch(MAPPED + "## R2 — Another\n")
        with self.spawns() as spawned:
            moved = found_map(self.root, "S01")
        assert moved is not None
        self.assertEqual(len(moved.rules), 2)
        self.assertNotIn("ls-tree", [call.args[1] for call in spawned.call_args_list])

    def test_the_payload_s_signature_moves_only_when_the_map_does(self) -> None:
        self.on_branch(MAPPED)
        self.git("merge", "-q", "--no-ff", "-m", "merge S01", "slice/S01")
        said = [json.loads(window_payload(self.root, "F", "S01"))["map_said"] for _ in range(2)]
        page = self.root / FOLDER / "examples.md"
        page.write_text(MAPPED + "## R2 — Another\n", encoding="utf-8")
        said.append(json.loads(window_payload(self.root, "F", "S01"))["map_said"])
        page.write_text(MAPPED + "## R2 — Another\n", encoding="utf-8")
        said.append(json.loads(window_payload(self.root, "F", "S01"))["map_said"])
        self.assertEqual((said[0] == said[1], said[1] == said[2], said[2] == said[3]), (True, False, True),
                         "a file written again with the same words is the same map")


if __name__ == "__main__":
    unittest.main()
