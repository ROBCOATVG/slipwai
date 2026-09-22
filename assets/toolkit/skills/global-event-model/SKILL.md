---
name: global-event-model
description: >-
  Maintain this project's one global event model — the cumulative event modeling
  diagram in docs/event-model/. Use when a slice is discovered, planned, or
  shipped; when an event, command, read model, actor, or stream identity is
  added or renamed; when the diagram must be regenerated or is failing
  check-model; or when someone asks what the system's event model looks like.
  Triggers on: "update the event model", "add this slice to the model",
  "regenerate the diagram", "check-model is failing", "show me the event model",
  "what does the model say about this event". NOT for facilitating the modelling
  conversation itself — that is the `event-modeling` skill, which produces the
  content this skill records.
license: MIT
metadata:
  author: slipwai
  context: [event-model]
  phase: understand
capabilities: event-modelling, event-sourcing
---

# The global event model

**Value:** One picture of the whole system that is true. The model is cumulative and machine-checked, so
the second slice can see what the first committed to — which is where event-sourced systems actually fail.

`docs/event-model/model.yaml` is the source. `docs/event-model/README.md` is the full reference; read it
before a first entry. This skill is the operating procedure.

## Division of labour

| Skill | Produces |
|---|---|
| `event-modeling` | the modelling conversation: actors, events, commands, read models, slices, GWT |
| **this skill** | recording that outcome in the global model, and keeping it true afterwards |

Do not use this skill to *decide* what the events are. If a name is needed and the modelling conversation
has not happened, that conversation is the next task — never invent an event name to make the diagram
complete.

## When to touch the model

| Trigger | Do |
|---|---|
| A slice is discovered in conversation | add it with `status: proposed` |
| The modelling session settles it | `status: modelled`, and name the `actor` — and, with more than one service in `project.json`, the `service` that owns it |
| the installed Spec Kit plan command covers it | `status: planned`, and name what the append is guarded by — the `stream`, or a tag `guard` |
| The slice ships | `status: implemented`, and fill in `gwt` and `code` |
| An event, command, or read model is renamed | rename it here in the same commit |
| Stream identity, or the guard, changes | update `stream` or `guard` and say why in the commit message — this is not a cosmetic change |

Always finish with:

```bash
make model-drawio && make check-model && make check-drawio
```

and commit the regenerated `model.drawio` alongside the YAML: it is the one rendering that lives in the
repository, and `make verify` fails while it is older than the model. `make model` draws the Mermaid
diagrams and the browsable page on demand; they are not committed, and the pages workflow redraws them.

## Adding a slice

Append to `slices:` — **order in the file is order on the timeline**, so a new slice normally goes last.
Within `frames`, order is causal order.

```yaml
  - id: S7
    name: Cancel an order          # one capability. If it needs "and", it is two slices
    pattern: state-change
    status: modelled
    actor: Customer
    service: orders                # a key of project.json's deployables; required at `modelled` once there are two
    stream: order-{orderId}        # required before `planned`
    reads: []                      # a state-change slice reads nothing — see below
    frames:
      - { type: ui,  name: OrderDetailScreen }
      - { type: cmd, name: CancelOrder, data: "orderId, reason" }
      - { type: evt, name: OrderCancelled, data: "orderId, reason, cancelledAt" }
```

Never write a frame number. They are derived from slice and frame position.

## Which service owns a slice

`service` names the deployable the slice's code lives in — a key of `project.json`'s `deployables`. With
one service the field is optional, because there is nothing to decide. With two or more, `check-model`
requires it from `modelled` onward: a slice that names no owner lands in the first service by gravity, and
the second service — which someone added for a reason — stays an empty directory.

Decide it against what each service says it owns: the `purpose` on its manifest entry, listed under
*Bounded contexts* in `docs/architecture.md`. A slice that no recorded purpose covers, or a service whose
purpose nobody has recorded, is a question for the user, not a default to the first service. Several
services may share one bounded context, and one service may hold several (`contexts` on the manifest
entry; then each slice also names its `context`); `make model` renders one canvas per context on
`model.html`, projected from the slices in it — purpose, language, inbound commands, outbound events, read
models, streams — so the canvas is never edited by hand.

