---
description: Name this feature's fairways and type the contracts every one of them steers by, before the work is split
argument-hint: [feature]
---

# Chart

Run this once per feature, after the mock-up review and **before** the split. A person is present — and
where none is, *Record the context answer, every time* says what stands in for them.

This is the standard profile's answer to what the event model is on the other one. The event profile has a
single artefact that names each slice's context and service, types its events, and says what it reads, so
its chart is rendered with `make chart` and never written. This profile has no such artefact, so the chart
is written here, and `make check-chart` holds it afterwards either way.

The file is `specs/<feature>/chart.yaml`.

## It is written in two passes, and nothing is claimed until both are done

The chart names fairways, marks and slices, and the slices do not exist yet when this stage runs. So:

- **This stage writes `fairways` and `marks`.** Those are the decisions that have to be taken before the
  work is cut up, because the way the work is cut up depends on them.
- **The split writes `slices`.** For each slice it has cut: the fairway it belongs to, the capability it is
  part of, the marks it sets and the marks it steers by.

"Before the split" means no slice is claimed until the whole chart is there. Both passes are before that,
and `check-chart` is what says the chart is whole.

## Work it out first. Bring a proposal, not a questionnaire

**Do the whole of pass one yourself before anyone is stopped.** Every question below has evidence in the
repository, and a stop that opens with blank questions spends a person's attention on work a careful
reading would have done. So read first, propose an answer to each with the evidence behind it, and then ask
the person to confirm it or amend it. This is the release-constraint stage's rule — *recommend the answer
with its reason rather than asking an open question* — applied to the stage that commits a feature's
contracts.

Three rules keep that honest.

- **Every proposal carries what it was read off**, by file and by line. "`billing customer` and `shipping
  customer` both appear in spec.md §3, so customer means two things here" is a proposal a person can
  disagree with. "Two contexts" is a guess wearing a conclusion's clothes.
- **Say which ones you are unsure about, and why, before the person reads the list.** A proposal offered
  with the same confidence as every other gets confirmed at the same speed as every other, and the one that
  was wrong goes through with the rest.
- **Genuinely undecidable things stay questions.** Where the evidence runs out — whether two vocabularies
  are two contexts or one with sloppy naming, whether a contract is published or internal — ask it as an
  open question rather than proposing the likelier answer. A product decision taken by inference is the
  failure this stage exists to prevent, and a confident wrong proposal is worse than a blank, because a
  blank gets thought about.

## Pass one, here: the fairways

A **fairway** is one bounded context's slices, with one holder. Work out an answer to each of these, then
put it to the person.

1. **Which bounded contexts does this feature touch?** Start from the work, not the nouns: the
   specification's Key Entities whose state the user stories change are the candidates, and an entity's
   state is never split across two contexts — publishing a listing and filling its chairs change one
   entity and stay together whatever else is decided. Then test every seam between two candidates three
   ways, the way `skills/domain-driven-design/resources/bounded-contexts.md` describes under *The Seam
   Tests*, each with the file and line it was read off:
   - **Language.** Does a word both sides use mean two things, with qualifiers creeping in like "billing
     customer" and "shipping customer" — or does one identity carry a different shape on each side, the
     same listing as a night with a private address and as a pin with a seat count?
   - **Change.** Name one plausible change to the rules on each side and say whether it reaches the
     other. Rules that change for different business reasons are the strongest reason to split; a change
     that cascades both ways is the strongest reason not to.
   - **Flow.** Which actor decides the rules on each side, and is the handoff between them something the
     far side only reads — a mark it steers by, never a state it writes?

   Then count what would cross: a mark steered by is cheap; a slice that must read the far side's current
   state to decide, or share its transaction, keeps the two together on its own. **A shared noun is
   evidence for neither side.** Two candidates that share every word and pass the change test and the
   flow test are two contexts; one vocabulary with one reason to change and one owner is one, and saying
   so with the evidence is the whole decision. Propose the contexts as a table — candidate, entities it
   owns, the three tests' evidence, what crosses, confidence — with the seams you are unsure about named
   first.

   **Before any seam test, interrogate the streams** — the ones the model names, or the ones each
   candidate's state would be written to. For each, list the invariants it protects, by requirement, and
   look first for those that span groups of slices: a decision that reads several groups' current state in
   one transaction, or a lifecycle state like closure that one group sets and every group must check. Such
   an invariant keeps those groups together — splitting them needs a process manager and opens a window to
   breach it. Groups no invariant spans are separate streams correlated by id, and the seam tests run
   between them. "One record per leaver" describes uniqueness or a view, not by itself a boundary.
2. **Which service holds each one?** Read `project.json`'s `deployables`, each service's recorded `purpose`
   and its existing `contexts`. Where one service plainly covers a context, propose it. Where none does, or
   two could, that is a question and not a proposal. Record the confirmed answer on the service with
   `slipwai describe-service <name> --context <context>`, once per context.
3. **What does each fairway own?** The paths no other fairway writes. Propose them from the layout that is
   already there: a service holding one context owns all of it; a service holding several gives each
   context its own directory. Say which directories exist today and which the proposal would create.

## Record the context answer, every time

**Pass one always writes its context answer as the next entry of `specs/<feature>/decisions.md`**, whether
it found several contexts or one — the shape `commands/cruise.md` shows and `make check-decisions` holds
(Question, Options, Decision, Why with Read against, Decided by, Confidence with Would reverse if, Written
to, Status). Head it `## D<n> — Which bounded contexts does <feature> touch?`, and put the seam table
under its `Options` line, indented two spaces so it stays inside the entry: candidate, entities it owns,
the Language · Change · Flow evidence with file and line, what crosses, confidence. One context is an
answer and the one that most needs its table: one fairway is one captain taking every slice in turn.
Where one fairway would hold more than twelve slices, add a `- **Why not split:**` line citing, by
requirement, the invariant that spans its groups. Twelve is not a limit and implies no split; it is where a
serial fairway costs enough of a run that its reason has to be written. `make check-chart` refuses a chart
whose fairways no such entry explains, and a crowded one whose entry records no `Why not split`.

