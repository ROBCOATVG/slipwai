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
# budget: 745 — a need's, a question's and a park's plain line (#172), and the one rule for whether a
# question is still open, which the board, the captain and clearance all ask; a person's mend-again and its receipt;
# where a run's state lives (`run_dir`, which both runtimes ask), the trunk mender's kinds,
# the park record (cause, until, needs, then) and the shape each field is held to, beside the whole
# vocabulary of both logs, each kind beside the reason it exists, and the few folds
# every reader needs, among them which slices a fairway holds in flight now that it holds several at once,
# and a park written when a need was a sentence, read as the record it now is. And a need
# the fleet was to tick with no check, read as a person's
# and a stream's lines read from every file that holds them, the chart feature's first, and the one
# rule for whether a person's answer can clear a park, which the harbourmaster and the board both ask;
# and which needs are a product or model decision, never the mender's (#154)
from __future__ import annotations

import json
import os
import platform
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

#: The format every line declares. A reader refuses anything higher and names what reads it.
V = 1
#: Where everything a run writes about itself lives, and nothing a checkout needs: the logs, what is running
#: and its pids, the berths' records, the sessions' files, the scratch worktrees. One folder, ignored by one
#: line, because the list of names it replaced fell behind what a run writes three times (phase 25.1), and
#: each time `check-slice-scope` failed every berth on files no slice wrote.
RUN = ".slipwai/run"
#: What stays at `.slipwai/` because it is committed: the record, which a checkout with only what git
#: carries needs. Anything else a run writes goes under RUN, and a keel test refuses a path that does neither.
COMMITTED = ("dispatch/", "extensions.json", "hooks.json", "guards.json", "quickstart.json", "packages/",
             "migration.json", "shape-transitions/")


def run_dir(root: Path) -> Path:
    """Where this project keeps its run state: RUN once its `.gitignore` names it, `.slipwai` before then.

    The ignore line is the switch because `slipwai migrate` writes it in the pass that moves the state, and a
    project whose toolkit is still 2.0 has never had it: the board, a release ahead, reads and writes the
    old places there rather than leaving its state in a folder nothing in that project reads.
    """
    try:
        ignored = {line.strip() for line in (root / ".gitignore").read_text(encoding="utf-8").splitlines()}
    except (OSError, UnicodeDecodeError):
        ignored = set()
    return root / RUN if f"{RUN}/" in ignored else root / ".slipwai"


def logs_dir(root: Path) -> Path:
    """The deck logs and the harbour logs. Ignored by git, since heartbeat and token lines arrive every few
    seconds; the harbourmaster syncs them through `refs/slipwai/logs`, so another machine reads the same
    lines with no commit."""
    return run_dir(root) / "logs"


def harbour_dir(root: Path) -> Path:
    """**One harbour log per machine, folded on read**, like the deck logs: "one writer per harbour" means
    nothing on three machines, and a directory per machine removes the single writer instead of electing one."""
    return logs_dir(root) / "harbour"


