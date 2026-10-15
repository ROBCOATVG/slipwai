#!/usr/bin/env python3
"""What may start now, in which band, and why the rest may not: the chart's marks against the logs.

Version 1's rule was "its own contract is settled", which a slice could only answer about itself. That
serialised a fresh fairway, because nothing said what a slice was waiting *for*. Issue #32 asked for this
one: a slice has clearance when every mark it steers by has been set, and a mark is set when some slice
wrote a `mark-set` line for it at its own first stage, in its own worktree.

So a sibling unblocks this slice by having **planned**, not by having merged. That is the whole of the
parallelism version 2 promises. If a merge were the signal, every fairway would wait on every other one.

**Clearance is one word, and one word hid a distinction that cost a run its afternoon.** A cleared slice may
*prepare* — its example map, the contract it sets, the gaps review — at once, because that is the stage
that writes its own `mark-set` lines; it may *implement* only once those are written and no product
question stands open against it. The page said "run every ready slice whose contract is settled", and a
slice settles its contract by preparing, so a host reading that waited for the one thing the wait was
stopping. The answer here is a **state** per slice rather than a yes: `blocked`, `migration-evidence-required`,
`awaiting-decision`, `preparation-ready`, `implementation-ready`, `running`, `awaiting-demo`, `done`, each
with the sentence that says why, and a **schedule** that says which slices start now, which are queued
and for what reason — no slot, claimed elsewhere, claims unreadable — so a host that has spare capacity and
eligible work left waiting has to have written down why.

**State comes from the log and never from a status field.** In the first attempt `model.yaml` said `planned`
for eight slices that were built and merged, because the field was written at plan time and never
reconciled. A log line is written by the thing that did the work at the moment it did it. The one place the
done marker is read is to *name* a wait, never to clear one: a prerequisite that shipped before marks were
logged has no line at all, and a slice waiting on it is told *migration evidence required* rather than
*blocked*, with the command that records the evidence — `--baseline-marks`, which writes, once, a `mark-set`
line carrying its provenance for every such slice, exactly as `check-decisions.py --adversary-baseline` does
for the adversary log. A reader can always tell a baselined mark from an earned one: the line says so.

This lives in the toolkit rather than in the keel because the things that ask it — a `/sail` session, and
the captain — run inside a generated project, which has no slipwai to import. That is the same reason
`check-chart` and `check-slice-scope` are scripts. The first version of this was a keel module, and it was
unreachable from everything that needed it.

    python3 scripts/agents/clearance.py                    # every slice, its state and why, and the schedule
    python3 scripts/agents/clearance.py BIL-01             # one slice: its state and what it waits on
    python3 scripts/agents/clearance.py --json             # the same, for a board; reaches no network
    python3 scripts/agents/clearance.py --baseline-marks   # once, after a crossing: record shipped marks
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import logs  # noqa: E402


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())
SPECS = ROOT / "specs"
LOGS = ROOT / ".slipwai/logs"
#: Where each machine's harbourmaster writes its own log. A directory of files rather than one file since
#: 11.3, and never a feature's — a `feature` directory and this one are both under `.slipwai/logs`.
HARBOUR_LOGS = LOGS / "harbour"
#: The log format this reader knows. A newer line is refused rather than guessed at.
V = 1
MARK_SET = "mark-set"
#: Offline machine-readable query supported by this script, checked before a board invokes it. Still 1
#: after `states`, `schedule`, `slots` and `claims` were added beside `ready`: every v1 key is there and
#: means what it meant, and a version is bumped for a reader that would otherwise misread, not for one
#: that would merely see more.
QUERY_VERSION = 1
#: Every state a slice can be in, slowest-moving first — the order a slice walks them, so a board can treat
#: it as a scale. `awaiting-decision` sits before the two ready states because a slice with an open
#: question is one nothing may start on, whatever else is true of it.
STATES = ("blocked", "migration-evidence-required", "awaiting-decision", "preparation-ready",
          "implementation-ready", "running", "awaiting-demo", "done")
#: Which band of the ladder each ready state admits a slice to. Preparation is the example map, the
#: contract the slice sets and the gaps review — the stages that end with its `mark-set` lines.
#: Implementation is the plan onward. A delegate is handed exactly one of these.
BANDS = {"preparation-ready": "prepare", "implementation-ready": "implement"}
#: What a baselined `mark-set` line says about itself, so no reader mistakes it for one a stage earned.
BASELINE = "baseline"


def load_yaml(text: str) -> object:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - exercised on a machine without PyYAML
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "PyYAML"], check=True)
        import yaml  # type: ignore[import-not-found]
    return yaml.safe_load(text)


def chart(feature: str = "") -> tuple[dict, str]:
    """The first feature with a chart, and its name. One feature is in flight at a time."""
    for path in sorted(SPECS.glob("*/chart.yaml")) if SPECS.is_dir() else []:
        if feature and path.parent.name != feature:
            continue
        loaded = load_yaml(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded, path.parent.name
    return {}, ""


def features() -> list[str]:
    """Every feature under `specs/`, charted or not. What the chart covers is a subset of this."""
    return sorted(path.name for path in SPECS.iterdir() if path.is_dir()) if SPECS.is_dir() else []


def uncharted(answering: str) -> list[str]:
    """The features this answer is **not** about, and that no chart covers either.

    A project with two features and one chart answers for the charted one and says nothing about the
    other, which is how `/sail <feature>` on an uncharted feature got the charted feature's schedule:
    every slice it asked about came back queued or blocked, because they are in a chart that is not its.
    """
    charts = {path.parent.name for path in SPECS.glob("*/chart.yaml")} if SPECS.is_dir() else set()
    return [name for name in features() if name != answering and name not in charts]


def log_paths(feature: str) -> list[Path]:
    """Every log a mark can be set in: the feature's deck logs, and every machine's harbour log.

    Every machine's, since there is one per machine: a mark another machine's harbourmaster carried is what
    clears a slice here, and reading only one of them would make clearance depend on which machine
    happened to carry it.
    """
    paths = [*(LOGS / feature).glob("*.jsonl")] if (LOGS / feature).is_dir() else []
    paths += [*HARBOUR_LOGS.glob("*.jsonl")] if HARBOUR_LOGS.is_dir() else []
    harbour = LOGS / "harbour.jsonl"
    if harbour.is_file():
        paths.append(harbour)
    return sorted(paths)


def lines(feature: str) -> list[dict]:
    """Every readable line of every log, in file order.

    A line of a kind this reader does not know is kept and ignored by whoever folds it: the logs hold a
    dozen kinds and will grow, and a reader that refused the unfamiliar would break every time one was
    added. A line in a *newer format* is a different matter and stops the read, because guessing which
    fields moved is how a reader reports a run that did not happen.
    """
    found: list[dict] = []
    for path in log_paths(feature):
        for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not text.strip():
                continue
            try:
                line = json.loads(text)
            except ValueError:
                raise SystemExit(f"clearance: {path.name}:{number} is not JSON. A log with a line nobody "
                                 f"can read is a log that answers wrongly rather than not at all.") from None
            if not isinstance(line, dict):
                continue
            if line.get("v") != V:
                raise SystemExit(f"clearance: {path.name}:{number} says v{line.get('v')} and this reader "
                                 f"knows v{V}. Run `slipwai upgrade`.")
            found.append(line)
    return found


def marks_set(feature: str) -> set[str]:
    """Every mark some slice has set, from every fairway's deck log and from the harbour log."""
    return folded(lines(feature)).marks


