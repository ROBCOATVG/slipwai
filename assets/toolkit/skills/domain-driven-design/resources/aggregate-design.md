# Aggregate Design

Aggregates are the hardest part of DDD to get right. Start small and tighten boundaries when you hit consistency issues.

## Design From Invariants, Not Relationships

The most common aggregate design mistake is starting from entity relationships. Developers see "Route has many Locations, Location has one VendingMachine" and build a hierarchy that mirrors this structure. The result looks domain-rich — organized entities, nested value objects, accessor methods — but conceals the absence of genuine business behavior.

**Aggregates are consistency boundaries, not containment hierarchies.** An aggregate exists to enforce invariants during state changes. If you can't name the invariant, you probably don't need the aggregate.

**The litmus test for aggregate membership:**

1. What commands change state in this area of the domain?
2. What must remain true immediately after each state change? (These are your invariants.)
3. What data is required to enforce those invariants? (Only this belongs in the aggregate.)

If the answer to #2 is only structural rules (one-to-many, one-to-one), database constraints enforce these more simply than aggregate code. Reserve aggregates for behavioral invariants — rules about what's allowed, limits, conditions, and business decisions.

{{example: domain-driven-design/invariant-driven-vending-machine}}

**Signs you have a relationship-driven aggregate:**
- Methods only add, remove, or attach children (no business rules enforced)
- No method ever returns a failure result — everything always succeeds
- The aggregate's value is "organizing" data rather than protecting correctness
- Removing the aggregate and using direct repository access would change nothing about system correctness

**Complementary heuristic — lifecycle identity:** Aggregates have lifecycles. They are "born" through domain events (a customer registers, a contract is signed, an order is placed) and eventually "die" (expiration, cancellation, liquidation). If you can identify what creates and destroys a thing, you've likely found an aggregate boundary. The birth event often reveals the root entity; the data needed for invariants between birth and death reveals what belongs inside.

## The Always-Valid Principle

An entity must satisfy its invariants at all times — after construction, after every state transition, and when retrieved from persistence.

{{example: domain-driven-design/always-valid-occasion-invariants}}

**Never allow temporary invalid states**, even in "internal" code. If an entity can be constructed without meeting its invariants, that's a bug.

## Sizing Aggregates

The most common mistake is making aggregates too large. Include only what's needed to enforce a consistency rule.

**Ask:** "Does modifying X require checking Y's state to maintain an invariant?"
- If yes: X and Y belong in the same aggregate
- If no: they're separate aggregates, referenced by ID

{{example: domain-driven-design/aggregate-sizing-occasion}}

## One Aggregate Per Transaction

Don't modify multiple aggregates in a single write operation. If a business process spans aggregates, use:

1. **One aggregate boundary** when the rule must hold atomically
2. **One aggregate write plus an outbox event** when temporary inconsistency is acceptable
3. **A process manager/saga** when cross-message state, ordering, correlation, timeouts, or deduplication are business-significant; add compensation only when that workflow needs an undo path

{{example: domain-driven-design/one-aggregate-per-transaction}}

Never model one business operation as sequential saves to two aggregates and call it eventual consistency: failure of the second save leaves a partial result with no durable instruction to finish or compensate. If contribution recording and balance deduction must succeed or fail together, redraw the aggregate/transaction boundary instead of splitting the writes.

**Data locality:** The flip side of "one aggregate per transaction" is that all of an aggregate's internals must be co-located in the same data store. Splitting an aggregate's child entities across separate databases or services forces distributed transactions to maintain consistency — defeating the purpose of the boundary. Store an aggregate's data together so it can be read, changed, and persisted atomically.

**Cross-aggregate rules are eventually consistent by default.** Any business rule that spans aggregates should not be expected to be immediately up-to-date at all times (Evans). Immediate consistency is a scarce resource — spend it only within aggregates where invariants truly demand it. Between aggregates, use domain events, batch processing, or reconciliation jobs to converge within acceptable business timeframes.

## Aggregate Root Rules

1. **External access only through the root** — never reach into child entities directly
2. **The root enforces all invariants** — children don't validate themselves in isolation
3. **Delete cascades from the root** — deleting an aggregate deletes all its children
4. **IDs are globally unique for roots** — child entity IDs only need to be unique within the aggregate