Which contexts a service holds is found in the model, not declared up front: when the slices fall into
clusters with vocabularies of their own — the same word meaning two things, or terms one cluster never
uses — those are the contexts (`skills/event-modeling/references/nine-steps.md`, *Apply Conway's Law*).
Record them on the service's manifest entry before the slices go to `modelled`, then place each slice with
`context:`. A list nobody has written is not a project with one context; it is a decision not yet taken.

## What the append is guarded by

A state-change slice declares one of two, and `planned` is where it is owed:

```yaml
    stream: order-{orderId}        # the version of one stream — the default, and most slices
```

```yaml
    guard:                         # a boundary drawn over tags, per decision
      by: [seat, hold]
      because: a seat may be claimed once, and a hold may not exceed its cap
```

`stream` is what nearly every slice wants: the append carries the version the decision was made at, and the
store refuses it if the stream moved. `guard` is for the constraint one stream cannot express — a capacity
and a member's own count, checked together, where either can change under you — where the append is refused
if anything matching a tag query arrived since. Never both: `one-guard-not-two`, because a conflict has to
mean one thing.

**What a decision folds must be what its append is guarded by.** That is one sentence with two checks
behind it. With `stream`, `folds-own-stream`: a Decider rehydrates from its own stream. With `guard`,
`folds-match-the-guard`: every folded event must carry an attribute identifying one of the guard's kinds. A
decision that folds an event its query cannot reach is guarded against something it never read, and nothing
downstream catches it — a Decider's own unit test hand-feeds it events no append could have loaded under
that guard.

`guard.because` is required for the reason `liveBudget.because` is: a boundary with no stated invariant is a
query somebody widened until the tests passed. The factory's own decision is
`docs/adr/0002-the-guard-a-slice-declares.md`.

## What an event carries, and which of it identifies something

An `evt` frame's `data` is prose — a worked example of the payload. An event may carry `attributes` instead,
which is the same list with somewhere to mark identity:

```yaml
      - type: evt
        name: SeatClaimed
        attributes:
          - { name: seatId,   identifies: seat }
          - { name: fromHold, identifies: hold }
          - { name: toHold,   identifies: hold }
          - { name: claimedAt, type: instant }
```

**`identifies` is the whole point of the field, and it names a kind rather than being a flag.** A
conditional append is guarded by a query over *tags*, and a tag is `<kind>:<value>` — so an event that says
which attributes identify a seat or a hold is an event whose tagging function can be transcribed from the
model instead of invented per project (`skills/event-sourcing/resources/event-store.md` has the worked
one). Two attributes may identify the same kind: `fromHold` and `toHold` are both a `hold`, the event
carries two `hold:` tags, and a query for either finds it. A flag could not express that, and it would
leave *what* is identified to be guessed from the attribute's name — which is how `customerId` on one event
and `buyer` on another become two kinds nobody meant.

**Tags themselves are never modelled.** They are a technical index over the log, not a fact about the
business, and there is no tag frame and no tag field. Identity is modelled; the index is derived.

Optional, and it belongs at `planned` rather than `modelled` — which attributes identify something is a
detail for the session with engineers, not for the discovery conversation. A slice whose events name none
keeps the default tagging function, which tags every event by its own stream, and everything written
against `append` and `expected_version` works exactly as before.

`check-model` refuses four things: `attributes` on a box that is not an event (a command's payload is what
a caller sends; the index is not derived from it), `data` and `attributes` on one frame (two places for one
list), the same attribute named twice, and an `identifies` that is not a lower-case kind.

## Pointing a white box at its mockups

A `ui` frame — and only a `ui` frame — may name the mocks for the screen it draws, one entry per state:

```yaml
      - type: ui
        name: OrderDetailScreen
        mockups:
          - { state: populated, at: docs/event-model/mockups/order-detail.html }
          - { state: empty,     at: docs/event-model/mockups/order-detail-empty.html }
          - { state: error,     at: https://www.figma.com/file/abc/Orders?node-id=12 }
```

**States, not one link.** A screen is almost never one picture, and the states nobody drew are where the
unmodelled behaviour hides. Listing them gives `/gaps` something to interrogate.

- `at` is repository-relative, like `gwt` and `code`, and must exist. An `http(s)` URL is taken on trust —
  this gate does no network.
- Once `render.page` is set, a repository-relative mock must be under `docs/event-model/`, because the
  publish workflow serves that directory and nothing else. `docs/event-model/mockups/` is the place.
- Nothing here reaches the diagram, so a mock changes no SVG. `model.html` is where the wireframes are
  drawn, so run `make model` to refresh it.

`model.html` shows each state as a wireframe under the slice — HTML mocks framed, images drawn, off-site
mocks named and linked. Do not invent a mock path to fill the field in: an absent design is a finding, and
*"no mockups yet"* under the screen is how it stays visible.

**Once the slice is `implemented`, the field is required** (`screen-states-recorded`), and the case that
brings you here is usually the one where nobody drew anything. That is fine — the states get designed while
the screen is built, and what this rule asks is that you write them back: commit the wireframe you settled on
under `docs/event-model/mockups/` and add its `mockups` entry in the same change as the code. *"No mockups
yet"* is an honest label for a screen that does not exist and a lie about one that shipped last month.

Its sibling is `screen-is-built`: an `implemented` slice's white box must appear in the source. **A white box
is a deliverable of the slice that models it** — the screen ships with its command, in the same change, even
when what its submit button reaches is not finished. Recording a slice as `implemented` when only the backend
was built is the drift these two rules exist to refuse.

## The four shapes, and what `check-model` refuses

| Pattern | Frames | `reads` | `materialisation` |
|---|---|---|---|
| `state-change` | `ui\|pcr → cmd → evt+` | **none** | none — it has no read model |
| `state-view` | `rmo → ui?` | required | required at `planned`: `live`, `inline` or `async` |
| `automation` | `rmo → pcr → cmd → evt+` | required | required at `planned`, and never `live` |
| `translation` | `evt(external) → pcr → cmd → evt+` | none | none |

Three rejections worth understanding rather than working around:

**A read model never feeds a command.** If you find yourself writing `rmo` then `cmd`, either a processor
belongs between them (making it an automation) or the command's input comes from the caller (making it a
state-change). The reason is consistency, not shape: a command may decide only from events it folded under
the same guard it appends with — its stream's expected version, or the tag query a conditional append is
guarded by — and a view something else maintains lags by design, with no guard over it.

