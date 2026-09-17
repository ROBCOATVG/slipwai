---
name: domain-driven-design
description: Domain-Driven Design patterns for TypeScript. Use when implementing ubiquitous language, value objects, entities, aggregates, domain events, domain services, or bounded contexts. Only applies to projects that explicitly use DDD. Do NOT use for simple CRUD or projects without domain modeling.
---

# Domain-Driven Design (DDD)

This skill applies only to projects that have opted in to DDD. Do not apply these patterns to projects that use a different approach.

For hexagonal architecture (ports and adapters), load the `hexagonal-architecture` skill. DDD and hexagonal architecture are complementary but independent — a project may use one without the other.

Use the `structure-codebase` skill when designing or changing physical placement. It keeps bounded context, feature/use-case cohesion, package enforcement, and any opted-in hexagonal inside/outside boundary as separate structural axes. If physical restructuring is not requested, preserve the repo's existing layout while keeping domain logic isolated.

**Deep-dive resources** are in the `resources/` directory. Load them on demand:

| Resource | Load when... |
|----------|-------------|
| `aggregate-design.md` | Designing or splitting aggregates, sizing questions, optimistic locking |
| `domain-services.md` | Unsure if logic is a domain service vs use case, naming conventions |
| `domain-events.md` | Cross-aggregate coordination, Decider pattern, event dispatch (outbox), process managers |
| `bounded-contexts.md` | Drawing context boundaries, integrating with external systems (ACL), context mapping |
| `modelling-process.md` | Starting DDD on a new or legacy system and unsure where to begin — the DDD Crew's eight-step process from business model to code, and which tool fits each step |
| `error-modeling.md` | Deciding between result types and exceptions, error propagation |
| `testing-by-layer.md` | Writing tests for DDD code, property-based testing for invariants |
| `references.md` | Checking focused source rationale for DDD, layer ownership, and testing |

For authoritative sources, see `resources/references.md`.

---

## When to Use DDD

DDD adds value for **complex domains** with rich business rules. Not every project needs it.

**Use DDD when:**
- Domain has complex business rules and invariants
- Multiple stakeholders with domain expertise
- Business logic is the core differentiator
- Terms have specific, important meanings

**Don't use DDD when:**
- Simple CRUD with no business rules
- Technical/infrastructure-focused projects
- No domain expert to consult

**Not sure where to begin?** `resources/modelling-process.md` walks the eight steps from understanding the business model to coding the domain — with the workshop and canvas that fits each step — for a greenfield project, a brownfield migration, or a team re-organisation.

**Start simple and evolve:** Begin with ubiquitous language (glossary) and value objects. Add aggregates, domain events, and bounded contexts only when the domain demands it. Your first model will be wrong — that's fine. The goal is to learn quickly and refactor toward deeper insight.

---

## Core Principle

**The code must speak the language of the domain.** The repository's declared glossary is the naming authority for each bounded context. When naming a declared concept, use its canonical spelling and capitalization in types, functions, variables, and tests. A concept absent from the glossary is not automatically approved or forbidden; it is not yet agreed. Plans, research, comments, conversations, and existing code may reveal candidate vocabulary, but they cannot silently canonize it.

**Domain models evolve.** The first model is never the final model. As understanding deepens through conversations with domain experts and building working software, the model should change — types get renamed, aggregates get split or merged, new concepts emerge. This is expected and ideal. A model that never changes is either perfect (unlikely) or stagnant (the team stopped learning). TDD and behavioral tests make this evolution safe — rename a concept, update the glossary, and the tests tell you what needs to change.

---

## Where Does This Code Belong?

This is the most common decision in DDD. When unsure, use this framework:

The roles below are logical placement guidance. Use `structure-codebase` to choose their physical folders and packages.

| Question | If yes → | If no ↓ |
|----------|----------|---------|
| Does it enforce a business rule or compute a business value? | Domain policy (entity function, value object, or domain service) | ↓ |
| Does it orchestrate domain operations without owning the rules? | Application policy / use case | ↓ |
| Does it format, transform, or prepare data for display? | Presentation code; in hexagonal architecture, often at the driving edge | ↓ |
| Does it talk to an external system (DB, API, file system)? | Infrastructure/integration code; in hexagonal architecture, a driven adapter implements an inside-owned port | ↓ |
| Is it framework-specific glue (route handler, middleware)? | Framework entrypoint; in hexagonal architecture, a driving adapter | — |

