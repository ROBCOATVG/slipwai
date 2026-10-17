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

These steps take about ten minutes. The next page takes about five more. In those five minutes, one
feature is specified, modelled, charted, split, built and demoed to you.

**You can also do all of this on a web page.** Run `slipwai` with no arguments to open **the board**. This
machine serves the board, and only this machine can open it. On the board, you can start a project from the
same questions. You can also give the board a requirements document, or the folder that contains it. The
board then drafts the first specification for you and waits for you to read it. After that, the
**Voyage** tab shows which stage the project is at. The board reads the stage from the files in the
project. Each stop that waits for a person has a button.

## New to this — start here

| | |
| --- | --- |
| **[Runsheet: generate a new project](docs/guide/runsheet-generate.md)** | You want a new repository. Every step in order, from installing the command to a fleet that cruises, and every release after that |
| **[Runsheet: adopt an existing repository](docs/guide/runsheet-adopt.md)** | You already have a codebase. Every step in order, from `slipwai adopt` through `/ground` to the first slice |

The runsheets give the sequence of steps. The five guide pages below give the reasons, one page for each
subject.

Do you use version 1? Read **[What is new since version 1](docs/whats-new.md)**. It lists every change
that affects you, the purpose of each change, and the one command that moves your project to version 2.

---

## What it is for

Coding agents write code quickly. They are bad at three things around the code:

- knowing what to build next
- not interfering with each other's work
- reporting honestly what they did

Slipwai is the repository around the agents. It fixes those three problems.

**One rule makes the rest possible.** Two workers each deliver a slice, and neither waits for the other's
branch. This works because a **chart** gives each contract between fairways a type and exactly one owner.
A slice can start when the contract that it needs is *set*. The slice that owns the contract sets it at
its first stage, in its own worktree, before anything merges.

**Slipwai does not believe a status because something reported it.** Slipwai calculates status from
append-only logs each time it shows the status. It stores the status nowhere. A stage that writes no log
line and makes no commit has made no progress. This is true even if the stage reports that it is nearly
done. This rule corrects two specific failures:

- In the first attempt, a runner was the only source of status. It stopped at iteration two, and twenty
  slices continued to merge without it.
- A model file said `planned` for eight slices that had already shipped.

## The five pages

| | |
| --- | --- |
| **[Start here](docs/guide/start-here.md)** | Install the command, answer its questions, and see the gate pass |
| **[Your first feature](docs/guide/first-feature.md)** | A specification, a model, a chart, a slice, and a demo that you accept |
| **[A second person joins](docs/guide/a-second-person.md)** | Fairways, berths, and why neither of you waits |
| **[Let it cruise](docs/guide/let-it-cruise.md)** | Captains, the telegraph, and the decisions that a person still makes |
| **[Bring an existing codebase](docs/guide/adopt.md)** | The other way in: survey the repository, then wrap it |

Each page ends where the next page starts. Stop when you have what you need.

Two more pages are maps, not steps. [The workflow](docs/guide/the-workflow.md) lists every step on one
page: who does the step, what the step writes, and where the step stops. [The board](docs/guide/the-board.md)
describes every screen and control, and the file that each control writes.

## What it looks like when it runs

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

- `slipwai fleet` prints the view above.
- `slipwai fleet <fairway>` prints the log of one fairway, one line at a time.
- `slipwai bridge` shows the same information as a page, and you can answer questions from that page.

[docs/captures](docs/captures/) has more examples. They come from real runs. Nobody drew them by hand.

## The board

Run `slipwai` with no arguments to open one page. The page has a tab for each of these:

- starting a project
- adopting a repository
- the packages that this machine can install
- the fleet
- the **Voyage**

The **Voyage** tab shows:

- **The stages**, from PRD (product requirements document) to accepted. Each stage is *done*, *working*,
  *waiting on you* or *to do*, and shows the file that proves it. The board reads each stage from the
  files. Nobody types a status.
- **The stops**, each as a button: open the specification, draw and approve the storyboard, continue the
  build, cast off or stop the fleet, and continue to the next feature.
- **The work**: the event model in the draw.io viewer, coloured by slice; the mock-ups and the screens that
  each slice has rendered; the slices by state; and the questions that wait for you, each with a box for
  your answer.
- **One Settings box**, with tabs for speed, fine tune, who answers, delegation and models. The project's
  own scripts write these settings. The board never writes them itself.

Each button runs a `make` target that you could type instead. `slipwai bridge install` starts the board
each time you log in. [Your first feature](docs/guide/first-feature.md#from-the-board) goes through the
page, and [the board](docs/guide/the-board.md) describes every control on it.

## Languages, and everything else

The command knows how to build a repository. It does not know any languages. Languages come from the
**chandlery**. The chandlery is an index of packages. Each package has a version, a compatibility range, a
checksum and a publisher.

```sh
slipwai search postgres        # by what a package answers, not by its name
slipwai show python
slipwai install python
```

Six languages are published at `https://robcoatvg.github.io/slipwai-index/`. When you install from a
publisher for the first time, slipwai asks you to confirm that publisher once. Slipwai checks the checksum
every time, for every publisher. To publish your own package, use four verbs — `slipwai package new`,
`check`, `version` and `release` — and then open a pull request. Clouds (`slipwai target install aws`) and
developer tooling (`slipwai extension`) are packages in the same way.

**The command includes six quickstarts.** A quickstart is a set of answers that somebody has already
decided. Each quickstart is described by what the product is like. Run `slipwai quickstart list` to see
them, then `slipwai generate <name> --quickstart <name>` to use one.

## Reference

[The vocabulary](GLOSSARY.md) · [extensions](docs/extensions.md) ·
[the backend protocol](docs/backend-protocol.md) · [the rules, in detail](docs/reference/) ·
[the plan this was built to](docs/slipwai-2-plan.md)

---

### Status

This is slipwai 2, and it is still under construction. On 2026-10-06 the tree was cleared. Since then,
version 2 has been brought back one module at a time. `docs/slipwai-2-plan.md` gives the order of the work
and what is left to do. The 1.x working contract came back with phase 8: `slipwai migrate` moves a version
1 project to version 2, and [what is new since version 1](docs/whats-new.md) says what that costs. Version
2 is developed in [ROBCOATVG/slipwai](https://github.com/ROBCOATVG/slipwai) on GitHub, which is the
canonical repository.
