"""The bridge: the board as a page, and the three things a person can do to a run from it.

The point of the page is not that it is prettier than the terminal. It is that a person answers from one
seat — so the test that matters most is that an answer typed on the page becomes a line in the right
stream's own log, which is the file the captain reads at its next boundary.
"""
from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import checkout_packages  # noqa: F401
from board_fixture import BoardTest, Fixture

from slipwai import logs
from slipwai.bridge import serve
from slipwai.bridge_page import PLAIN, page, read_only
from slipwai.cli_fleet import config
from slipwai.deck import tell
from slipwai.fleet import board
from slipwai.project.harbour import START
from slipwai.telegraph import MEANS

# budget: 470 — every route the board answers, driven against `board_fixture`: the fleet pages, the
# controls, the tell, and the landing a generate leaves behind with the voyage it opens. What a run's own
# *window* is — a seat each, the stop, who answers — is `test_run_window`, which this stopped being able to
# hold; the fixture moved out with it rather than being copied, which is what the one-suite rule was for.


class TellTest(Fixture):
    def test_an_answer_becomes_a_told_line_in_that_stream_s_own_log(self) -> None:
        """The whole point of the page: a message somewhere else is a message nothing is watching."""
        tell(self.root, "ORD", "stop and talk to me")
        told = [e for e in self.read("ORD") if e.kind == "told"]
        self.assertEqual(len(told), 1)
        self.assertEqual(told[0].fields["message"], "stop and talk to me")

    def test_a_stream_with_no_log_says_so_rather_than_making_one(self) -> None:
        with self.assertRaises(ValueError) as refused:
            tell(self.root, "NOPE", "hello")
        self.assertIn("no log here", str(refused.exception))

    def test_an_empty_message_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            tell(self.root, "ORD", "   ")


class PageTest(Fixture):
    def test_every_label_is_the_plain_word_and_never_the_method_s(self) -> None:
        """The nautical names are the method's. Somebody reading a dashboard should not need a glossary."""
        said = self.rendered()
        for name in MEANS:
            with self.subTest(number=name):
                self.assertIn(PLAIN[name], said)
                self.assertNotIn(f">{name}<", said)

    def test_it_leads_with_what_is_waiting_on_a_person(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="look at this"))
        said = self.rendered()
        self.assertLess(said.index("Waiting on you"), said.index("Streams"))
        self.assertIn("look at this", said)
        # Clicking it opens the stream's own lines and a box to answer from, which becomes a `told`.
        self.assertIn("<details", said[said.index("Waiting on you"):said.index("Streams")])
        self.assertIn('data-tell="ORD" data-box="tell-wait-0"', said)

    def test_a_message_from_a_person_is_escaped_and_never_rendered_as_markup(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="<script>alert(1)</script>"))
        self.assertNotIn("<script>alert(1)</script>", self.rendered())

    def test_the_dial_shows_where_it_is_and_what_else_there_is(self) -> None:
        said = self.rendered()
        self.assertIn("Half ahead", said)
        self.assertIn("Dead slow", said)

    def test_the_read_only_copy_is_the_same_page_with_nothing_to_press(self) -> None:
        said = read_only(board(self.root, config(self.root)), config(self.root))
        self.assertNotIn("<button", said)
        self.assertNotIn("<script>", said)
        self.assertIn("Streams", said)


