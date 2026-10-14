"""The committed model with each slice's standing drawn on it, and the fold the columns come from.

The picture is draw.io's and the file is the project's: what is proved is that the board finds a slice's
caption by the id the renderer gave it, strokes it and nothing else, and hands the file back untouched
wherever it cannot be sure — and that the words around the picture say what is missing.
"""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.voyage import cell_id, counts, folded, model_xml, restroked, states_of, viewer_config


def cell(name: str, value: str, style: str, parent: str) -> str:
    return f'<mxCell id="{name}" value="{value}" style="{style}" vertex="1" parent="{parent}"/>'


DRAWIO = ('<mxfile host="app.diagrams.net"><diagram id="d" name="model"><mxGraphModel><root>'
          '<mxCell id="0"/><mxCell id="1" parent="0"/>'
          + cell("c-frame", "model", "rounded=0;strokeColor=#b3b3b3;container=1;", "1")
          + cell("c-slice-Join_a_session", "Join a session", "rounded=1;strokeColor=#dbdada;strokeWidth=1;", "c-frame")
          + cell("c-slice-Search_games", "Search games", "rounded=1;strokeColor=#dbdada;", "c-frame")
          + '</root></mxGraphModel></diagram></mxfile>')


class CaptionTest(unittest.TestCase):
    def test_the_id_is_the_renderer_s(self) -> None:
        """`c-slice-<id>`, every character outside `[A-Za-z0-9_-]` an underscore — what drawio.ts writes."""
        self.assertEqual(cell_id("Join a session"), "c-slice-Join_a_session")
        self.assertEqual(cell_id("order.placed/v2"), "c-slice-order_placed_v2")

    def test_a_slice_s_caption_is_stroked_by_its_state_and_nothing_else_moves(self) -> None:
        drawn = restroked(DRAWIO, {"Join a session": "working", "Search games": "waiting", "Unknown": "done"})
        self.assertIn('style="rounded=1;strokeColor=#8a6d24;strokeWidth=3;"', drawn)
        self.assertIn("strokeColor=#b4432f;strokeWidth=3;dashed=1;dashPattern=6 4;", drawn)
        self.assertIn('strokeColor=#b3b3b3;container=1;', drawn, "the frame is not a slice")
        self.assertNotIn("Unknown", drawn)

    def test_a_slice_still_to_do_keeps_the_renderer_s_own_stroke(self) -> None:
        self.assertEqual(restroked(DRAWIO, {"Join a session": "todo"}), DRAWIO)

    def test_a_file_that_does_not_parse_comes_back_untouched(self) -> None:
        self.assertEqual(restroked("<mxfile><broken", {"x": "done"}), "<mxfile><broken")


class ModelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "docs/event-model").mkdir(parents=True)

    def test_no_model_and_no_picture_each_say_so(self) -> None:
        self.assertEqual(model_xml(self.root, {}), ("", "this project has no event model"))
        (self.root / "docs/event-model/model.yaml").write_text("slices: []\n", encoding="utf-8")
        xml, note = model_xml(self.root, {})
        self.assertEqual(xml, "")
        self.assertIn("make model-drawio", note)

    def test_a_picture_older_than_the_model_is_shown_with_a_note(self) -> None:
        (self.root / "docs/event-model/model.drawio").write_text(DRAWIO, encoding="utf-8")
        xml, note = model_xml(self.root, {"Join a session": "done"})
        self.assertIn("strokeColor=#0f6b6b", xml)
        self.assertEqual(note, "")
        time.sleep(0.05)
        (self.root / "docs/event-model/model.yaml").write_text("slices:\n  - id: A\n", encoding="utf-8")
        self.assertIn("newer than the picture", model_xml(self.root, {})[1])

    def test_the_viewer_is_given_the_picture_and_a_read_only_toolbar(self) -> None:
        held = json.loads(viewer_config(DRAWIO))
        self.assertEqual(held["xml"], DRAWIO)
        self.assertIn("zoom", held["toolbar"])
        self.assertFalse(held["lightbox"])


class FoldTest(unittest.TestCase):
    def test_no_chart_is_no_slices_and_no_fault(self) -> None:
        self.assertEqual(folded(Path(tempfile.mkdtemp())), ([], ""))

    def test_counts_and_states_read_the_rows(self) -> None:
        rows = [{"slice": "A", "state": "done"}, {"slice": "B", "state": "todo"}, {"slice": "C", "state": "todo"}]
        self.assertEqual(counts(rows), {"todo": 2, "done": 1})
        self.assertEqual(states_of(rows), {"A": "done", "B": "todo", "C": "todo"})


if __name__ == "__main__":
    unittest.main()
