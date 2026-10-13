# Written by scripts/shared-modules.py from src/slipwai/logs.py. Do not edit: edit the keel's module,
# run `make shared`, and commit both. A generated project has no slipwai to import, and both runtimes need
# this one — so there is one source and this copy, and `make check-shared` refuses a copy that has drifted.
"""The deck log and the harbour log: one line per event, and the only thing that says what happened.

The first attempt had a runner that was the single source of status, and it died at iteration two. Seventeen
of nineteen iterations ran from interactive sessions afterwards and wrote nothing at all — no run log, no
stream, no line — so the checkpoint still said "iteration 2" while twenty slices merged. Nobody could answer
what the state was without reading git. In MANDA the same shape failed the other way: `model.yaml` said
`planned` for eight slices that were built and merged, because the field was written at plan time and never
reconciled.

Both are the same mistake, which is state kept somewhere other than where the work happened. A log line is
written by the thing that did the work at the moment it did it, and the rule that falls out of that is the
one the whole of version 2 rests on: **a slice that wrote no line made no progress**. Status is folded from
lines, never stored.

**Two logs, and the split between them is about writers, not about contents.** A fairway's captain writes
its own **deck log** and nothing else, so no two processes ever append to one file. The **harbour log** has
exactly one writer, the harbourmaster, which copies across the handful of lines other fairways need — a
mark set, a park, a flag change, a telegraph. That is why the one shared log never conflicts.

**Every line carries `v`.** A reader that meets a version it does not know refuses the line and names the
upgrade rather than guessing which fields moved. Silently skipping a line it could not parse would make a
log that is missing events look exactly like a log of a run that did not have them, and that is the failure
this file exists to prevent.
"""
from __future__ import annotations

import json
import os
import platform
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

#: The format every line declares. A reader refuses anything higher and names what reads it.
V = 1
#: Where a fairway's own log lives, and the one log every fairway reads. Both are ignored by git: heartbeat
#: and token lines arrive every few seconds and have no place in trunk's history. The harbourmaster syncs
#: them through `refs/slipwai/logs`, so a captain on another machine reads the same lines with no commit.
LOGS = ".slipwai/logs"
#: Where this machine's harbourmaster writes. **One harbour log per machine, folded on read**, exactly like
#: the deck logs: "one writer per harbour" is unambiguous on one machine and meaningless on three, one
#: elected writer needs an election, and three writers on one file breaks the rule the whole design rests
#: on. A directory per machine costs nothing at read time and removes the single writer rather than
#: electing one.
HARBOUR_DIR = f"{LOGS}/harbour"
#: The one harbour log a project written before there were three writers already has. Still read and folded
#: in with the rest, and nothing moves it: a migration that relocates somebody's log is one that can lose a
#: line, and these lines are the only record there is of what happened.
HARBOUR = f"{LOGS}/harbour.jsonl"

#: How long a machine's identity may be. Short because it is spent inside other names — a database called
#: `bookings_<machine>_booking` reaching PostgreSQL's 63-byte limit is a berth that cannot connect and a
#: refusal nobody traces back to a hostname.
MACHINE_WIDTH = 16
#: What a machine's identity may be made of, which is the intersection of three alphabets: a git ref
#: component, a path component on every platform, and an unquoted SQL identifier.
UNUSABLE = re.compile(r"[^a-z0-9]+")

#: What every line carries, whichever log it is in.
COMMON = ("v", "t", "kind")

