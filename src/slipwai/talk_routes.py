"""The conversations' routes: the windows' polls, and everything a person says or does to a slice or a captain.

Here rather than in `bridge.py`, which is at its line budget, and in one place, because they are one thing:
each POST places one signed message in an inbox through `talk_said` and answers with what the route said and
the message's id, so whoever called can follow its receipt. `/tell` keeps the shape it had — a stream, a
message, a slice or a question's id — so the MCP tool, the board's answer boxes and anything else that posts
it keep working; it is only where the words go that changed.
"""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import unquote

from . import talk
from .captain_window import page as captain_page
from .captain_window import window_payload as captain_payload
from .captains_strip import heard as captain_heard
from .seats import parameter
from .talk_fold import heard as thread_heard
from .talk_fold import see
from .talk_page import SHOWN, dumps, payload
from .talk_said import answer, home, known, receipt_line, say, steer, tell, tell_every_captain

JSON = "application/json; charset=utf-8"
TEXT = "text/plain; charset=utf-8"


def route_get(board: Any, where: str, query: str) -> bool:
    """A conversation's poll, or a captain's window; or say it was not one of these."""
    fairway, named = unquote(parameter(query, "fairway")), unquote(parameter(query, "slice"))
    asked = parameter(query, "limit")
    limit = min(int(asked), 20000) if asked.isdigit() else SHOWN
    try:
        if where == "/talk.json":
            board.send(200, dumps(payload(board.root, fairway, named, limit=limit)), JSON)
        elif where == "/captain-window":
            board.send(*captain_page(board.root, fairway))
        elif where == "/captain-window.json":
            board.send(200, captain_payload(board.root, fairway, limit), JSON)
        else:
            return False
    except ValueError as fault:
        board.send(400, str(fault), TEXT)
    return True


def message_of(board: Any, fairway: str, slice_id: str, ident: str) -> dict[str, Any]:
    """A message already sent to this conversation, by its id."""
    found = next((one for one in talk.inbox(home(board.root, fairway, slice_id)) if str(one["id"]) == ident), None)
    if found is None or found.get("kind") != "say":
        raise ValueError(f"{slice_id or fairway} has no message {ident}")
    return found


def route_post(board: Any, where: str, held: dict[str, Any]) -> bool:
    """One thing a person did, placed as a signed message; `ValueError` says why it could not be."""
    root = board.root
    fairway, slice_id = str(held.get("fairway", "")), str(held.get("slice", "") or "")
    if where == "/tell":
        mode = "interrupt" if held.get("mode") == "interrupt" else "wait"
        replaces = str(held.get("replaces", "") or "")
        said = (answer(root, fairway, str(held["question"]), str(held.get("message", "")), replaces)
                if held.get("question") else
                tell(root, fairway, str(held.get("message", "")), slice_id, mode=mode, of=str(held.get("of", "") or ""),
                     replaces=replaces))
    elif where == "/talk/say":
        mode = "interrupt" if held.get("mode") == "interrupt" else "wait"
        sent = say(root, fairway, slice_id, str(held.get("text", "")), mode, talk.PERSON, str(held.get("of", "")))
        said = receipt_line(root, fairway, slice_id, sent)
    elif where == "/talk/steer":
        sent = steer(root, fairway, slice_id, str(held.get("kind", "")), str(held.get("why", "")),
                     str(held.get("of", "")))
        said = f"{sent['kind']} sent to {slice_id} · message {sent['id']}"
    elif where in ("/talk/interrupt", "/talk/again"):
        # Interrupt now: the queued one withdrawn and the same message sent to cut in. Send again: the same
        # message. Either way it stays whose it was — who sent it, through whom, what it routes and the words
        # it quotes — and only the mode changes: a captain's message re-sent as the person's would answer a
        # park and give a run back that a captain's words never do.
        was = message_of(board, fairway, slice_id, str(held.get("id", "")))
        if where == "/talk/interrupt":
            steer(root, fairway, slice_id, "withdraw", of=str(was["id"]))
        known(root, fairway)
        sent = talk.send(home(root, fairway, slice_id), "say", str(was.get("text", "")),
                         "interrupt" if where == "/talk/interrupt" else str(was.get("mode") or "wait"),
                         str(was.get("from") or talk.PERSON), of=str(was.get("of", "") or ""),
                         via=str(was.get("via", "") or ""), quote=str(was.get("quote", "") or ""),
                         quote_from=str(was.get("quote_from", "") or ""))
        said = receipt_line(root, fairway, slice_id, sent)
    elif where == "/talk/seen":
        try:
            count = int(held.get("heard", 0))
        except (TypeError, ValueError):
            raise ValueError("`heard` is how many lines the window showed") from None
        # Never more than the conversation holds: a count past it would silence the marker for good.
        most = (thread_heard(talk.thread(home(root, fairway, slice_id))) if slice_id
                else captain_heard(root, fairway))
        said = str(see(root, fairway, slice_id, min(count, most)))
    elif where == "/talk/all":
        record = tell_every_captain(root, str(held.get("message", "")))
        board.send(200, json.dumps(record, ensure_ascii=False), JSON)
        return True
    else:
        return False
    board.send(200, said, TEXT)
    return True
