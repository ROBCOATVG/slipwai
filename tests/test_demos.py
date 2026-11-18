"""Nobody is asked to accept a demo by default: the hand's verdict is the acceptance.

The owner's words: "do we need accept if we're running skipper. I think it's just an opportunity to add
feedback." So `.specify/cruise.json`'s `demos` is `hand` unless a project says `person`, and every reader of
a capability's acceptance — clearance, the capabilities report, the board's fold, the film and the Feedback
card — answers the same under each. A verdict that is not `accepted` is unchanged by either.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from test_clearance import CHART, chart, line, mark_set

from slipwai import demos, fleet, logs
from slipwai.assets import TOOLKIT_ROOT
from slipwai.feedback_card import act, capabilities_html, to_look_at
from slipwai.film import films_card, films_of
from slipwai.logs import run_dir
from slipwai.passage import stages
from slipwai.project.cruise import cruise_config
from slipwai.settings_card import stops_tab
from slipwai.voyage import folded
from slipwai.wheel import CONFIG, asking, orders, set_stop

AGENTS = TOOLKIT_ROOT / "scripts/agents"
HAND_ACCEPTED = line("accepted", capability="place-an-order", by="sail-demo-hand")
CHART_YAML = """slices:
  ORD-01: {fairway: ordering, capability: place-an-order, sets: [OrderPlaced], steers_by: []}
  ORD-02: {fairway: ordering, capability: place-an-order, sets: [PricingPort], steers_by: []}
"""


def project(demos_value: str = "") -> Path:
    """A generated project's bones: its toolkit scripts, a chart, and `demos` where it is given."""
    root = Path(tempfile.mkdtemp()).resolve()
    (root / "scripts/agents").mkdir(parents=True)
    for name in ("deck_line.py", "clearance.py", "logs.py", "capabilities.py", "cruise.py"):
        shutil.copy(AGENTS / name, root / "scripts/agents" / name)
    (root / "project.json").write_text("{}", encoding="utf-8")
    (root / "specs/001-shop").mkdir(parents=True)
    (root / "specs/001-shop/chart.yaml").write_text(CHART_YAML, encoding="utf-8")
    (root / ".specify").mkdir()
    held = json.loads(cruise_config())
    if demos_value:
        held["demos"] = demos_value
    else:
        held.pop("demos")  # a project written before the setting existed
    (root / CONFIG).write_text(json.dumps(held), encoding="utf-8")
    return root


def run(root: Path, script: str, *argv: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "SLIPWAI_FAIRWAY"}
    return subprocess.run([sys.executable, "-B", f"scripts/agents/{script}", *argv], cwd=root, env=env,
                          capture_output=True, text=True, check=False)


