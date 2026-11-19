"""A slice's card: closed, where it stands on the ladder; opened, how it got there.

Each case builds the row the fold would and reads the card, so nothing here needs a repository or a run.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401

from slipwai.activity import caption
from slipwai.slice_card import lit, slice_html
from slipwai.slice_rungs import LADDER, ladder
from slipwai.voyage_page import signature, work_card


def steps(at: int, began: float = 0.0, took: float = 0.0) -> str:
    return json.dumps([{"name": name, "state": "done" if index < at else "now" if index == at else "todo",
                        "began": began if index <= at else 0, "took": took if index <= at else 0}
                       for index, name in enumerate(LADDER)])


def row(**more: str) -> dict[str, str]:
    return {"slice": "GN3", "title": "Say you'll bring it", "state": "working", "fairway": "game-nights",
            "feature": "001-demo", "why": "claimed", "clearance": "running", "stage": "Implementing",
            "chip": "Implementing · 11/15", "tasks": "11/15", "ladder": steps(2, 1763290000.0, 720.0), **more}


class ClosedCardTest(unittest.TestCase):
    def test_a_slice_at_work_is_six_steps_the_one_it_is_on_and_what_is_still_to_come(self) -> None:
        card = slice_html(row())
        summary = card[card.index("<summary>"):card.index("</summary>")]
        self.assertEqual(summary.count('class="rung done"'), 2)
        self.assertIn('<span class="rung now part"><i style="width:73%"></i></span>', summary)
        self.assertIn("<b>Build · 11 of 15 tasks</b><span>then Demo, Review, Merge</span>", summary)
        self.assertNotIn('class="chip"', summary, "the strip says the stage, so the chip would say it twice")

    def test_a_word_the_step_s_name_does_not_cover_is_said_beside_it(self) -> None:
        card = slice_html(row(stage="Held · trunk red", chip="Held · trunk red", ladder=steps(5), tasks=""))
        self.assertIn("<b>Merge · held · trunk red</b>", card)

    def test_a_queued_slice_keeps_its_word_and_shows_how_far_it_had_got(self) -> None:
        card = slice_html(row(state="queued", stage="Planning", chip="Planning", tasks="", ladder=steps(1)))
        self.assertIn('<span class="chip">Queued</span>', card)
        self.assertIn("<b>Plan</b>", card)

    def test_a_slice_still_to_do_or_done_has_no_strip(self) -> None:
        self.assertNotIn('class="rungs"', slice_html(row(state="done")))
        self.assertNotIn('class="rungs"', slice_html(row(state="todo")))


class OpenedCardTest(unittest.TestCase):
    def test_each_step_says_when_it_began_and_how_long_it_took(self) -> None:
        card = slice_html(row(live="T012 · Style the control · 5s ago",
                              feed=json.dumps([{"t": "2026-11-16T11:46:02Z", "kind": "ran", "what": "unit tests"}])))
        self.assertIn('<li class="done"><b>Examples</b>', card)
        self.assertIn("12m so far", card)
        self.assertIn("<b>Now:</b> T012 · Style the control · 5s ago", card)
        self.assertIn("<li>11:46 ran unit tests</li>", card)
        self.assertIn('href="/slice?fairway=game-nights&amp;slice=GN3"', card, "the live window is one click away")
        self.assertIn("<small>A review of the whole diff, every finding closed</small>", card)
        for gone in ("Clearance", "Last line", "On its branch"):
            self.assertNotIn(gone, card)

    def test_a_refused_merge_still_says_why_and_a_queued_slice_why_it_waits(self) -> None:
        self.assertIn("<dt>Merge refused</dt><dd>trunk is red</dd>", slice_html(row(refused="trunk is red")))
        self.assertIn("<dt>Why</dt><dd>waiting for a slot</dd>",
                      slice_html(row(state="queued", why="waiting for a slot")))

    def test_a_slice_in_a_film_links_to_its_chapter(self) -> None:
        films = [{"id": "film-bring-it", "title": "Bring it", "feature": "001-demo",
                  "chapters": [{"at": 0.0, "slice": "GN1"}, {"at": 48.2, "slice": "GN3"},
                               {"at": 60.0, "slice": "GN3"}]}]
        card = slice_html(lit([row(state="done")], {}, None, films)[0])
        self.assertIn("Chapter 2 of 2 · starts at 0:48", card)
        self.assertIn('<a href="#film-bring-it" data-film-at="48">Watch from this chapter</a>', card)


class CaptionTest(unittest.TestCase):
    FOLD = {"last_t": 1.0, "current": None, "waiting": "", "said": "", "last": "Read the berth memories"}

    def test_the_task_in_hand_is_said_before_anything_the_session_wrote_and_never_its_last_command(self) -> None:
        self.assertTrue(caption(self.FOLD, "T012 · Style the control").startswith("T012 · Style the control · "))
        self.assertTrue(caption({**self.FOLD, "said": "Tests are green"}).startswith("Tests are green · "))
        self.assertTrue(caption(self.FOLD).startswith("active · "), "a command is the window's to show")


class WorkPollTest(unittest.TestCase):
    def test_the_band_carries_a_signature_that_moves_when_a_card_does(self) -> None:
        first, second = work_card([row()], ""), work_card([row(tasks="12/15")], "")
        self.assertIn('id="work"', first)
        self.assertNotEqual(signature(first), signature(second))
        self.assertEqual(signature(first), signature(work_card([row()], "")))
        self.assertIn('data-card="GN3"', work_card([row()], ""), "the poll opens again what a person had open")


class LadderTest(unittest.TestCase):
    def test_the_step_is_the_chip_word_s_and_an_unknown_word_stands_where_the_evidence_has_reached(self) -> None:
        import tempfile
        from pathlib import Path

        root = Path(tempfile.mkdtemp())
        self.assertEqual([one["state"] for one in ladder(root, "f", "S1", "Review fixes", 4)],
                         ["done", "done", "done", "done", "now", "todo"])
        self.assertEqual([one["state"] for one in ladder(root, "f", "S1", "Fixing gate refusal", 4)][2], "now")

    def test_a_step_s_time_is_every_stage_bracketed_on_it(self) -> None:
        import tempfile
        from pathlib import Path

        root = Path(tempfile.mkdtemp()) / "project"
        record = root / "specs/f/slices/S1/benchmark.json"
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps({"stages": [
            {"stage": "implement-shipwright", "started": "2026-11-16T11:00:00Z", "ended": "2026-11-16T11:10:00Z"},
            {"stage": "review-mate", "started": "2026-11-16T11:10:00Z", "ended": "2026-11-16T11:14:00Z"},
            {"stage": "implement-shipwright", "started": "2026-11-16T11:14:00Z"}]}), encoding="utf-8")
        from slipwai.slice_rungs import instant

        found = ladder(root, "f", "S1", "Review fixes", 6, now=instant("2026-11-16T11:19:00Z"))
        self.assertEqual((found[2]["took"], found[4]["took"]), (900.0, 240.0))


if __name__ == "__main__":
    unittest.main()
