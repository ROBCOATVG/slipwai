"""`slipwai bridge`: the board as a page you can answer from, served by the standard library.

The point of the page is not that it is prettier than the terminal. It is that a person answers from one
seat: a question from a stream is a line in that stream's deck log, and finding the right terminal to type
into is the friction that has questions go unanswered for an hour. Typing the answer here writes the `told`
line into the right log, and the stream's next boundary reads it.

**`http.server` and nothing else.** A dashboard that needed a web framework would be a dashboard most people
never ran. The whole server is three routes and a render.

**Local by default, and it says so.** It binds the loopback address: the page has controls that change what
a run does, and a default that put those on a network somebody shares is a default that would be wrong once
and then permanently. `--host` is there for somebody who means it.

**Writes go through the same code the verbs do.** Ringing the telegraph calls `cli_telegraph.ring`, and the
fine-tune panel calls `set_one`. A second path that wrote `harbour.json` its own way would be a second thing
to keep in step, and the first one to drift.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .adopt_page import looked
from .adopt_page import page as adoption
from .adopt_page import run as adopt
from .bridge_page import page, payload
from .cli_fleet import config
from .cli_telegraph import ring, set_one
from .fleet import board
from .interview_page import form
from .interview_page import page as interview
from .interview_page import run as generate
from .logs import deck_path, entry
from .telegraph import Refused

LIMIT = 64 * 1024  # bytes a request body may be; nothing here takes more than a sentence


def feature_of(root: Path, fairway: str) -> str:
    """Which feature's directory this stream's log is in, or `''` where it has none yet."""
    place = root / ".slipwai/logs"
    for path in sorted(place.rglob(f"{fairway}.jsonl")) if place.is_dir() else []:
        return path.parent.name
    return ""


def tell(root: Path, fairway: str, message: str) -> str:
    """Write a person's message into that stream's deck log, or say why it could not be.

    Into the deck log rather than anywhere of its own: the log is what the captain reads at its next
    boundary, and a message somewhere else is a message nothing is watching.
    """
    if not fairway or not message.strip():
        raise ValueError("a message needs a stream to go to and something to say")
    feature = feature_of(root, fairway)
    if not feature:
        raise ValueError(f"{fairway} has no log here, so there is nowhere for this to go. "
                         f"A stream gets a log when its captain writes its first line")
    path = root / deck_path(feature, fairway)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(entry("told", fairway=fairway, message=message.strip()).line())
    return f"told {fairway}"


class Bridge(BaseHTTPRequestHandler):
    """Three routes: the page, the board as JSON, and the three things a person can do to a run."""

    root: Path = Path(".")
    controls: bool = True
    server_version = "slipwai-bridge"

    def log_message(self, format: str, *args: Any) -> None:
        """Quiet. The run's log is the log; a request line per reload is noise over the top of it."""

    def send(self, code: int, body: str, kind: str = "text/html; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 — http.server's own spelling
        where = self.path.rstrip("/")
        if where == "/board.json":
            held = config(self.root)
            self.send(200, payload(board(self.root, held)), "application/json; charset=utf-8")
            return
        # Generation is the one thing on this server that is not a fold of the logs, and it is here rather
        # than on a server of its own because the two things a person does before there is anything to
        # watch are the two the board could not do.
        if where == "/generate" and self.controls:
            self.send(200, interview({}))
            return
        if where == "/adopt" and self.controls:
            self.send(200, adoption({"root": str(self.root.resolve())}))
            return
        if where not in ("", "/index.html"):
            self.send(404, "<p>Nothing here. The board serves /, /generate, /adopt and /board.json.</p>")
            return
        held = config(self.root)
        self.send(200, page(board(self.root, held), held, controls=self.controls))

    def body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length > LIMIT:
            raise ValueError("that is more than this page ever sends")
        held = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        if not isinstance(held, dict):
            raise ValueError("a request body is an object")
        return held

    def do_POST(self) -> None:  # noqa: N802 — http.server's own spelling
        if not self.controls:
            self.send(403, "This copy is read only.", "text/plain; charset=utf-8")
            return
        try:
            held = self.body()
            if self.path.rstrip("/") == "/generate/ask":
                # The questions again, for the answers given so far: one of them decides what the next one
                # offers, and which that is, is the catalogue's business and not the browser's.
                self.send(200, form({str(a): str(b) for a, b in held.items()}))
                return
            if self.path.rstrip("/") == "/generate/run":
                worked, out = generate({str(a): str(b) for a, b in held.items()}, self.root)
                self.send(200 if worked else 400, out, "text/plain; charset=utf-8")
                return
            # Looking is a read and answers 200 whatever it found, refusal included: what it found is the
            # page's content, and a repository that cannot be adopted is a finding rather than a fault.
            if self.path.rstrip("/") == "/adopt/look":
                self.send(200, looked({str(a): str(b) for a, b in held.items()}, self.root))
                return
            if self.path.rstrip("/") == "/adopt/run":
                worked, out = adopt({str(a): str(b) for a, b in held.items()}, self.root)
                self.send(200 if worked else 400, out, "text/plain; charset=utf-8")
                return
            if self.path.rstrip("/") == "/tell":
                said = tell(self.root, str(held.get("fairway", "")), str(held.get("message", "")))
            elif self.path.rstrip("/") == "/ring":
                ring(self.root, str(held.get("position", "")))
                said = f"rung to {held.get('position')}"
            elif self.path.rstrip("/") == "/set":
                pairs = held.get("pairs")
                if not isinstance(pairs, list):
                    raise ValueError("`pairs` is a list of `<name>=<value>`")
                set_one(self.root, [str(one) for one in pairs])
                said = "set"
            else:
                self.send(404, "No such control.", "text/plain; charset=utf-8")
                return
        except (ValueError, Refused, OSError) as fault:
            self.send(400, str(fault) or type(fault).__name__, "text/plain; charset=utf-8")
            return
        self.send(200, said, "text/plain; charset=utf-8")


def serve(root: Path, host: str = "127.0.0.1", port: int = 8099,
          controls: bool = True) -> ThreadingHTTPServer:
    """A bound server, not yet serving. Returned rather than run so a test can drive it and close it."""
    handler = type("BoundBridge", (Bridge,), {"root": root, "controls": controls})
    return ThreadingHTTPServer((host, port), handler)