**An automation needs all four boxes.** Triggering event, read model consulted, processor holding the
condition, resulting command. A command that simply appends two events is a state-change slice.

**A slice may only read events an earlier slice produces.** If `reads` names an event nothing produces, the
model is telling you a slice is missing — add it rather than deleting the read.

**A planned read model says where it lives.** `materialisation` is the read side of the question `stream`
asks on the write side: `live` folds the log on every query and stores nothing, `inline` writes the view in
the append's own transaction, `async` maintains it from a catch-up subscription with a checkpoint. It is
asked at `planned` because unasked, the answer is whichever one is nearest to hand rather than the one
somebody chose — and *the streams are short* becomes an assumption nothing measures. All three are built
from what the skeleton ships: the store's own unit of work for `inline` — the framework's transaction on the
JVM, so `@Transactional` is all a slice writes — and a checkpoint store with a catch-up runner for `async`,
started by the framework's own scheduler, plugin or lifespan rather than by a worker loop somebody writes. A `live` view therefore also names `liveBudget.events`, the ceiling one query may fold, and
`liveBudget.because`, why that ceiling holds in terms of the stream's own lifetime. An automation may not be
`live` at all: its read model is a todo list, losing it loses work nothing else records, and a per-request
fold cannot be spawned standalone to recover what a dead request abandoned.

## When `check-model` fails

