---
name: event-sourcing
description: Event sourcing patterns for functional TypeScript — persist state as an append-only log of past events and rebuild it by folding them. Use when implementing a Decider write model, an event store, projections and read models, event versioning, or snapshots. Builds on the Decider from domain-driven-design and the ports/adapters from hexagonal-architecture.
capabilities: event-modelling, event-sourcing
---

# Event Sourcing

## Scope: backend persistence only

Apply this skill only to backend contexts and deployables that own the event-sourced write model. A browser
frontend may issue commands and render query results, but it never owns streams, rehydrates Deciders, or
reads the event store. Under `apps/web/**`, use ordinary component, server, and URL state and consume a
deliberate API/query contract instead. Event Modeling may still include UI frames because it describes the
end-to-end journey; that does not make the UI event-sourced.

Event sourcing stores every change to application state as an immutable, append-only sequence of **past-tense domain events**. The current state is never stored directly — it is a **left fold** of the events: `state = events.reduce(evolve, initialState)`. The event log is the source of truth; every other representation (aggregate state, read models, search indexes) is a derived, disposable projection you can rebuild by replaying events.

**In this project event sourcing is the premise, not a candidate.** The decision was made when the domain was modelled, so this skill is about doing it well rather than about whether to do it. What still needs deciding per slice is **what its append is guarded by** — `stream`, where one stream is one consistency boundary and sets the concurrency ceiling, or a `guard` drawn over tags for the constraint one stream cannot express. The model asks for one of the two before a slice can be planned.

**This skill builds on three others — load them alongside it:**
- `domain-driven-design` — the **Decider** (`decide`/`evolve`/`initialState`) is defined in its `resources/domain-events.md`. Event sourcing *persists and replays* that same decider. This skill assumes you have read it.
- `hexagonal-architecture` — the event store is a **driven port** with an adapter; the domain stays pure. Reads use the **CQRS-lite** split (`resources/cqrs-lite.md`).
- `typescript-strict` — events cross a trust boundary on the way out of and back into storage, so they are **schema-first** with branded IDs.

**Deep-dive resources** are in `resources/`. Load them on demand:

| Resource | Load when... |
|----------|-------------|
| `when-to-use-event-sourcing.md` | Telling event sourcing apart from CQRS, event-driven architecture, streaming, and audit logs; the obligations it carries |
| `modelling-events.md` | Discovering and naming events with event modeling — swimlanes, the four patterns, slices — plus granularity and what data belongs in an event |
| `decider-and-rehydration.md` | Writing the decide/evolve pair, rehydration, the command handler loop, decider composition |
| `event-store.md` | Designing the EventStore port, the Postgres schema, optimistic concurrency, the event envelope, the TS/Node tooling landscape |
| `projections-and-read-models.md` | Building read models, inline vs async projections, rebuilds, checkpoints, eventual consistency |
| `event-versioning.md` | Evolving event schemas — upcasting, tolerant readers, weak schema, stream copy-transform |
| `testing-event-sourced-systems.md` | Testing deciders, projections, and upcasters as behaviour, directly or through an existing test DSL |
| `production-concerns.md` | Snapshots, GDPR/crypto-shredding, idempotent delivery, operability, the anti-patterns catalog |
| `references.md` | Checking the rationale and primary sources behind this guidance |

For the authoritative sources bundled with this skill, see `resources/references.md`.

---

## What Event Sourcing Obliges You To

Events are the source of truth, which makes four things permanent commitments rather than choices to revisit:

- **Event schemas live forever.** Events are never rewritten, so every field is a commitment for the life of the system, and old shapes must stay readable by new code. Decide the tolerant-reader / upcasting strategy on day one (`event-versioning.md`).
- **Stream identity is the consistency boundary.** One stream is one concurrency ceiling. Changing it later migrates the one thing that cannot be migrated.
- **Reads are projections.** The log answers get-by-id, so every query needs a read model, and those read models lag. Design the UI for the lag (`projections-and-read-models.md`).
- **Replay must be free of side effects.** Anything that talks to the outside world belongs in a handler, never in `evolve` — otherwise a rebuild re-sends it.

