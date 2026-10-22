"""One stream's log, as a person reads it: a line each, in the words of what happened.

`fleet.py` folds every log into a board — eight columns and a count. That answers *is anything stuck*, and
the moment the answer is yes the next question is always the same one: **what has this stream actually been
doing?** The board cannot answer it, because the answer is forty lines of one file and the board is one row.

So this is the other half: the stream's own log, newest last, each line said rather than printed. A
`mark-set` is not `{"kind": "mark-set", "mark": "OrderPlaced"}`; it is *set OrderPlaced*, and the
difference between those two is whether somebody who is not holding the format in their head can read it.

**It says the kind it does not know.** A line of a kind this has no sentence for is shown as its kind and
its fields rather than skipped — the log grows, and a reader meeting an unfamiliar line should see that
there was one.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .logs import Entry, Unreadable, deck_logs, deck_path, entry, fold, harbour_logs

#: How many lines one stream shows by default. Enough to cover a slice; short enough to read.
RECENT = 60
#: Where `fleet.py start` sends each captain's output, appended across every turn it runs.
RUNNING = ".slipwai/running"
#: How much of a captain's output its window opens on: the tail of a long run rather than all of it.
TAIL = 64 * 1024
#: Where a merge's time went, as the harbourmaster's answer carries it.
TIMINGS = ("waited_s", "lock_s", "gate_s", "attempt")


def said(entry: Entry) -> str:
    """One log line as a sentence. The kind and its fields where there is no sentence for it."""
    at = entry.fields
    kind = entry.kind
    if kind == "claimed":
        return f"claimed {at.get('slice')}"
    if kind == "mark-set":
        return f"set {at.get('mark')} — {at.get('slice')}"
    if kind == "demo":
        return f"demo of {at.get('slice')}: {at.get('verdict')}"
    if kind == "accepted":
        return f"accepted the {at.get('capability')} capability"
    if kind == "demo-due":
        return f"the {at.get('capability')} capability is ready to demo"
    if kind == "merged":
        return f"merged {at.get('slice')} as {str(at.get('commit'))[:8]}"
    if kind == "decision":
        return f"decided {at.get('id')}: {at.get('what')}"
    if kind == "told":
        return f"a person said: {at.get('message')}"
    if kind == "read":
        return f"read what was said at {at.get('told')}"
    if kind == "heartbeat":
        spent = at.get("tokens")
        return "still going" + (f", {spent}k spent" if spent is not None else "")
    if kind == "stowed":
        return f"stowed {at.get('what')} from {at.get('from')} — {at.get('slice')}"
    if kind == "taken-over":
        return f"took {at.get('slice')} over from {at.get('from')}, mid-slice"
    if kind == "stopped":
        return f"asked to stop, mid-way through {at.get('slice')}, which is carried on when it is lit again"
    if kind == "parked":
        return f"parked: {at.get('why')}"
    if kind == "request":
        return f"asked to {at.get('what')}: {at.get('detail')}"
    if kind == "berth-request":
        return "asked for a berth"
    rest = ", ".join(f"{name}={value}" for name, value in at.items())
    return f"{kind}" + (f" ({rest})" if rest else "")


def streams(root: Path) -> list[tuple[str, str]]:
    """Every stream with a log, as (feature, fairway), in name order."""
    return [(path.parent.name, path.stem) for path in deck_logs(root)]


def feature_of(root: Path, fairway: str) -> str:
    """Which feature this stream's log is under, or `''` where it has none."""
    return next((feature for feature, name in streams(root) if name == fairway), "")


def teller() -> str:
    """Whose a `told` is: `person`, which may answer a park, or `session`, which may not.

    The board writes a person's. So does the MCP server — except under a session the captain dispatched,
    which starts it with `SLIPWAI_FAIRWAY` set and inherits it here: a project's `.mcp.json` reaches every
    berth, and a session's note to the host cleared the decision-ceiling park it was meant to wait behind.
    """
    return "session" if os.environ.get("SLIPWAI_FAIRWAY") else "person"


