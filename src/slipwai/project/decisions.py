"""`.specify/memory/product-owner.md`: the owner brief `/cruise`'s skipper decides from, and the record it keeps.

A run with nobody at the wheel still has an owner; what changes is where the owner's judgement lives. The
constitution says what must never be violated and the specification says what to build, and between them sits
everything a person answers from taste and priority — which journey to prefer, which trade to make, what is
not this product's to do. This page is where that goes, so a person steers a run by editing a file rather than
by stopping it. It ships as placeholders in the constitution template's style, human-owned, and optional: an
empty brief means the skipper decides from the spec, the constitution and the standing decisions alone, and
says so in each entry. The entries themselves (`decisions.md`, `demo-log.md`) take their shape from
`cruise.py`, and `scripts/check-decisions.py` holds every entry to it.
"""
from __future__ import annotations

from .cruise import CONFIG, DECISION_ENTRY, DEMO_ENTRY, STOP_FILE
from .cruise_agents import DECISIONS, DEMO_LOG, HAND, OWNER_BRIEF, SKIPPER

PAGE = OWNER_BRIEF


def owner_brief() -> str:
    """The brief as generated: every section a placeholder, and the reason each exists."""
    return f"""# [PROJECT_NAME] — the product owner's brief

`/cruise` runs `/drive` with nobody at the wheel, and this page is the owner it decides for. The `{SKIPPER}`
delegate reads it before every product decision, after the specification and the constitution and before the
standing entries in `{DECISIONS}`. Edit it at any time: the next decision reads the new text, and no run has
to stop for that. Leave a section as its placeholder and the skipper decides that ground from the
specification, the constitution and the decisions already taken — and says so in the entry.

This file is human-owned. `/cruise` reads it and never writes it; `slipwai migrate` never rewrites it.

## Who the actor is

[ONE_PARAGRAPH: who uses this product, in their own words for what they do — "a campaign organiser
recording a night's battles", not "the user". Where there are several, name each and say which one a slice
serves by default when the specification does not.]

## What the product is for

[ONE_PARAGRAPH: the outcome the actor gets that they could not get before, and the one thing that would
make this product pointless if it were wrong. The specification says what to build; this says why, which is
what a decision between two readings of it turns on.]

## Priorities and tie-breakers

[Ordered, most important first. These decide between options the specification leaves open:

1. [e.g. the simpler journey over the richer one]
2. [e.g. an actor sees their own data before anyone sees a report over everyone's]
3. [e.g. correctness of money paths over throughput — and `cycle=example` for those]]

## Taste

[What "good" looks like here that no criterion states: tone of the copy, density of a screen, what an
error message says, whether a list defaults to newest first. A decision that cannot cite this section or the
specification is a guess, and the entry says which.]

## Out of scope

[What this product deliberately does not do, so the completion audit does not open a slice for it: an
integration deferred, an actor not served yet, a report nobody asked for. Each line is a decision already
taken; the skipper cites it rather than re-taking it.]

## Always ask a person

[Questions that park a run however clearly the specification seems to answer them — a price, a legal
wording, anything that reaches a real customer, a release with no flag holding it back. The skipper records
these as `unavailable` and the run parks with the exact question; `{STOP_FILE}` and `{CONFIG}` say how a run
stops and what it may decide.]

## What the record looks like

Every decision a run takes is appended to `{DECISIONS}`, one entry in this shape, and the artifact the stage
owns is written in the same step:

```markdown
{DECISION_ENTRY}
```

Every demo the `{HAND}` delegate runs is appended to `{DEMO_LOG}`, one entry in this shape, with its
evidence beside it:

```markdown
{DEMO_ENTRY}
```

`make check-decisions` holds both files to those shapes, and refuses an entry whose `Written to` or
`Evidence` path is not in the tree. Overrule a decision by changing its `Status` and writing the answer you
want into the artifact it names; the next iteration re-enters the ladder from that artifact.
"""


def decision_files() -> dict[str, str]:
    """The brief, keyed by its path in the project."""
    return {PAGE: owner_brief()}
