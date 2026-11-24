"""The Voyage window's routes: the page, and the one poll that keeps it current.

Each band of the page had a poll of its own — the strip `/voyage.json`, the Now strip `/now.json`, the work
`/work.json` — and each poll read the run from the start; the Fleet tab, the Decisions count, the feedback
points and "What to expect" had none and stood still until a reload. Now one request, `/live.json`, answers
for every band at once out of one read of the project (`board_read`), each band with the signature the page
compares it by, so a window swaps only what moved. `/voyage.json` is kept as it was for anything that reads
it; the page itself no longer asks for it.

Try it and Feedback keep their own polls: their cards are drawn by modules of their own that run their
own scripts, and a band here would be a second renderer of each to keep in step.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from . import page_copy
from .adoption_card import adoption_card, strategy_dates
from .board_read import Read, read
from .captains_strip import strip_html
from .decision_cards import polled as decisions_polled
from .decision_cards import tab as decision_tab
from .feedback_card import card as feedback_card
from .feedback_card import payload as feedback_payload
from .film import films_card, films_of
from .fleet_tab import fleet_tab
from .init_run import outside_session
from .launch_lock import unlock
from .live_page import look_html
from .live_page import window as slice_window
from .live_page import window_payload as slice_payload
from .on_you import streams_card, waiting
from .passage import stages
from .project.intake import ideas as intake_ideas
from .seats import parameter
from .settings_card import project_tabs, settings
from .slice_card import lit
from .storyboard_card import copy_said, live
from .storyboard_card import payload as talk_payload
from .trunk_card import band_html as trunk_band
from .trunk_card import mend_card
from .trunk_remote import card as remote_card
from .try_card import card as try_card
from .try_card import payload as try_payload
from .try_card import trunk_head
from .voyage import (
    counts,
    design_file,
    mockup_file,
    mockup_where,
    mockups,
    model_xml,
    running_app,
    screens,
    states_of,
)
from .voyage_page import band, expect_card, feedback_points_card, model_said, signature, work_card
from .voyage_page import page as voyage_page
from .voyage_page import payload as voyage_payload

JSON = "application/json; charset=utf-8"


def parts(board: Any) -> tuple[list, list[dict[str, str]], str, dict, dict, Read]:
    """The stages, the slices, the fault, the fleet and its settings — from the project's one kept read,
    with the stages read per request, since they carry this board's own child."""
    kept = read(board.root)
    found = stages(board.root, board.receipt() if board.fitting or outside_session(board.root) else None,
                   kept.fleet, counts(kept.rows))
    return found, kept.rows, kept.fault, kept.fleet, kept.config, kept


def able(board: Any, rows: list[dict[str, str]], fleet: dict) -> dict[str, Any]:
    """The flags that show the strip's buttons, and that the list of what waits on a person reads; `held` is
    why Continue the build is locked, which the strip shows beside it rather than hiding it (`launch_lock`)."""
    launchable = board.launchable()
    return {"launchable": launchable, "held": "" if launchable else board.held_back(),
            "castable": board.castable(rows, fleet),
            "stoppable": board.stoppable(fleet), "drawable": board.drawable(), "modelable": board.modelable(),
            "draftable": board.draftable()}


def shaped(made_of: str, decided: bool, running: str = "") -> str:
    """The page's shape with whether its Decisions tab exists: the tab, its styles and its script are drawn
    only once there is a decision, so the first one changes which cards the page has — a reload, as a file
    appearing is — where every later one only moves the band and the count the poll already swaps.

    And with the stage that has a tab of its own, while it runs: its start puts a card in its result's place,
    and its end puts the result there, each a reload. While it runs what it writes is not the shape: a page
    reloaded at every surface it wrote would be eight reloads of a card that says the same thing."""
    return f"{running}|{'d' if decided else ''}" if running else f"{made_of}|{'d' if decided else ''}"


def passage(board: Any, found: list, rows: list[dict[str, str]], fleet: dict, flags: dict[str, Any],
            listed: dict[str, Any], decided: bool) -> str:
    return voyage_payload(found, flags["launchable"], any(one.state == "working" for one in found),
                          flags["castable"], flags["stoppable"], flags["drawable"],
                          shaped(board.made_of(rows, fleet)[1], decided, live(board)["running"]),
                          flags["modelable"], waiting=listed,
                          draftable=flags["draftable"], writing=writing(board), held=flags["held"])


def writing(board: Any) -> bool:
    """Whether a turn of conversation with a stage is under way on this board, or in another window of this
    project: what it writes is the page's shape, and the page reloads once it has ended and not at each file."""
    fitting = board.fitting
    said = fitting.said(10 ** 9) if fitting is not None else None
    if said is not None and not said["done"]:
        return bool(said.get("talking"))
    return outside_session(board.root) is not None


def voyage_json(board: Any) -> str:
    found, rows, _, fleet, _, kept = parts(board)
    flags = able(board, rows, fleet)
    return passage(board, found, rows, fleet, flags, waiting(board, fleet, flags, rows, trunk=kept.trunk),
                   bool(decisions_polled(board.root)[0]))


def lit_rows(board: Any, kept: Read) -> list[dict[str, str]]:
    """The slices with what only the run's own files say: each working slice's caption, and its film."""
    return lit(kept.rows, kept.folds, board.root, films_of(board.root, board.named_seat()))


def machinery(kept: Read, rows: list[dict[str, str]], stoppable: bool) -> str:
    return fleet_tab(kept.fleet, rows, kept.trunk, stoppable) + mend_card(kept.trunk)


