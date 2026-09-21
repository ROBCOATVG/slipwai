"""`/where-are-we`: the demo stop's progress board, on demand.

The board went to the top of every demo stop because a product owner had to ask how far along the work
was. The question does not wait for a demo, though: it arrives mid-slice, at the start of a session, from
somebody who was not in the room for the last stop. This is the same board — the same parts, in the same
order, read off the same artifacts — with one line changed, because between demos there is nothing new to
show and something half-built to report: 🆕 *New in this demo* becomes 🔧 *In progress*, the slice being
worked and the stage of the ladder it has reached. It runs no stage, edits nothing, and never invents a slice
to have something to say.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..targets import managed
from .demo_stop import board_sources


def where_are_we_command(event: bool, target: str = "none") -> str:
    """`commands/where-are-we.md`, for the profile's artifacts and the target's release constraints."""
    feature = (
        "Given a feature, read `specs/<feature>/`; given nothing, the one the slices in "
        "`docs/event-model/model.yaml` point their `gwt` at, or the only one under `specs/`."
        if event
        else "Given a feature, read `specs/<feature>/`; given nothing, the active one recorded in "
        "`.specify/feature.json`, or the only one under `specs/`."
    )
    constraints = (
        "the release constraints from `infra/service/flags.auto.tfvars`: every flag still `off` holds a slice "
        "back from the actor and is on the board as such"
        if managed(CATALOG, target)
        else "the release constraints, if the project records any, from the slice's `plan.md`"
    )
    return f"""---
description: Show where the product stands — the progress board, on demand, read off disk and changing nothing
argument-hint: [feature]
---

# Where are we

Answer the question the product owner would otherwise have to ask: what works, what is being built, what is
left, and what comes next. Say it in the actor's vocabulary, from artifacts on disk, and change nothing. For
the one-step answer — which slice, which stage, which command — `/whats-next` reads the same artifacts and
says only that.
{feature}

## The board

The board `commands/drive.md` opens every demo stop with, in the same order, so the two can never disagree:

- ✅ **Works now** — every accepted slice, one line each, as the thing the actor can do
- 🔧 **In progress** — the slice being worked, as the thing it will let the actor do, and the stage of
  `/drive`'s ladder it has reached, with the artifact that says so: an example map written, a plan without
  tasks, tasks half checked, a converged verdict waiting for its demo. Nothing in progress is one line
  saying so
- ⬜ **Still to come** — the remaining slices of the split, in order and by name, headed by one line of
  counts: `N of M slices accepted`
- ⚠️ **Not working yet** — every deliberate stub and every release constraint still in force, named as
  such, so a hole reads as "not yet" and not as a fault the actor has to find
- 🔀 **Ready (parallel)** — every slice that can start now: not done, every `depends_on` done, and not
  pre-empted by an open `CRITICAL` — in two groups, *claimed* (a `slice/<id>` branch on the forge, by whom
  and how long ago) and *unclaimed*, so another session knows which sibling is free
- ➡️ **Next (this session)** — the slices this `/drive` will take: every unclaimed ready slice whose
  contract is settled, concurrently; or the earliest ready slice in split order where the harness cannot
  delegate, unless the user picks another ready one
- ⛔ **Blocked** — remaining slices waiting on unmet `depends_on`, or an open `CRITICAL` ahead of them

The second line is the only one that differs from the demo stop's 🆕 *New in this demo*: a demo has something
new to show, and a question asked between demos has something half-built to report.

## Where it is read from

The board is derived from artifacts, not memory, the way `/drive` derives its entry stage:
{board_sources(event)}. The slice in progress and its stage come from the ladder — the first
stage whose artifact is missing, empty, or still a placeholder — and its stubs from its `plan.md` and
`tasks.md`; {constraints}.

Before the split exists there is no board to draw. Say which stage of the ladder the work is at — principles,
specification, {"event model, " if event else ""}split — and what the next stage produces, and stop there.

## What it never does

- **Runs nothing.** No stage is entered, no task appended, no artifact edited: this is read-only, and safe to
  ask at any point on the ladder, including mid-implementation and in a session that has done nothing yet.
- **Counts slices, never tasks.** The task count is not on the board. Tasks stay in `tasks.md` for whoever
  is doing the work; a slice is a thing the actor can use, and fifty-eight tasks over two slices reads as
  fifty-eight features to somebody who did not write them.
- **Invents nothing.** A slice the split does not name is a question for `/story-splitting`, not a line on
  the board. A count an artifact cannot supply is written `unknown`, with the artifact that would have
  supplied it, never estimated.
- **Does not demo.** It hands over no command to paste and asks no question: that is the demo stop's job,
  and it belongs to `/drive`. Where the board shows a converged slice waiting for its demo, say so, and say
  that `/drive` is what runs it.
"""
