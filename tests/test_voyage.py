"""The committed model with each slice's standing drawn on it, and the fold the columns come from.

The picture is draw.io's and the file is the project's: what is proved is that the board finds a slice's
caption by the id the renderer gave it, strokes it and nothing else, and hands the file back untouched
wherever it cannot be sure — and that the words around the picture say what is missing.
"""
# budget: 605 — the fold, the mock-ups, the screenshots and the storyboard verdict one voyage page is held to,
# the design files a storyboard links that the board serves beside it, a step it did not start,
# and how far into its budget a drawing is, and a fleet at work read as working
# and a waiting slice's card, opened on its park and its questions with a box aimed at it
# and the Queued column a slice waiting for a slot stands in
# and a slice's stage read off its branch and log, held to the captain's rungs
# and a slice named from the model whatever its id
from __future__ import annotations

import json
import os
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
    running_app,
    screen_file,
    screens,
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
                         [("001-demo", "catalog.html", "catalog — Demo",
                           "/mockups/specs/001-demo/mockups/catalog.html")])
        self.assertEqual(mockups(Path(tempfile.mkdtemp())), [])

    def test_a_seat_stays_on_the_path_a_mock_up_s_own_files_are_loaded_from(self) -> None:
        """A query is dropped by the stylesheet, the script and the next frame. A path segment is not."""
        from slipwai.voyage import mockup_href, mockup_where
        href = mockup_href("001-demo", "storyboard.html", "window-one")
        self.assertEqual(href, "/mockups/by/window-one/specs/001-demo/mockups/storyboard.html")
        self.assertEqual(mockup_where("by/window-one/001-demo/storyboard.html"),
                         ("window-one", "001-demo/storyboard.html"))
        self.assertEqual(mockup_where("001-demo/styles.css"), ("", "001-demo/styles.css"))
        self.assertEqual(mockups(self.root, "window-one")[0]["href"],
                         "/mockups/by/window-one/specs/001-demo/mockups/catalog.html")

    def test_the_route_serves_a_mock_up_and_its_stylesheet_and_nothing_outside_them(self) -> None:
        self.assertEqual(mockup_file(self.root, "001-demo/catalog.html"), (self.home / "catalog.html").resolve())
        self.assertEqual(mockup_file(self.root, "001-demo/mock.css"), (self.home / "mock.css").resolve())
        for outside in ("001-demo/../../secret.txt", "001-demo/../spec.md", "../secret.txt", "001-demo/", "",
                        "nope/x.html"):
            self.assertIsNone(mockup_file(self.root, outside), outside)


    def test_a_project_path_reaches_the_design_a_storyboard_links_and_nothing_else(self) -> None:
        handed = self.root / "docs/design"
        handed.mkdir(parents=True)
        (handed / "styles.css").write_text("body{}", encoding="utf-8")
        (self.root / "docs/prd.md").write_text("# prd\n", encoding="utf-8")
        (self.root / "specs/001-demo/spec.md").write_text("# spec\n", encoding="utf-8")
        self.assertEqual(mockup_file(self.root, "docs/design/styles.css"), (handed / "styles.css").resolve())
        self.assertEqual(mockup_file(self.root, "specs/001-demo/spec.md"),
                         (self.root / "specs/001-demo/spec.md").resolve())
        self.assertEqual(mockup_file(self.root, "specs/001-demo/mockups/catalog.html"),
                         (self.home / "catalog.html").resolve())
        for outside in ("docs/prd.md", "docs/design/../prd.md", "specs/../secret.txt", "secret.txt",
                        "specs/001-demo/notes.md", "docs/design", "specs/001-demo/mockups/../../../secret.txt"):
            self.assertIsNone(mockup_file(self.root, outside), outside)


PNG = b"\x89PNG\r\n\x1a\n\xff\xfe"