def older_harbour(root: Path) -> Path:
    """The one harbour log a project written before there were three writers has. Still folded in with the
    rest and never rewritten: these lines are the only record there is of what happened."""
    return logs_dir(root) / "harbour.jsonl"


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
    # A stream that gave its berth up — slice 18.2. The harbour's fairway priority moved this one below
    # the lit line, so its captain finished what it had and stopped rather than holding a berth the run
    # wants elsewhere. `to` is the fairway that displaced it, which is the whole of why a later reader
    # needs this line: a captain that simply exited is indistinguishable from one that died, and a run
    # whose streams swap under it with nothing written down is the state this method exists to not have.
    # Not a `parked`: nothing is wrong and nobody is being asked anything, and a park waits for an answer.
    "yielded": ("fairway", "to"),
    # A captain asked to stop — `fleet.py stop`, a reboot, a person's Ctrl-C — while it was on a slice. It
    # ended the stage that was running and wrote this before giving its claim back, so the slice is one the
    # next captain lit for this fairway carries on rather than one it steps past. Not a `parked`: nobody is
    # being asked anything, and a stop is undone by lighting the fleet again, not by an answer. Before this
    # line a stopped captain wrote nothing at all, and its log read as working until the board said stalled.
    "stopped": ("fairway", "slice"),
    # A park with a `slice` holds that slice and not its siblings: with several of a fairway's slices in
    # flight at once, one that meets a question it may not guess past must not stop the ones that did not.
    # A park with no `slice` is the fairway's, as every park was before, and holds everything in it.
    "parked": ("fairway", "why"),
    # A person's tick of one need of a park, from the board: `parked` is the park's instant, `need` its
    # index. Not a `told` — a `told` after a park clears the whole park, and a tick is one item of it.
    "need-done": ("fairway", "parked", "need"),
    # A person's word, from the board, that the trunk mender may try a hand-back's needs again: `parked` is the
    # park's (or `told`'s) instant. The mender stops after its attempts; nothing else ever started it again.
    "mend-again": ("fairway", "parked"),
    # A slice's `try-it.json` ran green against the app its berth runs, at the Demo rung: `records` is how
    # many steps answered, `commit` the berth's head the story was run from. Written by `try_it.py seed
    # --slice` the way a stage writes `mark-set`, and held to by the captain the same way: a slice with a
    # story whose turn wrote no `seeded` line made no progress at that rung and parks. recap merged
    # fifteen slices whose stories every one failed at their first call, each saying *this step records
    # 401*, because *one the service refuses is fixed here* was a sentence and not a line.
    "seeded": ("fairway", "slice", "records", "commit"),
    # The captain ran a session of the ladder for this slice: one line a run, written when it ends, `free` where
    # it cost no attempt (a person's interrupt or message, a harness that would not run it, a stop of the fleet).
    # What bounds the runs a slice has between a person's words, whoever asked for them: the captain counts
    # these before every run and parks the slice for a person past the ceiling.
    "dispatched": ("fairway", "slice"),
    # What the captain program says about its own captain agent — that it failed and the stream runs on the
    # program alone, or that its session was refused commands — for a person to read. News, never something
    # owed an answer: not a `told`, which a `read` answers, which clears a park, and which the wait bound and
    # *Waiting on you* count until somebody does. Nothing counts a `noted`, so it can never hold a stream.
    "noted": ("fairway", "what"),
}

#: Why a park stands, as one word a reader and a board can act on without parsing `why`. `limit`: the
#: harness refused the run (a session limit, a rate limit) and the park carries `until`, the instant it
#: lifts by itself. `host`: a change on trunk only a person may make. `question`: a `question` line stands
#: open. `demo`: sent back. `gate`: a mark not set. `silence`: ended for writing nothing. `exit`: `/sail`
#: exited non-zero for any other reason. `ceiling`, `trunk`, `budget`: the decision ceiling, a red trunk,
#: a spent stage budget — the three parks that already clear by rule rather than by answer. `other` is
#: what a park with no `cause` reads as, so every old line has one.
CAUSES = ("limit", "host", "question", "demo", "gate", "silence", "exit", "ceiling", "trunk", "budget",
          "other")
#: The checks a `need` may carry, which is how the harbourmaster ticks it without a person: `text` says a
#: file at `path` holds `has`; `make` says a target exits 0. Both are asked of trunk, never of a berth.
CHECKS = ("text", "make")
#: Who ticks a need: a `person`, or the `fleet` through its `check`.
TICKERS = ("person", "fleet")
#: Where a need is a product or model decision rather than a change to land: the chart and the event
#: model, which say what slices there are and what they record. manda's mender was sent six follow-up
#: slices to add — each needing an event's name, a capability or a place in the split nobody had decided —
#: and refused every one, correctly and at a session's cost each, leaving them for a person.
DECIDED_IN = re.compile(r"^(?:specs/[^/]+/(?:chart\.yaml|story-split\.md)|(?:.*/)?docs/event-model/model\.yaml)$")


def asks_a_decision(need: object) -> bool:
    """Whether a need is a product or model decision — a new slice, an event's name, a change to the split —
    which goes to whoever decides (the skipper under `/cruise`, the person under `/sail`) and never to the
    mender: written so (`decide`, by `fleet.py tell --check decide`), or checked in the chart or the model.
    One that names the hand-back patch carrying it lands with its slice's merge instead (`need_owner.whose`),
    where the harbourmaster withholds a patch that adds or renames an event (`mender.model_patch_refusal`)."""
    if not isinstance(need, dict):
        return False
    if need.get("decide"):
        return True
    check = need.get("check")
    return isinstance(check, dict) and bool(DECIDED_IN.match(str(check.get("path", ""))))


