---

description: "Task template for an event-modelled vertical slice"
---

# Tasks: [FEATURE NAME] — Slice [SLICE_ID] ([SLICE_CAPABILITY])

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, **and this slice's executable
specification** — `specs/<feature>/slices/<id>/examples.md`, which `docs/event-model/model.yaml` names in
`gwt`. If it does not exist, stop: run `/example-map <id>` first. Task generation turns its scenarios into
test tasks, so without it the test tasks get invented here instead of derived from agreed examples.

**Tests**: **REQUIRED, not optional.** The constitution's Principle V mandates Given-When-Then acceptance
criteria observed failing before implementation, binding at the application boundary. Within the slice
phase this is enforced increment by increment: one rule's examples failing, the code that passes them, refactor,
commit — never a batch of tests followed by a batch of implementation. This overrides any template
default that tests are optional.

**Scope**: **One slice only.** One capability, one observable outcome per criterion. If this slice's name
contains "and", stop and split it before generating tasks (Principle V).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelisable (different files, no dependency on incomplete tasks)
- **[Story]**: `[US#]` on user-story phase tasks only; Setup, Foundational and Polish carry none
- Every task names an exact file path

## Read Before Starting

**If this is the first slice, it will be front-loaded** — the foundational phase builds infrastructure
every later slice reuses. Do not read the ratio of foundation to feature as a sign the slice is wrong.

**If the starter scaffolding is present**, Phases 1 and 2 are already done. Delete the tasks that are
satisfied and begin at the slice phase.

**One thing the starter does not scaffold is a frontend.** It ships a backend hexagon and no user
interface, so "Phase 1 is already done" is true of everything except the tree a white box needs. If any
slice here has a `ui` frame and the project has no frontend and no UI test harness yet, that is foundational
work this slice pays for — not a reason to ship the slice without its screen.

---

## Phase 1: Setup (skip if starting from the event-modelling starter)

- [ ] T001 Create the source and test tree: `apps/service/src/domain/shared/`, `apps/service/src/domain/[context]/`, `apps/service/src/application/{ports,usecases,projections}/`, `apps/service/src/adapters/{driving,driven}/`, `apps/service/src/composition/`, `apps/service/migrations/`, `apps/service/tests/{acceptance,domain,edge,projection,contract,integration,fakes,stubs}/` — plus, **wherever any slice on the roadmap has a `ui` frame, the frontend tree and its test harness**, since a white box is a deliverable of the slice that models it and a slice cannot build one into a tree that does not exist
- [ ] T002 Initialize the project and pin the runtime version in the repository
- [ ] T003 [P] Configure strict type checking at maximum practical setting
- [ ] T004 [P] Configure linting: ban escape-hatch types in domain and application; ban clock reads, randomness, and identifier generation inside the domain
- [ ] T005 [P] Write the dependency-direction check: fail the build if domain imports infrastructure, or imports any third-party package except the schema library
- [ ] T006 [P] Configure the test runner with five projects: `acceptance`, `domain`, `projection`, `contract`, `integration` — levels of scope, not categories of origin
- [ ] T007 [P] Add a local database container for development and tests
- [ ] T008 [P] Configure schema migrations
- [ ] T009 Validate every environment variable through a schema at startup, exiting non-zero on invalid input
- [ ] T010 [P] Assert the runtime version at startup against the repository pin
- [ ] T011 [P] Configure mutation testing scoped to the domain, wired to its own command (not the default test task)
- [ ] T012 Add CI running typecheck, lint, the import check, the vulnerability scan, migrations, and all tests — every step a target the pipeline and an engineer invoke identically

---

## Phase 2: Foundational (skip if starting from the event-modelling starter)

**Every task here blocks the slice phase.** All of it is reused unchanged by later slices.

### Domain primitives

- [ ] T013 [P] Branded value type for the domain's core measure (e.g. `Money` as integer minor units with explicit currency), with same-unit arithmetic enforced at compile time
- [ ] T014 [P] Branded identifiers, mutually non-assignable
- [ ] T015 [P] `Decision<E, R>` as accept-with-events or reject-with-reason, structurally unable to be both
- [ ] T016 [P] Event envelope and its schema: `schemaVersion`, actor union, correlation and causation ids as UUIDs in types of their own (causation optional), domain time. **Tolerant reader** — unknown fields ignored, not fatal

### Ports, fakes, and stubs

