# Your first feature

**In about five minutes, you go from a passing gate to one slice demoed.** You have a repository, and
`make verify` passes. This page takes one feature from a sentence that you type to a working thing that a
person watches and accepts.

You run the commands that start with a slash — `/sail`, `/speckit-specify`, `/mockups` — inside your coding
agent, not in the shell. `./init` installed them.

---

## Sail it

```
/sail
```

That is all that you type. `/sail` does these things:

1. It finds the stage that you are at from the files on disk, not from anything that you tell it.
2. It runs that stage and every stage after it.
3. It then **takes the next ready slice, and you do not have to ask again**.

It stops when there are no more slices in the split, or when every slice that is left is blocked.

You can run `/sail` before any of this exists. This is a valid start, not an error. In an empty
repository, the first stage is the first one whose artefact is missing. That is the principles, so `/sail`
starts there.

There are three narrower forms, for when you want one fairway or one slice:

```
/sail fairway=booking     one fairway, and the others' ready slices are named and left
/sail booking             one feature, across whichever fairways its slices are in
/sail BOK-01              this slice, and nothing else
```

**Use the bare form normally.** The narrower forms are for when a second person works beside you. The next
page covers that.

## From the board

You can also drive the same ladder from the board's **Voyage** tab (run `slipwai`, then open Voyage).

A strip across the top shows the stages: PRD, init, constitution, specification, storyboard, event model,
chart and split, slices, and accepted. Each stage is *done*, *working*, *waiting on you* or *to do*. Each
stage shows the file that proves it and the command that moves it on. Nobody types a status on this strip.
A stage is done when its artefact exists. The page updates itself while the agent works in another window.

Each stop for a person has its button on the stage that it belongs to:

| Where the project is | What the Voyage tab offers |
| --- | --- |
| A specification is written | **Open spec**, which shows the specification rendered, not as markup. **Draw the surfaces**, which runs `make surfaces` to draw a wireframe for each screen and make a storyboard from them |
| The surfaces are drawn | **Approve storyboard**, or **Disapprove** with a reason. On the event-modelling profile, approval starts the model. On the standard profile, approval starts the chart |
| The model is in | **Continue the build**, which runs `make launch`: the chart, the split, and then the fleet casts off |
| The split is written and nothing is running | **Cast off the fleet**, which is `make cruise`. **Stop the fleet** asks every captain to stop at its next boundary |
| A further feature waits in `docs/intake/` | **Continue the next feature** |

Below the strip, the page shows:

- the model, in the draw.io viewer, with each slice coloured by its state
- the mock-ups, and the screens that each slice has actually rendered
- the slices in four columns, named as the split names them
- one **Settings** box, with a tab each for speed, fine tune, who answers at each stop, delegation and
  models

Each button runs a `make` target that you could type instead. The project's own scripts write every
setting. The board never writes a setting itself.

By default, the specification, the storyboard and the model each stop for you. To change this, open the
**Who answers** tab and set the row *The specification, storyboard and model* to **advance on their own**.
The board then starts each of those steps when the step before it ends well. [The board](the-board.md)
describes every control and the file that it writes. [The workflow](the-workflow.md) lists every step on
one page.

---

## What it is doing underneath

You do not type the commands below. `/sail` runs them, in this order, and starts at the first one whose
artefact is missing. This page shows them because, the first time, you want to see each artefact appear.
It also shows them because **three of these stages stop for a person**:

- You ratify the principles.
- You approve the mock-ups, one state at a time.
- A person who watches the demo run accepts it.

These stages are the ladder. `commands/sail.md` in your own project has the full text of the ladder.

**This figure shows all of it.** It shows where a slice comes from, and what one worker gets when it starts:

![From a spec to a delegate on the event-modelling profile: the specification, the mock-up review and the
event model once per feature; the chart and the split; then per slice, clearance, the claim and the
dispatch; then what one delegate is handed, the example map it opens with, and the marks it sets in its
own worktree](../images/spec-to-delegate-event-modelling.svg)

If your project answered no to Event Modeling, read
[the same figure with two boxes different](../images/spec-to-delegate-standard.svg). The two different
boxes are where the feature is typed, and where the examples in the example map come from. Everything else
is the same on both profiles: the chart, the split, clearance, the claim, the brief and the width.

