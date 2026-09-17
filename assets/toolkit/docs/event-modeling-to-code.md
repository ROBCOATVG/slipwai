# From event model to code

The model says what happens. This says what each box becomes in a file, which is the step nothing else
here writes down — [`docs/event-model/README.md`](event-model/README.md) documents the model *format* and
the four patterns, and the constitution documents the *obligations*, and between them sits the translation
everybody has to do and nobody has written out.

Every identifier below is illustrative. This template ships no domain model on purpose, so `OrderPlaced` is
an example of a shape, never a name to adopt. Everything imported from `src/domain/shared/` is real and
ships here — `Decider`, `rehydrate`, `Decision`, `accept`, `reject`, `createEventParser`,
`defineStreamIdentity`, `moneySchema`, `instantSchema`, `currentVersion`. The two conversions in the use
case below, between a domain event and a stored envelope, are yours to write: what goes in an envelope
depends on who your actors are, which is a modelling output a starter cannot supply.

## The one-page map

Every frame in a slice becomes something, and the something is always in the same place:

| Frame | Colour | Becomes | Lives in |
|---|---|---|---|
| `ui` | white | **two files, not one: the surface the actor uses, and the driving adapter beneath it.** The surface is a screen in a UI, a command's rendered output in a CLI. The adapter parses, delegates, and maps outcomes to responses | the frontend, plus `src/adapters/driving/…`; tested at the project's UI level and in `tests/edge/` |
| `ui`'s `mockups` | — | the states that surface renders, one entry each. **Build targets where they exist; where they do not, the states are designed while the slice is built and written back here** | `docs/event-model/mockups/`, or a design tool by URL; shown per state on `model.html` |
| `cmd` | blue | a command type, and the use case that executes it | `src/application/usecases/` |
| `evt` | orange | a Zod schema plus a registry entry — permanent, versioned | `src/domain/<context>/events.ts` |
| `evt`'s `attributes` | — | the payload's fields; the ones marked `identifies:` become the event's **tags**, one `<kind>:<value>` each, in the project's tagging function | the schema, plus `tagsOf` where the store is built |
| `rmo` | green | a pure fold over events, plus the store the slice's `materialisation` names | `src/application/projections/`, plus a driven adapter for anything but `live` |
| `pcr` | purple | a processor: consult the todo list, decide, issue the command | `src/application/usecases/` |

And the fields on the slice itself:

| Field | Becomes |
|---|---|
| `stream` | `defineStreamIdentity('order')`, and the `expectedVersion` every append carries |
| `guard` | the other answer: a tag query and the position it was read at, which `appendIf` is refused by. `by` becomes the query's tag keys; `because` is the invariant the boundary protects |
| `folds` | exactly the events the Decider's `evolve` handles — nothing else can reach it, and nothing outside the slice's guard may appear in it |
| `reads` | the events a projection folds. A *different question* from `folds`; see below |
| `actor` | who calls the edge. **Not** the envelope's `actor` field, which records who the runtime observed |
| `gwt` | `specs/<feature>/slices/<id>/examples.md`, whose `AC-` ids appear in acceptance test titles |
| `code` | the files that realise the slice. `check-model` asserts they exist and that the events appear in them |

## The white box is a deliverable

The row above used to say a `ui` frame becomes "a route, a CLI command, a queue consumer", and that sentence
cost a project its entire frontend. It is true and it is half the answer: the adapter is what the surface
*talks to*, and reading it as the whole obligation makes a white box a caption on a backend. Slices got
modelled with screens, shipped with routes, and passed every gate — because nothing downstream of the model
ever asked for the screen.

So, three rules, and `check-model` holds the last two:

**The frontend belongs to the slice that models the white box.** Not a later UI slice, not a follow-up PR.
The same change that adds the command adds the screen that issues it. This is the rule people bend, because
a screen whose submit button reaches nothing feels like unfinished work worth deferring — and it is exactly
the thing to build anyway. A slice is a vertical, and a vertical with no top is a layer.

**A shipped white box exists in the source** (`screen-is-built`). The frame's name is the screen's name, the
same bargain an event name already makes: the model said it, so the code contains it. A screen named
differently in code is two names for one thing, which is the drift the whole file exists to prevent.

**A shipped white box records the states it renders** (`screen-states-recorded`). Where mocks were supplied,
`mockups` points at them and the screen is built to them, state by state. Where none were, the states get
designed as the screen is built — and then written back into `mockups` in the same change, with the
wireframe committed under `docs/event-model/mockups/`. Designing as you go is normal and expected; leaving
no record of what you chose is what turns `model.html` into a page saying *"no mockups yet"* about a screen
that shipped a month ago, and it puts the screen's unhandled states out of `/gaps`' reach permanently.

