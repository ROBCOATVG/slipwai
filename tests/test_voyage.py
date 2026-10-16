"""The committed model with each slice's standing drawn on it, and the fold the columns come from.

The picture is draw.io's and the file is the project's: what is proved is that the board finds a slice's
caption by the id the renderer gave it, strokes it and nothing else, and hands the file back untouched
wherever it cannot be sure — and that the words around the picture say what is missing.
"""
# budget: 390 — the fold, the mock-ups, the screenshots and the storyboard verdict one voyage page is held to
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
                         [("001-demo", "catalog.html", "catalog — Demo", "/mockups/001-demo/catalog.html")])
        self.assertEqual(mockups(Path(tempfile.mkdtemp())), [])

    def test_a_seat_stays_on_the_path_a_mock_up_s_own_files_are_loaded_from(self) -> None:
        """A query is dropped by the stylesheet, the script and the next frame. A path segment is not."""
        from slipwai.voyage import mockup_href, mockup_where
        href = mockup_href("001-demo", "storyboard.html", "window-one")
        self.assertEqual(href, "/mockups/by/window-one/001-demo/storyboard.html")
        self.assertEqual(mockup_where("by/window-one/001-demo/storyboard.html"),
                         ("window-one", "001-demo/storyboard.html"))
        self.assertEqual(mockup_where("001-demo/styles.css"), ("", "001-demo/styles.css"))
        self.assertEqual(mockups(self.root, "window-one")[0]["href"],
                         "/mockups/by/window-one/001-demo/catalog.html")

    def test_the_route_serves_a_mock_up_and_its_stylesheet_and_nothing_outside_them(self) -> None:
        self.assertEqual(mockup_file(self.root, "001-demo/catalog.html"), (self.home / "catalog.html").resolve())
        self.assertEqual(mockup_file(self.root, "001-demo/mock.css"), (self.home / "mock.css").resolve())
        for outside in ("001-demo/../../secret.txt", "001-demo/../spec.md", "../secret.txt", "001-demo/", "",
                        "nope/x.html"):
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

    def test_a_model_still_running_is_the_voyage_not_a_prompt_to_start_one(self) -> None:
        """A model step this board did not start still says where the project is, and that the log is not here."""
        from slipwai.init_run import model_session
        from slipwai.passage import stages
        from slipwai.voyage_page import page
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text('{"profile": "event-modelling"}\n', encoding="utf-8")
        (root / ".slipwai").mkdir()
        (root / ".slipwai/model-next.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        held = model_session(root)
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
        self.assertIsNone(model_session(root))


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


if __name__ == "__main__":
    unittest.main()
