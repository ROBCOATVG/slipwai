"""What waits on a person, as one list: the strip above the page, its count on the tab, and the column.

Three places said it, each from its own reading. The strip counted the parks the fleet groups and the
questions no park holds; the Fleet tab's badge counted every inbox row that was not paused, notes and
unread decisions among them; the column counted slices the fold had in `waiting`. On one run the three
said 4, 9 and 2 at once, and none of them was wrong by its own lights.

So this is the one reading, in two groups. *Holding work up*: a red trunk the harbour parked for a person
(nothing clears that park but trunk going green, so it links to the band that says so), a slice parked on a
person, a card a running
stage has put up, the one button the run cannot pass without, and a stream's log nobody can read (its
captain stops at every start until a person repairs the line), and a slice's product question where the
project says a person answers them. *When you have time*: a capability with something to look at, a feedback
proposal waiting for Confirm, and a slice a person or its captain paused (no rule lifts either). A note nobody has
read and a slice paused until a set time are not on it: neither holds anything up, and neither needs a
person to move. Each item links to where it is acted on, and the column draws exactly the slices this names.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .feedback import items
from .feedback_card import to_look_at
from .fleet_page import first_sentence, parks_table, plural
from .page_shell import esc
from .stage_session import running
from .storyboard_card import waiting_said
from .talk_waits import captain_window
from .talk_waits import items as talk_items
from .trunk_card import held_item, stranded_item
from .upstream import NAMED, held_by, unjudged
from .waiting_inbox import inbox, mender_card

NOTHING_WAITS: dict[str, Any] = {"count": 0, "text": "", "href": "", "holding": [], "later": [], "slices": []}


def open_asks(board: Any) -> int:
    """The cards a running stage has put up and nobody has answered."""
    session = running(board)
    if session is None:
        return 0
    turns = session.said(0)["turns"]
    asked = {t["ask"]["id"] for t in turns if t.get("kind") in ("permission", "question") and t.get("ask")}
    answered = {t["ask"]["id"] for t in turns if t.get("kind") == "answered" and t.get("ask")}
    return len(asked - answered)


def button_waiting(board: Any, able: dict[str, bool]) -> tuple[str, str]:
    """The one step the page offers that the run cannot pass without: what it says, and where it is."""
    fitting = getattr(board, "fitting", None)
    approving = unjudged(board.root) if fitting is None or fitting.said()["done"] else ""
    if approving:
        # What the fleet cannot start without, so it holds the work up: said the moment the drawing ends.
        return f"The storyboard for {approving} is ready to look at: approve it or send it back", "#mockups"
    for flag, said, where in (("draftable", "The draft ended without a specification: draft it again", "#draft"),
                              ("drawable", "The specification is ready: read it, then draw the storyboard", "#draw"),
                              ("modelable", "The storyboard is approved: model it", "#model"),
                              ("launchable", "The storyboard is approved: continue the build", "#launch"),
                              ("castable", "The chart is split: cast off the fleet", "#cast-off")):
        if able.get(flag):
            return said, where
    return "", ""


def slice_item(row: dict[str, str]) -> dict[str, Any]:
    """A slice parked on a person, said as its name and what it waits for, linked to its card."""
    name = f'{row["slice"]} · {row["title"]}' if row.get("title") else row["slice"]
    asked = [one for one in str(row.get("asked") or "").splitlines() if one.strip()]
    why = (f"{plural(len(asked), 'question')} open" if asked
           else first_sentence(str(row.get("park") or row.get("why") or ""), 90) or "waiting on you")
    return {"n": 1, "text": f"{name}: {why}", "href": f"#card-{row['slice']}", "slice": row["slice"]}


def parked(fleet: dict[str, Any], rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Every park and hand-back a person has to act on, read from the fleet's own logs, each slice it holds
    with the fold's row for it where there is one. The fleet first and the fold second: the fold has no row
    for a slice whose chart it cannot read, and none at all when the clearance script faults — and neither
    is nothing waiting. A paused park lifts by itself and is not on the list."""
    found: list[dict[str, Any]] = []
    by_slice = {row["slice"]: row for row in rows}
    seen: set[str] = set()
    for group in fleet.get("groups") or []:
        if group.get("paused") == "yes" or group.get("probably") or group.get("obsolete") \
                or group.get("acts") == "fleet":
            continue  # nothing only a person can move on: `settling` lists them, once each kind, or the fleet's own
        title = first_sentence(str(group.get("what") or ""), 90) or "waiting on you"
        if group.get("source") == "told":
            needs = [str(need.get("plain") or need.get("what") or "") for need in group.get("needs") or []
                     if need.get("met") != "yes"]
            found.append({"n": 1, "href": "#from-streams",
                          "text": f"A slice needs this on trunk: {first_sentence(needs[0], 90) if needs else title}"})
            continue
        for park in group.get("parks") or []:
            named, fairway = str(park.get("slice") or ""), str(park.get("fairway") or "")
            held = [named] if named else [row["slice"] for row in rows
                                          if row.get("fairway") == fairway and row.get("state") == "waiting"]
            if not held and f"stream:{fairway}" not in seen:
                seen.add(f"stream:{fairway}")
                found.append({"n": 1, "href": "#from-streams", "text": f"The {fairway} stream: {title}"})
            for one in held:
                if one in seen:
                    continue
                seen.add(one)
                found.append(slice_item(by_slice[one]) if one in by_slice else
                             {"n": 1, "href": "#from-streams", "text": f"{one}: {title}"})
    # A slice the fold holds on a person that no park of the fleet's names is still the person's.
    found += [slice_item(row) for row in rows if row.get("state") == "waiting" and row["slice"] not in seen]
    return found