## `state-change` — `ui → cmd → evt+`

The only way state changes, and the pattern everything else is defined against.

**The events come first, because they are permanent.** A schema per event type, a registry, and one parser
built from it:

```ts
// src/domain/ordering/events.ts
export const orderEvents = {
  OrderPlaced: z.object({ orderId: z.string(), total: moneySchema, placedAt: instantSchema }),
} as const satisfies EventSchemaRegistry;

export const parseOrderEvent = createEventParser(orderEvents);
export const orderStream = defineStreamIdentity('order');
```

`createEventParser` **skips event types it does not know and throws on a corrupt payload**. That
combination is deliberate: an unknown type is a newer version of the code writing to the same log, which a
rolling deploy makes routine, while a payload that fails its own schema is data loss and must not pass
quietly.

`defineStreamIdentity` exists as a named thing rather than an inline template string because it is the
single most consequential decision in the design — one stream is one consistency boundary, so it fixes both
what can be enforced atomically and where the throughput ceiling sits. Changing it later migrates the one
thing that cannot be migrated.

**The Decider is the whole business rule, and it is pure:**

```ts
// src/domain/ordering/decider.ts
type State = { readonly placed: boolean };

export const orderDecider: Decider<State, PlaceOrder, OrderEvent, 'AlreadyPlaced'> = {
  initialState: { placed: false },
  evolve: (state, event) => (event.type === 'OrderPlaced' ? { placed: true } : state),
  decide: (command, state) =>
    state.placed ? reject('AlreadyPlaced') : accept([{ type: 'OrderPlaced', payload: { … } }]),
};
```

Three things this shape buys, each of which is a rule elsewhere in the repo:

- **`decide` returns events *or* a rejection**, never both, because `Decision<E, R>` is a union. The
  illegal state is unrepresentable rather than merely undesirable.
- **No clock, no `Math.random`, no `crypto.randomUUID`** — ESLint enforces it inside `src/domain/`. Those
  arrive as typed inputs on the command, which is what makes a Decider testable without freezing time.
- **`evolve` handles exactly the events in the slice's `folds`**, and `check-model`'s `folds-own-stream`
  refuses one produced on a different stream. A Decider can only rehydrate from its own stream, so state
  folded from elsewhere is unreachable and the command refuses unconditionally — while its unit test
  passes, because the test hand-fed it an event the runtime never will.

**The use case is load, fold, decide, append — and re-decide on conflict:**

```ts
// src/application/usecases/place-order.ts
const stream = orderStream.forInstance(command.orderId);
const history = await events.readStream(stream);
const state = rehydrate(orderDecider, history.map(toDomainEvent));
const decision = orderDecider.decide(command, state);
if (isRejected(decision)) return decision;

const result = await events.append(stream, currentVersion(history), decision.events.map(toEnvelope));
// A version conflict is a RETURN VALUE, not an exception. Contention is expected: read again and re-decide.
if (!result.appended) return retry();
```

This is the level Principle V puts the acceptance gate at, because it is the whole path a slice has to get
right. The route above it does one job — parse, delegate, map each outcome to a response — and gets its own
test in `tests/edge/`.

## `state-view` — `rmo → ui?`

A read model is **a pure fold**, and the slice says where the fold's result lives — `materialisation`, which
`check-model` requires from `planned` exactly as it requires `stream` from a state-change slice:

| | The fold runs | Then you also write |
|---|---|---|
| `live` | per query, in memory | nothing — and `liveBudget` on the slice, the ceiling one query may fold and why it holds |
| `inline` | in the append's own transaction | the view's table, and the write path that updates it |
| `async` | in a catch-up subscription | the view's table, a checkpoint advanced in the same transaction, an exclusive sequential owner, and a rebuild path |

Write the fold first either way — it is the same function in all three, and the one place the slice's rules
live. What changes is what maintains it.

```ts
// src/application/projections/order-summary.ts
export const orderSummary = (events: readonly CommittedEvent[]): OrderSummary =>
  events.filter((e) => orderStream.matches(e.streamId)).reduce(apply, empty);
```

**Scope every projection to its own streams.** `orderStream.matches` is not decoration — a fold over the
whole log works until an unrelated stream exists whose event type name collides, and then it is silently
wrong rather than broken.

`reads` names the events it folds, and each must come from an *earlier* slice: a projection cannot fold an
event that has not happened yet.

## `automation` — `rmo → pcr → cmd → evt+`

The pattern people get wrong, in two distinct ways.

**A processor issuing a command makes the slice an automation.** If a `pcr` box issues the command it is
not a `state-change` — `check-model` refuses that by name. The tell in a model is an `actor` naming a human
on a command no human issues; the tell in code is a use case invoked only from other application code.

