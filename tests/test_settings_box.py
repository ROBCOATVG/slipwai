"""What a run is set to, in one box: the telegraph's two tabs and whatever the project has beside them.

Four settings surfaces were four places — two cards for the telegraph, a third for who answers, and two
files with no control at all that a person changed by typing a command in an agent while the board was
open in front of them. What is held here is which tabs a project gets, that the two files the ladder reads
are written by the project's own scripts, and that the box works on the copy of this board that has no
JavaScript at all.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai.bridge_page import read_only
from slipwai.dials import MODELS, MODELS_CONFIG, SAIL, dials, held, roles, set_dial
from slipwai.fleet import board
from slipwai.project.cruise import cruise_config
from slipwai.project.sail_settings import CONFIG as SAIL_CONFIG
from slipwai.project.sail_settings import sail_config
from slipwai.project.stage_models import stage_models
from slipwai.settings_card import project_tabs

#: A script that records what it was asked rather than writing anything, so these hold *that the board
#: runs the project's own writer* rather than re-testing the writer.
RECORDER = """import pathlib, sys
pathlib.Path("asked.txt").write_text(" ".join(sys.argv[1:]), encoding="utf-8")
"""


class ProjectFilesTest(unittest.TestCase):
    """Reading the two files the ladder reads, and writing them the one allowed way."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".specify").mkdir()
        (self.root / SAIL_CONFIG).write_text(sail_config(), encoding="utf-8")
        (self.root / MODELS_CONFIG).write_text(stage_models(), encoding="utf-8")

    def script(self, name: str, body: str = RECORDER) -> None:
        where = self.root / "scripts/agents"
        where.mkdir(parents=True, exist_ok=True)
        (where / name).write_text(body, encoding="utf-8")

    def test_a_generated_project_is_read_at_the_defaults_it_was_written_with(self) -> None:
        self.assertEqual(held(self.root, SAIL), {"delegate": "story", "cycle": "rule"})
        self.assertEqual(held(self.root, MODELS)["principles"], "strong")

    def test_a_project_without_the_file_is_nothing_to_show_rather_than_a_fault(self) -> None:
        """A harbour, an adopted repository, a project generated before the file existed."""
        bare = Path(tempfile.mkdtemp())
        self.assertEqual(held(bare, SAIL), {})
        self.assertEqual(project_tabs(bare, True), [])

    def test_the_roles_offered_are_the_ones_this_project_has_mapped(self) -> None:
        """`models.py` takes any role name and adds it unmapped, so a board offering one the project has
        not mapped would be offering a fall-through dressed as a choice."""
        found = roles(self.root)
        self.assertIn("strong", found)
        self.assertIn("fast", found)
        table = json.loads((self.root / MODELS_CONFIG).read_text(encoding="utf-8"))
        table.setdefault("roles", {}).setdefault("claude", {})["thrifty"] = "haiku"
        (self.root / MODELS_CONFIG).write_text(json.dumps(table), encoding="utf-8")
        self.assertIn("thrifty", roles(self.root))

    def test_every_stage_of_the_ladder_is_a_row_with_the_fall_through_first(self) -> None:
        rows = dials(self.root, MODELS)
        self.assertEqual(rows[0][0].key, "default", "what any stage with no row of its own runs under")
        self.assertGreater(len(rows), 20, "one per stage of the ladder")

    def test_setting_one_runs_the_project_s_own_script_rather_than_writing_the_file(self) -> None:
        """The rule `wheel` opens with: each script validates against the same table this renders from,
        and `make check-agents` holds the file's shape. A second writer here would be the first to drift."""
        self.script("sail.py")
        self.assertEqual(set_dial(self.root, "sail", "delegate", "task"), "delegate = task")
        self.assertEqual((self.root / "asked.txt").read_text(encoding="utf-8"), "--set delegate=task")
        self.script("models.py")
        set_dial(self.root, "models", "principles", "fast")
        self.assertEqual((self.root / "asked.txt").read_text(encoding="utf-8"), "--set principles=fast")

    def test_a_setting_or_value_this_board_does_not_draw_is_refused_before_anything_runs(self) -> None:
        self.script("sail.py")
        for panel, key, value, why in (("nope", "delegate", "task", "not a settings file"),
                                       ("sail", "wheel", "task", "not a setting"),
                                       ("sail", "delegate", "whatever", "not one of")):
            with self.subTest(panel=panel, key=key, value=value):
                with self.assertRaises(ValueError) as caught:
                    set_dial(self.root, panel, key, value)
                self.assertIn(why, str(caught.exception))
        self.assertFalse((self.root / "asked.txt").exists(), "nothing was run")

    def test_a_project_with_no_script_says_so_rather_than_writing_the_file_itself(self) -> None:
        with self.assertRaises(ValueError) as caught:
            set_dial(self.root, "sail", "delegate", "task")
        self.assertIn("is not in this project", str(caught.exception))