**Event sourcing is not CQRS.** They are orthogonal. CQRS separates the write model from read models; event sourcing chooses events as the write model's storage. You can do CQRS without event sourcing (that is the hexagonal skill's CQRS-lite) and — rarely — event sourcing without CQRS. In practice event sourcing almost always drives CQRS, because the stored events are a poor shape for queries, so you project them into read models. See `when-to-use-event-sourcing.md` for the full comparison against event-driven architecture, streaming (Kafka), and audit logs.

---

## Core Mental Model

Four ideas carry the whole pattern.

1. **Events are the source of truth.** They are immutable facts, named in the past tense, that record *what happened* and *why*. You never `UPDATE` or `DELETE` an event — you only `append`. Correcting a mistake means appending a new compensating event, exactly as an accountant never erases a ledger entry.

2. **State is a left fold of events.** There is no stored "current state". You rebuild it on demand by folding the `evolve` function over the stream — this rebuild is called **rehydration** or **replay**. Greg Young's formulation: *"Current State is a Left Fold of previous behaviours."*

   {{example: event-sourcing/rehydrate-left-fold}}

3. **The stream is the consistency boundary.** One aggregate instance maps to exactly one stream (e.g. `account-4f3c…`). All invariants for that aggregate are enforced within its stream, and appends use **optimistic concurrency** on the stream's version. You never rely on a cross-stream transaction to keep an aggregate's invariants true — the stream is the consistency boundary, and cross-aggregate work is a process manager / saga (some stores *can* append to several streams atomically, but a well-modelled aggregate never needs it).

4. **Read models are disposable derivations.** Because state is `fold(events)`, any read-optimised view is just a different fold. You can delete a projection and rebuild it from event zero. This is what makes "add a new report retroactively" trivial.

**Vocabulary** (used consistently across this skill):

| Term | Meaning |
|------|---------|
| Event | An immutable past-tense fact: `MoneyDeposited`, `OrderShipped`. The unit of storage. |
| Command | A request to *attempt* a change: `DepositMoney`. May be rejected. Never stored. |
| Stream | The ordered sequence of events for one aggregate instance. The consistency boundary. |
| Decider | The pure write model: `decide` (command + state → events) and `evolve` (state + event → state). |
| Rehydrate / replay | Rebuild state by folding `evolve` over a stream's events. |
| Projection | A fold of events into a read model (a query-optimised view). |
| Snapshot | A cached fold result stored to avoid replaying long streams. An optimisation, never the source of truth. |
| Event store | The append-only, ordered, optimistic-concurrency-aware persistence for streams. A driven port. |
| Expected version | The stream version a command was decided against; used to detect concurrent writes on append. |

---

## The Decider Is the Write Model

You do not write new domain logic for event sourcing — you **persist the Decider you already have** from the DDD skill. The functions are the same three, with one refinement for this skill: `decide` returns an explicit `Decision` (accept-with-events or reject-with-reason) rather than the DDD example's bare event array:

{{example: event-sourcing/account-decider-and-evolve}}

Financial events carry integer minor units and currency. The command boundary rejects non-safe integers (`NaN`, infinities, fractions, and overflow), and any conversion from decimal major units must name a currency exponent and rounding policy before the command is built; never persist a binary floating-point amount.

**The division of labour is strict** (get this wrong and the whole model rots):
- `decide` holds **all the business rules**. It reads current state, validates the command, and either **accepts** (returning events) or **rejects** (returning a business reason). It has no side effects and does not touch storage.
- `evolve` holds **no command rules**. It exhaustively applies every valid stored event. A known event that cannot follow the current state is corrupt history, so replay must surface a corruption error rather than silently retain state. Tolerant readers and upcasters keep older valid events readable; they do not make impossible transitions valid.

Modelling `decide`'s outcome as an explicit `Decision` result (accept-with-events or reject-with-reason) follows the DDD skill's error-modelling rule: expected business outcomes are result types, not exceptions. See `decider-and-rehydration.md` for `Decision`, `isTerminal`, and how deciders compose.

