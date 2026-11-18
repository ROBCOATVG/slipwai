"""A page of the board's as one file to send: what a copy carries, what it refuses, and what it says it is."""
from __future__ import annotations

import base64
import html
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import brief_session, page_copy
from slipwai.storyboard_card import copy_said, mockups_card, standing
from slipwai.voyage import mockups

PIXEL = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")


def anywhere(_: Path) -> bool:
    return True


class BundleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp()).resolve()

    def write(self, name: str, text: str | bytes) -> Path:
        path = self.home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
        return path

    def test_stylesheets_scripts_and_pictures_are_written_into_the_one_file(self) -> None:
        self.write("look/look.css", '@import "more.css";\nbody { background: url(dot.png); }')
        self.write("look/more.css", "h1 { color: teal; }")
        self.write("look/dot.png", PIXEL)
        self.write("app.js", "{ const end = '</script>'; }")
        page = self.write("index.html", '<html><head><link rel="stylesheet" media="screen" href="look/look.css">'
                                        '</head><body><img alt="" src="look/dot.png">'
                                        '<script defer src="app.js"></script></body></html>')
        made = page_copy.bundled(page, anywhere, "A copy.")
        self.assertIn('<style media="screen">h1 { color: teal; }', made)
        self.assertIn('background: url("data:image/png;base64,', made)
        self.assertIn('<img alt="" src="data:image/png;base64,', made)
        self.assertIn("<script defer>{ const end = '<\\/script>'; }</script>", made, "and its end tag cannot end it")
        self.assertNotIn("look.css", made)
        self.assertNotIn("app.js", made)

    def test_a_framed_page_becomes_the_frame_s_srcdoc_and_keeps_its_sandbox(self) -> None:
        self.write("booking.html", '<html><head><title>Mock: Booking</title><link rel="stylesheet" href="s.css">'
                                   '</head><body><article class="state"><h2>Empty</h2></article></body></html>')
        self.write("s.css", "article { border: 1px solid; }")
        page = self.write("storyboard.html", '<html><body><iframe sandbox="allow-scripts" src="booking.html#empty">'
                                             "</iframe></body></html>")
        made = page_copy.bundled(page, anywhere, "A copy.")
        self.assertIn('<iframe sandbox="allow-scripts" srcdoc="', made)
        self.assertNotIn("booking.html", made)
        inside = html.unescape(made.split('srcdoc="', 1)[1].split('"', 1)[0])
        self.assertIn("<style>article { border: 1px solid; }</style>", inside, "the framed page is whole too")
        self.assertIn("<h2>Empty</h2>", inside)

    def test_a_page_that_is_only_linked_is_drawn_at_the_end_and_the_link_goes_there(self) -> None:
        self.write("booking.html", "<html><head><title>Mock: Booking</title></head><body>b</body></html>")
        page = self.write("storyboard.html", '<html><body><a href="booking.html">Booking</a> '
                                             '<a href="booking.html">again</a> <a href="https://example.com/x.html">'
                                             'out</a> <a href="../spec.md">spec</a></body></html>')
        made = page_copy.bundled(page, anywhere, "A copy.")
        self.assertEqual(made.count('href="#slipwai-copy-1"'), 2)
        self.assertEqual(made.count('<section id="slipwai-copy-1"'), 1, "one page, drawn once")
        self.assertIn('<h2 style="font:600 16px system-ui,sans-serif">Booking</h2><iframe title="Booking" '
                      'sandbox="allow-scripts"', made)
        self.assertLess(made.index('<section id="slipwai-copy-1"'), made.index("</body>"))
        self.assertIn('href="https://example.com/x.html"', made)
        self.assertIn('href="../spec.md"', made)

    def test_pages_that_frame_each_other_end(self) -> None:
        self.write("a.html", '<html><body><iframe src="b.html"></iframe></body></html>')
        self.write("b.html", '<html><body><iframe src="a.html"></iframe></body></html>')
        made = page_copy.bundled(self.home / "a.html", anywhere, "A copy.")
        self.assertEqual(made.count("srcdoc="), 1)

    def test_a_copy_carries_only_what_it_is_allowed_and_only_what_a_page_is_made_of(self) -> None:
        self.write("inside/index.html", '<html><body><img src="../secret.png"><img src="notes.env">'
                                        '<img src=".hidden/dot.png"><img src="gone.png"><img src="dot.png">'
                                        "</body></html>")
        for name in ("secret.png", "inside/.hidden/dot.png", "inside/dot.png"):
            self.write(name, PIXEL)
        self.write("inside/notes.env", "TOKEN=1")
        within = self.home / "inside"
        made = page_copy.bundled(within / "index.html", lambda path: path.is_relative_to(within), "A copy.")
        self.assertEqual(made.count("data:image/png"), 1)
        self.assertNotIn(base64.b64encode(b"TOKEN=1").decode(), made)
        self.assertIn("Not in this copy: ../secret.png, notes.env, .hidden/dot.png, gone.png.", made)

    def test_a_file_too_large_to_mail_stays_out_and_is_named(self) -> None:
        self.write("big.png", PIXEL)
        page = self.write("index.html", '<html><body><img src="big.png"></body></html>')
        with mock.patch.object(page_copy, "LIMIT", 10):
            made = page_copy.bundled(page, anywhere, "A copy.")
        self.assertIn('src="big.png"', made)
        self.assertIn("Not in this copy: big.png.", made)

    def test_what_is_still_fetched_from_the_internet_is_counted_and_left_alone(self) -> None:
        page = self.write("index.html", '<html><head><link rel="stylesheet" href="https://fonts.example/f.css">'
                                        '<script src="https://cdn.example/x.js"></script></head><body>'
                                        '<a href="https://example.com">out</a></body></html>')
        made = page_copy.bundled(page, anywhere, "A copy.")
        self.assertIn('href="https://fonts.example/f.css"', made)
        self.assertIn('<script src="https://cdn.example/x.js"></script>', made)
        self.assertIn("2 parts of it load from the internet, and need a connection.", made, "a link is not a part")

    def test_the_strip_is_in_a_document_s_flow_and_fixed_and_dismissed_on_something_played(self) -> None:
        page = self.write("index.html", '<html><body class="app"><main>x</main></body></html>')
        read = page_copy.bundled(page, anywhere, "A <copy>.")
        self.assertIn('<body class="app"><div id="slipwai-copy" style="all:initial;display:block;', read)
        self.assertIn("A &lt;copy&gt;.</div><main>", read)
        self.assertNotIn("position:fixed", read)
        played = page_copy.bundled(page, anywhere, "A copy.", fixed=True)
        self.assertIn("position:fixed;left:0;right:0;bottom:0;", played)
        self.assertIn('onclick="this.parentNode.remove()"', played)
        bare = self.write("bare.html", "<p>no body tag</p>")
        self.assertTrue(page_copy.bundled(bare, anywhere, "A copy.").startswith('<div id="slipwai-copy"'))

    def test_a_copy_is_bytes_with_a_name_to_save_it_under(self) -> None:
        body, kind, more = page_copy.download("<p>é</p>", "club boats/../x-prototype")
        self.assertEqual(body, "<p>é</p>".encode())
        self.assertEqual(kind, "text/html; charset=utf-8")
        self.assertEqual(more, (("Content-Disposition", 'attachment; filename="club-boats-..-x-prototype.html"'),))


