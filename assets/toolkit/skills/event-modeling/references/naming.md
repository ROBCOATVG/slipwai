# Naming events

An event is a **named business fact, in the past tense, in the words the business already uses**. That one
sentence decides more about how long a model stays readable than any other rule here, because the names
outlive everything around them: the screens get redesigned, the services get split, the database gets
replaced, and `OrderPlaced` is still `OrderPlaced`.

Two of the rules below are gates — `make check-model` refuses a model that breaks them, on either rung.
The rest are judgement, written out here because a gate cannot hold them.

## The verb is what happened, not what the table did

`check-model`: **`event-is-not-crud`**

| Good | Bad | Why |
|---|---|---|
| `OrderPlaced` | `OrderCreated` | *Created* is what the row did. *Placed* is what the customer did, and it is the word they would use. |
| `OrderCancelled`, `OrderShipped`, `OrderRefunded` | `OrderUpdated` | One bad name hides three different facts. A reader of `OrderUpdated` has to open the payload to find out which thing happened — and a subscriber has to too. |
| `SubscriptionExpired` | `SubscriptionChanged` | *Changed* says a field moved. *Expired* says why, and says it happened on its own rather than because somebody asked. |
| `EmployeeResigned`, `EmployeeDismissed` | `EmployeeDeleted` | Nobody is deleted. The two facts have different consequences — notice periods, rehire eligibility — and one name erases the difference. |
| `AddressCorrected` | `AddressModified` | *Corrected* says the old one was wrong. *Modified* also covers moving house, which is a different fact with different consequences for anything already shipped. |

Dudycz calls the bad column **property sourcing**: the model ends up recording that a column changed, which
is what the table already knew, and the one thing a reader wanted — what happened — is nowhere. It is the
single most common way a reverse-engineered model goes wrong, which is why `/observe` reads a status
transition and proposes the business's name for it rather than the column's.

**The exemption, and it is real.** Some things honestly are field updates. A CMS page is saved. A feature
flag is toggled. A user changes their display name. Forcing a business verb onto those invents a fact
nobody has. The frame says so:

```yaml
- type: evt
  name: PageUpdated
  crud: true
  because: a CMS page is a document somebody edits; there is no business event under the save
```

`because` is required, because without it the exemption is the one everything gets.

## An event is something that happened, not something that did not

`check-model`: **`event-is-not-negative`**

| Good | Bad | Why |
|---|---|---|
| `ShipmentFailed` with `reason` | `OrderNotShipped` | Nothing raises an absence. Something went wrong, and the useful fact is which thing — carried as an attribute, not as five negative event names. |
| `PaymentDeclined` with `reason` | `PaymentNotReceived` | *Declined* is a thing the gateway did at a time. *Not received* is a state of the world that was true before the system started and will be true again. |
| `HoldExpired` | `SeatNeverClaimed` | An expiry is an event a timer raises. A never is a report. |

If the absence genuinely matters and nothing caused it, what you have is a **read model** answering *which
of these has not happened yet* — which is a `state-view` slice, not an event.

## A name already in a log is kept

A stored event cannot be renamed, so neither gate asks anything of one that was written before the gate
existed. A project that crossed from version 1 holds `.specify/event-names-from.json`, written once by
`slipwai migrate`: the events of the slices that were `implemented` at the crossing. `check-model` passes
exactly those names on exactly these two rules, and holds every event named afterwards to both. A project
made under the rules has no such file and no such names. It is a record of what was in the log, not a list
to add to: a new `OrderCreated` is renamed, or says `crud: true` and why.

## The rest, which are judgement

**No `Event` suffix.** `OrderPlacedEvent` says twice what the type already says once. The model has four
box types and the diagram colours them; a suffix in the name is noise in every lane it appears in.

**No broker, no table, no technology in the name.** `OrderPlacedKafkaMessage`, `OrdersRowInserted`,
`OrderPlacedV2Topic`. The name is a business fact; where it travels and what version of its schema is
current are facts about the plumbing, and the plumbing is replaced more often than the fact.

**Past tense, always, and the right past tense.** `PlaceOrder` is the command and `OrderPlaced` is the
event. If a name reads as an instruction, it is in the wrong box.

**Name the specific thing, not the category.** `SeatReserved` beats `InventoryChanged`. The test is
whether somebody who knows the business but not the code can say what happened from the name alone.

**One fact, one event.** If a name needs *and* in it — `OrderPlacedAndPaid` — it is two events, and
modelling them as one means nothing downstream can react to the first without the second.

**The name survives being wrong.** An event that was raised is a fact, and facts are not edited. If a
better name is found later, the new name goes on new events; the old ones keep theirs. On the event-sourced
rung this is forced — the log is immutable. On the state-stored rung it is a discipline, and the reason is
the same: anything that consumed the old name consumed it under that name.

## The honesty rule, which applies to the whole model

**No event may claim history the system did not record at the time.** An event raised from now on is a true
event. Backfilling ten years of `OrderPlaced` from a `created_at` column produces a log that reads as
history and is a reconstruction — with every field the row does not hold invented, and no way for a later
reader to tell which is which. Where the past matters and was not recorded, say so in a read model built
from the tables, labelled as what it is.