## Enforcing Boundaries in TypeScript

The rules above are meaningless without code-level enforcement. Three patterns prevent callers from bypassing the aggregate root:

### 1. Accept child IDs, not child objects

When an aggregate method operates on a child entity, accept the child's **ID** — not the entity itself. The root looks up the child internally and validates ownership. Passing a child entity object from outside leaks aggregate internals into the caller.

{{example: domain-driven-design/accept-child-id-remove-exercise}}

### 2. Create child entities through the root

Child entities should be created by aggregate root operations, not constructed externally and passed in. This ensures the root can enforce creation invariants (e.g., max items, uniqueness, ordering).

{{example: domain-driven-design/create-child-through-root}}

### 3. Expose ReadonlyArray for child collections

TypeScript's `ReadonlyArray<T>` (or `readonly T[]`) prevents callers from mutating the collection. This is the minimum boundary enforcement — callers can inspect children but cannot add, remove, or reorder them without going through root methods.

{{example: domain-driven-design/readonly-array-child-collection}}

**Together, these three patterns mean:** callers can see child entities (via `ReadonlyArray`), identify them (via IDs), and request operations on them (via root methods) — but can never construct, mutate, or remove them directly.

## When to Split vs Combine

**Split when:**
- Two things change for different reasons (different business rules)
- Performance: loading the full aggregate is expensive but you usually only need a subset
- Concurrency: multiple users modify different parts simultaneously

**Combine when:**
- An invariant spans both things (budget checking requires knowing all gift ideas)
- They always change together
- Splitting would require a complex coordination mechanism

**Start combined, split when you feel the pain.** Premature splitting creates coordination complexity worse than the performance problem it prevents. Aggregate boundaries are expected to evolve as domain understanding deepens — splitting or merging aggregates is a normal part of DDD, not a sign of failure.

## Aggregates Serve Commands, Not Queries

Aggregates exist to protect correctness during state changes. They do not exist to answer read-side questions efficiently. Separating these concerns (CQRS thinking) has a direct impact on aggregate design:

- **Commands** load the aggregate, enforce invariants, persist changes
- **Queries** read data directly — optimized views, joins, projections — without loading aggregates

**Don't let query needs inflate aggregate boundaries.** If a client needs alarm counts, last-alarm dates, or summary statistics, that's a read-model concern. Adding these as properties on the write-side aggregate conflates two responsibilities.

{{example: domain-driven-design/aggregate-vs-read-model}}

**The test:** For every piece of data in an aggregate, ask "Does any command need this to enforce an invariant?" If the answer is no — if it only exists to satisfy a read — it belongs in a read model, not the aggregate.

Domain events bridge the two sides: the aggregate publishes `AlarmTriggered` after a command succeeds, and a projection updates the read model. This keeps the aggregate small and focused on correctness.

## Concurrency: Optimistic Locking

When multiple users can modify the same aggregate concurrently, add a version field to detect conflicts:

{{example: domain-driven-design/optimistic-locking-version-field}}

The repository checks the version on save:

{{example: domain-driven-design/optimistic-locking-repository-save}}

If two users load version 3 and both try to save, the first succeeds (version
becomes 4) and the second receives `conflict`. The application maps that
expected compare-and-save outcome to its explicit `concurrent-change` result;
the driving adapter may render it as HTTP 409. Connection loss, timeouts, and
other unexpected infrastructure failures still throw. If retrying is part of
the use case, reload, re-run the domain decision, and retry the save a bounded
number of times rather than catching an exception and blindly repeating it.

**When to add optimistic locking:**
- Multiple users can edit the same aggregate
- The aggregate is long-lived (not created and discarded in one request)
- Concurrent modifications would violate invariants

**When it's unnecessary:**
- The storage operation already provides an equivalent atomic compare-and-set
  or serialization guarantee
- Fresh aggregate creation has no competing writer and handles duplicate keys
  as an explicit application outcome
- Appended facts are demonstrably commutative and unconstrained, with no stream
  head or invariant contract; this does **not** include event-sourced aggregates
