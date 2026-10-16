"""A run is watched in a window of its own, and a window is a seat.

The board served one directory for as long as it kept `root` on its handler class: a second window looked
wherever the first had pointed it, and a generate in one tab moved every other tab with it. These are the
four things that follow from fixing that — a seat per window, a bar that is the run\'s and not the board\'s,
the way to stop what is being watched, and who answers at each of its stops.

Driven against `board_fixture`, which `test_bridge` is driven against too: one fixture, two subjects.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai.project.cruise import cruise_config
from slipwai.seats import SEATS


class SeatTest(BoardTest):
    """A window each. One board served one directory for as long as it kept `root` on its handler class:
    a second window opened on the same board looked wherever the first had pointed it, and a generate in
    one moved the other. A seat is a window, and where it is looking is the one thing it owns."""

    def test_a_page_asked_for_without_a_seat_is_answered_with_one(self) -> None:
        """Minted by the server and carried in the address bar, which is the only place a window keeps
        something that a second window does not inherit."""
        asked = urllib.request.urlopen(self.at("/", seat=""), timeout=5)
        with asked:
            self.assertEqual(asked.status, 200)
        self.assertIn("seat=", asked.url, "the window was sent to an address of its own")
        self.assertNotEqual(asked.url.partition("seat=")[2], "")

    def test_two_windows_look_where_each_was_pointed_and_not_where_the_other_was(self) -> None:
        """The fault this is all for: a second window that showed the first one's project."""
        elsewhere = Path(tempfile.mkdtemp())
        self.assertEqual(self.post("/attach", {"root": str(elsewhere)}, seat="window-two")[0], 200)
        self.assertIn(str(elsewhere.resolve()), self.get("/", seat="window-two")[1])
        self.assertIn(str(self.root.resolve()), self.get("/")[1], "the first window did not move")

    def test_a_seat_this_board_has_never_seen_is_a_new_window_rather_than_a_refusal(self) -> None:
        """A board restarted under an open window answers its reload, because a refusal is the one thing
        a person sitting in front of a page cannot act on."""
        code, said = self.get("/", seat="never-issued")
        self.assertEqual(code, 200)
        self.assertIn(str(self.root.resolve()), said, "a new window starts where the board was started")

    def test_a_window_can_be_opened_straight_onto_a_named_project(self) -> None:
        """How a voyage gets a window of its own: the link names the tree, the seat arrives pointed at it,
        and the name is gone from the address afterwards."""
        elsewhere = Path(tempfile.mkdtemp())
        asked = urllib.request.urlopen(self.at(f"/?look={elsewhere}", seat=""), timeout=5)
        with asked:
            said = asked.read().decode("utf-8")
        self.assertIn(str(elsewhere.resolve()), said)
        self.assertIn("seat=", asked.url)
        self.assertNotIn("look=", asked.url, "read once, by a seat that did not exist yet")

    def test_a_look_at_something_that_is_not_a_directory_opens_the_harbour_instead(self) -> None:
        """A blank window with a sentence in it is not an answer anybody can act on; a board with its
        Looking at box in it is."""
        with urllib.request.urlopen(self.at("/?look=/nowhere/at/all", seat=""), timeout=5) as asked:
            self.assertIn(str(self.root.resolve()), asked.read().decode("utf-8"))

    def test_a_request_carrying_no_seat_still_reads_the_board_it_was_started_on(self) -> None:
        """`curl /board.json` and every poller written before windows had names. A data route is not
        redirected into a seat it would then have to keep."""
        code, said = self.get("/board.json", seat="")
        self.assertEqual(code, 200)
        self.assertIn("berths", json.loads(said), "the board the server was started on, not a redirect")

    def test_the_board_lets_go_of_its_oldest_windows_rather_than_holding_every_one_forever(self) -> None:
        """A login service keeps this running for a month. Letting one go costs nothing a person sees:
        the window is given a new seat at the directory the board was started in."""
        for number in range(SEATS + 5):
            self.get("/board.json", seat=f"window-{number}")
        self.assertLessEqual(len(self.seats()), SEATS)
        self.assertEqual(self.get("/", seat="window-0")[0], 200)

    def test_looking_at_a_project_is_not_a_reason_to_remember_it(self) -> None:
        """A board a login service has kept running is pointed at a lot of trees. Only the ones something
        was started in are held, or a record of nothing accumulates per window per harbour."""
        outfits = self.server.RequestHandlerClass.bench.outfits  # type: ignore[attr-defined]
        for number in range(5):
            where = Path(tempfile.mkdtemp())
            self.post("/attach", {"root": str(where)}, seat=f"window-{number}")
            self.get("/voyage", seat=f"window-{number}")
        self.assertEqual(outfits, {}, "nothing has been started in any of them")