class Folded:
    """What the logs say about every slice, read once. Every field is folded from lines and none is a status.

    A plain class rather than a dataclass: this script is loaded by path, outside `sys.modules`, by the
    tests and by anything else that runs it without importing it, and a dataclass resolving its own
    annotations needs the module it is in to be registered.
    """

    def __init__(self) -> None:
        #: Each mark that is set, by whichever slice and whichever log.
        self.marks: set[str] = set()
        #: The `mark-set` line that set each mark, so a baselined one can be told from an earned one.
        self.set_by: dict[str, dict] = {}
        self.claimed: dict[str, str] = {}  # slice -> when
        self.merged: dict[str, str] = {}  # slice -> commit
        self.verdict: dict[str, str] = {}  # slice -> the hand's last verdict
        #: Capabilities a person's demo is owed for and has not accepted: `demo-due` without a later `accepted`.
        self.demo_due: set[str] = set()
        #: Open questions per slice: a `question` whose `id` no `decision` has carried since.
        self.questions: dict[str, list[tuple[str, str]]] = {}
        self.parked: dict[str, str] = {}  # fairway -> why
        #: Every slice any line names at all. A done slice with none is one that shipped before marks were logged.
        self.mentioned: set[str] = set()
        #: Slices whose marks `--baseline-marks` recorded: shipped before the mark log, and never work again.
        self.baselined: set[str] = set()


def folded(found: list[dict]) -> Folded:
    """The fold. Order matters for every pair that answers each other — a `decision` closes the `question`
    it names, an `accepted` closes the `demo-due` for its capability, a `claimed` lifts its fairway's park."""
    state = Folded()
    for line in found:
        kind, slice_id = line.get("kind"), str(line.get("slice") or "")
        if slice_id:
            state.mentioned.add(slice_id)
        if kind == MARK_SET and line.get("mark"):
            state.marks.add(str(line["mark"]))
            state.set_by[str(line["mark"])] = line
            if line.get("provenance") == BASELINE and slice_id:
                state.baselined.add(slice_id)
        elif kind == "claimed" and slice_id:
            state.claimed[slice_id] = str(line.get("t", ""))
            state.parked.pop(str(line.get("fairway", "")), None)
        elif kind == "merged" and slice_id:
            state.merged[slice_id] = str(line.get("commit", ""))
        elif kind == "demo" and slice_id:
            state.verdict[slice_id] = str(line.get("verdict", ""))
        elif kind == "demo-due":
            state.demo_due.add(str(line.get("capability", "")))
        elif kind == "accepted":
            state.demo_due.discard(str(line.get("capability", "")))
        elif kind == "question" and slice_id and line.get("id"):
            state.questions.setdefault(slice_id, []).append((str(line["id"]), str(line.get("what", ""))))
        elif kind == "decision" and line.get("id"):
            answered = str(line["id"])
            for asked in state.questions.values():
                asked[:] = [(ident, what) for ident, what in asked if ident != answered]
        elif kind == "parked":
            state.parked[str(line.get("fairway", ""))] = str(line.get("why", ""))
    return state


