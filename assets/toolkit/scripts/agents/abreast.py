#!/usr/bin/env python3
"""How many of a fairway's slices run at once, and which fairway the next free session goes to.

A person who typed `/sail fairway=leaver-offboarding` got every ready slice fanned out once the walking
skeleton merged — rule 6 of *Ready-set selection* says run them concurrently — and the fleet, given the same
fairway, ran its twenty-two slices one after another, because the captain dispatched `/sail <slice>`, the
single-slice form, once a turn. The rules for running slices side by side were already written down in
`commands/sail.md` and the slice graph was already where it says; nothing in the fleet read either. This
module is where the fleet does, and it decides nothing the page does not already say.

**Which slices may run together is clearance's answer, not a second one.** `clearance.position` is the
ready rule — every `depends_on` merged, every mark it steers by set, no question open, no park — and
`clearance.independent` is the page's independence rule narrowed by the split's `parallel_ok_with`. What
is here is the part neither has to know: which of a fairway's slices are live right now, by its own lines,
and how many more it may start.

**`boilers` is one budget, and it counts slice sessions.** It used to count captains, one per fairway, and
a captain ran one slice. With a captain running several, a second budget for "slices per fairway" would be
two levers on one machine's capacity and a run that read either as the other. So `boilers` is every slice
session running in the harbour, whichever fairway it is in, and one process decides how they are shared:
the harbourmaster, which already lights captains and is the one writer of its machine's harbour log. It
writes a `slots` line per fairway; a captain reads it before it starts any slice beyond its first. The rule,
in order:

1. **Breadth first.** Every fairway with work gets one session before any fairway gets a second — a stream
   with nothing running is worth more than a third slice of one that has two.
2. **Then depth, by priority.** Spare sessions go to fairways that can use them: first the person's own
   order (`fairways` in `harbour.json`), then the critical path — a ready slice whose merge unblocks the most
   slices downstream, or sets a mark another fairway steers by — then the most ready slices left.
3. **`abreast` caps depth**, per fairway, default `DEFAULT`, and never above `boilers`.
4. **Back-pressure.** A fairway with a slice waiting on a merge answer starts nothing new. The harbourmaster
   merges one slice at a time with a full gate each; outrunning it only multiplies rebase conflicts.
5. **Nothing is preempted.** A running session keeps its slot until its slice merges, parks or stops; the
   slot it frees is offered again by the same rules, the way `yielded` hands a berth between captains.

`abreast: 1`, or `boilers` equal to the number of fairways with work, is one slice per fairway — exactly
what the fleet did before this file.

Standalone and dependency-free beyond the modules beside it: this runs inside a generated project, which has
no slipwai to import.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clearance  # noqa: E402
import logs  # noqa: E402

#: Slices one fairway runs at once where `harbour.json` names no `abreast`. Three, because that is
#: `half-ahead`'s `boilers` — a fresh harbour with one fairway then uses every session it was given, and
#: one with three fairways gives each one first — and because a slice's own `[P]` tasks already fan out to
#: `fanout` delegates inside it, so three slices abreast is already up to `3 × (1 + fanout)` agents on one
#: machine. More than that is a choice a person makes with `slipwai telegraph --set abreast=<n>`, where they
#: can see the arithmetic, rather than a default they inherit without it.
DEFAULT = 3
#: The ready states `clearance.py` admits a slice to a band from: the only states a slice is started in.
READY = tuple(clearance.BANDS)


def whole(value: object) -> int | None:
    """An int that is not a bool, or None."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def width(held: dict) -> int:
    """How many slices one fairway may run at once: `abreast`, never above `boilers`, never below one.

    Never below one because `boilers: 0` is the telegraph at `stop`, which lights no captain at all — a
    captain that is running was lit, and lit means one slice. That is also what makes `abreast: 1` the
    fleet as it was.
    """
    named = whole(held.get("abreast"))
    cap = named if named is not None and named >= 1 else DEFAULT
    boilers = whole(held.get("boilers"))
    if boilers is not None and boilers > 0:
        cap = min(cap, boilers)
    return max(1, cap)