#: Each deck-log kind against the fields it must carry beyond the common ones. A fairway's captain writes
#: these, in its own file, and nothing else writes there.
DECK_KINDS: dict[str, tuple[str, ...]] = {
    "claimed": ("fairway", "slice"),
    # Written at the setting slice's first stage, in its own worktree. This is what clears a sibling, which
    # is why it is not `merged`: waiting for a merge would serialise every fairway behind every other.
    "mark-set": ("fairway", "slice", "mark"),
    "demo": ("fairway", "slice", "verdict"),  # `verdict` is one of VERDICTS, below
    # Against a capability rather than a slice: a person's demo is of a whole chunk of work (theme B, 10).
    "accepted": ("fairway", "capability"),
    "demo-due": ("fairway", "capability"),
    "merged": ("fairway", "slice", "commit"),
    "decision": ("fairway", "id", "what"),
    # A product question the slice cannot be guessed past, written by the stage that met it. `id` is what
    # the answering `decision` line names back, which is how a reader tells an open question from an
    # answered one without a status field: open until a `decision` carries the same `id`. Per slice, so
    # clearance can say which slice is waiting on a person and which siblings that wait reaches — the
    # slices steering by a mark this one has not set yet. A question used to live only in the slice's
    # `plan.md`, which no scheduler reads, so a session holding one for a person stopped the fan-out with it.
    "question": ("fairway", "slice", "id", "what"),
    "told": ("fairway", "message"),
    # Carries the `t` of the `told` it answers, which is what makes it a receipt rather than an assertion.
    "read": ("fairway", "told"),
    "heartbeat": ("fairway",),
    # A captain holds no credential, so anything outside its berth is asked for. `what` is one of a closed
    # set (`push`, `merge`, `deploy`, `flag`, `publish`); `id` is what the answer names back.
    "request": ("fairway", "id", "what", "detail"),
    "berth-request": ("fairway",),
    "stowed": ("fairway", "slice", "from", "what"),
    # A stream that changed hands: the machine holding it went past its lease, and this captain took the
    # claim, the log and the in-flight branch over mid-slice. `from` is the machine it was taken from. Not
    # a `told`, which is a message to a person and owes a `read` receipt — nobody is being asked anything
    # here — and not a `claimed`, which says a slice was started rather than continued. A takeover is the
    # one thing in a fairway's history that a later reader cannot work out from any other line: two
    # machines' work in one chain, with nothing saying where the join is.
    "taken-over": ("fairway", "slice", "from"),
    "parked": ("fairway", "why"),
}

#: What a demo can have said, and the only three. The same three `check-decisions.py` already holds the demo
#: log's markdown to and `benchmark.py` records as an outcome, so this names the vocabulary rather than
#: inventing one: `accepted`, or sent back because the *behaviour* is wrong or because the *implementation*
#: is. The captain reads it — a sent-back demo is a retry and an accepted one closes the slice's gate — and
#: a free-form verdict would make that a guess about somebody's wording.
VERDICTS = ("accepted", "behaviour", "implementation")
#: Field → the only values it may hold, per kind. Checked on the way in *and* on the way out, like every
#: other rule here: a line nobody can interpret reads exactly like a line that was never written.
CLOSED: dict[str, dict[str, tuple[str, ...]]] = {"demo": {"verdict": VERDICTS}}

#: Each harbour-log kind. Only the harbourmaster writes these, which is how one shared file never conflicts.
HARBOUR_KINDS: dict[str, tuple[str, ...]] = {
    "mark-set": ("fairway", "slice", "mark"),
    "flag-hoisted": ("flag", "where"),
    "flag-struck": ("flag",),
    "berth-allocated": ("fairway", "berth"),
    "fires-banked": ("step", "why"),
    "park": ("fairway", "why"),
    "telegraph": ("position",),
    # The harbourmaster's answer to a `request`. Both outcomes are written: a request that was refused and
    # left no line is one the captain waits on for ever and nobody can explain afterwards.
    "granted": ("fairway", "request", "what"),
    # A receipt for the original park, never for a later heartbeat or another fairway.
    "cleared": ("fairway", "parked", "what"),
    "refused": ("fairway", "request", "why"),
    # Trunk's own CI, which is harbour-wide rather than one fairway's: the gate before a merge is `make
    # verify` and CI runs `make ci`, so trunk can go red from a check `verify` never ran. Written once per
    # change of state — a board that said `trunk-red` every fifteen seconds is one nobody reads.
    "trunk-red": ("commit", "job", "why"),
    "trunk-green": ("commit",),
    # Sent to the captain whose `merged` line names the commit that went red. The harbourmaster wrote that
    # line, which is how it knows where to send it; a red nothing accounts for is a `park` for a person.
    "fix-trunk": ("fairway", "slice", "commit", "job"),
}


