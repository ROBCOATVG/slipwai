---
description: Re-survey this repository with the factory and reconcile what it finds with what project.json records
---

# Survey

This repository adopted the delivery method: `project.json` records what the factory's survey detected about
the code that was here and what the person confirmed or overrode, each fact with its provenance. Code
changes; the survey is re-run, and the record is reconciled with it — refreshed where it was only detected,
questioned where a person decided. Run this when a build tool, a language, a schema tool or a deployment
description appears, moves or goes.

## Find the keel

The command belongs to the keel that generated this repository, not to the repository. It is
`slipwai adopt --refresh` where `slipwai` is on the `PATH` — installed with pip, or a released executable — and
`path/to/slipwai/slipwai adopt --refresh` from a checkout. If neither is at hand, ask where the
factory is. A wrong guess at its location is a stop, not a reason to edit `project.json` by hand from memory.

## Run it

1. `git status --porcelain` prints nothing. The command refuses an unclean tree so that `git checkout . &&
   git clean -fd` undoes exactly what it wrote and nothing else.
2. `slipwai adopt --refresh`, from this directory.
3. Read its report, which has three kinds of line.

## Read the report

- **Refreshed.** A fact recorded as `detected` that the tree now says differently was updated in place —
  a command the build gained, a toolchain pin that moved — and the files that read it were regenerated.
  Nothing to decide; `git diff` shows what changed.
- **Disagrees.** A fact a person `confirmed` or `overrode` that a fresh detection contradicts. It was **not**
  changed. Put the two side by side for the user — what was recorded, what the tree says, and the evidence —
  and record the answer: edit `project.json`, keeping the provenance honest (`confirmed` if the recorded
  value stands, `overridden` if they chose the new one), then run this command again so the files follow.
- **Not wrapped.** A directory that builds and has no record. Adding it is a decision, not a refresh: ask
  whether it is part of this system, and if so add its record to `project.json`'s `deployables` as
  `"generated": false` with the commands the report shows, then run this command again.

`{{survey-page}}` was rewritten as the survey now stands, with the evidence for every line, and `{{structure-page}}` — the
architecture view: where anything starts, what depends on what, where change happens — from the tree, the Git
history and a code index's graph where this project has adopted one.
<!-- section: event-model -->

## The event model

This project keeps a global event model in `docs/event-model/model.yaml`. Read `skills/event-modeling/SKILL.md`
first. The code that existed before the method is in that model as one of two things, and which one turns on
whether its behaviour has been modelled or only read:

- **An external system**, where this project reads what it emits or exposes and nobody has modelled what it
  does inside. Model it as the translation pattern that skill describes: an event marked `external: true`
  for what the legacy system emits, the process that reads it, and the command and event that are this
  project's own. This is the honest reading on the day the method arrives, and it stays the reading for
  everything nobody has looked at.
- **A state-stored service of this project**, where somebody has modelled its behaviour against the code —
  its slices written at `observed`, each with the handler it was read off. It is then a service on the
  timeline like any other, on the `state` rung unless a person has recorded `writeModel: events` for it,
  which `slipwai adopt --confirm <name> --write-model events` is how to do.

Neither reading licenses the one thing that is always wrong: nothing in the legacy system's tables, and
nothing in those tables' history, becomes an event by being renamed. `docs/change-strategy.md`, *Be honest
about the event model*, says why that honesty matters here, and what the rung has to do with it.
Run `/observe <capability> <service> <handler>` for the one capability a requirement touches whose behaviour
the model has not yet recorded. It runs the nine steps from source and the passing `/characterise` examples;
the big picture's process proposals remain on its survey page until this evidence exists.
<!-- end section -->

## Then

- `make verify` — the gate still holds after the record moved.
- Commit the result as one change, saying what the survey found and what was decided.
