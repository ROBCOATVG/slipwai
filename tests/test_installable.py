"""The board as something a browser will install, and what the installed window gets when it is not running.

Installing a page cannot start a server, and that is the whole difficulty: the icon in somebody's dock
opens a local URL, and where nothing is listening the browser's own answer is a connection error that tells
a person who does not open terminals nothing they can act on. So the three files a browser asks for are
served, and the one page the worker keeps is the page that says what has happened and what starts it.
"""
from __future__ import annotations

import json
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.bridge import serve
from slipwai.page_shell import (
    APP,
    ICON,
    INSTALL,
    MANIFEST,
    NOT_RUNNING,
    WORKER,
    WORKER_SOURCE,
    document,
    manifest,
    not_running,
)


class ManifestTest(unittest.TestCase):
    def test_it_is_a_manifest_a_browser_will_install_from(self) -> None:
        """Name, scope, a start URL and a display mode: the fields that decide whether the offer is made
        at all, rather than the ones that decide how it looks once it has been."""
        held = json.loads(manifest())
        self.assertEqual(held["start_url"], "/")
        self.assertEqual(held["scope"], "/")
        self.assertEqual(held["display"], "standalone")
        self.assertTrue(held["name"])
        self.assertTrue(held["icons"])

    def test_the_window_has_no_address_bar_because_typing_is_what_it_is_for_not_having(self) -> None:
        self.assertEqual(APP["display"], "standalone")

    def test_the_icon_is_one_a_platform_may_crop_as_well_as_one_it_may_not(self) -> None:
        purposes = {one["purpose"] for one in json.loads(manifest())["icons"]}
        self.assertEqual(purposes, {"any", "maskable"})


class WorkerTest(unittest.TestCase):
    def test_the_only_page_it_keeps_is_the_one_saying_the_board_is_not_running(self) -> None:
        """A dashboard is a fold of files that change under it. A worker that served yesterday's board out
        of a cache would be the one view on it that is a memory rather than a reading."""
        self.assertIn(f"const PAGE = '{NOT_RUNNING}'", WORKER_SOURCE)
        self.assertEqual(len(re.findall(r"cache\.add", WORKER_SOURCE)), 1)
        for route in ("/board.json", "/packages", "/generate", "/adopt"):
            self.assertNotIn(route, WORKER_SOURCE)

    def test_it_answers_a_navigation_and_leaves_everything_else_alone(self) -> None:
        self.assertIn("event.request.mode !== 'navigate'", WORKER_SOURCE)

    def test_it_falls_back_only_where_the_fetch_failed_outright(self) -> None:
        """A 404 from the board is the board's own answer, and the worker has nothing to add to it."""
        self.assertIn("fetch(event.request).catch(", WORKER_SOURCE)


class NotRunningTest(unittest.TestCase):
    def test_it_says_what_starts_the_board(self) -> None:
        from slipwai.assets import this_command
        from slipwai.page_shell import esc
        said = not_running()
        self.assertIn(esc(this_command()), said, "a quoted path is escaped the way the page escapes everything")
        self.assertIn("Nothing is serving the board", said)

    def test_it_does_not_ask_to_be_installed_while_it_is_the_page_that_is_showing(self) -> None:
        """It is served from a cache with no board behind it: a manifest link there is a route that 404s."""
        self.assertNotIn(MANIFEST, not_running())


class PageTest(unittest.TestCase):
    def test_a_served_page_offers_the_install_and_registers_the_worker(self) -> None:
        said = document("Board", "sub", "<p>body</p>", now="/")
        self.assertIn(f'<link rel="manifest" href="{MANIFEST}">', said)
        self.assertIn(f"navigator.serviceWorker.register('{WORKER}')", said)
        self.assertIn(INSTALL, said)

    def test_the_offer_is_hidden_until_the_browser_makes_one(self) -> None:
        """A button that explained why this browser will not install anything would be a page arguing with
        somebody about their browser. Shown when there is an offer to pass on, and not otherwise."""
        self.assertIn("hidden", INSTALL)
        self.assertIn("beforeinstallprompt", document("Board", "sub", "", now="/"))

    def test_it_does_not_say_install_beside_a_tab_of_things_to_install(self) -> None:
        self.assertIn("Install this board", INSTALL)

    def test_the_published_copy_carries_neither(self) -> None:
        """One file on somebody's Pages site: a manifest link would 404, and an install offer would install
        a copy of a board that is not theirs."""
        said = document("Bridge", "sub", "<p>body</p>")
        self.assertNotIn("manifest", said)
        self.assertNotIn("serviceWorker", said)


class ServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".slipwai").mkdir()
        self.server = serve(self.root, "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path: str) -> tuple[int, str, str]:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as answer:
            return answer.status, answer.headers.get("Content-Type", ""), answer.read().decode("utf-8")

    def test_each_file_is_served_as_what_it_is(self) -> None:
        """A browser decides whether to offer the install on the content type as much as on the content."""
        for path, kind in ((MANIFEST, "application/manifest+json"), (WORKER, "text/javascript"),
                           (ICON, "image/svg+xml"), (NOT_RUNNING, "text/html")):
            code, said, _ = self.get(path)
            self.assertEqual(code, 200, path)
            self.assertTrue(said.startswith(kind), f"{path} served as {said}")

    def test_the_icon_is_the_mark(self) -> None:
        _, _, said = self.get(ICON)
        self.assertIn("<svg", said)
        self.assertIn("slipwai", said)

    def test_the_read_only_copy_serves_none_of_it(self) -> None:
        server = serve(self.root, "127.0.0.1", 0, controls=False)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        for path in (MANIFEST, WORKER, ICON, NOT_RUNNING):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5).close()
                self.fail(f"a read-only copy served {path}")
            except urllib.error.HTTPError as answer:
                with answer:
                    self.assertEqual(answer.code, 404)


if __name__ == "__main__":
    unittest.main()
