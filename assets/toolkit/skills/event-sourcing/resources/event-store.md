# The Event Store and Storage

The event store is the append-only, ordered, optimistic-concurrency-aware persistence for streams. In hexagonal terms it is a **driven port** with an adapter — the application command handler depends on the interface, not the technology. This resource covers the port, a concrete Postgres implementation, the event envelope, serialization, and the TS/Node tooling landscape.

## Two Consistency Boundaries, and Which One This Project Guards With

Read this before the port below, because everything after it is written in terms of one of the two answers.

A guard on an append has to hold something still. **Stream-per-aggregate** holds one stream: you read it,
decide, and append at the version you read, and the store refuses the write if that version moved. It is
what this project's `EventStore.append` does, what every slice generated here uses, and the default this
factory keeps.

**A Dynamic Consistency Boundary** (Sara Pellegrini, "Killing the Aggregate") holds something the caller
draws per decision instead: a query over *tagged* events, plus the store position it was read at. The
append is refused if anything matching that query arrived since. It exists because some constraints do not
fit inside one stream — a course's capacity and a student's own subscription count, checked together, where
either can change under you — and stream-per-aggregate can only express that with a process manager and an
apology.

The two are not rivals here, and the log carries both:

- **A tag is the more general of the two.** Stream-per-aggregate is the case where every event carries
  exactly one tag, `stream:<streamId>` — which is literally what the default tagging function returns.
- **Tags live in a derived index**, `event_tags`, written inside the append's own transaction and
  rebuildable from the log at any time. The `events` table is untouched by the feature, which is the only
  reason a project already in production can adopt it: an append-only log cannot be backfilled, and a
  derived index does not need to be.
- **Tags are never modelled; identity is.** A tag comes from a function over the event, and nothing in
  the event model names one, because a tag is a technical index and not a fact about the business. What
  the model *does* carry is which of an event's attributes identify something — `attributes:` on an `evt`
  frame, each with the kind it identifies — and the tagging function is the transcription of that:

  {{example: event-sourcing/tags-of-from-identifying-attributes}}

  Two attributes may identify the same kind, and that case is the reason `identifies` names a kind
  rather than being a flag: a transfer carries two `hold:` tags and a query for either finds it. An
  index that mapped one kind to one attribute cannot express a transfer at all, and asking it "which
  hold?" has no answer.
- **Postgres pays for the conditional append with `SERIALIZABLE`**, not with a clever `WHERE NOT EXISTS`:
  the guard is the *absence* of rows, and absence is not something a row lock can hold. A serialisation
  failure at commit is reported to the caller as the same conflict a stale version would be, and asks the
  same next move — read again, decide again.
- **The boundary is pinned once, before the reads.** A decision that needs two queries — the course and
  the student — asks the store for its `head` first and passes it to both reads as `until`. Without that,
  each read hands back its own head and a caller guarding with the second one has promised something it
  never checked: an event matching the first query could have arrived between the two reads, *before* that
  head, and the conditional append would not look for it. The store's port carries `head()` and the
  ceiling for exactly this, and the contract suite has the case.
- **And that boundary is a *settled* position, not merely the newest visible one.** On Postgres a position
  is handed out at insert and revealed at commit, so two appends take 5 and 6 and 6 can commit first. A
  decision that read a head of 6 while 5 was invisible is guarded from *after* 6 — and 5, the event that
  should have refused it, sits below its own boundary where the guard never looks. So `head` waits for the
  appends in flight, which both settles the boundary and makes the read that follows see the event. This
  is the same protocol the read side uses to stop a projection skipping an event, and it is proved on the
  write path by an integration test that claims one seat twice without it.
- **Both conflicts are values, not exceptions**, for the reason the next section gives.

Which to use is a per-slice decision and a small one: `append` unless the constraint genuinely spans
entities. What is *not* a small decision is whether the log records tags at all, because that answer is
only cheap before there is history — which is why this factory decided it once, in
`docs/adr/0001-a-dcb-capable-log.md`, and generated it into every project.

## What an Event Store Must Provide

Every event store, whatever the backing technology, must offer four capabilities:

1. **Append-only writes** — events are inserted, never updated or deleted.
2. **Ordering within a stream** — a stream's events have a strict, gapless per-stream version.
3. **Optimistic concurrency** — appends assert an *expected version* and are rejected on mismatch.
4. **Read a stream** — load an aggregate's events (forward, optionally from a version) to rehydrate it.

Production stores add **global ordering** (a store-wide monotonic position for projections) and **subscriptions** (catch-up and/or persistent) so read models can follow the log. Greg Young's minimal framing: an event store *"at its simplest level has only two operations"* — append events for an aggregate, and read events for an aggregate; the get-by-id read is *"the only query that should be executed by a production system against the Event Storage."*

