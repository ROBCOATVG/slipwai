# Event Sourcing and What It Is Not

Event sourcing is the premise of this project, so this resource is not a decision framework. It is the vocabulary to tell event sourcing apart from the patterns it is most often confused with, and the obligations it carries once chosen. Confusing it with any of the four below produces a design that looks event-sourced and does not behave like one.

**A note on "tamper-evident."** Event sourcing gives you a *complete* domain history by construction, but append-only application logic is not by itself tamper-*evidence*: a DBA, a schema migration, or a compromised credential can still alter rows. If you need provable integrity, add controls on top — hash-chaining the events, WORM/immutable storage, restricted write permissions, or external audit logging. Event sourcing makes those easier; it does not supply them for free.

**Scope is still a modelling decision.** Event sourcing is chosen per bounded context, and stream identity is chosen per aggregate — one stream is one consistency boundary and therefore one concurrency ceiling. Greg Young: *"The largest failure I see from people using event sourcing is that they try to use it everywhere."* Read that as being deliberate about boundaries, not as a reason to revisit the pattern.

## The Obligations You Have Taken On

Permanent, and cheaper to design for now than to retrofit:

- **Eventual consistency.** Read models lag writes. The UI must be designed for it (see `projections-and-read-models.md`).
- **Event versioning.** Events are immutable and live forever, so old shapes must be readable by new code — decide the strategy on day one (`event-versioning.md`).
- **No ad-hoc queries.** You cannot `SELECT ... WHERE` against the log for current state; every query needs a projection. Young: *you need read models because the event store only answers get-by-id.*
- **The replay/external-effects hazard.** Fowler: *"if these events cause update messages to be sent to external systems … things will go wrong because those external systems don't know the difference between real processing and replays."* Side effects belong in handlers, never in `evolve`.
- **A steeper learning curve** and a smaller hiring pool who have done it well.

## Event Sourcing Is Not…

These are the four confusions that cause the most damage. Get the distinctions crisp.

### …CQRS
**Orthogonal patterns, frequently combined.** CQRS separates the write model from read models; event sourcing chooses events as the write model's storage. You can do CQRS without event sourcing — that is the hexagonal skill's **CQRS-lite** (one database, query functions that JOIN freely). In practice event sourcing almost always *drives* CQRS: because the log only answers get-by-id, you project events into read models to serve queries. Young's directional rule of thumb: *"You can use CQRS without Event Sourcing, but with Event Sourcing you must use CQRS"* — treat it as practical advice, not a formal law (the patterns are independent; Fowler considers CQRS optional and warns it *"adds risky complexity"*).

### …event-driven architecture
*"Event-driven"* is an overloaded umbrella. Fowler names four different patterns hiding under it: **event notification**, **event-carried state transfer**, **event sourcing**, and **CQRS**. Notification and carried-state-transfer are about *messaging between systems*; event sourcing is about *persistence within one system*. Publishing an event to tell another service something happened is event-*driven* and needs no event store. Only storing events as your source of truth is event sourcing.

### …event streaming (Kafka)
Different tools that merely integrate. Oskar Dudycz: *"Event Sourcing is about durable state stored and read as events, and Event Streaming is about moving events from one place to another."* Kafka lacks the two operations an event store exists to provide — **load a single aggregate's events** and **append with optimistic concurrency** — so it is a poor primary event store, though excellent for propagating events *between* services once they leave your context.

### …an audit log or CDC
The difference is the **direction of truth**. In event sourcing, events are primary and state is derived. In change-data-capture / an audit log, database *state* is primary and the log is a derived side effect. A 100%-reliable audit log is a *free benefit* of event sourcing, but it is not the point — and the reverse (treating a CDC row-change stream as your domain event stream) couples every consumer to your physical schema. Kislay Verma: *"some people propose to use the CDC stream as a system's event stream, and this is where I completely disagree."*
