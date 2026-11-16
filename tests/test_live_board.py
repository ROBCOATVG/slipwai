"""The board keeps itself current: one read shared by every poll, one poll for the page, one list of what
waits on a person, a strip that says only what is wrong, a compact view of the work, and a Fleet tab that is
the machinery.

The pure parts are driven with the rows the fold would make; the routes against `board_fixture`.
"""
from __future__ import annotations

import json
import re
import tempfile
import unittest
import urllib.error
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import attention, board_read, logs, shell_environment, voyage_page
from slipwai.fleet_tab import fleet_tab
from slipwai.live_page import look_html
from slipwai.on_you import waiting
from slipwai.voyage_page import signature, work_card

NOW = datetime.now(UTC)


def stamp(minutes: float = 0) -> str:
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def row(slice_id: str, state: str, **more: str) -> dict[str, str]:
    return {"slice": slice_id, "title": "", "state": state, "fairway": "game-nights", "feature": "001-demo",
            "why": "", "clearance": "running", **more}


def idle(root: Path) -> SimpleNamespace:
    """A board with nothing of its own running: no stage, so no cards and no button of a stage's."""
    return SimpleNamespace(root=root, fitting=None)


class KeptReadTest(unittest.TestCase):
    """Every poll read the run from the start; now a project is read once and the read shared for a while."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.made = 0
        board_read.forget()

        def fold(root: Path) -> board_read.Read:
            self.made += 1
            return board_read.Read([], "", {}, {}, {}, [], {})
        patched = mock.patch.object(board_read, "fold", fold)
        patched.start()
        self.addCleanup(patched.stop)
        self.addCleanup(board_read.forget)

    def test_polls_inside_two_seconds_are_answered_by_one_read(self) -> None:
        first = board_read.read(self.root)
        self.assertIs(board_read.read(self.root), first)
        self.assertEqual(self.made, 1)

    def test_a_person_s_action_drops_the_read_and_the_next_poll_reads_again(self) -> None:
        board_read.read(self.root)
        board_read.forget(self.root)
        board_read.read(self.root)
        self.assertEqual(self.made, 2)

    def test_a_read_made_while_a_person_acted_is_not_kept_after_it(self) -> None:
        """Begun before the action and finished after it, it would show what they did undone for two seconds."""
        def acted_meanwhile(root: Path) -> board_read.Read:
            self.made += 1
            board_read.forget(root)
            return board_read.Read([], "", {}, {}, {}, [], {})
        with mock.patch.object(board_read, "fold", acted_meanwhile):
            board_read.read(self.root)
            board_read.read(self.root)
        self.assertEqual(self.made, 2)

    def test_a_suite_can_ask_for_every_read_fresh(self) -> None:
        with mock.patch.object(board_read, "KEEP", 0.0):
            board_read.read(self.root)
            board_read.read(self.root)
        self.assertEqual(self.made, 2)


class OneAskTest(unittest.TestCase):
    """Inside the read, the clearance script once per feature and the login shell once per board process."""

    def test_the_columns_and_the_berths_share_one_answer_from_the_clearance_script(self) -> None:
        root = Path(tempfile.mkdtemp())
        (root / "specs/001-demo").mkdir(parents=True)
        (root / "specs/001-demo/chart.yaml").write_text("slices: []\n", encoding="utf-8")
        asked = []

        def ask(where: Path, feature: str) -> tuple[str, dict, str]:
            asked.append(feature)
            return feature, {"v": 1, "feature": feature, "states": {}, "ready": {}}, ""
        with mock.patch("slipwai.fleet.asked_of", ask):
            board_read.fold(root)
        self.assertEqual(asked, ["001-demo"])

    def test_the_login_shell_is_asked_once_while_the_board_keeps_its_answer(self) -> None:
        asked = []

        def login(command: str) -> dict[str, str]:
            asked.append(command)
            return {"PATH": "/from/login"}
        with mock.patch.object(shell_environment, "login_of", login), \
                mock.patch.dict(shell_environment.ANSWERED, clear=True):
            token = shell_environment.KEEP_LOGIN.set(True)
            try:
                for _ in range(3):
                    self.assertIn("/from/login", shell_environment.login_environment()["PATH"])
            finally:
                shell_environment.KEEP_LOGIN.reset(token)
            shell_environment.login_environment()
        self.assertEqual(len(asked), 2, "once kept for the board; a caller outside its read asks afresh")


class WaitingListTest(unittest.TestCase):
    """One list in two groups, read by the strip, the tab's count and the column alike."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())

    def test_a_slice_parked_on_you_holds_work_up_and_a_paused_one_or_a_note_is_not_counted(self) -> None:
        rows = [row("GN6", "waiting", title="Remind the night before", asked="Q1: Everyone?"),
                row("GN5", "queued", paused="21:40")]
        fleet = {"inbox": [{"kind": "told", "fairway": "game-nights", "what": "fyi", "t": stamp()}]}
        found = waiting(idle(self.root), fleet, {}, rows)
        self.assertEqual(found["count"], 1)
        self.assertEqual(found["holding"][0]["text"], "GN6 · Remind the night before: 1 question open")
        self.assertEqual(found["holding"][0]["href"], "#card-GN6")
        self.assertEqual(found["slices"], ["GN6"])

    def test_a_capability_to_look_at_and_a_proposal_to_confirm_wait_until_you_have_time(self) -> None:
        home = self.root / "docs/feedback"
        home.mkdir(parents=True)
        (home / "0001-say-who-sent-it.md").write_text("---\ntitle: Say who sent it\nproposed: 2026-11-16\n"
                                                     "route: change\n---\nThe invite should say who sent it.\n",
                                                     encoding="utf-8")
        found = waiting(idle(self.root), {"demo_due_in": {"Sign in and join": "accounts"}}, {"castable": True})
        self.assertEqual([one["text"] for one in found["later"]],
                         ["Sign in and join is ready for your verdict",
                          "A piece of feedback has a proposed route to confirm"])
        self.assertEqual([one["text"] for one in found["holding"]], ["The chart is split: cast off the fleet"])
        self.assertEqual(found["count"], 3)

    def test_the_column_draws_exactly_the_slices_the_list_names(self) -> None:
        rows = [row("GN6", "waiting", park="Which night?"), row("GN3", "working")]
        listed = waiting(idle(self.root), {}, {}, rows)
        card = work_card(rows, "", set(listed["slices"]))
        column = card[card.index('id="col-waiting"'):card.index('id="col-done"')]
        self.assertIn("Waiting on you · 1", column)
        self.assertIn('data-card="GN6"', column)

    def test_the_tab_s_count_is_the_list_s_count(self) -> None:
        listed = {"count": 2, "text": "x", "href": "#", "holding": [], "later": [], "slices": []}
        html = voyage_page.page(self.root, [], [], "", "", "", "", None, False, waiting=listed)
        self.assertIn('data-waiting-count>2 waiting</span>', html)
        self.assertNotIn("waiting</span></button><button", html.split('data-tab="fleet"')[-1][:80])

    def test_the_strip_opens_on_both_groups_and_draws_each_item_as_text(self) -> None:
        self.assertIn("<b>Holding work up</b>", attention.STRIP)
        self.assertIn("<b>When you have time</b>", attention.STRIP)
        self.assertIn("link.textContent = item.text", attention.SCRIPT, "a stream's words are never markup")


