# The global event model

One event model for the whole system, in one file, kept current as the work progresses.

`model.yaml` is the source. `make model` generates the diagram from it; `make check-model` fails the build
when the model and the repository disagree. Everything else in this directory is generated — do not edit it.

```bash
make model         # regenerate the diagram and the browsable page (PNG=1 also writes a raster copy)
make check-model   # validate the model and its links to the code — runs in CI, inside make verify
make model-drawio  # write the committed draw.io canvas, docs/event-model/model.drawio
make check-drawio  # fail when that canvas is missing or stale — runs in CI, inside make verify
```

## Why one model rather than one per feature

A plan covers a slice. A spec covers a feature. Neither survives the next feature, and event-sourced
systems fail at the joins: the second slice folds the first slice's events, the fourth discovers that
stream identity chosen in the first was wrong. Those are the mistakes a per-feature artifact cannot show
you, because the thing being violated is not in it.

So the model is global and cumulative. Each slice adds to the same timeline, which means the diagram
answers "what does this event already mean, and who reads it" *before* a new slice commits to an answer.

## Where it fits in the flow

```
Spec Kit constitution → specify → `/story-splitting` → plan → tasks → implement
                              add slices          split them          stream identity     model tasks       flip to
                              as proposed         → modelled          → planned                             implemented
```

`status` is the join. Each step tightens what the model must contain, and `make check-model` enforces the
tightening rather than trusting it:

| Status | Means | Then the model must carry |
|---|---|---|
| `proposed` | discovered in conversation, not yet agreed | its pattern and frames |
| `modelled` | the modelling session settled it | an `actor` for state-change and state-view slices, and the `service` that owns it once `project.json` lists more than one |
| `planned` | a plan covers it | what a state-change slice's append is guarded by — `stream` or a tag `guard`, the consistency boundary either way; `materialisation` for a state-view or automation slice — where its read model lives |
| `implemented` | it ships | `gwt` and `code` that exist, and events that appear in the source |

That last row is the one that keeps the diagram honest. Rename an event in the code and leave the model
behind, and `check-model` fails with the name it could not find.

## The file

A worked example — two slices, the second folding the first's event:

```yaml
version: 1

render:
  lanes:                         # see "Things that will bite"
    ui: actor                    # actor | context | none
    data: none                   # context | none
    events: stream               # stream | context | none
  framesPerSegment: 6
  # Optional. Set it once event-model.yml has deployed, and the README links the site instead of
  # embedding segments. Omit it and the README embeds segments, which needs no site.
  page: https://your-org.github.io/your-repo/

slices:
  - id: S1
    name: Place an order
    pattern: state-change
    status: implemented
    actor: Customer
    service: ordering              # a key of project.json's deployables — which service the code lives in
    stream: order-{orderId}
    spec: specs/001-ordering/spec.md
    gwt: specs/001-ordering/slices/S1.md
    code:
      - src/domain/ordering/events.ts
      - src/domain/ordering/decider.ts
      - src/application/usecases/place-order.ts
    frames:
      - type: ui
        name: CheckoutScreen
        data: "2 × Standard, £48.00"
        mockups:
          - { state: populated, at: docs/event-model/mockups/checkout.html }
          - { state: empty,     at: docs/event-model/mockups/checkout-empty.html }
          - { state: error,     at: https://www.figma.com/file/abc/Checkout?node-id=12 }
      - { type: cmd, name: PlaceOrder,  data: "orderId, items, idempotencyKey" }
      - { type: evt, name: OrderPlaced, data: "orderId, total £48.00, placedAt" }

  - id: S2
    name: See an order confirmation
    pattern: state-view
    status: planned
    actor: Customer
    reads: [OrderPlaced]
    materialisation: live          # folded per query, nothing stored — see below
    liveBudget:
      events: 40
      because: one order stream, closed at delivery; ~12 events at the ceiling
    frames:
      - { type: rmo, name: OrderSummary,       data: "orderId, total, status" }
      - { type: ui,  name: OrderConfirmation }
```

**Slice order is timeline order.** S1 renders to the left of S2 because it comes first in the file.

**Frame order is causal order.** Within a slice, each box is caused by the one before it.

**Frame numbers are derived, never written.** They are spaced ten apart per slice, so adding a box to S1
does not renumber S2.

**`reads` is how a slice draws on earlier events.** It names events, not frame numbers, and each one must
be produced by an *earlier* slice — a projection cannot fold an event that has not happened yet.

