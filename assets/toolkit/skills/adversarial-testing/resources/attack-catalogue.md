# Attack Catalogue

Seams an event-sourced, hexagonal system actually has, with probes for each. Work top to bottom for
breadth, then go deep where the answers were vague. The principle column is the promise the probe is trying
to break — a probe with no promise behind it produces an opinion, not a finding.

Not a checklist to tick. Half of these will be inapplicable to a given slice, and the interesting finding is
usually a variation you invent after reading one of them.

---

## 1. Replay and idempotency — Principle II

The single richest seam, because at-least-once delivery is the normal case and every retry path is a chance
to do the work twice.

- Send the same command twice with the same idempotency key. Then twice **concurrently**, not in sequence.
- Send the same key with a **different payload**. Does it return the first result, reject the mismatch, or
  quietly perform the second?
- Send the same key after the first attempt **failed**. Is the failure itself now cached, so a transient
  error is permanent?
- Replay a webhook or queue message with the provider's identifier reused. Then replay one whose identifier
  is new but whose content duplicates an earlier delivery.
- Kill the process between the append and the response. The caller retries: does the retry observe the
  committed effect, or start again?
- Does the deduplication check read the **event stream**, or a read model? A read model guarding a decision
  is a Principle III violation and an eventual-consistency race.

## 2. Concurrency and version conflict — Principles II, III

- Two commands against the same stream at the same expected version. One must lose. Does the loser
  rehydrate and re-decide, or throw, or overwrite?
- Make the re-decision reject on the second pass. The first pass accepted, the retry must not.
- Make the conflict repeat. Is the retry bounded, and what does the caller see when the bound is reached?
- Append with `noStream` against a stream that now exists — the create-twice race.
- Two different commands that are individually valid and jointly violate the invariant. If the invariant
  spans streams, no expected-version check protects it: that is a process manager, not a transaction.
- Hold a connection and reach for the pool again inside the same operation. Under contention the pool
  deadlocks, and this repository has already paid for that lesson once.

## 3. Stream identity and the consistency boundary — Principle III

- Ask what the stream identity is, then find an invariant the slice enforces that spans **more than one**
  such stream. Every one you find is unprotected by optimistic concurrency.
- Push write volume at a single stream. A stream-per-tenant or stream-per-day serialises every write in it.
- Reuse an identifier across tenants or contexts. Do two unrelated entities land in one stream?
- Feed a Decider an event history that is valid for the stream but which the current code path never
  produces — an older shape, a rejected-then-accepted sequence, events in an order the stream permits but
  the tests never exercise.

## 4. Projection scoping and event-type collision — Principle III

- Write an **unrelated** stream carrying an event whose `type` collides with one the projection folds. Does
  the projection consume it? A fold over the whole log will.
- Deliver events out of order, then duplicated, then both. Projections must be idempotent per position.
- Rebuild the projection from position zero and diff against the live one. Any divergence is a defect in
  one of them.
- Deliver an event type the projection has never seen. Crash, silent skip, or poison-pill loop?
- Read the projection immediately after the command returns. If the criterion promises the caller can see
  it, eventual consistency has just broken that promise.
- Read a projection whose position lags far behind. Is staleness observable to the caller, or invisible?

## 5. Schema evolution and the tolerant reader — Principle VIII

- Append an event carrying an **extra** unknown field, then read it. A strict parser here means the next
  additive change breaks the reader.
- Read an event written by the *previous* schema version. Is there an upcaster, and is it exercised by a
  test with a real old-shape payload rather than a synthesised one?
- Read an event whose `schemaVersion` is **higher** than this deployment knows — the rolling-deploy case,
  where the old version must tolerate what the new one writes.
- Look for anything that rewrites, deletes, or migrates a stored event. Prohibited outright.
- Check whether a removed or retyped field left readers folding over a field that is now absent.

## 6. Boundary parsing and untrusted input — Principles IV, IX

The driving adapter is the only place untrusted data becomes typed. Everything it lets through is a domain
problem forever.

- Unknown fields in a request body: rejected, or silently stripped and forgotten?
- A **client-supplied actor, user, or tenant identifier** on a request the session already identifies.
  Forged-actor input, and the schema should not declare the field at all.
