# Worked Example: Full Request Lifecycle

One feature traced through every role, showing how hex arch and DDD fit together in practice. The paths use an illustrative capability-first monorepo shape. They are not a universal directory template; the invariant is bounded context or business capability before technical layer.

**Feature:** "Pledge a contribution to an occasion's gift fund"

## 1. Glossary

| Term | Definition |
|------|-----------|
| Occasion | A gift-giving event (birthday, holiday) |
| Contribution | Money pledged toward an occasion's gift fund |
| Contributor | A person who pledges money |

## 2. Domain Types

```text
packages/
  gifting/
    hexagon/
      domain/
        src/
          types.ts          ← types + branded IDs
          occasion.ts       ← entity functions
          pledge.ts         ← aggregate operation + domain event
```

{{example: hexagonal-architecture/worked-example-domain-types}}

## 3. Domain Function (Pure Business Rule)

{{example: hexagonal-architecture/worked-example-domain-function-record-pledge}}

No ports, no infrastructure, no async. One aggregate changes, and the domain returns the event that describes the accepted pledge.

## 4. Port Interfaces (Inside Application Boundary)

{{example: hexagonal-architecture/worked-example-port-interfaces}}

## 5. Use Case (Orchestration)

{{example: hexagonal-architecture/worked-example-use-case-orchestration}}

The use case implementation is identifiable by its dependencies — it takes an
application-owned driven port and returns the driving port interface. This
operation's policy permits any authenticated pledger, so the provider-free
principal is both the authorization precondition and the source of the recorded
actor; the body cannot forge it. A narrower product rule would be checked here
before `recordPledge`. The use case loads one versioned aggregate, delegates to
the aggregate operation, and requests one atomic compare-and-save plus outbox
write. A concurrent change becomes an explicit application outcome instead of
a lost update.

The outbox worker retries delivery, so `PledgeRecorded` can arrive more than once. `PledgeProjection` accepts records from a validated immutable log where the same event ID permanently identifies the same payload; `recordFrom` inserts the first occurrence and ignores an identical redelivery. If an adapter cannot rely on that boundary contract, it must compare a canonical payload fingerprint and surface same-ID/different-payload corruption. Another handler that performs a side effect needs an equivalent idempotency key or inbox record. Transaction mechanics remain in the driven adapter — see `cross-cutting-concerns.md`.

## 6. Driven Adapters

```text
packages/gifting/adapters/driven/postgres/src/
  drizzle-pledge-persistence.ts
  drizzle-pledge-projection.ts
  schema.ts
```

{{example: hexagonal-architecture/worked-example-driven-adapters}}

The persistence adapter translates between domain types and database rows, and implements the application's atomic optimistic `saveWithOutbox` contract with one transaction. The version predicate prevents two readers from overwriting each other; a conflict inserts no outbox row. A successful call saves one aggregate plus durable delivery instructions — never a second aggregate. Under the validated immutable-event contract, the projection adapter makes redelivery idempotent by inserting on `eventId` and doing nothing on conflict; it never overwrites an existing event's projection with incoming data. Neither adapter contains business logic.

## 7. Driving Adapter at a Serverless Executable Entry Point

```text
packages/gifting/adapters/driving/http/src/occasions/by-id/pledge/post.ts
```

{{example: hexagonal-architecture/worked-example-driving-adapter-entrypoint}}

This deliberately small serverless handler combines a driving adapter with inline composition because it is the executable deployment entrypoint and its graph is trivial. Keep those roles visibly separate in the file. The narrowly scoped JSON parse maps malformed transport syntax to `400`; the path and body schemas map syntactically valid but invalid request data to `422`. Authentication still supplies the actor, and domain results retain their separate `404`/`409`/`422` mappings. An ordinary route module receives a prepared application capability and only parses → delegates → translates. When several endpoints share an object graph, configuration families, or resource lifecycle, move wiring into the host's explicit `composition/` directory. The status selection here is protocol translation, not business policy.

## 8. Fakes for Testing

{{example: hexagonal-architecture/worked-example-fakes-for-testing}}

Fakes implement the real interface and maintain state. If the interface changes, the fake breaks at compile time.

A fake is a driven *actor* that needs no adapter — it meets the port interface directly. It lives outside the production hexagon under `testing/fakes/`, separate from concrete production adapters.

## 9. Tests

### Use Case Test (Primary)

{{example: hexagonal-architecture/worked-example-use-case-test}}

One test file covers the use case, the aggregate operation, atomic persistence intent, and idempotent event handling. No mocks. The tests describe business behavior and delivery guarantees, not call order.

### Domain Unit Test (Complement)

{{example: hexagonal-architecture/worked-example-domain-unit-test}}

Direct domain tests complement use case tests for complex rules with many edge cases. This function is pure — no setup, no fakes, just values in and values out.

## File Map

```text
packages/
  gifting/                                      ← BOUNDED CONTEXT / CAPABILITY
    hexagon/                                    ← INSIDE
      domain/
        src/
          types.ts                  ← domain types and branded IDs
          occasion.ts               ← entity functions
          pledge.ts                 ← aggregate operation + domain event
          pledge-rules.test.ts
      application/
        src/
          pledging.ts               ← driving port + application result
          pledge-persistence.ts     ← application-owned atomic driven port
          pledge-projection.ts      ← application-owned idempotent driven port
          pledge-to-occasion.ts     ← use case orchestration
          pledge-recorded-handler.ts ← idempotent event handler
          pledge-contribution.test.ts
    adapters/                                   ← OUTSIDE
      driven/postgres/src/
        drizzle-pledge-persistence.ts
        drizzle-pledge-projection.ts
        schema.ts
      driving/http/src/occasions/by-id/pledge/
        post.ts
    testing/                                    ← OUTSIDE TEST INTERACTORS
      fakes/src/
        fake-pledge-persistence.ts
        fake-pledge-projection.ts
        test-factories.ts
```

## What Lives Where (Summary)

| What | Where | Why |
|------|-------|-----|
| Business rules | `<capability>/hexagon/domain/` pure functions | Testable without infrastructure, the core value |
| Application policy and ports | `<capability>/hexagon/application/` | Use cases own their repository/gateway abstractions |
| Persistence/projection implementations | `<capability>/adapters/driven/` | Driven adapters translate domain ↔ DB and implement atomicity/idempotency contracts |
| Route handlers | `<capability>/adapters/driving/` | Driving adapters remain thin glue |
| Fakes | `<capability>/testing/` | Outside in-memory actors shared across use-case tests |
| Focused tests | Colocated with inside behavior | Organized by behavior and protected from implementation coupling |
| Concrete wiring | `composition/` or this tiny route entrypoint | Only the executable host selects implementations |
