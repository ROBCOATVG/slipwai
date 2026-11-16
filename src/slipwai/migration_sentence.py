"""The instant a migrated project began to ask every new decision entry for its plain sentence.

`check-decisions` holds an entry written since the rule to an `**In short:**` line — one sentence a product
owner reads without the specification open. A project migrating across the rule already has dozens of
entries without one, written when nobody asked, and its gate must not fail on them the moment it migrates.
So `migrate` writes, once, the instant it brought the rule in, and the gate holds only entries whose `When` is
at or after it. Written only where the project has a decision already — in trunk or in any berth, since a
project whose decisions are all still on slice branches has them too: a project with none has nothing to
forgive, and one made under the rule never gets the file, which is how the gate knows to hold every entry.

**A slice already in flight is not caught by it.** A berth works on the command pages it began on, which never
asked for the sentence, until it takes trunk; an entry it writes after the instant is work begun before it.
So the file names the slices in flight at that moment — every `slice/<id>` branch with a checkout, or not yet
merged into trunk — and the gate does not ask their entries for one.

Never rewritten: a second migration finds the file and leaves it, so the instant is the crossing's and not
the latest upgrade's — moving it forward would forgive entries written under the rule without a sentence.
The file is staged where it is written, so the commit `migrate` makes next, or the one a person makes to
resolve a conflicted merge, carries it.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .project.cruise_record import SENTENCE_FROM
from .replay import git

_ENTRY = re.compile(r"^## D", re.MULTILINE)


def places(root: Path) -> list[Path]:
    """This checkout and every other worktree of the repository: the berths."""
    listed = git(root, "worktree", "list", "--porcelain", check=False).splitlines()
    return [root, *(Path(line[9:]) for line in listed if line.startswith("worktree ") and
                    Path(line[9:]).resolve() != root.resolve())]


def has_decisions(root: Path) -> bool:
    found = [path for place in places(root)
             for path in (*place.glob("specs/*/decisions.md"), *place.glob("fairways/**/decisions.md"))]
    return any(_ENTRY.search(path.read_text(encoding="utf-8", errors="replace")) for path in found)


def in_flight(root: Path) -> list[str]:
    """The slices begun and not finished: a `slice/<id>` branch checked out in a berth, or not merged yet."""
    listed = git(root, "worktree", "list", "--porcelain", check=False).splitlines()
    held = {line.rsplit("/", 1)[1] for line in listed if line.startswith("branch refs/heads/slice/")}
    open_ = git(root, "branch", "--list", "slice/*", "--no-merged", "HEAD", "--format=%(refname:short)",
                check=False).splitlines()
    return sorted(held | {name.split("/", 1)[1] for name in open_ if "/" in name})


def date_sentence_rule(root: Path, now: datetime | None = None) -> bool:
    """Write and stage the instant, where the project has decisions and no instant yet. True if written."""
    path = root / SENTENCE_FROM
    if path.exists() or not has_decisions(root):
        return False
    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"from": stamp, "in_flight": in_flight(root),
                                "why": "Decision entries written before this instant, or by a slice already in "
                                "flight then, predate the plain-sentence rule; scripts/check-decisions.py asks "
                                "only the rest for **In short:**. Written once by slipwai migrate; leave it as "
                                "it is."}, indent=2) + "\n", encoding="utf-8")
    git(root, "add", "--", SENTENCE_FROM, check=False)
    return True