#: What a sentence for a person may not lean on, because a person reading only the board cannot follow it:
#: a requirement or criterion id as the records write it (FR-012, SC-3), a fairway's decision id (D-ORD-07),
#: an example id (GN2-1), a backticked span, and a path. Not a bare `D20`, `SC2`, `R2` or `US-1`: this
#: project's own test bed is a game club, where a D20 is a die, and a file-looking word (`Node.js`,
#: `shelf.json`) is how products are named. `check-decisions` holds a decision's **In short** to it, and
#: `fleet.py tell` a need's and a question's `plain` line: one rule for every sentence a person reads first.
NOT_PLAIN = re.compile(r"\b(?:FR|SC|NFR)-\d+\b|\bD-(?:[A-Z0-9]+-)?\d+\b|\b[A-Z]{2,}\d+-\d+\b|`"
                       r"|(?<![\w/])[\w.-]+(?:/[\w.-]+)+\.\w+\b|(?<![\w/])[\w.-]+/[\w.-]+/[\w./-]+")


def unplain(said: str) -> str:
    """Why a sentence is not one a person reads without the specification open, or `""`: empty, or leaning on
    what `NOT_PLAIN` names, which the reason quotes."""
    if not said.strip():
        return "it is empty: say in a sentence or two, in plain English, what is wrong and why it matters"
    leaned = NOT_PLAIN.search(said)
    return (f"it names {leaned.group(0)!r}; say it without requirement, decision or example ids, backticks or "
            f"paths, so a person reads it without the specification") if leaned else ""


#: The fields a kind may carry beyond what it must. Named so a reader knows the shape to hold them to:
#: `slice` and `waiting` were written and read for months before anything said they existed. A `parked`
#: line is a record, not a paragraph: `cause` from `CAUSES`; `until`, an instant after which the park
#: lifts by itself; `needs`, one item per thing that has to change — `{"what", "by", "check"?, "path"?}` —
#: ticked by the harbourmaster or a person; `then`, one sentence on what the fleet does once they are met.
#: `why` stays, as the paragraph a reader without the board sees.
#: A `told` may carry `needs` in the park's shape: a hand-back that names a shared surface — a dependency,
#: a realm user, a flag line — is a need the harbourmaster ticks against trunk exactly as it ticks a
#: park's, and the board groups under *Waiting on you* rather than filing as a note. recap's 59 told lines
#: held the four things that darkened every story, as notes a person could dismiss. A `seeded` line may say
#: how many `given` records the story appended first, the `api` it ran against and the `story` file.
OPTIONAL: dict[str, tuple[str, ...]] = {
    # A park's `plain` is the sentence a person reads first, as a question's is: `why` is the captain's own.
    "parked": ("slice", "waiting", "cause", "until", "needs", "then", "plain"),
    "told": ("slice", "needs", "by", "story"),
    "seeded": ("given", "api", "story"),
    # One or two sentences a person reads first on the board, held to `unplain` where it is written. A need
    # carries its own `plain` the same way, beside `what`; a line written before either had one still reads.
    "question": ("plain",),
}
#: The instant an `until` is written in: the log's own format, so two logs sort it with everything else.
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