- Numbers where the domain means money: floats, negatives, zero, `1e309`, `-0`, `"10.00"` as a string,
  a currency mismatch between amount and account. Principle I bans floating point in any monetary value.
- Strings at the size limit and past it. Unicode normalisation, combining characters, right-to-left
  overrides, embedded NUL, newlines in a value that ends up in a log line.
- Arrays where one element is expected, `null` where a string is, `{}` where an array is, deeply nested
  objects, duplicate JSON keys.
- Timestamps supplied by the caller: far future, far past, non-UTC, no offset. Does the domain use them, or
  its injected `Clock`?
- An identifier that is well-formed but belongs to another tenant. Cross-tenant access must return
  **not-found**, never forbidden — existence is not leaked.

## 7. Authorisation — Principle IX

- Call every endpoint with no credential, an expired one, and one belonging to a different tenant.
- Authorisation enforced in the driving adapter only: find a second entry point to the same use case that
  bypasses it. Principle IX requires the check **inside the application**.
- Escalate through a read model — a view that returns rows the caller may not read, or that reveals
  existence through a count, a total, or a distinct error.
- Guess an identifier. Sequential or predictable identifiers plus a missing tenancy check is a full
  enumeration.
- Act on behalf of another subject where the operation legitimately allows it. Is the actor recorded as the
  operator, or as the target?

## 8. Time — Principles III, VII

- Make the injected clock go **backwards**, and make two calls return the same instant.
- Order anything by timestamp rather than by stream version or global position. Ties and skew break it.
- Cross a DST boundary, a leap second, and midnight in a timezone that is not the server's.
- Expire something exactly on its boundary instant: is the comparison inclusive on the side the domain
  intends?
- Find a `Date.now()`, `Math.random()`, or `crypto.randomUUID()` inside the domain. ESLint bans them, so a
  survivor means the value arrived through an adapter that should have injected it.

## 9. Partial failure of driven adapters — Principles IV, VI

- Fail each port in turn: unavailable, timing out, slow, returning a malformed payload, succeeding after
  the caller gave up.
- The append succeeds and the process dies before the response. Then before a downstream side effect. Then
  after it but before it is recorded.
- The side effect succeeds and its acknowledgement is lost, so it is retried. Is the *provider* idempotent,
  or only this code?
- Does the port's fake simulate these failures at all? A fake that cannot fail leaves every failure path
  untested, and Principle IV requires the fake to be usable, not merely present.
- Exhaust the connection pool while a request is in flight.
- Check what a failure leaks: a stack trace, a provider error string, a SQL fragment, an internal
  identifier.

## 10. The Decider's contract — Principles III, V

- Find a path where `decide` returns both events and a rejection, or neither.
- Find an accepted decision that produces an **empty** event list. What did the caller observe?
- Find a rejection with a side effect — a log write that matters, a mutated input, a cached value.
- Mutate the input command object after `decide` returns, and the state object during `evolve`. Shared
  mutable state across a fold is a class of bug the type system will not catch.
- Feed `evolve` an event the current `decide` cannot produce but the stream may contain.

## 11. Personal data and erasure — Principle IX

- Find personal data embedded in an event payload rather than referenced. Events are permanent, so this is
  a right-to-erasure problem that only gets more expensive.
- Ask how a subject's data is erased without deleting or rewriting an event. If the answer is designed
  after the fact, it is already too late; the mechanism must exist before the first such event is written.
- Grep the logs a request produces for anything identifying. Correlation identifiers, yes; personal data,
  never.

## 12. Operational surface — Principles VII, XII

- Does a failing background job look different from an idle one? A missing heartbeat must itself be
  alertable.
- Is a correlation identifier propagated across every hop, including the projection and the job — or does
  the trail stop at the HTTP boundary?
- Would the promised detection actually fire, or is there only an endpoint someone could look at once told?
- Start the process with a required environment variable missing, then present but empty, then malformed.
  Does it refuse to start, or serve traffic in a half-configured state?
- Run the migration against a database at the previous application version. Expand and contract must not
  ship in one deployment.
