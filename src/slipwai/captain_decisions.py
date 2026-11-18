"""What a stream's captain decided: each event it was woken for, how it was closed, the orders and their results.

A captain that is an agent leaves its decisions under the run folder (`docs/captain-agent-plan.md` 2.2): the
event the program wrote (`events/<fairway>/<id>.json`), the record that closed it (`<id>.closed.json`: `by`
the captain or the rule, why, and what it cost), and every order it gave (`orders/<fairway>/<id>.json`) with
the program's answer beside it (`<id>.result.json`: done or refused, and why). This reads them back as one
row an event, newest first, for the board's "what it decided today". It draws nothing and serves nothing.

An event still open — the captain is answering it now — has no closing record and is read as `open`. A file
that is not what the program writes is skipped rather than raised: this is a page's reader, and one torn
file must not cost the rest.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .logs import run_dir
from .talk import read_json

EVENTS, ORDERS = "events", "orders"


def held(path: Path) -> dict[str, Any] | None:
    """A file the captain program wrote, through the one reader the run folder is read with: plain files only,
    bounded, and never raising."""
    found = read_json(path)
    return found if isinstance(found, dict) else None


def orders_of(root: Path, fairway: str) -> dict[str, list[dict[str, Any]]]:
    """Every order this stream's captain gave, by the event it answered, each with its result."""
    folder = run_dir(root) / ORDERS / fairway
    found: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        if path.name.endswith(".result.json"):
            continue
        order = held(path)
        if order is None:
            continue
        result = held(path.with_name(f"{path.stem}.result.json")) or {}
        found.setdefault(str(order.get("event", "")), []).append({
            "id": path.stem, "t": str(order.get("t", "")), "verb": str(order.get("verb", "")),
            "slice": str(order.get("slice") or order.get("ask") or ""),
            "said": str(order.get("text") or order.get("note") or order.get("why") or ""),
            "state": str(result.get("state") or "unread"), "why": str(result.get("why") or "")})
    return found


def decided(root: Path, fairway: str, since: str = "") -> list[dict[str, Any]]:
    """One row per event, newest first: what woke the captain, how it was closed, and what it ordered.
    `since` is an instant (`2026-11-16T00:00:00Z`) before which nothing is read; `today` gives today's."""
    folder = run_dir(root) / EVENTS / fairway
    given = orders_of(root, fairway)
    rows = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        if path.name.endswith(".closed.json") or path.name in ("state.json", "captain.json"):
            continue
        event = held(path)
        if event is None or str(event.get("t", "")) < since:
            continue
        closed = held(path.with_name(f"{path.stem}.closed.json"))
        cost = (closed or {}).get("cost") or {}
        rows.append({"id": path.stem, "t": str(event.get("t", "")), "kind": str(event.get("kind", "")),
                     "slice": str(event.get("slice") or ""), "by": str((closed or {}).get("by") or "open"),
                     "why": str((closed or {}).get("why") or ""), "orders": given.get(path.stem, []),
                     "seconds": cost.get("seconds"), "ended": str(cost.get("ended") or ""),
                     "tokens": cost.get("tokens")})
    return sorted(rows, key=lambda row: (row["t"], row["id"]), reverse=True)


def status(root: Path, fairway: str) -> dict[str, Any] | None:
    """Whether this stream's captain is an agent, and why not where it is not — "no captain agent: this harness
    has no proven protocol launch" — as its captain program said when it started (`captain.json` beside its
    events), and `agent: false` with why and when after its agent failed. None where no captain program has
    said: the stream has never asked for an agent. The captain's window and the captains strip say it plainly."""
    return held(run_dir(root) / EVENTS / fairway / "captain.json")


def today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT00:00:00Z")


def tally(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """How a captain's decisions went: how many it made, how many fell to the rule, and what they took."""
    timed = [row["seconds"] for row in rows if isinstance(row.get("seconds"), int | float)]
    return {"events": len(rows), "by_captain": sum(1 for row in rows if row["by"] == "captain"),
            "by_rule": sum(1 for row in rows if row["by"] == "rule"),
            "refused": sum(1 for row in rows for one in row["orders"] if one["state"] == "refused"),
            "seconds": round(sum(timed), 3)}
