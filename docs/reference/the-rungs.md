# The rungs

A **rung** is how much of its past one service keeps. It is answered on the `write-model` axis, with two
answers:

- **`events`** — the log is the truth, and current state is a fold of it. Event sourcing.
- **`state`** — the service keeps current state, and the events the model names are contracts raised after
  the write and never replayed.

**Event Modeling is the same on every rung.** The model, the slices, the commands, the read models and the
chart are unchanged; what changes is the write model underneath them.

```
make check-model
```

---

## The rung is per service

Not per project. A product may own one context that earns the log beside three that do not, and the
catalogue forbade saying so until `write-model` became an axis of its own.

So two facts live in `project.json` where the keel had one boolean:

| Fact | Scope | Where |
|---|---|---|
| Is there a model? | The project — it is the profile | `profile: event-modelling` |
| Is the log the truth? | One service | `deployables.<name>.selection.write-model`, mirrored as `eventSourced` |

A browser app has no write side to be a rung of. A service of the standard profile was never asked, and the
axis's `absent` answers for it — `state`.

---

## It cannot be walked back

**This is the one answer about a service that cannot be walked back once it holds data.** A log folds down
into tables whenever you decide it should; state cannot be turned back into history it never recorded. Only
one direction is cheap, so the exception is the answer to be sure about and the log is the default.

Two rules in the code hold that:

- The axis declares itself **unprunable**. A catalogue whose `write-model` axis says anything else is
  refused, by name: a project that could answer the rung down later would be a project that could silently
  throw its own history away. It is the one axis `./init` may not answer down.
- A language package written before the axis existed — when the store was the only place events could live,
  so every project it generated was event-sourced — is **read as answering `events`, and only `events`**.
  Renaming the axis alone would have left it answering nothing, and an axis no backend answers falls to its
  `absent`, which is `state`. The package would not have dropped off the menu; it would quietly have changed
  the rung of every project generated with it.

---

## What a backend declares

A rung settles *what the store is asked to hold*, not which store it is — the `persistence` axis has already
chosen that. So a backend declares both sets against the same feature keys: its feature rows at the top,
which are what an event-sourced service is given, and the state-stored rung's rows under one `state` key
beside them. One member per side and not two, because it is one question asked once per rung: what does this
store answer with.

**A backend that declares no `state` block answers a state-stored service with nothing.** That is the honest
shape of a language that has not written the skeleton yet, and `slipwai package check` names it — rather
than a generated page with a hole in it.

---

## What the gate holds

`make check-model` reads a slice against the rung its service is on. A field that needs a log is refused by
name on a service that keeps none: a `guard` is a boundary over a tag query and `folds` is a replay, and a
slice naming either on a state-stored service is describing machinery that service was never given.

**The rung is invisible to the chart.** The chart renderer reads `context`, `service`, event frames and
`reads`, and none of the fields that move between rungs — so the division of work is the same whichever rung
either slice is on, and a mixed project splits exactly like a pure one.

The naming rules are not rung rules and hold across both: an event is a named business fact wherever it is
kept.

---

## Adoption, and the map that deliberately omits it

An application the keel did not make is `state` until a person says otherwise, and never `events` by
detection alone — a log nobody vouched for is a guess wearing a fact's clothes. A survey *proposes* the rung
off an event-store dependency, on the candidate; what records it is `/ground` or:

```
slipwai adopt --confirm <name> --write-model events
```

**No row for the rung is ever added to the convergence map.** The map's ladders are the keel's own shape —
how a repository is built, tested, released, laid out — and a row there would be telling every service to
climb to the log. The rung is a product decision per service, and `project.json` is already its record.

---

Next: [the chart and the mark](the-chart-and-the-mark.md) · [package kinds](package-kinds.md), and what a
language package has to answer · [bring an existing codebase](../guide/adopt.md)