class NeedsALookTest(unittest.TestCase):
    """The Now strip was every working slice; the card says that now, and the strip says what is wrong."""

    def test_a_red_trunk_comes_first_then_a_slice_going_in_circles_each_linked_to_where_to_look(self) -> None:
        rows = [row("CL2", "working", stage="Review"), row("GN4", "working", stage="Demo"), row("AC5", "working")]
        folds = {"game-nights/CL2": {"warnings": [{"kind": "circles", "level": "red",
                                                   "said": "failed 3 times running: npm test"}]},
                 "game-nights/GN4": {"warnings": [{"kind": "shared", "level": "red", "said": "waiting too"}]}}
        drawn = look_html(rows, folds, {"state": "red", "t": stamp(6), "why": "lint failed"})
        self.assertIn("Needs a look · 2", drawn)
        self.assertLess(drawn.index("Trunk is red"), drawn.index("CL2 · Review"))
        self.assertIn("Going in circles: failed 3 times running: npm test", drawn)
        self.assertIn('href="#card-CL2">Open its card</a>', drawn)
        self.assertNotIn("GN4", drawn, "only stuck, circling and quiet are the strip's")
        self.assertNotIn('class="did"', drawn, "what its captain did goes here once captains decide")

    def test_a_refused_merge_needs_a_look(self) -> None:
        drawn = look_html([row("TB2", "working", stage="Merge refused", refused="trunk moved on")], {}, {})
        self.assertIn("Merge refused: trunk moved on", drawn)

    def test_nothing_wrong_is_one_line(self) -> None:
        rows = [row(f"S{n}", "working") for n in range(5)]
        drawn = look_html(rows, {}, {"state": "green", "t": stamp(), "why": ""})
        self.assertIn("<b>5 working</b> · nothing needs a look", drawn)
        self.assertNotIn('class="look', drawn)
        self.assertEqual(look_html([row("S1", "done")], {}, {}), "", "nothing in flight, nothing to say")


