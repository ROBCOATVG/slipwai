# Your first feature

**Five minutes from a green gate to one slice demoed.** You have a repository and `make verify` passes;
this page is one feature, from a sentence you type to a working thing you watch a person accept.

The commands with a slash — `/sail`, `/speckit-specify`, `/mockups` — are run inside your coding agent, not
in the shell. `./init` installed them.

---

## Sail it

```
/sail
```

That is the whole of it. `/sail` works out which stage you are at from what is on disk rather than from
anything you tell it, runs that stage and every stage after it, and then **takes the next ready slice
without being asked again**. It stops when the split is exhausted or everything left is blocked.

Being invoked before any of this exists is a valid start, not an error: with an empty repository the first
stage is the first one whose artefact is missing, which is the principles, and it begins there.

Three narrower forms exist for when you want one fairway or one slice:

```
/sail fairway=booking     one fairway, and the others' ready slices are named and left
/sail booking             one feature, across whichever fairways its slices are in
/sail BOK-01              this slice, and nothing else
```

**Bare is the normal form.** The narrower ones are for when a second person is working beside you, which
is the next page.

## From the board

The same ladder can be driven from the board's **Voyage** tab (`slipwai`, then Voyage). Across the top is a
strip of its stages — PRD, init, constitution, specification, storyboard, event model, chart and split,
slices, accepted — each *done*, *working*, *waiting on you* or *to do*, with the file that proves it and
the command that moves it. Nothing on it is a status anybody typed: a stage is done when its artefact
exists. The page keeps itself current while the agent works in another window.

Each stop for a person has its button on the stage it belongs to:

| Where the project is | What the Voyage offers |
| --- | --- |
| A specification is written | **Open spec**, rendered rather than as markup, and **Draw the surfaces**, which runs `make surfaces` to draw a wireframe for each screen and storyboard them |
| The surfaces are drawn | **Approve storyboard** or **Disapprove** with a reason. Approving starts the model on the event-modelling profile and the chart on the standard one |
| The model is in | **Continue the build**, which runs `make launch`: the chart, the split and the fleet cast off |
| The split is written and nothing is running | **Cast off the fleet**, which is `make cruise`; **Stop the fleet** asks every captain to stop at its next boundary |
| A further feature is waiting in `docs/intake/` | **Continue the next feature** |

Under the strip are the model in draw.io's own viewer with each slice coloured by where it stands, the
mock-ups and the screens each slice has actually rendered, the slices in four columns named as the split
names them, and one **Settings** box with a tab each for speed, fine tune, who answers at each stop,
delegation and models. Every button is a `make` target you could type instead, and every setting is
written by the project's own scripts, never by the board.

---

## What it is doing underneath

You do not type the commands below — `/sail` runs them, in this order, and enters at the first one whose
artefact is missing. They are here because the first time through you want to see each artefact appear,
and because **three of these stages stop for a person**: the principles are ratified by you, the mock-ups
are approved one state at a time, and the demo is accepted by somebody watching it run.

The stages are the ladder, and `commands/sail.md` in your own project carries its full text.

**All of it in one figure.** Where a slice comes from, and what one worker is handed when it starts:

![From a spec to a delegate on the event-modelling profile: the specification, the mock-up review and the
event model once per feature; the chart and the split; then per slice, clearance, the claim and the
dispatch; then what one delegate is handed, the example map it opens with, and the marks it sets in its
own worktree](../images/spec-to-delegate-event-modelling.svg)

A project that answered no to Event Modeling reads
[the same figure with two boxes different](../images/spec-to-delegate-standard.svg): what the feature is
typed in, and where the example map's examples come from. Everything else — the chart, the split,
clearance, the claim, the brief, the width — is the same on both.

### 1. Principles

`/speckit-constitution`, which fills `.specify/memory/constitution.md` and asks you to ratify it. These
are the rules every later stage is held to — what a slice must be, what a test must prove, what may not
enter domain code. A constitution that is absent, unfilled or unratified is where `/sail` starts, because
everything after it is judged against something.