class BoxTest(BoardTest):
    """The box on the page, and the route behind its controls."""

    def project(self) -> None:
        (self.root / ".specify").mkdir(exist_ok=True)
        (self.root / ".specify/cruise.json").write_text(cruise_config(), encoding="utf-8")
        (self.root / SAIL_CONFIG).write_text(sail_config(), encoding="utf-8")
        (self.root / MODELS_CONFIG).write_text(stage_models(), encoding="utf-8")

    def test_the_telegraph_is_always_there_and_the_project_s_own_files_only_where_they_are(self) -> None:
        said = self.get("/voyage")[1]
        for key in ("speed", "tune"):
            self.assertIn(f'for="tab-{key}"', said, "the board's own, whatever it is looking at")
        for key in ("answers", "sail", "models"):
            self.assertNotIn(f'for="tab-{key}"', said)
        self.project()
        said = self.get("/voyage")[1]
        for key in ("speed", "tune", "answers", "sail", "models"):
            self.assertIn(f'for="tab-{key}"', said)
        self.assertIn('id="tab-speed" checked', said, "speed is the tab the box opens on")

    def test_twenty_two_stages_are_a_table_of_menus_rather_than_a_hundred_buttons(self) -> None:
        self.project()
        said = self.get("/voyage")[1]
        self.assertIn('<select data-dial="models" data-key="principles">', said)
        self.assertIn('<option value="strong" selected>', said)

    def test_every_stage_row_is_named_by_something_that_tells_it_from_the_others(self) -> None:
        """Three stages of the ladder carry no title and two share one, so a row labelled by its title
        alone is a blank row or one of an indistinguishable pair. The key is what the file holds."""
        self.project()
        said = self.get("/voyage")[1]
        for key in ("demo-hand", "plan", "tasks-quartermaster"):
            with self.subTest(stage=key):
                self.assertIn(f'<i class="key">{key}</i>', said)

    def test_a_setting_is_changed_from_the_page_through_the_project_s_own_script(self) -> None:
        self.project()
        (self.root / "scripts/agents").mkdir(parents=True, exist_ok=True)
        (self.root / "scripts/agents/sail.py").write_text(RECORDER, encoding="utf-8")
        self.assertEqual(self.post("/dial", {"panel": "sail", "key": "cycle", "value": "example"})[0], 200)
        self.assertEqual((self.root / "asked.txt").read_text(encoding="utf-8"), "--set cycle=example")

    def test_a_dial_this_board_does_not_draw_is_refused(self) -> None:
        code, said = self.post("/dial", {"panel": "sail", "key": "delegate", "value": "whatever"})
        self.assertEqual(code, 400)
        self.assertIn("is not one of delegate's values", said)
        self.assertEqual(self.post("/dial", {"panel": "sail", "key": "wheel", "value": "task"})[0], 400)


class PublishedTest(unittest.TestCase):
    def test_the_tabs_work_on_the_copy_that_has_no_javascript(self) -> None:
        """The published board is one file with nothing to press and therefore no script. Radio buttons
        and a stylesheet, so a box whose tabs only worked on the served copy is not what gets published."""
        root = Path(tempfile.mkdtemp())
        said = read_only(board(root), {})
        self.assertNotIn("<script>", said)
        self.assertIn('id="tab-speed"', said)
        self.assertIn("#tab-tune:checked~.panels>[data-panel=tune]", said)
        self.assertNotIn("data-dial=", said, "nothing to press on a published file")


if __name__ == "__main__":
    unittest.main()