**`folds` is what the slice's Decider rehydrates from**, and it is a different question from `reads` —
different enough that getting them the wrong way round is the most expensive mistake in this file. What it
may name is *whatever the append is guarded by*: with `stream`, events on this slice's own stream, including
ones it appends itself; with a tag `guard`, events carrying an attribute that identifies one of the guard's
kinds. `check-model` refuses the rest, because a decision folding something its guard cannot reach is
guarded against a fact it never read. It is optional, because requiring it would invalidate every slice
already planned; it is checked whenever present. See [`reads` and `folds` are different questions](#reads-and-folds-are-different-questions).

**`stream` or `guard` is what the append is checked against**, and a state-change slice names one of them
before it can be planned:

```yaml
    stream: order-{orderId}        # the version of one stream — the default, and most slices
```

```yaml
    guard:                         # a boundary drawn over tags, per decision
      by: [seat, hold]
      because: a seat may be claimed once, and a hold may not exceed its cap
```

`stream` makes one stream the consistency boundary and its version the concurrency control. `guard` draws
the boundary per decision out of tags, for the constraint one stream cannot express — a capacity and a
member's own count, checked together, where either can change under you — and the append is refused if
anything matching the query arrived since. Never both (`one-guard-not-two`): a conflict has to mean one
thing. `guard.because` is required for the same reason `liveBudget.because` is — a boundary with no stated
invariant is a query somebody widened until the tests passed. The factory's decision behind all of this is
`docs/adr/0002-the-guard-a-slice-declares.md`.

**`data` is a worked example, not a schema.** Concrete values (`£48.00`) beat type names (`Money`); that
is the whole point of modelling with an example. Braces and newlines are stripped, because Mermaid's
inline data cannot escape them.

**`attributes` is `data` with somewhere to mark identity**, and only an `evt` frame has it:

```yaml
      - type: evt
        name: SeatClaimed
        attributes:
          - { name: seatId,   identifies: seat }
          - { name: fromHold, identifies: hold }
          - { name: toHold,   identifies: hold }
          - { name: claimedAt, type: instant }
```

`identifies` names the kind of thing an attribute identifies, and it is what a tagging function is
transcribed from: a conditional append is guarded by a query over tags, a tag is `<kind>:<value>`, and this
is where the model says which value that is. Two attributes may identify the same kind — `fromHold` and
`toHold` are both a `hold` — so the event carries two `hold:` tags and a query for either finds it; that
case is why `identifies` names a kind rather than being a flag.

Tags themselves are never modelled: they are an index over the log, not a fact about the business, and
there is no tag field anywhere here. On the diagram an identifying attribute is starred — `seatId*` — and
the kinds are on `model.html`, where there is room. A frame carries `data` **or** `attributes`, never both,
and `check-model` refuses the rest: identity on a box that is not an event, one attribute named twice, and
an `identifies` that is not a lower-case kind. It is optional and belongs at `planned` rather than
`modelled` — which attributes identify something is a detail for the session with engineers, not for
discovery.

**`mockups` is how a white box points at its designs**, and only a white box has them — a command, an
event and a read model are data, so a picture of one is really a picture of the screen that shows it, and
`check-model` refuses the mistake as `mockup-is-a-screen`.

It is a list of *labelled states* rather than one link, because a screen is almost never one picture:
empty, populated, error and mid-flight are different designs, and the differences between them are exactly
where the unmodelled states hide. Naming them here gives `/gaps` and `/example-map` something to interrogate
— *you have designed populated and error; what does empty look like?* — instead of asking it against memory.
Two mocks claiming the same state fail `mockup-state-is-unique`: one of them is current and one is not, and
nothing here can tell which.

`at` is repository-relative, exactly like `gwt`, `spec` and `code`, and is checked to exist
(`mockup-exists`). An absolute `http(s)` URL is allowed for a mock held in a design tool, and is taken on
trust — `check-model` does no network, the same trade `render.page` makes and for the same reason.

**Once `render.page` is set, a repository-relative mock must live under `docs/event-model/`.** The publish
workflow serves that directory and nothing else, so a link to `design-mocks/checkout.html` resolves in a
clone and 404s on the page people are actually sent to. `mockup-publishes-with-the-page` refuses it;
`docs/event-model/mockups/` is where mocks go if you want them published, and a URL is the other answer.
Unpublished, the rule stays quiet — the page is opened from a clone, where any path in the tree resolves.

**`model.html` draws them**, under the slice diagram and headed by the screen they belong to — the
wireframes themselves, at thumbnail size, each one a link to the full mock. An HTML mock is framed with
`sandbox="allow-same-origin"`, which renders it faithfully while withholding scripts, forms, popups and
navigation; an image is drawn directly; one held in a design tool is named and linked, never fetched, so
the page stays a file that reaches nowhere. A screen with no mocks says so in words, because an undesigned
state is a finding rather than an empty space.

None of this reaches the *diagram*. The `eventmodeling` DSL has no link, no `click` directive and no way
to put an image in a box, so the wireframes sit beside the slice rather than inside its white box — which
means adding one changes no SVG, and `make model` only has to run again to refresh the page.

**A screen that has shipped must have them** (`screen-states-recorded`), and that is a rule about the
commonest case rather than the rare one. Most white boxes are never drawn by anybody: the slice gets built,
the states get decided at the keyboard, and the model keeps saying *"no mockups yet"* about a screen that has
been in production for a month. So where mocks were supplied, `mockups` points at them and the screen is
built to them state by state; where none were, the states are designed as the screen is built and written
back here in the same change, wireframe committed under `docs/event-model/mockups/`. Designing as you go is
expected. Leaving no record of what you chose is what makes the screen's unhandled states unreachable by
`/gaps` and invisible to the next person, which is the entire cost this field exists to avoid.

Its sibling rule is `screen-is-built`: an `implemented` slice's white box has to appear in the source, the
same bargain an event name makes. Between them they refuse the failure this whole field was too polite to
prevent — a slice that models a screen, builds the route beneath it, ships with no user interface, and passes
every other gate. See
[`event-modeling-to-code.md#the-white-box-is-a-deliverable`](../event-modeling-to-code.md#the-white-box-is-a-deliverable).

## The four patterns

> Each pattern's translation into files — schemas, Deciders, use cases, projections, and the test level
> that owns each behaviour — is [`docs/event-modeling-to-code.md`](../event-modeling-to-code.md). This
> section is the *model* shape; that one is what you write.


`check-model` holds every slice to the shape of its pattern, and refuses the shapes event modelling
forbids:

| Pattern | Frames | Also required |
|---|---|---|
| `state-change` | `ui → cmd → evt+` | no `reads` — a command takes user input and folds events under the same guard it appends with, never a maintained view |
| `state-view` | `rmo → ui?` | `reads` — the events the fold is built from, and `materialisation` once planned — where the view lives |
| `automation` | `rmo → pcr → cmd → evt+` | `reads` — what triggers it. All four boxes, or it is not an automation. `materialisation` may not be `live`: a todo list is persisted |
| `translation` | `evt(external) → pcr → cmd → evt+` | the first frame carries `external: true` |

Three rules worth naming, because they are the ones people break:

**A read model never feeds a command.** `rmo` immediately followed by `cmd` is rejected — and the reason is
consistency rather than shape. A command may decide only from what its own append can hold still: the
events it folded under the same guard it appends with, which is its stream's expected version, or the tag
query a conditional append is guarded by. A view something else maintains is neither — it lags by design,
and no guard covers it, which is how the last ticket gets sold twice. In an automation the processor sits
between them and holds the conditional logic, and the read model it consults is a *trigger*, not the
decision.

**An automation needs all four parts.** Triggering event, read model consulted, processor with the
condition, resulting command. A command that simply emits two events is a state-change slice, not an
automation.

**A processor never issues a state-change.** A `pcr` box anywhere in a `state-change` slice is rejected by
name (`processor-means-automation`), because a state-change slice is a command issued by *a UI*. This one
is worth the dedicated error: the wrong classification validates, renders, and looks right. What it loses
is every arrow between the steps — see below.



## `depends_on` is a build order, not a timeline fact

Optional on each slice. Lists sibling slice ids that must be **done** — `status: implemented` — before this
one may start — genuine code or contract dependencies only. Needing another slice's events is *not* a
`depends_on`: seed from synthetic fixtures (Principle V). `make check-model` refuses a `depends_on` set that
is exactly the producers of this slice's `reads`, and refuses cycles. `/drive` uses the field (with the
split's `## Slice graph`) to compute which slices are **ready**, in one session or across several.

Ready is necessary for running alongside a sibling, not sufficient: the slice must also be `planned`. Its
events' `attributes`, its `stream` or `guard` and its `examples.md` are the contract a concurrent sibling
builds against, and `modelled` is the word for a contract that may still move. `/drive` fans out over the
ready slices that are `planned` and works a ready `modelled` one itself first.

## `reads` and `folds` are different questions

Two folds, easy to confuse, and confusing them is what makes the `automation` pattern look structurally
impossible:

| | `reads` | `folds` |
|---|---|---|
| Answers | **is there work?** | **is this allowed?** |
| Belongs to | a projection — the processor's *todo list* | the Decider behind the command |
| May name | events from **earlier slices only** | whatever the append is guarded by: this slice's own stream, or events identifying one of a tag `guard`'s kinds |
| Enforced by | `reads-resolve`, `reads-earlier-slice` | `folds-resolve`, and `folds-own-stream` or `folds-match-the-guard` |

**The mistake, worked through.** A slice allocates a seat when a place is claimed. Asked "what does this
step need to know?", the natural answer is *the seat capacity* — so `SeatAllocated` and `SeatOffered` go
into `reads`, and `check-model` refuses them, because this slice produces one and a later slice produces
the other:

```
reads-earlier-slice
  - R2: reads `SeatAllocated`, produced by R2, which is not earlier on the timeline
```

That looks like proof the slice cannot be an automation. **It is proof the wrong events were listed.** The
capacity events are what the *ticket-pool Decider* folds to answer *"is a seat allowed?"* — they are
`folds`. The automation's read model is a todo list answering *"is there a claim with no seat yet?"*,
which folds `PlaceClaimed` from an earlier slice and validates immediately.

Get this the wrong way round and the second failure follows: `folds-own-stream` — or
`folds-match-the-guard`, where the boundary is drawn over tags — catches state specified outside the guard,
which is unreachable however green the Decider's unit test looks — hand-feeding a
Decider events from another stream is the normal way to write those tests, and it is how a meaningless
green test gets written.

## Where the read model lives

`materialisation` is the read side's `stream`. One says what a write costs to keep consistent; the other
says what a query costs to answer. Both are answered once, both are lived with, and `check-model` asks for
each at `planned` — a state-change slice for its `stream`, a state-view or automation slice for its
`materialisation`.

| | Runs | Consistency | What it costs |
|---|---|---|---|
| `live` | per query, folded in memory, nothing stored | strong | the whole fold on every read, forever |
| `inline` | in the same transaction as the append | strong | projection work on the write path, and write throughput coupled to it |
| `async` | a catch-up subscription with a checkpoint | **eventual** | a lag to design for and cap, plus the worker that runs the subscription |

All three are buildable out of what this project already has. `inline` is written inside
`EventStore.unitOfWork` — the seam that suspends `append`'s own commit, so a view write and the events it
derives from land together or not at all. `async` is `CheckpointStore` and the catch-up runner beside it:
`catchUp` applies the log in batches and advances the checkpoint **in the view's own transaction**, and
`rebuild` empties the view and folds the whole log back in. `live` needs nothing but the fold and the
ceiling `liveBudget` puts on it.

Default to `async` for anything that must scale or fan out; keep `inline` for the few views a user must
never see stale immediately after their own write; take `live` deliberately, and only where the fold stays
small. `skills/event-sourcing/resources/projections-and-read-models.md` has the mechanics — checkpoints,
idempotency, ordered ownership, rebuilds — and `resources/production-concerns.md` beside it has the
operational half, including when a stream has earned a snapshot and why closing the books beats one.

**Why the field exists at all, rather than being left to the plan.** The skeleton used to ship an event
store with `read`, `append` and `readAll` and nothing else: no checkpoint, no runner, no rebuild. So folding
the log per query was the only read path that already existed, and every other answer was greenfield. A
slice that reached a plan without being asked therefore got `live` — not because anybody weighed it, but
because it was free — and the assumption underneath it, *the streams are short*, is never written down where a reviewer
could dispute it or a gate could fail it. The read side now ships as finished as the write side, so all
three answers cost about the same to take; the field stays because the *choice* is what was missing, and a
choice nobody is asked for is made by gravity. That is what `liveBudget` is:

```yaml
    materialisation: live
    liveBudget:
      events: 40
      because: one order stream, closed at delivery; ~12 events at the ceiling
```

`events` is the ceiling one query may fold; `because` argues it from the stream's own lifetime — a start
event and an end event, or a closing-the-books summary that starts a fresh stream. Write the fold's own
projection test against that ceiling, and a stream that outgrows it fails a test instead of quietly getting
slower. A `live` view whose `because` is "for now" is a deferral: put it in the plan's Stubs and Deferrals
table, where the thing it will cost to retrofit is visible.

**`live` is not a lesser answer.** For a view over one short-lived stream it is the right one, and it is the
only lifecycle that is strongly consistent without putting work on the write path — which is also the
cheapest fix for read-your-writes on the slice that just wrote. What it is not is the answer nobody chose.

## A processor is a role, not a deployment — and it is spawnable

**An automation's processor may be invoked in-request for latency, and MUST ALSO be runnable standalone.
Its read model is therefore persisted, because a standalone run has no request to tell it what to look
at.**

Those two sentences are the whole of it, and their absence is expensive. The pattern is four boxes and the
boxes say nothing about how the `rmo` persists or when the `pcr` runs — so an implementer can satisfy every
documented requirement with an in-request fold (a few `readStream` calls, concatenated, folded in memory,
no table and no runner), pass `check-model`, match the diagram exactly, and have built something that
structurally cannot do the job.

**A process manager is not request-scoped.** It is spawned — on a timer, on a notification, at startup,
after a crash — and it queries its todo list *to discover work it did not create*. That is the defining
capability of the pattern, and an in-request fold cannot do it: it only knows which streams to read because
the request that just wrote them said so. Such a processor **cannot be invoked standalone at all** — not
slower, impossible — and a request that dies midway leaves work nothing will ever pick up.

So: two invocations, one processor, one persisted read model. The request invokes it inline, so the happy
path finishes and the response can honestly say what happened; a standalone run sweeps up what a dead
request left behind. The worked code is in the `event-sourcing` skill:
`resources/projections-and-read-models.md` holds the incremental fold, the checkpoint written in the
projection's own transaction and the rebuild from zero, and its *A Todo List Is Claimed as Well as Folded*
section holds the claiming that stops two runners acting on one row — with the two things about it that are
usually built backwards.

**A todo list is not a view, though the model calls both `rmo`.** A view is disposable: stale means someone
saw old data, and losing it means rebuilding it. **A todo list is operationally load-bearing — losing it
loses work**, because nothing else records the intent. Eventual consistency is fine for both; *absent* is
fine for neither.

**None of this makes the automation pattern asynchronous.** The pattern describes *causality* — this
command follows that event — and says nothing about timing.

This is worth stating because assuming otherwise makes the correct model look like it costs a product
change: that reclassifying to `automation` forces eventual consistency, rewrites the acceptance criteria,
and turns *"the place was claimed and the seat allocated"* into *"claimed, seat follows"*. None of that is
implied. Choose the timing when you plan the slice; record it in `research.md` if it is interesting. The
model is not the place that decision lives.

## A worked process manager

The shape most likely to be modelled wrongly, and the one the four patterns above do not show. Five steps
orchestrated by the system, of which two are automations:

```yaml
  - id: R1
    name: Claim a place
    pattern: state-change          # a person clicks; this one really is a UI
    actor: Attendee
    stream: registration-{registrationId}
    frames:
      - { type: ui,  name: RegistrationForm }
      - { type: cmd, name: ClaimPlace }
      - { type: evt, name: PlaceClaimed }

  - id: R2
    name: Allocate a seat
    pattern: automation            # the system issues this, not the attendee
    reads: [PlaceClaimed]          # the todo list: a claim with no seat yet
    stream: ticket-pool-{eventId}
    folds: [SeatAllocated, SeatReleased]   # the Decider's own history, same stream
    materialisation: async                 # a persisted todo list; `live` is refused on an automation
    frames:
      - { type: rmo, name: UnallocatedClaims }
      - { type: pcr, name: AllocateOnClaim }
      - { type: cmd, name: AllocateSeat }
      - { type: evt, name: SeatAllocated }
```

Three things this buys that the five-state-change-slices version does not: the causal chain is *in* the
model rather than in prose inside a label, Constitution VII's `causationId` has something to derive from,
and no command carries a human `actor` who does not issue it. That last one is not cosmetic — a model that
forces `actor: Attendee` onto a system-issued command produces a real disagreement between documents about
who acted, and the argument that follows is about a fact the model invented.

**The compensation gap, which you have to decide rather than discover.** A compensating step — release the
place when the seat cannot be allocated — is triggered by a *refusal*, and **a refusal appends nothing**.
There is no triggering event, so there is nothing for `reads` to name. Two honest answers:

- **The todo list detects the absence** — `ClaimsAwaitingSeats` folds `PlaceClaimed` and `SeatAllocated`
  and lists claims older than some interval with no seat. The trigger is elapsed time, so the automation
  needs a runner and a termination condition.
- **The refusal becomes an event** — `SeatAllocationRefused` is appended, and the compensation `reads` it
  like any other trigger. This makes a rejection part of the permanent record, which is a real decision
  with a real cost: refusals are usually the noisiest thing a system does.

Neither is wrong. Choosing by default is.

## Shapes that look right and are not

Three counter-examples, because the patterns above show what works and the expensive mistakes all look
like something that works:

| Looks like | Actually is | What it costs before anyone notices |
|---|---|---|
| A `state-change` slice whose command is issued by a `pcr` | An `automation` | The orchestration exists nowhere a tool can read. Every step renders as an unrelated interaction — a five-step process manager drew its UI box three times, as though the attendee filled in three separate forms |
| A Decider folding an event that establishes existence, appended by a different slice | State on another stream, so unreachable | The command refuses unconditionally. The Decider's unit test passes, because it was hand-fed an event that could never have been appended to that stream |
| An accepted ADR that changes what an earlier accepted plan means | Two correct documents that contradict each other | Nothing compares them. It surfaces at the first line of code, at the point where sunk cost argues for coding around it |
| An `automation`'s read model folded in-request — a few `readStream` calls concatenated in memory | A processor that cannot be spawned | It satisfies the `rmo` frame and matches the diagram. It cannot be invoked standalone, so abandoned work is never recovered, and nobody finds out until a request dies. `todo-list-is-persisted` refuses the *declaration* — a slice claiming `async` and shipping an in-request fold is still this row, and only the code review sees it |
| A projection folded from a subset of streams, exposed as a **collection** | A map that answers "not ready" for everything it did not fold | The shape invites a query it cannot answer correctly, and a wrong answer is indistinguishable from a right one. Return the single item, or fold what makes the whole collection true |

The third has no validator and probably cannot have one. What it has is a procedure: **an ADR names the
artifacts it invalidates or amends, in the ADR itself.** See `docs/adr/` and the `architecture-decisions`
skill.

**And one detector that is not a gate at all: look at the rendered diagram.** The processor defect above
survived four workflow stages, two days of implementation and a green `make check-model`. It was caught by
a person opening `model.html` and noticing the picture did not tell the story. Every automated check reads
the model as text. Nothing but you looks at it.

## What the diagram looks like

Three swimlanes, and Mermaid's own event-modeling colours:

| | |
|---|---|
| **UI / wireframe** (white) | what the actor sees. The only frame with `mockups`, which the page links per state |
| **Processor** (purple) | automation: where the condition lives |
| **Command** (blue) | an intent that may be rejected |
| **Read model** (green) | a fold over events |
| **Event** (orange) | a fact, permanent once written |

Generated artifacts:

| File | What it is for |
|---|---|
| `model.mmd` | the Mermaid source — paste into any Mermaid renderer, or diff it in review |
| `model.svg` | the whole timeline in one picture. Grows without limit; see below |
| `model.html` | the browsable page: diagram, slice register, and each slice on its own. Print it to PDF |
| `segments/model-N.svg` | the timeline in readable pieces — what the README embeds |
| `slices/<id>.svg` | one slice with the events it consumes drawn in |
| `model.png` | raster copy, only with `PNG=1` |
| `model.drawio` | **the committed canvas** — the same timeline as one editable draw.io page, written by `make model-drawio` and held current by `make check-drawio`. See below |

Everything `make model` writes is generated on demand and not committed: it takes a headless browser to
draw, so nothing that runs on every commit could prove a committed copy current, and a picture that can
quietly stop matching the model is worse than none. The pages workflow redraws it all on every model
change. **GitHub's Markdown renderer runs a Mermaid older than 11.15**, so a fenced `eventmodeling`
block will not draw there — check what it runs today by putting a fenced `info` diagram in a comment, which
renders as the version string. Where the README needs a picture, `make model` embeds the segment SVGs
inside its markers, or links the published page once `render.page` is set.

## The committed canvas

`make model-drawio` writes the whole timeline as one draw.io page, `docs/event-model/model.drawio`, and that
file **is committed**. It is the one rendering with that property, and the reason is what it takes to draw:
a `.drawio` file is plain XML, so writing one is arithmetic and a string — no browser, no account, no
credential, no network. That is what lets `make check-drawio` regenerate it in memory and compare it on every
commit, inside `make verify`, which nothing driving a headless browser could ever do.

| | Mermaid (`make model`) | draw.io (`make model-drawio`) |
|---|---|---|
| Produces | slice diagrams, README segments, the whole-timeline SVG, the browsable page | one editable canvas |
| Lives | generated on demand, not committed | committed |
| Needs | a headless browser | Node, and nothing else |
| Currency | redrawn by the pages workflow | **`check-drawio`, inside `verify`** |
| Good for | reading, embedding, GitHub | working on, annotating, presenting |

Neither replaces the other, and both draw the same model: a box that sits fourth on the canvas sits fourth in
`model.svg`, in the same swimlane, with the same arrows and the same colour. That is not a coincidence to
maintain — which lane a box is in and which arrows exist are answered once, in `scripts/event-model/model.ts`,
and both renderers ask it; the palette is one table both read.

What the canvas looks like: one column per box, left to right in timeline order; rows are the notation's
bands — UI and automation on top, commands and read models in the middle, events underneath — with a lane
per actor or stream where the model groups them; a caption per slice above the bands; a legend above that.
A step within a slice is a solid arrow. A read of an earlier event is dashed, and one that spans more than
a column detours below the bands through a corridor rather than crossing every box in between, with every
reader of one event sharing that event's corridor. Under each box that reads anything is a caption naming
every event it reads, so a reader learns where an arrow came from without following it.

Open it in draw.io — [app.diagrams.net](https://app.diagrams.net), the desktop app, or the VS Code
extension — to present it, walk a stakeholder through it, or lay annotations over it. **Do not edit the
committed file**: `make check-drawio` compares it byte for byte with what the model produces, so a hand
edit fails the gate on the next commit. Copy it to annotate, and put what you learn back into `model.yaml`,
where the next `make model-drawio` will draw it. A model with no slices has no canvas, and a canvas left
behind by a model that was emptied is stale like any other.

Fit-to-window on a model of any size shows boxes and no text: at a few percent zoom every label is
sub-pixel. That is the viewer, not the file — zoom in.

## Publishing it

**The browsable page can be a URL.** `.github/workflows/event-model.yml` renders `model.html` and deploys it
to GitHub Pages, and attaches the same files to the run as an artifact. It is path-filtered to `model.yaml`
and the renderer, because rendering fetches a headless browser and the model changes rarely. That job is also
the only place `make model` runs in CI — `check-model` is the gate precisely because it needs no browser.

**Check your Pages visibility before you enable it.** An event model is your event names, stream identities,
actors and slice register — close to a design document of the whole system:

| Plan | What publishing means |
|---|---|
| **Enterprise Cloud** | A private repository can serve an **access-controlled** site, visible only to people who can already see the repository. This is the setting the workflow assumes |
| **Pro / Team** | Publishing from a private repository makes the **site public** |
| **Free** | Pages serves public repositories only |

On the last two, delete the `deploy` job and keep the artifact — it is available on every plan and stays
inside the repository's access control. Two settings turn it on: *Settings → Pages → Source: GitHub
Actions*, and *Visibility: Private*.

Once the site exists, read its address off the deploy job's environment URL and set `render.page`. The README
block then becomes that link and stops embedding segments — see the reasoning below.

**The README block is opt-in by marker.** `make model` maintains whatever sits between
`<!-- event-model:start -->` and `<!-- event-model:end -->` — the diagrams or the link, the slice count, and
how many slices sit at each status — and `make check-model` fails when it drifts. A README with neither
marker is left completely alone and nothing is reported, so a project that would rather not carry the section
deletes both and never hears about it again. One marker without its pair *is* reported, because that is a
mistake rather than a choice. Never hand-edit inside the markers: the next `make model` overwrites it.

The reason it lives in the README at all: a model nobody sees is a model nobody notices has gone stale, and
answering *"what does this event already mean, and who reads it"* is only useful **before** the next slice
commits to an answer.

## Things that will bite

**The renderer is fetched on demand.** `make model` installs `@mermaid-js/mermaid-cli` into
`scripts/event-model/.mermaid-cli/` (gitignored), which downloads a headless browser the first time. It is
not a project devDependency, so `npm install` stays fast and `make check-model` — the gate that runs in CI
— needs no browser at all. The local prefix is so the renderer can patch mermaid's swimlane bug
([mermaid-js/mermaid#7925](https://github.com/mermaid-js/mermaid/issues/7925)) before the first diagram.

**`check-drawio` needs Node and no browser.** It runs the same TypeScript pipeline `make model` does, minus
the rendering, so `make verify` in an event-profile project installs `scripts/event-model`'s three
dependencies on first run — about a second once the tree is there — whichever language the services are
written in. CI is given a Node for it where the project has none of its own.

**That download does not exist on linux/arm64.** Google ships no Chrome build for it, so on an ARM
sandbox or container `make model` fails at the browser fetch. Nothing gates on this — `check-model` needs
no browser — but to actually regenerate the diagram there, supply a browser yourself and tell the
renderer where it is:

```bash
npx playwright install --with-deps chromium-headless-shell   # Playwright does build arm64 Chromium
cat > /tmp/mermaid-puppeteer.json <<'EOF'
{
  "executablePath": "<path playwright install printed>/chrome-headless-shell",
  "args": ["--no-sandbox", "--disable-dev-shm-usage"]
}
EOF
MERMAID_PUPPETEER_CONFIG=/tmp/mermaid-puppeteer.json make model
```

Recent Playwright names that binary `chrome-headless-shell`; an older pinned one names it `headless_shell`.
Use whichever `playwright install` actually printed.

`--no-sandbox` is required because Chromium's own sandbox cannot initialise inside an already
unprivileged container; `--disable-dev-shm-usage` avoids crashes from the small `/dev/shm` most
containers mount. When `MERMAID_PUPPETEER_CONFIG` is unset, rendering behaves exactly as before.

**Arrows come from adjacency, not from declarations.** In the Mermaid DSL, two boxes next to each other in
the file get an arrow whether or not you meant one. That is why frames are causal order and why slices with
external inputs are emitted differently. The generator handles it; if you hand-edit `model.mmd`, it will
not.

**`rf` silently discards relations.** A reset frame given an `->>` list parses fine and draws no arrows at
all. The generator never does this. Noted here because it costs an hour to find.

**The whole timeline stops being readable at about the fourth slice.** Not a fixable property of the
picture — the diagram is a timeline, so it grows sideways forever while the column it is read in does not.
Measured against mermaid-cli 11.16.0, scaled into a ~830px README column:

| | Natural width | Scaled |
|---|---|---|
| 1 slice | 909px | 91% |
| 2 slices | 1371px | 61% |
| 4 slices | 2269px | 37% |
| 20 slices | 6564px | 13% — a coloured smear |

So the README embeds **segments** rather than `model.svg`: contiguous runs of whole slices, each under
`render.framesPerSegment` frames (default 6, about two slices, ~70–80% scale). Segment width is bounded;
timeline width is not. Frame numbers stay global across every view, so a box carries the same number in a
segment, in its slice view, and in the whole timeline — which is what makes them one model rather than
three drawings. A slice reading an event produced in an earlier segment shows it as a consumed source, so
nothing appears to come from nowhere.

`model.svg` is still generated and still linked; it is the right thing on a big screen, and each segment
links to itself full size for the same reason.

**Unless the model is published, in which case the diagrams stop being worth embedding at all.** Set
`render.page` to the site `event-model.yml` deploys and the README block becomes the link, with `model.svg`
kept as a text link beside it and no image of any kind. Segments exist because a README column can neither
zoom nor scroll, and the page can do both — plus it carries the slice register and every slice on its own,
which no embedded picture does. So once the better version has an address there is nothing left for the
worse one to contribute.

This was settled by measurement rather than taste, in a project with thirteen slices: nine segments, which
is nine pictures of a timeline in a column too narrow to read any of them, stacked above a link to the page
that showed all of it properly. An overview of the whole timeline instead of the stack was tried and is no
better — at thirteen slices it is the 13% smear in the table above.

The URL is declared rather than derived. `https://<org>.github.io/<repo>/` is a guess that is wrong for a
custom domain and wrong for every project that deleted the `deploy` job because its plan would have made
the site public, and a README link that 404s is worse than no link. Deriving it from `origin` would also
make `check-model` depend on which remote a clone happens to have, and a gate that answers differently in a
fork is not a gate. Read it off the deploy job's environment URL after the first successful run.

Check the site's visibility before committing the URL: the README is the part that publishes it.

The count-and-status line stays either way, which is what keeps a stale block a failing gate: the link does
not change when the model does, so it is that line that notices a README a new slice left behind.

**Each band's lanes group by their own thing.** Mermaid resolves a namespace *within* a band, not across
the diagram, so `Guest.` on a `ui` box and `Inventory.` on an `evt` box are independent. That is what makes
the notation's own picture one diagram: actors across the top, streams across the bottom. `render.lanes`
is one setting per band:

| Band | Boxes | Options | Default | Names the lane after |
|---|---|---|---|---|
| `ui` | `ui`, `pcr` | `actor`, `context`, `none` | `actor` | the slice's `actor` — a processor gets its own lane |
| `data` | `cmd`, `rmo` | `context`, `none` | `none` | the slice's `context` |
| `events` | `evt` | `stream`, `context`, `none` | `stream` | the slice's `stream`, placeholder removed |

`events: stream` is the notation's bottom band. The lane name is the stream identity with its placeholder
taken out — `order-{orderId}` is the `order` lane — so every order stream is one lane rather than one per
order, and the lane a reader sees is the consistency boundary the append was guarded by. A slice that
guards with a `guard` instead of a `stream` has no such name and falls back to its `context`; with neither,
its events stay in the default lane, which makes an unplaced slice visible rather than guessed at. An event
consumed by a later slice is drawn in its **producing** slice's lane, so the same event is never in two
places.

`data` is `none` by default because splitting the middle band rarely earns the height it costs — set it to
`context` when the Conway's law step has found contexts worth seeing all the way down.

`render.actorLanes` is still read for a model written before `lanes`: `true` is `ui: actor` with the other
two bands ungrouped, `false` is no grouping at all, so such a model renders exactly what it always did.
Setting both is refused rather than resolved.

Mermaid still allocates a fresh lane per namespaced box — `calculateSwimlaneProps` never stores
`namespace`, so `findSwimlaneByNamespace` cannot match
([mermaid-js/mermaid#7925](https://github.com/mermaid-js/mermaid/issues/7925)). Two lines reproduce it
without the local patch:

```
eventmodeling

rf 01 ui Sales.A
tf 02 ui Sales.B
```

Two boxes, one namespace, one entity type: two full-width lanes, both labelled `UI/A: Sales`. Drop the
prefix and they share one lane. The unmerged fix is
[mermaid-js/mermaid#7986](https://github.com/mermaid-js/mermaid/pull/7986). Until mermaid-cli ships it,
`scripts/event-model/patch-mermaid-swimlanes.ts` applies that change to the mermaid-cli install `make model`
fetches, so the committed SVG and `model.html` group correctly on either axis. Pasting `model.mmd` into
another renderer does not. Delete the patcher when the pin no longer needs it.

**Box labels are `foreignObject`, and that is browser-dependent.** Mermaid's eventmodeling renderer
hardcodes label text as embedded HTML rather than SVG `<text>` — `renderer.ts` always appends a
`foreignObject` and never reads `htmlLabels`. Setting `htmlLabels: false` in a mermaid-cli config file
therefore changes nothing for these diagrams (it is a flowchart/class-diagram switch). Chrome draws the
embedded HTML when the SVG is loaded through an `<img>` tag — which is how a Markdown image renders — but
this is exactly the case some browsers have historically not drawn, so a reader may see boxes and arrows
with no words in them. `model.html` inlines the SVG into the document instead, where it always renders;
that is another reason the page exists.

**Nine frames per slice is the ceiling.** Not a rendering limit — a slice needing a tenth box is almost
always two slices.