def tell(root: Path, fairway: str, message: str, slice_id: str = "", by: str = "") -> str:
    """Write a person's message into that stream's deck log, or say why it could not be.

    With `slice_id`, the message is for that one slice — the box on a red card on the voyage — and answers
    only that slice's park, never its siblings'.

    Into the deck log rather than anywhere of its own: the log is what the captain reads at its next
    boundary, and a message somewhere else is a message nothing is watching. Here rather than beside the
    board's route for it, because this is a line in a deck log and that is what this module is.

    `by` names a writer that is neither: `feedback`, a person's confirmed feedback handed to the captain,
    which the captain reads and which answers no park.
    """
    if not fairway or not message.strip():
        raise ValueError("a message needs a stream to go to and something to say")
    if slice_id and not re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", slice_id):
        raise ValueError(f"{slice_id!r} is not a slice id")
    feature = feature_of(root, fairway)
    if not feature:
        raise ValueError(f"{fairway} has no log here, so there is nowhere for this to go. "
                         f"A stream gets a log when its captain writes its first line")
    path = root / deck_path(feature, fairway)
    with path.open("a", encoding="utf-8") as handle:
        line = (entry("told", fairway=fairway, message=message.strip(), by=by or teller(), slice=slice_id)
                if slice_id else entry("told", fairway=fairway, message=message.strip(), by=by or teller()))
        handle.write(line.line())
    return f"told {slice_id or fairway}"


def mark_read(root: Path, fairway: str, stamps: list[str]) -> str:
    """Write a `read` receipt for each decision named by its instant, or say why none could be written.

    The receipt the decision ceiling counts, and until this the only way to write one was by hand in a
    terminal: hr-test-2 parked with fourteen decisions over its ceiling and a board that could show them and
    could not take them off. Only a decision in this stream's own log is receipted, so a stale page or a
    mistyped instant writes nothing rather than a receipt for something that was never decided.
    """
    feature = feature_of(root, fairway)
    if not feature:
        raise ValueError(f"{fairway} has no log here, so there is nothing of it to mark read")
    found, fault = entries(root, fairway, feature)
    if fault:
        raise ValueError(fault)
    decided = {e.t for e in found if e.kind == "decision"}
    done = {str(e.fields.get("told")) for e in found if e.kind == "read"}
    wanted = [one for one in dict.fromkeys(stamps) if one in decided and one not in done]
    if not wanted:
        raise ValueError(f"nothing to mark read: {fairway} has no unread decision at those instants")
    with (root / deck_path(feature, fairway)).open("a", encoding="utf-8") as handle:
        for one in wanted:
            handle.write(entry("read", fairway=fairway, told=one).line())
    return f"marked {len(wanted)} decision(s) read in {fairway}"



def tick_need(root: Path, fairway: str, parked: str, need: int) -> str:
    """Write a person's tick of one need of a park: a `need-done` line naming the park and the need.

    Not a `told`: a `told` after a park clears the whole park, and a tick is one item of it. The
    harbourmaster turns the line into its `need-met` receipt on its next pass and clears the park once every
    need has one. Only a need the park actually lists is ticked, so a stale page writes nothing.
    """
    if not fairway or not parked:
        raise ValueError("a tick names the stream, the park's instant and the need")
    found, fault = entries(root, fairway)
    if fault and not found:
        raise ValueError(fault)
    park = next((e for e in found if e.kind == "parked" and e.t == parked), None)
    if park is None:
        raise ValueError(f"{fairway} has no park at {parked}")
    needs = park.fields.get("needs")
    if not isinstance(needs, list) or not 0 <= need < len(needs):
        raise ValueError(f"the park at {parked} has no need {need}")
    path = root / deck_path(feature_of(root, fairway), fairway)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(entry("need-done", fairway=fairway, parked=parked, need=need).line())
    return f"ticked need {need} of {fairway}'s park at {parked}"


def dismiss(root: Path, fairway: str, told: str) -> str:
    """Write the `read` receipt for one `told`, named by its instant, so it leaves *Waiting on you*.

    A session's note for the host — `For the host: …` — is a task for a person, and no decision or claim
    answers it, so it sat under *Waiting on you* until somebody wrote a receipt by hand. Pressing Done on
    it is that receipt. Only a `told` the log actually holds is dismissed: a receipt for nothing is a line
    that would quietly answer a message written later in the same second.
    """
    if not fairway or not told:
        raise ValueError("a dismissal names the stream and the instant of the message it dismisses")
    found, fault = entries(root, fairway)
    if fault and not found:
        raise ValueError(fault)
    if not any(e.kind == "told" and e.t == told for e in found):
        raise ValueError(f"{fairway} has no message at {told} to dismiss")
    path = root / deck_path(feature_of(root, fairway), fairway)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(entry("read", fairway=fairway, told=told).line())
    return f"dismissed {fairway}'s message of {told}"


