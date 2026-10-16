"""`slipwai bridge`: the board as a page you can answer from, served by the standard library.

The point of the page is not that it is prettier than the terminal. It is that a person answers from one
seat: a question from a stream is a line in that stream's deck log, and finding the right terminal to type
into is the friction that has questions go unanswered for an hour. Typing the answer here writes the `told`
line into the right log, and the stream's next boundary reads it.

**`http.server` and nothing else.** A dashboard that needed a web framework would be a dashboard most people
never ran. The whole server is a handful of routes and a render.

**Local by default, and it says so.** It binds the loopback address: the page has controls that change what
a run does, and a default that put those on a network somebody shares is a default that would be wrong once
and then permanently. `--host` is there for somebody who means it.

**Writes go through the same code the verbs do.** Ringing the telegraph calls `cli_telegraph.ring`, and the
fine-tune panel calls `set_one`. A second path that wrote `harbour.json` its own way would be a second thing
to keep in step, and the first one to drift.

**One board, many seats.** The board is a server and a window is a person sitting at it, and the two were
the same thing for as long as this server kept one `root` on its handler class: a second window opened on
the same board looked wherever the first one had pointed it, and a generate in one moved the other. A seat
is a window — an id minted when a page is loaded without one and carried in that window's URL from then on
— and what belongs to a window belongs to its seat.

**What a seat owns, and what it does not.** A seat owns where it is looking, and nothing else, because
nothing else about the board is a property of the person looking. The streams, the logs, the telegraph and
the fine tune are folds of files on disk, and two windows open on the same project see the same run because
they both read it. `Outfit` — the `./init` this board started in a project, and whether its build has been
continued from here — is keyed by the project for the same reason: there is one such child per tree, not
one per person watching it, and a second window that could start a second would be two harbourmasters,
which `fleet.py` refuses and `launched` exists to prevent.
"""
from __future__ import annotations

import json
import mimetypes
import secrets
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from .adopt_page import looked
from .adopt_page import page as adoption
from .adopt_page import run as adopt
from .bridge_page import page, payload
from .chandlery_page import put
from .chandlery_page import served as chandlery
from .cli_telegraph import ring, set_one
from .deck import tell
from .dials import set_dial
from .errors import GenerationError
from .fleet import board
from .folder_choice import chosen
from .harbour import config
from .init_run import Fitting
from .init_run import assess as assess_idea
from .init_run import cast_off as start_fleet
from .init_run import draw as draw_surfaces
from .init_run import launch as continue_build
from .init_run import start as fit_out
from .init_run import stop as stop_fleet
from .interview_form import form
from .interview_form import page as interview
from .interview_page import NO_INIT, destination, elected_in, repository_for
from .interview_page import run as generate
from .landing_page import landing
from .page_shell import (
    ICON,
    MANIFEST,
    NOT_RUNNING,
    WORKER,
    WORKER_SOURCE,
    esc,
    icon,
    manifest,
    not_running,
)
from .passage import EVENT_PROFILE, drawn, modelled, profile_of, specifications, stages
from .project.intake import ideas as intake_ideas
from .seats import Bench, Outfit, Seat, parameter
from .spec_page import page as spec
from .telegraph import Refused
from .voyage import (
    MOCK_ROUTE,
    SCREEN_ROUTE,
    SPEC_ROUTE,
    counts,
    fleet_running,
    folded,
    mockup_file,
    mockups,
    model_xml,
    running_app,
    screen_file,
    screens,
    shape,
    spec_file,
    states_of,
    viewer_script,
)
from .voyage_page import now_said
from .voyage_page import page as voyage
from .voyage_page import payload as voyage_payload
from .wheel import set_stop

