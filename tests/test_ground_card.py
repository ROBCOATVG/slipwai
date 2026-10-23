"""`/ground` on the board: one row at a time, each answer written where the record keeps it."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import ground_card
from slipwai.convergence import AXES
from slipwai.errors import GenerationError


def adopted(**more: object) -> dict:
    return {"name": "kept", "origin": "adopted", "profile": "standard", "frontend": "none", "target": "existing",
            "deployables": {}, "layout": {"delivery": "adopt"},
            "convergence": [{"axis": axis.key, "rung": axis.rungs[0], "target": axis.target,
                             "evidence": "read", "provenance": "unrecorded"} for axis in AXES], **more}


class GroundTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        for patched in (mock.patch.object(ground_card, "refuse_foreign"),
                        mock.patch.object(ground_card.resurvey, "writes", return_value=set()),
                        mock.patch.object(ground_card.resurvey, "refresh",
                                          return_value=SimpleNamespace(rewritten=["adopt/docs/convergence.md"]))):
            patched.start()
            self.addCleanup(patched.stop)
        git = mock.patch.object(ground_card.subprocess, "run")
        self.git = git.start()
        self.addCleanup(git.stop)
        self.write(adopted())

    def write(self, document: dict) -> None:
        (self.root / "project.json").write_text(json.dumps(document))

    def document(self) -> dict:
        return json.loads((self.root / "project.json").read_text())

    def row(self, axis: str) -> dict:
        return next(row for row in self.document()["convergence"] if row["axis"] == axis)

    def now(self) -> str:
        asked = ground_card.asked(self.document())
        return asked.axis.key if asked else ""

    def answer(self, axis: str, answer: str, **more: str) -> list[str]:
        return ground_card.record(self.root, {"axis": axis, "answer": answer, **more}, today="2026-10-23")

    def test_the_first_row_nobody_answered_is_the_one_asked(self) -> None:
        self.assertEqual(self.now(), AXES[0].key)
        self.assertIn("I don't know", ground_card.card(self.root))

    def test_a_rung_is_recorded_in_the_persons_words_and_committed_with_what_it_rewrote(self) -> None:
        paths = self.answer("integration", "trunk", evidence="every branch is merged the same day")
        row = self.row("integration")
        self.assertEqual((row["rung"], row["provenance"], row["evidence"]),
                         ("trunk", "confirmed", "every branch is merged the same day"))
        self.assertEqual(paths, ["adopt/docs/convergence.md", "project.json"])
        added = self.git.call_args_list[0].args[0]
        self.assertEqual(added, ["git", "add", "--", "adopt/docs/convergence.md", "project.json"])

    def test_the_path_to_production_writes_the_release_path_the_gate_caps_it_by(self) -> None:
        self.answer("path-to-production", "one-path")
        self.assertEqual(self.document()["release"]["path"], "pipeline")
        self.answer("path-to-production", "scripted")
        self.assertEqual(self.document()["release"]["path"], "scripted")

    def test_a_home_elsewhere_names_its_repository(self) -> None:
        with self.assertRaises(GenerationError):
            self.answer("data", "elsewhere")
        self.answer("data", "elsewhere", repository="github.com/shop/schema")
        self.assertEqual(self.document()["database"],
                         {"schema": "elsewhere", "repository": "github.com/shop/schema", "provenance": "confirmed"})
        self.assertEqual(self.row("data")["rung"], "settled")

    def test_i_dont_know_leaves_the_row_unrecorded_and_moves_on(self) -> None:
        self.answer(AXES[0].key, ground_card.UNKNOWN)
        row = self.row(AXES[0].key)
        self.assertEqual((row["provenance"], row["asked"]), ("unrecorded", "2026-10-23"))
        self.assertEqual(self.now(), AXES[1].key)

    def test_a_row_the_tree_reads_is_only_asked_never_held(self) -> None:
        """Confirmed, the constitution would stand at `template` after `/speckit-constitution` ratified it."""
        self.answer("constitution", ground_card.AS_READ)
        self.assertEqual(self.row("constitution")["provenance"], "unrecorded")
        self.assertEqual(self.row("constitution")["asked"], "2026-10-23")

    def test_why_is_the_strategy_rows_fact(self) -> None:
        with self.assertRaises(GenerationError):
            self.answer("strategy", "why")
        self.answer("strategy", "why", evidence="the platform is out of support")
        self.assertEqual(self.document()["why"], "the platform is out of support")

    def test_an_answer_not_on_offer_writes_nothing(self) -> None:
        before = self.document()
        with self.assertRaises(GenerationError):
            self.answer("integration", "nightly")
        self.assertEqual(self.document(), before)

    def test_every_row_answered_says_so(self) -> None:
        self.write(adopted(convergence=[{"axis": axis.key, "rung": axis.rungs[0], "provenance": "unrecorded",
                                         "asked": "2026-10-23"} for axis in AXES]))
        self.assertIsNone(ground_card.asked(self.document()))
        self.assertIn("Every row of the map has been answered", ground_card.card(self.root))

    def test_a_generated_project_has_no_card(self) -> None:
        self.write({"name": "made"})
        self.assertEqual(ground_card.card(self.root), "")


if __name__ == "__main__":
    unittest.main()