def observed(charted: dict) -> set[str]:
    """Every slice the chart records as `observed`, which is every slice that is not work.

    An `observed` slice says *this is what the code already does*. Nobody builds it, so nobody is offered
    it — and a later slice that steers by what it sets is cleared the moment the chart is drawn, because
    the behaviour it waits on shipped before this model existed. It owes the model gate the same evidence
    an implemented slice owes — code and scenarios that exist — which is what makes it a record and not a
    way past clearance.
    """
    return {str(slice_id) for slice_id, entry in (charted.get("slices") or {}).items()
            if isinstance(entry, dict) and entry.get("observed") is True}


def already_set(charted: dict) -> set[str]:
    """The marks an `observed` slice sets, which no deck log will ever carry a `mark-set` line for."""
    return {str(mark) for slice_id in observed(charted)
            for mark in (charted.get("slices") or {}).get(slice_id, {}).get("sets") or []}


def steered_by(charted: dict, slice_id: str) -> list[str]:
    entry = (charted.get("slices") or {}).get(slice_id)
    steers = entry.get("steers_by") if isinstance(entry, dict) else None
    return [str(mark) for mark in steers] if isinstance(steers, list) else []


def sets_of(charted: dict, slice_id: str) -> list[str]:
    entry = (charted.get("slices") or {}).get(slice_id)
    sets = entry.get("sets") if isinstance(entry, dict) else None
    return [str(mark) for mark in sets] if isinstance(sets, list) else []


def setter_of(charted: dict, mark: str) -> str | None:
    for slice_id, entry in (charted.get("slices") or {}).items():
        if isinstance(entry, dict) and mark in [str(name) for name in entry.get("sets") or []]:
            return str(slice_id)
    return None


def migration_hold(charted: dict, slice_id: str) -> str | None:
    """The sentence a crossing's record holds this slice with, or None. A record that cannot be read is a
    hold too: an unreadable migration is not one that is finished."""
    # Resolved here and not at import: a test, and a board reading another checkout, point `ROOT` elsewhere.
    migration = ROOT / ".slipwai/migration.json"
    if not migration.is_file():
        return None
    try:
        state = json.loads(migration.read_text(encoding="utf-8"))
        if state.get("v") != 1 or not isinstance(state.get("features"), dict):
            return "migration state is newer or unreadable; run `slipwai upgrade` then `python3 scripts/check-migration.py`"
        record = state["features"].get(str(charted.get("feature") or ""), {"proposed": [], "unplaced": []})
        if not isinstance(record, dict) or not all(isinstance(record.get(key), list) and
                all(isinstance(name, str) and name for name in record[key]) for key in ("proposed", "unplaced")):
            raise ValueError("malformed migration feature")
        fairway = (charted.get("slices") or {})[slice_id].get("fairway")
        if fairway in (record.get("proposed") or []) or slice_id in (record.get("unplaced") or []):
            return f"{slice_id}'s fairway needs confirmation; run `python3 scripts/check-migration.py --confirm`"
    except (OSError, ValueError, TypeError, AttributeError):
        return "migration state is unreadable; restore .slipwai/migration.json then run `python3 scripts/check-migration.py`"
    return None


def cleared(charted: dict, settled: set[str], slice_id: str) -> bool | str:
    """`True`, or the sentence saying what this slice waits on and who owes it.

    Every missing mark, not the first: a fairway told one blocker at a time is a fairway blocked once per
    blocker. A slice the chart does not name is refused rather than cleared, because answering yes for an
    uncharted slice would clear anything anybody asked about.
    """
    if slice_id not in (charted.get("slices") or {}):
        return f"{slice_id} is not on the chart, so nothing says what it steers by"
    held = migration_hold(charted, slice_id)
    if held:
        return held
    waiting = [mark for mark in steered_by(charted, slice_id) if mark not in settled]
    if not waiting:
        return True
    owed = [f"{mark} (set by {setter_of(charted, mark)})" if setter_of(charted, mark)
            else f"{mark} (no slice sets it — the chart is wrong)" for mark in waiting]
    return f"{slice_id} steers by {', '.join(owed)}, and none of those is set yet"