- [ ] T017 `EventStore` port: `append`, `readStream`, `readAll`; expected version as `noStream | exactly`; **a version conflict returned as a value, not thrown**
- [ ] T018 [P] `Clock` and `IdGenerator` ports
- [ ] T019 [P] In-memory `EventStore` fake able to **force a conflict on demand**, so contention paths are deterministic
- [ ] T020 [P] Advanceable `Clock` fake and deterministic `IdGenerator` fake
- [ ] T021 [P] Stub harness for systems this codebase does not own: a provider served over loopback, the requests it received observable, a sequence of responses to drive retries, and a way to accept a request and never answer it so the **adapter's** timeout is what ends the test. Plus the pinning convention — every stub response validated against a recorded or published contract, recordings committed under `tests/stubs/contracts/`. **A fake implements our port; a stub impersonates their provider, and nothing we own says what it should return** (Principle VI). Skip only if no slice on the roadmap integrates with anything

### Event store

- [ ] T022 Migration: event log table with a **unique constraint on (stream, version)** — that constraint IS the optimistic concurrency control — and separate domain-time and storage-time columns
- [ ] T023 Migration: enforce append-only at the database. **Revoking privileges is not sufficient if the application role owns the table** — an owner keeps its privileges. Use a statement-level trigger refusing UPDATE, DELETE, and TRUNCATE
- [ ] T024 Event store adapter, translating a unique-constraint violation into a conflict result. **Anything called from inside `append` must reuse `append`'s connection** — reaching for the pool while holding a connection deadlocks under contention
- [ ] T025 One shared `EventStore` contract suite, run against **both** the fake and the real adapter, so the fake cannot drift
- [ ] T026 Concurrency test against the real store: N simultaneous writers to one stream, exactly one wins. Real store only — the fake cannot genuinely race

### Projections and cross-cutting

- [ ] T027 Projection runner: apply a pure fold, and **rebuild any projection from position zero**. Needed by the first slice whose `materialisation` is `inline` or `async`; a roadmap of nothing but `live` folds defers it, and says so in the plan's Stubs and Deferrals with what the first materialised view will cost to retrofit
- [ ] T028 Structured logging with correlation-id propagation
- [ ] T029 Application-layer authorisation policy, invoked by use cases and never by route handlers
- [ ] T030 HTTP app factory with schema parsing that distinguishes **schema failure from business rejection**
- [ ] T031 Composition root — the only place adapters are bound to ports

---

## Phase 3: Slice [SLICE_ID] — [SLICE_CAPABILITY] 🎯

**Goal**: [one capability, stated as an observable outcome]

**Independent test**: [how this slice is verified without any other slice working]

**Stream identity**: [name the stream and what it makes the consistency boundary — this determines the
concurrency ceiling and MUST be explicit, not incidental]

### The model first

- [ ] T032 [US1] Confirm this slice in `docs/event-model/model.yaml`: its frames in causal order, its
      `reads`, its `stream`, `gwt` pointing at `specs/<feature>/slices/<id>/examples.md`, and
      `status: planned`. Run `make model && make check-model` and commit the regenerated diagram. **Do this
      before the first increment** — the event names asserted below are the names the model carries, and
      reconciling them afterwards means renaming events that are already written. `check-model` refuses
      `planned` without `gwt` (`examples-before-planning`), so if that file does not exist yet, stop and run
      `/example-map <id>`: the increments below drive its scenarios, and inventing them here instead means
      building against a guess

### Increments for this slice — one rule per RED-GREEN-REFACTOR cycle ⚠️

**Each task below is one rule of `slices/<id>/examples.md` with the examples that belong to it — one full
cycle, not a test to be batched with the others.** Stub whatever the rule's examples name so the suite
builds, write its examples — together or one at a time, as the implementer judges — observe each failing
*and failing for its own stated reason*, write the smallest code that makes them pass, refactor on green, and
run the quickest relevant tests in the same file or area. Then start the next rule.

**Do not write the next rule's examples until the current rule is green and refactored** (Principle
V). Commit each increment locally. Do not push those commits until the actor has accepted the demo; that is
when the full suite runs. The history choice never permits writing this whole list as tests first and then
implementing against them: that fixes the design before the first test result arrives and turns a one-line
attribution into a debugging session. The map's rules are the list of increments to drive, their examples the
tests inside each — not a body of test code to author in one sitting.

The order is deliberate. The first increment pays the structural cost of reaching every layer; each later
one adds a rule to code that already exists.

**Each RED below cites a scenario id from `slices/<id>/examples.md`** — `AC-` at the boundary, `CS-` at the
Decider, `VS-` for a view fold — and the test's own title carries that id. Two things fall out of that: a
grep proves every agreed example has a test, and a test with no id is either a scenario missing from the map
or behaviour being invented at the keyboard. If an increment has no scenario to cite, the map is incomplete —
go back to `/example-map` rather than filling the gap here. Replace the generic increments below with one per
rule the map actually holds, each citing its `R<n>`; the list is a checklist of *kinds*, not a quota to meet. A
task whose GREEN would be empty — a proof over behaviour an earlier task built — is a rule cut too small, and
folds into the task that produces the behaviour it guards.

