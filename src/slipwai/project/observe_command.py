"""One adopted capability read into the model, with the source behind every proposed business fact.

The command belongs beside `/characterise`: its examples come from that seam, and its nine steps read
what exists rather than designing what ought to exist. It is shipped only by the adopted event profile.
"""
from __future__ import annotations

from ..layout import Layout
from ..services import App, wrapped_of


def observe_command(apps: list[App], layout: Layout) -> str:
    applications = ", ".join(f"`{app.name}` (`{app.path}`)" for app in wrapped_of(apps)) or "none confirmed yet"
    pinned = layout.under("survey/pinned.md")
    structure = layout.under("survey/structure.md")
    retirement = layout.under("retirement.md")
    return f"""---
description: Observe one existing capability from source and pinned examples into the global event model
argument-hint: <one capability, owning wrapped service, and its handler or seam>
---

# Observe

Read `skills/event-modeling/SKILL.md`, its `references/nine-steps.md` and
`skills/global-event-model/SKILL.md`. Run all nine steps below, separately, against **one capability**.
This is a record of what the code does, not a redesign. The big picture in `survey/big-picture.md` was
read once for the whole system; do not repeat it or put its eventless process proposals into the model.
`{structure}`'s hotspots suggest the first capability where no requirement has named one.

## Before writing anything

An empty `$ARGUMENTS`, "everything", "the whole system", "all services" or "the service" is refused.
Name one behaviour, its actor and its seam, then run `/observe <capability> <service> <handler>` again.
Read `project.json` now: the generated list ({applications}) is a pointer, not authority. Choose the
owning `deployables` entry with `kind: service` and `generated: false`, whose path contains the handler.
A missing application, an unresolved `candidates` entry, or `provenance.kind` / `provenance.language`
that is not `confirmed` or `overridden` is a stop: run `/ground`, then `/survey` and rerun `/observe`.
For an outstanding candidate, `slipwai adopt --confirm <name> --kind service` records the application.
For an already wrapped service, `/ground` records those facts with the person's confirmed provenance;
`--confirm` applies to outstanding candidates, not to a deployable already in the record.
A generated service uses the ordinary modelling workflow. Never default to the first deployable.

Read the service's `eventSourced`, `writeModel` and `provenance.writeModel`. Use **status columns and
their writes** for `state` (including an unanswered rung). Use the **existing events module** only
when `writeModel: events` has `confirmed` provenance and `eventSourced: true`. An apparent log with no
confirmation is a question for `/ground`. For an outstanding candidate,
`slipwai adopt --confirm <name> --write-model events` records the answer; for an already wrapped service,
`/ground` records `writeModel` with `confirmed` provenance and `/survey` recomputes `eventSourced`.
Do not switch rungs by detection or edit the manifest to make the observation fit.
Record which source was used, its files and the manifest decision in
`specs/<feature>/observations/<capability>.md`.

First read `{pinned}`. If this capability has no passing characterisation tests, run
`/characterise <behaviour at its seam>` first, and run the recorded command. Read the actual tests and
copy their actual inputs, initial state and outputs into each slice's
`specs/<feature>/slices/<id>/examples.md`, citing the test file, test name and source lines. These are the
Given/When/Then, including undesirable behaviour; never replace them with desired examples.

## Step 1: Identify the user goal

Read the entry point, its caller and the pinned scenarios. Name who acts, the one goal and the observed
success/failure boundary. Confirm unclear business words through `/gaps`, one question at a time. Each
question records its **Intention** and **Assumption proceeded on**. Do not quietly redesign an ugly rule.

## Step 2: Brainstorm the facts from source

For a state-stored service, trace the handler to every write and enumerate the status enum and branches.
Write the **extraction table**, one block per table this capability writes, one row per actual transition:

### Table: orders — status column

| Column | Transition | Proposed business fact | Write read off | Pinned example |
|---|---|---|---|---|
| status | draft → confirmed | OrderConfirmed | <repository-relative file>:<line of write> | <test file>:<line>, <test name> |

The example row is a format, never evidence to copy. A write without a status column names its actual
business transition instead. Record unsupported enum transitions as unobserved gaps, not extra slices.
For confirmed `events`, use the events module and append/raise handler instead of inventing a status
table: record each existing event type, payload, producer file:line and pinned example in an equivalent
extraction block. Existing tables are current state; neither their rows nor timestamps prove past events.
An observed `evt` on `state` names the fact represented by the write; it does not claim the application
already emitted or persisted that event. No backfill, genesis event, outbox or schema change is done here.
Name facts in past-tense business language. `OrdersUpdated` is a row operation, not `OrderConfirmed`.
Apply `references/naming.md`; keep uncertainty beside the source line and put it through `/gaps`.

## Step 3: Order the timeline

Follow actual branches and pinned scenarios, including rejection, retry and concurrency paths. A status
enum suggests a transition list, not chronology: only a handler or test proves an edge. Reuse facts already
on the global timeline; do not invent duplicate producers to order two capabilities.

## Step 4: Account for the screens as white boxes

Read the actual screen or HTTP/form surface and sketch plain wireframes: what the actor sees, provides
and can do. Put each existing surface in a `ui` frame, with its source name and observed states in
`docs/event-model/mockups/`; link them via `mockups: [{{state: ..., at: ...}}]`. White boxes describe
the existing screen, with no new styling or invented interface. A job has a `pcr` trigger, not a fake UI.

## Step 5: Identify commands

The handler's trigger and input become `ui → cmd → evt` (`state-change`), or `pcr → cmd → evt` where
a process triggers it. Trace each command and fact to the handler and extraction row; type their payloads
from the actual contract. Put the repository-relative handler path in `code:`, not a file:line string
(lines belong in the extraction table). On `state`, `stream` describes the row identity and version
the write actually uses; no invented tag guard, fold or history. On confirmed `events`, read the real
consistency boundary and event identities from its module. Keep the service and bounded context explicit.

## Step 6: Design the observed read models and name the first move

Read queries, reports and exports as `state-view`: `rmo → ui?`, with `reads` naming the observed facts
from earlier producer slices on this same service. Record the actual query in `code:` and the pinned
results in `gwt:`. A current-state query reads tables; its `reads` joins the business facts on the timeline
and does not claim replay. State its real materialisation. Confirmed `events` may read a real projection.

Name the **first move** in the observation record: implement a `state-view` over the wrapped service's
own data, with no write path, genesis or routing seam. This is available on either rung. Where that query
already exists, observe it now; where it does not, record the proposed move in the working record and
model its typed slice only when its inputs are evidenced. Do not mark nonexistent code `observed`.
The move from `observed` to `implemented` is work, not a status edit. Under a confirmed strangler strategy,
its implementation is the first row in `{retirement}`: name the view, old data source, new reader and
remaining dependency honestly; the original write path has not been retired.

## Step 7: Find automations

Trace jobs and consumers within this capability: `rmo → pcr → cmd → evt`, `reads` at the earlier trigger
fact, with the real condition and termination rule. A job alone is not an automation; find its consulted
state and command. Unconditional co-produced facts belong on one command slice, not a fake automation.

## Step 8: Map translations

Trace outbound calls and inbound hooks as `evt → pcr → cmd → evt` (`translation`). Name the actual
external fact with `external: true`, the conversion and the local command/fact. Record source lines and
pinned inputs; a URL literal alone is not proof of behaviour. Cross-cutting transport and persistence
are infrastructure, not extra business slices. Never add a publisher merely to draw an observed join.

## Step 9: Record the vertical slices and check them

Write only evidenced slices to `docs/event-model/model.yaml`, preserving unrelated slices. Each has
`id`, `capability`, `service`, `context`, `pattern`, `status: observed`, the required `actor`, typed
`frames`, `code: [<handler path>]` and `gwt: specs/<feature>/slices/<id>/examples.md`. Read the schema in
`docs/event-model/README.md`: a state-view/automation needs `reads` and `materialisation`; its producing
slice precedes it. Do not insert eventless `proposed` placeholders from the big picture. A slice whose
evidence is missing remains a question in the observation record. Record the nine-step results and the
first move there; each `/gaps` item carries intention and the assumption used in the meantime.

Run `{layout.make} check-model`, `{layout.make} chart` and `{layout.make} check-chart`. Read the rendered
chart: observed slices are recorded evidence, never `/sail`'s ready work. If an event name fails the CRUD
lint, return to its extraction row and name the fact; never disable the check. Review the diff with the
source and pinned examples side by side. Observation changes the model and its evidence, not production
code. The new requirement now models its changed behaviour against this observed baseline.
"""


def observation_stage(layout: Layout) -> str:
    """The existing Event-model stage discovers missing baseline evidence before designing a change."""
    return f""" In this adopted repository, first name the capability this requirement touches and its
   wrapped service. Read what is already recorded for that capability in `docs/event-model/model.yaml`.
   Where no `observed` slice (or its later `implemented` replacement) records that behaviour, run
   `/characterise <behaviour at its seam>` and `/observe <capability> <service> <handler>` **before**
   modelling the new requirement. `{layout.under('survey/structure.md')}` suggests a first seam.
   A global model containing some other capability does not satisfy this stage. `/observe` records the
   actual source, its nine steps and pinned Given/When/Then; it refuses whole-system discovery, missing
   or unconfirmed applications, and events from a log nobody confirmed. A requirement wholly in code
   this project generated says so and continues with the ordinary modelling workflow."""