def preferred_fairways(config: Path) -> list[str]:
    """The fairway order the harbour holds — `fairways` in `harbour.json`, set while a run is going.

    Read on every query rather than once, because that is the point of it: a person moves a stream up at
    half past three and the next boundary is where it takes effect.
    """
    try:
        held = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return []
    wanted = held.get("fairways") if isinstance(held, dict) else None
    return [str(name) for name in wanted] if isinstance(wanted, list) else []


def fairway_order(charted: dict, preferred: list[str]) -> list[str]:
    """Every fairway the chart names, in the order their captains are lit — slice 18.2.

    **The `fairways` block's order, and the harbour's answer over it.** With fewer berths than fairways,
    which captain is lit is which stream the run makes progress on at all, so it is a priority and is read
    from the block the split wrote rather than from wherever a fairway's first slice happens to fall. Both
    profiles write that block deliberately: `/chart` with a person present, the renderer from the model.

    `preferred` is `fairways` in `harbour.json`, which `slipwai telegraph --set fairways=billing` writes. It
    moves the names it holds to the front and does nothing else. It is **not** the list of fairways to run:
    one that silently stopped the streams it did not name would be a way to park a fairway nobody meant to
    park, and a name left behind after the chart changed would then park the lot. So the chart says which
    fairways there are, and the harbour says which of them goes first.
    """
    named = [str(name) for name in (charted.get("fairways") or {})]
    if not named:
        # A chart without the block, which `check-chart` refuses but a half-written feature can be holding.
        for body in (charted.get("slices") or {}).values():
            name = str((body or {}).get("fairway", "")) if isinstance(body, dict) else ""
            if name and name not in named:
                named.append(name)
    first = [name for name in preferred if name in named]
    return first + [name for name in named if name not in first]


def fairway_of(charted: dict) -> dict[str, str]:
    """Which fairway each slice belongs to, for a reader that has the states and not the chart."""
    return {str(slice_id): str((body or {}).get("fairway", ""))
            for slice_id, body in (charted.get("slices") or {}).items()}


def order_reasons(charted: dict) -> list[tuple[str, str]]:
    """Every slice in the chart's own order, with what that position is read off — slice 18.1.

    The order of the `slices` block is the order every captain takes them in: `next_slice` walks it top to
    bottom, the ready set is in it, and merges inside a fairway are in it. It was written by the split as a
    side effect of writing the rows, so the one decision that governs what the whole loop does next was the
    only one nobody argued. This is what the split reads out to propose it, and a proposal is an order with
    a reason per row — the `/chart` rule, applied to the stage that commits the running order.

    Three clauses, in the order a person weighs them. **What holds it** is the hard constraint and comes
    first: a row cannot go above the slices that set the marks it steers by, whatever anybody prefers.
    **What waits on it** is the judgement the proposal is actually about — a slice four siblings steer by
    is a slice that unblocks a fairway by going early. **Where it falls in its capability** is last and is
    the reason not to shuffle rows purely by weight: a capability is what a person's demo is of, so a
    capability's slices finishing together is worth more than the odd slice starting sooner.
    """
    slices = charted.get("slices") or {}
    waited_on: dict[str, int] = {}
    for body in slices.values():
        for mark in (body or {}).get("steers_by") or []:
            waited_on[str(mark)] = waited_on.get(str(mark), 0) + 1
    seen: dict[str, str] = {}
    found: list[tuple[str, str]] = []
    for slice_id, body in slices.items():
        slice_id, body = str(slice_id), body or {}
        if body.get("observed"):
            found.append((slice_id, "observed — already in the tree, so it is a record and not work"))
            continue
        holds = [f"{mark} ({setter_of(charted, str(mark)) or 'nobody — the chart is wrong'})"
                 for mark in body.get("steers_by") or []]
        sets = [str(mark) for mark in body.get("sets") or []]
        waiting = sum(waited_on.get(mark, 0) for mark in sets)
        capability = str(body.get("capability") or "")
        said = [f"steers by {said_list(holds)}" if holds else "steers by nothing"]
        said.append(f"sets {said_list(sets)}, which "
                    f"{'nothing' if not waiting else f'{waiting} slice' + ('s' if waiting > 1 else '')} "
                    f"steers by" if sets else "sets nothing")
        if capability:
            said.append(f"first of {capability}" if capability not in seen
                        else f"{capability}, after {seen[capability]}")
            seen.setdefault(capability, slice_id)
        found.append((slice_id, "; ".join(said)))
    return found


def said_list(names: list[str]) -> str:
    """`a`, `a and b`, `a, b and c` — a list a person reads rather than one a parser does."""
    if len(names) <= 1:
        return names[0] if names else ""
    return f"{', '.join(names[:-1])} and {names[-1]}"