---

## The Command Handler Loop

The application service ties the pure decider to the impure event store. This loop is the heart of every event-sourced write, and it is the same every time:

{{example: event-sourcing/command-handler-loop}}

Everything pure (`evolve`, `decide`) is trivially testable with no mocks. Everything impure is behind the `EventStore` port. The **expected version** on append is what makes concurrent writes safe: if another writer appended to the stream between step 1 and step 4, the append fails and the caller retries from step 1 (load fresh state, re-decide). This snippet shows the **bare shape**; the production form wraps steps 1–4 in a bounded reload/re-decide retry loop (see `decider-and-rehydration.md`). Never skip the expected version — without it, two concurrent withdrawals can both pass the balance check and overdraw the account.

---

## The Event Store Port

The event store is a **driven port** (hexagonal skill). The application command handler consumes it, so define the interface in the application layer in application language; implement it in an adapter. Keep domain event types and the pure decider in the domain. The minimal contract is small:

{{example: event-sourcing/event-store-port}}

A production store adds subscriptions (for async projections) and reading the global event order, but every event store must provide: **append-only writes, ordering within a stream, and optimistic concurrency via expected version.** The canonical Postgres implementation atomically compares and advances a stream-head row in the same transaction that appends events; `UNIQUE (stream_id, version)` remains a defence-in-depth constraint. See `event-store.md` for the full schema, the event envelope (with correlation/causation UUIDs), and where Emmett, KurrentDB (EventStoreDB), and message-db fit.

**Events are stored as data across a trust boundary,** so on the way out they are validated with a schema (a **tolerant reader**) before `evolve` ever sees them. This is where event sourcing meets `typescript-strict`: the stored JSON is untrusted input, parsed into branded domain events on read. It is also where **versioning** lives — see below.

---

## Events as Data

Events are the most permanent thing you will ever write. A row in a table can be migrated; an event is a historical fact that will be replayed for as long as the system lives. Design them with care (full guidance in `modelling-events.md`):

- **Name them in the past tense, in business language.** `SubscriptionCancelled`, not `UpdateStatus`. `FundsWithdrawn`, not `RowUpdated`. An event names something that *happened* in the domain.
- **Avoid CRUD events.** `AccountCreated` / `AccountUpdated` / `AccountDeleted` is a database changelog wearing an event-sourcing costume — it captures *that data changed* but not *what happened or why*. Model the intent: `AccountOpened`, `AddressCorrected`, `AccountClosed`.
- **Put the facts in the event, not references to look up later.** An event must be interpretable on its own, years later, without joining to mutable tables. Capture the values that were true at the moment it happened (the price charged, the rate applied) — not a foreign key to a row that will have changed.
- **Give every event an envelope:** a unique id, type, stream id, version, timestamp, and metadata (correlation and causation ids for tracing a command through the events it caused). The domain payload is separate from this envelope. **Both ids are UUIDs, each in its own type** — a free string invites an id that means different things in different services, and a shared type lets the two be swapped without a compiler or a test noticing.
- **Model events as a discriminated union** with a `type` discriminant and exhaustive handling, exactly like commands and state — the same `never`-guarded switches the DDD skill uses.

---

## Projections and Read Models (CQRS)

Most questions a user asks are not answered by folding a stream per read: a cross-aggregate query needs data the streams deliberately keep apart, and a fold whose cost grows with history is a cost that never comes back down. Instead, **project** event envelopes into read models: a projection is just another fold, `envelopes.reduce(applyToBalanceView, emptyBalanceView)`, whose result is a query-shaped table.

Where the result of that fold lives is a decision with three answers — folded per query, written inline with the append, or maintained by a catch-up subscription — and it is not a decision to leave implicit, because the implicit answer is always the per-query fold: it is the only one the event-store port can already do. A per-query fold is a legitimate answer for a view over one short-lived stream, and a liability everywhere else. `projections-and-read-models.md` sets out the three, what each costs, and the ceiling a per-query fold has to declare; in a project generated by this factory the answer is a field on the slice and `make check-model` asks for it before the slice can be planned.