# budget: 630 — one server and every route the board answers, each a few lines handing off to a page
# module. The intake route is the voyage button for a feature handed to /sail.
# The number is the route count rather than any one route's length: a control a person can press is ten
# lines here — the guard that says why it cannot be pressed, and the call to whatever does it — and the
# board has gained the surfaces, the settings dials and the rendered specification since this was 560.
# or to a guarded read out of the project, plus the three reads a request makes through its seat
# (`seats.py` holds the table itself). A second server would be two things each sure they are the board,
# which `open_board` exists to prevent.
LIMIT = 4 * 1024 * 1024  # bytes a request body may be: a sentence, or a PRD riding in a generate's answers
#: The four an installable page is made of, each with what it is served as. A browser decides whether to
#: offer the install on the content type as much as the content, so none of these is served as HTML.
APP_FILES: dict[str, tuple[Callable[[], str], str]] = {
    MANIFEST: (manifest, "application/manifest+json; charset=utf-8"),
    WORKER: (lambda: WORKER_SOURCE, "text/javascript; charset=utf-8"),
    ICON: (icon, "image/svg+xml; charset=utf-8"),
    NOT_RUNNING: (not_running, "text/html; charset=utf-8"),
}


#: The pages a person sits on, each of which is given a seat on arrival. The data routes are not here on
#: purpose: a poll carries the seat of the page that made it, and a `curl /board.json` carries none and
#: should read the board rather than be redirected into a seat it would then have to keep.
SEATED: tuple[str, ...] = ("", "/index.html", "/voyage", "/generate", "/adopt", "/packages")


