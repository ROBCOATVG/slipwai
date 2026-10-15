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

## 1. The researcher

Delegate this half to a fresh context that may write under `specs/<feature>/mockups/` and nowhere else. Give
it `specs/<feature>/spec.md`, the domain knowledge in `.specify/domain/`, **everything under `docs/design/`**,
and the paths of any mock-ups a person has already put in the directory.

`docs/design/` is what this project was handed rather than what it generated — a brand sheet, a stylesheet,
wireframes somebody drew, a competitor teardown — carried in beside `docs/prd.md` at generation. Where it
holds a direction, **follow it rather than invent one**, and say in the research note which file each
decision came from. A drawing that ignores the direction a person already settled is the stage doing the
one thing it exists to prevent. Where the directory is empty or absent, there is nothing to follow and the
note says so. It answers four questions **per surface the spec implies**, and a
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
  `skills/frontend-design/SKILL.md` for this. Do **not** load `web-interface-guidelines`: it reviews
  browser UI *code* against a standard, and these are not code yet — it runs later, before the demo of any
  slice that builds one of these.

There is always something to review. A feature whose mock-ups nobody drew is the case this stage exists for,
not a case it skips.

## 2. The storyboard, which is the review

Run `skills/storyboard/SKILL.md` over the directory: one page, the flow between the surfaces, a gap card for
every surface the spec names and no file shows, and an audit checklist per mock-up. Then run
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
- **The demo.** The hand walks those states when it walks the slice's examples, and the person's demo of the
  capability walks them again as one flow.
- **`web-interface-guidelines`.** Before the demo of any slice that builds one of these surfaces.

## When to run it again

When the specification changes what a surface is for, or adds one. Not when a slice changes how a surface is
built. A re-run reviews only the surfaces that moved, and leaves the rest of `mock-states.md` alone.