{{example: event-sourcing/balance-view-projection}}

The creation event is the only transition from `unopened` to `open`, and the read-model ID comes from the validated envelope's `streamId`, not duplicated payload data or a caller-supplied seed. The consumer skips an exact redelivery by event ID or checkpoint before this fold; an admitted later `AccountOpened`, a money event before opening, or an envelope from another stream is therefore impossible known history and must stop the projection for investigation. Tolerant reading and upcasting also happen before this typed fold; they preserve compatible old events, not impossible transitions.

- **Inline (synchronous) projections** update in the same transaction as the append — no lag, but they couple write throughput to projection work. **Async projections** subscribe to the event stream and update separately — they scale and isolate failures, at the cost of **eventual consistency** (a read model may lag the write by milliseconds).
- **Eventual consistency is the headline trade-off.** A user who just issued a command may not immediately see it reflected in an async read model. Design the UI for it (return the just-written state from the command, show optimistic UI) rather than pretending the lag does not exist.
- **Projections are disposable.** Track a **checkpoint** (the last event position processed); to rebuild, reset the read model and the checkpoint to zero and replay. This is how you add a brand-new read model over years of existing history, and how you fix a buggy projection.
- **Projections must be idempotent.** Delivery is at-least-once, so applying the same event twice must not double-count. Key on the **event id** or **global position** (unique store-wide); a bare stream `version` only suffices when the read-model row is scoped to a single stream, because versions repeat across streams.

This is the write/read split from the hexagonal skill's CQRS-lite, taken to its full form: writes go through the decider + event store; reads go through projected read models. See `projections-and-read-models.md`.

---

## Testing Event-Sourced Systems

Event sourcing is one of the most testable patterns there is, because the write model is pure: **events in → state → command → events out**, all plain data.

The event-sourcing literature almost universally reaches for a **given-when-then** shape here — *given* these past events, *when* this command is handled, *then* expect these new events — often as a fluent `given(...).when(...).then(...)` DSL or Gherkin scenarios. It reaches for it for a good reason: **that shape is the decider's algebra.** Past events fold to state, a command is applied, and the assertion is on the resulting events. It is worth understanding *why* the pattern fits so well.

Express that algebra using the repository's established test style. A direct behaviour-driven test (see the `testing` skill) calls the public function, asserts on the observed output, names the test after the business behaviour, and builds data with factories. An existing given/when/then helper may express the same behavior; do not introduce a new DSL merely because event-sourcing literature uses one. The direct form maps cleanly with no new machinery:

- **"given past events"** → build the starting state with a factory, or fold event factories with `evolve`. (Past events are just data.)
- **"when a command"** → call the public function directly (`decide`, or the command handler).
- **"then expect events"** → `expect(...)` on the returned events — the events *are* the observable output of `decide`.

{{example: event-sourcing/decider-insufficient-funds-test}}

The starting state comes from folding factory-built events, the "action" is a direct call, and the assertion is on the returned data — behaviour through the public API, per the `testing` skill. No event bus or mocks are required. Factories keep repeated histories readable, but explicitly typed one-off inline events are equally valid. An *uncontextualized* array literal may widen its `type` discriminant to `string`; prevent that with an `AccountEvent[]` annotation or `satisfies readonly AccountEvent[]`. Test **projections** and **upcasters** the same way (they are folds and pure functions): feed events, assert on the read model or the upcast event. Full patterns — including testing the command handler against an in-memory `EventStore` fake and property-testing the fold — are in `testing-event-sourced-systems.md`.

---

## Snapshots (Briefly)

A snapshot is a stored fold result — `{ version: 240, state: {…} }` — so you can rehydrate from the snapshot plus the events *after* it, instead of from event zero. **A snapshot is a cache, never the source of truth:** delete every snapshot and the system must be identical after rebuilding them from events. Most streams are short enough that you never need one — reach for snapshots only when a stream grows large enough that replay is measurably slow, and never before.