- [ ] T033 [US1] **Happy path.** RED: boundary acceptance for the happy path, entering through the use case, asserting on what is observable there. The route gets its own `tests/edge/` test for parse, delegate, and outcome-to-status — it is a translation, not where the rule is proved. GREEN: the minimum that satisfies it — the event schema(s) this one scenario needs, `initialState` and `evolve`, `decide` for the one command, the driving port returning discriminated outcomes, the use case (load, fold, decide, append with expected version), the route handler, and the composition wiring
- [ ] T034 [US1] **The white box, in its main state.** *Delete these three tasks only if this slice has no `ui` frame — which for a `state-change` or `state-view` slice means the model is wrong, not that there is no screen.* RED: a test at the project's UI level drives the surface the way its actor does — type into the labelled fields, click the button — and asserts what the actor sees. GREEN: the screen. **If the `ui` frame has `mockups`, that state's mock is the build target**; open it and build to it. **If it has none, design it here** — then commit the wireframe under `docs/event-model/mockups/` and add its `mockups` entry to the frame in the same commit, because a screen whose states are recorded nowhere is a screen whose gaps nobody can see. An HTTP test through the route is **not** evidence about this task; load `front-end-testing` (and `react-testing` if the project is React) for the lightest harness that proves a browser-observable claim
- [ ] T035 [US1] **Every other state of the screen.** One increment per state — empty, error, submitting, forbidden, whatever the screen can actually be in. RED at the UI level per state, GREEN the rendering it needs. These are where the unmodelled states surface: a screen with one design has three states nobody decided. Each one ends up in `mockups` too, so the model carries what the screen can be rather than what somebody remembered to draw
- [ ] T036 [US1] **The screen reaches the command.** RED: submitting drives the driving adapter with the actor's input and renders each outcome the use case can return — accepted, business rejection, schema failure. GREEN: the wiring. **If the path beneath the screen is not finished in this slice, the screen still ships** — its submit reaches whatever exists and its states are still built and tested. A white box deferred to a later slice makes this slice a layer, and Principle V's slice independence is about seeding from synthetic events, never about leaving the actor with nothing to use
- [ ] T037 [US1] **First business rejection.** RED: one rejection at the boundary, with its reason and any detail the caller needs to explain it. GREEN: extend `decide` to reject in business vocabulary. **Each further rejection is its own increment** — repeat this cycle per rule, do not add them as a batch
- [ ] T038 [US1] **Schema failure is not business rejection.** RED: malformed input returns a *different* status from a business rejection. GREEN: parse into a typed command at the driving adapter
- [ ] T039 [US1] **Idempotency.** RED: the same key replayed produces one effect and returns the original outcome. GREEN: check the event stream, never a read model (Principle II)
- [ ] T040 [US1] **Concurrency at the contended boundary.** RED: N simultaneous callers, exactly one succeeds, the invariant never violated. GREEN: re-decide on conflict rather than surfacing it — a version conflict is a return value, not an exception
- [ ] T041 [US1] **Authorisation.** RED: another tenant's resource returns not-found, not forbidden. GREEN: enforce inside the application, not in the driving adapter alone (Principle IX)
- [ ] T042 [US1] **Audit fields.** RED: every appended event carries actor, correlation id, and domain time, and no sensitive or personal data. GREEN: populate the envelope from ports, not from ambient context
- [ ] T043 [US1] **Projection fold.** RED: fold specs over synthetic event fixtures. GREEN: the projection as a pure fold **scoped to its own streams** — a projection folding every stream in the log fails the moment an unrelated stream exists
- [ ] T044 [US1] **Read model at the boundary.** RED: the view is observable through the use case that exposes it. GREEN: whatever the slice's `materialisation` names — for `inline` or `async`, the view's table and its queries; for `live`, the per-query fold **plus a test that fails when the fold exceeds `liveBudget.events`**, which is what makes the ceiling a fact rather than a hope
- [ ] T045 [US1] **Rebuild equivalence.** RED: dropping and rebuilding read models from zero yields identical values. GREEN: whatever the rebuild path lacks
- [ ] T046 [US1] **Rules the boundary cannot reach.** One increment per rule: a Decider spec driving it directly, then the rule. A rule with no test is where bugs live — say why the boundary cannot reach it
- [ ] T047 [US1] **The provider failure catalogue.** *Only where this slice adds or changes a driven adapter to a third-party system; delete this task otherwise.* One increment per failure mode, each against the stub: the 4xx a caller can fix, credential rejection, rate limiting with its retry hint, 5xx, timeout, and a response the contract does not allow. GREEN maps each to domain vocabulary — never a leaked provider type, never a retry that can duplicate a non-idempotent effect. Add the adapter to its port's contract suite in the same slice, so the port is satisfied by the real implementation and not only by the fake
- [ ] T048 [US1] **Forward compatibility.** RED: a reader built against the **previous** schema ignores unknown event types and fields. GREEN: tolerant reading, plus any discriminator later slices will need — adding a field is additive; discovering every historical event lacks it is not