def live_json(board: Any) -> str:
    """Every band, each with its signature: the passage strip's state, the list of what waits on a person,
    the unread decisions, and the drawn bands the page swaps where their signature has moved."""
    found, _, fault, fleet, _, kept = parts(board)
    rows = lit_rows(board, kept)
    flags = able(board, kept.rows, fleet)
    listed = waiting(board, fleet, flags, kept.rows, trunk=kept.trunk)
    cards, unread = decisions_polled(board.root)
    drawn = {"trunk": trunk_band(kept.trunk), "look": look_html(rows, kept.folds, kept.trunk),
             "points": feedback_points_card(kept.points),
             "work": work_card(rows, fault, set(listed["slices"])),
             "streams": streams_card(fleet),
             "captains": strip_html(board.root, kept.rows, set(listed["slices"])),
             "expect": expect_card(found),
             "fleet": machinery(kept, rows, flags["stoppable"])}
    if cards:  # the tab exists only once there is a decision; the first one is a change of the page's shape
        drawn["decisions"] = cards
    return json.dumps({"passage": json.loads(passage(board, found, kept.rows, fleet, flags, listed, bool(cards))),
                       "waiting": listed, "decisions": unread, "model": model_said(kept.rows),
                       "bands": {name: {"said": signature(html), "html": html} for name, html in drawn.items()}})


def voyage(board: Any) -> str:
    """The window, drawn whole once; the bands in it are kept current by `live_json`."""
    found, _, fault, fleet, held, kept = parts(board)
    root, seat = board.root, board.named_seat()
    folds, films = kept.folds, films_of(root, seat)
    rows = lit(kept.rows, folds, root, films)
    flags = able(board, kept.rows, fleet)
    listed = waiting(board, fleet, flags, kept.rows, trunk=kept.trunk)
    feature, made_of = board.made_of(rows, fleet)
    decided = decision_tab(root, band)
    now = live(board)
    made_of = shaped(made_of, bool(decided[0]), now["running"])
    xml, note = model_xml(root, states_of(rows))
    running = bool(board.fitting and not board.fitting.said()["done"])
    adopting = adoption_card(root, running)
    tab = band("fleet", machinery(kept, rows, flags["stoppable"])) + settings(
        fleet["pressure"], held, True, project_tabs(root, True))
    # The frames are the one thing on this page the browser fetches without a script's help, so the seat
    # goes on their addresses here: a frame that asked unseated would be shown another window's project.
    return voyage_page(root, found, rows, fault, xml, note, "", board.made(), flags["launchable"], fleet, held,
                       mockups(root, seat), flags["castable"], flags["stoppable"], feature, flags["drawable"],
                       made_of, intake_ideas(root), screens(root, rows, seat), running_app(root),
                       flags["modelable"], try_card(root, seat), look_html(rows, folds, kept.trunk),
                       films_card(films, rows, fleet.get("demo_due_in"))
                       + feedback_card(root, rows, fleet, board.triaging(), trunk_head(root)),
                       decided, points=kept.points, adopting=adopting,
                       dates="" if adopting else remote_card(root) + strategy_dates(root),
                       draftable=flags["draftable"], machinery=tab, streams=streams_card(fleet), waiting=listed,
                       captains=strip_html(root, kept.rows, set(listed["slices"])), stage=now,
                       trunk=trunk_band(kept.trunk), locked=flags["held"],
                       unlocking=unlock(root, flags["held"], seat))


def route_get(board: Any, where: str, query: str) -> bool:
    """Answer one of the Voyage window's GETs, or say it was not one."""
    if where == "/voyage":
        board.send(200, voyage(board))
    elif where == "/voyage.json":
        board.send(200, voyage_json(board), JSON)
    elif where == "/live.json":
        board.send(200, live_json(board), JSON)
    elif where in ("/slice", "/slice.json"):
        fairway, named = unquote(parameter(query, "fairway")), unquote(parameter(query, "slice"))
        if where == "/slice":
            board.send(200, slice_window(board.root, fairway, named))
        else:
            board.send(200, slice_payload(board.root, fairway, named), JSON)
    elif where == "/feedback.json":
        kept = read(board.root)
        board.send(200, feedback_payload(board.root, kept.rows, kept.fleet, board.triaging()), JSON)
    elif where == "/stage/talk.json":  # a conversation with a stage, and whether it runs: `storyboard_card`
        since = parameter(query, "since")
        board.send(200, json.dumps(talk_payload(board, unquote(parameter(query, "command")),
                                                int(since) if since.isdigit() else 0)), JSON)
    elif where == "/try.json":
        board.send(200, try_payload(board.root, board.named_seat()), JSON)
    elif where.startswith(page_copy.ROUTE):
        board.send(*storyboard_copy(board, where.removeprefix(page_copy.ROUTE)))
    else:
        return False
    return True


def storyboard_copy(board: Any, where: str) -> tuple:
    """A mock-up page as one file to send, from the window its address names: what `/mockups/` would have
    served there, and reaching only what `/mockups/` serves."""
    named, rest = mockup_where(where)
    root = (board.bench.seat(named).root if named else board.root).resolve()
    path = mockup_file(root, rest)
    parts = path.relative_to(root).parts if path is not None and path.is_relative_to(root) else ()
    if len(parts) != 4 or parts[0] != "specs" or path is None or path.suffix.lower() != ".html":
        return 404, "No such mock-up page to copy.", "text/plain; charset=utf-8"

    def allowed(one: Path) -> bool:
        return one.is_relative_to(root) and design_file(root, one.relative_to(root).as_posix()) is not None

    return (200, *page_copy.storyboard(path, allowed, parts[1], copy_said(root, parts[1])))