#: What a demo can have said, and the only three. The same three `check-decisions.py` already holds the demo
#: log's markdown to and `benchmark.py` records as an outcome, so this names the vocabulary rather than
#: inventing one: `accepted`, or sent back because the *behaviour* is wrong or because the *implementation*
#: is. The captain reads it — a sent-back demo is a retry and an accepted one closes the slice's gate — and
#: a free-form verdict would make that a guess about somebody's wording.
VERDICTS = ("accepted", "behaviour", "implementation")
#: Field → the only values it may hold, per kind. Checked on the way in *and* on the way out, like every
#: other rule here: a line nobody can interpret reads exactly like a line that was never written.
CLOSED: dict[str, dict[str, tuple[str, ...]]] = {"demo": {"verdict": VERDICTS}, "parked": {"cause": CAUSES}}

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
    # One need of a park, met: `parked` is the park's instant, `need` its index in the park's `needs`,
    # `how` what saw it — the trunk commit a check passed at, or the person's word. A park whose every
    # need has one of these gets its `cleared` receipt without anybody being asked. A `told` with needs is
    # ticked by the same line, `parked` carrying the told's instant.
    "need-met": ("fairway", "parked", "need", "how"),
    # Every need of a `told` met: the receipt that takes it off *Waiting on you*, as `cleared` takes a park.
    "told-met": ("fairway", "told", "what"),
    # A `question` nobody owes an answer any more: the need it was asked for is met, or its slice has merged
    # and a recorded decision answers it. `id` is the question's, `how` says which. manda's S110-decide-2 was
    # answered by D523 and stood open after S110 merged, because only a `decision` with its own id closed it.
    "question-met": ("fairway", "id", "how"),
    "refused": ("fairway", "request", "why"),
    # Trunk's own CI, which is harbour-wide rather than one fairway's: the gate before a merge is `make
    # verify` and CI runs `make ci`, so trunk can go red from a check `verify` never ran. Written once per
    # change of state — a board that said `trunk-red` every fifteen seconds is one nobody reads.
    "trunk-red": ("commit", "job", "why"),
    "trunk-green": ("commit",),
    # Read only, from logs written before 2.1 sent the trunk mender (`mender.py`) instead: `mend` is one
    # attempt, `job` `trunk` or `need`; `mended` says it landed, `commit` being trunk now; `mend-failed` why not.
    "fix-trunk": ("fairway", "slice", "commit", "job"),
    "mend": ("job", "commit", "attempt"),
    "mended": ("job", "commit"),
    # The harbourmaster's receipt of a person's `mend-again`: the attempts the mender spent on that park's needs
    # count from here, so each gets its attempts afresh. `at` is the deck line's instant, written once.
    "mend-again": ("fairway", "parked", "at"),
    "mend-failed": ("job", "why"),
    # The merge ref taken off a machine past its lease: `from` held it, `since` is the last time it said it
    # was still merging. Harbour-wide, because the merge is — and the one line that explains a trunk two
    # machines' gates both touched, should the one that went quiet turn out not to have been dead.
    "merge-taken-over": ("from", "since"),
    # How many slice sessions this fairway may run at once, decided once for every fairway because
    # `boilers` is one budget across all of them: breadth first, then depth by the harbour's priority, each
    # fairway capped at `abreast` — `abreast.py` in the toolkit is the rule. Written when a fairway's number
    # changes and read by its captain before it starts a slice beyond its first; a captain that finds no
    # line at all runs one slice, which is what every captain did before the number existed. `to`, where the
    # number is 0, names the fairway the slot went to, for the `yielded` line that captain then writes.
    "slots": ("fairway", "slots"),
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
    if kind in ("parked", "told"):
        shaped(body)


def shaped(body: dict) -> None:
    """Refuse a park whose record fields are not the shape a reader can hold them to.

    Checked in both directions like everything else here: an `until` nobody can parse is a pause that never
    lifts, and a `needs` item with no `what` is a tick nobody can draw. Refusing is the kinder failure.
    """
    until = body.get("until")
    if until is not None and not (isinstance(until, str) and INSTANT.match(until)):
        raise Unreadable(f"a park's until is an instant like 2026-10-21T20:40:00Z; this one says {until!r}")
    needs = body.get("needs")
    if needs is None:
        return
    if not isinstance(needs, list):
        raise Unreadable("a park's needs is a list, one item per thing that has to change")
    for index, need in enumerate(needs):
        if not isinstance(need, dict) or not str(need.get("what", "")).strip():
            raise Unreadable(f"need {index} of a park says nothing: each need is an object with `what`")
        if need.get("by", "person") not in TICKERS:
            raise Unreadable(f"need {index} is ticked by one of {', '.join(TICKERS)}; this one says "
                             f"{need.get('by')!r}")
        check = need.get("check")
        if check is None and need.get("by") == "fleet":
            # `fleet.py tell` refuses this too; a line written past it is read as a person's (`read`).
            raise Unreadable(f"need {index} is ticked by the fleet and has no check: the harbourmaster ticks "
                             f"only what it can check on trunk, so without one it is a person's")
        if check is None:
            continue
        if not isinstance(check, dict) or check.get("kind") not in CHECKS:
            raise Unreadable(f"need {index}'s check is one of {', '.join(CHECKS)}; this one says "
                             f"{check!r}")
        if check["kind"] == "text" and not (check.get("path") and check.get("has")):
            raise Unreadable(f"need {index}'s text check names a `path` and what it `has`")
        if check["kind"] == "make" and not check.get("target"):
            raise Unreadable(f"need {index}'s make check names a `target`")


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