def entries(root: Path, fairway: str, feature: str = "") -> tuple[list[Entry], str]:
    """One stream's entries, and the fault where its log cannot be read.

    The fault is returned rather than raised, and the entries with it: a log that goes bad at line 90 has
    89 lines somebody still wants, and the whole point of looking at one stream is that something has
    gone wrong with it.
    """
    found = feature or feature_of(root, fairway)
    if not found:
        return [], f"{fairway} has no log here"
    path = root / deck_path(found, fairway)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as fault:
        return [], f"{path} cannot be read ({type(fault).__name__})"
    kept: list[Entry] = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            kept += fold([line])
        except Unreadable as fault:
            return kept, f"line {number} cannot be read: {fault}"
    return kept, ""


def recent(root: Path, fairway: str, limit: int = RECENT) -> tuple[list[tuple[str, str]], str]:
    """The last `limit` lines of one stream as (when, what), and the fault where there is one."""
    found, fault = entries(root, fairway)
    return [(one.t, said(one)) for one in found[-limit:]], fault


def harbour_said(entry: Entry) -> str:
    """One harbour line about a fairway as a sentence: what the harbourmaster did with what it was asked."""
    at = entry.fields
    kind = entry.kind
    if kind == "granted":
        commit = f" at {str(at['commit'])[:8]}" if at.get("commit") else ""
        return f"{at.get('request')} granted{commit}" + (f" · CI {at['ci']}" if at.get("ci") else "")
    if kind == "refused":
        return f"{at.get('request')} refused: {at.get('why')}"
    if kind == "berth-allocated":
        return f"berth {at.get('berth')} allocated"
    if kind == "cleared":
        return f"cleared the park of {at.get('parked')}: {at.get('what')}"
    if kind == "mark-set":
        return f"carried {at.get('mark')} to the other fairways"
    if kind == "park":
        return f"carried the park to the inbox: {at.get('why')}"
    if kind == "fix-trunk":
        return (f"trunk went red at {str(at.get('commit'))[:8]} in {at.get('job')}, "
                f"and this fairway's merge is the one to fix it")
    return said(entry)


def timeline(root: Path, fairway: str) -> tuple[list[dict], str]:
    """One captain's whole history: its deck log, and every harbour line naming its fairway, by time.

    The deck log alone says *asked to merge* and stops; what happened to the request is in the harbour log,
    with the time it took. Read together, a request sits beside its answer. Each line says which slice it
    belongs to — its own `slice` where it has one, else the slice last claimed — and carries the line as
    written, so a reader who wants the fields rather than the sentence has them. Like `entries`, a log that
    goes bad returns what came before it with the fault.
    """
    deck, fault = entries(root, fairway)
    harbour: list[Entry] = []
    for path in harbour_logs(root):
        try:
            found = fold(path.read_text(encoding="utf-8").splitlines(), harbour=True)
        except (OSError, UnicodeDecodeError, Unreadable) as broken:
            fault = fault or f"{path.name} cannot be read ({broken})"
            continue
        harbour += [one for one in found if one.fields.get("fairway") == fairway]
    # By the instant, and at the same instant the captain's line first: an answer is written after what
    # it answers. `sorted` keeps each log's own order inside one second.
    both = sorted([(one, False) for one in deck] + [(one, True) for one in harbour],
                  key=lambda pair: (pair[0].t, pair[1]))
    lines: list[dict] = []
    working = ""
    for one, from_harbour in both:
        if one.kind == "claimed" and not from_harbour:
            working = str(one.fields.get("slice", ""))
        lines.append({
            "t": one.t,
            "who": "harbour" if from_harbour else "person" if one.kind == "told" else "captain",
            "kind": one.kind,
            "slice": str(one.fields.get("slice") or working),
            "what": harbour_said(one) if from_harbour else said(one),
            "timing": {name: one.fields[name] for name in TIMINGS if name in one.fields},
            "line": {"v": one.v, "t": one.t, "kind": one.kind, **one.fields},
        })
    return lines, fault


def output(root: Path, fairway: str, after: int = -1) -> tuple[str, int]:
    """What this captain's process has printed since byte `after`, and the byte it ends at.

    `-1` is a window opening: the last `TAIL` bytes, from the first whole line in them. An `after` past the
    end means the file was started again, so that is answered as an opening too rather than as silence.
    Only a fairway with a deck log here has an output to read, which also keeps the name a fairway's.
    """
    if not feature_of(root, fairway):
        return "", 0
    path = root / RUNNING / f"captain-{fairway}.out"
    try:
        size = path.stat().st_size
        opening = not 0 <= after <= size
        start = max(0, size - TAIL) if opening else after
        with path.open("rb") as handle:
            handle.seek(start)
            data = handle.read(size - start)
    except OSError:
        return "", 0
    if opening and start:
        data = data.partition(b"\n")[2]
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n"), size
