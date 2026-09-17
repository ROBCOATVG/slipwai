# Domain Services

When business logic doesn't naturally belong to a single entity or value object, it belongs in a **domain service**.

## When to Use a Domain Service

- A pure decision combines domain facts or read-only snapshots that do not naturally belong to one entity
- Logic doesn't fit naturally on any single entity
- The operation is a core business concept that domain experts talk about (e.g., "pledging a contribution")

A domain service does not make a two-aggregate write atomic. If one invariant
requires two aggregates to change synchronously, reconsider the aggregate
boundary. Otherwise update one aggregate per transaction and coordinate the
other outcome through a domain event or process manager.

## When NOT to Use a Domain Service

- Logic belongs on a single entity (put it there as a pure function)
- Logic is orchestration (loading from repos, calling services, saving) — that's a use case
- Logic is presentation (formatting for display) — that's presentation code under the selected client/application structure
- Logic is infrastructure (sending emails, calling APIs) — that's integration/infrastructure code; a driven adapter only when hexagonal architecture is used

## Domain Service vs Use Case

{{example: domain-driven-design/domain-service-vs-use-case}}

## Naming

Name domain operations and use cases after the business operation: `pledgeContribution`, `transferMoney`, `placeOrder`. Never after technical patterns: `ContributionService`, `PlaceOrderUseCase`, `ShippingCalculator`. Your domain experts say "place an order", not "execute the place order use case."

You can tell a use case from a domain function by its signature, not its name:

{{example: domain-driven-design/naming-signature-domain-vs-use-case}}

Pure domain services are the default. A domain-owned driven port is a rare exception when the model itself, rather than an application use case, owns the conversation. Treat the consuming service as effectful despite keeping it provider-free, isolate the pure decision where practical, and do not move application repository or gateway orchestration into the domain under this exception.

## Testing

Test pure domain services like entity functions: pass domain values and assert the result without mocks. For the explicit port-consuming exception, test the collaboration through a small fake while keeping the underlying decision separately testable as a pure function.

{{example: domain-driven-design/domain-service-test-pledge-contribution}}