def cleared_slices(charted: dict, settled: set[str]) -> list[str]:
    """Every slice that may start now, in the chart's own order, which is split order.

    An `observed` slice is never among them: it is a record of what the code does, not work somebody takes,
    and a ready set that offered one would send a captain to build what is already built.
    """
    never = observed(charted)
    settled = settled | already_set(charted)
    return [str(slice_id) for slice_id in (charted.get("slices") or {})
            if str(slice_id) not in never
            and cleared(charted, settled, str(slice_id)) is True]


def reaches(charted: dict, folded_logs: Folded, slice_id: str) -> list[str]:
    """The siblings a wait on this slice reaches: every slice steering by a mark it has not set yet."""
    unset = {mark for mark in sets_of(charted, slice_id) if mark not in folded_logs.marks}
    return [str(other) for other in (charted.get("slices") or {})
            if str(other) != slice_id and unset & set(steered_by(charted, str(other)))]


def position(charted: dict, folded_logs: Folded, slice_id: str,
             done: frozenset[str] | set[str] = frozenset()) -> tuple[str, str]:
    """This slice's state, and the sentence that says why.

    `done` is the done marker's set — a register row or `status: implemented` — and it is read for two
    purposes only: to say *migration evidence required* instead of *blocked* when the setter a slice waits
    on has shipped and has no line in any log, and to keep such a slice out of the ready set, because a
    slice that shipped before the mark log is a record and not work. It never clears anything. A reader
    that cleared on a status field is the reader the first attempt had, and it said `planned` for eight
    merged slices; a slice the marker names *and* a log mentions is read from the log.
    """
    entry = (charted.get("slices") or {}).get(slice_id)
    if not isinstance(entry, dict):
        return "blocked", f"{slice_id} is not on the chart, so nothing says what it steers by"
    if slice_id in folded_logs.merged:
        return "done", f"merged at {folded_logs.merged[slice_id][:8] or 'an unrecorded commit'}"
    if slice_id in folded_logs.baselined:
        return "done", "shipped before the mark log; its marks were recorded by --baseline-marks, not earned by a stage"
    if slice_id in done and slice_id not in folded_logs.mentioned:
        return "done", ("the done marker says it shipped and no log has a line for it — a record from before the "
                        "mark log, not work; `--baseline-marks` records the marks it sets")
    fairway = str(entry.get("fairway", ""))
    if fairway in folded_logs.parked:
        return "awaiting-decision", f"its fairway {fairway} is parked — {folded_logs.parked[fairway]}"
    asked = folded_logs.questions.get(slice_id) or []
    if asked:
        held = ", ".join(f"{ident}: {what}" for ident, what in asked)
        reached = reaches(charted, folded_logs, slice_id)
        tail = f"; the answer unblocks {', '.join(reached)}" if reached else "; no sibling waits on it"
        return "awaiting-decision", f"a question stands open ({held}){tail}"
    settled = folded_logs.marks | already_set(charted)
    answer = cleared(charted, settled, slice_id)
    if answer is not True:
        if "migration" in answer or "check-migration" in answer:
            return "migration-evidence-required", answer
        waiting = [mark for mark in steered_by(charted, slice_id) if mark not in settled]
        unlogged = [mark for mark in waiting
                    if (who := setter_of(charted, mark)) and who in done and who not in folded_logs.mentioned]
        if unlogged:
            who = ", ".join(sorted({str(setter_of(charted, mark)) for mark in unlogged}))
            return ("migration-evidence-required",
                    f"{slice_id} steers by {', '.join(unlogged)}, set by {who}, which the done marker says shipped "
                    f"and no log has a line for — it predates the mark log. Record the evidence once with "
                    f"`python3 scripts/agents/clearance.py --baseline-marks`; nothing is cleared on the marker alone")
        asking = [f"{mark} (set by {who}, which is awaiting decision)" for mark in waiting
                  if (who := setter_of(charted, mark)) and folded_logs.questions.get(who)]
        if asking:
            return "blocked", f"{slice_id} steers by {', '.join(asking)}"
        return "blocked", answer
    own = sets_of(charted, slice_id)
    unset = [mark for mark in own if mark not in settled]
    if slice_id in folded_logs.claimed:
        capability = str(entry.get("capability", ""))
        if capability and capability in folded_logs.demo_due:
            return "awaiting-demo", f"its capability {capability} is due a person's demo; nothing else of it waits"
        verdict = folded_logs.verdict.get(slice_id, "")
        if verdict and verdict != "accepted":
            return "running", f"sent back at the hand's demo ({verdict}); its delegate is retrying"
        band = f"preparing — its own {', '.join(unset)} not set yet" if unset else "implementing — its own marks set"
        return "running", f"claimed at {folded_logs.claimed[slice_id] or 'an unrecorded instant'}; {band}"
    if unset:
        return ("preparation-ready",
                f"cleared; may prepare now — example map, the contract it sets, gaps — and implementation waits "
                f"on its own mark-set for {', '.join(unset)}")
    provenance = [mark for mark in own if (folded_logs.set_by.get(mark) or {}).get("provenance") == BASELINE]
    said = f" ({', '.join(provenance)} recorded by baseline, not earned by a stage)" if provenance else ""
    return "implementation-ready", (f"cleared and its own marks set{said}" if own
                                    else "cleared and sets nothing, so there is nothing to settle")


