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

**Cheap enough for a poll that runs every few seconds.** One `git rev-parse` per slice in flight, and the
branch is only read again when its head has moved.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .logs import Entry

#: Rung, the word on the chip, and what moves a slice onto it: a line in its log, or a file on its branch.
#: The numbers are the captain's `LOG_RUNGS` and `FILE_RUNGS`, so the board and the captain rank alike.
LOGGED = {"request": (8, "Merging"), "demo": (7, "Demo"), "stowed": (5, "Review")}
FILED = {"review.md": (6, "Review"), "tasks.md": (4, "Implementing"), "plan.md": (3, "Planning"),
         "research.md": (3, "Planning"), "examples.md": (2, "Example mapping")}
#: A task line in `tasks.md`: `- [ ] T001 …` or `- [x] T001 …`.
TASK = re.compile(r"^\s*[-*] \[( |x|X)\] ", re.M)
#: The branch read last time, by slice, with its head: what the branch said is only read again when it moved.
SEEN: dict[tuple[str, str], tuple[str, dict[str, str]]] = {}


def git(root: Path, *argv: str) -> str:
    done = subprocess.run(["git", "-C", str(root), *argv], capture_output=True, text=True, check=False)
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
             "commit": git(root, "log", "-1", "--format=%cI %s", ref).strip()}
    if "tasks.md" in files:
        ticks = TASK.findall(git(root, "show", f"{ref}:{folder}tasks.md"))
        facts["tasks"] = f"{sum(1 for one in ticks if one.strip())}/{len(ticks)}" if ticks else ""
    SEEN[key] = (head, facts)
    return facts


def rung(root: Path, feature: str, slice_id: str, entries: list[Entry]) -> dict[str, str]:
    """The slice's stage, the chip that names it, and the facts the opened card shows.

    `stage` is the word, `chip` the word with what counts it — `Implementing · 14/22` — and `last` the
    newest line the slice's log has that is not a heartbeat, so an opened card says what it last did.
    """
    facts = branch_facts(root, feature, slice_id)
    mine = [e for e in entries if str(e.fields.get("slice", "")) == slice_id]
    climbed = [LOGGED[e.kind] for e in mine
               if e.kind in LOGGED and (e.kind != "request" or e.fields.get("what") == "merge")]
    climbed += [FILED[f"{name}.md"] for name in facts.get("files", "").split(",") if name]
    number, stage = max(climbed, default=(0, "Starting"))
    if stage == "Merging" and any(e.kind == "merged" for e in mine):
        stage = "Merged"
    tasks = facts.get("tasks", "")
    chip = f"{stage} · {tasks}" if stage == "Implementing" and tasks else stage
    told = [e for e in mine if e.kind != "heartbeat"]
    last = f"{told[-1].t} {told[-1].kind}" if told else ""
    return {"stage": stage, "rank": str(number), "chip": chip, "tasks": tasks, "artifacts": facts.get("files", ""),
            "commit": facts.get("commit", ""), "last": last}
