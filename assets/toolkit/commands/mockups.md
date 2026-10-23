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

**Typed by a person**, this file is the rules from here down, both halves of it, in the session you are in.

**In a session dispatched by `scripts/agents/surfaces.py`** (`SLIPWAI_STAGE=surfaces` in the environment —
the board's **Draw the surfaces** button, or `{{make}} surfaces`), **run sections 1 and 2 and stop at the
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

## 1. The researcher

Delegate this half to a fresh context that may write under `specs/<feature>/mockups/` and nowhere else. Give
it `specs/<feature>/spec.md`, the domain knowledge in `.specify/domain/`, **everything under `docs/design/`**,
and the paths of any mock-ups a person has already put in the directory.

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

1. What job is the user doing on this surface, in their words rather than the system's?
2. How do comparable products do that job? Use the harness's web search where it has one. Where it has
   none, answer from your own knowledge and **say that is what you are doing** — an uncited claim about
   what is conventional is the one thing here that is worse than no claim.
3. Which states does every good version of this surface carry? Loading, empty, populated, partial, error,
   recovery, permission-denied, offline. Name the ones that apply and say why the rest do not.
4. What will a user arrive already expecting, from the other software they use all day?

It writes `specs/<feature>/mockups/research.md` in that shape, one section per surface, each naming what it
drew on. Questions the spec does not answer go under `## Questions` and the stage copies them to the inbox.

Then one of two things, depending on what was in the directory.

- **A person handed over mock-ups.** Review each against the note. One finding list per mock-up, in the
  shape the `/gaps` stage uses, so one triage reads both. Do not redraw them.
- **The directory was empty.** Draft them: one static HTML file per surface, from the note. No framework and
  no build step, because the point is a file a person opens in a browser and points at. Load
  `skills/frontend-design/SKILL.md` for this, read through *How much rigour a mock-up gets* below, which
  overrides it for this stage. Do **not** load `web-interface-guidelines`: it reviews browser UI *code*
  against a standard, and these are not code yet — it runs later, before the demo of any slice that builds
  one of these.

  **Each surface is its own page, and the storyboard is not one.** `<surface>.html` per surface, its
  `<title>` naming it, and each state an `<article class="state">` headed by an `<h2>` naming the state — that
  is what the board reads when a person approves the drawing, one verdict per state. The storyboard
  (`storyboard.html`) embeds or links those pages: the ones beside it, or — where a person handed the mock-ups
  over in `docs/design/` — those pages where they are, which the board then reads as the surfaces. A storyboard
  with the surfaces drawn inside it and no page to show is nothing anybody can approve, and the stage refuses it
  as nothing drawn.

  **The first drawing is styled.** Where `docs/design/` held a direction, follow it, as above. Where it was
  empty, set a short one before the first surface: a handful of tokens (a type scale, four to six colours, a
  spacing step), one shared stylesheet every surface links — `specs/<feature>/mockups/mockups.css` — and
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
(an `<iframe>` each) or links them; it does not render them to images, per the rules above. Then run
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
  of each slice that does, under the `open` release mode.

## When to run it again

When the specification changes what a surface is for, or adds one. Not when a slice changes how a surface is
built. A re-run reviews only the surfaces that moved, and leaves the rest of `mock-states.md` alone.