def live(deck: list[logs.Entry]) -> list[str]:
    """The slices whose session is running now, by this fairway's own lines, in the order they started.

    Claimed — or taken over — with nothing since that ends the run: a `merged`, a `stopped`, a park of its
    own, or a park of the whole fairway. Claimed is not the same as live: a slice a stop interrupted is
    still claimed, and is carried on, but nothing is running it until the captain claims it again.
    """
    running: dict[str, bool] = {}
    for entry in deck:
        named = str(entry.fields.get("slice", ""))
        if entry.kind in ("claimed", "taken-over") and named:
            running[named] = True
        elif entry.kind in ("merged", "stopped") and named:
            running[named] = False
        elif entry.kind == "parked":
            for one in ([named] if named else list(running)):
                running[one] = False
    return [named for named, on in running.items() if on]


def pending(deck: list[logs.Entry], harbour: list[logs.Entry]) -> list[str]:
    """The slices waiting on a merge answer: a `request` for a merge the harbour has not answered."""
    answered = {str(e.fields.get("request", "")) for e in harbour if e.kind in ("granted", "refused")}
    return [str(e.fields.get("slice", "")) for e in deck
            if e.kind == "request" and e.fields.get("what") == "merge"
            and str(e.fields.get("id", "")) not in answered]


def fix_owed(fairway: str, deck: list[logs.Entry], harbour: list[logs.Entry]) -> logs.Entry | None:
    """A `fix-trunk` for this fairway that it has not answered, or None.

    Answered means a `merged` line of this fairway's, no older than the order, naming a commit that is not
    the one that went red. By commit and not by the clock alone: a timestamp is to the second, so the merge
    that answers an order can carry the same instant as the order itself, and the merge that *broke* trunk
    is the one line that carries the broken commit. Here because two readers need it — the captain, which
    takes the fix ahead of anything new, and the plan, for which a fix owed is work even when nothing is
    ready, so the fairway that reddened trunk is lit to mend it.
    """
    orders = [e for e in harbour if e.kind == "fix-trunk" and str(e.fields.get("fairway", "")) == fairway]
    if not orders:
        return None
    last = orders[-1]
    broke = str(last.fields.get("commit", ""))
    answered_by = [e for e in deck if e.kind == "merged" and e.t >= last.t
                   and not str(e.fields.get("commit", "")).startswith(broke[:8])]
    return None if answered_by else last


def ready(charted: dict, folded_logs: clearance.Folded, done: set[str], fairway: str,
          beside: list[str]) -> list[str]:
    """The fairway's slices that may start now beside `beside`, in split order.

    Clearance's ready rule, slice by slice, and then the independence rule against everything already
    running and everything chosen before it: a slice whose `parallel_ok_with` leaves out one already in
    flight waits for it, and is offered again at the next boundary.
    """
    _, parallel = clearance.slice_graph(charted)
    never = clearance.observed(charted)
    chosen: list[str] = []
    for slice_id, body in (charted.get("slices") or {}).items():
        slice_id = str(slice_id)
        if slice_id in never or slice_id in beside or str((body or {}).get("fairway", "")) != fairway:
            continue
        state, _ = clearance.position(charted, folded_logs, slice_id, done)
        if state in READY and all(clearance.independent(parallel, slice_id, other)
                                  for other in [*beside, *chosen]):
            chosen.append(slice_id)
    return chosen


def critical(charted: dict, slice_id: str) -> int:
    """How much one slice's merge unblocks: every slice downstream of it in the slice graph, plus every
    slice in another fairway steering by a mark it sets. The second counts because a fairway that is
    waiting on another is a whole stream idle, not one slice."""
    depends, _ = clearance.slice_graph(charted)
    below: set[str] = set()
    frontier = [slice_id]
    while frontier:
        one = frontier.pop()
        for other, deps in depends.items():
            if one in deps and other not in below:
                below.add(other)
                frontier.append(other)
    slices = charted.get("slices") or {}
    mine = str((slices.get(slice_id) or {}).get("fairway", ""))
    sets = set(clearance.sets_of(charted, slice_id))
    across = {str(other) for other, body in slices.items()
              if str((body or {}).get("fairway", "")) != mine
              and sets & set(clearance.steered_by(charted, str(other)))}
    return len(below | across)