class ServerTest(BoardTest):
    """Every route the board answers, driven against one bound board."""

    def test_it_binds_this_machine_only(self) -> None:
        """The page changes what a run does; a default that put that on a shared network would be wrong
        once and then permanently."""
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_the_page_is_served(self) -> None:
        """The Board is the landing — looking at, where it stands, what can be started — and the live cards
        are on the Voyage tab, beside the stages and the model."""
        code, said = self.get("/")
        self.assertEqual(code, 200)
        self.assertIn("Start something", said)
        self.assertNotIn("<h2>Streams</h2>", said)
        code, said = self.get("/voyage")
        self.assertEqual(code, 200)
        self.assertIn("<h2>Streams</h2>", said)
        self.assertIn("<h2>Speed</h2>", said)
        self.assertIn('data-ring', said, "the controls came with the cards")

    def test_the_board_is_also_json_for_anything_that_would_rather_read_it(self) -> None:
        code, said = self.get("/board.json")
        self.assertEqual(code, 200)
        self.assertIn("berths", json.loads(said))

    def test_an_answer_posted_from_the_page_reaches_the_log(self) -> None:
        code, _ = self.post("/tell", {"fairway": "ORD", "message": "from the page"})
        self.assertEqual(code, 200)
        self.assertEqual([e.fields["message"] for e in self.read("ORD") if e.kind == "told"],
                         ["from the page"])

    def test_ringing_from_the_page_writes_the_same_file_the_verb_does(self) -> None:
        """A second path that wrote harbour.json its own way would be the first one to drift."""
        code, _ = self.post("/ring", {"position": "dead-slow"})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads((self.root / "harbour.json").read_text())["position"], "dead-slow")

    def test_setting_one_number_from_the_page_leaves_the_rest(self) -> None:
        self.post("/set", {"pairs": ["boilers=1"]})
        held = json.loads((self.root / "harbour.json").read_text())
        self.assertEqual(held["boilers"], 1)
        self.assertEqual(held["position"], START)

    def test_a_position_that_is_not_one_is_a_refusal_and_not_a_traceback(self) -> None:
        code, said = self.post("/ring", {"position": "flank"})
        self.assertEqual(code, 400)
        self.assertIn("full-ahead", said)

    def test_a_route_it_has_not_got_says_what_it_has(self) -> None:
        code, said = self.post("/anything", {})
        self.assertEqual(code, 404)


