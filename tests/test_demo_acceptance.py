"""Who may write a capability's acceptance, and when: whole, cleared, and as the setting says.

The first build of the `demos` setting gave `deck_line.py accepted` a `--by person` that any session could
pass, with nothing merged and no gates record, so a slice's own session could accept as a person and undo
`demos: person`. These hold the doors shut: the command takes only the hand's acceptance and only of a whole,
cleared capability; the board writes a person's, under the same rule; and a project mid-voyage keeps what the
hand had already accepted on paper before there was a line to say so.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from test_clearance import chart
from test_demos import CHART_YAML, deck, project, run

from slipwai import demos, fleet, logs
from slipwai.feedback_card import act
from slipwai.logs import run_dir

TWO_FAIRWAYS = """slices:
  ORD-01: {fairway: ordering, capability: checkout, sets: [OrderPlaced], steers_by: []}
  BIL-01: {fairway: billing, capability: checkout, sets: [InvoiceRaised], steers_by: []}
"""


def merge(root: Path, *slices: str, fairway: str = "ordering") -> None:
    path = logs.deck_path(root, "001-shop", fairway)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for one in slices:
            handle.write(logs.entry("merged", fairway=fairway, slice=one, commit="c0ffee").line())


def clear(root: Path, capability: str = "place-an-order") -> None:
    record = root / "specs/001-shop/capabilities" / capability / "gates.md"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text("# Gates\n\nCleared: 2026-11-16 · c0ffee\n", encoding="utf-8")


def accepted(root: Path) -> list[str]:
    return [one for row in json.loads(run(root, "capabilities.py", "--json").stdout)["rows"]
            if row["accepted"] for one in [row["capability"]]]


def written(root: Path) -> list[dict]:
    """Every fairway's log of the feature, as clearance folds them."""
    return [json.loads(text) for path in sorted(logs.deck_path(root, "001-shop", "x").parent.glob("*.jsonl"))
            for text in path.read_text(encoding="utf-8").splitlines()]


class CommandTest(unittest.TestCase):
    def test_the_hand_s_acceptance_is_refused_until_the_capability_is_whole_and_cleared(self) -> None:
        root = project()
        hand = ("accepted", "--capability", "place-an-order", "--by", "sail-demo-hand")
        self.assertIn("is not whole: ORD-01, ORD-02 not merged", run(root, "deck_line.py", *hand).stderr)
        merge(root, "ORD-01", "ORD-02")
        self.assertIn("gates have not cleared", run(root, "deck_line.py", *hand).stderr)
        clear(root)
        done = run(root, "deck_line.py", *hand)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual([(one.kind, one.fields.get("by")) for one in deck(root)][-1],
                         ("accepted", "sail-demo-hand"))
        self.assertIn("accepted already", run(root, "deck_line.py", *hand).stderr)

    def test_no_session_can_write_a_person_s_acceptance_under_either_setting(self) -> None:
        for setting in ("hand", "person"):
            with self.subTest(demos=setting):
                root = project(setting)
                merge(root, "ORD-01", "ORD-02")
                clear(root)
                done = run(root, "deck_line.py", "accepted", "--capability", "place-an-order", "--by", "person")
                self.assertNotEqual(done.returncode, 0)
                self.assertIn("written by the board when they press Accept", done.stderr)
                self.assertNotIn("accepted", [one.kind for one in deck(root)])

    def test_under_person_the_hand_s_command_is_refused_and_demo_due_is_written(self) -> None:
        root = project("person")
        merge(root, "ORD-01", "ORD-02")
        clear(root)
        hand = run(root, "deck_line.py", "accepted", "--capability", "place-an-order", "--by", "sail-demo-hand")
        self.assertIn("write `demo-due`", hand.stderr)
        self.assertEqual(run(root, "deck_line.py", "demo-due", "--capability", "place-an-order").returncode, 0)
        self.assertEqual([one.kind for one in deck(root)][-1], "demo-due")

    def test_under_hand_demo_due_is_refused_with_the_reason_rather_than_written_and_ignored(self) -> None:
        root = project()
        merge(root, "ORD-01", "ORD-02")
        clear(root)
        done = run(root, "deck_line.py", "demo-due", "--capability", "place-an-order")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("so no person is owed a demo", done.stderr)
        self.assertNotIn("demo-due", [one.kind for one in deck(root)])

    def test_under_hand_due_says_nothing_is_owed_a_person_and_lists_what_the_hand_owes(self) -> None:
        root = project()
        merge(root, "ORD-01", "ORD-02")
        clear(root)
        said = run(root, "capabilities.py", "--due").stdout
        self.assertIn("nothing is owed a person", said)
        self.assertIn("1 whole and gated with no `accepted` line yet", said)
        self.assertIn("capabilities: 1 owed a demo", run(project_of(root, "person"), "capabilities.py", "--due").stdout)


def project_of(root: Path, setting: str) -> Path:
    """The same project under the other setting."""
    held = json.loads((root / ".specify/cruise.json").read_text(encoding="utf-8"))
    (root / ".specify/cruise.json").write_text(json.dumps({**held, "demos": setting}), encoding="utf-8")
    return root


