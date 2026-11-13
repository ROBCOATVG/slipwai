"""How far up the ladder one slice in flight has climbed, said as the chip on its card.

The voyage's columns say whether a slice is at work, queued for a slot or waiting on a person, and nothing
about how far it has got: a slice an hour from its merge and one still mapping its examples were the same
amber card, and a run that was moving looked stuck between commits. Every rung leaves evidence already —
an artifact on its `slice/<id>` branch, or a line in its stream's log — so the stage is read off those and
never stored.

**The same rungs, in the same order, as the captain's `progress()`** (`scripts/agents/captain.py`, which
chooses who takes a free slot): a merge request, a demo, a review, review findings stowed, the task list,
the plan, the example map. The captain ranks by them; the board names them. The two are kept as two tables
rather than one carried module because the captain only needs a number and the board needs the words, and
`tests/test_voyage.py` holds the order to the captain's so they cannot drift apart unnoticed.

**The chip says what the slice is doing now, and the rank what it has reached.** They parted in
game-club-manager: TB1's merge request was refused on a red trunk at 12:37 and its chip said `Merging` for
three hours of work after; AC2 said `Implementing · 13/13` while it mended a gate refusal; and every count
went `0/13` to `13/13` in one step, because the session ticks `tasks.md` a batch at a time while the branch
takes a commit a minute naming its task. So a merge request is read with the harbour's answer to it, a stage
left open is not believed past a later line of the log, and a task is counted from the commit that did it.

**Cheap enough for a poll that runs every few seconds.** One `git rev-parse` per slice in flight, and the
branch is only read again when its head has moved.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from .logs import Entry

#: Rung, the word on the chip, and what moves a slice onto it: a line in its log, or a file on its branch.
#: The numbers are the captain's `LOG_RUNGS` and `FILE_RUNGS`, so the board and the captain rank alike.
LOGGED = {"request": (8, "Merging"), "demo": (7, "Demo"), "stowed": (5, "Review")}
FILED = {"review.md": (6, "Review"), "tasks.md": (4, "Implementing"), "plan.md": (3, "Planning"),
         "research.md": (3, "Planning"), "examples.md": (2, "Example mapping")}
#: The word for each stage `benchmark.py` brackets, by the stage name's first word: `implement-shipwright` and
#: `implement` are both Implementing. A stage not named here is said as its own name.
STAGES = {"example": "Example mapping", "gaps": "Example mapping", "contracts": "Example mapping",
          "skipper": "Deciding", "plan": "Planning", "tasks": "Planning", "analyze": "Planning",
          "screen": "Designing", "design": "Designing", "implement": "Implementing", "converge": "Converging",
          "demo": "Demo", "review": "Review", "adversary": "Attack review", "mutation": "Mutation testing"}
#: A task line in `tasks.md`: `- [ ] T001 …` or `- [x] T001 …`.
TASK = re.compile(r"^\s*[-*] \[( |x|X)\] (?:(T\d+)\b)?", re.M)
#: A task, or a run of them, as a commit's subject names it: `T004`, `T001-T006`, `T011–T017`.
NAMED = re.compile(r"\bT(\d+)(?:\s*[-–]\s*T(\d+))?\b")
#: The chips that carry the task count.
COUNTED = ("Implementing", "Tasks done")
#: The lines of a slice's log that say it has moved on from whatever stage its berth left open.
MOVED = ("demo", "stowed", "mark-set", "merged")
#: The branch read last time, by slice, with its head: what the branch said is only read again when it moved.
SEEN: dict[tuple[str, str], tuple[str, dict[str, str]]] = {}


def git(root: Path, *argv: str) -> str:
    done = subprocess.run(["git", "-C", str(root), *argv], capture_output=True, text=True, check=False,
                          encoding="utf-8", errors="replace")
    return done.stdout if done.returncode == 0 else ""


def branch_facts(root: Path, feature: str, slice_id: str) -> dict[str, str]:
    """What the slice's branch carries: which ladder artifacts, how many tasks are ticked, its last commit."""
    ref = f"refs/heads/slice/{slice_id}"
    head = git(root, "rev-parse", "--verify", "--quiet", ref).strip()
    if not head:
        return {}
    key = (str(root.resolve()), slice_id)
    held = SEEN.get(key)
    if held and held[0] == head:
        return held[1]
    folder = f"specs/{feature}/slices/{slice_id}/"
    files = [Path(line).name for line in git(root, "ls-tree", "--name-only", ref, folder).splitlines()]
    facts = {"files": ",".join(sorted(name.removesuffix(".md") for name in files if name in FILED)),
             "commit": git(root, "log", "-1", "--format=%cI %s", ref).strip(),
             "at": git(root, "log", "-1", "--format=%ct", ref).strip()}
    if "tasks.md" in files:
        ticks = TASK.findall(git(root, "show", f"{ref}:{folder}tasks.md"))
        ticked = {name for tick, name in ticks if tick.strip() and name}
        done = named_tasks(root, ref, f"{folder}tasks.md", slice_id) & {name for _, name in ticks} - ticked
        facts["tasks"] = f"{sum(1 for tick, _ in ticks if tick.strip()) + len(done)}/{len(ticks)}" if ticks else ""
    SEEN[key] = (head, facts)
    return facts


