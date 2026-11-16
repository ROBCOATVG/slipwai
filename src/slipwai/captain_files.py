"""What a stream's captain decided, read from the files it decides through — and nothing where there are none.

The captain agent acts only by writing an order (`orders/<stream>/<id>.json`), which the captain program
checks and answers with `<id>.result.json` (`done` or `refused`, and why); what woke it is an event
(`events/<stream>/<id>.json`), closed by its orders or by the fixed rule (`<id>.closed.json`). That is the
contract both sides were built to (`docs/captain-agent-plan.md` §2.2), and this reads it without holding the
captain's code to anything more: a file that is not JSON, a field that is missing, a folder that is not
there are each simply nothing to show. A project whose captain is the program alone has no such folders,
and its window says so.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from . import talk
from .logs import run_dir

ORDERS = "orders"
EVENTS = "events"
#: The words a result has been seen to carry its outcome under, first that holds wins.
OUTCOME = ("result", "state", "outcome", "status")


def loaded(path: Path) -> dict[str, Any]:
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def folder(root: Path, kind: str, fairway: str) -> Path:
    return run_dir(root) / kind / fairway


def own(path: Path) -> bool:
    """An order or an event itself, not its answer."""
    return path.suffix == ".json" and not path.name.endswith((".result.json", ".closed.json")) \
        and not path.name.startswith(".")


def outcome(held: dict[str, Any]) -> str:
    return next((str(held[name]) for name in OUTCOME if isinstance(held.get(name), str) and held[name]), "")


def text_of(held: dict[str, Any]) -> str:
    return next((str(held[name]) for name in ("text", "why", "note", "words") if held.get(name)), "")


def orders(root: Path, fairway: str) -> list[dict[str, Any]]:
    """Every order this stream's captain gave, oldest first: what, for which slice, and what became of it."""
    home = folder(root, ORDERS, fairway)
    found = []
    for path in sorted(home.glob("*.json")) if home.is_dir() else []:
        if not own(path):
            continue
        held = loaded(path)
        if not held:
            continue
        result = loaded(path.with_name(f"{path.stem}.result.json"))
        found.append({"id": str(held.get("id") or path.stem), "t": str(held.get("t", "")),
                      "verb": str(held.get("verb") or held.get("kind") or held.get("order") or ""),
                      "slice": str(held.get("slice", "")), "text": text_of(held), "of": str(held.get("of", "")),
                      "event": str(held.get("event", "")), "result": outcome(result),
                      "why": str(result.get("why", ""))})
    return sorted(found, key=lambda one: (one["t"], one["id"]))


def events(root: Path, fairway: str) -> list[dict[str, Any]]:
    """Every event that woke it, oldest first, with how it was closed: by the captain, or by the rule."""
    home = folder(root, EVENTS, fairway)
    found = []
    for path in sorted(home.glob("*.json")) if home.is_dir() else []:
        if not own(path):
            continue
        held = loaded(path)
        if not held:
            continue
        closed = loaded(path.with_name(f"{path.stem}.closed.json"))
        found.append({"id": str(held.get("id") or path.stem), "t": str(held.get("t", "")),
                      "kind": str(held.get("kind", "")), "slice": str(held.get("slice", "")),
                      "by": str(closed.get("by", "")), "why": str(closed.get("why", "")), "closed": bool(closed)})
    return sorted(found, key=lambda one: (one["t"], one["id"]))


def agent(root: Path, fairway: str) -> bool:
    """Whether this stream has a captain agent: `harbour.json` says so, or it has decided something."""
    held = loaded(root / "harbour.json").get("captain")
    if isinstance(held, dict) and held.get("agent") is True:
        return True
    return folder(root, ORDERS, fairway).is_dir() or folder(root, EVENTS, fairway).is_dir()


def today(stamp: str) -> bool:
    try:
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return False
    return when.date() == datetime.now().astimezone().date()


#: An order said as a sentence, by its verb.
VERBS = {"start": "Started {slice}", "message": "Told {slice}", "retry": "Retried {slice}", "park": "Parked {slice}",
         "pause": "Paused {slice}", "resume": "Resumed {slice}", "stop": "Stopped {slice}", "say": "Said to you",
         "ask": "Asked you", "allow": "Allowed what was asked", "refuse": "Refused what was asked",
         "none": "Left it to the rule"}


def decided_today(root: Path, fairway: str) -> list[dict[str, str]]:
    """What the captain decided today, newest first, each a sentence: its orders with what became of them,
    and each event the rule closed in its place."""
    lines = []
    for one in orders(root, fairway):
        if not today(one["t"]):
            continue
        # The sentence is ours and the slice only fills it: an order's own words are never the template.
        known = VERBS.get(one["verb"])
        said = known.replace("{slice}", one["slice"] or "a slice") if known else (one["verb"] or "An order")
        said += f": {one['text']}" if one["text"] else ""
        refused = f"refused: {one['why']}" if one["why"] else "refused"
        after = {"done": "done", "refused": refused}.get(one["result"], "")
        lines.append({"t": one["t"], "text": said, "after": after or "waiting for the program",
                      "tone": "bad" if one["result"] == "refused" else "good" if one["result"] == "done" else "wait"})
    for one in events(root, fairway):
        if today(one["t"]) and one["by"] == "rule":
            what = f"{one['kind']} · {one['slice']}" if one["slice"] else one["kind"]
            lines.append({"t": one["t"], "text": f"The rule decided {what}", "after": one["why"], "tone": "quiet"})
    return sorted(lines, key=lambda one: one["t"], reverse=True)


def routes(root: Path, fairway: str) -> dict[str, list[str]]:
    """Where a captain sent each message on, by the id of what it routed — its orders that name it, and the
    messages in its slices' inboxes that carry it (`via` the captain, `of` the id) — read once for them all."""
    found: dict[str, list[str]] = {}
    for one in orders(root, fairway):
        if one["of"] and one["slice"] and one["result"] != "refused":
            found.setdefault(one["of"], []).append(one["slice"])
    for slice_id in talk.conversations(run_dir(root), fairway):
        if slice_id == talk.CAPTAIN:
            continue
        for one in talk.inbox(talk.place(run_dir(root), fairway, slice_id)):
            if one.get("of") and one.get("via"):
                found.setdefault(str(one["of"]), []).append(slice_id)
    return {ident: list(dict.fromkeys(named)) for ident, named in found.items()}


def routed(root: Path, fairway: str, ident: str) -> list[str]:
    """The slices a captain sent one message on to."""
    return routes(root, fairway).get(ident, [])


def said_to_you(root: Path, fairway: str) -> list[dict[str, str]]:
    """What the captain said or asked a person, through its `say` and `ask` orders, oldest first."""
    return [{"t": one["t"], "id": one["id"], "verb": one["verb"], "text": one["text"]}
            for one in orders(root, fairway) if one["verb"] in ("say", "ask") and one["text"]]
