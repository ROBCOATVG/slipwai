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

from slipwai.voyage import (
    cell_id,
    counts,
    fleet_running,
    folded,
    mockup_file,
    mockups,
    model_xml,
    restroked,
    states_of,
    titles,
    viewer_config,
)


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
        self.assertEqual(held["toolbar"], "", "the board's own controls stand in for the viewer's")
        self.assertFalse(held["resize"], "a fixed canvas, panned and zoomed, rather than one sized to the picture")
        self.assertFalse(held["lightbox"])


class MockupsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.home = self.root / "specs/001-demo/mockups"
        self.home.mkdir(parents=True)
        (self.home / "catalog.html").write_text("<html><head><title>Mock: catalog — Demo</title></head></html>",
                                                encoding="utf-8")
        (self.home / "mock.css").write_text("body{}", encoding="utf-8")
        (self.home / "research.md").write_text("# notes\n", encoding="utf-8")
        (self.root / "secret.txt").write_text("no", encoding="utf-8")

    def test_every_wireframe_is_listed_by_its_own_title(self) -> None:
        found = mockups(self.root)
        self.assertEqual([(row["feature"], row["name"], row["title"], row["href"]) for row in found],
                         [("001-demo", "catalog.html", "catalog — Demo", "/mockups/001-demo/catalog.html")])
        self.assertEqual(mockups(Path(tempfile.mkdtemp())), [])

    def test_the_route_serves_a_mock_up_and_its_stylesheet_and_nothing_outside_them(self) -> None:
        self.assertEqual(mockup_file(self.root, "001-demo/catalog.html"), (self.home / "catalog.html").resolve())
        self.assertEqual(mockup_file(self.root, "001-demo/mock.css"), (self.home / "mock.css").resolve())
        for outside in ("001-demo/../../secret.txt", "001-demo/../spec.md", "../secret.txt", "001-demo/", "",
                        "nope/x.html"):
            self.assertIsNone(mockup_file(self.root, outside), outside)


class FoldTest(unittest.TestCase):
    def test_no_chart_is_no_slices_and_no_fault(self) -> None:
        self.assertEqual(folded(Path(tempfile.mkdtemp())), ([], ""))

    def test_a_slice_s_title_is_read_off_the_split(self) -> None:
        """The chart carries ids; the split's table is where a slice is called something a person would say."""
        root = Path(tempfile.mkdtemp())
        (root / "specs/001-demo").mkdir(parents=True)
        (root / "specs/001-demo/story-split.md").write_text(
            "**S02 Publish a listing** — a host publishes a table\n\n"
            "| Slice | Outcome |\n|---|---|\n| S01 Set up an account | A signed-in person has a name |\n"
            "| S02 Publish a listing | A host can offer chairs |\n", encoding="utf-8")
        self.assertEqual(titles(root, "001-demo"), {"S01": "Set up an account", "S02": "Publish a listing"})
        self.assertEqual(titles(root, "002-none"), {})

    def test_the_fleet_is_running_only_while_a_pid_it_wrote_is_alive(self) -> None:
        root = Path(tempfile.mkdtemp())
        self.assertFalse(fleet_running(root), "nothing started")
        (root / ".slipwai/running").mkdir(parents=True)
        (root / ".slipwai/running/captain-x.pid").write_text("999999999\n", encoding="utf-8")
        self.assertFalse(fleet_running(root), "a captain that has died")
        import os
        (root / ".slipwai/running/harbourmaster.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        self.assertTrue(fleet_running(root))

    def test_counts_and_states_read_the_rows(self) -> None:
        rows = [{"slice": "A", "state": "done"}, {"slice": "B", "state": "todo"}, {"slice": "C", "state": "todo"}]
        self.assertEqual(counts(rows), {"todo": 2, "done": 1})
        self.assertEqual(states_of(rows), {"A": "done", "B": "todo", "C": "todo"})


if __name__ == "__main__":
    unittest.main()