def named_tasks(root: Path, ref: str, tasks: str, slice_id: str) -> set[str]:
    """The tasks this slice's own commits name since its task list was written: `GN2 T004: …`, `CL3: T025 …`.

    The checkbox is ticked by the session, a batch at a time; the commit that did the task lands as it is
    done. Only a subject that opens with the slice's id counts, so a sibling's commit merged in from trunk
    is not this slice's progress, and the commit that wrote the list — `tasks T001-T029` — is before the range.
    """
    wrote = git(root, "log", "-1", "--diff-filter=A", "--format=%H", ref, "--", tasks).strip()
    found: set[str] = set()
    for subject in git(root, "log", "--format=%s", f"{wrote}..{ref}").splitlines() if wrote else []:
        if not re.match(rf"{re.escape(slice_id)}\b", subject):
            continue
        for first, last in NAMED.findall(subject):
            span = range(int(first), int(last or first) + 1)
            found.update(f"T{number:0{len(first)}d}" for number in (span if len(span) <= 200 else [int(first)]))
    return found


def instant(at: str) -> float:
    """A log line's `t` as seconds, to set beside a commit's; 0 where it has none."""
    try:
        return datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()
    except ValueError:
        return 0.0


def stage_now(root: Path, feature: str, slice_id: str) -> tuple[str, str]:
    """The word for the stage the slice's berth has open now and when it opened, from its `benchmark.json`,
    or `("", "")`.

    The rungs above are read off what a stage leaves behind, so they move when a stage *ends*: hr-test-2's L18
    ticked its eighteenth task and then said `Implementing · 18/18` for twenty-seven minutes through its demo
    and review, because `review.md` is committed when a review closes. `benchmark.py start` writes an entry
    the moment a stage opens, in the berth's own tree, so an open newest entry there is what the slice is on.
    Between stages nothing is open, and the evidence says it better: a closed `implement` after a review is
    the review's fixes, and `Implementing` would send the chip back down the ladder.
    The berth is where the captain moors it (`moorings.py`), beside the checkout; a slice worked in the
    checkout itself has its record there.
    """
    record = Path(f"specs/{feature}/slices/{slice_id}/benchmark.json")
    for place in (root.parent / f"{root.name}-{slice_id}", root):
        try:
            stages = json.loads((place / record).read_text(encoding="utf-8")).get("stages") or []
        except (OSError, ValueError, AttributeError):
            continue
        newest = (stages[-1] or {}) if stages else {}
        named = str(newest.get("stage", ""))
        if named:
            return ("", "") if newest.get("ended") else (STAGES.get(named.split("-")[0], named),
                                                         str(newest.get("started", "")))
    return "", ""


