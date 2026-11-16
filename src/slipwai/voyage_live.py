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
from typing import Any
from urllib.parse import unquote

from .adoption_card import adoption_card, strategy_dates
from .board_read import Read, read
from .decision_cards import polled as decisions_polled
from .decision_cards import tab as decision_tab
from .feedback_card import card as feedback_card
from .feedback_card import payload as feedback_payload
from .film import films_card, films_of
from .fleet_tab import fleet_tab
from .init_run import outside_session
from .live_page import look_html
from .live_page import window as slice_window
from .live_page import window_payload as slice_payload
from .on_you import streams_card, waiting
from .passage import stages
from .project.intake import ideas as intake_ideas
from .seats import parameter
from .settings_card import project_tabs, settings
from .slice_card import lit
from .trunk_remote import card as remote_card
from .try_card import card as try_card
from .try_card import payload as try_payload
from .try_card import trunk_head
from .voyage import counts, mockups, model_xml, running_app, screens, states_of
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


def able(board: Any, rows: list[dict[str, str]], fleet: dict) -> dict[str, bool]:
    """The flags that show the strip's buttons, and that the list of what waits on a person reads."""
    return {"launchable": board.launchable(), "castable": board.castable(rows, fleet),
            "stoppable": board.stoppable(fleet), "drawable": board.drawable(), "modelable": board.modelable(),
            "draftable": board.draftable()}


def passage(board: Any, found: list, rows: list[dict[str, str]], fleet: dict, flags: dict[str, bool],
            listed: dict[str, Any]) -> str:
    return voyage_payload(found, flags["launchable"], any(one.state == "working" for one in found),
                          flags["castable"], flags["stoppable"], flags["drawable"], board.made_of(rows, fleet)[1],
                          flags["modelable"], waiting=listed, draftable=flags["draftable"])


def voyage_json(board: Any) -> str:
    found, rows, _, fleet, _, kept = parts(board)
    flags = able(board, rows, fleet)
    return passage(board, found, rows, fleet, flags, waiting(board, fleet, flags, rows))


def lit_rows(board: Any, kept: Read) -> list[dict[str, str]]:
    """The slices with what only the run's own files say: each working slice's caption, and its film."""
    return lit(kept.rows, kept.folds, board.root, films_of(board.root, board.named_seat()))


def machinery(kept: Read, rows: list[dict[str, str]], stoppable: bool) -> str:
    return fleet_tab(kept.fleet, rows, kept.trunk, stoppable)


def live_json(board: Any) -> str:
    """Every band, each with its signature: the passage strip's state, the list of what waits on a person,
    the unread decisions, and the drawn bands the page swaps where their signature has moved."""
    found, _, fault, fleet, _, kept = parts(board)
    rows = lit_rows(board, kept)
    flags = able(board, kept.rows, fleet)
    listed = waiting(board, fleet, flags, kept.rows)
    cards, unread = decisions_polled(board.root)
    drawn = {"look": look_html(rows, kept.folds, kept.trunk),
             "points": feedback_points_card(kept.points),
             "work": work_card(rows, fault, set(listed["slices"])),
             "streams": streams_card(fleet),
             "expect": expect_card(found),
             "fleet": machinery(kept, rows, flags["stoppable"])}
    if cards:  # the tab exists only once there is a decision; the first one is a change of the page's shape
        drawn["decisions"] = cards
    return json.dumps({"passage": json.loads(passage(board, found, kept.rows, fleet, flags, listed)),
                       "waiting": listed, "decisions": unread, "model": model_said(kept.rows),
                       "bands": {name: {"said": signature(html), "html": html} for name, html in drawn.items()}})


def voyage(board: Any) -> str:
    """The window, drawn whole once; the bands in it are kept current by `live_json`."""
    found, _, fault, fleet, held, kept = parts(board)
    root, seat = board.root, board.named_seat()
    folds, films = kept.folds, films_of(root, seat)
    rows = lit(kept.rows, folds, root, films)
    flags = able(board, kept.rows, fleet)
    listed = waiting(board, fleet, flags, kept.rows)
    feature, made_of = board.made_of(rows, fleet)
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
                       decision_tab(root, band), points=kept.points, adopting=adopting,
                       dates="" if adopting else remote_card(root) + strategy_dates(root),
                       draftable=flags["draftable"], machinery=tab, streams=streams_card(fleet), waiting=listed)


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
    elif where == "/try.json":
        board.send(200, try_payload(board.root, board.named_seat()), JSON)
    else:
        return False
    return True