class Unreadable(Exception):
    """A line this reader cannot be trusted with. Never swallowed: a log missing the events it could not
    parse reads exactly like a log of a run that did not have them."""


def now() -> str:
    """The timestamp a line carries: UTC, to the second, which is what sorts two logs into one order."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def machine() -> str:
    """Which machine this is: one identity, derived from the hostname, used everywhere two of them meet.

    It names the claim ref a captain takes (`refs/slipwai/claims/<fairway>` carries it as the commit's
    author), the harbour log this machine writes, and the database a berth allocates. Three answers to
    *which machine* would be three ways for two of them to disagree about whether a collision is one, which
    is why there is this one and it is in the module both runtimes already share.

    **Derived and not chosen**, which is the berth rule: nobody picks a number, so nobody picks the same
    one twice. The hostname's first label, lowercased, with everything outside the three alphabets it has
    to survive — a git ref component, a path component, an unquoted SQL identifier — folded to `_`.

    `SLIPWAI_MACHINE` is the one place a name is typed, and it is typed once. Two containers off one image
    share a hostname, and a shared database is where that is found out rather than said.
    """
    given = os.environ.get("SLIPWAI_MACHINE") or platform.node() or ""
    slug = UNUSABLE.sub("_", given.split(".")[0].strip().lower()).strip("_")
    if not slug[:1].isalpha():
        # A name that begins with a digit is not an SQL identifier and a name with nothing usable in it is
        # not a path component. Neither is a fault worth refusing a run over, so both become a machine
        # whose name says it was not readable rather than an empty string nothing can be built out of.
        slug = f"m_{slug}" if slug else "machine"
    return slug[:MACHINE_WIDTH].rstrip("_")


@dataclass(frozen=True)
class Entry:
    """One event, in whichever log its kind belongs to."""

    kind: str
    fields: dict = field(default_factory=dict)
    t: str = ""
    v: int = V

    def line(self) -> str:
        """The line as it is appended: one JSON object, one `\\n`, no indentation.

        Written with `O_APPEND` and one `write()` per line by whoever calls this, so two processes
        interleave whole lines rather than tearing one.
        """
        body = {"v": self.v, "t": self.t or now(), "kind": self.kind, **self.fields}
        return json.dumps(body, ensure_ascii=False, sort_keys=False) + "\n"


def declared(kind: str, harbour: bool = False) -> tuple[str, ...]:
    """The fields a kind must carry, or a refusal naming the log it was looked for in."""
    kinds = HARBOUR_KINDS if harbour else DECK_KINDS
    if kind not in kinds:
        where = "the harbour log" if harbour else "a deck log"
        raise Unreadable(f"{kind!r} is not a kind {where} has. Its kinds are: {', '.join(sorted(kinds))}")
    return kinds[kind]


def closed(kind: str, body: dict) -> None:
    """Refuse a field whose value is outside the set its kind allows, naming the set."""
    for name, allowed in CLOSED.get(kind, {}).items():
        value = body.get(name)
        if value is not None and value not in allowed:
            raise Unreadable(f"a {kind!r} line's {name} is one of {', '.join(allowed)}; this one says "
                             f"{value!r}, which no reader can act on")


def entry(kind: str, harbour: bool = False, **fields: object) -> Entry:
    """One entry, with every field its kind declares, or a refusal naming what is missing.

    Checked on the way in rather than on the way out: a line that is written short is a line some reader
    weeks later cannot use, and by then nobody knows what the missing value was.
    """
    required = declared(kind, harbour)
    missing = [name for name in required if name not in fields]
    if missing:
        raise Unreadable(f"a {kind!r} line carries {', '.join(required)}; this one has no "
                         f"{', '.join(missing)}")
    closed(kind, fields)
    return Entry(kind=kind, fields=dict(fields))


def read(line: str, harbour: bool = False) -> Entry:
    """One line back, or a refusal that says which rule it broke and what to do about it."""
    text = line.strip()
    if not text:
        raise Unreadable("an empty line")
    try:
        body = json.loads(text)
    except ValueError as fault:
        raise Unreadable(f"not JSON: {fault}") from fault
    if not isinstance(body, dict):
        raise Unreadable("a line is one JSON object")
    version = body.get("v")
    if version != V:
        raise Unreadable(
            f"this line says v{version} and this reader knows v{V}. A newer slipwai wrote it: "
            f"upgrade with `slipwai upgrade` rather than reading it with this one, which would have to "
            f"guess which fields moved"
        )
    kind = str(body.get("kind", ""))
    required = declared(kind, harbour)
    missing = [name for name in required if name not in body]
    if missing:
        raise Unreadable(f"a {kind!r} line carries {', '.join(required)}; this one has no "
                         f"{', '.join(missing)}")
    closed(kind, body)
    known = {*COMMON, *required}
    return Entry(kind=kind, t=str(body.get("t", "")),
                 fields={name: value for name, value in body.items() if name not in known} |
                        {name: body[name] for name in required})


def deck_path(feature: str, fairway: str) -> str:
    """A fairway's own log. One writer, its captain, so two fairways never meet on one line."""
    return f"{LOGS}/{feature}/{fairway}.jsonl"


