"""`harbour.json`: the numbers a run is held to, in the project rather than in anybody's head.

The experiment spent 104 hours and, at its worst, hundreds of millions of input tokens on one slice, with
nothing anywhere saying what too much was. A stage that has no budget cannot be over one, so the only
signals were a person noticing and the bill arriving. Both are late.

So every bounded thing a run does gets a number here: how long a stage may take and what it may spend, how
severe a finding has to be before it stops a merge, how many decisions may go unreviewed, and how long any
wait may last. They are in the project, versioned with it and visible in a diff, because a number in a
prompt is a number nobody can find afterwards and a number in somebody's head is not a number.

**What happens at a budget is stowing, not stopping.** A stage that runs out writes what is left into the
fairway's careen and goes on, and the slice merges. The exceptions are the two that would be dishonest: work
above the severity bar parks for a person instead, and nothing CRITICAL is ever stowed. That ordering is the
whole point — the first attempt's alternative was carrying gaps into the next slice, where a slice that
inherits one pays for it without having chosen to.

**These are defaults, and defaults are the thing most likely to be wrong.** They are written where a person
can change them for exactly that reason. Slice 7.3 adds the telegraph on top: named positions that set
several of these at once, so a person rings `half-ahead` rather than editing six numbers. The numbers stay
individually settable underneath it, which is the point of them being a file.
"""
from __future__ import annotations

import json

from ..telegraph import settings

CONFIG = "harbour.json"
#: Where a fresh harbour's telegraph starts. Not `full-ahead`: a first run is the one nobody has watched yet,
#: and the position that spends most is a strange place to begin.
START = "half-ahead"
#: Wall-clock minutes and thousands of input tokens one stage may take. Per stage, because a converge and
#: an implement are not the same kind of work and one number for both would be wrong for each.
STAGE_BUDGETS: dict[str, dict[str, int]] = {
    "default": {"minutes": 30, "tokens": 400},
    "example-map": {"minutes": 20, "tokens": 200},
    "gaps-lookout": {"minutes": 20, "tokens": 200},
    "plan": {"minutes": 30, "tokens": 300},
    "tasks-quartermaster": {"minutes": 15, "tokens": 150},
    "implement-shipwright": {"minutes": 90, "tokens": 1200},
    "converge-navigator": {"minutes": 30, "tokens": 400},
    "review-mate": {"minutes": 25, "tokens": 300},
    "adversary-privateer": {"minutes": 40, "tokens": 500},
    "mutation-shipworm": {"minutes": 60, "tokens": 200},
}
#: How many decisions may stand unread by a person before a fairway parks. The experiment reached 125
#: decisions with 105 of them never reviewed, which is not a record of judgement, it is a backlog of it.
DECISION_CEILING = 10
#: Minutes a wait may go with nothing written to the harbour log — waiting for a mark, for a person, for a
#: lock — before it becomes a `parked` line with a reason. In the first attempt a wait with no bound was
#: indistinguishable from a run that had stopped. What it is a bound on is *silence* and not elapsed time:
#: a harbourmaster answering a merge is on the far side of a rebase and the project's whole gate, which is
#: a different length on every machine, so a clock started at the request measures the gate rather than the
#: harbour's health. Any new line restarts it; a harbour that has stopped writing is what it still catches.
WAIT_BOUND = 60

COMMENT = (
    "What this run is held to. `stages` is minutes and thousands of input tokens per stage, `default` for "
    "any not named. `bar` is the severity at or above which an adversary finding must close before the "
    "merge; below it a finding is stowed into the fairway's careen and the slice merges, and nothing "
    "CRITICAL is ever stowed. `decision_ceiling` is how many decisions may stand unread before a fairway "
    "parks. `wait_bound` is how long a wait may go with nothing written to the harbour log before it is a "
    "parked line with a reason — a bound on silence, so a harbourmaster that is writing is waited for. "
    "`attempts` is how many times a captain may re-dispatch `/sail` for one slice — a demo sent back is a "
    "retry, not a park — before the fairway parks naming what is still missing. `ci` is how the "
    "harbourmaster asks the forge whether trunk is green before it grants any merge: absent means `gh` "
    "where it is installed, a list of words is a command for another forge with `{trunk}` and `{limit}` "
    "filled in, and `off` says not to ask — which reads as unverified and never as green. Change "
    "them here, or ring the telegraph — `slipwai telegraph slow-ahead` sets the group, `slipwai telegraph --set "
    "boilers=2` sets one, and `slipwai telegraph` shows where it is."
)


def harbour_config() -> str:
    """`harbour.json` as generated: the defaults, and the comment that says what each one holds."""
    # The telegraph's own numbers, from the position a fresh harbour starts at, so one file holds every
    # number a run is held to and `slipwai telegraph` has something to ring from the first generation.
    document = {
        "_comment": COMMENT,
        "v": 1,
        "position": START,
        "stages": STAGE_BUDGETS,
        # Last, so the file matches the position it declares exactly. `bar`, `decision_ceiling` and
        # `wait_bound` are the telegraph's rows now, and `START`'s are the three constants above — written
        # once here rather than twice, because two sources for one number is how a board starts lying.
        **settings(START),
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def budget_section() -> str:
    """The `/sail` section that says what a stage does when it reaches its budget."""
    return f"""### When a stage reaches its budget

Every stage has one, in `{CONFIG}`: wall-clock minutes and thousands of input tokens. A stage that reaches
either does **not** keep going, and does not quietly hand its leftovers to the next slice. It stows.

1. **Write what is left into the fairway's careen** — `fairways/<name>/careen.md`, one row per item, each
   saying what is wrong and what closing it would take, with `budget` as the row's *From*.
2. **Append a `stowed` line** to the deck log naming the stage, the slice and how many items.
3. **Go on.** The slice continues to its next rung and may merge. Stowed work is the careen's, and the
   careen is a slice that fairway runs before its flag is hoisted.

Two exceptions, and they are the ones where stowing would be dishonest:

- **Anything at or above the severity bar parks for a person** instead of being stowed. The bar is
  `{CONFIG}`'s `bar`, and the point of a bar is that what is above it does not get deferred by a clock.
- **Nothing CRITICAL is ever stowed**, whatever the budget said. Data of one actor reaching another, or an
  actor gaining a role, is the next slice.

**Say the number, not just that it was reached.** The `stowed` line and the careen rows record what the
budget was and what was spent, because a budget that is hit every time is a budget that is wrong, and
nobody can see that from the word *stowed* alone.

In the experiment no stage had a budget, so no stage was ever over one: 104 hours and hundreds of millions
of input tokens on a single slice, with the only signals a person noticing and the bill arriving.
"""