### 2. Say what you are building

```
/speckit-specify  Guests book a table. A guest picks a time, we hold it, and the
                  restaurant sees it on tonight's list.
```

This writes `specs/booking/spec.md` — the product, in the language of the people who want it, with no
technology in it. Then:

```
/speckit-clarify
```

Clarify writes the open questions back into the specification, under `## Clarifications`. Against that
clarified snapshot, `/sail` runs `/speckit-checklist` and the read-only find-gaps survey in parallel.
Checklist writes `specs/booking/checklists/`. When both return, the host continues with:

```
/gaps
```

which runs the find-gaps conversational loop over the survey's candidates, using the clarifications and
checklist as evidence rather than substitutes. Who cancels a booking? What happens when two guests take the
last table? Answer them now, in the specification, because every one of them becomes a slice later and a
question answered here costs a sentence.

A further feature is handed to `/sail` in the same conversation: the request, or a document that session
can read. `/sail` writes the record under `docs/intake/`, asks whether it is really a new feature, and
runs Spec Kit's assessment before it specifies. A `go` is what becomes the next `specs/<feature>/spec.md`.

### 3. Mock-ups, approved one at a time

```
/mockups
```

Every screen state the feature needs, written under `specs/booking/mockups/` and approved by you one state
at a time — the empty one, the loaded one, the one that failed. This stage stops for a person on purpose:
a screen nobody looked at before it was built is the most expensive thing on this ladder to discover late,
and a slice's `ui` frame later points at the state it is built to.

### 4. Model it

Modelling is a skill rather than a command, because it is a conversation: you and the agent name the
commands, events and read models together. On the event-modelling profile it writes
`docs/event-model/model.yaml`: the commands somebody issues, the events that are the record of what happened, the read models the screens are built from, and which slice
each belongs to. One file, and everything downstream is rendered from it.

```console
$ make model
  wrote docs/event-model/model.svg
  wrote docs/event-model/slices/BOK-01.mmd
  wrote docs/event-model/model.html
  wrote README.md (event-model block)

model: 3 slices rendered. Open docs/event-model/model.html to browse it.
```

Open it. You get the timeline with a swimlane per context, each slice as a vertical stripe through it, and
every command, event and read model in its place:

![An event model with its timeline and swimlanes](../captures/event-model.png)

### 5. The fairways, charted from the model

A **fairway** is one bounded context's slices, held by one worker at a time; a **mark** is a typed contract — an event,
a read model, a route — that one fairway sets and others steer by. The **chart** names them, and it is
written before the work is cut up, because how you cut the work up depends on it.

On the event profile you do not write the chart. The model already says each slice's context, the events
it produces and what it reads, so the chart is rendered:

```console
$ make chart
chart: specs/booking/chart.yaml written from the model — 2 fairways, 2 marks, 3 slices
$ make check-chart
check-chart: 1 chart(s), 2 marks, one setter each, every slice in a capability
```

On the standard profile there is no such artefact, so `/chart` writes it with a person present. Either way
`make check-chart` holds it afterwards, and it refuses the two mistakes that cost the most: a mark nobody
typed, and a mark two slices both set.

**One setter per mark.** That rule is the whole reason the rest of this works. If exactly one fairway sets
`BookingHeld`, then everyone else can be told the moment it exists and can start — without waiting for a
branch to merge, and without a second definition of it appearing anywhere.

### 6. Split it

```
/story-splitting
```

One feature becomes slices, each a thin vertical cut that is demoable on its own, and each one writes its
own row into the chart: the fairway it belongs to, the capability it is part of, the marks it sets, the
marks it steers by.

```console
$ python3 scripts/agents/clearance.py
clearance: 1 of 3 slices start now in booking (slots: 3)
  start  BOK-01  prepare  — cleared; may prepare now — example map, the contract it sets, gaps — and implementation waits on its own mark-set for BookingHeld
  blocked   BOK-02  — BOK-02 steers by BookingHeld (set by BOK-01), and none of those is set yet
  blocked   AVA-01  — AVA-01 steers by BookingHeld (set by BOK-01), and none of those is set yet
```

