# Implementation Plan: [FEATURE] — Slice [SLICE_ID]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

## Scope Of This Plan

This plan covers **one slice**. State it as a single capability with a single observable outcome. If the
slice name contains "and", a comma between verbs, or "plus", split it before planning (Principle V).

| Slice | Capability | Requirements | Release constraint |
|---|---|---|---|
| [ID] | [one capability, observable] | [FR refs] | [shippable / internal / pilot-only, and why] |

**Slice graph** (must match `## Slice graph` in the split, and `depends_on` on this slice in
`docs/event-model/model.yaml` when the event profile carries one):

| Slice | depends_on | parallel_ok_with | Notes |
|---|---|---|---|
| [ID] | [genuine build deps, or —] | [siblings that share only a schema / synthetic seed] | [why a listed dep is genuine; synthetic-event seeding is not a dependency] |

**Explicitly deferred** (later slices, not oversights): [list]

## Global Event Model

*GATE: this slice must exist in `docs/event-model/model.yaml` before Phase 0. Planning a slice that is not
on the timeline is planning against a model nobody can see.*

| | |
|---|---|
| **Slice id in the model** | [the `id`, which is the same id this plan and its tasks use] |
| **Pattern** | [state-change / state-view / automation / translation — and if the plan changes it, say what changed] |
| **Status transition** | `modelled` → `planned` as part of this plan |
| **Events it consumes** | [the `reads` entries, and which slice produces each — or none] |
| **Events it appends** | [names only; the schemas belong in `contracts/`] |
| **Events its Decider folds** | [the `folds` entries, all on this slice's own stream — or none. Not the same question as `reads`: that is a todo list over earlier slices, this is the history the command decides from] |
| **Who issues the command** | [an actor through a UI → `state-change`. The system, through a processor → `automation`. If a `pcr` box issues it, the pattern is `automation` and no `actor` belongs on it] |
| **The white boxes, and their states** | [every `ui` frame in this slice, and for each one: the states it can be in, whether `mockups` exists for each, and **where the screen will live in the tree**. A white box is a deliverable of *this* slice — see below] |

**The white box is in scope, and this is the row people get wrong.** A `ui` frame is the surface its actor
uses, not a caption on the route beneath it, and it ships in this slice rather than in a later UI slice —
including when the path under its submit button is not finished yet. Two obligations follow:

- **Where mocks exist**, `mockups` names one per state and the screen is built to them, state by state.
- **Where they do not**, the states are designed as the screen is built, and written back into `mockups`
  with the wireframe committed under `docs/event-model/mockups/`. Designing as you go is expected; leaving
  no record of what you chose is what makes a shipped screen's unhandled states invisible.

`check-model` refuses an `implemented` slice whose white box appears nowhere in the source
(`screen-is-built`) or that records none of the states it renders (`screen-states-recorded`). If this
project has no frontend or UI test harness yet, say so in **Complexity Tracking** and treat building them as
this slice's foundational cost — the starter ships a backend hexagon and no user interface.

**Read the diagram back**: [open `docs/event-model/model.html`, look at this slice and its neighbours, and
say in one sentence what the picture claims happens. A model can be green and still tell the wrong story —
five steps of one orchestration drawing as five unrelated interactions, the same UI box appearing three
times as though the user filled in three forms. Every gate reads the model as text. This is the only step
that looks at it, and it is the one that has caught what the gates could not.]

**What the model already says about these events**: [for each event this slice reads or appends that
*already exists*, what it currently means and who else reads it. A new slice cannot redefine an event
another slice folds — that is the failure the global model exists to make visible before it happens.]

Run `make model && make check-model` and commit the regenerated diagram with this plan.

## Summary

[The primary requirement, plus the technical approach in two or three sentences. Name the centre of
gravity — the one path where being wrong is expensive — and say how the design addresses it.]

## Technical Context

**Language/Version**: [pinned in the repository, identical across local, CI, and production]

**Primary Dependencies**: [each one earning its place]

**Storage**: [event store product, and where read models live — per slice, the `materialisation` its model.yaml entry declares: `live` (per-query fold, nothing stored, `liveBudget` naming its ceiling), `inline` (written in the append's transaction) or `async` (catch-up subscription plus checkpoint). `make check-model` requires the field before a slice with a read model can be planned, so this line and the model agree or the gate says so]

**Testing**: [runner, the levels of scope, how the boundary level is driven, and — where this slice adds
a provider-facing adapter — what its stub is pinned to]

**Target Platform**: [runtime target]

**Project Type**: [single deployable / API + client / …]

**Performance Goals**: [domain-specific, or state that none applies at this scale]

**Constraints**: [the invariants that cannot be traded, e.g. never issue the same unit twice; a payer
always ends with the thing or their money back]

**Scale/Scope**: [honest current scale, and note which guarantees must hold at any scale regardless]

**Unresolved unknowns**: [none, or list them — a plan with unresolved technical unknowns is not ready
for tasks. Non-technical gates such as regulatory permissions are tracked as gates, not unknowns.]

## Constitution Check

*GATE: must pass before Phase 0 research. Re-check after Phase 1 design, and again after any gap-closing
session that changes the design.*

| Principle | Verdict | How this slice complies |
|---|---|---|
| I. [Domain correctness] | | [the invariant, and what enforces it by construction rather than by care] |
| II. Idempotency & replay | | [where the idempotency key comes from, what enforces uniqueness, how duplicates are deduplicated, and that the check reads the event stream] |
| III. Event-sourced core + Decider | | [the Deciders, that `decide` is pure and returns events **or** a rejection, **stream identity and what it makes the consistency boundary** — the same value recorded as this slice's `stream` in `docs/event-model/model.yaml` — and which complexity rung any non-event-sourced context sits on] |
| IV. Hexagonal | | [what the domain imports (nothing outward), the ports, that each has a fake, and that the direction is machine-enforced] |
| V. ATDD from GWT | | [that every scenario enters through the **use case**, not a route; that the delivery adapter has its own parse/delegate/map test; **that each white box has a test per state at the UI level, because no level above it observes rendering**; that format validation is deliberately NOT a scenario; and any rule unreachable from the boundary that is therefore driven at the Decider level] |
| V. One increment at a time | | [the ordered list of scenarios this slice will drive, and confirmation they will be taken **one RED-GREEN-REFACTOR cycle at a time** with only the quick tests in the same file or area between cycles, each cycle committed locally, and the first implementation push only after demo acceptance once `make verify` is green. A plan that schedules the slice's tests as one activity and its implementation as another fails this row] |
| VI. Contract-bounded integrations | | [**"this slice adds no adapter to a third-party system"** if that is true, and move on. Otherwise: each driven adapter, where provider types stop, **the stub it is tested against and the recorded or published contract that stub is pinned to**, and the failure catalogue it maps — 4xx, credential rejection, rate limiting, 5xx, timeout, contract-violating response] |
| VII. Observability & auditability | | [correlation propagation, what the event log records, and **what alerts** — a read model is not detection] |
| VIII. Versioning | | [event schema versioning from day one, and whether the deploy strategy demands forward compatibility as well as tolerant reading] |
| IX. Security & privacy | | [what sensitive data never enters, and **the erasure mechanism, designed before the first personal-data event is persisted**] |

**Simplicity check**: [each additional service, cache, queue, framework, or abstraction layer, justified
against a named requirement — or state that none were added]

## Project Structure

### Documentation (this feature)

```text
docs/event-model/
└── model.yaml           # The global model — this slice's entry moves to `planned` here, not in specs/

specs/[###-feature]/
├── spec.md              # Feature specification
├── story-split.md        # Slice breakdown, and which slice this plan covers
├── plan.md              # This file
├── research.md          # Phase 0 — one numbered decision per unknown
├── data-model.md        # Phase 1 — streams, events, Deciders, read models, state machines
│                        #   every Decider's state names the stream it folds — see below
├── quickstart.md         # Phase 1 — how to run and validate, per slice
├── contracts/           # Phase 1 — external API, event schemas, port interfaces
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (the backend deployable)

Names below are directories, not files; spell the files in whatever the deployable's language calls them.
`apps/service/` stands for **the service that owns this slice** — the one its `model.yaml` entry names in
`service`. When `project.json` lists more than one service, that choice is made against what each says it
owns (`purpose` in `project.json`; *Bounded contexts* in `docs/architecture.md`), never the first service
by default, and it is written down under *Structure Decision* below. A slice no recorded purpose covers is
a product decision to ask before planning it. `[context]` is the bounded context the slice's `model.yaml`
entry names in `context` — one of the service's `contexts` in `project.json` — and the *Structure Decision*
names it too; when the service holds several, `make check-imports` refuses one context's code reaching
into another's except through its `public` module.

```text
apps/service/src/
├── domain/                 # pure: no I/O, no framework, no clock, no ids
│   ├── shared/             # value types, branded ids, Decision
│   └── [context]/          # the events and the Decider — one folder per bounded context
├── application/
│   ├── ports/              # driven port interfaces, application-owned
│   ├── usecases/           # driving ports and their implementations
│   └── projections/        # pure folds → read models
├── adapters/
│   ├── driving/            # HTTP, CLI, queue consumers — parse and delegate
│   └── driven/             # event store, providers, clock, ids — one folder each
├── composition/            # the only place adapters meet ports
└── migrations/

apps/web/                   # THE WHITE BOXES — one screen per `ui` frame, with its own tests beside them.
                            #   State where this lives and what tests it. A repository scaffolded without a
                            #   frontend ships none, so there is no default to inherit; a slice with a `ui`
                            #   frame and no answer here ships with no user interface and `screen-is-built`
                            #   fails it.

apps/service/tests/
├── acceptance/             # boundary GWT — THE GATE
├── domain/                 # Decider specs
├── projection/             # fold specs over synthetic fixtures
├── edge/                   # the driving adapter itself: parse, delegate, map outcomes to statuses
├── contract/               # one suite per port, run against the fake AND the real implementation
├── integration/            # one driven adapter vs a stub of its provider: wire, error mapping, retry, timeout
├── fakes/                  # implement OUR ports — first-class deliverables, not scaffolding
└── stubs/                  # impersonate THEIR providers, pinned to a recorded or published contract
```

**Structure Decision**: [the chosen layout, and why the hexagon is visible in the tree. Name what you
deliberately did NOT build and what would trigger building it. **Where the frontend lives and what tests
it** belongs here — an HTTP test through the route is not evidence about a screen, so a slice with a `ui`
frame needs a UI level named.]

## Complexity Tracking

> Fill for every deliberate deviation, including ones the constitution permits — it requires the
> reasoning be written down, not that there be none.

| Decision | Why needed | Simpler alternative rejected because |
|---|---|---|
| | | |

## What `data-model.md` must state, and what invalidated it

Two requirements on the Phase 1 artifact, both of which exist because a `data-model.md` can be complete,
reviewed, accepted, and unbuildable.

**Every Decider's state names the stream it is folded from**, written next to the state shape rather than
inferred from it:

```markdown
### `registration` Decider
State:  { claimed: boolean, seatId?: SeatId }
Stream: registration-{registrationId}          ← the only history this can rehydrate from
Folds:  PlaceClaimed, PlaceReleased            ← every one appended to that stream
```

Say it here and a cross-stream fold is visible while writing. Leave it implicit and the first proof is the
command refusing unconditionally, some days later, with the Decider's own unit test still green because it
was hand-fed an event that could never have been appended to that stream. Mirror the same list into the
slice's `folds` in `model.yaml`, where `check-model` enforces it.

**List the ADRs accepted since anything this plan reuses was written.**

| ADR | Accepted after | What it changes about an artifact this plan depends on |
|---|---|---|
| | | |

An accepted ADR can make an already accepted document unbuildable — an encryption decision changes the
shape of every Decider state folded from the encrypted payload, and a fold over ciphertext cannot produce
the value a comparison needs. Both documents were correct when written, neither is wrong, and nothing
compares them unless someone does it here. Empty is a fine answer; *unfilled* is not.

## Stubs and Deferrals

> Where a slice ships incomplete, record it here rather than in a commit message. Stubs belong at the
> edges; anything expensive to retrofit should be real from the start.
>
> **Re-read every open deferral against this slice's pattern before adding to the list.** A deferral is
> justified by a condition, and correcting a slice's pattern can end that condition without anybody
> noticing — "no projection runner, because this slice has no read model" is sound until the slice is
> reclassified as an `automation`, at which point it has one, the trigger has already fired, and no gate
> relates a pattern to the infrastructure it requires. An `automation` needs a **persisted** todo list and
> something able to run its processor standalone; if that is still deferred, say so here and say what
> breaks meanwhile.

| Deferred | Substitute | Consequence if shipped as-is |
|---|---|---|
| | | |

## Phase Status

- [ ] **Global event model** — this slice is on the timeline at `planned`, with its stream identity, and
      `make check-model` passes with the regenerated diagram committed
- [ ] **Phase 0** — research complete, every unknown resolved → `research.md`
- [ ] **Phase 1** — design complete → `data-model.md`, `contracts/`, `quickstart.md`, with every Decider's
      state naming the stream it folds, and the later-ADR table filled in or explicitly empty
- [ ] **Constitution re-check after Phase 1**
- [ ] **Phase 2** — task generation via `/speckit-tasks`. Not produced by this command.
