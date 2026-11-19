---
description: Research, draft or review this feature's surfaces, storyboard them, and get each state approved before anything is modelled or charted
argument-hint: [feature]
---

# Mock-up review

Run this once per feature, after `/speckit-specify` and its `/gaps` pass, and **before** the event model or
the chart. A person is present for the second half of it; that is the point of it.

Version 1 had no stage here. A slice's plan invented its screens, and the first time anyone saw one was the
demo of the slice that built it — by which point the shape of it was already in the tests, the read models
and the routes. The `storyboard`, `find-gaps` and `frontend-design` skills were all in the toolkit and no
stage called them.

Everything this stage writes lives under `specs/<feature>/mockups/`.

**A feature is drawn into the product, not beside it.** The storyboard stays one per feature — that is what
`mock-states.md`, `check-surfaces` and the board's verdict are each held to, and a storyboard per project
would make every one of them answer for surfaces no feature in front of them is building. So a reader sees
one flow because **a further feature's storyboard frames what the project already has**, where it lies, and
draws this feature's surfaces into it. The newest feature's storyboard is the flow as it will stand. Section 0
is how the stage knows what the project has.

**Typed by a person**, this file is the rules from here down, both halves of it, in the session you are in.

**In a session dispatched by `scripts/agents/surfaces.py`** (`SLIPWAI_STAGE=surfaces` in the environment —
the board's **Draw the storyboard** button, or `{{make}} surfaces`), **run sections 0, 1 and 2 and stop at the
storyboard.** Nobody is in that session: there is no one to show a surface to, so the stop in section 2 is
where it ends, and section 3 is not yours to write. Do not create `mock-states.md`, and do not mark a state
`approved`, `parked` or `n/a` — a verdict is the one thing here that only a person can give, and a file of
approvals nobody gave is exactly the failure this stage was added to prevent. Write the research, the
mock-ups and the storyboard, say what you drew and which surfaces the specification implies, and leave the
questions from section 1 in the inbox as usual. The person runs `/mockups <feature>` afterwards, in a
session they are in, and that run picks up at section 2's stop with the drawings already there.

**That session has a budget, and it is ended at it.** `SLIPWAI_BUDGET_MINUTES` is how many minutes you have
and `SLIPWAI_BUDGET_ENDS` the clock time they run out — fifteen for a first drawing and ten for a redraw,
scaled by the telegraph like every stage budget in `harbour.json`. Plan to it: the research note and the
shared stylesheet first, then every surface roughly drawn before any is refined, then the storyboard, so that
whatever the clock finds is a storyboard with every surface on it rather than three perfect screens and no
flow. At the budget `surfaces.py` ends the session and every delegate it started, and keeps what is on disk. A
run measured without one spent seventy minutes on a redraw, most of it rendering and re-rendering screenshots,
while the person who asked for it waited.

**When `SLIPWAI_REDRAW=1` is set as well, a person disapproved the storyboard and this is the redraw.** The
drawings in the directory are this stage's own drafts, turned down — not mock-ups a person handed over — so
do not review them as a hand-over: draw again. `specs/<feature>/mockups/mock-states.md` has every state
parked with the person's reason, and that reason is the brief. Answer it, and **only** it, in place and
under the same file names: change what the reason concerns and leave the rest as it was. A reason about the
look is a change to the shared stylesheet, not nine surfaces drawn from nothing; a reason about one surface
is that surface. Where a design direction and a stylesheet already exist under `specs/<feature>/mockups/`
(or `docs/design/`), reuse and amend them — a turned-down drawing is not a reason to start a design system.
The budget above and the capped checking in section 1 hold for a redraw exactly as for a first drawing. Add
a `## Redrawn` section to `research.md` saying what changed and which part of the reason each change
answers. Leave `mock-states.md` alone: `surfaces.py` retires it to
`disapproved.md` once the redraw lands, so the new storyboard waits on a verdict of its own.

**When the person talks to that session afterwards.** The board keeps the drawing's session, and what a
person types under the storyboard comes to it as one more turn, followed by a line beginning *The board
started this turn*. Answer in that turn. A change they ask for is made there and then, in place and under
the same file name, as a redraw would make it; the board withdraws any verdict on a page that changed, so
leave `mock-states.md` alone. A decision they make — an answer to one of `research.md`'s `## Questions`, how
a finding in the review is settled — is written down in the same turn: the next entry of
`specs/<feature>/decisions.md`, in the shape `commands/cruise.md` shows, with `Decided by: human`, and the
question or the finding marked `— answered (D<n>)` where it was written, and the two counts below rewritten.
Saying it is not recording it. A verdict is still not yours: `approved`, `parked` and `n/a` are given on the
board.

**What is left to discuss, declared.** Begin `research.md` with these two lines, as plain text — no bold, no
list marker:

```
Blockers open: pending
Questions open: pending
```

Only when the review is finished, replace `pending` with the counts in figures: `Blockers open`, the Blocker
findings nobody has settled; `Questions open`, the questions under `## Questions` nobody has answered; `0`
where there are none. Until then `pending` tells the board the review is not finished. Keep the counts true:
rewrite them whenever a finding or a question is settled, in a conversation turn as much as in the drawing. A board set to advance by itself reads these two
lines to tell whether a storyboard has anything left to discuss, and waits for the person where it cannot
read them; a person judging the storyboard needs nothing from them.

## 0. What exists

**Before anything is researched or drawn, list what the project has.** Run

```
python3 scripts/agents/existing.py <feature> --write
```

which writes `specs/<feature>/mockups/existing.md` and prints it. In a session `surfaces.py` dispatched it has
run already and `SLIPWAI_EXISTING` is the page's path; read that. It is not a hand-over and not a mock-up: it
is the list of what to read first, each thing with where it is and what it is evidence of —

1. **Earlier features' mock-ups** — `specs/*/mockups/`: each surface page, and what `mock-states.md` says of
   each state.
2. **The browser app**, where `project.json` records one: its committed screen previews under `screens/`,
   one page per state, grouped by surface; the routes its source names; its own stylesheets under
   `src/styles/`; the file its shell is in.
3. **The event model's `ui` frames**, on the event-modelling profile, each with its slice and whether that
   slice is `implemented`.
4. **`docs/design.md`**, which says what this project's screens are made of, the design review's
   photographs, and anything a person handed over under `docs/design/`.

The page ends its opening with three lines the rest of this stage follows: whose **look** the drawing takes,
what the **storyboard** is made from, and how a surface is **marked**. Under them, *What each surface is*
lists every surface the evidence names, one row each, with the word it takes and the page to frame. A first
feature in a project with nothing built gets a short page saying so, and this stage runs as it always did.

**Every surface on the storyboard is one of four things, and says which:**

| | What it is | Where it is | A verdict? |
|---|---|---|---|
| `built` | the project's already: a committed preview, an earlier feature's surface that has been built | where it lies — never copied, never redrawn | no. It is shown for the flow |
| `planned` | approved for an earlier feature and not built yet | the earlier feature's own page, where it lies | no. Its verdict was given there, and it is that feature's to deliver |
| `changed` | a built surface this feature alters: a new panel, a new state, a different step | a page of its own beside the storyboard, drawing **only the states this feature changes or adds** | yes |
| `new` | a surface this feature adds | a page of its own beside the storyboard | yes |

What counts as built is evidence the list gives, in this order: a committed preview, a `ui` frame whose slice
is `implemented`, a design-review photograph, a route.

**A route alone is built, unseen.** A surface known only from a route — or from an implemented frame nobody
drew or photographed — is `built`: the app has it. But nothing shows how it looks, and `existing.md` says so
on its row: *built, no picture*. **Draw it as a plain labelled box and invent nothing**: no layout, no
fields, no copy, no guess at its states. The box is an element of the storyboard itself, not a page —

```html
<div class="unseen" data-surface="built" data-picture="none" data-route="/workspace/explain">
  /workspace/explain — built, no picture
</div>
```

`data-picture="none"` beside `data-surface="built"` is the mark; `data-route` (or `data-frame`, with the
frame's name, where it is known from the model and has no route) says what it is known by, and the label
says the same and no more. It is never a fifth word. Do not draw a page for it, do not frame a similar
screen in its place, and do not put it up for a verdict. Where this feature changes such a surface, the
change is a `changed` page as ever, and the box beside it is its original. `python3
scripts/agents/existing.py <feature> --check` refuses a box that frames a page, is an `<iframe>` or an
`<img>`, does not say what it is known by, or holds anything drawn — a form, a table, a list, an image;
`surfaces.py` runs the same check when the drawing ends. What the label's words claim is not something a
script can judge: that part is this instruction.

**`planned` is the word for what is settled and not
there yet:** an earlier feature's surface with at least one state a person approved, and no evidence in that
list that anybody built it. It is framed from that feature's page, exactly as a built surface is framed from
its preview, and it is treated as a built one is — not drawn again, not asked about, not in this feature's
`mock-states.md` as a block, not this feature's to deliver. The moment a preview, an implemented frame, a
photograph or a route says it exists, it is `built`. An earlier feature's surface nobody approved — unjudged,
or parked — is neither: it is a question still open under that feature, and this storyboard names it as a box
in the flow and frames nothing. `existing.md` says which word each surface takes; where you disagree with a
row, the row says what it matched, so say in `research.md` what you framed instead and why.

## 1. The researcher

Delegate this half to a fresh context that may write under `specs/<feature>/mockups/` and nowhere else. Give
it `specs/<feature>/spec.md`, the domain knowledge in `.specify/domain/`, **everything under `docs/design/`**,
the paths of any mock-ups a person has already put in the directory, and **`existing.md` from section 0, to
read first**: before it answers anything about a surface it opens the previews and earlier surfaces that
surface leads from and to, and the app's stylesheets, so that the note says of each surface which built
screen leads to it, which built screen gains a panel or a state, and which it is — `changed` or `new`.

`docs/design/` is what this project was handed rather than what it generated — a brand sheet, a stylesheet,
wireframes somebody drew, a competitor teardown — carried in beside `docs/prd.md` at generation. Where it
holds a direction, **follow it rather than invent one**, and say in the research note which file each
decision came from. A drawing that ignores the direction a person already settled is the stage doing the
one thing it exists to prevent. Where the directory is empty or absent, there is nothing to follow and the
note says so — and the draughtsman sets a short direction of its own before drawing (below), because a
first drawing with no look at all was turned down for exactly that, twice, and the redraw it bought cost ten
times the drawing. It answers four questions **per surface the spec implies**, and a
surface is any place a person or another system meets this feature: a screen, a command line, an email, a
webhook, a report.

**In a repository that was adopted, the strategy says whose look a surface takes.** Read the specification's
`## Strategy fit`. Where it `Lands in:` a new home, the surface is drawn in the new home's UI, never the old
app's — under `Visibility: page`, the whole new page, with the old page's behaviours that its parity rows
bring in drawn on it; under `Visibility: seam`, the old page as it is with the new panel in it; where the
spec says the choice is close, both, side by side, so the storyboard's verdict decides. Where it lands in the
old code, the old app's look is the direction to follow.

1. What job is the user doing on this surface, in their words rather than the system's?
2. How do comparable products do that job? Use the harness's web search where it has one. Where it has
   none, answer from your own knowledge and **say that is what you are doing** — an uncited claim about
   what is conventional is the one thing here that is worse than no claim.
3. Which states does every good version of this surface carry? Loading, empty, populated, partial, error,
   recovery, permission-denied, offline. Name the ones that apply and say why the rest do not.
4. What will a user arrive already expecting, from the other software they use all day?

It writes `specs/<feature>/mockups/research.md` in that shape, one section per surface, each naming what it
drew on. Questions the spec does not answer go under `## Questions` and the stage copies them to the inbox.
It opens with the two lines above, `Blockers open: N` and `Questions open: N`.

Then one of two things, depending on what was in the directory.

- **A person handed over mock-ups.** Review each against the note. One finding list per mock-up, in the
  shape the `/gaps` stage uses, so one triage reads both, in `specs/<feature>/mockups/review.md`. Do not
  redraw them.
- **A person handed over a prototype** (`docs/design/prototype/index.html`): the drawing they approved by
  playing it. The storyboard embeds it first, as the thing to play, and every surface drawn or reviewed
  follows its look and layout; a surface page that says a state in words the prototype shows is reviewed
  against the prototype, not the words. It is not a surface: it has no state articles, the board asks for
  no verdict on it, and nothing is built from its code.
- **The directory was empty** — `existing.md` aside, which is this stage's own list. Draft them: one static HTML file per surface, from the note. No framework and
  no build step, because the point is a file a person opens in a browser and points at. Load
  `skills/frontend-design/SKILL.md` for this, read through *How much rigour a mock-up gets* below, which
  overrides it for this stage. Do **not** load `web-interface-guidelines`: it reviews browser UI *code*
  against a standard, and these are not code yet — it runs later, before the demo of any slice that builds
  one of these.

  **Each surface is its own page, and the storyboard is not one.** `<surface>.html` per surface, its
  `<title>` naming it, and each state an `<article class="state">` headed by an `<h2>` naming the state — that
  is what the board reads when a person approves the drawing, one verdict per state. The storyboard
  (`storyboard.html`) embeds or links those pages: the ones beside it, or — where a person handed the mock-ups
  over in `docs/design/` — those pages where they are, which the board then reads as the surfaces. A handed-over
  article may carry `data-decided="person"` or `data-decided="proposed"`, saying who chose the state; keep it
  on a redraw, because the board counts it and writes it after each verdict. A storyboard
  with the surfaces drawn inside it and no page to show is nothing anybody can approve, and the stage refuses it
  as nothing drawn.

  **The look is the real app's.** Where `docs/design/` held a direction, follow it, as above: what a person
  handed over still wins. Otherwise, where `existing.md` says the look is the app's own, **every surface this
  stage draws links the app's own stylesheets** — `<link rel="stylesheet"
  href="../../../<app>/src/styles/tokens.css">` and the others it lists, by relative path, never a copy — and
  **sits in the app's shell**: the same header, navigation and page frame the previews show, taken from a
  preview's markup, so that a new surface reads as a screen of this product. Write no `mockups.css` of your
  own beyond the few rules a new component needs, and write those in the app's tokens. Say in `research.md`
  under `## Look` which files the drawing links. Where the list says an earlier feature's storyboard set the
  look, link that feature's stylesheet the same way; a second proposed look in one project is two products.

  **The first drawing is styled.** Only a project with none of those — no direction handed over, no browser
  app, no earlier storyboard — proposes a look. There, set a short one before the first surface: a handful
  of tokens (a type scale, four to six colours, a spacing step), one shared stylesheet every surface links — `specs/<feature>/mockups/mockups.css` — and
  only the few components these surfaces actually use. That is minutes of work, not a design system: no
  component sheet, no token documentation, no dark theme. Write it into `research.md` under `## Proposed
  look`, and say there that it is **a proposed look for reviewing the flow, not a brand** — a person who
  has a brand hands it over in `docs/design/`, and the next drawing follows that instead. Plain unstyled
  boxes are not the neutral choice they look like: a reviewer cannot judge feel, hierarchy or whether a
  state reads as an error from grey rectangles, so they turn the drawing down and the stage runs twice.

  **Where the drawing fans out to delegates** — one per surface, or a few surfaces each — the direction and
  the stylesheet come first, written once by you before any delegate starts, because every delegate links
  the same file and a direction written three times is three looks. It is a prerequisite, so it has to stay
  short: everything is waiting on it. Give each delegate the stylesheet's path and the section below, and a
  share of the budget that leaves time for the storyboard.

There is always something to review. A feature whose mock-ups nobody drew is the case this stage exists for,
not a case it skips.

### How much rigour a mock-up gets

**The storyboard does not need the rigour the end product needs.** It is a sketch a person reviews for flow,
content, states and feel. Production-grade visual quality is checked later, and properly: by
`web-interface-guidelines` and the design review before a slice that builds the surface is demonstrated. So
in the mock-up stage, and only here, these override what `frontend-design` and `storyboard` say about
checking your own work visually:

- **At most one render per surface per pass**, in one theme, to catch a broken layout — overflow, overlap,
  text that cannot be read. Fix what it shows and move on. It is a check, not a polish: no render, look,
  tweak, render loop.
- **No light and dark pairs, and no phone-width sweeps**, unless the specification makes mobile the primary
  surface — then the one render is at phone width instead.
- **No screenshots or thumbnails for the storyboard.** It embeds or links the surfaces themselves; a
  rendered picture of a page that is sitting right there is a second copy to keep in step.

A run without this read its own screenshots back 183 times across one redraw. Not one of those looks was a
question about flow, content or states, which are the only questions a person is asked here.

## 2. The storyboard, which is the review

Run `skills/storyboard/SKILL.md` over the directory: one page, the flow between the surfaces, a gap card for
every surface the spec names and no file shows, and an audit checklist per mock-up. It embeds the surfaces
(an `<iframe>` each) or links them; it does not render them to images, per the rules above.

**It is the project's flow with this feature in it.** Where `existing.md` lists anything built or drawn, the
storyboard's flow diagram is the flow as it stands with this feature's surfaces placed in it — which built
screen leads to each, and where each leads back — and the page frames the built screens from the real thing:
the app's own preview, or the earlier feature's page, by relative path where it lies
(`../../../<app>/screens/<page>.html`, `../../<feature>/mockups/<page>.html`). Never a copy, never a redraw,
never a picture. **Mark every frame and link that shows a surface**, on the `<iframe>` or `<a>` itself:
`data-surface="built"`, `data-surface="planned"`, `data-surface="changed"` or `data-surface="new"`. That mark
is what the board reads to show the four apart and to ask a verdict on the last two only; a built or planned
frame without it is read as a mock-up somebody handed over, and put up for approval as if it were new. **The
legend the storyboard draws names all four** — built, planned, changed, new — with the gap's beside them, and
*built, no picture* as the built colour with a dashed edge; a planned frame's cell says which feature
approved it. Before the stop below, run `python3 scripts/agents/existing.py <feature> --check`, which holds
the marks to what can be checked and prints how many of each the storyboard shows.

**Where the project has a storyboard, add to that flow; where it has none, this is the first, made from what
exists.** A project that crossed from version 1 has dozens of built screens and no storyboard: draw the flow
as it stands from the list, then this feature in its place. **Frame the part this feature touches and its
neighbours** — each `changed` surface's built original beside it, each built screen that leads to or from a
`changed` or `new` one, one frame per built surface in its ordinary state rather than one per state — and
name the rest of the flow as boxes in the diagram, each linking its preview. Two hundred frames is not a
storyboard, and the budget is the same fifteen minutes. Then run
`skills/find-gaps/SKILL.md` over that page in its design-mock mode, writing each answer back as a state the
mock-up has to show.

**Then stop and show it to a person, surface by surface.** This is a stop, not a notification. Ask about one
surface at a time and write the answer down before moving to the next.

Facing a person, name everything twice the first time it comes up: the slipwai word and the ordinary one.
"the fairway (this bounded context's slices)", "the careen (the hardening slice at the end)", "hoist the
flag (turn it on for real users)". Nobody should have to learn a vocabulary to answer a question about a
screen.

## 3. What the stage writes down

`specs/<feature>/mockups/mock-states.md`. One block per surface, its states beneath it, each state marked
`approved`, `parked` or `n/a`:

```markdown
## Surface: Order confirmation
- populated — approved
- empty (no items) — approved
- payment declined — approved
- offline — n/a: this surface is server-rendered and has no offline mode
- partial refund shown — parked: waiting on whether partial refunds exist at all (inbox 2026-10-07)
```

A `parked` state carries the question it is waiting on and the inbox line that asked it. `n/a` carries its
reason. A state with neither is not a decision, it is a blank.

**Only `changed` and `new` surfaces have a block.** A `built` surface was shown for the flow and nobody was
asked about it, so it has no `## Surface:` block and no state is marked for it: a state marked `approved` here
is a state the split then has to deliver, and a built screen is delivered already. A `planned` surface has
none either: its states were approved under the earlier feature, and the slice that delivers them is that
feature's. Ask a person about a `changed` surface's changed and added states, and about a `new` surface's
states, and about nothing else. The board writes one line per framed surface above the blocks —
`<!-- built: <its title> — <its page> (…) -->`, `<!-- planned: <its title> — <its page> (…) -->` — so the file
says what was shown; where you write the file by hand, write the same line. A slice that names a built or a
planned surface is refused by `check-surfaces`: where this feature changes it, it is `changed`, with a page
and a verdict of its own.

**A feature with no surface at all** — a migration, an integration, a scheduled job — writes the whole file
as `surfaces: none`, with the sentence saying why, and the stage closes. That is a valid answer and the
commonest one on a back-end-only feature. It is written down so that the next reader knows the question was
asked rather than skipped.

## What reads this afterwards

- **The event model, or the chart.** Its UI lane and read models, or its routes, are drawn from the approved
  surfaces, not from the specification alone.
- **The split.** Every slice names the surfaces and states it delivers, and may not name one that is not
  `approved` here.
- **The example map.** One example per approved state, so the state a person approved is the state a test is
  named after.
- **The demo.** The hand walks those states when it walks the capability's examples, and the person's demo of
  the capability walks them again as one flow.
- **`web-interface-guidelines`.** In the design review of any capability that builds one of these surfaces —
  of each slice that does, where the project reads each slice.

## When to run it again

When the specification changes what a surface is for, or adds one. Not when a slice changes how a surface is
built. A re-run reviews only the surfaces that moved, and leaves the rest of `mock-states.md` alone.

**A further feature is not a re-run of an earlier feature's stage.** It runs the stage for itself, under its
own `specs/<feature>/mockups/`, with the built app framed in as `built` and the earlier features' surfaces
as `built` or `planned`, whichever the evidence says (section 0). The earlier feature's `mock-states.md` is not reopened and not copied: where the new feature
alters one of its surfaces, that surface is `changed` here, and the verdict on the change is this feature's.