**Checkpoint**: this slice is independently shippable. State its release constraint explicitly.

**Demo checkpoint — stop here before Phase 4.** As soon as the actor-visible path and its focused tests are
green, give the user the shortest exact demo: command, URL or interaction, required seed data, expected
result, and every deliberate stub or release constraint. Do not treat an internal test or a backend behind
an unbuilt modelled white box as a demo. Ask what using it revealed. Feed defects and small adjustments
within agreed scenarios back through RED-GREEN-REFACTOR; changed rules back to `/example-map`; newly exposed
boundaries within the specified product to `/story-splitting`; new product scope to `/speckit-specify` and
its downstream stages; and new event names, fields or stream identity to event modelling. Demonstrate the
revised path again. Resume Phase 4 only when the demo is accepted with no unresolved feedback; evidence must
not delay feedback on working behaviour.

---

## Phase 4: Polish

- [ ] Run `/adversary` and record the full attempt log; fix every confirmed violation of an existing
      scenario through a failing `adversarial: <attack>` test, asking only where behaviour is undefined
- [ ] T049 Run mutation testing on this slice's Decider; address surviving mutants or record a documented reason with mutation marked N/A
- [ ] T050 [P] Verify the append-only guarantee as a test, not an assumption
- [ ] T051 [P] Walk this slice's quickstart section by hand and correct any drift
- [ ] T052 [P] Record any capability shipped incomplete, what substitutes for it, and the consequence of shipping it as-is (a deferral — not to be confused with a provider stub under `tests/stubs/`)
- [ ] T053 Move this slice to `status: implemented` in `docs/event-model/model.yaml`, filling in `gwt`,
      `code` — **including the frontend files, which are as much this slice's implementation as its
      Decider** — and every `ui` frame's `mockups`, then `make model && make check-model`. The check fails
      if a listed path does not exist, if an event in the model appears nowhere in the source, if a white
      box appears nowhere in the source (`screen-is-built`), or if a shipped screen records none of the
      states it renders (`screen-states-recorded`) — which is how a rename that stopped at the code, or a
      slice that quietly shipped without its user interface, gets caught rather than becoming diagram fiction

---

## Dependencies & Execution Order

- **Phase 1** → no dependencies
- **Phase 2** → requires Phase 1; **blocks Phase 3 entirely**
- **Phase 3** → requires Phase 2
- **Phase 4** → requires Phase 3

### Slice dependencies

Fill the same structured graph the split and plan carry — genuine build deps only:

| Slice | depends_on | parallel_ok_with | Notes |
|---|---|---|---|
| [ID] | [ids, or —] | [sibling ids] | synthetic-event seeding is **not** a dependency (Principle V) |

On the event profile, the same `depends_on` list lives on this slice in `docs/event-model/model.yaml`.
`/drive` selects from the **ready** set (deps archived), not blindly the next row of the split.

### Parallel opportunities

**Across slices:** siblings in `parallel_ok_with` whose `depends_on` are already archived may run in
parallel across sessions; one `/drive` session still drives one slice.

**Inside this slice — Phase 3 has none, by construction.** Its tasks are RED-GREEN-REFACTOR increments and
are strictly sequential: each one starts after the prior increment's local quick tests are green.
Parallelising them is the
batched-tests anti-pattern wearing a `[P]` marker.

Domain primitives in Phase 2 are parallel, as are the independent Polish tasks. Tasks touching the same
file are never parallel, however independent they look.

---

## Implementation Strategy

1. Phases 1–2 — foundation. Nothing user-visible; do not ship alone.
2. Phase 3 — **the slice ships**, one increment at a time, each committed locally. Push after demo
   acceptance. State its release constraint.
3. Phase 4 — evidence. Required before "done", not before "demonstrable".
4. Archive the slice-scoped artifacts, then automatically select the next **ready** slice (earliest in the
   split among those whose `depends_on` are archived; name any parallel siblings), map if necessary, plan
   and generate tasks. Stop only for required input, the next demo, or an exhausted / fully blocked split.

### Notes

- One file or one tightly-scoped change per task. Commit each green Phase 3 increment locally; push the
  slice after demo acceptance.
- A Phase 3 task is not done when its test is written. It is done when its test is green, the refactor
  step has been taken, and the quickest relevant tests in the same file or area pass.
- A version conflict is a return value, never an exception. Contention is expected under load.
- Every task carries a checkbox, a sequential id, a story label where required, and an exact file path.
