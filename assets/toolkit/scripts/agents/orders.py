#!/usr/bin/env python3
"""The only way a stream's captain agent acts: one order, checked for shape, signed, and handed to the program.

The captain became a program because rules given to an agent as instructions failed under load. It is an
agent again only for choosing, and only through this door: the agent runs

    python3 scripts/agents/orders.py start ORD-02
    python3 scripts/agents/orders.py retry ORD-01 --note "the demo log names the missing seed step"
    python3 scripts/agents/orders.py park ORD-01 --why "the third run failed the same way" --needs "a person reads it"
    python3 scripts/agents/orders.py message ORD-01 --text "the rounding rule is in D12" [--interrupt] [--of <id>]
    python3 scripts/agents/orders.py message captain:BIL --text "ORD-02 has set Paid"
    python3 scripts/agents/orders.py pause|resume|stop ORD-01 --why "..."
    python3 scripts/agents/orders.py say --text "Started ORD-02 ahead of ORD-03: it is nearer its merge"
    python3 scripts/agents/orders.py ask --text "Ship the export without the CSV?" --options yes,no
    python3 scripts/agents/orders.py allow|refuse ask-3 --why "..."
    python3 scripts/agents/orders.py none --why "nothing to add"

and this writes `orders/<fairway>/<id>.json` under the run folder, bound to the event it answers (`--event`,
or the one event still open). The captain program reads it, checks it against the rules **again** — this
script's checks are a courtesy to the agent, never the program's — does it or refuses it, and writes
`<id>.result.json` beside it, which this prints once it is there.

**Signed with a key only the captain's session is handed.** Every session in the fleet has a shell, and a
slice's session could otherwise write an order to start, retry or resume itself. The program makes a key
when it starts, keeps it in memory, and gives it to the captain's agent in its environment alone; an order
carries an HMAC over everything it says. A slice's session is never given the key. As with the
conversation key, that does not stop a process of the same user that reads another's environment, which
only running sessions as another user would.

Standalone and dependency-free: this runs inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import talk  # noqa: E402 — carried beside this; its `read_json` is the one reader for the run folder

V = 1
#: Every verb, and what each must carry beyond itself. Anything else is not an order.
VERBS: dict[str, tuple[str, ...]] = {
    "start": ("slice",), "message": ("slice",), "retry": ("slice", "note"), "park": ("slice", "why"),
    "pause": ("slice", "why"), "resume": ("slice", "why"), "stop": ("slice", "why"), "say": ("text",),
    "ask": ("text",), "allow": ("ask", "why"), "refuse": ("ask", "why"), "none": ("why",),
}
#: The fields an order may carry, each a string unless said: the signature covers all of them.
FIELDS = ("v", "id", "t", "event", "fairway", "verb", "slice", "ask", "text", "note", "why", "needs", "of",
          "options", "interrupt")
NAME = re.compile(r"(captain:)?[A-Za-z0-9_.-]{1,64}")
#: The longest thing an order may say: a sentence a person reads, not a transcript.
LONGEST = 2000
KEY = "SLIPWAI_CAPTAIN_KEY"
FAIRWAY = "SLIPWAI_CAPTAIN_FAIRWAY"
ORDERS = "SLIPWAI_CAPTAIN_ORDERS"
EVENTS = "SLIPWAI_CAPTAIN_EVENTS"


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


def run_dir() -> Path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import logs  # noqa: PLC0415 — carried beside this; it owns where the run's state lives
    return logs.run_dir(project_root(Path(__file__).resolve()))


def shape(order: Any) -> str:
    """Why this is not an order, or `''`. The program asks this of every file as well as the script."""
    if not isinstance(order, dict):
        return "it is not a JSON object"
    verb = order.get("verb")
    if verb not in VERBS:
        return f"{verb!r} is not an order a captain gives: {', '.join(VERBS)}"
    unknown = sorted(set(order) - set(FIELDS) - {"sig"})
    if unknown:
        return f"it carries {', '.join(unknown)}, which no order has"
    for name in VERBS[verb]:
        if not str(order.get(name) or "").strip():
            return f"`{verb}` needs {'--' + name if name not in ('slice', 'ask') else 'a ' + name}"
    if verb == "message" and not str(order.get("text") or "").strip() and not order.get("of"):
        return "`message` needs --text, or --of the message it routes"
    for name in FIELDS:
        value = order.get(name)
        if name == "interrupt":
            if value is not None and not isinstance(value, bool):
                return "`interrupt` is true or false"
        elif name == "options":
            if value is not None and not (isinstance(value, list) and all(isinstance(one, str) for one in value)):
                return "`options` is a list of words"
        elif name == "v":
            if value != V:
                return f"it is not version {V} of an order"
        elif value is not None and not isinstance(value, str):
            return f"`{name}` is not text"
        elif isinstance(value, str) and len(value) > LONGEST:
            return f"`{name}` is longer than {LONGEST} characters: say it in a sentence"
    for name in ("slice", "ask", "of", "event", "id"):
        value = order.get(name)
        if value and not NAME.fullmatch(str(value)):
            return f"{value!r} is not a name"
    return ""


def body(order: dict[str, Any]) -> bytes:
    return json.dumps({name: order.get(name) for name in FIELDS}, sort_keys=True, ensure_ascii=False).encode("utf-8")


def sign(secret: bytes, order: dict[str, Any]) -> str:
    return hmac.new(secret, body(order), hashlib.sha256).hexdigest()


def signed(secret: bytes, order: dict[str, Any]) -> bool:
    """Whether the order carries the signature this key makes. No key is no order, and nor is a file whose
    signature or fields no signature could have been made over: it is refused, never raised on."""
    try:
        return bool(secret) and hmac.compare_digest(str(order.get("sig", "")), sign(secret, order))
    except (TypeError, ValueError, UnicodeError):
        return False


def open_events(folder: Path) -> list[dict[str, Any]]:
    """The events waiting on the captain in this folder, oldest first: an event file with no closing record."""
    found = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        if path.name.endswith((".closed.json", ".result.json")) or path.name == "state.json":
            continue
        if path.with_name(f"{path.stem}.closed.json").exists():
            continue
        held = talk.read_json(path)
        if isinstance(held, dict) and held.get("id") == path.stem:
            found.append(held)
    return sorted(found, key=lambda one: (str(one.get("t", "")), str(one["id"])))


def write(folder: Path, order: dict[str, Any]) -> Path:
    """Whole, and renamed into place, so the program never reads half an order."""
    folder.mkdir(parents=True, exist_ok=True)
    aside = folder / f".{order['id']}.json.part"
    aside.write_text(json.dumps(order, ensure_ascii=False) + "\n", encoding="utf-8")
    path = folder / f"{order['id']}.json"
    os.replace(aside, path)
    return path


def give(verb: str, target: str = "", event: str = "", **said: Any) -> tuple[int, str]:
    """Write one order and wait a while for its result. (exit status, what to print)."""
    try:
        secret = bytes.fromhex(os.environ.get(KEY, "") or "")
    except ValueError:
        secret = b""
    fairway = os.environ.get(FAIRWAY, "")
    run = run_dir()
    evaluating = bool(os.environ.get("SLIPWAI_EVAL"))
    if evaluating and not fairway:
        # An eval's throwaway project holds one event; its stream is the folder it is in. An order written
        # here unsigned is read by the eval and nothing else: the program believes no unsigned order.
        held_in = [path.parent.name for path in sorted((run / "events").glob("*/*.json"))
                   if open_events(path.parent)] if (run / "events").is_dir() else []
        fairway = held_in[0] if held_in else ""
    if (not secret and not evaluating) or not fairway:
        return 2, ("orders: only the captain's session gives orders, and this one was not handed the captain's "
                   "key. A slice's session acts in its berth; it does not order the stream")
    events = Path(os.environ.get(EVENTS) or run / "events" / fairway)
    orders = Path(os.environ.get(ORDERS) or run / "orders" / fairway)
    waiting = open_events(events)
    held = next((one for one in waiting if one["id"] == event), None) if event else (waiting[-1] if waiting else None)
    if held is None:
        return 2, (f"orders: no event {event} is open for {fairway}" if event
                   else f"orders: no event is open for {fairway}, so there is nothing to answer")
    t = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    order: dict[str, Any] = {"v": V, "id": f"{t.replace('-', '').replace(':', '')}-{secrets.token_hex(3)}", "t": t,
                             "event": held["id"], "fairway": fairway, "verb": verb}
    if target:
        order["ask" if verb in ("allow", "refuse") else "slice"] = target
    order.update({name: value for name, value in said.items() if value not in (None, "", [], False)})
    why = shape(order)
    if not why and verb not in (held.get("may") or []):
        why = f"`{verb}` is not an order this {held.get('kind')} event takes: {', '.join(held.get('may') or [])}"
    if why:
        return 2, f"orders: not written — {why}"
    order["sig"] = sign(secret, order) if secret else ""
    path = write(orders, order)
    result = path.with_name(f"{order['id']}.result.json")
    until = time.monotonic() + float(os.environ.get("SLIPWAI_CAPTAIN_WAIT") or 30)
    while time.monotonic() < until:
        answer = talk.read_json(result)
        if not isinstance(answer, dict):
            time.sleep(0.1)
            continue
        state, why = str(answer.get("state")), str(answer.get("why") or "")
        return (0 if state == "done" else 1), f"{verb}: {state}" + (f" — {why}" if why else "")
    return 0, f"{verb}: written as {order['id']}; the captain answers it in {result}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="orders", description=__doc__.splitlines()[0])
    parser.add_argument("verb", choices=list(VERBS))
    parser.add_argument("target", nargs="?", default="", help="the slice (or captain:<fairway>), or the ask's id")
    parser.add_argument("--event", default="", help="the event this answers; the open one where there is one")
    for name in ("text", "note", "why", "needs", "of"):
        parser.add_argument(f"--{name}", default="")
    parser.add_argument("--options", default="", help="for `ask`: the answers offered, comma-separated")
    parser.add_argument("--interrupt", action="store_true", help="for `message`: cancel the turn under way")
    parsed = parser.parse_args(argv)
    options = [one.strip() for one in parsed.options.split(",") if one.strip()]
    code, said = give(parsed.verb, parsed.target, parsed.event, text=parsed.text, note=parsed.note, why=parsed.why,
                      needs=parsed.needs, of=parsed.of, options=options, interrupt=parsed.interrupt)
    print(said, file=sys.stderr if code == 2 else sys.stdout)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