class BoardSideTest(BoardTest):
    def fetch(self, path: str) -> tuple[int, str, str]:
        try:
            with urllib.request.urlopen(self.at(path), timeout=5) as answer:
                return answer.status, answer.read().decode("utf-8"), answer.headers.get("Content-Disposition", "")
        except urllib.error.HTTPError as answer:
            with answer:
                return answer.code, answer.read().decode("utf-8"), ""

    def test_the_first_page_offers_the_prototype_as_a_file_and_serves_it_whole(self) -> None:
        with mock.patch.object(brief_session, "SKETCHES", Path(tempfile.mkdtemp()) / "sketches"):
            home = brief_session.prepared(brief_session.workspace("club-boats"))
            self.assertEqual(self.fetch("/brief/copy?sketch=club-boats")[0], 404, "nothing drawn, nothing to copy")
            (home / "brief" / "look").mkdir(parents=True, exist_ok=True)
            (home / "brief" / "look" / "look.css").write_text("body { color: navy; }", encoding="utf-8")
            (home.parent / "other.css").write_text("body { color: red; }", encoding="utf-8")
            page = home / brief_session.PROTOTYPE / "index.html"
            page.write_text('<html><head><link rel="stylesheet" href="../brief/look/look.css">'
                            '<link rel="stylesheet" href="../../other.css"></head><body>tap</body></html>',
                            encoding="utf-8")
            code, made, saved = self.fetch("/brief/copy?sketch=club-boats")
            self.assertEqual(code, 200)
            self.assertEqual(saved, 'attachment; filename="club-boats-prototype.html"')
            self.assertIn("<style>body { color: navy; }</style>", made)
            self.assertNotIn("color: red", made, "another sketch's file is not this one's to send")
            self.assertIn("A copy of the prototype “club-boats”, made ", made)
            self.assertIn("Not in this copy: ../../other.css.", made)
            self.assertIn("position:fixed", made)
            self.assertNotIn("slipwaiFault", made, "the board's own reporter stays on the board")
            self.assertEqual(page.read_text(encoding="utf-8").count("slipwai-copy"), 0, "nothing is written")
            self.assertIn(' · <a class="quiet-link" href="/brief/copy?sketch=club-boats" download>Save a copy to '
                          "send</a></p>", self.get("/brief?sketch=club-boats")[1])
            self.assertEqual(self.fetch("/brief/copy?sketch=..")[0], 404)

    def drawn(self) -> Path:
        home = self.root / "specs" / "001-booking" / "mockups"
        home.mkdir(parents=True)
        (self.root / "docs" / "design").mkdir(parents=True)
        (self.root / "docs" / "design" / "styles.css").write_text("article { margin: 0; }", encoding="utf-8")
        (self.root / "harbour.css").write_text("body { color: red; }", encoding="utf-8")
        (home / "booking.html").write_text(
            '<html><head><title>Mock: Booking</title><link rel="stylesheet" href="../../../docs/design/styles.css">'
            '<link rel="stylesheet" href="../../../harbour.css"></head><body><article class="state"><h2>Empty</h2>'
            "</article></body></html>", encoding="utf-8")
        (home / "storyboard.html").write_text(
            '<html><head><title>Storyboard</title></head><body><iframe sandbox src="booking.html"></iframe>'
            "</body></html>", encoding="utf-8")
        return home

    def test_the_voyage_offers_the_storyboard_as_a_file_and_serves_it_with_where_its_verdict_stood(self) -> None:
        home = self.drawn()
        card = mockups_card(mockups(self.root, self.seat), self.root)
        address = f"/copy/by/{self.seat}/specs/001-booking/mockups/storyboard.html"
        self.assertIn(f'<a href="{address}" download>Save a copy to send</a> — 001-booking: one file', card)
        code, made, saved = self.fetch(address)
        self.assertEqual(code, 200)
        self.assertEqual(saved, 'attachment; filename="001-booking-storyboard.html"')
        self.assertIn("A copy of the storyboard for 001-booking, made ", made)
        self.assertIn("It is not approved yet. Verdicts are given on the board, not on this copy.", made)
        inside = html.unescape(made.split('srcdoc="', 1)[1].split('"', 1)[0])
        self.assertIn("<style>article { margin: 0; }</style>", inside, "what the project was handed is carried")
        self.assertNotIn("color: red", inside, "and what `/mockups/` refuses, a copy refuses")
        self.assertIn("Not in this copy: ../../../harbour.css.", made)
        (home / "mock-states.md").write_text("- Booking / Empty — approved\n", encoding="utf-8")
        self.assertEqual(standing(self.root, "001-booking"), ("approved", ""))
        self.assertIn("It is approved.", self.fetch(address)[1])
        (home / "mock-states.md").write_text("- Booking / Empty — parked: too busy\n", encoding="utf-8")
        self.assertEqual(copy_said(self.root, "001-booking"), "It was disapproved: too busy.")
        self.assertIn("a mock-up for 001-booking", self.fetch(address.replace("storyboard", "booking"))[1])

    def test_only_a_mock_up_page_is_copied(self) -> None:
        self.drawn()
        (self.root / "specs" / "001-booking" / "spec.md").write_text("# Booking", encoding="utf-8")
        for refused in ("specs/001-booking/spec.md", "docs/design/styles.css", "specs/001-booking/mockups/none.html",
                        "specs/001-booking/mockups/../../../harbour.json"):
            self.assertEqual(self.fetch(f"/copy/by/{self.seat}/{refused}")[0], 404, refused)


if __name__ == "__main__":
    unittest.main()