## The Port

Define the port beside the application command handler that consumes it, using application language. Keep it small; model expected concurrency failure as a **returned value**, not a thrown exception (per the error-modelling rule):

{{example: event-sourcing/event-store-port-interface}}

Typing the port to `E` (rather than a per-call `readStream<E>`) keeps call sites cast-free and gives each command handler a view over one aggregate's event family. `version` is the stream's current version — the number of events it holds. A brand-new stream is version `0`; append with `expectedVersion: 0` to require it not yet exist. Some libraries (Emmett, KurrentDB) **throw** a `ConcurrencyError`/`WrongExpectedVersionException` instead of returning a status; if you adopt one of those, translate the throw into a result at the adapter boundary so the domain stays exception-free for expected outcomes.

A fuller port adds `subscribe`/`readAll` for async projections — keep those on a separate port so a use case that only writes does not depend on subscription machinery.

## A Postgres Event Store

Postgres is the pragmatic default: a stream-head row for compare-and-swap, an append-only event table, and transactional appends. This version also uses a transactional global counter so a projection's scalar checkpoint follows commit order:

```sql
CREATE TABLE event_stream (
    stream_id  uuid PRIMARY KEY,
    version    int NOT NULL CHECK (version >= 0)
);

CREATE TABLE event_store_position (
    singleton  boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    position   bigint NOT NULL CHECK (position >= 0)
);
INSERT INTO event_store_position (singleton, position) VALUES (true, 0);

CREATE TABLE event (
    global_position  bigint      NOT NULL,           -- commit-ordered projection cursor
    id               uuid        NOT NULL,           -- unique event id (idempotency + causation target)
    stream_id        uuid        NOT NULL REFERENCES event_stream (stream_id),
    version          int         NOT NULL CHECK (version > 0),
    type             text        NOT NULL,           -- event type name, e.g. 'MoneyDeposited'
    data             jsonb       NOT NULL,           -- domain payload
    metadata         jsonb       NOT NULL,           -- envelope: correlation/causation (UUIDs), etc.
    logged_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (global_position),
    UNIQUE (stream_id, version),                      -- defence in depth for gapless stream order
    UNIQUE (id)                                       -- event id unique store-wide (dedupe + causation)
);
```

**`expectedVersion` must compare the actual stream head and append atomically.** Merely inserting at `N+1` behind a unique constraint rejects a stale-low expectation, but a stale-high expectation could create a gap. The adapter rejects empty batches, then performs this compare-and-swap and the inserts in one transaction:

```sql
BEGIN;

INSERT INTO event_stream (stream_id, version)
VALUES ($stream_id, 0)
ON CONFLICT DO NOTHING;

UPDATE event_stream
SET version = version + $event_count
WHERE stream_id = $stream_id AND version = $expected_version
RETURNING version;
-- Require exactly one returned row. Otherwise ROLLBACK and return 'version-conflict'.

UPDATE event_store_position
SET position = position + $event_count
WHERE singleton = true
RETURNING position;
-- The returned value is this batch's final global position. This row remains
-- locked until COMMIT, so a later position cannot commit first.

-- Insert every row at stream versions expectedVersion+1..newVersion and at
-- global positions endPosition-eventCount+1..endPosition.
INSERT INTO event (global_position, id, stream_id, version, type, data, metadata)
VALUES ($global_position, $id, $stream_id, $version, $type, $data, $metadata);

COMMIT;
```

The counter makes a monotonic projection checkpoint commit-safe and gapless, but it serializes global-position allocation. If that becomes a measured bottleneck, use a store with a guaranteed commit cursor or retain sequence-assigned positions only with a gap-aware subscription plus a safe committed watermark; never advance a scalar checkpoint past a missing `bigserial` value, because that earlier transaction may still commit. A `write_message`-style stored function (message-db, Marten) can centralize the same stream-head compare-and-append guarantee server-side.

## The Event Envelope

Separate the **domain payload** from the **envelope** of storage/tracing metadata. A good stored shape:

{{example: event-sourcing/event-envelope-type}}

**Correlation vs causation** is the pair that makes an event log traceable, and the rule (Greg Young, popularised by Arkency) is precise:

> *"If you are responding to a message, copy its correlation id as your correlation id, its message id is your causation id."*

So when a handler emits new events in response to an incoming message: `correlationId` = the incoming message's correlationId (or, if it is the first, its own id) — this lets you see an entire business transaction; `causationId` = the incoming message's id — this lets you reconstruct the exact causal tree of what caused what. EventStoreDB/KurrentDB and Marten both surface `$correlationId`/`$causationId` as first-class metadata, so this is the de-facto standard.

