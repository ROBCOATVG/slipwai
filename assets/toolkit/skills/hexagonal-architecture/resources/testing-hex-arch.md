# Testing Strategy for Hexagonal Architecture

Hex arch's primary value is testability. The architecture creates natural test boundaries — but the primary boundary is the **use case**, not each layer in isolation. This approach follows Use Case Driven Development (UCDD) — see `references.md` for sources.

## A Port Is Only Real If It Is Tested

Every port needs a test interactor: a test driver at each driving port, a fake at each driven port. Without one, the "port" is an arbitrary interface line — nothing enforces it as a boundary. The tests double as the leak detector: business logic drifting into an adapter, or technology detail drifting into the domain, breaks a boundary test the moment it happens. When reviewing, ask of each port: what drives it, or fakes it, in the test suite?

## Primary Boundary: The Use Case

Test by calling the driving port implementation with driven ports replaced by in-memory fakes. This exercises the full business logic path without touching infrastructure.

{{example: hexagonal-architecture/testing-use-case-primary-boundary}}

This proves the feature works — not just that individual components return correct values.

## Fakes, Not Mocks

Replace driven ports with in-memory fakes that implement the real interface and maintain state.

{{example: hexagonal-architecture/testing-fake-order-repo}}

**Why fakes over mocks:**
- Fakes implement the real interface — if the interface changes, the fake breaks at compile time
- Fakes test behavior ("was the data saved?"), not implementation ("was `.save()` called?")
- Loosely typed mocks can drift from the real contract; typed mocks and interface-constrained stubs also catch signature changes at compile time
- Prefer stateful fakes for repository behavior. Use mocks when an interaction itself is observable behavior, without coupling tests to incidental call shape

**Note on mutability in fakes:** Fakes use encapsulated mutable state (`Map.set`, `Array.push`) to simulate a data store. That state is intentional test infrastructure and does not leak into the domain contract; the domain types they store remain immutable.

## Fakes for Instrumentation Ports (Domain Probes)

A Domain Probe (see `cross-cutting-concerns.md`, Tier 2) is a driven port, so it gets a recording fake like any other. Use-case tests then assert observations as behavior — "placing a rejected pledge announces the rejection" — the same way they assert a save happened.

{{example: hexagonal-architecture/testing-recording-fake-instrumentation}}

The probe's adapter — translating observations into log lines, metrics, or span attributes — is tested separately as adapter code (see the `observability` skill's `resources/testing-telemetry.md` for in-memory exporter patterns). Mutation-testing note: an unasserted probe call is a surviving-mutant farm; asserting observations through the fake is what makes instrumentation mutation-proof behavior.

## Domain Unit Tests: A Complement

Pure domain functions (business rules, calculations) can also be tested directly. This is behavioral testing — the domain function IS the public API. Use this for complex rules with many edge cases. For property-based testing of domain invariants with `fast-check`, see the DDD skill's `resources/testing-by-layer.md`.

{{example: hexagonal-architecture/testing-domain-unit-test-example}}

## Narrow Integration Tests: Driven Adapters

Driven adapters (repositories, API clients) need integration tests to verify they translate between domain types and infrastructure correctly. These are secondary to use case tests.

The `createTestDb` helper creates a fresh in-memory database per test:

{{example: hexagonal-architecture/testing-create-test-db-helper}}

{{example: hexagonal-architecture/testing-narrow-integration-tests}}

## E2E Tests: Proving Delivery

E2E tests (Playwright) prove the full stack works from the user's perspective. They're the final verification, not the primary testing strategy.

## The Swappability Test

The ultimate validation of hex arch boundaries: can you swap an adapter without changing domain code or use case tests?

- Swap PostgreSQL for DynamoDB → only the repository adapter changes
- Swap Stripe for PayPal → only the payment adapter changes
- Use case tests continue to pass with any adapter (they use fakes)

If any swap requires changing domain code or use case tests, the boundary is wrong.

## Strategy Summary

| Priority | What | How | Speed |
|----------|------|-----|-------|
| **Primary** | Use cases | Driving port + faked driven ports | Fast |
| **Complement** | Domain logic | Direct unit tests for complex rules | Very fast |
| **Secondary** | Driven adapters | Integration tests (real DB/MSW) | Slower |
| **Verification** | Full stack | E2E (Playwright) | Slowest |