class StopTest(BoardTest):
    """The pair of Cast off. A run a person cannot end from the page they are watching it on is a run that
    sends them back to a terminal to find the right one, which is the friction this board exists to remove."""

    def test_there_is_nothing_to_stop_where_no_captain_is_running(self) -> None:
        code, said = self.post("/stop", {})
        self.assertEqual(code, 400)
        self.assertIn("nothing to stop", said)
        self.assertFalse(json.loads(self.get("/voyage.json")[1])["stoppable"])
        self.assertIn('id="stop"', self.get("/voyage")[1], "on the card, hidden, so the poll can show it")

    def test_a_running_fleet_can_be_asked_to_stop_from_the_page(self) -> None:
        """Asked, not killed: `make cruise-stop` is `fleet.py stop`, and a captain finishes the stage it is
        on. A captain killed mid-stage leaves a worktree half written with nothing saying so."""
        running = self.root / ".slipwai/running"
        running.mkdir(parents=True)
        (running / "ORD.pid").write_text(str(os.getpid()), encoding="utf-8")
        (self.root / "Makefile").write_text("cruise-stop:\n\t@echo 'every captain asked'\n", encoding="utf-8")
        self.assertTrue(json.loads(self.get("/voyage.json")[1])["stoppable"])
        self.assertEqual(self.post("/stop", {}), (200, "asking the fleet to stop"))
        for _ in range(100):
            receipt = json.loads(self.get("/init.json")[1])
            if receipt["done"]:
                break
            time.sleep(0.1)
        self.assertIn("every captain asked", receipt["lines"])
        self.assertIn("asked to stop", "\n".join(receipt["lines"]))

    def test_a_second_stop_while_the_first_is_still_asking_is_refused(self) -> None:
        """Two asks and one answer would read as a button that did nothing."""
        running = self.root / ".slipwai/running"
        running.mkdir(parents=True)
        (running / "ORD.pid").write_text(str(os.getpid()), encoding="utf-8")
        (self.root / "Makefile").write_text("cruise-stop:\n\t@sleep 2\n", encoding="utf-8")
        self.assertEqual(self.post("/stop", {})[0], 200)
        self.assertEqual(self.post("/stop", {})[0], 400)


class DrawTest(BoardTest):
    """The stage between a specification and a model, which had no button at all.

    The page said "Next: /mockups in the agent" to somebody sitting in front of a board that had just run
    two headless sessions for them. This runs the half of that stage nobody has to be present for, and
    stops where the stage actually is: a person looking at a storyboard.
    """

    def specified(self) -> None:
        (self.root / "specs/001-ordering").mkdir(parents=True)
        (self.root / "specs/001-ordering/spec.md").write_text("# Ordering\n", encoding="utf-8")

    def test_there_is_nothing_to_draw_without_a_specification(self) -> None:
        """The surfaces are drawn from the specification, so there is nothing to draw them from."""
        code, said = self.post("/draw", {})
        self.assertEqual(code, 400)
        self.assertIn("nothing to draw", said)
        self.assertFalse(json.loads(self.get("/voyage.json")[1])["drawable"])
        self.assertIn('id="draw"', self.get("/voyage")[1], "on the card, hidden, so the poll can show it")

    def test_a_drafted_specification_can_have_its_surfaces_drawn_from_the_page(self) -> None:
        self.specified()
        self.assertTrue(json.loads(self.get("/voyage.json")[1])["drawable"])
        (self.root / "Makefile").write_text("surfaces:\n\t@echo 'storyboard drawn'\n", encoding="utf-8")
        self.assertEqual(self.post("/draw", {}), (200, "drawing the surfaces"))
        for _ in range(100):
            receipt = json.loads(self.get("/init.json")[1])
            if receipt["done"]:
                break
            time.sleep(0.1)
        self.assertIn("storyboard drawn", receipt["lines"])
        self.assertIn("surfaces", receipt["step"])

    def test_surfaces_already_drawn_are_waiting_on_a_person_rather_than_on_this(self) -> None:
        """The button goes the moment there are drawings, because what they wait on is a verdict on each
        state and no button gives one. Pressing it again would redraw the thing being read."""
        self.specified()
        mockups = self.root / "specs/001-ordering/mockups"
        mockups.mkdir()
        (mockups / "basket.html").write_text("<title>Mock: Basket</title>", encoding="utf-8")
        self.assertFalse(json.loads(self.get("/voyage.json")[1])["drawable"])
        code, said = self.post("/draw", {})
        self.assertEqual(code, 400)
        self.assertIn("your verdict", said)