def deck(root: Path) -> list[logs.Entry]:
    path = logs.deck_path(root, "001-shop", "ordering")
    return logs.fold(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else []


def merged_and(*more: dict) -> list[dict]:
    return [line("claimed", slice="ORD-01"), line("merged", slice="ORD-01", commit="a1"),
            line("claimed", slice="ORD-02"), line("merged", slice="ORD-02", commit="b2"), *more]


class ClearanceTest(unittest.TestCase):
    def test_under_hand_a_capability_the_hand_accepted_leaves_its_slices_done_and_nothing_awaiting_a_person(
            self) -> None:
        folded = chart.folded(merged_and(line("demo-due", capability="place-an-order"), HAND_ACCEPTED), "hand")
        self.assertEqual(folded.demo_due, set())
        self.assertEqual([chart.position(CHART, folded, one)[0] for one in ("ORD-01", "ORD-02")], ["done", "done"])

    def test_under_hand_a_slice_still_in_flight_is_never_awaiting_demo_even_with_a_demo_due_line(self) -> None:
        state, _ = chart.position(CHART, chart.folded([line("claimed", slice="ORD-01"),
                                                       mark_set("OrderPlaced", "ORD-01"),
                                                       line("demo-due", capability="place-an-order")], "hand"),
                                  "ORD-01")
        self.assertEqual(state, "running")

    def test_under_person_the_hand_s_accepted_closes_nothing_and_a_person_s_does(self) -> None:
        owed = [line("claimed", slice="ORD-01"), mark_set("OrderPlaced", "ORD-01"),
                line("demo-due", capability="place-an-order"), HAND_ACCEPTED]
        self.assertEqual(chart.position(CHART, chart.folded(owed, "person"), "ORD-01")[0], "awaiting-demo")
        theirs = [*owed, line("accepted", capability="place-an-order", by="person")]
        self.assertEqual(chart.position(CHART, chart.folded(theirs, "person"), "ORD-01")[0], "running")

    def test_a_verdict_that_is_not_accepted_is_a_retry_under_either_setting(self) -> None:
        for setting in ("hand", "person"):
            with self.subTest(demos=setting):
                state, why = chart.position(CHART, chart.folded([
                    line("claimed", slice="ORD-01"), mark_set("OrderPlaced", "ORD-01"),
                    line("demo", slice="ORD-01", verdict="behaviour")], setting), "ORD-01")
                self.assertEqual(state, "running")
                self.assertIn("sent back at the hand's demo (behaviour)", why)


class ProjectTest(unittest.TestCase):
    """What a generated project's own scripts write and read, run the way the project runs them."""

    def test_the_setting_is_hand_where_the_file_has_none_and_reads_back_once_changed(self) -> None:
        root = project()
        self.assertEqual(demos.setting(root), "hand")
        self.assertEqual(chart.demos_setting(root), "hand")
        done = run(root, "cruise.py", "--check")
        self.assertEqual(done.returncode, 0, done.stderr)
        done = run(root, "cruise.py", "--set", "demos=person")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((demos.setting(root), chart.demos_setting(root)), ("person", "person"))
        refused = run(root, "cruise.py", "--set", "demos=anyone")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("`demos` must be one of hand, person", refused.stderr)

    def test_the_capabilities_report_takes_the_hand_s_acceptance_only_under_hand(self) -> None:
        for setting, said in (("hand", "accepted, not hoisted"), ("person", "whole — gates due")):
            with self.subTest(demos=setting):
                root = project(setting)
                path = logs.deck_path(root, "001-shop", "ordering")
                path.parent.mkdir(parents=True)
                path.write_text("".join(json.dumps({"t": "2026-11-16T09:00:00Z", **one}) + "\n"
                                        for one in merged_and(HAND_ACCEPTED)), encoding="utf-8")
                done = run(root, "capabilities.py")
                self.assertIn(f"place-an-order: {said}", done.stdout, done.stderr)


class BoardTest(unittest.TestCase):
    def fold(self, setting: str, *more: logs.Entry) -> dict:
        root = project(setting)
        written = [logs.entry("merged", fairway="ordering", slice="ORD-01", commit="a1"), *more]
        path = logs.deck_path(root, "001-shop", "ordering")
        path.parent.mkdir(parents=True)
        path.write_text("".join(one.line() for one in written), encoding="utf-8")
        with mock.patch.object(fleet, "gates_owed", return_value=[]):
            return fleet.board(root, {})

    def test_under_hand_the_board_owes_no_person_a_demo_and_counts_the_hand_s_acceptance(self) -> None:
        board = self.fold("", logs.entry("demo-due", fairway="ordering", capability="place-an-order"),
                          logs.entry("accepted", fairway="ordering", capability="place-an-order",
                                     by="sail-demo-hand"))
        self.assertEqual((board["demos"], board["accepted"], board["demo_due"], board["demo_due_in"]),
                         ("hand", ["place-an-order"], [], {}))

    def test_under_person_the_board_owes_the_demo_until_a_person_accepts_it(self) -> None:
        due = logs.entry("demo-due", fairway="ordering", capability="place-an-order")
        hand = logs.entry("accepted", fairway="ordering", capability="place-an-order", by="sail-demo-hand")
        board = self.fold("person", due, hand)
        self.assertEqual((board["accepted"], board["demo_due_in"]), ([], {"place-an-order": "ordering"}))
        board = self.fold("person", due, hand, logs.entry("accepted", fairway="ordering",
                                                         capability="place-an-order", by="person"))
        self.assertEqual((board["accepted"], board["demo_due_in"]), (["place-an-order"], {}))

    def test_the_work_columns_read_a_hand_accepted_capability_s_slices_as_done_under_either_setting(self) -> None:
        """The board's columns are read off clearance's own answer, run as the project runs it. A capability
        the hand accepted has every slice merged, so neither setting holds one in *Working*."""
        for setting in ("hand", "person"):
            with self.subTest(demos=setting):
                root = project(setting)
                path = logs.deck_path(root, "001-shop", "ordering")
                path.parent.mkdir(parents=True)
                path.write_text("".join(json.dumps({"t": "2026-11-16T09:00:00Z", **one}) + "\n" for one in
                                        merged_and(line("demo-due", capability="place-an-order"),
                                                   HAND_ACCEPTED)), encoding="utf-8")
                rows, fault = folded(root)
                self.assertEqual(fault, "")
                self.assertEqual({row["slice"]: (row["state"], row["clearance"]) for row in rows},
                                 {"ORD-01": ("done", "done"), "ORD-02": ("done", "done")})

    def test_the_last_stage_says_who_accepts(self) -> None:
        for setting, said in (("hand", "the hand's walk, whose verdict is the acceptance"),
                              ("person", "the demo, as the actor; /cruise-tell records the verdict")):
            with self.subTest(demos=setting):
                found = stages(project(), None, {"accepted": ["place-an-order"], "demos": setting}, {"done": 2})
                last = next(one for one in found if one.key == "accepted")
                self.assertIn(said, last.next)
                self.assertIn("Nothing stops for you" if setting == "hand" else "It stops for you", last.expect)

    def test_built_and_nothing_accepted_yet_is_taken_to_its_acceptance_not_promised_a_demo(self) -> None:
        found = stages(project(), None, {"accepted": [], "demos": "hand"}, {"done": 2})
        last = next(one for one in found if one.key == "accepted")
        self.assertEqual(last.next, "/sail takes each whole capability through its gates to its acceptance")


class FilmAndFeedbackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.home = run_dir(self.root) / "walks/001-shop/place-an-order"
        self.home.mkdir(parents=True)
        (self.home / "film.webm").write_bytes(b"0123")
        (self.root / "specs/001-shop").mkdir(parents=True)
        (self.root / "specs/001-shop/chart.yaml").write_text(CHART_YAML, encoding="utf-8")

    def test_under_hand_the_film_offers_say_what_it_showed_and_the_feedback_card_no_accept(self) -> None:
        board: dict = {"demos": "hand", "demo_due_in": {}}
        card = films_card(films_of(self.root), [], board["demo_due_in"])
        self.assertIn("Say what it showed", card)
        self.assertIn("&quot;capability&quot;: &quot;place-an-order&quot;", card, "the film's context on the box")
        self.assertNotIn("Ready for you", card)
        self.assertEqual(capabilities_html(board), "")
        with self.assertRaises(ValueError) as refused:
            act(self.root, {"verb": "accept", "capability": "place-an-order", "fairway": "ordering"}, [], board,
                lambda: True)
        self.assertIn("the hand's verdict as the acceptance", str(refused.exception))

    def test_under_person_the_film_says_ready_and_the_feedback_card_offers_accept_and_not_yet(self) -> None:
        board: dict = {"demos": "person", "demo_due_in": {"place-an-order": "ordering"}}
        card = films_card(films_of(self.root), [], board["demo_due_in"])
        self.assertIn("Ready for you · accept it below", card)
        self.assertNotIn("Say what it showed", card)
        offered = capabilities_html(board)
        self.assertIn('data-fb="accept"', offered)
        self.assertIn("Not yet: say why", offered)

    def test_a_film_nobody_has_said_anything_about_or_opened_is_there_to_look_at(self) -> None:
        self.assertEqual(to_look_at(self.root, {}), [{"feature": "001-shop", "capability": "place-an-order",
                                                     "title": "Place an order", "accept": ""}])
        self.assertEqual(to_look_at(self.root, {"demo_due_in": {"place-an-order": "ordering"}})[0]["accept"],
                         "yes")
        demos.mark_opened(self.root, "001-shop", "place-an-order")
        self.assertEqual(to_look_at(self.root, {}), [])

    def test_saying_what_a_film_showed_takes_it_off_the_list(self) -> None:
        act(self.root, {"verb": "send", "words": "The basket total looked wrong.",
                        "context": {"from": "capability", "capability": "place-an-order"}}, [], {}, lambda: False)
        self.assertEqual(to_look_at(self.root, {}), [])


class SettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = project()

    def test_the_setting_is_shown_beside_who_answers_and_defaults_to_the_hand(self) -> None:
        answers = orders(self.root)
        self.assertEqual(answers["demos"], "hand", "a file without it reads as its default")
        found = stops_tab(answers, True)
        assert found is not None
        self.assertIn("demo</b>", found[2])
        self.assertIn('data-key="demos" data-value="person"', found[2])
        self.assertNotIn("a capability's demo", asking(self.root))

    def test_person_is_the_value_that_asks_and_is_set_through_the_project_s_own_script(self) -> None:
        self.assertEqual(set_stop(self.root, "demos", "person"), "demos = person")
        self.assertEqual(orders(self.root)["demos"], "person")
        self.assertIn("A capability's demo", asking(self.root))
        found = stops_tab(orders(self.root), True)
        assert found is not None
        self.assertIn("This run stops for you at: the specification, storyboard and model, a capability", found[2])
        self.assertIn('class="now asks">wait for me to accept it', found[2], "drawn amber, as its neighbours")


if __name__ == "__main__":
    unittest.main()