def harbour_path(machine: str) -> str:
    """One machine's harbour log. One writer, its harbourmaster, for the same reason a deck log has one."""
    return f"{HARBOUR_DIR}/{machine}.jsonl"


def harbour_logs(root: Path) -> list[Path]:
    """Every harbour log there is: one per machine, plus the single file older projects still have."""
    directory = root / HARBOUR_DIR
    found = sorted(directory.glob("*.jsonl")) if directory.is_dir() else []
    older = root / HARBOUR
    return ([older] if older.is_file() else []) + found


def deck_logs(root: Path) -> list[Path]:
    """Every fairway's log, in name order, and no harbour log.

    The exclusion is by directory and not by one resolved path: every reader of the deck logs globs the
    whole tree, and when there was one harbour log they each compared against it by name. Three of them in
    a directory of their own is a rule a reader can hold instead of a list it has to keep.
    """
    place = root / LOGS
    harbour = (root / HARBOUR_DIR).resolve()
    older = (root / HARBOUR).resolve()
    return [path for path in sorted(place.rglob("*.jsonl")) if place.is_dir()
            if path.parent.resolve() != harbour and path.resolve() != older]


def harbour_fold(root: Path) -> list[Entry]:
    """Every machine's harbour log as one history, ordered by the instant each line records.

    Interleaved by time rather than concatenated by machine, which is what makes three files read as one
    harbour rather than three lists stapled together — `render-fairways.py` folds the decisions by the same
    rule and for the same reason. Ties keep the machines' own file order, so the result is stable.
    """
    found: list[Entry] = []
    for path in harbour_logs(root):
        found.extend(fold(path.read_text(encoding="utf-8").splitlines(), harbour=True))
    return sorted(found, key=lambda entry: entry.t)


def fold(lines: list[str], harbour: bool = False) -> list[Entry]:
    """Every readable entry, in the order written. A line that cannot be read stops the fold.

    Deliberately not "skip what you cannot parse". A board folded from a log with holes in it is a board
    that is confidently wrong, and the first attempt's whole problem was a status nobody could check.
    """
    return [read(line, harbour) for line in lines if line.strip()]


def open_parks(deck: list[Entry], harbour: list[Entry], fairway: str) -> list[Entry]:
    """The parks that still owe an answer: receipt identity is fairway plus original timestamp."""
    receipts = {(str(e.fields["fairway"]), str(e.fields["parked"]))
                for e in harbour if e.kind == "cleared"}
    return [e for e in deck if e.kind == "parked" and str(e.fields["fairway"]) == fairway
            and (fairway, e.t) not in receipts]