def merge_word(mine: list[Entry], harbour: Sequence[Entry], committed: float) -> tuple[str, str]:
    """What became of the slice's newest merge request: the chip's word, and why where it was refused.

    `Merging` was any request ever made and not yet landed, which is five different things to a person
    watching: asked and unanswered, granted and landing, refused, held behind a red trunk, and refused hours
    ago with the slice long back at work. The harbour answers each request by its id, so the answer is read.
    No word, with the reason, is the last of those: a commit since the refusal is the slice at work again,
    and its chip is whatever that work is.
    """
    asks = [e for e in mine if e.kind == "request" and e.fields.get("what") == "merge"]
    if not asks:
        return "", ""
    if any(e.kind == "merged" for e in mine):
        return "Merged", ""
    answers = [e for e in harbour if e.kind in ("granted", "refused") and e.t >= asks[-1].t
               and e.fields.get("request") == asks[-1].fields.get("id")]
    if not answers:
        return "Merge requested", ""
    if answers[-1].kind == "granted":
        return "Merging", ""
    why = str(answers[-1].fields.get("why", ""))
    if committed > instant(answers[-1].t):
        return "", why
    trunk = [e.kind for e in harbour if e.kind in ("trunk-red", "trunk-green")]
    return ("Held · trunk red" if why.startswith("trunk is red") and trunk[-1:] == ["trunk-red"]
            else "Merge refused"), why


def at_work(root: Path, feature: str, slice_id: str, entries: list[Entry], reached: tuple[int, str],
            tasks: str) -> str:
    """The word for a slice that is not at the harbour: the stage it has open, or what its log last says.

    A stage left open is believed until the log moves past it: TB1's `implement-shipwright` stood open
    through its demo and a gate park. An `implement` opened after the review is the review's fixes. With
    nothing open, a gate refusal newer than anything the slice has reached is what it is mending, and a
    task list ticked to the end is no longer being implemented.
    """
    mine = [e for e in entries if str(e.fields.get("slice", "")) == slice_id]
    moved = max([e.t for e in mine if e.kind in MOVED], default="")
    gate = max([e.t for e in entries if e.kind == "parked" and e.fields.get("cause") == "gate"
                and (e.fields.get("slice") == slice_id or str(e.fields.get("why", "")).startswith(f"{slice_id}:"))],
               default="")
    number, stage = reached
    now, opened = stage_now(root, feature, slice_id)
    if now and opened >= max(moved, gate):
        return "Review fixes" if now == "Implementing" and number >= LOGGED["stowed"][0] else now
    if gate and gate >= moved:
        return "Fixing gate refusal"
    done, _, of = tasks.partition("/")
    return "Tasks done" if stage == "Implementing" and done and done == of else stage


def rung(root: Path, feature: str, slice_id: str, entries: list[Entry],
         harbour: Sequence[Entry] = ()) -> dict[str, str]:
    """The slice's stage, the chip that names it, and the facts the opened card shows.

    `stage` is the word, `chip` the word with what counts it — `Implementing · 14/22` — and `last` the
    newest line the slice's log has that is not a heartbeat, so an opened card says what it last did.
    `rank` stays the furthest rung the evidence shows, which is what the captain ranks by; `refused` is why
    the harbour turned its last merge request away, where it did.
    """
    facts = branch_facts(root, feature, slice_id)
    mine = [e for e in entries if str(e.fields.get("slice", "")) == slice_id]
    asked = [LOGGED["request"]] if any(e.kind == "request" and e.fields.get("what") == "merge" for e in mine) else []
    climbed = [LOGGED[e.kind] for e in mine if e.kind in LOGGED and e.kind != "request"]
    climbed += [FILED[f"{name}.md"] for name in facts.get("files", "").split(",") if name]
    tasks = facts.get("tasks", "")
    stage, refused = merge_word(mine, harbour, float(facts.get("at") or 0))
    stage = stage or at_work(root, feature, slice_id, entries, max(climbed, default=(0, "Starting")), tasks)
    chip = f"{stage} · {tasks}" if stage in COUNTED and tasks else stage
    told = [e for e in mine if e.kind != "heartbeat"]
    last = f"{told[-1].t} {told[-1].kind}" if told else ""
    return {"stage": stage, "rank": str(max(climbed + asked, default=(0, ""))[0]), "chip": chip, "tasks": tasks,
            "artifacts": facts.get("files", ""), "commit": facts.get("commit", ""), "last": last,
            "refused": refused}