| Rule | What it means |
|---|---|
| `diagram-current` | the committed picture is older than the YAML. `make model` and commit |
| `pattern-shape` | the frames do not match the pattern. Usually the pattern label is wrong, or it is two slices |
| `no-readmodel-to-command` | see above — this one is never a false positive |
| `reads-resolve` | a read names an event nothing produces |
| `reads-earlier-slice` | the producing slice is not earlier on the timeline |
| `model-matches-code` | an implemented slice's event or command appears nowhere in the source. Something was renamed in one place only |
| `guard-before-planning` | a state-change slice reached `planned` naming neither `stream` nor `guard`. One of them is what its append is checked against |
| `one-guard-not-two` | it names both. A conflict has to mean one thing |
| `folds-match-the-guard` | a slice with a tag `guard` folds an event none of its kinds can reach, so the decision is guarded against something it never read |
| `materialisation-before-planning` | a state-view or automation slice reached `planned` without saying where its read model lives. Answer it — `live`, `inline` or `async` — rather than shipping the per-query fold nobody chose |
| `todo-list-is-persisted` | an automation declared `materialisation: live`. A todo list is not a view: losing it loses work, and a fold that only knows this request's streams cannot sweep up an abandoned one |
| `live-fold-is-bounded` | a `live` state-view named no `liveBudget`. The ceiling one query may fold, and why it holds, are what make a per-query fold a decision rather than an assumption |
| `live-budget-bounds-a-live-fold` | `liveBudget` on a slice with no `live` fold. A materialised view's cost belongs to the subscription that maintains it — cap its lag instead |
| `materialisation-needs-a-read-model` | `materialisation` on a state-change or translation slice, which has none. A command decides from events it folded under the same guard it appends with, never from a maintained view |
| `service-named` | the project has more than one service and a modelled slice names none. Read the purposes in `project.json` and decide — or ask |
| `service-exists` | `service` names something `project.json` does not list as a service. A rename in one place only |
| `command-is-imperative` | a command is named as a fact. Commands ask, events record |
| `attributes-belong-to-an-event` | `attributes` on a box that is not an `evt`. The tag index is derived from events; identity marked elsewhere implies a guard that does not exist |
| `attributes-or-data` | a frame carries both. Keep the attributes — they say which of them identify something, and the diagram is rendered from them |
| `attribute-names-are-unique` | one attribute named twice. Two of the same kind are two names, both marked — that is how `fromHold` and `toHold` are both a `hold` |
| `mockup-is-a-screen` | `mockups` on a frame that is not a white box. Only a screen has a design |
| `mockup-exists` · `mockup-state-is-unique` | the path is not in the tree; or two mocks claim one state |
| `mockup-publishes-with-the-page` | `render.page` is set and the mock is outside `docs/event-model/`, which is all the workflow publishes |
| `screen-is-built` | an implemented slice's white box appears nowhere in the source. The screen was never built, or it is called something else in code |
| `screen-states-recorded` | an implemented white box has no `mockups`, so nothing records which of its states exist |

`model-matches-code` is the one that earns the whole mechanism. Do not "fix" it by dropping the slice to
`planned` — find out whether the model or the code moved, and correct the one that is wrong. The same goes
for `screen-is-built`: a slice with an unbuilt screen is not implemented, and demoting its status to silence
the gate is how a project ends up with a timeline of screens nobody can use.

The source it searches is `src/` and `tests/` plus every file any slice names in `code`, at any of the
extensions a frontend is written in. So a screen outside the template's trees still counts — as long as the
slice lists it, which `code` requires anyway.

## Reading the model

- `docs/event-model/model.html` — the browsable page: timeline, slice register, each slice on its own.
  Diagrams are click-to-zoom. Generated by `make model`; open it from disk.
- `docs/event-model/model.svg` — the committed picture. Embed it in Markdown as an image;
  **a fenced `eventmodeling` block will not render on GitHub**, whose Mermaid is older than 11.15.
- `docs/event-model/slices/<id>.mmd` — one slice, with the events it consumes.
- `docs/event-model/model.drawio` — the committed canvas: the same timeline, in the same order and the same
  colours, as one editable draw.io page. Open it in draw.io to work on it or present it; regenerate it with
  `make model-drawio` rather than editing it, because `make check-drawio` compares it byte for byte.

## Verification

- [ ] Every slice touched by this change has the right `status` for where it actually is
- [ ] No event name in the model is absent from the code of an implemented slice, and none was invented
- [ ] Every state-change slice at `planned` or beyond names what its append is guarded by — `stream` or `guard` — and folds only what that guard covers
- [ ] With more than one service, every slice at `modelled` or beyond names its `service`, and the choice followed a recorded purpose rather than the first directory
- [ ] `make check-model` passes, and the regenerated diagram is in the same commit
- [ ] The commit message says what changed about the *model*, not just that the diagram was regenerated
