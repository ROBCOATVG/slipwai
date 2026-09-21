"""`/whats-next`: the one thing to do next — which slice, which part of it, and the command — in a few lines.

`/where-are-we` answers the product owner's question with the whole board, and the board is the right answer
to "how far along are we". It is the wrong answer to the question that arrives at the start of a session or
after an interruption: *what do I do now*. That question wants one slice, one stage, one command and the reason
it is those, and nothing that would make the reader scan. This reads exactly what the board reads — the split,
the statuses, the claims, the slice's own artifacts — and says only the next step, derived the way `/drive`
derives its entry stage. It runs nothing, edits nothing, and never invents a slice to have an answer.
"""
from __future__ import annotations

from .demo_stop import board_sources


def whats_next_command(event: bool) -> str:
    """`commands/whats-next.md`, for the profile's artifacts."""
    feature = (
        "the one the slices in `docs/event-model/model.yaml` point their `gwt` at, or the only one under `specs/`"
        if event
        else "the active one recorded in `.specify/feature.json`, or the only one under `specs/`"
    )
    return f"""---
description: Say what is next — one slice, one stage, one command — read off disk and changing nothing
argument-hint: [feature]
---

# What's next

Answer *what do I do now* in at most six lines. `/where-are-we` draws the whole board; this names the next step
and stops. Given a feature, read `specs/<feature>/`; given nothing, {feature}.

## The answer

Four labelled lines, in this order, every one in the actor's vocabulary rather than a test name:

- **Next:** the slice — its id and the thing it lets the actor do — or, above the split, the stage of the
  ladder still owing an artifact
- **Stage:** the part of that slice to do now — the first stage of `/drive`'s ladder whose artifact is
  missing, empty or still a placeholder, with the artifact that says so; mid-implementation, the next unchecked
  task by id and rule; after a converged verdict, the demo
- **Because:** the one fact that selected it — the last slice accepted, this one the earliest ready and
  unclaimed; or the slice in progress on this branch; or the only slice left unblocked
- **Run:** the command to type — `/drive <id>`, or the upstream command the stage names
  (`/story-splitting`, `/speckit-specify`, {"`/example-map <id>`, " if event else ""}`/speckit-constitution`)

Where more than one slice is ready and unclaimed, headline the earliest in split order and add one line —
*and N more ready in parallel: …* — since `/drive` will take them together. Where nothing can start, the
first line is **Blocked:** with the `depends_on` or the open `CRITICAL` that holds it, and **Run:** is what
clears it. Where a slice is claimed by another session, say so and name the next unclaimed one instead.

## Where it is read from

The same artifacts the board is read from, so the two can never disagree:
{board_sources(event)}. The stage comes from the ladder — the first stage whose artifact is missing, empty, or
still a placeholder — and the next task from that slice's `tasks.md`. Check the branch first, the way `/drive`
does: a checkout behind trunk answers this question wrongly with confidence, so say when it could not be
verified as current.

## What it never does

- **Runs nothing** and edits nothing: read-only, safe to ask at any point on the ladder.
- **Never more than six lines.** A second slice, a count of tasks, a history of what was done — that is the
  board, and `/where-are-we` draws it.
- **Invents nothing.** No slice the split does not name, no stage the artifacts do not select. Where the
  artifacts cannot say, the line reads `unknown` with the artifact that would have said, and **Run:** is
  `/where-are-we`.
"""