class CompactTest(unittest.TestCase):
    def test_compact_is_a_line_a_slice_in_flight_waiting_first_each_opening_its_card(self) -> None:
        rows = [row("GN3", "working", stage="Implementing", live="T012 · Style it"),
                row("GN6", "waiting", park="Which night? It matters."), row("GN1", "done")]
        card = work_card(rows, "")
        compact = card[card.index('class="compact"'):]
        self.assertLess(compact.index("GN6"), compact.index("GN3"))
        self.assertNotIn("GN1", compact)
        self.assertIn('href="#card-GN6" data-open-card="GN6"', compact)
        self.assertIn('data-view-pick="compact">Compact</button>', card)

    def test_the_choice_is_remembered_in_this_browser_and_a_private_window_does_not_break_it(self) -> None:
        script = voyage_page.SCRIPT
        self.assertIn("localStorage.setItem('voyage-work-view', name); } catch (fault) {}", script)
        self.assertIn("try { const kept = localStorage.getItem('voyage-work-view')", script)


class FleetTabTest(unittest.TestCase):
    FLEET = {"counts": {"running": 2, "slots": 3}, "bunker": {"today": 620, "allowed": 1000},
             "processes": [{"name": "harbourmaster", "role": "harbourmaster", "fairway": "", "state": "running"},
                           {"name": "captain-game-nights", "role": "captain", "fairway": "game-nights",
                            "state": "running"}],
             "berths": [{"fairway": "game-nights", "state": "working", "slice": "GN3"}],
             "streams": {"game-nights": [(stamp(1), "GN3 heartbeat")]},
             "feed": [(stamp(2), "harbour", "granted")]}

    def test_it_is_slots_tokens_trunk_and_a_row_per_process_and_never_a_row_per_slice(self) -> None:
        drawn = fleet_tab(self.FLEET, [row("GN5", "queued")], {"state": "red", "t": stamp(6), "why": "lint"}, True)
        self.assertIn("<b>2 of 3</b><span>1 slot free · GN5 takes it</span>", drawn)
        self.assertIn("<b>620k of 1,000k</b>", drawn)
        self.assertIn("Merges are held until it is green: lint", drawn)
        self.assertIn("<b>Captain · game-nights</b>", drawn)
        self.assertIn("GN3 heartbeat", drawn)
        self.assertIn("granted", drawn, "the harbourmaster's last line")
        self.assertIn("data-fleet-stop>Stop the fleet", drawn)
        self.assertNotIn("Piece of work", drawn)


class OnePollTest(BoardTest):
    """One request answers for every band, and the page asks for nothing else."""

    def test_the_poll_carries_every_band_and_the_page_was_drawn_with_the_same_signatures(self) -> None:
        found = json.loads(self.get("/live.json")[1])
        self.assertEqual(set(found["bands"]), {"look", "points", "work", "streams", "expect", "fleet", "captains"})
        page = self.get("/voyage")[1]
        for name, band in found["bands"].items():
            with self.subTest(band=name):
                held = re.search(rf'data-band="{name}" data-said="([^"]*)"', page)
                assert held is not None
                self.assertEqual(held.group(1), band["said"], "a first poll that swapped would flicker")
                self.assertEqual(signature(band["html"]), band["said"])
        self.assertEqual(set(found["passage"]), set(json.loads(self.get("/voyage.json")[1])))

    def test_a_note_landing_moves_its_band_and_no_other(self) -> None:
        before = json.loads(self.get("/live.json")[1])["bands"]
        self.deck("ORD", logs.entry("told", fairway="ORD", message="a note for you"))
        after = json.loads(self.get("/live.json")[1])["bands"]
        self.assertNotEqual(before["streams"]["said"], after["streams"]["said"])
        self.assertIn("a note for you", after["streams"]["html"])
        self.assertEqual(before["expect"]["said"], after["expect"]["said"])

    def test_the_old_polls_are_gone_and_the_page_asks_for_the_one(self) -> None:
        page = self.get("/voyage")[1]
        self.assertIn("fetch('/live.json')", page)
        for gone in ("/now.json", "/work.json"):
            self.assertNotIn(gone, page)
            with self.subTest(gone=gone), self.assertRaises(urllib.error.HTTPError) as refused:
                self.get(gone)
            refused.exception.close()
            self.assertEqual(refused.exception.code, 404)

    def test_a_post_drops_the_kept_read_so_the_next_poll_shows_what_was_done(self) -> None:
        with mock.patch.object(board_read, "KEEP", 60.0):
            self.get("/live.json")
            self.post("/talk/all", {"message": "told from the page"})
            self.assertIn("told from the page", json.loads(self.get("/live.json")[1])["bands"]["captains"]["html"])


if __name__ == "__main__":
    unittest.main()