def positions(charted: dict, folded_logs: Folded,
              done: frozenset[str] | set[str] = frozenset(),
              fairways: list[str] | None = None) -> dict[str, tuple[str, str]]:
    """Every slice that is work, in the order it is offered, with its state. `observed` ones are not.

    Split order, under the fairway priority — slice 18.2. `fairways` is that priority, and the sort by it
    is stable, so **within one fairway the chart's own order is untouched**: across streams the priority
    decides which gets a scarce slot, and inside one the split's order is the whole rule, which is what
    makes the merge order predictable. None leaves the rows exactly as the chart has them, which is what
    every caller that has no fairway question gets and what this did before there was one.
    """
    never = observed(charted)
    found = {str(slice_id): position(charted, folded_logs, str(slice_id), done)
             for slice_id in (charted.get("slices") or {}) if str(slice_id) not in never}
    if not fairways:
        return found
    place = {name: number for number, name in enumerate(fairways)}
    of_fairway = fairway_of(charted)
    return dict(sorted(found.items(),
                       key=lambda row: place.get(of_fairway.get(row[0], ""), len(place))))


def schedule(found: dict[str, tuple[str, str]], slots: int | None,
             claims: set[str] | None) -> dict[str, list[dict[str, str]]]:
    """Which slices start now, in which band, and — for every eligible slice that does not — why.

    `slots` is how many more delegates may be in flight; None is unbounded, which is a harness that said
    nothing. `claims` is what the forge's `slice/<id>` branches say is taken elsewhere; **None means the
    read failed**, and a failed read starts nothing: every slice reading as unclaimed is exactly the answer
    that lets two sessions take one, so the queue says *claims could not be read* and the host fixes the
    read before it fills a slot. Running and waiting slices are listed so the host answers the question
    that is always asked next — why is this one not going — without a second query.

    The rows are walked in the order they come in, which is the order `positions` put them in: the chart's
    own, under the fairway priority of slice 18.2. So a scarce slot goes to the stream that is meant to have
    it without this having to know what a fairway is.
    """
    start: list[dict[str, str]] = []
    queued: list[dict[str, str]] = []
    waiting: list[dict[str, str]] = []
    running: list[dict[str, str]] = []
    done: list[dict[str, str]] = []
    for slice_id, (state, why) in found.items():
        band = BANDS.get(state)
        if band is None:
            row = {"slice": slice_id, "state": state, "why": why}
            (done if state == "done" else running if state in ("running", "awaiting-demo") else waiting).append(row)
            continue
        row = {"slice": slice_id, "band": band, "state": state}
        if claims is None:
            queued.append({**row, "why": "claims could not be read — nothing is started on the strength of it"})
        elif slice_id in claims:
            queued.append({**row, "why": "claimed on the forge by another session"})
        elif slots is not None and len(start) >= slots:
            queued.append({**row, "why": f"no slot: {slots} may start this turn and {len(start)} already have"})
        else:
            start.append({**row, "why": why})
    return {"start": start, "queued": queued, "waiting": waiting, "running": running, "done": done}


def done_marked(feature: str) -> set[str]:
    """The done marker's set, as the ladder writes it: a register row, or `status: implemented` in the model.

    Read in two places and for one reason each: to *name* a wait as migration evidence required, and to
    say which slices `--baseline-marks` may record. Never to clear a slice.
    """
    found: set[str] = set()
    register = SPECS / feature / "slices/README.md"
    if register.is_file():
        for text in register.read_text(encoding="utf-8").splitlines():
            if text.strip().startswith("|"):
                first = text.strip().strip("|").split("|")[0].strip().strip("`")
                if first and first[0].isalpha() and any(ch.isdigit() for ch in first) and first.lower() != "slice":
                    found.add(first.split()[0])
    model = ROOT / "docs/event-model/model.yaml"
    if model.is_file():
        loaded = load_yaml(model.read_text(encoding="utf-8"))
        slices = loaded.get("slices") if isinstance(loaded, dict) else None
        for item in slices if isinstance(slices, list) else []:
            if isinstance(item, dict) and item.get("status") == "implemented" and item.get("id"):
                found.add(str(item["id"]))
    return found


