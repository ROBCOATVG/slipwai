"""The instant a migrated project began to ask every new decision entry for its plain sentence.

`check-decisions` holds an entry written since the rule to an `**In short:**` line — one sentence a product
owner reads without the specification open. A project migrating across the rule already has dozens of
entries without one, written when nobody asked, and its gate must not fail on them the moment it migrates.
So `migrate` writes, once, the instant it brought the rule in, and the gate holds only entries whose `When` is
at or after it. Written only where the project has a decision already: a project with none has nothing to
forgive, and one made under the rule never gets the file, which is how the gate knows to hold every entry.

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


def has_decisions(root: Path) -> bool:
    found = [*root.glob("specs/*/decisions.md"), *root.glob("fairways/**/decisions.md")]
    return any(_ENTRY.search(path.read_text(encoding="utf-8", errors="replace")) for path in found)


def date_sentence_rule(root: Path, now: datetime | None = None) -> bool:
    """Write and stage the instant, where the project has decisions and no instant yet. True if written."""
    path = root / SENTENCE_FROM
    if path.exists() or not has_decisions(root):
        return False
    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"from": stamp, "why": "Decision entries written before this instant predate "
                                "the plain-sentence rule; scripts/check-decisions.py asks only later ones for "
                                "**In short:**. Written once by slipwai migrate; leave it as it is."},
                               indent=2) + "\n", encoding="utf-8")
    git(root, "add", "--", SENTENCE_FROM, check=False)
    return True
