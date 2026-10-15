"""Who is at the wheel at each stop of a run, read off the project and changed from the board.

The pair `/sail` and `/cruise` is one sentence in the glossary — somebody is at the wheel, or nobody is —
and it was never one switch. `/cruise` runs the same ladder and differs only at the stops, and
`.specify/cruise.json` answers each of them separately: `park` on one *is* `/sail` for that stop. So what
this holds is that the board reads those answers, writes one through the project's own script, and never
writes the file itself.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.project.cruise import cruise_config
from slipwai.settings_card import stops_tab
from slipwai.wheel import ASKS, CONFIG, STOPS, asking, known, orders, set_stop

#: A script that records what it was asked instead of writing anything, so the test holds *that the board
#: runs the project's own writer* rather than re-testing the writer.
RECORDER = """import json, pathlib, sys
pathlib.Path("asked.txt").write_text(" ".join(sys.argv[1:]), encoding="utf-8")
"""
REFUSER = """import sys
print("that is not one of this stop's answers", file=sys.stderr)
sys.exit(1)
"""


def tab(answers: dict[str, str]) -> str:
    """The stops tab's HTML. A tab is (key, what the bar says, the panel); the panel is what is read here."""
    found = stops_tab(answers, True)
    return found[2] if found else ""


class WheelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".specify").mkdir()
        (self.root / CONFIG).write_text(cruise_config(), encoding="utf-8")

    def script(self, body: str) -> None:
        where = self.root / "scripts/agents"
        where.mkdir(parents=True)
        (where / "cruise.py").write_text(body, encoding="utf-8")

    def answer(self, **given: str) -> None:
        held = json.loads((self.root / CONFIG).read_text(encoding="utf-8"))
        (self.root / CONFIG).write_text(json.dumps({**held, **given}), encoding="utf-8")

    def test_the_stops_and_their_answers_come_from_the_one_list_the_project_is_written_from(self) -> None:
        """Rendered from `project.cruise.SETTINGS`, so the card cannot offer an answer the project's own
        checker would refuse."""
        for name, _, says in STOPS:
            with self.subTest(stop=name):
                self.assertEqual(set(says), set(known(name)), "every value the setting takes, and no other")

    def test_a_generated_project_answers_every_stop_itself(self) -> None:
        """Which is what `/cruise` is. A fresh project stops for nobody, and the card says so."""
        self.assertEqual(asking(self.root), [])
        self.assertIn("Nothing here stops for you", tab(orders(self.root)))

    def test_a_stop_set_to_park_is_this_run_asking_a_person(self) -> None:
        self.answer(unblock=ASKS, release=ASKS)
        self.assertEqual(asking(self.root), ["A block", "A release"])
        said = tab(orders(self.root))
        self.assertIn("This run stops for you at: a block, a release.", said)
        self.assertIn('class="now asks"', said, "the amber of a control that waits on somebody")

    def test_there_is_no_card_where_the_project_has_no_answers_to_show(self) -> None:
        """A harbour, or a repository adopted before this was configurable. A card offering to set a file
        that is not there would be a control that refuses every press."""
        self.assertEqual(orders(Path(tempfile.mkdtemp())), {})
        self.assertIsNone(stops_tab({}, True), "no tab at all, rather than an empty one")

    def test_setting_one_runs_the_project_s_own_script_rather_than_writing_the_file(self) -> None:
        """`scripts/agents/cruise.py` is what `/cruise-settings` runs and what `make check-agents` holds.
        A second writer here would be the first to drift from the project's own checker."""
        self.script(RECORDER)
        self.assertEqual(set_stop(self.root, "unblock", ASKS), "unblock = park")
        self.assertEqual((self.root / "asked.txt").read_text(encoding="utf-8"), "--set unblock=park")
        self.assertEqual(orders(self.root)["unblock"], "bosun", "the recorder wrote nothing, and nor did we")

    def test_what_the_script_refused_is_what_the_page_is_told(self) -> None:
        self.script(REFUSER)
        with self.assertRaises(ValueError) as refused:
            set_stop(self.root, "unblock", ASKS)
        self.assertIn("not one of this stop's answers", str(refused.exception))

    def test_a_project_with_no_script_says_where_the_script_comes_from(self) -> None:
        with self.assertRaises(ValueError) as refused:
            set_stop(self.root, "unblock", ASKS)
        self.assertIn("./init", str(refused.exception))

    def test_a_stop_or_a_value_this_board_does_not_draw_is_refused_before_anything_runs(self) -> None:
        self.script(RECORDER)
        for stop, value in (("model", "gpt-9"), ("unblock", "whatever"), ("", "")):
            with self.subTest(stop=stop), self.assertRaises(ValueError):
                set_stop(self.root, stop, value)
        self.assertFalse((self.root / "asked.txt").exists(), "refused before the script was reached")


if __name__ == "__main__":
    unittest.main()