def settling(fleet: dict[str, Any]) -> list[dict[str, Any]]:
    """The hand-backs of merged slices that are probably done, as one thing to confirm, and each park an earlier
    slipwai wrote, as one thing to dismiss: listed when you have time, never as holding work up."""
    groups = fleet.get("groups") or []
    probably = [g for g in groups if g.get("probably")]
    found = [{"n": 1, "href": "#probably", "text": f"{plural(len(probably), 'hand-back')} of merged slices "
                                                    f"probably done: confirm"}] if probably else []
    return found + [{"n": 1, "href": "#obsolete", "text": f"The {', '.join(g.get('fairways') or ['?'])} stream's park "
                     f"is obsolete since {g['obsolete']}: dismiss it"} for g in groups if g.get("obsolete")]


def waiting(board: Any, fleet: dict[str, Any], able: dict[str, bool],
            rows: list[dict[str, str]] | None = None, root: Path | None = None,
            trunk: dict[str, Any] | None = None) -> dict[str, Any]:
    """The list: how many things, the first of them in its own words with the way to it, both groups, and
    the slices the column draws. `able` is the flags that show the strip's buttons, so the words here and
    the button there agree; a stage still running offers no button, and is not a wait. `trunk` is the
    board's (`trunk_story`): a park the harbour wrote with no fairway — the trunk mender's attempts spent, or
    no mender at all — holds every merge, and is first."""
    holding: list[dict[str, Any]] = held_item(trunk or {}) + stranded_item(trunk or {})
    asked = open_asks(board)
    if asked:
        holding.append({"n": asked, "href": "#stage-asks", "text": "The agent asks you something" if asked == 1
                        else f"The agent asks you {asked} things"})
    holding += parked(fleet, rows or [])
    holding += [{"n": 1, "text": f"The {row['fairway']} log cannot be read: its captain cannot start",
                 "href": "#from-streams"} for row in fleet.get("inbox") or [] if row.get("kind") == "unreadable"]
    # What a person said to a stage and was never said to it — after a Stop or a restart — with the two things a
    # person can do about it right here: say it now, or discard it. One queued behind a turn under way is said.
    for one in waiting_said(board):
        named = NAMED.get(one["command"], one["command"])
        holding.append({"n": 1, "href": "#storyboard-talk" if one["command"] == "mockups" else "#fitting",
                        "text": f"Said to the {named} stage and not said to it yet: “{one['text'][:80]}”"
                                + (" — it is said when the turn under way ends" if one["live"] else ""),
                        **({} if one["live"] else {"say": {"command": one["command"], "id": one["id"],
                                                           "text": one["text"]}})})
    # Where the board was set to advance by itself and will not, why — in place of the line it would repeat.
    why, there = held_by(board)
    if why:
        holding.append({"n": 1, "text": why, "href": there})
    said, where = button_waiting(board, able)
    if said and not (why and there == where):
        holding.append({"n": 1, "text": said, "href": where})
    # A product question a slice asked a person, where the project says a person answers them, and a slice a
    # person or its captain paused, since no rule lifts a pause (`talk_waits`).
    asked_you, paused_by_you = talk_items(root or board.root, rows or [])
    holding += asked_you
    # A capability on film that nobody has opened or said anything about, and one owed a person's verdict
    # where the project asks for it: `feedback_card.to_look_at` says which films, so the two cannot disagree.
    films = to_look_at(root or board.root, fleet)
    later = [{"n": 1, "href": f"#film-{one['capability']}",
              "text": f"{one['title']} is ready for your verdict" if one["accept"]
              else f"{one['title']} is on film: say what it showed"} for one in films]
    later += [{"n": 1, "text": f"{name} is ready for your verdict", "href": "#feedback"}
              for name in sorted(fleet.get("demo_due_in") or {}) if name not in {one["capability"] for one in films}]
    proposed = len([one for one in items(root or board.root) if one.state == "proposed"])
    if proposed:
        said = ("A piece of feedback has" if proposed == 1 else f"{proposed} pieces of feedback have")
        later.append({"n": proposed, "href": "#feedback", "text": f"{said} a proposed route to confirm"})
    later += paused_by_you
    later += settling(fleet)
    if not holding and not later:
        return dict(NOTHING_WAITS)
    first = (holding or later)[0]
    return {"count": sum(one["n"] for one in holding + later), "text": first["text"], "href": first["href"],
            "holding": holding, "later": later, "slices": [one["slice"] for one in holding if one.get("slice")]}


