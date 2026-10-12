"""The commands a person types beside a fleet that is running — `/cruise-watch`, `/cruise-status`,
`/cruise-stop`, `/cruise-tell` — and the watch seat itself, whose words `commands/cruise.md` also renders.

Each is a shell command and the rule for what to do with what it printed. The rule matters more than the
command: a harness folds a command's output to a few lines, so a status or a feed reaches a person only through
the reply, and each of these says so in the same words the watch seat uses.

**All four used to speak to the runner**, which held the state of the run in its own files — a pid, a feed, an
inbox, a cursor — and could therefore only ever report one machine's work. They speak to the logs now. The
difference shows in what each command can be asked while nothing is running: `tell` writes a line a captain
reads whenever one is next lit, `watch` sits on files rather than on a process, and `status` says which
processes are up without pretending that is the same question as what the work is doing.

The words moved to `assets/cruise/` in slice 16.3's rule and 16.6's turn at it. The four pages are a file
each; `parts.md` is what more than one page is assembled from — the watch seat, which `cruise-watch.md` and
`commands/cruise.md` both carry, the sentence every seat command shares about the harness folding output,
and the section `/where-are-we` and `/whats-next` end with, which are not this tree's pages at all. One text
per part, so two pages cannot say two different things, which is the guarantee these functions were written
for and the one an asset per page would have given up.

**Kept apart from `cruise.py` for what it does rather than for its length.** `/cruise` is the ladder with
nobody at the wheel; these are what a person types *beside* a fleet that is already going, and one of them is
not a command of this tree at all — `under_cruise_section` is the last section of `/where-are-we` and
`/whats-next`, which `whats_next.py` and `where_are_we.py` read and which have nothing to do with casting
off. Putting these back in `cruise.py` would have those two modules import the page writer for `/cruise` in
order to ask how a board reads while a fleet is running.
"""
from __future__ import annotations

from ..assets import CRUISE_ROOT
from ..layout import AT_ROOT, Layout
from .cruise_agents import DECISIONS
from .cruise_record import CONFIG, SCRIPT
from .cruise_told import seat_queues, seat_stands
from .prose import page
from .prose import part as one_part

#: The script that starts, stops, watches and tells — everything about the fleet that is not a setting.
FLEET = "scripts/agents/fleet.py"
#: What a person reads to see one stream's own lines, rather than every stream's as they arrive.
INBOX_SCRIPT = "scripts/agents/inbox.py"
#: The parts more than one page is made of, one section each and nothing between them.
PARTS = "parts.md"


def part(name: str, named: dict[str, str] | None = None) -> str:
    """One section of `parts.md`: a passage more than one page here is assembled from."""
    return one_part(CRUISE_ROOT, PARTS, name, named)


def values(layout: Layout = AT_ROOT) -> dict[str, str]:
    """Every value a page under `assets/cruise/` may name from this module, and the whole of what it may.

    The parts are values like any other: a page names `{{watch-seat}}` and this is where the seat's own
    words are rendered, once, for whichever page asked.
    """
    named = {"fleet": FLEET, "inbox": INBOX_SCRIPT, "config": CONFIG, "script": SCRIPT,
             "decisions": DECISIONS, "make": layout.make,
             "queues": seat_queues(FLEET), "stands": seat_stands()}
    return {**named, "verbatim": part("verbatim"), "watch-seat": part("watch-seat", named)}


def cruise_status_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-status`: what is running, and — separately — what the work is doing."""
    return page(CRUISE_ROOT, "cruise-status.md", values(layout))


def cruise_stop_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-stop`: ask every captain to stop at its next boundary."""
    return page(CRUISE_ROOT, "cruise-stop.md", values(layout))


def cruise_tell_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-tell`: write one `told` line into a stream's deck log."""
    return page(CRUISE_ROOT, "cruise-tell.md", values(layout))


def under_cruise_section() -> str:
    """The section `/where-are-we` and `/whats-next` end with: how the answer changes while a fleet is going,
    and — where none is — how it does not change at all."""
    return part("under-a-fleet", {"verbatim": part("verbatim")})


def watch_seat_body(layout: Layout = AT_ROOT) -> str:
    """The watch seat's rules: what the seat prints, when it watches again, when it ends the turn, and how a
    person typing there is answered. One text, so `commands/cruise.md` — which leads into it after casting
    off — and `/cruise-watch` — the seat on its own — cannot say two different things."""
    return values(layout)["watch-seat"]


def cruise_watch_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-watch`: the watch seat on its own, without starting anything."""
    return page(CRUISE_ROOT, "cruise-watch.md", values(layout))
