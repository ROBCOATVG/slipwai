# Bounded Contexts

A bounded context is a linguistic boundary — the region where a particular domain model and ubiquitous language apply consistently. Context boundaries are discovered through team structure, language divergence, and business capability mapping, not by technical convenience.

## Context Mapping Patterns

When bounded contexts interact, the relationship follows one of these patterns:

| Pattern | Relationship | When to use |
|---------|-------------|-------------|
| **Anti-Corruption Layer** | Downstream translates upstream model | Upstream model doesn't fit your domain — protect your model with a translation layer |
| **Shared Kernel** | Two contexts share a minimal subset | Small, stable shared concepts (Money, Email). Both teams agree on changes |
| **Published Language** | Shared interchange format (schemas) | Event-driven communication. Events use a shared schema |
| **Open Host Service** | Upstream provides a stable API | Multiple downstream consumers. The API is the contract |
| **Conformist** | Downstream accepts upstream model as-is | No influence over upstream. Accept their types directly |
| **Separate Ways** | No integration | Cost of integration exceeds the benefit |

**For most projects, Anti-Corruption Layer and Shared Kernel are the most immediately useful.**

## Anti-Corruption Layer (ACL)

The ACL translates between an external model and your domain model at the boundary. This is the most practically important context mapping pattern — use it whenever integrating with external APIs, legacy systems, or other bounded contexts whose types don't match yours.

{{example: domain-driven-design/acl-stripe-payment-translation}}

The ACL lives at the integration boundary — a driven adapter when hexagonal architecture is used. Domain code never sees `StripeCharge` — only `PaymentResult`.

## Shared Kernel

A minimal set of types shared across contexts. Keep it as small as possible — only truly universal value objects — and give every shared concept one explicit owning context or purpose-named package.

{{example: domain-driven-design/shared-kernel-package-layout}}

**Warning signs the shared kernel is too large:**
- It contains entity types (not just value objects)
- Changes to the kernel require coordinating multiple teams
- It has its own business logic beyond construction/validation

## Structuring Context Boundaries in Code

The physical structure depends on the selected application architecture. Use the `structure-codebase` skill for the target tree; bounded contexts define language/model authority and must not silently select hexagonal architecture.

**DDD without ports and adapters:**

```
src/
  contexts/
    gifting/
      glossary.md
      occasions/
      contributions/
      application/
      public.ts
    budgeting/
      glossary.md
      budgets/
      application/
      public.ts
```

This structure protects context public APIs without claiming an inside/outside technology test wall.

**DDD plus explicitly adopted hexagonal architecture:**

```
packages/
  gifting/                           # context/capability first
    hexagon/
      domain/                        # pure business rules and model
      application/                   # use cases and normally application-owned ports
    adapters/
      driving/
      driven/
    testing/
  budgeting/
    hexagon/
      domain/
      application/
    adapters/
      driving/
      driven/
    testing/
```

If both contexts genuinely share a concept, assign it one explicit context or purpose-owned package and expose it through that owner's public contract; do not create a repository-root `shared`, `utils`, or catch-all `shared-kernel` bucket.

The grouping directories do not make a context real. Glossary scope, model authority, public contracts, and enforced imports do. The `hexagon/` directories add a separate claim: their packages are provider-free and independently testable from actors and adapters.

**Separate services** (strongest isolation):

Each bounded context is its own deployable service. Communicate via events (Published Language) or explicit API contracts (Open Host Service). Use ACLs to translate between contexts.

The deployment model is independent of the context boundary. A monolith can have well-defined contexts; microservices can have muddled ones. The boundary is linguistic and ownership-based, not deployment-based.

## Enforcing Boundaries

- **Import restrictions**: in this repository, `make check-imports` refuses an import from one context into another that does not go through the other's `public` module (`api` in Java), as soon as a service lists more than one context in its `project.json` `contexts`. Elsewhere, ESLint rules (eslint-plugin-boundaries, Nx enforce-module-boundaries) do the same job
- **One published module**: each context exposes only its public API — `public.ts`, `public.py`, a `public` package in Go, an `api` package in Java. Everything else in the context is its own
- **Code review**: Every PR touching domain code should be checked for ubiquitous language compliance against the glossary
- **Separate packages/services**: The strongest enforcement — contexts can only communicate through published interfaces. See *When a Context Becomes a Service* below for when that cost is worth paying

## Discovering Context Boundaries

Context boundaries are discovered, not designed up front. They emerge where language, ownership, or business rules diverge.

### The Language Test

The strongest signal is when the same word means different things to different people:

| Word | In gifting context | In billing context |
|------|-------------------|-------------------|
| "User" | Someone who organizes occasions and manages gift ideas | An account with a payment method and billing history |
| "Event" | A gift-giving occasion (birthday, holiday) | A billable transaction or audit log entry |
| "Amount" | How much to pledge toward a gift | An invoice line item total |