### 1. Principles

`/speckit-constitution` fills `.specify/memory/constitution.md` and asks you to ratify it. These are the
rules that every later stage must follow: what a slice must be, what a test must prove, and what must not go
into domain code. If the constitution is absent, not filled in or not ratified, `/sail` starts here. Every
later stage is judged against the constitution, so it must come first.

### 2. Say what you are building

```
/speckit-specify  Guests book a table. A guest picks a time, we hold it, and the
                  restaurant sees it on tonight's list.
```

This writes `specs/booking/spec.md`. The specification describes the product in the language of the people
who want it, and it contains no technology. Then:

```
/speckit-clarify
```

Clarify writes the open questions back into the specification, under `## Clarifications`. `/sail` then
runs two things in parallel against that clarified version: `/speckit-checklist`, and the read-only
find-gaps survey. Checklist writes `specs/booking/checklists/`. When both have finished, the host
continues with:

```
/gaps
```

This runs the find-gaps conversation over the candidates that the survey found. It uses the clarifications
and the checklist as evidence, not as replacements for the conversation. For example: who cancels a
booking? What happens when two guests take the last table? Answer these questions now, in the
specification. Each question becomes a slice later. A question that you answer here costs one sentence.

To add a further feature, give it to `/sail` in the same conversation. Give either the request, or a
document that the session can read. `/sail` then:

1. writes the record under `docs/intake/`
2. asks whether it really is a new feature
3. runs Spec Kit's assessment before it writes the specification

When you answer `go`, the request becomes the next `specs/<feature>/spec.md`.

### 3. Mock-ups, approved one at a time

```
/mockups
```

This writes every screen state that the feature needs under `specs/booking/mockups/`: the empty state, the
loaded state, and the failed state. You approve them one state at a time. This stage stops for a person on
purpose. A screen that nobody looked at before it was built is the most expensive thing on this ladder to
find late. Later, a slice's `ui` frame points at the state that the slice builds.

### 4. Model it

Modelling is a skill, not a command, because it is a conversation. You and the agent name the commands,
events and read models together. On the event-modelling profile, the skill writes
`docs/event-model/model.yaml`. The file holds:

- the commands that somebody issues
- the events that record what happened
- the read models that the screens are built from
- the slice that each one belongs to

It is one file, and everything after it is rendered from it.

```console
$ make model
  wrote docs/event-model/model.svg
  wrote docs/event-model/slices/BOK-01.mmd
  wrote docs/event-model/model.html
  wrote README.md (event-model block)

model: 3 slices rendered. Open docs/event-model/model.html to browse it.
```

Open the page. It shows the timeline with a swimlane for each context. Each slice is a vertical stripe
through the timeline, and every command, event and read model is in its place:

![An event model with its timeline and swimlanes](../captures/event-model.png)

### 5. The fairways, charted from the model

- A **fairway** is the slices of one bounded context. One worker holds a fairway at a time.
- A **mark** is a typed contract, such as an event, a read model or a route. One fairway sets a mark, and
  other fairways steer by it.
- The **chart** names the fairways and the marks. It is written before the work is divided, because the
  way that you divide the work depends on the chart.

On the event-modelling profile, you do not write the chart. The model already gives each slice's context,
the events that it produces and what it reads. So the chart is rendered from the model:

```console
$ make chart
chart: specs/booking/chart.yaml written from the model — 2 fairways, 2 marks, 3 slices
$ make check-chart
check-chart: 1 chart(s), 2 marks, one setter each, every slice in a capability
```

On the standard profile, there is no model, so `/chart` writes the chart with a person present. On both
profiles, `make check-chart` checks the chart after that. It refuses the two mistakes that cost the most:

- a mark that nobody gave a type
- a mark that two slices both set

It also refuses fairways that no recorded decision explains. The model step writes that decision to
`specs/booking/decisions.md`: which bounded contexts the feature touches, and the seam table it was read
from.

**Each mark has one setter.** This rule is the reason that the rest works. If exactly one fairway sets
`BookingHeld`, every other fairway can be told as soon as it exists, and can start. They do not wait for a
branch to merge, and no second definition of the mark can appear anywhere.

### 6. Split it

```
/story-splitting
```