def baseline(charted: dict, done: set[str], found: list[dict], machine: str,
             write: Path | None = None) -> tuple[list[logs.Entry], str]:
    """The `mark-set` lines a crossing owes, each carrying its provenance, and the sentence for a person.

    For every done slice no log has a line for, one line per mark its `sets` names, saying `baseline` and
    what the evidence was. Written to this machine's harbour log — the log that carries marks between
    fairways, and the one place a mark set by nobody's stage belongs — and refused outright where any
    baselined line already exists: a baseline is the done set at one moment, not a way past the gate later.
    """
    if any(line.get("kind") == MARK_SET and line.get("provenance") == BASELINE for line in found):
        return [], ("a baseline was already taken; a slice finished since writes its own mark-set at its first "
                    "stage, and a second baseline would be a way past that")
    folded_logs = folded(found)
    owed: list[logs.Entry] = []
    for slice_id, entry in (charted.get("slices") or {}).items():
        slice_id = str(slice_id)
        if slice_id not in done or slice_id in folded_logs.mentioned or not isinstance(entry, dict):
            continue
        for mark in sets_of(charted, slice_id):
            if mark in folded_logs.marks:
                continue
            owed.append(logs.entry(MARK_SET, harbour=True, fairway=str(entry.get("fairway", "")), slice=slice_id,
                                   mark=mark, provenance=BASELINE, by=machine,
                                   evidence="done marker: a register row or status: implemented, read once "
                                            "by --baseline-marks"))
    if not owed:
        return [], "every done slice already has a line — nothing to baseline"
    if write is not None:
        write.parent.mkdir(parents=True, exist_ok=True)
        with open(write, "a", encoding="utf-8") as handle:
            for row in owed:
                handle.write(row.line())
    return owed, f"baselined {len(owed)} mark(s) for {len({row.fields['slice'] for row in owed})} shipped slice(s)"


def numbers_from(config: Path, running: int) -> dict[str, int | None]:
    """The telegraph's two concurrency numbers and what they bound this turn, read from `harbour.json`.

    Two numbers, because they bound two different things and a run confused them once: `boilers` is how
    many slices may run at once — one `sail-slice-watch` delegate each — and `fanout` is how many delegates
    may run *inside* one slice, the `[P]` siblings a whole-slice delegate hands to `sail-implement-shipwright`.
    `slots` is boilers less the slices already running; `tree` is the most agents the harness is asked for
    at the fan-out's widest, boilers × (1 + fanout). None where no harbour.json says — a harness that said
    nothing is not bounded here, and the page says what to do with that.
    """
    try:
        held = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        held = {}
    held = held if isinstance(held, dict) else {}
    boilers = held.get("boilers") if isinstance(held.get("boilers"), int) else None
    fanout = held.get("fanout") if isinstance(held.get("fanout"), int) else None
    return {"boilers": boilers, "fanout": fanout, "running": running,
            "slots": max(0, boilers - running) if boilers is not None else None,
            "tree": boilers * (1 + fanout) if boilers is not None and fanout is not None else None}


def slots_from(config: Path, running: int) -> int | None:
    """How many more slices this turn may start: the telegraph's `boilers` less what is already running."""
    return numbers_from(config, running)["slots"]


def numbers_line(numbers: dict[str, int | None]) -> str:
    """The one line that says what bounds what, so a host never again reads one number as the other."""
    if numbers["boilers"] is None:
        return "slots: unbounded — no `boilers` in harbour.json"
    inside = (f" · fanout {numbers['fanout']} delegate(s) inside each slice · tree ≤ {numbers['tree']} agents"
              if numbers["fanout"] is not None else " · no `fanout` in harbour.json")
    return (f"slots: {numbers['slots']} slice(s) may start (boilers {numbers['boilers']} − {numbers['running']} "
            f"running){inside}")


def say_order(charted: dict, feature: str) -> int:
    """The chart's running order with what each row is read off, for the split to propose from — 18.1.

    Reads the chart and no log: this is asked before any slice has started, by the stage that is deciding
    what the order should be. Everything else here answers *what may start now*, which is a question about
    a run; this one is about the decision the run will then follow.
    """
    rows = order_reasons(charted)
    print(f"clearance: {feature} — {len(rows)} slices in the chart's order, "
          f"which is the order every captain takes them in")
    width = max((len(slice_id) for slice_id, _ in rows), default=0)
    for place, (slice_id, why) in enumerate(rows, start=1):
        fairway = str(((charted.get("slices") or {}).get(slice_id) or {}).get("fairway", ""))
        print(f"  {place:>3}  {slice_id:<{width}}  {fairway}  — {why}")
    print("\nPropose this order or a better one, a reason per row, and write what the person confirms: the "
          "`slices` block's order is the decision.")
    return 0