class Bridge(BaseHTTPRequestHandler):
    """The board's pages, the board as JSON, and the things a person can do from them to a run or to this
    machine's packages."""

    controls: bool = True
    server_version = "slipwai-bridge"
    #: This board's windows, and what is under way in each project they have been pointed at. Replaced per
    #: server by `serve`, so two boards in one process are two sets of windows.
    bench: Bench = Bench(Path("."))

    def named_seat(self) -> str:
        """Which window this request came from, off `?seat=<id>`.

        Empty where it carries none, and that is a seat too — the one a poller, a `curl` and the suite sit
        in. A request with no id is not a fault to refuse: it is somebody reading the board the way the
        board was always read before windows had names, and it reads the directory the board was started in.
        """
        return parameter(self.path.partition("?")[2], "seat")

    def seat(self) -> Seat:
        """This request's window. `seats.Bench.seat` says what an id this board has not seen means."""
        return self.bench.seat(self.named_seat())

    def minted(self, where: str, query: str) -> str:
        """The address a window with no seat is sent to: one of its own, at the directory it was opened on.

        `?look=<directory>` is how one window opens another on a project that is not the one it is looking
        at — the voyage link does it, because a run belongs in a window of its own and that window has to
        arrive already pointed at the right tree. It is read exactly once, here, by a seat that does not
        exist yet, and is gone from the address after this redirect; moving a seat that *does* exist is
        `/attach`, which is a POST, and stays one.

        A `look` at something that is not a directory is not refused. A refusal here would be a blank
        window with a sentence in it, where falling back to where the board was started is a window on the
        harbour with its "Looking at" box right there — which is the answer a person can act on.
        """
        named = secrets.token_urlsafe(8)
        looked = unquote(parameter(query, "look"))
        at = Path(looked).expanduser().resolve() if looked.strip() else self.bench.start
        self.bench.sit(named, at if at.is_dir() else self.bench.start)
        kept = "&".join(pair for pair in query.split("&") if pair and not pair.startswith("look="))
        return f"{where or '/'}?seat={named}{'&' + kept if kept else ''}"

    @property
    def root(self) -> Path:
        """Which directory this request's window is a view of. Read fresh per request and never cached,
        which is what lets a seat be moved with a sentence rather than a restart."""
        return self.seat().root

    def look(self, where: Path) -> None:
        """Point this request's window at a directory, and no other window with it."""
        self.seat().root = where

    def outfit(self, starting: bool = False) -> Outfit:
        """What is under way in the project this window is looking at."""
        return self.bench.outfit(self.root, starting)

    @property
    def fitting(self) -> Fitting | None:
        """The child this board last started in this project, and everything it has said."""
        return self.outfit().fitting

    @fitting.setter
    def fitting(self, one: Fitting | None) -> None:
        self.outfit(starting=True).fitting = one

    @property
    def launched(self) -> bool:
        """Whether this project's build has been continued from this board."""
        return self.outfit().launched

    @launched.setter
    def launched(self, one: bool) -> None:
        self.outfit(starting=True).launched = one

    def log_message(self, format: str, *args: Any) -> None:
        """Quiet. The run's log is the log; a request line per reload is noise over the top of it."""

    def send(self, code: int, body: str | bytes, kind: str = "text/html; charset=utf-8") -> None:
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def sent_to(self, where: str) -> None:
        """A redirect, which is how a window comes by its seat.

        The address bar is the only place a seat can live that a window keeps and a second window does not
        inherit: a cookie is one per browser rather than one per window, and anything a script stashed
        would be gone by the time the next page was asked for. So the first load of a page is answered with
        the same page at an address that names a seat, and from there the window carries it.
        """
        self.send_response(303)
        self.send_header("Location", where)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 — http.server's own spelling
        """A page, or the one line saying why there is none.

        The net is here rather than per route: a refusal that reached `http.server` closed the connection
        without a word, and a browser shows that as the board being broken. Every page this serves is a
        render of something read off disk, and anything on disk can be unreadable.
        """
        try:
            self.answer()
        except GenerationError as refused:
            self.send(500, f'<div class="card"><h2>This page could not be put together</h2>'
                           f"<p>{esc(refused)}</p></div>")

    def answer(self) -> None:
        where, _, query = self.path.partition("?")
        where = where.rstrip("/")
        # Before any of the routes, because every one of them below reads `self.root`, and which directory
        # that is, is a question only a seated window has an answer to.
        if where in SEATED and self.controls and not self.named_seat():
            self.sent_to(self.minted(where, query))
            return
        if where == "/init.json" and self.controls:
            self.send(200, json.dumps(self.receipt(since(query))), "application/json; charset=utf-8")
            return
        if where == "/voyage" and self.controls:
            self.send(200, self.voyage())
            return
        if where == "/voyage.json" and self.controls:
            self.send(200, self.voyage_json(), "application/json; charset=utf-8")
            return
        # A screen the design review photographed, from the project. Bytes, not text: a picture is not
        # a document, and decoding it would be serving a different file.
        if where.startswith(SCREEN_ROUTE) and self.controls:
            path = screen_file(self.root, where.removeprefix(SCREEN_ROUTE))
            if path is None:
                self.send(404, "<p>No such screen.</p>")
                return
            kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send(200, path.read_bytes(), kind)
            return
        # A mock-up as the stage wrote it, from the project: a page, or the stylesheet beside it.
        if where.startswith(MOCK_ROUTE) and self.controls:
            path = mockup_file(self.root, where.removeprefix(MOCK_ROUTE))
            if path is None:
                self.send(404, "<p>No such mock-up.</p>")
                return
            kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send(200, path.read_text(encoding="utf-8", errors="replace"),
                      f"{kind}; charset=utf-8" if kind.startswith("text/") else kind)
            return
        # The specification, as the agent wrote it. Plain text rather than rendered: the keel has no
        # markdown renderer and should not grow one to show somebody a file they are about to agree to,
        # and a browser shows this one readably as it stands.
        if where.startswith(SPEC_ROUTE) and self.controls:
            path = spec_file(self.root, where.removeprefix(SPEC_ROUTE))
            if path is None:
                self.send(404, "<p>No specification under that feature.</p>")
                return
            # Rendered, not served: Continue the build is a person's word that this document is good, and
            # a page that asks for that word and hands back `text/plain` is asking them to read markup.
            # Against the resolved root: `spec_file` resolves, and on a machine whose temporary directory
            # is a symlink — every macOS one — an unresolved root is not a parent of it.
            self.send(200, spec(path.relative_to(self.root.resolve()).as_posix(),
                                path.read_text(encoding="utf-8", errors="replace")))
            return
        if where == "/drawio-viewer.js" and self.controls:
            script, fault = viewer_script()
            self.send(503 if fault else 200, fault or script.decode("utf-8", "replace"),
                      "text/plain; charset=utf-8" if fault else "text/javascript; charset=utf-8")
            return
        if where == "/board.json":
            held = config(self.root)
            self.send(200, payload(board(self.root, held)), "application/json; charset=utf-8")
            return
        # Generation is the one thing on this server that is not a fold of the logs, and it is here rather
        # than on a server of its own because the two things a person does before there is anything to
        # watch are the two the board could not do.
        if where == "/generate" and self.controls:
            self.send(200, interview({}, root=self.root))
            return
        if where == "/adopt" and self.controls:
            self.send(200, adoption({"root": str(self.root.resolve())}))
            return
        # What a browser asks for before it will offer to install the board, and the page the installed
        # window is given when nothing is serving. Routes rather than files, because the board is a server
        # and has no directory beside the page to put a manifest in.
        if where in APP_FILES and self.controls:
            body, kind = APP_FILES[where]
            self.send(200, body(), kind)
            return
        # The chandlery, for the same reason generation is here: a person who typed one word and got a board
        # has no terminal open to type `slipwai search` into, and a board that could only show them what is
        # already installed would be the page telling them to go back to it.
        if where == "/packages" and self.controls:
            self.send(200, chandlery())
            return
        if where not in ("", "/index.html"):
            self.send(404, "<p>Nothing here. The board serves /, /generate, /adopt, /packages, "
                           "/board.json and /init.json.</p>")  # and the four an installable page is made of
            return
        held = config(self.root)
        if not self.controls:  # the published copy: the live cards alone, nothing to press
            self.send(200, page(board(self.root, held), held, controls=False))
            return
        self.send(200, landing(str(self.root.resolve()), self.root.resolve().name, now_said(self.voyage_parts()[0]),
                               (self.root / "project.json").is_file()))

    def land(self, answers: dict[str, str], out: str) -> str:
        """Move the board into the project that was just made, and start the step that finishes it.

        A window is a view of one directory, and the moment a generate succeeds the directory worth looking
        at is the new one: everything the page can do next — its streams, its telegraph, its fine tune — is
        about that project rather than about wherever the board happened to be started. Every request reads
        its seat's root fresh, nothing being cached anywhere, so landing is one assignment and the next page
        served to *this* window is the new project's. Another window is somebody else at another desk and
        does not move: a generate in one tab that re-pointed every open tab was the thing seats are for.

        `./init` is then started in it as a child that outlives this request, because it installs Spec Kit
        over the network and a POST held open for minutes is a page a person reloads and a page that loses
        what it was doing. What it says is read from `/init.json` instead, by the card the board now carries.
        """
        where = destination(answers, self.root)
        named = answers.get("init") or NO_INIT
        self.look(where)
        self.launched = False
        self.fitting = fit_out(where, None if named == NO_INIT else named, out.splitlines(),
                               repository_for(answers), prd=bool(str(answers.get("prd") or "").strip()),
                               extensions=elected_in(answers))
        return "\n".join(self.fitting.said()["lines"]) if self.fitting else out

    def active_feature(self) -> Path | None:
        """The feature Continue the build is about: the one `.specify/feature.json` names, else the only
        specification that has no chart yet."""
        pointer = self.root / ".specify/feature.json"
        try:
            held = json.loads(pointer.read_text(encoding="utf-8"))
            named = (self.root / str(held.get("feature_directory") or "")).resolve()
            if named.is_relative_to(self.root.resolve()) and (named / "spec.md").is_file():
                return named
        except (OSError, ValueError, AttributeError):
            pass
        specs = specifications(self.root)
        uncharted = [path.parent for path in specs if not (path.parent / "chart.yaml").is_file()]
        if len(uncharted) == 1:
            return uncharted[0]
        return specs[0].parent if len(specs) == 1 else None

    def launchable(self) -> bool:
        """Whether the build can be continued from here: the active feature has a specification and no chart
        yet — on the event profile, a model too — nothing running or failed on this board, and not launched
        already."""
        feature = self.active_feature()
        if self.launched or feature is None or (feature / "chart.yaml").is_file():
            return False
        if self.fitting and (not self.fitting.said()["done"] or self.fitting.said()["code"]):
            return False
        return profile_of(self.root) != EVENT_PROFILE or modelled(self.root)

    def receipt(self, since: int = 0) -> dict:
        """What the board's child has said after the `since`th line, and whether the build can be continued."""
        if not self.fitting:
            return {"lines": [], "at": 0, "done": True, "step": "", "root": str(self.root),
                    "launchable": self.launchable()}
        said = self.fitting.said(since)
        said["launchable"] = self.launchable()
        said["root"] = str(self.root)
        return said

    def voyage_parts(self) -> tuple[list, list[dict[str, str]], str, dict, dict]:
        rows, fault = folded(self.root)
        held = config(self.root)
        fleet = {**board(self.root, held), "running": fleet_running(self.root)}
        found = stages(self.root, self.receipt() if self.fitting else None, fleet, counts(rows))
        return found, rows, fault, fleet, held

    def stoppable(self, fleet: dict) -> bool:
        """Whether there is a fleet here to stop: something of it alive, and no child of this board already
        on its way to stopping it. A second Stop while the first is still asking would be two asks and one
        answer, and the button would read as having done nothing."""
        return bool(fleet.get("running")) and (not self.fitting or self.fitting.said()["done"])

    def drawable(self) -> bool:
        """Whether the surfaces can be drawn from here: a specification to draw them from, nothing drawn
        yet, and no child of this board already on its way.

        Gone the moment there are drawings, and that is the point of it rather than a limit on it. What a
        storyboard nobody has looked at is waiting for is a person's verdict on each state, and there is no
        button that gives one: pressing this again would redraw the thing already waiting to be read.
        """
        idle = not self.fitting or self.fitting.said()["done"]
        return bool(specifications(self.root)) and not drawn(self.root) and idle

    def castable(self, rows: list[dict[str, str]], fleet: dict) -> bool:
        """Whether the fleet can be cast off from here: a split to work, nothing of it running, and no child
        of this board on the way."""
        idle = not self.fitting or self.fitting.said()["done"]
        return bool(rows) and not fleet.get("running") and idle and any(row["state"] != "done" for row in rows)

    def made_of(self, rows: list[dict[str, str]], fleet: dict) -> tuple[str, str]:
        """The feature this window is about, and the one-line signature of what its page is built out of —
        which the poll carries so that a page built before a file existed can tell, and reload."""
        specs = specifications(self.root)
        feature_path = self.active_feature()
        feature = feature_path.name if feature_path else (specs[0].parent.name if specs else "")
        return feature, shape(self.root, rows, fleet, feature, bool(self.made()))

    def voyage(self) -> str:
        found, rows, fault, fleet, held = self.voyage_parts()
        feature, made_of = self.made_of(rows, fleet)
        xml, note = model_xml(self.root, states_of(rows))
        # The frames are the one thing on this page the browser fetches without a script's help, so the
        # seat goes on their addresses here: a frame that asked unseated would be shown another window's
        # project inside this one's page.
        return voyage(self.root, found, rows, fault, xml, note, "", self.made(), self.launchable(), fleet, held,
                      mockups(self.root, self.named_seat()), self.castable(rows, fleet), self.stoppable(fleet),
                      feature, self.drawable(), made_of, intake_ideas(self.root),
                      screens(self.root, rows, self.named_seat()), running_app(self.root))

    def voyage_json(self) -> str:
        found, rows, _, fleet, _ = self.voyage_parts()
        return voyage_payload(found, self.launchable(), any(one.state == "working" for one in found),
                              self.castable(rows, fleet), self.stoppable(fleet), self.drawable(),
                              self.made_of(rows, fleet)[1])

    def attach(self, named: str) -> str:
        """Point this board at another directory, or say why it cannot be.

        Refused rather than attached where there is nothing there: a board looking at a path that does not
        exist is an empty harbour that says nothing is running, which is the one wrong answer it could give.
        """
        if not named.strip():
            raise ValueError("attaching needs a directory to attach to")
        where = Path(named).expanduser().resolve()
        if not where.is_dir():
            raise ValueError(f"{where} is not a directory on this machine")
        self.look(where)
        return f"looking at {where}"

    def made(self) -> dict | None:
        """What this board last made, for the card that says so — nothing, on a board that has made nothing."""
        return self.receipt() if self.fitting else None

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
            # The path without its query, because the seat rides there: `/tell?seat=hVn0` is the tell route.
            where = self.path.partition("?")[0].rstrip("/")
            if where == "/generate/ask":
                # The questions again, for the answers given so far: one of them decides what the next one
                # offers, and which that is, is the catalogue's business and not the browser's.
                self.send(200, form({str(a): str(b) for a, b in held.items()}, self.root))
                return
            if where == "/generate/run":
                answers = {str(a): str(b) for a, b in held.items()}
                worked, out = generate(answers, self.root)
                if worked:
                    out = self.land(answers, out)
                self.send(200 if worked else 400, out, "text/plain; charset=utf-8")
                return
            # The machine's own folder chooser, for the one answer on the form that is a path. A read,
            # and 200 whatever came back: cancelling is an answer — it means the field keeps what it had.
            if where == "/choose":
                self.send(200, chosen(Path(str(held.get("start") or "")).expanduser() or self.root),
                          "text/plain; charset=utf-8")
                return
            # Looking is a read and answers 200 whatever it found, refusal included: what it found is the
            # page's content, and a repository that cannot be adopted is a finding rather than a fault.
            if where == "/adopt/look":
                self.send(200, looked({str(a): str(b) for a, b in held.items()}, self.root))
                return
            if where == "/adopt/run":
                worked, out = adopt({str(a): str(b) for a, b in held.items()}, self.root)
                self.send(200 if worked else 400, out, "text/plain; charset=utf-8")
                return
            # Installing is the one control here that reaches a network, and it is still a call rather than
            # a child: `put` is the function each install verb calls, so the page and the verb stage, verify
            # and admit a package the one way. What it said is what the terminal would have printed.
            if where == "/packages/install":
                said = "\n".join(put(str(held.get("kind", "")), str(held.get("name", "")),
                                      bool(held.get("accept"))))
            # Where this board is looking, moved on purpose rather than by stopping it and starting it
            # again with `--root`. The same assignment `land` makes, and the only other thing that makes it.
            elif where == "/attach":
                said = self.attach(str(held.get("root", "")))
            # The one button a person presses between a drafted specification and a running fleet. The
            # receipt is carried into the new run, so the card keeps saying what was made and drafted.
            elif where == "/cast-off":
                _, rows, _, fleet, _ = self.voyage_parts()
                if not self.castable(rows, fleet):
                    raise ValueError("nothing to cast off: no split to work, or the fleet is already running")
                self.fitting = start_fleet(self.root, self.fitting.said()["lines"] if self.fitting else None)
                said = "casting off"
            # The pair of Cast off, and the one control here that ends something. It asks rather than kills:
            # `make cruise-stop` is `fleet.py stop`, which every captain reads at its next boundary, and a
            # captain killed mid-stage leaves a worktree half written with nothing saying so.
            # Who answers at one stop of the run, written by the project's own `scripts/agents/cruise.py`
            # — the script `/cruise-settings` runs, which validates the value and which `make check-agents`
            # holds. A second writer here would be the first one to drift from the project's own checker.
            elif where == "/wheel":
                said = set_stop(self.root, str(held.get("stop", "")), str(held.get("value", "")))
            # The same again for the two files the ladder reads, which had no control at all: how `/sail`
            # delegates, and which model runs which stage. Each written by its own project script.
            elif where == "/dial":
                said = set_dial(self.root, str(held.get("panel", "")), str(held.get("key", "")),
                                str(held.get("value", "")))
            elif where == "/stop":
                _, _, _, fleet, _ = self.voyage_parts()
                if not self.stoppable(fleet):
                    raise ValueError("nothing to stop: no captain of this fleet is running, or this board is "
                                     "already asking it to")
                self.fitting = stop_fleet(self.root, self.fitting.said()["lines"] if self.fitting else None)
                said = "asking the fleet to stop"
            # The one button between a specification a person has read and a storyboard they have not seen
            # yet. Half a stage: the drawing, which nobody has to be present for, and then the stop that is
            # the stage — which is why this ends with the strip amber rather than with a tick.
            elif where == "/intake":
                pending = [one for one in intake_ideas(self.root) if one.state not in ("specified", "kill")]
                if not pending:
                    raise ValueError("nothing waiting under docs/intake; hand the feature to /sail")
                idea = pending[0]
                if idea.state == "confirm":
                    path = self.root / "docs/intake" / idea.slug / "confirmed"
                    path.write_text("yes\nperson\n", encoding="utf-8")
                    said = f"confirmed {idea.slug}"
                elif idea.state in ("assessing", "go", "changed"):
                    if self.fitting and not self.fitting.said()["done"]:
                        raise ValueError("this board is already running something; wait for it to finish, "
                                         f"then press Continue the next feature for {idea.slug}")
                    self.fitting = assess_idea(self.root, idea.slug,
                                               self.fitting.said()["lines"] if self.fitting else None)
                    said = f"assessing {idea.slug}"
                else:
                    raise ValueError(f"{idea.slug} is {idea.state}; /sail is what moves an idea in that state")
            elif where == "/draw":
                if not self.drawable():
                    raise ValueError("nothing to draw: the surfaces are drawn from a specification under "
                                     "specs/, and once they are drawn what they wait on is your verdict on "
                                     "each state, which `/mockups` in the agent asks you for")
                self.fitting = draw_surfaces(self.root, self.fitting.said()["lines"] if self.fitting else None)
                said = "drawing the surfaces"
            elif where == "/launch":
                if not self.launchable():
                    raise ValueError("nothing to continue from here: a specification under specs/, written by "
                                     "`make draft` or with the agent, is what the build continues from")
                self.launched = True
                self.fitting = continue_build(self.root, self.fitting.said()["lines"] if self.fitting else None)
                said = "continuing the build"
            elif where == "/tell":
                said = tell(self.root, str(held.get("fairway", "")), str(held.get("message", "")))
            elif where == "/ring":
                ring(self.root, str(held.get("position", "")))
                said = f"rung to {held.get('position')}"
            elif where == "/set":
                pairs = held.get("pairs")
                if not isinstance(pairs, list):
                    raise ValueError("`pairs` is a list of `<name>=<value>`")
                set_one(self.root, [str(one) for one in pairs])
                said = "set"
            else:
                self.send(404, "No such control.", "text/plain; charset=utf-8")
                return
        except (ValueError, Refused, GenerationError, OSError) as fault:
            self.send(400, str(fault) or type(fault).__name__, "text/plain; charset=utf-8")
            return
        self.send(200, said, "text/plain; charset=utf-8")


def since(query: str) -> int:
    """How many lines the asker already has, off `?since=<n>`. Anything else is none of them, because a tail
    that answered a malformed poll with a refusal would be a board that stops updating and says nothing."""
    value = parameter(query, "since")
    return int(value) if value.isdigit() else 0


def serve(root: Path, host: str = "127.0.0.1", port: int = 8099,
          controls: bool = True) -> ThreadingHTTPServer:
    """A bound server, not yet serving. Returned rather than run so a test can drive it and close it.

    Its own `Bench` rather than the class's, because a mutable default on a base class is one object
    however many subclasses inherit it: two boards in one process — which is what the suite is — would
    otherwise be one board's windows seen through two ports.
    """
    handler = type("BoundBridge", (Bridge,), {"controls": controls, "bench": Bench(root)})
    return ThreadingHTTPServer((host, port), handler)
