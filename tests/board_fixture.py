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
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.bridge import serve
from slipwai.bridge_page import page
from slipwai.cli_fleet import config
from slipwai.fleet import board
from slipwai.project.harbour import harbour_config


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".slipwai").mkdir()
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))

    def deck(self, fairway: str, *entries: logs.Entry) -> None:
        path = self.root / logs.deck_path("ordering", fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def read(self, fairway: str) -> list[logs.Entry]:
        path = self.root / logs.deck_path("ordering", fairway)
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
        self.server = serve(self.root, "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        self.seat = "window-one"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)

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