def main(argv: list[str]) -> int:
    if "--json" in argv:
        # A board's read query never installs a dependency or reaches the network.
        try:
            import yaml  # noqa: F401
        except ImportError:
            print(json.dumps({"v": QUERY_VERSION, "error": "PyYAML is not installed. Run `python3 -m pip install PyYAML` "
                                       "in this project's Python environment"}))
            return 1
    requested = ""
    if "--feature" in argv:
        index = argv.index("--feature") + 1
        if index >= len(argv) or argv[index].startswith("--"):
            print(json.dumps({"v": QUERY_VERSION, "error": "give a feature name. Run "
                             "`python3 scripts/agents/clearance.py --json --feature <feature>`"}))
            return 1
        requested = argv[index]
    charted, feature = chart(requested)
    # **Cannot schedule, rather than a calm nothing.** A feature somebody named and no chart covers is the
    # one case where silence is worst: the answer that came back was the *other* feature's, every slice in
    # it read as queued or blocked, and a run took that for "nothing may start" and went its own way.
    if requested and not charted:
        known = ", ".join(path.parent.name for path in sorted(SPECS.glob("*/chart.yaml"))) or "none"
        said = (f"cannot schedule {requested}: it has no specs/{requested}/chart.yaml, so nothing says what "
                f"its slices set or steer by. Run `make chart` for it. Charted here: {known}")
        print(json.dumps({"v": QUERY_VERSION, "error": said}) if "--json" in argv
              else f"clearance: {said}", file=None if "--json" in argv else sys.stderr)
        return 1
    if "--json" in argv and not charted:
        print(json.dumps({"v": QUERY_VERSION, "error": "no readable chart exists. Run `make chart`"}))
        return 1
    if not charted:
        print("clearance: no chart yet, so nothing is waiting on anything")
        return 0
    if "--order" in argv:
        return say_order(charted, feature)
    found = lines(feature)
    done = done_marked(feature)
    if "--baseline-marks" in argv:
        machine = logs.machine()
        written, said = baseline(charted, done, found, machine, ROOT / logs.harbour_path(machine))
        for row in written:
            print(f"  {row.fields['slice']} sets {row.fields['mark']} — recorded, provenance {BASELINE}")
        print(f"clearance: {said}")
        return 0 if written or "nothing to baseline" in said else 1
    folded_logs = folded(found)
    order = fairway_order(charted, preferred_fairways(ROOT / "harbour.json"))
    states = positions(charted, folded_logs, done, order)
    claims: set[str] | None = set(folded_logs.claimed)
    if "--claims-unreadable" in argv:
        claims = None
    elif "--claims" in argv:
        index = argv.index("--claims") + 1
        claims = {name for name in (argv[index] if index < len(argv) else "").split(",") if name}
    in_flight = sum(1 for state, _ in states.values() if state in ("running", "awaiting-demo"))
    numbers = numbers_from(ROOT / "harbour.json", in_flight)
    slots = numbers["slots"]
    if "--slots" in argv:
        index = argv.index("--slots") + 1
        slots = int(argv[index]) if index < len(argv) and argv[index].lstrip("-").isdigit() else slots
        numbers = {**numbers, "slots": slots}
    planned = schedule(states, slots, claims)
    if "--json" in argv:
        settled = folded_logs.marks | already_set(charted)
        # Keyed in the fairway priority, so a reader takes the first key and has the stream that is
        # meant to go first rather than the one the chart happens to name first.
        ready: dict[str, list[str]] = {}
        of_fairway = fairway_of(charted)
        for slice_id in sorted(cleared_slices(charted, settled),
                               key=lambda one: order.index(of_fairway.get(one, ""))
                               if of_fairway.get(one, "") in order else len(order)):
            ready.setdefault(of_fairway.get(slice_id, ""), []).append(slice_id)
        print(json.dumps({"v": QUERY_VERSION, "feature": feature, "ready": ready, "fairways": order,
                          "states": {slice_id: {"state": state, "why": why, "band": BANDS.get(state)}
                                     for slice_id, (state, why) in states.items()},
                          "slots": slots, "numbers": numbers,
                          "claims": "unreadable" if claims is None else sorted(claims),
                          "schedule": planned}))
        return 0
    asked = [arg for arg in argv if not arg.startswith("--") and arg not in (requested,)
             and (argv.index(arg) == 0 or argv[argv.index(arg) - 1] not in ("--feature", "--claims", "--slots"))]
    if asked:
        slice_id = asked[0]
        state, why = position(charted, folded_logs, slice_id, done)
        print(f"clearance: {slice_id} is {state} — {why}")
        return 0 if state in BANDS else 1
    print(f"clearance: {len(planned['start'])} of {len(states)} slices start now in {feature}"
          f" (slots: {'unbounded' if slots is None else slots})")
    if (elsewhere := uncharted(feature)):
        print(f"  this answer is about {feature} alone; {', '.join(elsewhere)} "
              f"{'has' if len(elsewhere) == 1 else 'have'} no chart and nothing here is about "
              f"{'it' if len(elsewhere) == 1 else 'them'}")
    print(f"  {numbers_line(numbers)}")
    for row in planned["start"]:
        print(f"  start  {row['slice']}  {row['band']}  — {row['why']}")
    for row in planned["queued"]:
        print(f"  queued {row['slice']}  {row['band']}  — {row['why']}")
    for row in planned["running"]:
        print(f"  {row['state']:<9} {row['slice']}  — {row['why']}")
    for row in planned["waiting"]:
        print(f"  {row['state']:<9} {row['slice']}  — {row['why']}")
    for row in planned["done"]:
        print(f"  done   {row['slice']}  — {row['why']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