**The purity test is necessary but not sufficient.** A pure function that formats a date for display does not belong in domain policy just because it's pure. The question is always: "Is this a business rule?"

{{example: domain-driven-design/purity-test-domain-vs-presentation}}

**Why placement matters:** Domain-policy code typically has strict coverage requirements and zero infrastructure imports. Putting code in the wrong role creates unnecessary testing obligations and architectural violations.

When `structure-codebase` has been applied, enforce domain and any visible hexagonal boundary mechanically with its package/import rules.

When an architecture uses ports, ownership follows the innermost consumer that needs the abstraction. Repository and gateway ports are therefore normally application-owned because use cases consume them. A port belongs in domain only when the domain model itself genuinely consumes that abstraction. "Inside-owned" does not mean "domain-owned."

Keep domain policy free of frameworks, transport and persistence types, clocks, UUID generators, vendor SDKs, and UI concerns. Parse external input at the edge; pass current time, identifiers, and other external facts into domain functions as typed values. Application use cases coordinate those functions and any required ports.

---

## Ubiquitous Language & Glossary

DDD projects must maintain a repository-declared glossary that defines agreed domain terms. It is the naming authority for its bounded context. The glossary evolves as the model evolves — when the team discovers a better name or splits a concept, decide and record the change before code follows.

### The Glossary File

For projects with multiple bounded contexts, organize by context. The same term may have different definitions in different contexts — this is correct, not a bug.

```markdown
## Gifting Context

| Term | Definition | Examples |
|------|-----------|----------|
| Occasion | A gift-giving event (birthday, holiday) | "Mum's Birthday", "Christmas 2026" |
| Gift Idea | A potential gift for an occasion | "Cookbook", "Scarf" |
| Contribution | Money pledged toward a gift | "£25 from Dad" |

## Notifications Context

| Term | Definition | Examples |
|------|-----------|----------|
| Occasion | An upcoming event that may trigger reminders | (same events, different concern) |
| Recipient | The person being gifted — target of reminder scheduling | "Mum" |
```

### Enforcement Rules

- Use the canonical spelling and capitalization whenever naming a declared concept.
- Treat an absent term as a candidate requiring agreement, not as automatically approved or forbidden.
- Rejected or deprecated aliases must point to the owning bounded context and canonical replacement.
- Apply glossary checks to `type` and `interface` names, function names, and test descriptions within the check's declared scope.
- Treat a green language-lint command as evidence for its targeted ratchet only, never as proof that every prose passage and identifier uses the ubiquitous language correctly.

{{example: domain-driven-design/ubiquitous-language-glossary-types}}

---

## Building Blocks

### Value Objects

Immutable, identity-less, compared by their attributes (not by reference). Represent domain concepts defined by their attributes. Two `Money` values with the same minor units and currency are equal — value objects have no identity.

{{example: domain-driven-design/money-value-object-factory}}

Store and calculate money in integer minor units, never binary floating-point major units. A boundary that accepts decimal text must use the currency's exponent and an explicit policy for excess precision (for example, reject it or round half-even); never convert with `Math.round(rawNumber * 100)`.

For value objects crossing trust boundaries (API input, form data), use Zod schemas. For domain-internal value objects, plain types + factory functions suffice. See the `typescript-strict` skill for schema-first patterns.

**Zod-to-branded-type bridging** — parse raw input into branded domain types at trust boundaries:

{{example: domain-driven-design/zod-branded-type-bridging}}

Reconstitution (rebuilding domain objects from DB rows) uses the same factory functions as creation. The factory validates, so invalid persisted data is caught on read rather than silently corrupting the domain.

### Branded Types

The branded type pattern itself is covered by the `typescript-strict` skill — load it for the general rules. The DDD-specific application:

