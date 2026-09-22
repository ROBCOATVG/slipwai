# The global event model

*Event profile only.* `docs/event-model/model.yaml` is the source of truth for the commands, events, read
models and actors of the whole system — and `make model` draws it, `make check-model` refuses to let it
drift from the code, and `make model-drawio` writes the one rendering that is committed, which
`make check-drawio` holds current on every commit.

- [What Event Modeling is](#what-event-modeling-is)
- [Why one model rather than one per feature](#why-one-model-rather-than-one-per-feature)
- [What `make model` produces](#what-make-model-produces)
- [What `make check-model` enforces](#what-make-check-model-enforces)
- [The committed canvas: `make model-drawio` and `make check-drawio`](#the-committed-canvas-make-model-drawio-and-make-check-drawio)
- [What a slice owes: its guard, and where its read model lives](#what-a-slice-owes-its-guard-and-where-its-read-model-lives)
- [Publishing the page](#publishing-the-page)
- [From a box to a file](#from-a-box-to-a-file)

## What Event Modeling is

[**Event Modeling**](https://eventmodeling.org/) is Adam Dymitruk's method for designing a system as **one
timeline of how information changes over time**, built in a facilitated session with the people who own the
words. It is not a diagramming notation bolted onto a design that already exists: the timeline *is* the
design, and its output is the shape of the write model. The
[cheat sheet](https://eventmodeling.org/posts/event-modeling-cheatsheet/) is the one-page version;
[What is Event Modeling](https://eventmodeling.org/posts/what-is-event-modeling/) is the introduction.

The model is read left to right as time, in **three swimlanes**:

| Lane | Holds |
|---|---|
| UI / Automation | What the actor sees, and the processors that act without one |
| Command / Read model | The intent being submitted, and the projections that inform a view |
| Events | The facts, in the order they happened — the backbone of the model |

**The colour grammar is load-bearing**, and `make model` renders exactly it, so the legend cannot drift from
the boxes:

| Element | Colour | Means |
|---|---|---|
| Event | Orange | A past-tense fact somebody appended. Permanent |
| Command | Blue | An intent that may be rejected. Never stored |
| Read model | Green | A fold over events, serving a view or a processor. **Never feeds a command** |
| UI / wireframe | White | What the actor sees at that point in time |
| Processor | Purple | Automation: the conditional logic between an event and the next command |

**Every slice is exactly one of four patterns** — and a vertical slice is the unit of work: one slice, one
plan, one set of Given/When/Then scenarios, one shippable change.

| Pattern | Shape | Reads |
|---|---|---|
| **State change** | `ui\|processor → command → event+` | Nothing — the command takes user input and folds the events its own guard reaches |
| **State view** | `events → read model → ui?` | The events it folds |
| **Automation** | `event → read model → processor → command → event+` | What triggers it |
| **Translation** | `external event → processor → command → event+` | Nothing — the external event is its input |

Slices that share an event schema are independent: the schema is the contract between them, so neither has
to be built first. That is what makes the model a plan for delivery and not only a picture — and it is why
`/drive` runs ready slices concurrently only once each is `planned`: the attributes, the guard and the example
map are the contract, and a `modelled` slice's contract may still move ([delivery-loop.md](delivery-loop.md),
*Who runs each stage*).

Two rules the shapes encode, both checked mechanically by `make check-model`:

- **A read model never feeds a command.** The reason is consistency rather than shape: a command may decide
  only from events it folded **under the same guard it appends with** — its stream's expected version, or
  the tag query a conditional append is guarded by — and a view something else maintains lags by design,
  with no guard over it. That is how the last ticket gets sold twice. In an automation, the processor sits
  between them and holds the condition, and the read model it consults is the trigger rather than the
  decision.
- **An automation has all four boxes** — event, read model, processor, command — or it is not an automation.

In a generated project, the facilitated session is `skills/event-modeling/SKILL.md` (the nine-step
procedure), recording its outcome is `skills/global-event-model/SKILL.md`, and the schema reference is the
project's own `docs/event-model/README.md`.

## Why one model rather than one per feature

A plan covers a slice. A spec covers a feature. Neither survives the next feature — and event-sourced
systems fail precisely at the joins, where the thing being violated is not in the artifact you are looking
at:

- the second slice folds the first slice's events, and discovers they do not carry what it needs;
- the fourth discovers that the stream identity chosen in the first was the wrong consistency boundary.

So the model is **global and cumulative**. Each slice adds to the same timeline, which means the diagram can
answer *"what does this event already mean, and who reads it?"* **before** a new slice commits to an answer.

## What `make model` produces

```sh
make model            # regenerate every artifact from model.yaml
make model PNG=1      # and a raster copy
```

| Artifact | Is |
|---|---|
| `model.mmd` | The Mermaid source for the whole timeline |
| `model.svg` | The rendered timeline |
| per-segment `.mmd` / `.svg` | The timeline cut into readable segments, for a model too wide to take in at once |
| `model.png` | A raster copy, on `PNG=1` |
| `model.html` | **The browsable page** — the timeline, the slice register, and each slice on its own |
| the README section | Regenerated in place, embedding the segments or linking the published page |

The browsable page is self-contained and **nothing on it is scripted** — the zoom is a `:checked` rule and
the filters are `:has()`. That is a test rather than a preference: the page has to work from a `file://`
path, inside a review attachment, and on paper, and a page that needed JavaScript to be navigable would be
blank in half the places it gets opened. The SVGs are inlined for the same reason. Colours are Mermaid's own
event-modeling defaults, so the legend cannot drift from the boxes.

Rendering fetches the Mermaid CLI into a gitignored prefix rather than committing it as a devDependency,
because it pulls a headless browser — making every `npm install` pay for that so one person can regenerate
a diagram is a poor trade. The prefix also lets `make model` apply mermaid-js/mermaid#7986 until mermaid-cli
ships it, so grouped swimlanes work in the committed SVG.

`render.lanes` chooses what each band's swimlanes group by, independently, because Mermaid resolves a
namespace within a band rather than across the diagram. The defaults are the notation's own picture:
`ui: actor` puts a lane per actor across the top, `events: stream` a lane per stream across the bottom, and
`data: none` leaves the commands and read models in one. An event's lane is its stream identity with the
placeholder removed, so `order-{orderId}` is the `order` lane. Set `data: context` — or `ui: context` — once
the *Apply Conway's Law* step has found contexts worth drawing.

## What `make check-model` enforces

`check-model` needs no browser at all, which is why *it* is the gate that runs in CI and inside
`make verify`. Each slice's `status` tightens what the model must carry, and the check enforces the
tightening rather than trusting it:

| Status | Means | The model must then carry |
|---|---|---|
| `proposed` | Discovered in conversation, not yet agreed | Its pattern and frames |
| `modelled` | The modelling session settled it | An `actor` for state-change and state-view slices, and the owning `service` once `project.json` lists more than one — plus the `context`, where that service holds several |
| `planned` | A plan covers it | What a state-change slice's append is guarded by — `stream`, or a tag `guard`, never both — and `materialisation` for any slice that holds a read model |
| `implemented` | It ships | `gwt` and `code` paths that exist, and events that actually appear in the source |

That last row is what keeps the diagram honest. **Rename an event in the code and leave the model behind,
and `check-model` fails with the name it could not find.**

It also refuses a slice that leaves its owning service or bounded context unsaid once there is more than one
to choose between — because defaulting to the first service in the list is how a model quietly stops
describing the system. See [Services](services.md).

## The committed canvas: `make model-drawio` and `make check-drawio`

Everything `make model` writes is gitignored. It has to be: Mermaid draws through a headless Chromium, so
`make verify` — which must never need a browser — cannot check that a rendered diagram still matches the
model, and a diagram nothing checks is a diagram that quietly stops matching `model.yaml`. Which is exactly
how a model stops being trusted.

So the event profile has a second rendering with a property none of the Mermaid artifacts have: it is
committed, and a gate proves it current. `make model-drawio` writes `docs/event-model/model.drawio`, one
editable draw.io canvas of the whole timeline. A `.drawio` file is plain XML, and producing one is arithmetic
and a string — no browser, no account, no credential, no network — so `check-drawio` can regenerate it in
memory and compare, and it sits **inside `verify`**. Its failure names the fix (`Run make model-drawio and
commit the result`), and tells a missing file from a stale one.

| | Mermaid | draw.io |
|---|---|---|
| Produces | slice diagrams, README segments, whole-timeline SVG, HTML page | one editable canvas |
| Lives | gitignored, regenerated on demand | committed |
| Needs | a headless browser | Node, and nothing else |
| Currency | unchecked | **`check-drawio`, inside `verify`** |
| Good for | reading, embedding, GitHub | working on, annotating, presenting |

Neither replaces the other. `make model` and everything it writes are unchanged, the README's generated
block still renders, and `check-model` still asks only its own question — is the model valid, and does the
code agree with it — which is a different question from whether a drawing is current.

The pipeline is four files under `assets/toolkit/scripts/event-model/`, and the split is what keeps the next
change cheap: `board-plan.ts` is pure geometry — every box, label and arrow with a centre, a size and a
colour, reading no file, no clock and no network, and knowing no output format; `drawio.ts` is a pure
`BoardPlan` → mxGraph XML string; `render-drawio.ts` is the entry point that writes the file or `--check`s
it; `example-model.ts` is the worked example both test files run over. `make model-drawio-test` runs those
tests, with no browser and no network. The two questions a rendering must not decide for itself — which
swimlane a box sits in, and which frames a slice's first box draws its arrows from — live in `model.ts` as
`laneName` and `sliceInputs`, and both renderers import them, so the canvas and the SVG cannot disagree on
the things that make them the same model. The palette is one table, `palette.ts`, that the page's legend
and the canvas both read.

Two properties the whole thing rests on. **Determinism**: the file is a pure function of the model — no
timestamp, no `modified` attribute, no generated id, every collection ordered by the model or sorted, a
trailing newline — so the same model gives byte-identical output and the gate has something to compare.
**Readability**: a slice can read an event modelled thirty columns earlier, and an arrow drawn straight
between them crosses every box in between. A read that spans more than a column instead leaves its source
underneath, runs along a corridor below the bands, and rises into its reader; every read of one event shares
that event's corridor, packed by interval colouring; and a caption under each reader names every event it
reads. Captions are positioned text cells, not edge labels — edge labels inside a container carrying
hand-placed waypoints did not render — and the trunks are not colour-coded, because fifteen hues that
survive a colour-vision check do not exist and a corridor's index is rank, not identity.

`check-drawio` needs Node, which `make verify` in an event-profile project therefore needs too, whatever
language the services are written in. The generated verify workflow sets one up where the project has no
Node of its own.

## What a slice owes: its guard, and where its read model lives

Two of the things the ladder asks for at `planned` are the ones that are hardest to change afterwards, and
both are answered once and lived with. The schema reference — the project's own
`docs/event-model/README.md` — is authoritative on the syntax; what follows is what the model is asking and
why.

**The guard is what the append is checked against.** A state-change slice names either `stream`, whose
version the append carries, or `guard`, a boundary drawn per decision over tags:

```yaml
    stream: order-{orderId}        # the version of one stream — the default, and most slices
```

```yaml
    guard:                         # a boundary over tags, for a constraint one stream cannot express
      by: [seat, hold]
      because: a seat may be claimed once, and a hold may not exceed its cap
```

Never both (`one-guard-not-two`): a conflict has to mean one thing. Both are consistency boundaries and
therefore concurrency ceilings, which is why the answer is owed at `planned` rather than at the first
conflict — changing either later migrates the one thing that cannot be migrated. Whichever it is, what the
slice `folds` has to be reachable under it: its own stream's events (`folds-own-stream`), or events carrying
an attribute that identifies one of the guard's kinds (`folds-match-the-guard`). A decision folding
something its guard cannot reach is guarded against a fact it never read, and no unit test catches that —
a Decider's test hand-feeds it events no append could have loaded.
[ADR 0002](adr/0002-the-guard-a-slice-declares.md) records the decision and what was read to reach it.

**Identity is modelled; tags are not.** An `evt` frame may carry `attributes` in place of `data`, each one
optionally naming the kind of thing it `identifies` — `{ name: seatId, identifies: seat }`. That is what a
project's tagging function is transcribed from, and it names a *kind* rather than being a flag because two
attributes may identify the same one: `fromHold` and `toHold` are both a `hold`, so the event carries two
`hold:` tags and a query for either finds it. The tags themselves appear nowhere in `model.yaml` — they are
an index over the log rather than a fact about the business. The diagram stars an identifying attribute,
`seatId*`, and `model.html` lists the kinds, where there is room.

The index they feed is derived: the generated store writes `event_tags` inside the append's own transaction
from the project's own tagging function, so nothing about the log is rewritten and no tag is stored on an
event. `read_tagged` and `append_if` are what a tag `guard` becomes in code.
[ADR 0001](adr/0001-a-dcb-capable-log.md) records why the log records tags at all — and why
stream-per-aggregate stays the **default** write path rather than being replaced by the boundary it makes
available.

**`materialisation` is the read side's `stream`.** One says what a write costs to keep consistent, the
other what a query costs to answer. A state-view or automation slice names where its read model lives, and
all three answers cost about the same to take because [all three ship built](what-you-get.md#the-read-side):

| | Runs | Consistency | What it costs |
|---|---|---|---|
| `live` | per query, folded in memory, nothing stored | strong | the whole fold on every read, forever |
| `inline` | in the same transaction as the append, through the store's unit of work | strong | projection work on the write path, and write throughput coupled to it |
| `async` | a catch-up subscription with a checkpoint | **eventual** | a lag to design for and cap, plus the worker that runs the subscription |

A `live` view also carries a `liveBudget`: the number of events one query may fold, argued from the stream's
own lifetime, with the fold's projection test written against that ceiling — so a stream that outgrows it
fails a test rather than getting a millisecond slower every week. The field exists because the answer was
otherwise made by gravity: with no checkpoint store in the skeleton, folding the log per query was the only
read path that was free, and a slice that reached a plan without being asked got it without anybody weighing
it.

## Publishing the page

`.github/workflows/event-model.yml` validates the model, renders it, and publishes the browsable page on
every push that touches `model.yaml` or the workflow itself — validating first, so an invalid model fails
before a browser is spent on it. Only that job writes, and only to the `pages` branch.

Set `render.page` in `model.yaml` once the site is up and the README links it instead of embedding segments;
leave it unset and the README embeds the segments, which needs no site at all.

## From a box to a file

`docs/event-modeling-to-code.md`, generated into every event-profile project, maps each box in the model to
the file it becomes — in that project's own language and paths. `events.ts` / `events.py` / `Events.java`
for the event contract, the decider for the domain rule, a use case per command, and the slice's test in the
native test framework, all under the bounded context the slice names.

The nine-step modelling procedure itself is `skills/event-modeling/SKILL.md`, and the recording procedure —
how a session's outcome becomes entries in `model.yaml` — is `skills/global-event-model/SKILL.md`. The
schema reference ships as the project's own `docs/event-model/README.md`.
