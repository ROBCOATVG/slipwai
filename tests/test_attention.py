"""What waits on the person: folded for the Voyage in `upstream`, and said by the strip and the switch every
served page carries from `attention`."""
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import checkout_packages  # noqa: F401

from slipwai import page_shell, upstream


class Stage:
    def __init__(self, turns: list[dict], done: bool = True) -> None:
        self.turns, self.done = turns, done

    def said(self, since: int = 0) -> dict:
        return {"turns": self.turns[since:], "at": len(self.turns), "done": self.done, "command": ""}


def board(root: Path, turns: list[dict] | None = None, done: bool = True) -> SimpleNamespace:
    fitting = SimpleNamespace(stage=Stage(turns or [], done), said=lambda since=0: {"done": done, "lines": []})
    return SimpleNamespace(root=root, fitting=fitting if turns is not None else None)


class VoyageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.held = TemporaryDirectory()
        self.root = Path(self.held.name)
        self.addCleanup(self.held.cleanup)

    def test_nothing_offered_and_nothing_parked_is_no_wait(self) -> None:
        self.assertEqual(upstream.on_voyage(board(self.root), {}, {}), {"count": 0, "text": "", "href": ""})

    def test_a_specification_with_nothing_drawn_waits_to_be_read_and_drawn(self) -> None:
        said = upstream.on_voyage(board(self.root), {}, {"drawable": True, "launchable": False})
        self.assertEqual(said, {"count": 1, "text": "The specification is ready: read it, then draw the surfaces",
                                "href": "#draw"})

    def test_a_drawn_storyboard_waits_on_a_verdict_before_anything_else(self) -> None:
        mockups = self.root / "specs/001-demo/mockups"
        mockups.mkdir(parents=True)
        (self.root / "specs/001-demo/spec.md").write_text("# Demo\n", encoding="utf-8")
        (mockups / "discover.html").write_text("<p>drawn</p>", encoding="utf-8")
        said = upstream.on_voyage(board(self.root), {}, {"drawable": True})
        self.assertEqual(said["text"], "The storyboard for 001-demo is drawn: approve it or send it back")
        self.assertEqual(said["href"], "#tab-screens")
        # Not while a stage of this board is still running: what it draws is not there to judge yet.
        running = board(self.root, [], done=False)
        self.assertEqual(upstream.on_voyage(running, {}, {})["count"], 0)

    def test_cards_and_parks_are_counted_each_and_the_card_is_said_first(self) -> None:
        turns = [{"role": "agent", "kind": "permission", "text": "Write spec.md", "ask": {"id": "p1"}},
                 {"role": "agent", "kind": "question", "text": "Which zone?", "ask": {"id": "q2"}},
                 {"role": "agent", "kind": "answered", "text": "", "ask": {"id": "p1"}}]
        fleet = {"groups": [{"paused": "no"}, {"paused": "yes"}], "inbox": [{"kind": "question", "grouped": "no"}]}
        said = upstream.on_voyage(board(self.root, turns), fleet, {"launchable": True})
        self.assertEqual(said["count"], 4, "one open card, one park, one question, and the button")
        self.assertEqual(said["text"], "The agent asks you something")
        self.assertEqual(said["href"], "#stage-asks")

    def test_the_approved_storyboard_waits_on_the_build_then_the_split_waits_to_be_cast_off(self) -> None:
        self.assertEqual(upstream.on_voyage(board(self.root), {}, {"launchable": True})["href"], "#launch")
        self.assertEqual(upstream.on_voyage(board(self.root), {}, {"modelable": True, "launchable": True})["href"],
                         "#model")
        self.assertEqual(upstream.on_voyage(board(self.root), {}, {"castable": True})["text"],
                         "The chart is split: cast off the fleet")


class ShellTest(unittest.TestCase):
    def test_a_served_page_carries_the_strip_and_the_switch_and_the_published_copy_neither(self) -> None:
        served = page_shell.document("Voyage", "", "<p>body</p>", "", now="/voyage")
        self.assertIn('id="waiting" hidden', served)
        self.assertIn('id="tell-me" hidden', served)
        self.assertIn("window.waiting = {set(said)", served)
        published = page_shell.document("Voyage", "", "<p>body</p>", "")
        self.assertNotIn('id="waiting"', published)
        self.assertNotIn("tell-me", published)


if __name__ == "__main__":
    unittest.main()