class RecordTest(unittest.TestCase):
    """A project mid-voyage: the hand's verdicts on paper, no `accepted` line."""

    def test_a_register_naming_the_hand_for_every_slice_reads_as_the_hand_s_acceptance_under_hand(self) -> None:
        root = project()
        merge(root, "ORD-01", "ORD-02")
        clear(root)
        (root / "specs/001-shop/slices").mkdir(parents=True)
        (root / "specs/001-shop/slices/README.md").write_text(
            "| Slice | Accepted |\n|---|---|\n| ORD-01 | 2026-10-20 · accepted-by: sail-demo-hand |\n"
            "| ORD-02 | 2026-10-21 · accepted-by: sail-demo-hand |\n", encoding="utf-8")
        self.assertEqual(accepted(root), ["place-an-order"])
        self.assertIn("accepted (the hand's, from its record)", run(root, "capabilities.py").stdout)
        with mock.patch.object(fleet, "gates_owed", return_value=[]):
            self.assertEqual(fleet.board(root, {})["accepted"], ["place-an-order"])
        self.assertEqual(accepted(project_of(root, "person")), [], "a person's demo is not backfilled")

    def test_a_capability_demo_log_ending_on_the_hand_s_accepted_reads_the_same(self) -> None:
        root = project()
        merge(root, "ORD-01", "ORD-02")
        log = root / "specs/001-shop/capabilities/place-an-order/demo-log.md"
        log.parent.mkdir(parents=True)
        log.write_text("## 2026-10-20T10:00:00Z — accepted · place-an-order · sail-demo-hand (model)\n",
                       encoding="utf-8")
        self.assertEqual(accepted(root), [], "not before its gates clear")
        clear(root)
        self.assertEqual(accepted(root), ["place-an-order"])


class BoardAcceptTest(unittest.TestCase):
    def test_under_person_accept_on_the_board_writes_the_person_s_line_once_whole_and_cleared(self) -> None:
        root = project("person")
        board = {"demos": "person", "demo_due_in": {"place-an-order": "ordering"}}
        press = {"verb": "accept", "capability": "place-an-order", "fairway": "ordering"}
        with self.assertRaises(ValueError) as refused:
            act(root, press, [], board, lambda: True)
        self.assertIn("is not whole", str(refused.exception))
        merge(root, "ORD-01", "ORD-02")
        clear(root)
        self.assertIn("place-an-order accepted", act(root, press, [], board, lambda: True))
        self.assertIn(("accepted", "person"), [(one.kind, one.fields.get("by")) for one in deck(root)])
        self.assertEqual(accepted(root), ["place-an-order"])
        with self.assertRaises(ValueError):
            demos.accept(root, "place-an-order")

    def test_under_hand_the_board_writes_no_person_s_acceptance(self) -> None:
        root = project()
        merge(root, "ORD-01", "ORD-02")
        clear(root)
        with self.assertRaises(ValueError) as refused:
            demos.accept(root, "place-an-order")
        self.assertIn("the hand's verdict as the acceptance", str(refused.exception))


class TwoFairwaysTest(unittest.TestCase):
    def test_a_capability_across_two_fairways_is_accepted_in_the_last_and_read_so_from_every_reader(self) -> None:
        root = project()
        (root / "specs/001-shop/chart.yaml").write_text(TWO_FAIRWAYS, encoding="utf-8")
        merge(root, "ORD-01")
        merge(root, "BIL-01", fairway="billing")
        clear(root, "checkout")
        done = run(root, "deck_line.py", "accepted", "--capability", "checkout", "--by", "sail-demo-hand")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("billing.jsonl", done.stdout, "the fairway its last slice is in, in split order")
        self.assertEqual(accepted(root), ["checkout"])
        with mock.patch.object(fleet, "gates_owed", return_value=[]):
            self.assertEqual(fleet.board(root, {})["accepted"], ["checkout"])

    def test_under_person_the_demo_due_in_the_last_fairway_is_owed_until_the_board_accepts_it(self) -> None:
        root = project("person")
        (root / "specs/001-shop/chart.yaml").write_text(TWO_FAIRWAYS, encoding="utf-8")
        merge(root, "ORD-01")
        merge(root, "BIL-01", fairway="billing")
        clear(root, "checkout")
        self.assertEqual(run(root, "deck_line.py", "demo-due", "--capability", "checkout").returncode, 0)
        with mock.patch.object(fleet, "gates_owed", return_value=[]):
            self.assertEqual(fleet.board(root, {})["demo_due_in"], {"checkout": "billing"})
            self.assertEqual(chart.folded(written(root), "person").demo_due, {"checkout"})
            demos.accept(root, "checkout")
            self.assertEqual(fleet.board(root, {})["demo_due_in"], {})
        self.assertEqual(chart.folded(written(root), "person").demo_due, set(), "clearance reads both fairways")


class OpenedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (run_dir(self.root) / "walks/001-shop/place-an-order").mkdir(parents=True)
        (self.root / "specs/001-shop").mkdir(parents=True)
        (self.root / "specs/001-shop/chart.yaml").write_text(CHART_YAML, encoding="utf-8")

    def test_a_film_the_chart_and_the_walks_folder_hold_is_marked_opened(self) -> None:
        self.assertTrue(demos.mark_opened(self.root, "001-shop", "place-an-order"))
        self.assertTrue(demos.opened(self.root, "001-shop", "place-an-order"))

    def test_a_name_that_climbs_out_or_that_nothing_holds_is_answered_no_and_writes_nothing(self) -> None:
        (run_dir(self.root) / "walks/001-shop/stray").mkdir()
        for feature, capability in (("001-shop", "../../.."), ("..", "place-an-order"), ("001-shop", "a/b"),
                                    ("001-shop", "stray"), ("001-shop", "missing"), ("", ""),
                                    ("001-shop", "place-an-order\x00")):
            with self.subTest(feature=feature, capability=capability):
                self.assertFalse(demos.mark_opened(self.root, feature, capability))
        self.assertEqual(sorted(path.name for path in self.root.rglob("opened")), [])


if __name__ == "__main__":
    unittest.main()
