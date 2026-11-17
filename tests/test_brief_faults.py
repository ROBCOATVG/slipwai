"""A prototype that does not run says so: the reporter it is served with, and the names a page cannot declare."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import brief_faults, brief_session
from slipwai.brief_page import SCRIPT

PAGE = ("<!doctype html>\n<html>\n<head>\n<title>x</title>\n</head>\n<body>\n<script>\n{body}\n</script>\n"
        "</body></html>\n")


class ClashTest(unittest.TestCase):
    def test_a_name_the_browser_has_taken_is_found_with_its_line(self) -> None:
        found = brief_faults.clashes(PAGE.format(body="const a = 1;\nfunction top(){\n  return 1;\n}"))
        self.assertEqual([one["line"] for one in found], [9])
        self.assertIn("Identifier 'top' has already been declared", str(found[0]["message"]))
        for declared in ("let window = 1;", "const document = 2;", "class location {}", "async function top(){}"):
            self.assertTrue(brief_faults.clashes(PAGE.format(body=declared)), declared)

    def test_the_same_names_inside_a_block_or_as_a_property_are_nobody_s_fault(self) -> None:
        for fine in ("{\n  function top(){}\n}", "const topics = [];", "obj.top = 1;", "var x = window.top;",
                     "function topUp(){}", "  let top = 3;"):
            self.assertEqual(brief_faults.clashes(PAGE.format(body=fine)), [], fine)

    def test_a_page_that_is_not_there_has_no_fault(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            self.assertIsNone(brief_faults.fault(Path(home) / "index.html"))


class ReporterTest(unittest.TestCase):
    def test_the_reporter_goes_in_after_the_head_on_one_line_so_the_page_s_lines_keep_their_numbers(self) -> None:
        page = PAGE.format(body="function top(){}").encode()
        served = brief_faults.with_reporter(page)
        self.assertEqual(served.count(b"\n"), page.count(b"\n"))
        self.assertIn(b"<head><script>(function(){", served)
        self.assertEqual(served.replace(brief_faults.REPORTER.encode(), b""), page)
        self.assertTrue(brief_faults.with_reporter(b"<p>bare</p>").startswith(b"<script>"))

    def test_only_a_prototype_s_page_is_served_with_it(self) -> None:
        with tempfile.TemporaryDirectory() as held:
            home = Path(held)
            for name in ("prototype/index.html", "brief/prd.html", "prototype/look.css"):
                (home / name).parent.mkdir(parents=True, exist_ok=True)
                (home / name).write_text("<head></head>", encoding="utf-8")
            sent = {name: brief_faults.outgoing(home / name, kind, "prototype")
                    for name, kind in (("prototype/index.html", "text/html; charset=utf-8"),
                                       ("brief/prd.html", "text/html; charset=utf-8"),
                                       ("prototype/look.css", "text/css; charset=utf-8"))}
        self.assertIn(b"slipwaiFault", sent["prototype/index.html"])
        self.assertEqual(sent["brief/prd.html"], b"<head></head>")
        self.assertEqual(sent["prototype/look.css"], b"<head></head>")

    def test_the_page_takes_a_fault_only_from_its_own_frame_and_says_it_only_when_asked(self) -> None:
        self.assertIn("const now = known || seen;", brief_faults.SCRIPT, "the file's own line wins")
        self.assertIn("event.origin !== location.origin || event.source !== frame.contentWindow",
                      brief_faults.SCRIPT)
        self.assertIn("words.textContent =", brief_faults.SCRIPT, "what a prototype says is drawn as words")
        self.assertNotIn("innerHTML", brief_faults.SCRIPT)
        self.assertIn("new CustomEvent('brief-say'", brief_faults.SCRIPT)
        self.assertIn("document.addEventListener('brief-say', event => ask(event.detail));", SCRIPT)
        self.assertIn("new CustomEvent('brief-polled', {detail: said})", SCRIPT)
        self.assertNotIn("__FIX__", brief_faults.SCRIPT)
        self.assertIn(json.dumps(brief_faults.FIX), brief_faults.SCRIPT)


class BoardSideTest(BoardTest):
    def test_the_board_serves_the_reporter_shows_the_holder_and_the_poll_carries_the_fault(self) -> None:
        area = mock.patch.object(brief_session, "SKETCHES", Path(tempfile.mkdtemp()) / "sketches")
        with area:
            home = brief_session.prepared(brief_session.workspace("club-boats"))
            page = home / brief_session.PROTOTYPE / "index.html"
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(PAGE.format(body="function top(){}"), encoding="utf-8")
            code, served = self.get("/brief/files/club-boats/prototype/index.html")
            self.assertEqual(code, 200)
            self.assertIn("slipwaiFault", served)
            self.assertNotIn("slipwaiFault", page.read_text(encoding="utf-8"), "never written to the sketch")
            drawn = self.get("/brief?sketch=club-boats")[1]
            self.assertIn('<div class="fault" hidden role="alert">', drawn)
            self.assertIn('<a class="quiet-link" target="_blank" rel="noopener" '
                          'href="/brief/files/club-boats/prototype/index.html">Open the prototype in a full window',
                          drawn)
            self.assertIn('<p class="full"><button type="button" class="widen" aria-pressed="false">Show it full '
                          'width</button>', drawn)
            self.assertIn("#sketch.wide { grid-template-columns: minmax(0, 1fr); }", brief_faults.STYLE)
            self.assertIn("page.classList.toggle('wide', on)", brief_faults.SCRIPT)
            self.assertIn('<p class="full" hidden>', brief_faults.under("/x", False), "nothing drawn, no link yet")
            self.assertIn("full.hidden = frame.hidden;", brief_faults.SCRIPT)
            said = json.loads(self.get("/brief.json?sketch=club-boats")[1])
            self.assertEqual(said["fault"]["line"], 8)
            page.write_text(PAGE.format(body="{ function top(){} }"), encoding="utf-8")
            self.assertIsNone(json.loads(self.get("/brief.json?sketch=club-boats")[1])["fault"])


if __name__ == "__main__":
    unittest.main()