**Its read model is a persisted todo list, not a per-request fold.** A processor may be invoked in-request
for latency and **must also be runnable standalone**, because that is how it discovers work it did not
create and recovers what a dead request abandoned. A standalone run has no request to tell it where to
look, so a read model folded per request cannot be spawned at all.

That is the whole difference between the two folds, and it is worth having straight:

| | `reads` | `folds` |
|---|---|---|
| Answers | **is there work?** | **is this allowed?** |
| Belongs to | the processor's todo list | the command's Decider |
| May name | events from **earlier slices only** | events on **this slice's own stream**, including its own |

The worked implementation is in the `event-sourcing` skill's `projections-and-read-models.md`:
incremental fold, checkpoint on global position advanced in the projection's own transaction, rebuild from
zero, and `SKIP LOCKED` claiming so two runners cannot both act on one item. The `pcr` box itself is an ordinary function: claim work, decide,
issue the command through the same use case a person would have driven.

## `translation` — `evt(external) → pcr → cmd → evt+`

The anti-corruption layer. **Provider types stop at the adapter** — nothing from a vendor SDK reaches
`src/domain/`, which `check-imports` enforces.

```
src/adapters/driven/<provider>/    ← their shapes, their errors, their retries
        ↓ mapped here, and only here
src/application/usecases/          ← our command
src/domain/<context>/events.ts     ← our event
```

The adapter is tested against a **stub** in `tests/integration/` — a real server on loopback whose
responses are pinned to a recorded or published contract. A fake implements *our* port and is held honest
by the port's contract suite; a stub impersonates *their* provider, where nothing we own defines the right
answer.

## Which test level proves what

| The behaviour | The level | Why there |
|---|---|---|
| An acceptance criterion (`AC-`) | `tests/acceptance/` — through the **use case** | It survives swapping the delivery adapter, which Principle IV exists to allow |
| Parse, delegate, outcome-to-status | `tests/edge/` | A translation, not a rule |
| A state of a screen — what the actor sees and can do | the project's UI level, one test per `mockups` state | Rendering, empty and error states, and whether the submit path is reachable are browser-observable and invisible to every level above. `front-end-testing` picks the lightest harness that proves the claim; **an HTTP test through the route is not evidence about the screen** |
| A rule unreachable from the boundary (`CS-`) | `tests/domain/` | The combinatorial tail, where a boundary test per case would be absurd |
| A fold's collisions, ordering, rebuild | `tests/projection/` | Synthetic event fixtures; no I/O |
| What any implementation of a port must do | `tests/contract/` | Run against the fake **and** the real thing, so the fake cannot drift |
| A driven adapter's error mapping, retry, timeout | `tests/integration/` | Against a pinned stub |

**A red-team finding is reproduced from outside** — that is where an attacker stands — and then its test
goes wherever the behaviour lives. If the rule was wrong, the Decider or the use case owns it. If the rule
was right and the route got past it, the edge owns it.

## What is deliberately not in the model

The commonest way to over-model is to put these in it:

- **Format and structure validation.** If the type system can reject it, it is not a scenario and not a
  frame. `Money` is branded integer minor units, so cross-currency arithmetic is a compile error rather
  than a rule anyone tests.
- **Infrastructure preconditions.** "Is the database up" is not a read model.
- **A command's own input.** A `state-change` slice declares no `reads` — its command takes user input and
  folds the events it decides from under the same guard it appends with, which is the stream's expected
  version, or the tag query a conditional append is guarded by. A view something else maintains cannot be
  that: it lags by design and no guard covers it, which is how the last ticket gets sold twice.
- **Timing.** In-request or background is an invocation choice recorded in `research.md`, not a property of
  the pattern.

## Where the gates fire

| When | What refuses it |
|---|---|
| Writing the model | `check-model` — pattern grammar, a read model feeding a command, an automation with no processor, a cross-stream `folds`, a slice reading an event nothing produces |
| Reaching `planned` | the guard present — `stream` or `guard`; `materialisation` present on a slice with a read model, and `liveBudget` on a `live` one; `gwt` naming the examples the tests will cite |
| Writing the code | `check-imports`, the `any` ban, and the clock/randomness ban inside `src/domain/` |
| Reaching `implemented` | `code` and `gwt` exist, every event named appears in the source, and every white box both **exists in the source** (`screen-is-built`) and **records the states it renders** (`screen-states-recorded`) |
| Before the PR | `/mutation` — and `/adversary` before it, where the slice changed attack surface or closed the split; `adversary-log.md` holds that decision |

The one thing no gate does is look at the picture. Open `docs/event-model/model.html` and say in a sentence
what it claims happens; that is the check that has caught what the others could not.
