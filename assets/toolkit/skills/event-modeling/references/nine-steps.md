# The Nine-Step Workflow Design Process

Follow ALL nine steps for each workflow. Do not skip steps. Do not combine
steps. The process reveals understanding that shortcuts would miss.

## Step 1: Identify the User Goal

Ask until the goal is crystal clear:
- "What exactly is the user trying to accomplish?"
- "What does success look like to them?"
- "What would make this fail?"

Do not proceed until the goal is unambiguous.

## Step 2: Brainstorm Events

Sticky-note style -- capture all possible events without ordering:
- "What facts need to be recorded?"
- "What happened that we care about?"
- "What would an auditor want to know?"

Events must be past tense, business language, facts. Example:
`OrderPlaced`, `PaymentReceived`, `InventoryReserved`.

Keep asking: "What else? What am I missing?"

### Domain Facts vs. Runtime Context

Events must record **domain facts** — statements that are true regardless of
which machine, process, or environment replays them. Runtime context does not
belong in event data.

```
# Bad — runtime context leaks into the event:
ProjectInitialized {
  project_id: "abc-123",
  working_directory: "/home/dev/projects/myapp",   # machine-specific
  pid: 48291,                                       # process-specific
  hostname: "dev-laptop.local"                      # environment-specific
}

# Good — domain facts only:
ProjectInitialized {
  project_id: "abc-123",
  project_name: "myapp",
  initialized_by: "user-456",
  template: "web-app"
}
```

**Test:** "Would this field have the same value if the event were replayed on
a different machine?" If no, it is runtime context and does not belong in the
event.

## Step 3: Order Events Chronologically

Arrange brainstormed events into the timeline -- the "plot" of the workflow.

- "What happens first?"
- "And then what happens?" (repeat until complete)
- Identify the happy path and alternative/error paths

## Step 4: Create Wireframes

These wireframes do not need to represent the actual UI/UX of the
application. Their purpose is to provide a complete accounting of what data
a user can see and what actions a user can take from each screen.

For each user interaction point, create an ASCII wireframe showing:
- What data the user SEES (from read models)
- What data the user PROVIDES (command inputs)
- What actions the user can TAKE (buttons/triggers)

```
+-------------------------------+
|  Place Order                  |
+-------------------------------+
|  Items: [list from cart]      |
|  Shipping: [address]          |
|  Total: $XX.XX                |
|                               |
|  [Confirm Order]              |
+-------------------------------+
```

Every wireframe field must trace to an event field (displays) or a command
input (inputs). If you cannot trace a field, something is missing.

### Concurrency Check

If the domain supports concurrent instances (e.g., multiple orders, multiple
journeys), wireframes should show lists or tables, not single-item views.
Ask: "Can there be more than one of these in progress at the same time?"

## Step 5: Identify Commands

For each event, determine the trigger:
- "What triggered this event?"
- "Who or what issued that command?"
- "What information did they provide?"
- "Under what circumstances would this NOT happen?"

Commands are imperative, present tense: `PlaceOrder`, `ProcessPayment`.
Commands can fail; events cannot.

## Step 6: Design Read Models

Read models exist to support data displayed on wireframes as well as data
needed by automations. For each actor at each workflow point, and for each
automation:
- "What does this person need to see?"
- "What information do they need to make decisions?"
- "What data does this automation need to determine its next action?"

Verify every read model field traces back to an event. Example:
```
OrderSummary:
  orderId       <- OrderPlaced.orderId
  items         <- ItemAdded, ItemRemoved events
  totalAmount   <- OrderPlaced.totalAmount
  status        <- OrderPlaced, PaymentReceived, OrderShipped events
```

If a field has no source event, the model is incomplete.

### Concurrency Check

For each read model field, ask: "Can there be more than one of these active
at the same time?" If the domain supports concurrent instances, use collection
types, not singular values:
```
# Singular (only valid if business rule enforces one-at-a-time):
current_phase: string

# Collection (when concurrent instances exist):
active_journeys: [{journey_id, phase, started_at}, ...]
```