When you find yourself adding qualifiers ("billing user" vs "gifting user"), you've found a context boundary. Each context should use the unqualified term with its own meaning.

### Signals That You Need to Split

**Strong signals (split now):**
- The same word means different things — and you're adding prefixes to disambiguate
- Two parts of the system change for different business reasons at different rates
- A model that makes one workflow simple makes another workflow awkward
- Different stakeholders or domain experts own different parts of the system

**Moderate signals (consider splitting):**
- You're building a "god entity" with dozens of fields, most irrelevant to any single use case
- Teams step on each other's code — merge conflicts across unrelated features
- Business rules in one area have nothing to do with business rules in another

**Weak signals (probably don't split yet):**
- Code is getting large (size alone doesn't imply a boundary)
- You want to "clean up" the architecture (refactoring isn't the same as boundary discovery)
- Technical concerns differ (use hex arch layers, not context boundaries)

### How to Find Boundaries in Practice

**1. Listen for language friction.** When domain conversations become awkward — "I mean the *shipping* address, not the *billing* address" — you've found a seam. Map where these qualifiers appear.

**2. Map the workflows.** For each major business workflow (e.g., "place an order", "process a return", "manage inventory"), list the entities and rules involved. Where workflows share entities but use different fields or apply different rules, there's likely a boundary.

```
Workflow: "Pledge a contribution"
  → Entities: Occasion, Contributor, Money
  → Rules: balance check, funding-closed check

Workflow: "Send gift reminders"
  → Entities: Occasion, Recipient, NotificationPreference
  → Rules: reminder timing, opt-out, channel selection

These share "Occasion" but use different fields and rules.
"Occasion" means different things in each workflow.
→ Potential boundary between gifting and notifications.
```

**3. Follow the ownership.** If different people (or teams) are responsible for different decisions, those decisions likely belong in different contexts. The gifting team decides budget rules; the notifications team decides delivery channels.

**4. Check for independent deployability.** Could this part of the system change and deploy without affecting the other? If yes, it's likely a separate context. If changes always cascade across both, they may be one context.

## When a Context Becomes a Service

The signals above answer one question: *is this a separate context?* A different question, with different
signals, is *should this context be a separate deployable?* A project generated here starts as one service, and
that service may hold several contexts as `src/<context>/` — one deployable, several models, each behind its
own `public` module, kept apart by `make check-imports`. That is the modular monolith, and it is the right
shape for a context whose boundary is still being found: renaming, splitting or merging a directory is cheap;
doing the same to a service, its database, its image and its pipeline is not.

Three rungs, each costing more than the last, each recorded in `project.json` rather than in the tree:

| Rung | What it is | What it costs | When |
|------|-----------|---------------|------|
| A name on a service | `contexts: ["billing"]` — the service is one context | Nothing | The service is one model with one language |
| A directory inside a service | `src/billing/` and `src/gifting/` in one service, `contexts: ["billing", "gifting"]` | An import rule and a `public` module per context | Two models, two glossaries, one deployable — the default |
| A service of its own | `apps/billing`, added with the factory's `add-service` | A network boundary, its own data store, image, pipeline and on-call | A deployment reason, below |

**Deployment reasons — split into a service when one of these is true:**
- It has to release on its own cadence — changes to it are held back by, or hold back, the rest
- It has to scale or run on its own terms — a different load profile, runtime, memory or latency budget
- It owns data that must live in a store of its own — for isolation, regulation, or a different storage model
- It belongs to another team, with its own on-call and its own deploys
- It is written, or should be written, in another language or on another framework

**Not deployment reasons:**
- It is a separate context — that is what the directory rung is for
- The code is large — size is a reason to split a module, not to add a network hop
- The team wants "microservices" — a boundary drawn for its own sake moves the coupling onto the wire, where it is slower and harder to see

**Keep it on the directory rung when:**
- The two contexts call each other synchronously and often — every such call becomes a network round trip and a partial-failure mode
- They share a transaction — a write that must succeed or fail in both is one consistency boundary, and a service boundary cannot hold it
- One is small enough that its own pipeline and store would be most of the work

The sequence is: find the boundary on the directory rung, prove it — the import gate stays green, and what
crosses the boundary is events the other context publishes or calls to its `public` module — and move to a
service the day a deployment reason turns up. Because the seam was enforced, that move is `add-service`,
a directory move and a rewrite of each slice's `service` in the model, not a rewrite of the code. Splitting
before the boundary is proved means finding it across a network, which is the expensive way.

### Common Mistakes

- **Splitting by technical layer** (a "database context" and an "API context") — contexts are business boundaries, not technical ones
- **One context per entity** — most entities don't warrant their own context. Split by business capability, not by noun
- **Splitting too early** — start with one context and split when you feel the friction. Premature boundaries create coordination overhead worse than a slightly large model
- **Ignoring the cost of communication** — every context boundary adds an integration point. Only split when the cost of a unified model exceeds the cost of integration