class ScreensTest(unittest.TestCase):
    """Design-review photographs, read from where that rung writes them.

    A picture is evidence the slice was rendered. The voyage's job is to show it beside the mock-up it was
    drawn from, labelled by the same standing the columns use, and to serve the file itself — nothing that
    merely sits near it.
    """

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.design = self.root / "specs/001-demo/slices/S01/design"
        self.design.mkdir(parents=True)
        (self.design / "home.png").write_bytes(PNG)
        (self.design / "empty.webp").write_bytes(b"RIFF")
        (self.design / "also.jpeg").write_bytes(b"\xff\xd8\xff")
        (self.design / "icon.gif").write_bytes(b"GIF89a")
        (self.design / "notes.md").write_text("looked at it\n", encoding="utf-8")
        (self.design / "diagram.svg").write_text("<svg></svg>", encoding="utf-8")
        (self.root / "specs/001-demo/slices/S01/loose.png").write_bytes(PNG)
        other = self.root / "specs/001-demo/slices/S02/design"
        other.mkdir(parents=True)
        (other / "list.jpg").write_bytes(b"\xff\xd8\xff")
        orphan = self.root / "specs/001-demo/slices/S03/design"
        orphan.mkdir(parents=True)
        (orphan / "orphan.png").write_bytes(PNG)
        elsewhere = self.root / "specs/001-other/slices/S01/design"
        elsewhere.mkdir(parents=True)
        (elsewhere / "x.png").write_bytes(PNG)
        (self.root / "secret.png").write_bytes(PNG)
        self.rows = [
            {"slice": "S02", "state": "done", "title": "Publish", "feature": "001-demo"},
            {"slice": "S01", "state": "working", "title": "Set up an account", "feature": "001-demo"},
        ]

    def test_each_screenshot_carries_its_slice_s_standing_and_nothing_else_is_one(self) -> None:
        """A note, a drawing and a picture left outside `design/` are not screens. A slice the chart has
        not got is to do. The same slice id in another feature does not inherit this one's title."""
        found = screens(self.root, self.rows, "window")
        self.assertEqual(
            [(row["feature"], row["slice"], row["title"], row["state"], row["name"]) for row in found],
            [
                ("001-demo", "S01", "Set up an account", "working", "also.jpeg"),
                ("001-demo", "S01", "Set up an account", "working", "empty.webp"),
                ("001-demo", "S01", "Set up an account", "working", "home.png"),
                ("001-demo", "S01", "Set up an account", "working", "icon.gif"),
                ("001-demo", "S02", "Publish", "done", "list.jpg"),
                ("001-demo", "S03", "", "todo", "orphan.png"),
                ("001-other", "S01", "", "todo", "x.png"),
            ])
        home = next(row for row in found if row["name"] == "home.png")
        self.assertIn("/screens/001-demo/S01/home.png?", home["href"])
        self.assertIn("seat=window", home["href"])
        self.assertIn("v=", home["href"])
        self.assertEqual(screens(Path(tempfile.mkdtemp()), [], ""), [])

    def test_a_name_with_a_space_is_escaped_on_the_address(self) -> None:
        held = self.design / "home page.png"
        held.write_bytes(PNG)
        found = next(row for row in screens(self.root, [], "") if row["name"] == "home page.png")
        self.assertIn("home%20page.png", found["href"])
        self.assertEqual(screen_file(self.root, "001-demo/S01/home%20page.png"), held.resolve())

    def test_the_route_serves_one_screenshot_and_nothing_outside_its_directory(self) -> None:
        self.assertEqual(screen_file(self.root, "001-demo/S01/home.png"), (self.design / "home.png").resolve())
        (self.design / "linked.png").symlink_to(self.root / "secret.png")
        for outside in ("001-demo/S01/../../secret.png", "001-demo/S01/%2e%2e%2f%2e%2e%2fsecret.png",
                        "001-demo/S01/notes.md", "001-demo/S01/diagram.svg", "001-demo/S01/loose.png",
                        "001-demo/S01/linked.png", "001-demo/S01/", "", "nope/x.png"):
            self.assertIsNone(screen_file(self.root, outside), outside)
        self.assertNotIn("linked.png", [row["name"] for row in screens(self.root, [], "")])

    def test_the_running_app_is_the_first_browser_port_and_only_a_port(self) -> None:
        """A service's port is not a screen, and a value that is not a port is not an address."""
        self.assertEqual(running_app(self.root), "")
        (self.root / "project.json").write_text("{", encoding="utf-8")
        self.assertEqual(running_app(self.root), "")
        (self.root / "project.json").write_text(json.dumps({"deployables": {
            "api": {"kind": "service", "port": 3000},
            "admin": {"kind": "web", "port": True},
            "web": {"kind": "web", "port": "5173"},
            "shop": {"kind": "web", "port": 5174},
            "later": {"kind": "web", "port": 5175},
        }}), encoding="utf-8")
        self.assertEqual(running_app(self.root), "http://localhost:5174")
        for port in (0, 65536, -1):
            (self.root / "project.json").write_text(
                json.dumps({"deployables": {"web": {"kind": "web", "port": port}}}), encoding="utf-8")
            self.assertEqual(running_app(self.root), "", port)


