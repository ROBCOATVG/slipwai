# Modelling Events

Events are the most permanent artefact in an event-sourced system — you will replay them for the life of the system. Time spent modelling them well is repaid many times over. This resource covers discovering events with **event modeling**, the command/event distinction, granularity, and the naming anti-patterns.

## Discovering Events: Event Modeling

Event modeling (Adam Dymitruk) builds **one timeline of how information changes over time**, and its output *is* the shape of a write model — which is why it is the front end to everything in this skill. The facilitated session is the `event-modeling` skill; recording the result is the `global-event-model` skill, which keeps it in `docs/event-model/model.yaml` and renders the diagram.

**Three swimlanes, read left to right as time:**

| Lane | Holds |
|------|-------|
| UI / Automation | what the actor sees, and the processors that act without one |
| Command / Read Model | the intent being submitted, and the projections that inform a view |
| Events | the facts, in the order they happened — the backbone of the model |

**The colour grammar** (load-bearing, and what `make model` renders):

| Element | Colour | Meaning |
|---------|--------|---------|
| Event | Orange | A past-tense fact somebody appended. Permanent. |
| Command | Blue | An intent that may be rejected. Never stored. |
| Read model | Green | A fold over events, serving a view or a processor. **Never feeds a command.** |
| UI / wireframe | White | What the actor sees at that point in time. |
| Processor | Purple | Automation: the conditional logic between an event and the next command. |

**Four patterns, and every slice is exactly one of them:**

| Pattern | Shape | Reads |
|---------|-------|-------|
| State change | `ui\|processor → command → event+` | nothing — the command takes user input and consults the event stream |
| State view | `events → read model → ui?` | the events it folds |
| Automation | `event → read model → processor → command → event+` | what triggers it |
| Translation | `external event → processor → command → event+` | nothing — the external event is its input |

**A vertical slice is one instance of one pattern**, and it is the unit of work: one slice, one plan, one set of Given/When/Then scenarios, one shippable change. Slices sharing an event schema are independent — the schema is the contract between them, so neither has to be built first.

**Two rules the shapes encode**, both of which are checked mechanically by `make check-model`:

- **A read model never feeds a command.** The reason is consistency rather than shape: a command may decide only from events it folded under the same guard it appends with — its stream's expected version, or the tag query a conditional append is guarded by — and a view something else maintains lags by design, with no guard over it. That is how the last ticket gets sold twice. In an automation the processor sits between them and holds the condition, and the read model it consults is the trigger rather than the decision.
- **An automation needs all four parts.** Triggering event, read model consulted, processor with the condition, resulting command. A command that simply appends two events is a state change, not an automation.

**Pivotal events** are the few most significant events (`OrderPlaced`, `PaymentReceived`, `ShiftClosed`) that mark major state transitions. They are the primary signal for **bounded-context and stream boundaries** — they usually mark where one aggregate's lifecycle ends and the next begins. Place them first and fill in between them. This directly feeds the short-stream / "closing the books" modelling in `production-concerns.md`.

**Every read model field must trace back to an event.** If a field has no source event, the model is incomplete — something nobody appends is being displayed. That check is the reason to model information flow rather than screens.

## Commands vs Events

The command/event distinction is the axis the whole model turns on. Confusing them produces the "passive-aggressive event" anti-pattern below.

| | Command | Event |
|--|---------|-------|
| Intent | Imperative request to *do* something | A fact that *already happened* |
| Naming | Imperative — `PlaceOrder` | Past tense — `OrderPlaced` |
| Recipients | One handler | Broadcast to 0..N subscribers |
| Outcome | **May be rejected** | Can only be **ignored** |
| Stored? | No | Yes — it is the source of truth |

The tell, from Dudycz: *"commands can be rejected by the command handler. Events can only be ignored."* If a message must be acknowledged or refused on a blocking path (payment, shipment), it is a command — model it explicitly. If it merely announces a fact that others may react to, it is an event.

## Naming Events

- **Past tense, business language.** `SubscriptionCancelled`, `SeatReserved`, `FundsWithdrawn`. Greg Young: *"All events should be represented as verbs in the past tense such as CustomerRelocated, CargoShipped, or InventoryLossageRecorded."*
- **Intention-revealing, not technical.** The name should carry the business reason. `OrderShippingAddressCorrected` says why; `OrderUpdated` says nothing.
- **Never put "and" in an event name.** It signals two facts crammed into one and guarantees future versioning pain. Split into two events.

## What Goes In an Event

An event must be a **self-contained business fact** — interpretable on its own, years later, without joining to mutable tables.

- **Capture the values that were true at the moment it happened** — the price charged, the tax rate applied, the result returned by an external service. Not a foreign key to a row that will have changed, and not a value the projection must recompute later. Greg Young's rule: bake behaviour-determining data into the event at creation time, so replay stays deterministic even if the algorithm changes.
- **Always include the relevant IDs**, and prefer copying immutable values over references.
- **Model events as discriminated unions** with a `type` discriminant and exhaustive `never`-guarded handling — the same shape as commands and state (see `typescript-strict` and the `functional` skill).

## Granularity: Thin, Fat, and Summary

Event size is a real design decision with named patterns (Mathias Verraes):

- **Thin event** — carries only what the fact needs. Default for internal events. The failure mode is the *clickbait event*: an event carrying only an id, forcing subscribers to call back to the producer, which reintroduces coupling and race conditions.
- **Fat event** — deliberately adds redundant data so consumers need fewer event types and are better isolated from the producer. Verraes's heuristic: *"consider the number of consumers and their ownership. If a single team owns both the producer and consumer, Fat Events pose less of a risk."* The risk is events that bloat and accrete fields nobody can prove are still used.
- **Summary event** — a single coarse event that concludes a process (`ShiftClosed` with the day's totals), built by a projection over the fine-grained events, for consumers who only care about the outcome.

There is no universal right size; choose per consumer and per boundary.

## Internal vs External Events

The most important granularity decision is the **internal/external split**, and it is the one teams most often skip. Your fine-grained internal events are an implementation detail of your bounded context; the events you publish to *other* contexts are a **contract** and must be designed with the same rigour as a public API.

Dudycz: *"We'll shoot ourselves in the foot if we don't split our events into internal and external. We'll have a leaking abstraction that creates coupling, and it's a first step to the distributed monolith."* Verraes calls the same idea **Segregated Event Layers**: *"Keep all internal events strictly private. Set up an adapter that listens to internal events, and emits a new stream of different events."* The public stream is effectively a different bounded context with its own language — an anti-corruption layer.

Practically: keep internal events free to change; expose a coarse, enriched, versioned external event (often a *summary* or *fat* event) on a separate channel. This is also what buys you versioning freedom internally (`event-versioning.md`).

## Anti-Patterns

- **CRUD / property sourcing** — `Created`/`Updated`/`Deleted` events, or one-event-per-field-change. They record *that data changed*, not *what happened or why*. Dudycz's *State Obsession*: storing `BalanceUpdated {amount}` loses the fact that it was a deposit — *"change your mindset of thinking 'what has changed?' to 'what has happened?'"* Model `MoneyDeposited`, not `BalanceUpdated`.
- **Clickbait event** — an event carrying only an id, so subscribers must query back. Put the fact in the event.
- **Passive-aggressive event** — an event whose real intent is to *trigger* an action in a specific consumer. That is a command in disguise; if the relationship is real and blocking, make it an explicit command.
- **Exposing internal events as your integration contract** — see the internal/external split above; it couples other contexts to your write model's shape.