**Make both of them UUIDs, and give each its own type.** Two decisions, and they are separate:

*A UUID, not a free string.* These ids are written by one service and read by another, often years later by a tool nobody has written yet. They must be unique without a registry, parse the same everywhere, and be impossible to confuse with something else — which a UUID is and `"checkout"`, a request path, or an order reference is not. It also stops the failure that a text column invites: an id that is empty, or that means one thing in one service and something else in the next. Where the store has a native type — Postgres' `uuid`, which is 16 bytes rather than 36 characters and rejects a malformed value at the door — use it; SQLite and JSON metadata keep the canonical lower-case text form, and the adapter is where that difference stops.

*Its own type, not a bare UUID.* Correlation and causation sit side by side in every envelope and are the same shape underneath, so swapping them compiles, runs, and produces a causal tree in which everything appears to have caused itself. A wrapper — a branded type, a `NewType`, a one-field record — makes the swap a compile error and costs a line. `causationId` is **optional**, and genuinely so: the first message in a transaction has no cause to point at, and inventing one is a lie about the shape of the tree.

Parse text into these types at the edge — the HTTP header, the queue message, the stored row — and once, so everything above the edge holds an id that has already been checked. That is the tolerant reader below applied to the envelope rather than the payload.

## Serialization and Validation on Read

Events are stored as JSON (`jsonb` in Postgres) with the **type name travelling as a string**, not a language type — that string is what lets you deserialize tolerantly and evolve versions. On the way in, stored events are untrusted data crossing a trust boundary, so **validate them on read** before `evolve` ever sees them. The order matters: **validate first, then upcast.** Parse the raw record against a *tolerant* schema for the shape that was actually persisted (possibly an old version), then run upcasters on that validated value to reach the current shape — so the upcaster never receives unchecked JSON. This is the **tolerant reader**, and it is exactly the `typescript-strict` rule of schema-first at boundaries, plain types inside.

{{example: event-sourcing/tolerant-reader-read-path}}

Never let unvalidated stored JSON flow into an upcaster or into `evolve`; a single malformed row would otherwise corrupt every rehydration of that stream.

## The TS/Node Tooling Landscape

Choose deliberately; the space is young and moving. Balanced summary as of this writing — **verify versions and licences before adopting**:

- **Emmett** (`@event-driven-io/emmett`, Oskar Dudycz) — "event sourcing made simple" for TS/Node. Gives you the `Event`/`Command` types, the Decider trio, a `CommandHandler` wrapping read→decide→append, an `EventStore` abstraction (`readStream`, `aggregateStream`, `appendToStream` with `expectedStreamVersion`), and projections. Pluggable stores: in-memory, PostgreSQL, EventStoreDB, MongoDB, SQLite. **Caveats:** pre-1.0 (the API still moves) and the **licence is unresolved** (an open RFC around AGPLv3/SSPL). Best when you want idiomatic, low-boilerplate deciders with pluggable storage.
- **EventStoreDB / KurrentDB** — the purpose-built, event-native database with server-side subscriptions and projections. The Node client is `@kurrent/kurrentdb-client` (1.x, GA — the rebrand of the legacy `@eventstore/db-client`; construction went connection-string-only at v1, and symbol names like `expectedRevision`/`NO_STREAM` differ across the rebrand, so pin the client and follow its current docs rather than older samples). Best when you want a managed event-sourcing-first store rather than hand-rolling on Postgres.
- **message-db** (Eventide) — an event store that is *just* a Postgres schema plus SQL functions (`write_message` with `expected_version`, `get_stream_messages`, `get_category_messages`). Mature and language-agnostic; richest client tooling is Ruby, so from Node you call the SQL functions directly. Best when you want a well-specified SQL contract on plain Postgres.
- **Marten** (.NET, Postgres) — **reference design only**, not TS. The most mature open-source Postgres event store; excellent to mine for schema (`mt_events`/`mt_streams`), inline/async projections, correlation/causation metadata, and concurrency handling.
- **DynamoDB single-table** (AWS) — a well-supported serverless pattern: table keyed by aggregate id + version, **optimistic concurrency via a conditional write** on the version attribute, fan-out via DynamoDB Streams. You hand-roll more (no built-in fold, no gapless global position). Best for serverless AWS-native stacks.

For most TypeScript projects the honest default is **Postgres** (the table above, or via Emmett/message-db) until scale or an explicit event-native requirement justifies KurrentDB. Do not adopt a pre-1.0 library or an unresolved licence into a long-lived system without a deliberate decision.