class BuiltScreensPageTest(unittest.TestCase):
    def page(self, shots: list[dict[str, str]] | None, mocks: list[dict[str, str]], app: str = "") -> str:
        from slipwai.voyage_page import page
        return page(Path(tempfile.mkdtemp()), [], [], "", "", "", "", None, False,
                    mocks=mocks, shots=shots, app=app)

    def test_screenshots_sit_beside_that_feature_s_mock_ups_and_a_title_is_text(self) -> None:
        mocks = [
            {"feature": "001-demo", "name": "storyboard.html", "title": "review",
             "href": "/mockups/001-demo/storyboard.html?seat=w"},
            {"feature": "001-demo", "name": "catalog.html", "title": "catalog",
             "href": "/mockups/001-demo/catalog.html?seat=w"},
            {"feature": "002-other", "name": "basket.html", "title": "basket",
             "href": "/mockups/002-other/basket.html"},
        ]
        shots = [
            {"feature": "001-demo", "slice": "S01", "title": "Set up an account", "state": "working",
             "name": "home.png", "href": "/screens/001-demo/S01/home.png?seat=w&v=1"},
            {"feature": "001-demo", "slice": "S01", "title": "Set up an account", "state": "working",
             "name": "empty.png", "href": "/screens/001-demo/S01/empty.png?seat=w&v=2"},
            {"feature": "001-demo", "slice": "S02", "title": "<script>", "state": "waiting",
             "name": "list.png", "href": '/screens/x" onmouseover="alert(1)'},
        ]
        html = self.page(shots, mocks, "http://localhost:5173")
        card = html[html.index('id="built"'):html.index("<h2>Mockups")]
        self.assertIn("Built screens · 3", card)
        self.assertIn("Intended", card)
        self.assertIn('src="/mockups/001-demo/storyboard.html?seat=w"', card)
        self.assertNotIn('src="/mockups/001-demo/catalog.html', card, "the storyboard is the door")
        self.assertIn("Working", card)
        self.assertIn("Waiting on you", card)
        self.assertIn('src="/screens/001-demo/S01/home.png?seat=w&amp;v=1"', card)
        self.assertIn('src="/screens/001-demo/S01/empty.png?seat=w&amp;v=2"', card)
        self.assertIn('target="_blank"', card)
        self.assertIn('href="http://localhost:5173"', card)
        self.assertIn("Open the running app", card)
        self.assertNotIn("<script>", card)
        self.assertIn("&lt;script&gt;", card)
        self.assertNotIn('onmouseover="alert(1)"', card)
        self.assertIn("basket.html", html[html.index("<h2>Mockups"):], "another feature's mock-up stays")

    def test_wireframes_stand_in_when_there_is_no_storyboard(self) -> None:
        mocks = [{"feature": "001-demo", "name": "catalog.html", "title": "catalog",
                  "href": "/mockups/001-demo/catalog.html"}]
        shots = [{"feature": "001-demo", "slice": "S01", "title": "", "state": "done",
                  "name": "home.png", "href": "/screens/001-demo/S01/home.png"}]
        card = self.page(shots, mocks)
        self.assertIn('src="/mockups/001-demo/catalog.html"', card)
        self.assertIn(">Done<", card)
        self.assertNotIn("Open the running app", card)
        self.assertNotIn("<h2>Mockups", card)
        self.assertNotIn("<h2>Storyboard", card)

    def test_no_screenshot_leaves_the_mock_ups_where_they_were(self) -> None:
        mocks = [{"feature": "001-demo", "name": "storyboard.html", "title": "review",
                  "href": "/mockups/001-demo/storyboard.html"}]
        html = self.page([], mocks, "http://localhost:5173")
        self.assertNotIn('id="built"', html)
        self.assertIn("<h2>Storyboard</h2>", html)
        self.assertNotIn("Open the running app", html)

    def test_either_verdict_disables_approve_and_disapprove(self) -> None:
        """Pressing one locks both, and a recorded verdict leaves them locked after the reload."""
        from slipwai.voyage_page import SCRIPT, verdict_form
        root = Path(tempfile.mkdtemp())
        home = root / "specs/001-demo/mockups"
        home.mkdir(parents=True)
        open_form = verdict_form(root, "001-demo")
        self.assertNotIn("disabled", open_form)
        self.assertIn("dataset.storyboard === story", SCRIPT)
        self.assertIn("one.disabled = true", SCRIPT)
        for mark in ("approved", "parked: the map"):
            (home / "mock-states.md").write_text(
                f"## Surface: Discover\n- Populated \u2014 {mark}\n", encoding="utf-8")
            closed = verdict_form(root, "001-demo")
            self.assertIn('data-verdict="approved" disabled', closed, mark)
            self.assertIn('data-verdict="parked" disabled', closed, mark)

    def test_a_locked_verdict_button_looks_locked(self) -> None:
        """A disabled control keeps the attribute and loses the teal of a button that can be pressed."""
        from slipwai.page_shell import STYLE
        self.assertIn("button.go:disabled", STYLE)
        self.assertIn("cursor:not-allowed", STYLE)

    def test_a_berth_at_work_is_the_slices_step_working(self) -> None:
        """`fleet.state_of` calls a live berth `working`; the step compared against `running`, which it never
        returns, so a fleet at work read as `todo` once nothing waited on a person."""
        from slipwai.passage import stages
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text('{"profile": "standard"}\n', encoding="utf-8")
        fleet = {"berths": [{"state": "working"}], "inbox": [], "running": True}
        found = stages(root, None, fleet, {"todo": 20, "working": 0})
        slices = next(one for one in found if one.key == "slices")
        self.assertEqual(slices.state, "working")
        self.assertIn("the fleet is running", slices.next)

    def test_a_model_still_running_is_the_voyage_not_a_prompt_to_start_one(self) -> None:
        """A model step this board did not start still says where the project is, and that the log is not here."""
        from slipwai.init_run import outside_session
        from slipwai.passage import stages
        from slipwai.voyage_page import page
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text('{"profile": "event-modelling"}\n', encoding="utf-8")
        (root / ".slipwai").mkdir()
        (root / ".slipwai/model-next.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        held = outside_session(root)
        self.assertIsNotNone(held)
        assert held is not None
        self.assertEqual(held["step"], "model")
        self.assertFalse(held["done"])
        found = stages(root, held)
        self.assertEqual(next(one.state for one in found if one.key == "model"), "working")
        html = page(root, found, [], "", "", "", "", held, False)
        self.assertIn('id="fitting"', html)
        self.assertIn("has not got its log", html)
        self.assertNotIn("Model it next", html)
        (root / ".slipwai/model-next.pid").write_text("999999999\n", encoding="utf-8")
        self.assertIsNone(outside_session(root))

    def test_a_storyboard_being_drawn_by_another_session_reads_as_working_not_stuck(self) -> None:
        """`make surfaces` run without this board — a redraw after a disapproval, or a board restarted mid-draw
        — showed a storyboard waiting on a verdict whose buttons were locked, which reads as a run stopped."""
        from slipwai.init_run import outside_session
        from slipwai.passage import stages
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text('{"profile": "standard"}\n', encoding="utf-8")
        (root / ".slipwai").mkdir()
        (root / ".slipwai/surfaces.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        held = outside_session(root)
        assert held is not None
        self.assertEqual(held["step"], "surfaces")
        self.assertIn("Drawing the surfaces is running", held["lines"][0])
        self.assertEqual(next(one.state for one in stages(root, held) if one.key == "storyboard"), "working")

    def test_a_drawing_under_way_says_how_far_into_its_budget_it_is(self) -> None:
        """The question at the ten-minute mark is whether ten minutes is normal, and the pid file the drawing
        writes carries its start and its budget so the strip can say — without a second reading of
        `harbour.json` on the board."""
        from slipwai.init_run import outside_session
        from slipwai.passage import drawing_clock, stages
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text('{"profile": "standard"}\n', encoding="utf-8")
        (root / ".slipwai").mkdir()
        began = time.time() - 6 * 60 - 5
        (root / ".slipwai/surfaces.pid").write_text(f"{os.getpid()}\n{began:.0f}\n900\n", encoding="utf-8")
        self.assertEqual(drawing_clock(root), "6 of about 15 min")
        held = outside_session(root)
        assert held is not None
        self.assertGreaterEqual(held["seconds"], 360)
        storyboard = next(one for one in stages(root, held) if one.key == "storyboard")
        self.assertEqual(storyboard.detail, "drawing: 6 of about 15 min")

    def test_a_drawing_from_before_the_budget_says_nothing_about_one(self) -> None:
        from slipwai.passage import drawing_clock
        root = Path(tempfile.mkdtemp())
        (root / ".slipwai").mkdir()
        (root / ".slipwai/surfaces.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        self.assertEqual(drawing_clock(root), "")


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

    def test_the_short_description_is_the_value_column_and_the_card_says_so(self) -> None:
        """The split's candidates table puts the name in the next cell. The slice graph's next cell is a
        dependency, and reading that would name a slice after a dash."""
        from slipwai.voyage_page import page
        root = Path(tempfile.mkdtemp())
        (root / "specs/001-demo").mkdir(parents=True)
        (root / "specs/001-demo/story-split.md").write_text(
            "## Split Candidates\n"
            "| Slice | Value | Includes |\n|---|---|---|\n"
            "| S10 | Appoint a moderator | Gather a community |\n\n"
            "## Slice graph\n"
            "| Slice | depends_on | parallel_ok_with | Notes |\n|---|---|---|---|\n"
            "| S10 | — | other slices | Open an account |\n", encoding="utf-8")
        self.assertEqual(titles(root, "001-demo"), {"S10": "Appoint a moderator"})
        html = page(root, [], [{"slice": "S10", "state": "todo", "title": "Appoint a moderator",
                                "why": "cleared", "fairway": "", "clearance": "preparation-ready"}],
                    "", "", "", "", None, False)
        self.assertIn("S10 · Appoint a moderator", html)
        self.assertNotIn("Open an account", html, "the slice graph's note column is not its name")

    def test_a_slice_is_called_what_the_model_names_it_whatever_its_id(self) -> None:
        """hr-test-2's ids are `L01`, and every card was nameless: titles were read for `S` ids only, and
        the model's `name`, which the drawio captions the slice with, was not read at all."""
        root = Path(tempfile.mkdtemp())
        (root / "specs/001-leaver").mkdir(parents=True)
        (root / "specs/001-leaver/story-split.md").write_text(
            "| Slice | Value | Includes |\n|---|---|---|\n| L04 | Access removal gets an owner | name |\n"
            "| L05 | Settle an item | settle |\n", encoding="utf-8")
        (root / "docs/event-model").mkdir(parents=True)
        (root / "docs/event-model/model.yaml").write_text(
            "slices:\n  - id: L04\n    name: Name the owner of access removal\n    pattern: state-change\n",
            encoding="utf-8")
        self.assertEqual(titles(root, "001-leaver"),
                         {"L04": "Name the owner of access removal", "L05": "Settle an item"})

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




class AnswerCardTest(unittest.TestCase):
    def test_a_waiting_slice_opens_on_its_park_its_questions_and_a_box_aimed_at_it(self) -> None:
        from slipwai.voyage_page import slice_html

        row = {"slice": "L07", "title": "Record the agreed final day", "state": "waiting", "fairway": "leaver",
               "clearance": "running", "why": "claimed", "park": "stops before the plan on two questions",
               "asked": "L07-Q1: after the agreed date?\nL07-Q2: which days?", "aim": "L07"}
        card = slice_html(row)
        self.assertTrue(card.startswith('<details class="slice waiting">'))
        self.assertIn("stops before the plan on two questions", card)
        self.assertIn("<li>L07-Q2: which days?</li>", card)
        self.assertIn('data-answer="leaver" data-slice="L07"', card)
        self.assertIn("Send to L07", card)

    def test_a_slice_held_by_its_stream_s_park_answers_the_stream(self) -> None:
        from slipwai.voyage_page import slice_html

        row = {"slice": "L02", "title": "", "state": "waiting", "fairway": "leaver", "clearance": "running",
               "why": "", "park": "the gate stayed red", "asked": "", "aim": ""}
        card = slice_html(row)
        self.assertIn('data-slice=""', card)
        self.assertIn("Send to the leaver stream", card)

    def test_a_closed_card_is_its_number_its_title_and_its_stage(self) -> None:
        """The rest is behind a click: a column of cards carrying every reason was too loud to scan."""
        from slipwai.voyage_page import slice_html

        row = {"slice": "L03", "title": "Record equipment", "state": "working", "fairway": "leaver",
               "clearance": "running", "why": "implementing — its own marks set", "chip": "Implementing · 14/22",
               "stage": "Implementing", "artifacts": "examples,plan,tasks", "last": "2026-10-20T11:00:00Z mark-set"}
        card = slice_html(row)
        summary = card[card.index("<summary>"):card.index("</summary>")]
        self.assertTrue(card.startswith('<details class="slice working">'))
        self.assertIn("L03 · Record equipment", summary)
        self.assertIn('<span class="chip">Implementing · 14/22</span>', summary)
        self.assertNotIn("its own marks set", summary, "the reason waits behind the click")
        self.assertIn("its own marks set", card)
        self.assertIn("examples, plan, tasks", card)


class QueuedColumnTest(unittest.TestCase):
    def test_a_slice_waiting_for_a_slot_has_a_column_of_its_own(self) -> None:
        from slipwai.voyage_page import slice_html, work_card

        rows = [{"slice": "L11", "title": "", "state": "queued", "fairway": "leaver", "clearance": "running",
                 "why": "claimed, waiting for a slot: carried on when a session frees"},
                {"slice": "L02", "title": "", "state": "working", "fairway": "leaver", "clearance": "running",
                 "why": "implementing"}]
        card = work_card(rows, "")
        self.assertIn("Queued · 1", card)
        self.assertIn("Working · 1", card)
        self.assertTrue(slice_html(rows[0]).startswith('<details class="slice queued">'))
        self.assertIn('<span class="chip">Queued</span>', slice_html(rows[0]))


class RungTest(unittest.TestCase):
    """A slice's stage, read off its branch and its log the way the captain ranks it."""

    def setUp(self) -> None:
        import subprocess

        self.root = Path(tempfile.mkdtemp())
        folder = self.root / "specs/001-demo/slices/S01"

        def git(*argv: str) -> None:
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv], cwd=self.root,
                           check=True, capture_output=True)

        git("init", "-q", "-b", "main")
        (self.root / "README.md").write_text("x\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "scaffold")
        git("checkout", "-q", "-b", "slice/S01")
        folder.mkdir(parents=True)
        (folder / "examples.md").write_text("# examples\n", encoding="utf-8")
        (folder / "plan.md").write_text("# plan\n", encoding="utf-8")
        (folder / "tasks.md").write_text("- [x] T001 one\n- [X] T002 two\n- [ ] T003 three\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "S01: tasks")
        git("checkout", "-q", "main")

    def test_a_slice_with_tasks_ticked_says_how_many(self) -> None:
        from slipwai.slice_rungs import rung

        found = rung(self.root, "001-demo", "S01", [])
        self.assertEqual((found["stage"], found["chip"], found["artifacts"]),
                         ("Implementing", "Implementing · 2/3", "examples,plan,tasks"))

    def test_a_merge_request_in_its_log_is_the_furthest_rung(self) -> None:
        from slipwai import logs
        from slipwai.slice_rungs import rung

        asked = [logs.entry("request", fairway="F", slice="S01", id="S01-merge", what="merge", detail="merge it"),
                 logs.entry("heartbeat", fairway="F", slice="S01")]
        found = rung(self.root, "001-demo", "S01", asked)
        self.assertEqual(found["chip"], "Merging")
        self.assertTrue(found["last"].endswith(" request"), "a heartbeat is not what the slice last did")

    def test_the_stage_its_berth_has_open_names_the_chip(self) -> None:
        """hr-test-2's L18 said `Implementing · 18/18` through its demo and review: the files the board read
        move when a stage ends, and the berth's benchmark record moves when one starts."""
        import json
        import shutil

        from slipwai.slice_rungs import rung

        berth = self.root.parent / f"{self.root.name}-S01"
        self.addCleanup(shutil.rmtree, berth, ignore_errors=True)
        record = berth / "specs/001-demo/slices/S01/benchmark.json"
        record.parent.mkdir(parents=True)
        stages = [{"stage": "implement-shipwright", "started": "t0", "ended": "t1"}]
        stages.append({"stage": "demo", "started": "t2"})
        record.write_text(json.dumps({"stages": stages}), encoding="utf-8")
        found = rung(self.root, "001-demo", "S01", [])
        self.assertEqual((found["chip"], found["rank"], found["tasks"]), ("Demo", "4", "2/3"),
                         "the rank stays the evidence's, which is what the captain ranks by")
        stages[-1]["ended"] = "t3"
        record.write_text(json.dumps({"stages": stages}), encoding="utf-8")
        self.assertEqual(rung(self.root, "001-demo", "S01", [])["chip"], "Implementing · 2/3",
                         "between stages the evidence speaks")

    def test_a_slice_with_no_branch_is_starting(self) -> None:
        from slipwai.slice_rungs import rung

        self.assertEqual(rung(self.root, "001-demo", "S09", [])["chip"], "Starting")

    def test_the_rungs_are_the_captain_s_rungs(self) -> None:
        """The board names what the captain ranks by: the same signals at the same height, so the slice the
        captain carries on first is the one whose chip says it is furthest along."""
        import ast

        from slipwai.slice_rungs import FILED, LOGGED

        source = (Path(__file__).resolve().parents[1] / "assets/toolkit/scripts/agents/captain.py").read_text(
            encoding="utf-8")
        tables = {node.targets[0].id: ast.literal_eval(node.value) for node in ast.parse(source).body
                  if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                  and node.targets[0].id in ("LOG_RUNGS", "FILE_RUNGS")}
        self.assertEqual(tables["LOG_RUNGS"], {kind: number for kind, (number, _word) in LOGGED.items()})
        self.assertEqual(tables["FILE_RUNGS"],
                         {name: number for name, (number, _word) in FILED.items() if name != "research.md"})


if __name__ == "__main__":
    unittest.main()