def allocate(order: list[str], preferred: list[str], wants: dict[str, int], running: dict[str, int],
             held: set[str], weight: dict[str, int], boilers: int | None,
             cap: int) -> dict[str, tuple[int, str]]:
    """Each fairway's sessions, and — for one given none while it has work — the fairway the slot went to.

    `wants` is what a fairway could start now beyond what it is `running`; `held` is the fairways under
    back-pressure; `weight` is each one's critical-path score. `boilers` None is unbounded. A running
    session is never taken back, so a fairway's number is at least what it is running even where that is
    past the budget — a person who rang the telegraph down mid-run gets the smaller number at the next
    boundaries, not a killed stage.
    """
    granted = {fairway: running.get(fairway, 0) for fairway in order}
    free = None if boilers is None else max(0, boilers - sum(granted.values()))
    last = ""
    for fairway in order:  # breadth
        if granted[fairway] == 0 and wants.get(fairway, 0) > 0 and (free is None or free > 0):
            granted[fairway], last = 1, fairway
            free = None if free is None else free - 1

    def key(fairway: str) -> tuple[int, int, int, int]:
        rank = preferred.index(fairway) if fairway in preferred else len(preferred)
        left = wants.get(fairway, 0) - (granted[fairway] - running.get(fairway, 0))
        return rank, -weight.get(fairway, 0), -left, order.index(fairway)

    while free is None or free > 0:  # depth, one session at a time to the best fairway that can use it
        able = [fairway for fairway in order if granted[fairway] >= 1 and fairway not in held
                and granted[fairway] < cap
                and wants.get(fairway, 0) > granted[fairway] - running.get(fairway, 0)]
        if not able:
            break
        best = min(able, key=key)
        granted[best] += 1
        free = None if free is None else free - 1
    return {fairway: (count, last if count == 0 and wants.get(fairway, 0) > 0 and last else "")
            for fairway, count in granted.items()}


def deck_of(feature: str, fairway: str) -> list[logs.Entry]:
    """One fairway's lines, or none where they cannot be read — the captain says so; this only counts."""
    path = clearance.ROOT / logs.deck_path(feature, fairway)
    try:
        return logs.fold(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else []
    except (OSError, UnicodeDecodeError, logs.Unreadable):
        return []


def harbour_plan(lit: set[str], config: Path) -> dict[str, tuple[int, int, str]]:
    """Every fairway's (sessions, running now, the fairway a slot went to) for this pass of the harbourmaster.

    `lit` is the fairways whose captain is alive on this machine: a fairway with no captain is running
    nothing, whatever its log last said, and the slices it claimed count as work it wants rather than
    sessions it holds. A fairway parked as a whole wants nothing; one whose slices are parked on their own
    wants what is left.
    """
    try:
        held = json.loads(config.read_text(encoding="utf-8")) if config.is_file() else {}
    except (OSError, ValueError, UnicodeDecodeError):
        held = {}
    held = held if isinstance(held, dict) else {}
    charted, feature = clearance.chart()
    if not charted:
        return {}
    preferred = clearance.preferred_fairways(config)
    order = clearance.fairway_order(charted, preferred)
    found = clearance.lines(feature)
    folded_logs = clearance.with_evidence(charted, clearance.folded(found))
    done = clearance.done_marked(feature)
    harbour = logs.harbour_fold(clearance.ROOT)
    wants: dict[str, int] = {}
    running: dict[str, int] = {}
    weight: dict[str, int] = {}
    backed: set[str] = set()
    for fairway in order:
        deck = deck_of(feature, fairway)
        parks = logs.open_parks(deck, harbour, fairway)
        on = live(deck) if fairway in lit else []
        running[fairway] = len(on)
        if logs.fairway_parks(parks):
            wants[fairway] = 0
            continue
        stopped = [one for one in logs.unmerged(deck) if one not in on and one not in logs.held_slices(parks)]
        offered = ready(charted, folded_logs, done, fairway, on + stopped)
        owed = 1 if fix_owed(fairway, deck, harbour) is not None and not on else 0
        wants[fairway] = len(stopped) + len(offered) + owed
        weight[fairway] = max([critical(charted, one) for one in offered + stopped] or [0])
        if pending(deck, harbour):
            backed.add(fairway)
    boilers = whole(held.get("boilers"))
    planned = allocate(order, preferred, wants, running, backed, weight,
                       boilers if boilers is not None and boilers > 0 else None, width(held))
    return {fairway: (count, running[fairway], to) for fairway, (count, to) in planned.items()}


def granted(harbour: list[logs.Entry], fairway: str) -> logs.Entry | None:
    """The harbourmaster's latest `slots` line for this fairway, or None where it has never written one."""
    return next((e for e in reversed(harbour) if e.kind == "slots" and str(e.fields.get("fairway", "")) == fairway),
                None)