- **Give every entity its own branded ID** (`OccasionId`, `GiftIdeaId`) so the compiler rejects cross-entity ID mixups — passing a `GiftIdeaId` where an `OccasionId` is expected is a compile error, not a runtime bug.
- **Brand only through validating factory functions** — raw strings become branded values only after validation. The `as` assertion inside such a factory is the one justified exception: validate first, then brand.
- Use branded types for entity IDs and single-value value objects (`EmailAddress`).

{{example: domain-driven-design/branded-id-types}}

### Entities

Have identity and a lifecycle. Always valid after construction or state transition.

{{example: domain-driven-design/entity-rename-occasion}}

**Always-valid principle:** An entity must satisfy its invariants at all times. Validate on construction (factory functions or schema parsing) and on every state transition. Never allow an entity to exist in an invalid state, even temporarily.

### Make Illegal States Unrepresentable

General type-safety patterns (contained `any` only at unavoidable interop boundaries, discriminated unions, schema-first validation) live in the `typescript-strict` skill. The DDD-specific application: model entity **lifecycles** as discriminated unions where each variant carries only the data valid for that state — never boolean flags plus optional fields, which allow contradictory combinations like `{ isVerified: true, verifiedAt: undefined }`:

{{example: domain-driven-design/order-lifecycle-union}}

**Always handle all lifecycle variants exhaustively.** The `never` type ensures the compiler catches unhandled states when you add a new variant:

{{example: domain-driven-design/describe-order-exhaustive-switch}}

### Aggregates

Clusters of entities and value objects with a single root. All modifications go through the root.

1. **One aggregate root per transaction**
2. **Reference other aggregates by ID** — never embed
3. **All invariants enforced by the root**
4. **Keep aggregates small** — only what's needed for consistency

For detailed aggregate design guidance, see `resources/aggregate-design.md`.

### Specifications (Predicate Functions)

Complex business rules for filtering, eligibility, or validation are expressed as predicate functions in the domain layer. Evans calls these "specifications."

{{example: domain-driven-design/specification-can-pledge}}

Specifications are pure predicate functions — they return `boolean` and have no side effects. Use them in domain services, use cases, and query filters. Name them with `is`, `can`, or `has` prefixes.

### Domain Events

Domain events represent something meaningful that happened in the domain ("OrderPlaced", "ContributionPledged"). They coordinate side effects across aggregates and bounded contexts.

**Domain events earn their complexity when:**
- Side effects cross aggregate boundaries
- Other bounded contexts need to react to changes
- You need an audit trail or event-driven workflows

**Don't add domain events when:**
- All logic is within a single aggregate
- Side effects are within the same transaction
- Explicit return values from domain functions suffice

