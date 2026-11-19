"""The board, bound and driven: the harbour one is served from, and a window sitting at it.

Here rather than in a suite because there are two now, and the budget on a suite is the thing that said so.
`test_bridge` holds what each route answers; `test_run_window` holds what a run\'s own window is — a seat
each, the stop, who answers, and the bar that is not the board\'s. They are two subjects and one fixture,
and a fixture copied into the second file would be the duplication the one-suite rule existed to avoid.
"""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.bridge import serve
from slipwai.bridge_page import page
from slipwai.cli_fleet import config
from slipwai.fleet import board
from slipwai.project.harbour import harbour_config


def served(case: unittest.TestCase, root: Path, controls: bool = True) -> ThreadingHTTPServer:
    """A board serving `root` on a port of its own until `case` is over. The one way a suite starts a board
    it means to stop: four suites each wrote these lines, and three of them left the thread unjoined."""
    server = serve(root, "127.0.0.1", 0, controls=controls)
    serving = threading.Thread(target=server.serve_forever, daemon=True)
    serving.start()
    # Cleanups run last first, so these read upwards: stop serving, see the thread out, then close. Closed
    # first, the socket went from under a thread still selecting on it — WinError 10038, once a case.
    case.addCleanup(server.server_close)
    case.addCleanup(serving.join)
    case.addCleanup(server.shutdown)
    return server


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".slipwai").mkdir()
        # No stage here is ever a session of whatever agent this machine happens to have: a board under test
        # runs its stages as the children it always ran, unless a test hands a stage its own stand-in agent.
        launchable = mock.patch("slipwai.stage_session.launchable", return_value=None)
        launchable.start()
        self.addCleanup(launchable.stop)
        # Nor what this machine's own board installed under ~/.slipwai/agents: a row is able by the fake PATH alone.
        installed = mock.patch("slipwai.harness.INSTALLED", Path(tempfile.mkdtemp()) / "agents")
        installed.start()
        self.addCleanup(installed.stop)
        # Nor is a read kept between requests: a test writes a file and reads the board again at once, and a
        # board keeping its read for two seconds would answer from before the write. `test_live_board_read` holds
        # what keeping it does.
        fresh = mock.patch("slipwai.board_read.KEEP", 0.0)
        fresh.start()
        self.addCleanup(fresh.stop)
        # Nor what this machine has installed: no board under test asks it, whichever fixture started the
        # board — `checkout_packages.no_machine`, above.
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))

    def deck(self, fairway: str, *entries: logs.Entry) -> None:
        path = logs.deck_path(self.root, "ordering", fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def read(self, fairway: str) -> list[logs.Entry]:
        path = logs.deck_path(self.root, "ordering", fairway)
        return logs.fold(path.read_text(encoding="utf-8").splitlines())

    def rendered(self, controls: bool = True) -> str:
        held = config(self.root)
        return page(board(self.root, held), held, controls=controls)



class BoardTest(Fixture):
    """One board, driven from one window.

    Every request the suite makes carries a seat, because every request a browser makes carries one: a page
    loaded without a seat is answered with a redirect to the same page at a seat of its own, and a suite
    that read the unseated board would be testing the one path no person takes. The id is made up rather
    than fetched — a seat this board has not seen is a new window, which is what makes a reload after a
    restart work — and `seat=` on a call is how a test opens a second window.
    """

    def setUp(self) -> None:
        super().setUp()
        self.server = served(self, self.root)
        self.port = self.server.server_address[1]
        self.seat = "window-one"

    def at(self, path: str, seat: str | None = None) -> str:
        """That path on this board, carrying a window's seat — `seat=""` for a request that carries none."""
        seat = self.seat if seat is None else seat
        where, _, query = path.partition("?")
        asked = "&".join(bit for bit in (f"seat={seat}" if seat else "", query) if bit)
        return f"http://127.0.0.1:{self.port}{where}" + (f"?{asked}" if asked else "")

    def seats(self) -> dict:
        """The windows this board is holding, by the id each carries."""
        return self.server.RequestHandlerClass.bench.seats  # type: ignore[attr-defined]

    def get(self, path: str, seat: str | None = None) -> tuple[int, str]:
        with urllib.request.urlopen(self.at(path, seat), timeout=5) as answer:
            return answer.status, answer.read().decode("utf-8")

    def post(self, path: str, body: dict, seat: str | None = None) -> tuple[int, str]:
        request = urllib.request.Request(self.at(path, seat),
                                         data=json.dumps(body).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5) as answer:
                return answer.status, answer.read().decode("utf-8")
        except urllib.error.HTTPError as answer:
            with answer:  # closed here, or the warning filter turns a refusal into noise in every run
                return answer.code, answer.read().decode("utf-8")