def written_before_needs_were_records(body: dict) -> dict:
    """A park's needs as records, where it was written when a need was a sentence.

    Read and never written: `entry` still refuses a sentence. recap's LB10 parked with two strings the week
    before needs became `{"what", "by"}`, and every captain started after the upgrade refused the whole
    library log at that line and exited — the board drew the fairway with nothing waiting, because the park
    it was waiting on was the line nobody could read. A sentence is a need only a person can tick, which is
    what it always was.
    """
    needs = body.get("needs")
    if not isinstance(needs, list) or not any(isinstance(need, str) for need in needs):
        return body
    return body | {"needs": [{"what": need, "by": "person"} if isinstance(need, str) else need
                             for need in needs]}


def unchecked_fleet_needs_as_persons(body: dict) -> dict:
    """A need the fleet was to tick with no check to tick it by, read as a person's.

    Read and never written: `entry` refuses one. game-club-manager's CL-01 handed back three — a typed
    `post`, the brand values, a lock file — that the harbourmaster had nothing to run against trunk for, and
    the board offered no Done because the fleet was to tick them, so the hand-back sat under *Waiting on
    you* for good once all three had landed. Nobody but a person can say such a need is met.
    """
    needs = body.get("needs")
    if not isinstance(needs, list) or not any(isinstance(need, dict) and need.get("by") == "fleet"
                                              and need.get("check") is None for need in needs):
        return body
    return body | {"needs": [need | {"by": "person"} if isinstance(need, dict) and need.get("by") == "fleet"
                             and need.get("check") is None else need for need in needs]}


def read(line: str, harbour: bool = False) -> Entry:
    """One line back, or a refusal that says which rule it broke and what to do about it."""
    text = line.strip()
    if not text:
        raise Unreadable("an empty line")
    try:
        body = json.loads(text)
    except (ValueError, RecursionError) as fault:
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
    if kind in ("parked", "told"):
        body = unchecked_fleet_needs_as_persons(written_before_needs_were_records(body))
    closed(kind, body)
    known = {*COMMON, *required}
    return Entry(kind=kind, t=str(body.get("t", "")),
                 fields={name: value for name, value in body.items() if name not in known} |
                        {name: body[name] for name in required})


def deck_path(root: Path, feature: str, fairway: str) -> Path:
    """A fairway's own log. One writer, its captain, so two fairways never meet on one line."""
    return logs_dir(root) / feature / f"{fairway}.jsonl"


def harbour_path(root: Path, machine: str) -> Path:
    """One machine's harbour log. One writer, its harbourmaster, for the same reason a deck log has one."""
    return harbour_dir(root) / f"{machine}.jsonl"


def harbour_logs(root: Path) -> list[Path]:
    """Every harbour log there is: one per machine, plus the single file older projects still have."""
    directory = harbour_dir(root)
    found = sorted(directory.glob("*.jsonl")) if directory.is_dir() else []
    older = older_harbour(root)
    return ([older] if older.is_file() else []) + found


def deck_logs(root: Path) -> list[Path]:
    """Every fairway's log, in name order, and no harbour log.

    The exclusion is by directory and not by one resolved path: every reader of the deck logs globs the
    whole tree, and when there was one harbour log they each compared against it by name. Three of them in
    a directory of their own is a rule a reader can hold instead of a list it has to keep.
    """
    place = logs_dir(root)
    harbour = harbour_dir(root).resolve()
    older = older_harbour(root).resolve()
    return [path for path in sorted(place.rglob("*.jsonl")) if place.is_dir()
            if path.parent.resolve() != harbour and path.resolve() != older]