For most projects, start without domain events and add them when the domain demands coordination. See `resources/domain-events.md` for the Decider pattern and detailed guidance. When events become the source of truth — persisted to an append-only log and replayed to rebuild state — that is event sourcing; load the `event-sourcing` skill (it builds directly on this Decider). Where domain events already exist, observability rides for free as another subscriber — an observability adapter on the existing publisher port, not a second announcement channel (see the `hexagonal-architecture` skill's four-tier observability model and the `observability` skill).

---

## Domain Services

When business logic doesn't belong to a single entity, it belongs in a **domain service** — a stateless function in the domain layer that combines domain values or read-only policy facts. A domain service does not make multi-aggregate writes atomic: redraw the aggregate when one invariant requires synchronous change, or coordinate one aggregate write plus a durable event in the application layer.

{{example: domain-driven-design/domain-service-pledge-contribution}}

**Domain service vs use case (application service):**

| | Domain Service | Use Case |
|--|----------------|----------|
| Contains business logic? | Yes | No — orchestration only |
| Logical role | Domain policy | Application policy — coordinates domain operations and collaborations |
| Depends on | Domain types only by default | Domain services and normally application-owned repository/integration ports |
| Example | `pledgeContribution(occasion, eligibility, pledge)` | `handlePledge(persistence, eligibilityGateway, dto)` — loads, calls domain service, saves one aggregate plus its outbox event |

Keep domain business decisions pure by default. A domain-owned driven port is a rare, explicit exception only when the model itself—not application orchestration—owns the conversation. The consuming domain service is then effectful but still provider-free: isolate its pure decision logic and test the port interaction with a fake. Do not use this exception for repositories or gateways needed only by application orchestration.

Physical placement depends on the selected architecture. Organize by bounded context or business capability before technical role. In a visible hexagonal backend both roles are inside, commonly in separate domain/application packages when that dependency boundary earns its cost, or in cohesive feature/use-case modules inside one capability package. DDD without hexagonal architecture may use another context-first arrangement. Follow `structure-codebase` rather than assuming `domain/` contains all inside code.

For detailed guidance, see `resources/domain-services.md`.

---

## Error Modeling

Use discriminated union result types for expected business outcomes. Reserve exceptions for programmer mistakes and infrastructure failures.

{{example: domain-driven-design/pledge-result-types}}

**The test:** Could a user's action legitimately cause this outcome? If yes → result type. If no (it would mean a bug) → exception.

For detailed error modeling patterns and how errors propagate through layers, see `resources/error-modeling.md`.

---

## Repository Pattern

Repositories provide collection-like access to aggregates. Put the **interface with the innermost policy that consumes it** and the concrete implementation with infrastructure or integration code. In an explicitly hexagonal system, repository ports are normally application-owned because use cases load and save aggregates; place them beside that application policy and let a driven adapter implement them. Put one in domain only when the domain model itself genuinely owns and consumes the abstraction. DDD without ports and adapters does not gain adapter layers by implication; follow the architecture selected by `structure-codebase`. Repositories use `interface` (not `type`) because they define behavior contracts, and their methods use domain language.

{{example: domain-driven-design/occasion-repository-interface}}

**Repositories handle writes and single-aggregate reads.** For reads that need to JOIN across aggregates (dashboard views, detail pages combining data from multiple entities), repositories are the wrong tool — they enforce aggregate boundaries that reads need to cross. Use query functions that JOIN freely instead. This is the CQRS-lite pattern: writes go through repositories (consistency), reads go through query functions (flexibility). See the `hexagonal-architecture` skill's CQRS-lite section and its `resources/cqrs-lite.md` for details.

For simple domains where reads map cleanly to a single aggregate, repository reads are fine. Don't separate prematurely.

---

## DDD + TDD Integration

### Test by Domain Concept, Not Implementation File

Follow the physical shape selected for the project and keep focused tests beside the behavior they describe; DDD does not require a root `tests/` directory.

```
<selected-context-or-feature>/
  occasions/
    create-occasion.test.ts       # Behavior: creating occasions
    add-gift-idea.test.ts         # Behavior: managing gift ideas
    occasion-budget.test.ts       # Behavior: budget constraints
```

### Select the Primary Behavioral Boundary

Test through the broadest stable public behavior that the chosen architecture actually has:

- For a domain-only model or library, call aggregate operations, domain services, or Deciders directly; these tests are primary, not a fallback.
- When application policy exists, call the use case with simple fakes or stubs for its collaboration contracts. This exercises domain behavior and orchestration together without inventing ports.
- In an explicitly hexagonal system, exercise the driving port with driven actors replaced by outside test interactors; load `hexagonal-architecture` for that testing strategy.
- Add integration and delivery tests according to real infrastructure and user risk, not because DDD mandates a layer pyramid.

Focused tests for complex pure business rules complement application tests when both exist. They may be the complete primary suite for a provider-free domain package.

See `resources/testing-by-layer.md` for the architecture-neutral decision. For a DDD system that also adopts hexagonal architecture, the hexagonal skill's `resources/worked-example.md` traces one feature across ports, adapters, and tests.

### Test Factories Use Domain Language

{{example: domain-driven-design/test-factory-get-occasion}}

---

## Bounded Contexts

A bounded context is a linguistic boundary within which a particular domain model and glossary apply. The same word (e.g., "User") can mean different things in different contexts — and that's correct.

1. **Each context owns its own model and glossary** — `User` in billing differs from `User` in shipping
2. **Communicate between contexts via events or explicit contracts** — never share mutable state
3. **Anti-Corruption Layer (ACL)** — when integrating with external systems or other contexts whose model doesn't fit yours, translate at the boundary rather than letting their types leak in
4. **Shared kernel should be minimal** — only truly universal value objects (Money, Email). If the shared kernel grows, boundaries are unclear
5. **Each context has its own glossary section**

For context mapping patterns, monorepo structure, and ACL examples, see `resources/bounded-contexts.md` — including *When a Context Becomes a Service*: a context is a model boundary and a service a deployment one, and this project starts as one service holding several contexts (`src/<context>/`, each behind a `public` module, listed in `project.json` and kept apart by `make check-imports`) until a deployment reason makes one a service. For how contexts are found in the first place — decomposing an event storm, the Bounded Context Canvas, aligning teams to the boundaries — see `resources/modelling-process.md`.

---

## Anti-Patterns

### Anemic Domain Model

Entities are data bags with no behavior. All logic in "services." Fix: put behavior as pure functions next to the types they operate on.

### Generic Technical Names

Using `Item`, `Entity`, `Record`, `Data`, `Info` instead of domain terms. Always use the glossary.

### Presentation Logic in Domain

Display formatting does not belong in domain policy. The test: "make this look right for a human" = presentation. "Enforce a business rule" = domain. Purity is not sufficient — a pure formatting function is still presentation.

### Leaking Domain Logic

Business logic in route handlers, database queries, or adapters. Keep it in domain-policy modules under the physical shape selected for the project.

### Relationship-Driven Aggregates

Designing aggregates by mapping entity hierarchies ("Order contains OrderLines, OrderLine contains Product") instead of discovering invariants. The tell: aggregate methods only add, remove, or attach children — no business rules are enforced. If an aggregate's only job is managing parent-child associations, those relationships likely belong as database constraints or simple data models, not an aggregate hierarchy.

**The fix:** Ask "What must remain true when state changes?" If the answer is only structural (one-to-many, one-to-one), you don't need an aggregate — you need a foreign key. Aggregates earn their complexity when they enforce behavioral invariants during commands.

### Over-Engineering

Not every project needs aggregates, domain events, or bounded contexts. Start with:
1. Ubiquitous language (glossary)
2. Value objects and entities
3. Add complexity only when the domain demands it

### Resisting Model Evolution

Treating the initial model as sacred — refusing to rename types, split aggregates, or restructure bounded contexts as understanding deepens. The model should evolve continuously. If a refactoring reveals that "Occasion" should really be "GiftEvent" and "SavingsGoal", do it. The glossary changes, the types change, the tests guide the migration. Evans calls these "breakthroughs" — moments where the model fundamentally improves because the team learned something new about the domain.

---

## Checklist

- [ ] Glossary file exists and is up to date
- [ ] Declared concepts use the glossary's canonical spelling and capitalization
- [ ] Missing terms are treated as candidates requiring agreement, not silently adopted
- [ ] Rejected aliases name the owning bounded context and canonical replacement
- [ ] Any green language-lint result is reported with its actual targeted scope
- [ ] Value objects are immutable and identity-less
- [ ] Entities are always valid (invariants enforced on construction and transitions)
- [ ] Entities have branded IDs; primitive value objects use branded types
- [ ] Aggregate roots enforce all invariants
- [ ] Aggregate boundaries justified by invariants, not entity relationships
- [ ] Aggregates contain no read-only properties that exist solely for query convenience
- [ ] Other aggregates referenced by ID, not embedded
- [ ] Cross-aggregate logic in domain services, not crammed into one entity
- [ ] Use cases and orchestration live in application policy, not domain policy
- [ ] Repository and gateway ports live with the innermost consumer—normally application policy; domain owns only ports it genuinely consumes
- [ ] Concrete driven adapters implement inside-owned ports and live with infrastructure/integration
- [ ] Discriminated unions have exhaustive switch handling
- [ ] Expected business outcomes use result types, not exceptions
- [ ] Domain logic has zero infrastructure dependencies
- [ ] If `structure-codebase` has been applied, its domain/context and any visible inside/outside rules are present and passing
- [ ] Presentation logic is NOT in domain policy (even if pure)
- [ ] Tests organized by domain concept, not implementation file
- [ ] Each logical role has behavioral tests at the appropriate level