class ShapeTest(BoardTest):
    """A window stays current without anybody reloading it.

    The strip repaints from the poll and always did; the cards do not. A window opened while `make draft`
    ran watched the specification land and showed nothing of it — no Open spec button, no storyboard, no
    work — until somebody pressed reload, which is the one thing a page that polls is there to save them.
    """

    def shape_of(self, page: str) -> str:
        found = re.search(r'id="passage" data-shape="([^"]*)"', page)
        assert found is not None, "the card carries the signature it was drawn with"
        return found.group(1)

    def test_the_page_and_the_poll_agree_on_what_the_page_is_made_of(self) -> None:
        """They have to: a disagreement is a window that reloads itself for ever."""
        self.assertEqual(self.shape_of(self.get("/voyage")[1]),
                         json.loads(self.get("/voyage.json")[1])["shape"])

    def test_a_specification_landing_under_an_open_window_changes_the_signature(self) -> None:
        before = json.loads(self.get("/voyage.json")[1])["shape"]
        (self.root / "specs/001-ordering").mkdir(parents=True)
        (self.root / "specs/001-ordering/spec.md").write_text("# Ordering\n", encoding="utf-8")
        self.assertNotEqual(json.loads(self.get("/voyage.json")[1])["shape"], before)
        self.assertEqual(self.shape_of(self.get("/voyage")[1]),
                         json.loads(self.get("/voyage.json")[1])["shape"],
                         "and the window that reloads on it is drawn with the new one")

    def test_a_surface_drawn_under_an_open_window_changes_the_signature(self) -> None:
        """The storyboard card is rendered once, out of files the window was opened before."""
        mockups = self.root / "specs/001-ordering/mockups"
        mockups.mkdir(parents=True)
        before = json.loads(self.get("/voyage.json")[1])["shape"]
        (mockups / "basket.html").write_text("<title>Mock: Basket</title>", encoding="utf-8")
        self.assertNotEqual(json.loads(self.get("/voyage.json")[1])["shape"], before)

    def test_nothing_changing_leaves_the_signature_alone(self) -> None:
        """The other half of the rule, and the one that keeps a window from reloading every eight seconds."""
        first = json.loads(self.get("/voyage.json")[1])["shape"]
        self.assertEqual(json.loads(self.get("/voyage.json")[1])["shape"], first)

    def test_a_screenshot_landing_under_an_open_window_changes_the_signature(self) -> None:
        """The built-screens card is rendered once, out of files the window was opened before. A note
        beside a screenshot is not one of those files: it does not redraw the page."""
        design = self.root / "specs/001-ordering/slices/S01/design"
        design.mkdir(parents=True)
        before = json.loads(self.get("/voyage.json")[1])["shape"]
        (design / "home.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        landed = json.loads(self.get("/voyage.json")[1])["shape"]
        self.assertNotEqual(landed, before)
        self.assertEqual(self.shape_of(self.get("/voyage")[1]), landed,
                         "and the window that reloads on it is drawn with the new one")
        (design / "notes.md").write_text("looked at it\n", encoding="utf-8")
        self.assertEqual(json.loads(self.get("/voyage.json")[1])["shape"], landed)
        (design / "home.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff")
        self.assertNotEqual(json.loads(self.get("/voyage.json")[1])["shape"], landed)


class WheelRouteTest(BoardTest):
    """The board's half of who answers: the stops are shown on the run's own window, and a press runs the
    project's own writer. `test_wheel` holds the reading and the writing; this holds the route."""

    def test_a_stop_is_answered_from_the_page_through_the_project_s_own_script(self) -> None:
        (self.root / ".specify").mkdir()
        (self.root / ".specify/cruise.json").write_text(cruise_config(), encoding="utf-8")
        (self.root / "scripts/agents").mkdir(parents=True)
        (self.root / "scripts/agents/cruise.py").write_text(
            'import pathlib, sys\npathlib.Path("asked.txt").write_text(" ".join(sys.argv[1:]))\n',
            encoding="utf-8")
        said = self.get("/voyage")[1]
        self.assertIn('data-dial="cruise" data-key="unblock"', said)
        self.assertIn("Nothing here stops for you", said)
        self.assertIn('for="tab-answers"', said, "a tab of the settings box, beside Speed")
        self.assertEqual(self.post("/wheel", {"stop": "unblock", "value": "park"}),
                         (200, "unblock = park"))
        self.assertEqual((self.root / "asked.txt").read_text(encoding="utf-8"), "--set unblock=park")

    def test_a_stop_this_board_does_not_draw_is_refused(self) -> None:
        code, said = self.post("/wheel", {"stop": "model", "value": "gpt-9"})
        self.assertEqual(code, 400)
        self.assertIn("not a stop this board sets", said)

    def test_a_harbour_with_no_cruise_answers_carries_no_tab(self) -> None:
        """A tab offering to set a file that is not there would be a control that refuses every press."""
        said = self.get("/voyage")[1]
        self.assertNotIn('for="tab-answers"', said)
        self.assertIn('for="tab-speed"', said, "the telegraph's tabs are the board's own and always there")


class RunWindowTest(BoardTest):
    """A run is a window, not a tab. The board is where a person starts, adopts and installs; a voyage is
    the one product they are watching, and a tab is a thing they lose by pressing Packages."""

    def test_the_board_s_bar_does_not_carry_the_voyage(self) -> None:
        said = self.get("/")[1]
        for name in ("Start a project", "Adopt a repository", "Packages"):
            self.assertIn(f">{name}</a>", said)
        self.assertNotIn(">Voyage</a>", said)

    def test_the_way_to_a_run_names_its_project_and_opens_its_own_window(self) -> None:
        said = self.get("/")[1]
        self.assertNotIn("/voyage?look=", said, "this directory is a harbour and has no project in it")
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        said = self.get("/")[1]
        self.assertIn(f'href="/voyage?look={quote(str(self.root.resolve()))}"', said)
        self.assertIn('target="_blank"', said)

    def test_a_run_window_carries_one_way_back_and_it_opens_its_own_window_too(self) -> None:
        """A run window that navigated itself to the board would be a run nobody is watching."""
        said = self.get("/voyage")[1]
        self.assertIn('<a href="/" target="_blank"', said)
        for name in ("Start a project", "Adopt a repository", "Packages"):
            self.assertNotIn(f">{name}</a>", said, "a run window is not the board with a tab selected")


class BuiltScreenRouteTest(BoardTest):
    """The picture the page shows is the file the review wrote, bytes unchanged."""

    def test_a_screenshot_on_the_voyage_is_served_as_itself(self) -> None:
        feature = self.root / "specs/001-demo"
        design = feature / "slices/S01/design"
        design.mkdir(parents=True)
        png = b"\x89PNG\r\n\x1a\n\xff\xfe"
        (design / "home.png").write_bytes(png)
        (design / "notes.md").write_text("private\n", encoding="utf-8")
        (feature / "mockups").mkdir()
        (feature / "mockups/catalog.html").write_text(
            "<html><head><title>Mock: catalog</title></head></html>", encoding="utf-8")
        (self.root / "project.json").write_text(
            '{"deployables":{"api":{"kind":"service","port":3000},"web":{"kind":"web","port":5173}}}',
            encoding="utf-8")
        said = self.get("/voyage")[1]
        card = said[said.index('id="built"'):said.index("<h2>The work</h2>")]
        self.assertIn("Built screens", card)
        self.assertIn("To do", card)
        self.assertIn(f"/screens/001-demo/S01/home.png?seat={self.seat}", card)
        self.assertIn("/mockups/001-demo/catalog.html", card)
        self.assertIn('href="http://localhost:5173"', card)
        self.assertNotIn("<h2>Mockups", said)
        with urllib.request.urlopen(self.at("/screens/001-demo/S01/home.png"), timeout=5) as answer:
            self.assertEqual(answer.headers.get_content_type(), "image/png")
            self.assertEqual(answer.read(), png)
        for asked in ("/screens/001-demo/S01/../../../../harbour.json",
                      "/screens/001-demo/S01/notes.md"):
            with self.subTest(asked=asked), self.assertRaises(urllib.error.HTTPError) as refused:
                self.get(asked)
            refused.exception.close()
            self.assertEqual(refused.exception.code, 404, asked)


if __name__ == "__main__":
    unittest.main()