### Command Independence

Commands derive their inputs from user-provided data and the event stream.
Read models serve views and automations — they do NOT feed commands. If a
command needs to know whether something already happened, it checks the
event stream directly, not a read model.

- "Does the command rely on a read model to decide what to do?" → Wrong.
  The command should check the event stream for prior events.
- "Is an idempotency guard querying a read model?" → Wrong. Check the
  event stream for a duplicate event.

### No Read Models for Infrastructure Preconditions

Read models represent meaningful domain projections — not infrastructure
checks. If a precondition is purely about infrastructure state (does a
directory exist? is a service running?), it does not need its own read model.

```
# Bad — infrastructure check modeled as a read model:
ReadModel: RepositoryExistence
  exists: boolean    ← RepositoryInitialized

# Good — command checks the precondition directly:
Command: InitializeProject
  Precondition: directory exists (infrastructure, not domain state)
  Produces: ProjectInitialized
```

Infrastructure preconditions are either:
1. Implicit in the command's execution context (the OS provides them)
2. Checked as part of the command handler's implementation

They do not need a domain read model.

## Step 7: Find Automations

Look for automatic responses to events that involve decision-making:
- "Does anything happen automatically after this event?"
- "What business rules trigger other processes?"
- "Does the system need to check anything before acting?"

Pattern: Event -> Read Model (todo list) -> Process -> Command -> Event

**All four components are required for a true Automation:**
1. A triggering event
2. A read model (the "todo list") the process consults
3. Conditional logic that decides whether and how to act
4. A resulting command that produces new events

If there is no read model and no conditional logic — if the events are
always unconditionally co-produced — it is NOT an Automation. Model it as
a single Command slice with multiple output events.

**Test**: Ask "Can this automatic response ever be skipped or vary based on
system state?" If no, it is co-production, not automation.

Every automation must have a clear termination condition. Watch for infinite
loops.

## Step 8: Map External Integrations

Identify external system interactions using the Translation pattern:
- "Does this workflow receive data from outside?"
- "Does this workflow send data to external systems?"

Note only names and general purposes. No technical details (APIs, webhooks,
protocols). Example: "Stripe provides payment confirmation" -- not
"Stripe webhook sends POST to /api/webhooks/stripe".

### Data Flow Rules for Diagrams

When creating workflow diagrams, data flows follow these rules:
- **Actor/UI → Command**: User inputs flow into commands
- **Command → Event**: Commands produce events
- **Event → Read Model**: Events feed read model projections
- **Read Model → Actor/UI**: Read models serve views
- **Event → Automation Read Model → Process → Command**: Automations
  consult read models, but the resulting command still checks the event
  stream for its own validation

There must be NO `ReadModel → Command` edges in any diagram. If you find
one, the command is incorrectly depending on a read model.

### Infrastructure vs. Domain Translations

Ask: "Is this integration specific to THIS workflow, or would every
workflow need it?"

If every workflow needs it, it is cross-cutting infrastructure (persistence,
messaging, logging) — NOT a Translation slice. Note it as an infrastructure
dependency, not as a slice.

## Step 9: Decompose into Vertical Slices

List all vertical slices grouped by pattern type:

- **Command Slices:** Each command that produces events
- **View Slices:** Each read model/projection
- **Automation Slices:** Each automatic process
- **Translation Slices:** Each external integration

A good slice is: a complete user interaction, independently valuable,
testable in isolation, small enough for 1-2 days of work.

Bad slices: "Set up database" (technical, no user value), "Implement order
system" (too broad), "Create Order table" (implementation detail).