**With nobody present** — any session a script dispatched, which says so with `SLIPWAI_STAGE` in its
environment (`launch`, `model`, a captain's `drive`) — do not decide silently and do not stop. Proceed on the best-evidenced proposal, and record it as `Decided by: host (stage
recommendation)` with `Status: awaiting human confirmation`. Then post the question for a person: append
one `question` line to the deck log of the first fairway the chart names,
`.slipwai/logs/<feature>/<fairway>.jsonl` — `{"v": 1, "t": "<ISO instant>", "kind": "question", "fairway":
"<fairway>", "slice": "chart", "id": "D<n>", "what": "<the contexts proposed, and the seam you are least
sure of>"}`. The board's *Waiting on you* shows it; `slice: chart` names no slice, so nothing waits on it.
A person confirms by setting the entry's `Status` to `confirmed by human <date>`, or overturns it with an
entry of their own; whoever records that answer writes the `decision` line carrying `D<n>`, which is what
closes the question.

## Pass one, here: the marks

A **mark** is one published contract another slice steers by. Propose these too, from the specification's
own nouns and verbs and from the surfaces `mock-states.md` approved: a screen showing an order needs
something that publishes one, and a state a person approved is a state something has to serve. Four kinds,
each typed in a file the mark names, because a contract a reader cannot open is not a contract:

| Kind | What it is | What it names |
|---|---|---|
| `event` | Something that happened, which other slices fold | a JSON Schema |
| `schema` | A shape published for others to read or write | a JSON Schema |
| `route` | An HTTP operation this feature publishes | an OpenAPI operation, as `specs/<feature>/contracts/openapi.yaml#/paths/...` |
| `port` | A named capability another context calls through | two JSON Schemas, its inputs and its outputs |

**A mark's file lives under `specs/<feature>/contracts/`**, which is Spec Kit's contracts directory and one
of the few feature-shared paths `check-slice-scope` lets a slice amend. Anywhere else and the slice that
owns the mark cannot touch its own contract: the scope gate refuses everything outside a deployable, so a
mark at the repository root would be a contract only the host could ever change.

Write the file as well as the entry. A mark naming a file nobody wrote is a promise that gets discovered at
the far end, by the fairway that believed it, and `check-chart` refuses it here instead.

**A mark is set once and never moved.** That is why this stage is a stop and not a form: every one of these
is a commitment another fairway builds against, and withdrawing one later is taken out of whoever steered
by it. `check-chart` refuses a deletion; an amendment is additive and goes in `fairways/<name>/chart.d/`.

## Pass two, at the split: the slices

The split fills in, per slice:

- `fairway` — which one of the fairways above it belongs to.
- `capability` — the chunk of work this slice is part of, the thing a person's demo is of. A capability is
  usually several slices. It is a product judgement and this is the moment to take it, because a person is
  here and will not reliably be later. `check-chart` refuses a slice without one.
- `sets` — the marks this slice publishes, from the `marks` block. One mark has exactly one setter.
- `steers_by` — the marks it builds against, which some other slice sets.

## The shape

```yaml
v: 1
feature: ordering
fairways:
  ordering: {context: ordering, service: apps/orders, owns: [apps/orders/**]}
  billing:  {context: billing,  service: apps/billing, owns: [apps/billing/**]}
marks:
  OrderPlaced:  {kind: event, schema: specs/ordering/contracts/events/OrderPlaced.json}
  POST /orders: {kind: route, operation: specs/ordering/contracts/openapi.yaml#/paths/~1orders/post}
  PricingPort:  {kind: port,  inputs: specs/ordering/contracts/ports/PricingPort.in.json, outputs: specs/ordering/contracts/ports/PricingPort.out.json}
slices:
  ORD-01: {fairway: ordering, capability: place-an-order, sets: [OrderPlaced, POST /orders], steers_by: []}
  BIL-01: {fairway: billing,  capability: bill-an-order,  sets: [InvoiceRaised], steers_by: [OrderPlaced]}
```

## Facing a person

Name everything twice the first time it comes up: the slipwai word and the ordinary one. "A fairway, which
is this bounded context's slices." "A mark, which is a contract another part of the work builds against."
"A capability, which is the chunk of work we would demo in one go." Nobody should have to learn a
vocabulary to answer a question about their own product.

## When it is done

`make check-chart` passes. That means every mark is typed and its file is in the tree, every mark steered by
has a setter, no mark has two, nothing has been withdrawn, every slice names its capability, and the
fairways are explained by a recorded context decision.
