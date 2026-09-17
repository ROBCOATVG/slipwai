# Testing Event-Sourced Systems

Event sourcing is one of the most testable patterns there is: the write model is pure data in and pure data out. This resource shows how to test deciders, projections, and upcasters as **behaviour through the public API** — the `testing` skill's approach — and how that relates to the "given-when-then" idiom the event-sourcing literature reaches for.

## Why the Literature Reaches for Given-When-Then

Almost every event-sourcing text tests deciders in a **given-when-then** shape: *given* these past events, *when* this command is handled, *then* expect these new events — frequently as a fluent `given(events).when(command).then(events)` DSL (Emmett's `DeciderSpecification`, Dudycz's C# `Given/When/Then`) or as Gherkin scenarios.

It is worth understanding **why** it fits so naturally, because the reason is real: that shape *is the decider's algebra*. Past events fold through `evolve` to a state; a command runs through `decide` against that state; the output is new events. "Given events / when command / then events" is just those three moves named. The insight is genuine and worth keeping.

## Choosing the Test Expression

Follow the repository's established test style. A direct behaviour-driven expression follows the `testing` skill: call the public function, assert on the observed output, name the test after the business behaviour, and build data with factory functions. An existing given/when/then helper may encode the same algebra; do not add a new DSL only for event-sourced code. The direct form needs no extra machinery because the three moves are already plain function calls on plain data:

| The literature's idiom | Direct behaviour-driven expression |
|------------------------|------------------------------------|
| *given* past events | Build the starting state — fold event factories with `evolve`, or a state factory. Past events are just data. |
| *when* a command | Call the public function directly (`decide`, or the command handler). |
| *then* expect events | `expect(...)` on the returned events — the events **are** the observable output of `decide`. |

No event bus or mocks are required. Apply the `testing` skill to the decider, using the repository's existing helpers where they improve clarity.

## Testing the Decider

`decide` returns its events (or a rejection) as a value, so asserting on that return value is behaviour testing through the public API — the events are the observable behaviour. Build the "prior state" by folding factory-built events with `evolve`:

{{example: event-sourcing/decider-behaviour-tests}}

The starting state is a fold of factory events, the action is a direct call, and the assertion is on the returned data. Test names describe business behaviour, not the mechanics. Use factories when histories repeat or read more clearly that way. One-off inline events are fine when explicitly typed; an uncontextualized array literal may widen its discriminant, so annotate it as `AccountEvent[]` or use `satisfies readonly AccountEvent[]`. Cover the branches that matter (the `mutation-testing` skill's mutator awareness applies — avoid identity values like a withdrawal of exactly the balance unless the boundary *is* the behaviour under test).

## Testing `evolve` Through Behaviour, Not Directly

Do not write a 1:1 `evolve.test.ts` asserting each transition in isolation — that is testing an implementation detail (the `testing` skill's "no 1:1 mapping" rule). `evolve` is exercised thoroughly by the decider tests above (every one folds events through it) and by rehydration tests. If you want to pin down rehydration as a behaviour, assert on what the folded state *lets you do*:

{{example: event-sourcing/evolve-behaviour-via-withdraw-limit}}

## Testing the Command Handler With an In-Memory Store

The command handler is impure (it touches the store), so test it against an **in-memory `EventStore` fake** — a real implementation of the port backed by a `Map`, not a mock (the DDD/hex skills' "fakes, not mocks" rule). This proves load → rehydrate → decide → append works end to end, including optimistic concurrency.

{{example: event-sourcing/in-memory-event-store-fake}}

## Testing Projections

A projection is a fold, so test it as behaviour: feed a sequence of events, assert the resulting read model.

{{example: event-sourcing/projection-behaviour-tests}}

**Then prove idempotency with a redelivery**, because at-least-once delivery
permits duplicate attempts and production consumers must tolerate them. An
idempotent projector no-ops on an event it has already applied — assert the
balance does not double-count. This projector row is **scoped to one account
(one stream)**, so the stream `version` is a valid dedupe key; a projection that
folds across many streams would instead key on the **event id** or **global
position**, because versions repeat across streams:

{{example: event-sourcing/idempotent-projection-dedupe}}

## Testing Upcasters

Upcasters are pure functions from an old event shape to the next, so test them directly as behaviour (old shape in, new shape out) — and add a test that an old event, once upcast, folds correctly through the *current* `evolve`. That second test is the one that catches a versioning bug before it corrupts a replay:

{{example: event-sourcing/upcaster-behaviour-test}}

## Property-Based Testing (Optional, High Value)

Because deciders are pure algebra, they invite property tests for invariants that must hold across *any* history:

- **`evolve` covers valid history** — folding generated valid histories never throws; a separate corruption test proves an impossible owned transition does throw.
- **Rehydration determinism** — folding the same events yields the same state every time.
- **Business invariants** — e.g. after any sequence of accepted deposits and withdrawals, the balance never goes negative (because `decide` rejects overdrafts).

These complement, and never replace, the behaviour tests above.
