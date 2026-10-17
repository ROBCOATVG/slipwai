# The rungs

A **rung** is how much of its past one service keeps. The `write-model` axis gives the rung, and it has two
answers:

- **`events`**: the log is the truth, and the current state is a fold of the log. This is event sourcing.
- **`state`**: the service keeps the current state. The events that the model names are contracts. The
  service raises them after the write, and never replays them.

**Event Modeling is the same on every rung.** The model, the slices, the commands, the read models and the
chart do not change. Only the write model underneath them changes.

```
make check-model
```

---

## The rung is per service

The rung belongs to a service, not to the project. A product can have one context that needs the log, beside
three contexts that do not. The catalogue could not say this until `write-model` became an axis of its own.

So `project.json` now holds two facts, where the keel once had one boolean:

| Fact | Scope | Where |
|---|---|---|
| Is there a model? | The project — it is the profile | `profile: event-modelling` |
| Is the log the truth? | One service | `deployables.<name>.selection.write-model`, mirrored as `eventSourced` |

A browser app has no write side, so it has no rung. Nobody asks a service of the standard profile for its
rung. The axis's `absent` value answers for it, and that value is `state`.

---

## It cannot be walked back

**After a service holds data, this is the one answer about the service that you cannot change back.** You
can fold a log down into tables whenever you decide to. You cannot turn state back into history that it
never recorded. Only one direction is cheap. So the log is the default, and `state` is the exception that you
must be sure about.

Two rules in the code enforce this:

- The axis declares itself **unprunable**. The keel refuses a catalogue whose `write-model` axis says
  anything else, and the refusal names the axis. A project that could later change its rung down could throw
  away its own history without anybody noticing. This is the one axis that `./init` must not answer down.
- Some language packages were written before the axis existed. At that time the store was the only place
  for events, so every project that those packages generated was event-sourced. The keel reads such a
  package as **answering `events`, and only `events`**. If the keel had only renamed the axis, the package
  would answer nothing. An axis that no backend answers falls to its `absent` value, which is `state`. The
  package would not disappear from the menu. Instead, it would change the rung of every project that it
  generated, and nobody would notice.

---

## What a backend declares

A rung decides *what the store must hold*. It does not decide which store it is: the `persistence` axis
already chose the store. So a backend declares two sets of rows against the same feature keys:

- its feature rows at the top, which an event-sourced service gets;
- the rows for the state-stored rung, under one `state` key beside them.

There is one member for each side, not two, because it is one question for each rung: what does this store
answer with?

**If a backend declares no `state` block, it answers a state-stored service with nothing.** That is the
honest shape of a language that has not written the skeleton yet. `slipwai package check` names this case.
This is better than a generated page with a gap in it.

---

## What the gate holds

`make check-model` reads a slice against the rung of its service. On a service that keeps no log, the gate
refuses a field that needs a log, and it names the field:

- a `guard` is a boundary over a tag query;
- `folds` is a replay.

A slice that names either field on a state-stored service describes machinery that the service does not
have.

**The chart does not see the rung.** The chart renderer reads `context`, `service`, event frames and
`reads`. It reads none of the fields that change between rungs. So the work divides in the same way whatever
rung each slice is on. A mixed project splits exactly like a project with one rung.

The naming rules are not rung rules, and they apply on both rungs. An event is a named business fact,
wherever it is kept.

---

## Adoption, and the map that deliberately omits it

An application that the keel did not make is `state` until a person says otherwise. Detection alone never
makes it `events`. A log that nobody vouched for is a guess that looks like a fact.

A survey *proposes* a rung when it finds an event-store dependency, and records the proposal on the
candidate. To record the rung, use `/ground`, or run:

```
slipwai adopt --confirm <name> --write-model events
```

**The convergence map never gets a row for the rung.** The map's ladders describe the keel's own shape: how
a repository is built, tested, released and laid out. A row there would tell every service to climb to the
log. The rung is a product decision for each service, and `project.json` already records it.

---

Next: [the chart and the mark](the-chart-and-the-mark.md) · [package kinds](package-kinds.md), and what a
language package has to answer · [bring an existing codebase](../guide/adopt.md)