**Cleared** means every mark this slice steers by has been set. Nothing has been set yet, so only the slice
that waits for nothing may start — and it starts in the *prepare* band, the stages before implementation,
which is why the line says what it may do now and what implementation still waits on. A slice that is not
cleared names what it is waiting for and who is setting it, so "blocked" is never a mood — it is a mark
with an owner.

### 7. Then, per slice, until the demo

The example map, the slice's own gaps, plan and tasks, then `/speckit-analyze` — a read of the spec, the
plan and the tasks, writing nothing — and only then implementation, one RED-GREEN-REFACTOR increment at a
time, every example proven by a test, one review of the slice's own diff, the record of which attack-surface
triggers it widened, and the merge to trunk. Each writes its artefact under `specs/booking/slices/BOK-01/`, which is how `/sail`
knows where it got to if you close the terminal. Analyze is the exception: a clean reading is the absence
of a finding, and there is no file.

## The demo stops for you

An actor-visible run of the thing, in front of a person:

```
demo of BOK-01 — a guest holds 19:30 for four

  POST /bookings  { "at": "19:30", "covers": 4 }  →  201  held until 19:45
  the restaurant's list now shows it

accept this? [y/n/notes]
```

Say yes and the line goes in the log. Say no with notes and they go back into the slice. You are shown a
capability once its last slice has merged and its gates have cleared: converge and the gaps trace over its
whole diff, the design review from screenshots, one adversary pass where a slice widened a trigger, the
mutation run, and the hand's own walk of every example. Under the `open` release mode, where a merge reaches
the actor at once, converge, the gaps trace, design review and walk run per slice as well, and a slice that
widened authorisation, identity or money is attacked before its push.

```console
$ slipwai fleet booking
booking: the last 6 line(s) its captain wrote
  2026-10-08T09:14:48Z  claimed BOK-01
  2026-10-08T09:14:48Z  set BookingHeld — BOK-01
  2026-10-08T09:14:49Z  still going, 42k spent
  2026-10-08T09:14:49Z  demo of BOK-01: accepted
  2026-10-08T09:14:50Z  asked to merge: merge slice/BOK-01 into trunk after the full gate
  2026-10-08T09:14:58Z  merged BOK-01 as a1b2c3d4
```

The timestamps are that run's; yours will be your own. The last line is the harbourmaster's work, not the
captain's: a captain holds no credential, so it asks, and the thing that holds them rebases the branch onto
trunk, runs the whole gate there, and answers with the commit.

**That is the fifteen minutes.** One slice, specified, modelled, charted, built, and accepted by a person
who watched it work — and `/sail` has already taken the next ready slice.

---

## The one thing worth understanding before you go further

Look at the second line of that log. `set BookingHeld` was written when the slice **started**, in its own
worktree, before anything merged. Run clearance again and the slice in the other fairway that steers by
`BookingHeld` is now cleared:

```console
$ python3 scripts/agents/clearance.py
clearance: 2 of 3 slices start now in booking (slots: 3)
  start  BOK-02  implement  — cleared and sets nothing, so there is nothing to settle
  start  AVA-01  prepare  — cleared; may prepare now — example map, the contract it sets, gaps — and implementation waits on its own mark-set for TableTaken
  done   BOK-01  — merged at a1b2c3d4
```

One line in a log, and two more slices may start. **Nothing merged.** A second fairway can start on the
strength of a contract that exists and has one owner, which is why two people — or two agents — are not
queueing behind each other's branches. That is the claim
version 2 is built on, and the next page is what it looks like with more than one of you.

## Next

→ **[A second person joins](a-second-person.md)** — fairways, berths, and the board that shows both.

Other pages: [start here](start-here.md) · [let it cruise](let-it-cruise.md) ·
[bring an existing codebase](adopt.md) · [the vocabulary](../../GLOSSARY.md)