This divides one feature into slices. Each slice is a thin vertical cut that you can demo on its own. Each
slice writes its own row into the chart: its fairway, the capability that it is part of, the marks that it
sets, and the marks that it steers by.

```console
$ python3 scripts/agents/clearance.py
clearance: 1 of 3 slices start now in booking (slots: 3)
  start  BOK-01  prepare  — cleared; may prepare now — example map, the contract it sets, gaps — and implementation waits on its own mark-set for BookingHeld
  blocked   BOK-02  — BOK-02 steers by BookingHeld (set by BOK-01), and none of those is set yet
  blocked   AVA-01  — AVA-01 steers by BookingHeld (set by BOK-01), and none of those is set yet
```

**Cleared** means that every mark this slice steers by has been set. No mark is set yet, so only the slice
that waits for nothing can start. It starts in the *prepare* band, which is the stages before
implementation. This is why the line says what the slice can do now and what implementation still waits
for. A slice that is not cleared names what it waits for and who sets it. So "blocked" is never vague: it
always names a mark and its owner.

### 7. Then, per slice, until the demo

Each slice goes through these stages, in this order:

1. the example map
2. the slice's own gaps, plan and tasks
3. `/speckit-analyze`, which reads the specification, the plan and the tasks, and writes nothing
4. implementation, one RED-GREEN-REFACTOR increment at a time, with every example proven by a test
5. one review of the slice's own diff
6. the record of which attack-surface triggers the slice widened
7. the merge to trunk

Each stage writes its artefact under `specs/booking/slices/BOK-01/`. This is how `/sail` knows where it got
to if you close the terminal. Analyze is the exception: a clean reading means that there is no finding, so
there is no file.

## The demo stops for you

The demo is a run of the slice that an actor can see, in front of a person:

```
demo of BOK-01 — a guest holds 19:30 for four

  POST /bookings  { "at": "19:30", "covers": 4 }  →  201  held until 19:45
  the restaurant's list now shows it

accept this? [y/n/notes]
```

If you say yes, the line goes into the log. If you say no with notes, the notes go back into the slice.

You see a capability when its last slice has merged and its gates have passed. These are the gates:

- converge, and the gaps trace over the capability's whole diff
- the design review, from screenshots
- one adversary pass, where a slice widened a trigger
- the mutation run
- the hand's own walk through every example

Under the `open` release mode, a merge reaches the actor at once. So in that mode, converge, the gaps trace,
the design review and the walk also run for each slice. A slice that widened authorisation, identity or
money is also attacked before its push.

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

The timestamps are from that run. Your timestamps will be different. The harbourmaster wrote the last line,
not the captain. A captain holds no credential, so it asks the harbourmaster to merge. The harbourmaster
holds the credentials. It rebases the branch onto trunk, runs the whole gate there, and answers with the
commit.

**That is the fifteen minutes.** One slice is specified, modelled, charted, built, and accepted by a person
who watched it work. `/sail` has already taken the next ready slice.

---

## The one thing worth understanding before you go further

Look at the second line of that log. The slice wrote `set BookingHeld` when it **started**, in its own
worktree, before anything merged. Run clearance again. The slice in the other fairway that steers by
`BookingHeld` is now cleared:

```console
$ python3 scripts/agents/clearance.py
clearance: 2 of 3 slices start now in booking (slots: 3)
  start  BOK-02  implement  — cleared and sets nothing, so there is nothing to settle
  start  AVA-01  prepare  — cleared; may prepare now — example map, the contract it sets, gaps — and implementation waits on its own mark-set for TableTaken
  done   BOK-01  — merged at a1b2c3d4
```

One line in a log lets two more slices start. **Nothing merged.** A second fairway can start because a
contract exists and has one owner. This is why two people, or two agents, do not wait in a queue behind
each other's branches. Version 2 is built on this rule. The next page shows what it looks like with more
than one of you.

## Next

→ **[A second person joins](a-second-person.md)**: fairways, berths, and the board that shows both.

Other pages: [start here](start-here.md) · [let it cruise](let-it-cruise.md) ·
[bring an existing codebase](adopt.md) · [the workflow](the-workflow.md) · [the board](the-board.md) ·
[the vocabulary](../../GLOSSARY.md)