class ReadOnlyServerTest(Fixture):
    def test_the_published_copy_refuses_every_control(self) -> None:
        server = serve(self.root, "127.0.0.1", 0, controls=False)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        request = urllib.request.Request(f"http://127.0.0.1:{port}/tell", data=b"{}",
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(request, timeout=5).close()
            self.fail("a read-only copy accepted a control")
        except urllib.error.HTTPError as answer:
            with answer:
                self.assertEqual(answer.code, 403)


class TailTest(Fixture):
    """Every log on the board is a tail: bounded, scrolled, and open on its newest line.

    A log that grows the page a screen at a time pushes everything under it off the bottom, and one that
    opens at its oldest line makes a reader scroll to reach the part they came for. The height is CSS and
    the pinning is two lines of script; what is held here is that every log is marked for both.
    """

    def test_a_streams_own_log_is_one(self) -> None:
        self.deck("ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.assertIn('<ol class="lines" data-tail>', self.rendered())

    def test_the_event_feed_is_one(self) -> None:
        self.assertIn('<ul class="feed" data-tail>', self.rendered())

    def test_the_feed_shows_every_line_the_fold_carries_rather_than_the_last_fifteen(self) -> None:
        """What used to be cut to keep the page short is scrolled now."""
        for number in range(25):
            self.deck("ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark=f"Mark{number}"))
        held = config(self.root)
        found = board(self.root, held)
        shown = page(found, held).partition('<ul class="feed" data-tail>')[2].partition("</ul>")[0]
        folded = found["feed"]
        assert isinstance(folded, list)  # `board` answers with `object`, and this is the feed
        self.assertGreater(len(folded), 15)
        self.assertEqual(shown.count("<li>"), len(folded))

    def test_the_script_pins_each_of_them_to_the_bottom(self) -> None:
        said = self.rendered()
        self.assertIn("[data-tail]", said)
        self.assertIn("scrollHeight", said)


class AttachTest(BoardTest):
    """Where the board is looking, moved from the page instead of by restarting it with `--root`."""

    def test_the_page_says_which_directory_it_is_a_view_of(self) -> None:
        self.assertIn(str(self.root.resolve()), self.get("/")[1])

    def test_attaching_points_every_later_request_at_the_other_project(self) -> None:
        elsewhere = Path(tempfile.mkdtemp())
        code, said = self.post("/attach", {"root": str(elsewhere)})
        self.assertEqual(code, 200)
        self.assertIn(str(elsewhere.resolve()), said)
        self.assertIn(str(elsewhere.resolve()), self.get("/")[1])

    def test_a_directory_that_is_not_there_is_refused_and_the_board_stays_put(self) -> None:
        """An empty harbour at a path that does not exist would say nothing is running, which is the one
        wrong answer this page could give."""
        code, said = self.post("/attach", {"root": str(self.root / "nowhere")})
        self.assertEqual(code, 400)
        self.assertIn("not a directory", said)
        self.assertIn(str(self.root.resolve()), self.get("/")[1])

    def test_the_published_copy_has_nothing_to_attach_to(self) -> None:
        """It is one file on somebody's Pages site, and a view of nothing it could move to."""
        self.assertNotIn('id="attach"', read_only(board(self.root, config(self.root)), config(self.root)))


class LandingTest(BoardTest):
    """What a generate from the board leaves behind: a board looking at the project it just made.

    Generation itself is stubbed here. Driving the real verb needs a language package and takes a minute,
    `test_interview_page` already does it, and what this is about is the three lines after it worked —
    where the board is now pointed, what it carries, and what it will tell a poll.
    """

    def setUp(self) -> None:
        super().setUp()
        self.made = Path(tempfile.mkdtemp()) / "demo"
        self.made.mkdir()
        self.patch("generate", lambda answers, root: (True, f"created: {self.made}"))
        self.patch("destination", lambda answers, root: self.made)

    def patch(self, name: str, with_this: object) -> None:
        import slipwai.bridge as module
        held = getattr(module, name)
        setattr(module, name, with_this)
        self.addCleanup(setattr, module, name, held)

    def land(self) -> tuple[int, str]:
        return self.post("/generate/run", {"name": "demo", "init": "none"})

    def test_the_board_is_the_new_project_s_board_from_here(self) -> None:
        """The whole of attaching: a seat's root is read fresh on every request, so landing is one
        assignment — and it is made to the window that generated and to no other."""
        self.assertEqual(self.land()[0], 200)
        self.assertEqual(self.seats()[self.seat].root, self.made)

    def test_it_lands_with_the_receipt_for_what_it_made(self) -> None:
        self.land()
        code, said = self.get("/voyage")
        self.assertEqual(code, 200)
        self.assertIn("Made demo", said)
        self.assertIn(str(self.made), said)

    def test_a_poll_before_anything_was_made_is_a_finished_nothing(self) -> None:
        """The board carries the card's script whether or not there is a card; the route answers either way."""
        said = json.loads(self.get("/init.json")[1])
        self.assertEqual(said["lines"], [])
        self.assertTrue(said["done"])

    def test_the_tail_is_polled_for_what_came_after_the_lines_the_page_has(self) -> None:
        self.land()
        said = json.loads(self.get("/init.json")[1])
        self.assertIn(f"created: {self.made}", said["lines"])
        self.assertEqual(json.loads(self.get(f"/init.json?since={said['at']}")[1])["lines"], [])

    def test_declining_init_still_says_what_the_next_step_is(self) -> None:
        self.assertIn("./init was not run", self.land()[1])

    def test_the_voyage_says_what_stage_the_project_is_on_and_moves_with_the_child(self) -> None:
        """The window a generate opens: every stage with its state, polled while the child runs."""
        self.land()
        code, said = self.get("/voyage")
        self.assertEqual(code, 200)
        self.assertIn('data-stage="prd"', said)
        self.assertIn("Made demo", said, "the receipt is on this page too")
        found = json.loads(self.get("/voyage.json")[1])
        self.assertEqual([one["key"] for one in found["stages"]][:2], ["prd", "init"])
        self.assertFalse(found["launchable"])
        (self.made / "specs/001-demo").mkdir(parents=True)
        (self.made / "specs/001-demo/spec.md").write_text("# Demo\n", encoding="utf-8")
        self.assertTrue(json.loads(self.get("/voyage.json")[1])["launchable"])
        self.assertIn('id="launch"', self.get("/voyage")[1])

    def test_the_model_is_still_said_to_be_next_with_the_storyboard_in_front_of_it(self) -> None:
        """On the event profile the chart is drawn from the model, so there is nothing to press until
        somebody has modelled and the page says so instead. The storyboard now stands before the model, so
        that sentence hangs on the model's own state rather than on which stage happens to be current — and
        a page with neither the chip nor a button would say nothing at all."""
        self.land()
        (self.made / "project.json").write_text(json.dumps({"profile": "event-modelling"}), encoding="utf-8")
        (self.made / "specs/001-demo").mkdir(parents=True)
        (self.made / "specs/001-demo/spec.md").write_text("# Demo\n", encoding="utf-8")
        said = self.get("/voyage")[1]
        self.assertIn("Model it next", said)
        self.assertIn('data-stage="storyboard"', said)
        self.assertEqual(json.loads(self.get("/voyage.json")[1])["stages"][4]["key"], "storyboard",
                         "straight after the specification, where the ladder has the mock-up review")

        (self.made / "docs/event-model").mkdir(parents=True)
        (self.made / "docs/event-model/model.yaml").write_text("version: 1\nslices:\n  - id: A\n",
                                                               encoding="utf-8")
        self.assertNotIn("Model it next", self.get("/voyage")[1], "modelled: the chip has done its job")

    def test_the_specification_can_be_read_from_the_page_that_asks_you_to_agree_to_it(self) -> None:
        """Continue the build is a person's word that the specification is good to build from, and a page
        that asks for that word while giving no way to open the file is asking somebody to agree to
        something they have not read. The mock-up pairs the two buttons; this is the quiet one."""
        self.land()
        self.assertNotIn("Open specs/", self.get("/voyage")[1], "nothing written yet, nothing to open")
        (self.made / "specs/001-demo").mkdir(parents=True)
        (self.made / "specs/001-demo/spec.md").write_text("# Demo\n\nWhat it does.\n", encoding="utf-8")
        said = self.get("/voyage")[1]
        self.assertIn('href="/spec/001-demo"', said)
        self.assertIn("Open specs/001-demo/spec.md", said)
        self.assertIn('target="_blank"', said, "read it beside the run, not instead of it")
        self.assertEqual(self.get("/spec/001-demo"), (200, "# Demo\n\nWhat it does.\n"))

    def test_the_specification_route_serves_that_file_and_nothing_near_it(self) -> None:
        """The same guard the mock-up route has, for the same reason: a route that takes a name out of a
        URL and joins it to a path is a route that serves `../../.ssh/id_rsa` unless it is stopped."""
        self.land()
        (self.made / "specs/001-demo").mkdir(parents=True)
        (self.made / "specs/001-demo/spec.md").write_text("# Demo\n", encoding="utf-8")
        (self.made / "specs/001-demo/notes.md").write_text("private\n", encoding="utf-8")
        for asked in ("/spec/../../etc/passwd", "/spec/001-demo/notes.md", "/spec/nope", "/spec/"):
            with self.subTest(asked=asked), self.assertRaises(urllib.error.HTTPError) as refused:
                self.get(asked)
            refused.exception.close()
            self.assertEqual(refused.exception.code, 404, asked)

    def test_mock_ups_are_on_the_voyage_and_served_from_the_project(self) -> None:
        home = self.made / "specs/001-demo/mockups"
        home.mkdir(parents=True)
        (home / "catalog.html").write_text("<html><head><title>Mock: catalog</title></head><body>hi</body></html>",
                                           encoding="utf-8")
        self.land()
        said = self.get("/voyage")[1]
        self.assertIn("<h2>Mockups · 1</h2>", said)
        self.assertIn(f'src="/mockups/001-demo/catalog.html?seat={self.seat}"', said,
                      "a frame carries its window's seat: nothing else on it does")
        # With a storyboard, that is the door and the mock-ups are reached from it.
        (home / "storyboard.html").write_text("<html><head><title>Storyboard: 001 — review</title></head></html>",
                                              encoding="utf-8")
        said = self.get("/voyage")[1]
        self.assertIn("<h2>Storyboard</h2>", said)
        self.assertIn(f'src="/mockups/001-demo/storyboard.html?seat={self.seat}"', said)
        self.assertNotIn('src="/mockups/001-demo/catalog.html"', said)
        self.assertIn("1 mock-ups, from the storyboard", said)
        self.assertEqual(self.get("/mockups/001-demo/catalog.html"), (200, (home / "catalog.html").read_text()))
        with self.assertRaises(urllib.error.HTTPError) as refused:
            self.get("/mockups/001-demo/../../project.json")
        self.assertEqual(refused.exception.code, 404)

    def test_a_split_with_no_fleet_running_offers_to_cast_off_and_the_button_runs_make_cruise(self) -> None:
        import slipwai.bridge as module
        self.land()
        self.assertEqual(self.post("/cast-off", {})[0], 400, "no split, nothing to cast off")
        rows = [{"slice": "S01", "state": "todo", "title": "", "why": "", "fairway": "", "clearance": "blocked",
                 "feature": "001-demo"}]
        self.patch("folded", lambda root, feature="": (rows, ""))
        (self.made / "Makefile").write_text("cruise:\n\t@echo 'captain started'\n", encoding="utf-8")
        found = json.loads(self.get("/voyage.json")[1])
        self.assertTrue(found["castable"])
        self.assertEqual(next(s for s in found["stages"] if s["key"] == "slices")["state"], "waiting")
        self.assertIn('id="cast-off"', self.get("/voyage")[1])
        self.assertEqual(self.post("/cast-off", {}), (200, "casting off"))
        for _ in range(100):
            receipt = json.loads(self.get("/init.json")[1])
            if receipt["done"]:
                break
            time.sleep(0.1)
        self.assertIn("captain started", receipt["lines"])
        self.assertEqual(receipt["step"], "cruise")
        del module

    def test_the_viewer_is_served_from_the_copy_the_board_keeps_or_the_page_says_why(self) -> None:
        import slipwai.bridge as module
        self.patch("viewer_script", lambda: (b"// viewer", ""))
        code, said = self.get("/drawio-viewer.js")
        self.assertEqual((code, said), (200, "// viewer"))
        self.patch("viewer_script", lambda: (b"", "could not be fetched"))
        with self.assertRaises(urllib.error.HTTPError) as refused:
            self.get("/drawio-viewer.js")
        self.assertEqual(refused.exception.code, 503)
        del module

    def test_the_build_can_be_continued_once_a_specification_exists_and_once_only(self) -> None:
        """The button is the person's word that the specification is good to build from. Before a
        specification there is nothing to continue; after pressing it, the fleet is cast off and a second
        press would be a second harbourmaster."""
        self.land()
        self.assertFalse(json.loads(self.get("/init.json")[1])["launchable"])
        self.assertEqual(self.post("/launch", {})[0], 400)
        (self.made / "specs/001-demo").mkdir(parents=True)
        (self.made / "specs/001-demo/spec.md").write_text("# Demo\n", encoding="utf-8")
        (self.made / "Makefile").write_text("launch:\n\t@echo 'cast off'\n", encoding="utf-8")
        self.assertTrue(json.loads(self.get("/init.json")[1])["launchable"])
        self.assertIn('id="launch"', self.get("/voyage")[1])
        code, said = self.post("/launch", {})
        self.assertEqual((code, said), (200, "continuing the build"))
        for _ in range(100):
            receipt = json.loads(self.get("/init.json")[1])
            if receipt["done"]:
                break
            time.sleep(0.1)
        self.assertIn("cast off", receipt["lines"])
        self.assertIn("Made demo", self.get("/voyage")[1], "the receipt is carried into the new run")
        self.assertFalse(receipt["launchable"], "pressed once")
        self.assertEqual(self.post("/launch", {})[0], 400)


if __name__ == "__main__":
    unittest.main()


class StreamDrawerTest(Fixture):
    """Clicking a stream opens its captain's log. A `<details>`, not a route: the published copy is one
    file with nothing to press, and a link that worked served and 404'd published would be the two
    copies disagreeing."""

    def test_each_stream_row_carries_its_own_log(self) -> None:
        self.deck("ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        said = self.rendered()
        self.assertIn("lines from ORD's captain", said)
        self.assertIn("set Placed", said)

    def test_the_lines_are_said_and_never_the_raw_json(self) -> None:
        self.deck("ORD", logs.entry("demo", fairway="ORD", slice="ORD-01", verdict="accepted"))
        said = self.rendered()
        self.assertIn("demo of ORD-01: accepted", said)
        self.assertNotIn('"kind"', said)

    def test_a_stream_with_a_log_and_no_lines_says_so(self) -> None:
        path = self.root / logs.deck_path("ordering", "EMPTY")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        self.assertIn("Nothing in this stream", self.rendered())

    def test_it_is_a_details_and_never_a_link_to_a_route(self) -> None:
        said = self.rendered()
        self.assertIn("<details class=\"log\">", said)
        self.assertNotIn('href="/stream', said)

    def test_the_published_copy_opens_it_too(self) -> None:
        """Nothing to press is not nothing to read: a drawer is a CSS rule, not a control."""
        from slipwai.bridge_page import read_only
        said = read_only(board(self.root, config(self.root)), config(self.root))
        self.assertIn("captain", said)
        self.assertIn("<details class=\"log\">", said)

    def test_a_person_s_message_is_still_escaped_inside_the_drawer(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="<script>alert(1)</script>"))
        self.assertNotIn("<script>alert(1)</script>", self.rendered())
