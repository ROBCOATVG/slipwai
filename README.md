# Slipwai

[![verify](https://github.com/ROBCOATVG/slipwai/actions/workflows/verify.yml/badge.svg?branch=main)](https://github.com/ROBCOATVG/slipwai/actions/workflows/verify.yml)
[![PyPI](https://img.shields.io/pypi/v/slipwai)](https://pypi.org/project/slipwai/)
[![Python](https://img.shields.io/pypi/pyversions/slipwai)](https://pypi.org/project/slipwai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Slipwai creates product repositories and runs a delivery loop in them with coding agents.** Say the name
as "slipway".

```console
$ slipwai install typescript
typescript installed from the slipwai chandlery 1.0.0, published by ROBCOATVG (verified)

$ slipwai generate
Create a new product monorepo. Press Enter to accept a shown default.
Project name: bookings
Start from (none/laptop-trial/internal-tool/…) [none]:
Use Event Modeling? [Y/n]:
  …   the target, the service and its contexts, how it stores data, who signs in
Product requirements document (a path; Enter for none): ~/briefs/bookings.md
created: /Users/you/code/bookings

$ cd bookings && make verify   # ./init ran where the project was made

verify: all gates passed
```

That is ten minutes. The other five are one feature — specified, modelled, charted, split, built and
demoed in front of you — and they are on the next page.

**Or do all of it on a page.** `slipwai` on its own opens **the board**, served from this machine only:
start a project from the same questions, or hand over a requirements document or the folder it sits in,
and the first specification is drafted for you and waits for you to read it. Its **Voyage** tab then says
which stage the project is on, read off the tree, with a button at every stop that waits for a person.

## New to this — start here

| | |
| --- | --- |
| **[Runsheet: generate a new project](docs/guide/runsheet-generate.md)** | You want a fresh repository. Every step in order, from installing the command to a fleet cruising and every release after |
| **[Runsheet: adopt an existing repository](docs/guide/runsheet-adopt.md)** | You already have a codebase. Every step in order, from `slipwai adopt` through `/ground` to the first slice |

The runsheets are the sequence; the five guide pages below are the reasoning, a page each.

Coming from version 1? → **[What is new since version 1](docs/whats-new.md)** — every change that affects
you, what each is for, and the one command that moves your project across.

---

## What it is for

Coding agents are fast at writing code and bad at everything around it: knowing what to build next, not
treading on each other, and being honest about what they did. Slipwai is the repository around them that
fixes those three.

**One claim holds the rest up.** Two workers, each delivering a slice, and neither waiting on the other's
branch. That works because a **chart** types the contracts between fairways and insists each one has
exactly one owner — so a slice is cleared to start the moment the contract it needs is *set*, which happens
at the setting slice's first stage, in its own worktree, before anything merges anywhere.

**Nothing is believed because something said it.** Status is folded from append-only logs every time it is
drawn, and is stored nowhere. A stage that wrote no line made no progress — including a stage that reports
cheerfully that it is nearly done. That rule is the correction of two specific failures: a runner that was
the single source of status and died at iteration two while twenty slices went on merging, and a model file
that said `planned` for eight slices that had shipped.

## The five pages

| | |
| --- | --- |
| **[Start here](docs/guide/start-here.md)** | Install it, answer its questions, watch the gate go green |
| **[Your first feature](docs/guide/first-feature.md)** | A spec, a model, a chart, a slice, and a demo you accept |
| **[A second person joins](docs/guide/a-second-person.md)** | Fairways, berths, and why neither of you is waiting |
| **[Let it cruise](docs/guide/let-it-cruise.md)** | Captains, the telegraph, and what a person still decides |
| **[Bring an existing codebase](docs/guide/adopt.md)** | The other door: survey, then wrap |

Each one ends where the next begins. Stop when you have what you came for.

Two more pages are maps rather than steps. [The workflow](docs/guide/the-workflow.md) lists every step on
one page: who does it, what it writes, and where it stops. [The board](docs/guide/the-board.md) describes
every screen and control, and the file each control writes.

## What it looks like running

```
waiting on you: 2
  billing    told    should a refund be its own capability?

berths: 2, 2 working
  fairway   feature  slice   state    last line  tokens  merged  marks
  --------  -------  ------  -------  ---------  ------  ------  -----
  billing   model    BIL-01  working  12s ago    42      0       1
  ordering  model    ORD-02  working  31s ago    84      1       1

telegraph: half-ahead  boilers 3  fanout 2  bunker 126/10000k today
```

`slipwai fleet` for that, `slipwai fleet <fairway>` for one fairway's own log said a line at a time, and
`slipwai bridge` for the same thing as a page you can answer from. More in
[docs/captures](docs/captures/), which are from real runs rather than drawn.

## The board

`slipwai` with nothing after it opens one page with a tab each for starting a project, adopting a
repository, the packages this machine can install, the fleet, and the **Voyage**:

- **The stages**, from PRD to accepted, each *done*, *working*, *waiting on you* or *to do*, with the file
  that proves it — read off the tree, never typed
- **The stops**, each a button: open the specification, draw and approve the storyboard, continue the
  build, cast off or stop the fleet, continue the next feature
- **The work**: the event model in draw.io's viewer coloured by slice, the mock-ups and the screens each
  slice has rendered, the slices by state, and the questions waiting on you with a box to answer each
- **One Settings box** — speed, fine tune, who answers, delegation and models — written by the project's
  own scripts, never by the board

Every button is a `make` target you could type instead. `slipwai bridge install` keeps the board running
whenever you log in. [Your first feature](docs/guide/first-feature.md#from-the-board) walks the page, and
[the board](docs/guide/the-board.md) describes every control on it.

## Languages, and everything else

The command knows how to build a repository. It does not know any languages — those come from the
**chandlery**, an index of packages with a version, a compatibility range, a checksum and a publisher each.

```sh
slipwai search postgres        # by what a package answers, not by its name
slipwai show python
slipwai install python
```

Six languages are published at `https://robcoatvg.github.io/slipwai-index/`. A publisher you have not met is
confirmed once; the checksum is checked every time, whoever published it. Publishing your own is four verbs
— `slipwai package new`, `check`, `version`, `release` — and a pull request. Clouds (`slipwai target
install aws`) and dev tooling (`slipwai extension`) are packages the same way.

**Six quickstarts are carried with the command** — a set of answers somebody already settled, offered by
what the product is like: `slipwai quickstart list`, then `slipwai generate <name> --quickstart <name>`.

## Reference

[The vocabulary](GLOSSARY.md) · [extensions](docs/extensions.md) ·
[the backend protocol](docs/backend-protocol.md) · [the rules, in detail](docs/reference/) ·
[the plan this was built to](docs/slipwai-2-plan.md)

---

### Status

This is slipwai 2, in a fork, under construction. The tree was cleared on 2026-10-06 and is being brought
back in version 2 shape one module at a time; `docs/slipwai-2-plan.md` has the order of work and what is
left. The 1.x working contract came back with phase 8: `slipwai migrate` crosses a version 1 project, and
[what is new since version 1](docs/whats-new.md) says what that costs. The fork merges back to
[ROBCOATVG/slipwai](https://github.com/ROBCOATVG/slipwai) as version 2 once, when complete.