Also not slices: cross-cutting infrastructure (e.g., "Persist Events to
Database") that would appear identically in every workflow. Infrastructure
is not business behavior — document it in the domain overview, not as
workflow slices.

### Slice Independence

Slices that share an event schema are **independent** — connected by the
event contract, not by execution order. The event schema is the shared
contract between a command slice that produces events and a view slice that
consumes them.

```
# Bad — artificial dependency chain:
Slice 1: "Initialize Project" (must complete before Slice 2)
Slice 2: "Show Project Dashboard" (depends on Slice 1 running first)

# Good — independent slices sharing an event schema:
Slice 1: "Initialize Project" → produces ProjectInitialized event
Slice 2: "Project Dashboard" → projects from ProjectInitialized event
  (testable with synthetic ProjectInitialized fixtures, no Slice 1 needed)
```

- **Command slices** test by asserting on produced events (given prior
  events, when command executes, then these events are produced)
- **View slices** test with synthetic event fixtures (given these events,
  the projection shows this state)
- Neither slice needs the other to be implemented or running

### Interrogate every stream before naming it

A stream is one expected-version check: every command appended to it is refused if anything else on it
moved, so everything on one stream is serialised for ever, and the seam tests below take each stream as a
candidate they may never split. That makes naming a stream the first context decision, taken one level
down, and the noun-first mistake this method warns about for contexts is easiest to make here. "One record
per leaver (FR-003), so one stream `leaver-{leaverId}`" is the wrong reason whatever the answer turns out
to be: the noun says nothing about which decisions have to see each other's state.

So before a slice gets its `stream`, for each stream proposed:

1. **List the invariants it protects** — each decision that must see the current state to be safe, with
   the requirement it comes from. "It is all about one leaver" is not an invariant.
2. **Look first for invariants that span groups of slices.** A decision that reads several groups'
   current state at once — clearance closes only when the final day has passed, every item is back and the
   interview was held, in one transaction (an FR like that) — or a lifecycle state one group sets and every
   group must check — once the case is closed, by whichever group closes it, every later command is
   refused. Either is the reason to keep those groups on one stream: splitting them needs a process manager
   and opens a window in which the invariant can be breached. Name it, by FR.
3. **Where no invariant spans two groups, they are separate streams** correlated by id —
   `exit-interview-{leaverId}`, `clearance-{leaverId}` — and the seam tests then run between them. A
   different actor, trigger or reason to change is evidence for separating, but it does not outweigh an
   invariant that spans them.
4. **"One record per X" describes uniqueness, or a view** — what a person sees, folded from every stream
   with that id — and is not by itself a boundary. The boundary comes from the invariants.

What survives is written once per stream in the model's `streams` block, as `streams: {leaver: {because:
"<the spanning invariant, with its FR>"}}` — quoted, because a comma in an unquoted flow value starts a
new key and the model no longer parses. `make check-model` refuses a placed state-change slice whose
stream states none (`skills/global-event-model/SKILL.md`, *What the append is guarded by*).

### Apply Conway's Law: Which Lanes Are Which Context

Event Modeling ends by grouping the lanes into units that can change on their own — historically the
teams that would own them, but the boundary is in the model whether or not there are teams behind it, and
when one person or an agent does all the work it matters just as much: it is what stops one change from
rippling through everything, and it is what lets two of them go on at once. Here that step decides the
bounded contexts, and it runs over the model rather than over an org chart.

**Start from the streams, not the nouns.** Run `make seams`: it groups the slices by the stream they
write, attaches each view to the stream it folds, and lists the views that fold several. Those groups are
the candidates — once each stream has been interrogated above. A stream is one consistency boundary and is
never split across contexts — publishing a
listing and filling its chairs are one stream and stay together whatever else is decided. That rule is
what keeps this from becoming a process-stage split, which is the commonest wrong cut.

**Then test every seam between two candidates three ways**, each with the file and line it was read off
(`skills/domain-driven-design/resources/bounded-contexts.md`, *The Seam Tests*):

1. **Language.** Does a word both sides use mean two things — "Occasion" as a gift-giving date and as a
   billable line — or carry a different shape on each side, the same listing as a published night with a
   private address and as an approximate pin with a seat count? Qualifiers creeping in ("gifting user",
   "billing user") are this test failing out loud.
2. **Change.** Name one plausible change to the rules on each side and say whether it reaches the other.
   Seat rules, search radius, a feedback window and a community's house rules each change for a business
   reason of their own; a change that cascades both ways is one context's change.
3. **Flow.** Which actor decides the rules on each side, and is the handoff between them an event the far
   side only folds? A host's night, a player's search and the trust record meet at `ListingPublished`,
   `SeatAccepted` and `SessionCompleted`; a step inside one actor's job is not a seam.

Then count what crosses. An event folded on the far side is contract coupling, and cheap. A command that
must read the far side's current state at decision time, or share its transaction, is strong coupling and
keeps the two together on its own. A view that folds several candidates is a view unless its rules change
for their own reasons, in which case it is a context with no writes, and still one.

**A shared noun is evidence for neither side.** Two candidates that share every word and change for one
reason, under one actor, are one context. Two that share every word and fail the change test or the flow
test are two. One vocabulary with one reason to change is still one context. The seams output saying *one stream,
one candidate* is the end of the seam tests, not of the decision: it is only as good as the stream
interrogation that produced it, and it is recorded like any other answer.

Write the proposal as a table — candidate, streams it writes, the three tests' evidence, what crosses,
confidence — then say which seams you are unsure about and why, and leave the genuinely undecidable ones as
questions. Record the contexts on the owning service in `project.json` as `contexts: ["tables",
"community"]`, then give every slice its `context:` beside its `service`. From then on `make check-model`
requires the field and refuses a stream written from two contexts, and `make check-imports` refuses one
context reaching into another except through its `public` module. A context is not a service, and finding
two does not mean adding a deployable (`docs/architecture.md`, *Bounded contexts*, has when it does). This
is a decision to take with the user: the model shows the seams, the people who own the words confirm them,
and the decision entry carries all three tests in its *Why* and its *Would reverse if*.

**It is always recorded, one context included**, as the next entry of `specs/<feature>/decisions.md`,
headed `## D<n> — Which bounded contexts does <feature> touch?`, with the table above under its `Options`
line. Where one context would hold more than twelve slices, the entry adds a `- **Why not split:**` line
citing, by FR, the invariant that spans its groups and keeps them together. Twelve is not a limit and
nothing here implies a split: it is where one serial fairway costs enough of a run that its reason has to
be written down. `make check-chart` refuses the chart without the entry, or without that line.
With nobody present — a session a script dispatched, `SLIPWAI_STAGE` in its environment — proceed on
the best-evidenced proposal, record it `Decided by: host (stage recommendation)` at `Status: awaiting human
confirmation`, and post the question to the board as `commands/chart.md`, *Record the context answer,
every time*, says: a `question` line with the entry's `D<n>` as its `id`.