def charted_feature(root: Path) -> str:
    """The feature the project's one chart is written under — the first in name order with a `chart.yaml` —
    or `""`. Found by its path and never parsed: the keel reads no YAML."""
    found = sorted((root / "specs").glob("*/chart.yaml"))
    return found[0].parent.name if found else ""


def streams(root: Path) -> dict[str, list[Path]]:
    """Each stream's log files by its name, in name order: its one log, under the chart's feature, first.

    A stream has one log. Until sessions were told where it is, one working a further feature's slice wrote
    under that feature's name instead, so a stream can have a second file whose lines are as much its own —
    and the board drew that file as a second stream that never started. Every reader folds them all.
    """
    home = charted_feature(root)
    found: dict[str, list[Path]] = {}
    for path in deck_logs(root):
        found.setdefault(path.stem, []).append(path)
    return {name: sorted(found[name], key=lambda path: path.parent.name != home) for name in sorted(found)}


#: The instant a line records, read without parsing it: a line nobody can parse still has a place in the order.
INSTANT_OF = re.compile(r'"t":\s*"([^"]*)"')


def stream_lines(paths: list[Path]) -> list[str]:
    """One stream's lines from every file that holds them: one file exactly as it is, several interleaved by
    the instant each line records, as `harbour_fold` reads the machines' logs. Within one second the stream's
    own log comes last: its captain answers what a session wrote. OSError where one cannot be read."""
    if len(paths) == 1:
        return paths[0].read_text(encoding="utf-8").splitlines()
    found = [line for path in reversed(paths) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sorted(found, key=lambda line: at.group(1) if (at := INSTANT_OF.search(line)) else "")


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
    found: list[Entry] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            found.append(read(line, harbour))
        except Unreadable as fault:
            # The rule alone sends a person through eleven hundred lines for the one that broke it.
            raise Unreadable(f"line {number}: {fault}") from fault
    return found


def about(park: Entry, slice_id: str) -> bool:
    """Whether a park is about this slice: it names it in its field, or — a park of the whole stream — opens
    its why with the slice's whole id, as `L03: …` or `L03 is awaiting …` do and `L030: …` does not."""
    if park.fields.get("slice"):
        return str(park.fields["slice"]) == slice_id
    return bool(slice_id) and re.match(rf"{re.escape(slice_id)}(?![\w-])", str(park.fields.get("why", ""))) is not None


#: What a captain's park at the decision ceiling waits on, in its `waiting`: lifted by reading, never by a message.
REVIEW = "decision-review"


def answers(told: Entry, park: Entry) -> bool:
    """Whether a `told` is a person's answer to this park: a person wrote it (`by: person`, which the board and
    `/cruise-tell` write and a session never does), after the park, and aimed at it — the stream's word answers
    any park; a word to a slice, only the park `about` that slice."""
    if told.kind != "told" or told.fields.get("by") != "person" or told.t <= park.t:
        return False
    named = str(told.fields.get("slice", ""))
    return not named or about(park, named)


def over_ceiling(unread: int, ceiling: int | None) -> bool | None:
    """Whether more decisions stand unread than the ceiling allows; None where no ceiling can be read."""
    return None if ceiling is None else unread > ceiling


def answer_held(park: Entry, over: bool | None) -> str:
    """Why a person's answer cannot clear this park now, as one word, or `""` where it would. The harbourmaster's
    rule (`told_after_parks`) and the board's *HELD* line both ask this, so the two cannot disagree: `review`, a
    park the captain wrote at the decision ceiling, which only the reading lifts; `ceiling`, more decisions
    unread than the ceiling allows, when *go* is not a reading; `uncounted`, the count could not be read."""
    if park.fields.get("waiting") == REVIEW:
        return "review"
    return "uncounted" if over is None else "ceiling" if over else ""


def open_parks(deck: list[Entry], harbour: list[Entry], fairway: str) -> list[Entry]:
    """The parks that still owe an answer: receipt identity is fairway plus original timestamp.

    A park of one slice is also answered by a later `claimed` of it — the captain took it up again, as
    `clearance.folded` has it. hr-test-2's L13 was worked for hours after its budget park while the board
    listed it as waiting. Later by place in the deck, not timestamp, so a claim in the same second counts.
    """
    receipts = {(str(e.fields["fairway"]), str(e.fields["parked"]))
                for e in harbour if e.kind == "cleared"}
    # A park an earlier slipwai wrote, carried across a migration (`crossed`), that a person dismissed as obsolete.
    dismissed = {str(e.fields.get("told", "")) for e in deck if e.kind == "read" and not e.fields.get("inbox")}
    last_claim = {str(e.fields["slice"]): index for index, e in enumerate(deck)
                  if e.kind == "claimed" and e.fields.get("slice")}
    return [e for index, e in enumerate(deck) if e.kind == "parked" and str(e.fields["fairway"]) == fairway
            and (fairway, e.t) not in receipts and not (e.fields.get("crossed") and e.t in dismissed)
            and last_claim.get(str(e.fields.get("slice") or ""), -1) < index]


def unanswered(asked: Iterable[Entry], answers: Iterable[Entry], fairway: str = "") -> list[Entry]:
    """The `question` lines among `asked` that somebody still owes an answer: no `decision` in `answers`
    carries the question's `id`, and no harbour `question-met` names its fairway and `id`.

    The one rule for whether a question is open, which the board, the captain and clearance all ask. Before
    it, only the board read `question-met`: manda's S110-decide-2 left the board once D523 answered it, and
    clearance still held the slice and the captain still put it to the skipper. `answers` is deck and harbour
    lines together, so a caller passes what it has read; `fairway` is the stream a `question-met` must name,
    or each question's own `fairway` where it is not given.
    """
    decided, met = set(), set()
    for e in answers:
        if e.kind == "decision":
            decided.add(str(e.fields.get("id", "")))
        elif e.kind == "question-met":
            met.add((str(e.fields.get("fairway", "")), str(e.fields.get("id", ""))))
    return [e for e in asked if e.kind == "question" and (named := str(e.fields.get("id", ""))) not in decided
            and (fairway or str(e.fields.get("fairway", "")), named) not in met]


def fairway_parks(parks: list[Entry]) -> list[Entry]:
    """The parks that hold a whole fairway: those naming no `slice`, which is every park written before a
    fairway ran several slices at once, and every park that is about the fairway rather than one slice."""
    return [e for e in parks if not e.fields.get("slice")]


def held_slices(parks: list[Entry]) -> dict[str, str]:
    """Each slice an open park holds on its own, with the latest reason. Its siblings are not held by it."""
    return {str(e.fields["slice"]): str(e.fields.get("why", "")) for e in parks if e.fields.get("slice")}


def cause_of(park: Entry) -> str:
    """The one word a park stands on. A line written before parks had one is `other`."""
    return str(park.fields.get("cause") or "other")


def paused(parks: list[Entry], now: str = "") -> list[Entry]:
    """The open parks that lift by themselves: a `limit`, a `trunk` wait, or an `until` still ahead.

    Nobody is asked anything by one of these, so a board calls them paused and no fleet waits on a person.
    `trunk` is a merge refused only because trunk was red. `now` is an instant in the log's format, or the clock.
    """
    at = now or globals()["now"]()
    return [e for e in parks if cause_of(e) in ("limit", "trunk") or str(e.fields.get("until") or "") > at]


def unmerged(deck: list[Entry]) -> list[str]:
    """Every slice this fairway claimed and has not merged, in the order it claimed them.

    A slice is let go only by merging: a stop, a park since cleared, a machine that went down mid-stage —
    none of them hands a slice back, so all of them leave it here to be carried on. With one slice at a time
    this was the last claimed; with several in flight it is all of them, and a reader that took the last
    would resume one and step past the rest as claimed.
    """
    merged = {str(e.fields.get("slice", "")) for e in deck if e.kind == "merged"}
    found: list[str] = []
    for e in deck:
        named = str(e.fields.get("slice", ""))
        if e.kind == "claimed" and named not in merged and named not in found:
            found.append(named)
    return found