def streams_card(fleet: dict[str, Any], controls: bool = True) -> str:
    """What the streams have asked of a person or told them, answered here: each park with what it needs,
    a question no park holds, a hand-back, a note, the decisions nobody has read, a log nobody can read.

    The Fleet tab carried this, and it is not machinery. It sits under the work because that is where the
    slices it is about are. So do the two things a person could do from that tab before it became the
    machinery: try the slices a limit has paused now anyway, and say something to a stream — now a link to
    its captain's window, where it is said and receipted. A paused park is not drawn as a thing to do.
    """
    groups = [g for g in fleet.get("groups") or [] if g.get("paused") != "yes"]
    others = [row for row in fleet.get("inbox") or [] if row["kind"] != "parked"]
    limit = next((g for g in fleet.get("groups") or [] if g.get("cause") == "limit"), None)
    streams = sorted({str(row["fairway"]) for row in fleet.get("berths") or []}) if controls else []
    if not groups and not others and limit is None and not streams:
        return ""
    # One compact row per thing, in the order attention goes (`waiting_inbox`); the card each was is its Details.
    cards = inbox({**fleet, "groups": groups}, controls) if groups or others else ""
    paused = ""
    if controls and limit is not None:
        lifts = f"; it lifts by itself at {limit['clock']}" if limit.get("clock") else ""
        parks = esc(json.dumps(limit.get("parks") or []))
        paused = (f'<div class="ask"><button type="button" class="quiet-button" data-tell-each=\'{parks}\' '
                  f'data-message="resume now">Try the {len(limit.get("slices") or [])} paused slices now anyway'
                  f'</button><span class="empty">Before then the harness will just say no again{esc(lifts)}'
                  f"</span></div>")
    # Said to a stream in its captain's window now, where the receipt and the captain's routing are shown.
    links = " · ".join(f'<a href="{esc(captain_window(one))}" target="_blank" rel="noopener">Captain · {esc(one)}</a>'
                       for one in streams)
    told = (f'<h3>Talk to a stream\'s captain</h3><p class="talk-to">{links}</p>'
            if links else "")
    return (f'<div class="card" id="from-streams"><h2>Waiting on you</h2><p class="empty">What the streams '
            f"have asked of you or left for you, answered from here: what only you can decide first, then what "
            f"the mender tried and could not land, then tidying. Notes and unread decisions hold nothing up, so "
            f"they are not counted as waiting on you.</p>{cards}{paused}{told}</div>"
            f"{mender_card({**fleet, 'groups': groups}, controls)}{parks_table(fleet)}")

