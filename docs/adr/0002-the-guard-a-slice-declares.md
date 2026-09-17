# 0002. A slice declares the guard its append is checked against, and identity is modelled while tags are not

Date: 2026-09-10

## Status

Accepted. Completes the half [`0001`](0001-a-dcb-capable-log.md) recorded as owed.

## Context

`0001` made the log Dynamic-Consistency-Boundary-capable and deliberately stopped there: *"the model contract
is not changed by this ADR… `stream` stays required of a state-change slice at `planned`, and `folds` still
means the slice's own stream."* So a project could hold a boundary the model had no way to describe. Two
rules demanded a decision DCB says does not exist:

- `stream-identity-before-planning` refused a planned state-change slice with no `stream`.
- `folds-own-stream` refused a folded event produced on any other stream.

Under a boundary drawn out of tags there is no stream to name, and the events a decision folds are the ones
its query reaches — which may be produced anywhere. Left alone, the gate would have made the capability
unusable: a slice using it either lied about a stream or could not be planned.

Two things were read as source before this was taken, and both changed its
shape:

- **Dilger, *How does DCB affect Event Modeling***: *"How do you model Tags in the Event Model? You don't…
  it's not essential to the business, it's a technical optimization."* Identity is expressed as metadata on
  an event's attributes, and the tags are derived from it.
- **`sliceworkz/eventmodeling`** (LGPL-3.0, read for its shapes and not copied) makes the invariant explicit
  in code: the optimistic-lock filter of a command is *"the union of the eventQueries the models were
  ACTUALLY read with"*. What a decision reads is what its append must be guarded by — which is not a new
  rule but the general form of the one we already had. Its `Entity` type also showed the trap: keying one
  tag kind to one attribute cannot express a transfer, and asking such an index "which account?" returns an
  arbitrary one of the two.

## Decision

1. **A state-change slice declares one guard, and `planned` is where it is owed.** Either `stream` — whose
   version the append carries, unchanged and still the default — or `guard`, a boundary over tags:

       guard:
         by: [seat, hold]
         because: a seat may be claimed once, and a hold may not exceed its cap

   `guard-before-planning` replaces `stream-identity-before-planning`, which is a rename of the finding and
   not a loosening of it: both answers are unmigratable once there is history, so the question is asked at
   the same status it always was. `one-guard-not-two` refuses both at once, because a conflict has to mean
   one thing.
2. **`guard.because` is required, for the reason `liveBudget.because` is.** A boundary with no stated
   invariant is a query somebody widened until the tests passed.
3. **What a decision folds must be what its append is guarded by.** With `stream`, that is
   `folds-own-stream`, unchanged. With `guard`, it is `folds-match-the-guard`: every folded event must carry
   an attribute identifying one of the guard's kinds. A decision folding an event its query cannot reach is
   guarded against something it never read, and no unit test can catch it — a Decider's test hand-feeds it
   events that no append could have loaded under that guard.
4. **Identity is modelled; tags are not.** An `evt` frame may carry `attributes`, each optionally naming the
   kind it `identifies`. There is no tag frame and no tag field: a tag is `<kind>:<value>`, derived from
   those marks by the project's tagging function, which the `event-sourcing` skill now ships worked in every
   language. Optional, and asked at `planned` rather than `modelled` — Dilger's Discovery / Detailed-Modeling
   split, and the same status at which `materialisation` is asked.
5. **`identifies` names a kind rather than being a flag.** Two attributes may identify the same kind —
   `fromHold` and `toHold` are both a `hold` — so the event carries two `hold:` tags and a query for either
   finds it. A flag cannot express that, and it leaves *what* is identified to be inferred from the
   attribute's name, which is how `customerId` on one event and `buyer` on another become two kinds nobody
   meant.
6. **The default does not move.** `stream` stays what every generated slice declares, `append` stays what
   every generated slice calls, and a project that never draws a tag boundary sees one new optional field it
   never fills in.

## Consequences

- A slice can now describe the constraint `0001` made the store capable of holding, and `make check-model`
  holds the description to the code rather than blocking it.
- **A model already written stays valid.** Every existing slice names a `stream` and folds its own stream's
  events; nothing here asks for more of it. The one visible change is a finding's name.
- `folds-match-the-guard` needs the producing event's `attributes` to say anything, so a `guard` without
  them reports every fold. That is the intended order — mark identity, then draw the boundary — and the
  finding says so.
- The model still says nothing about *how* the guard is enforced. `append_if` under `SERIALIZABLE` is the
  Postgres adapter's business, and a project that moves to another store keeps its model.
- **What is still not modelled, on purpose:** the criteria query itself. Dilger derives it from the GWT's
  GIVEN, and that derivation is the thing worth having; `guard.by` is the boundary's shape, not its
  generated form. Recorded as future work rather than taken here.