*Measurably* is the load-bearing word, and it needs an instrument rather than an instinct: name the number of events the stream is expected to hold at its own end, and put a test on the write path that appends that many and asserts rehydration stays inside a stated budget. Then a snapshot is justified by that test failing on a stream already modelled as short as it can be — not by a suspicion, and not after a customer noticed. The same ceiling-plus-reason is what a per-query read model declares as `liveBudget`; the two escapes cancel each other, so do not take both without measuring either. See `production-concerns.md`.

---

## Anti-Patterns

- **CRUD events.** `Created`/`Updated`/`Deleted` events that mirror table writes. They record that data changed, not what happened or why, which is the one thing the log exists to keep. Model intent: `AccountOpened`, `AddressCorrected`, `AccountClosed`.
- **No versioning strategy.** Shipping v1 events with no plan for evolving them. Because events are immutable and permanent, you *will* need to read old shapes with new code — decide the tolerant-reader / upcasting strategy on day one (`event-versioning.md`).
- **Re-deciding in `evolve`.** Putting command policy in replay. `evolve` applies valid facts without business rejection, but it must surface a known event in an impossible state as corrupt history rather than silently no-op.
- **Mutable events.** "Fixing" a bug by editing or deleting past events. The fix is a new compensating event. The moment you edit history, replay is no longer trustworthy and the pattern's core promise is broken.
- **Snapshot as source of truth.** Treating snapshots as authoritative rather than a rebuildable cache. If you cannot delete all snapshots and rebuild, you have lost the event log's guarantee.
- **The event store as an integration bus.** Letting other services subscribe directly to your internal domain events couples them to your write model's shape. Publish deliberate, versioned integration events instead (the distinction is in the DDD `domain-events.md`).
- **Fat events / God streams.** Events carrying huge blobs, or one giant stream for everything instead of one stream per aggregate. Both destroy the consistency-boundary and replay-cost model.
- **Ignoring eventual consistency.** Building UIs that assume async read models are instantly up to date. Design for the lag.
- **Skipping expected version.** Appending without optimistic concurrency, so concurrent commands silently violate invariants.

---

## Checklist

- [ ] Stream identity is explicit per context, and stated as the consistency boundary it creates
- [ ] Events are past-tense, business-named, and intention-revealing — no CRUD events
- [ ] Events are self-contained data (values captured, not mutable references), modelled as discriminated unions
- [ ] Every event has an envelope (id, type, stream id, version, timestamp, correlation/causation metadata)
- [ ] Correlation and causation ids are UUIDs in types of their own, parsed at the edge, with causation genuinely optional
- [ ] `decide` holds all business rules and returns accept-with-events or reject-with-reason
- [ ] `evolve` applies every valid stored event exhaustively; impossible known transitions surface corruption rather than silently no-op
- [ ] State is rebuilt by folding `evolve`; nothing stores current state as the source of truth
- [ ] Appends use optimistic concurrency (expected version); conflicts are handled by reload-and-retry
- [ ] The event store is a driven port; the domain has zero infrastructure imports
- [ ] Stored events are validated with a schema (tolerant reader) on read, at the trust boundary
- [ ] A versioning strategy exists before the first event ships (tolerant reader and/or upcasters)
- [ ] Read models are projections (folds) that can be rebuilt from event zero via a checkpoint
- [ ] Every read model's lifecycle is a written answer — inline, async, or a per-query `live` fold that names the ceiling it holds inside and why that ceiling holds
- [ ] Projections are idempotent and the UI accounts for eventual consistency
- [ ] Snapshots (if any) are a rebuildable cache, never authoritative, and were reached because a measured replay budget failed rather than because replay felt slow
- [ ] Tests exercise public behavior through observed events/state/results; any DSL follows the repository's established test style rather than adding event-sourcing-only machinery
- [ ] PII strategy decided if events hold personal data (see crypto-shredding in `production-concerns.md`)