## Output Structure

This repository records the outcome in one cumulative model plus one example map per slice, not in a
per-workflow directory tree. `docs/event-model/README.md` is the schema reference and
`skills/global-event-model/SKILL.md` is the recording procedure:

```
docs/event-model/model.yaml               every slice: pattern, actor, stream, events, reads, status
specs/<feature>/slices/<id>/examples.md   one slice's rules, examples and Given/When/Then,
                                          linked from that slice's `gwt` field in model.yaml
```

The diagram is generated from `model.yaml` by `make model` and checked by `make check-model`; the draw.io
canvas beside it by `make model-drawio`, held current by `make check-drawio`. Neither is ever hand-written.

## Facilitation Questions Quick Reference

**Domain Discovery:** What does the business do? Who are the actors? What
are the major processes? What external systems exist? Which workflow is
most critical?

**Events:** What facts need recording? What happened here? Would the
business need to know this?

**Timeline:** What happens first? And then? Can these happen in parallel?

**Commands:** Who initiates this? Is it user-triggered or automatic? What
intent does this represent?

**Read Models:** What does this actor need to see? What queries do users
run? Can there be multiple instances active simultaneously?

**Automations:** Does anything happen automatically? What business rules
apply? Does this trigger other processes?

**Edge Cases:** What if this fails? What if the user cancels? What if the
external system is down?
