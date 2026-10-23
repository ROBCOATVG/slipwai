---
description: Add a service to this project with the factory's add-service, and leave it green
argument-hint: <name> --purpose "<what it owns>" [--context <name>]... [--language <language>] [--framework <framework>] [--<axis> <answer>]
---

# Add service

A service is a change to the list in `project.json` and a regeneration of everything that reads it — the
Makefile, Compose, CI, the workspace, `scripts/verify`, the prose that lists the services. The factory's
`add-service` makes both. Nothing here is copied from `{{example-path}}` by hand: a copy has to find the nine
files that name it, and misses the tenth.

## What is here

{{applications}}

## Decide with the user, not for them

- **Name** — `apps/<name>` and its Compose service: lowercase letters, digits and hyphens, and none of the
  names above.
- **Language and framework** — {{default-language}}
  Another language beside it is
  `--language {{languages}}`; a language with more than one framework also takes
  `--framework {{frameworks}}`, which is refused without `--language`. `--backend <key>` names both at once,
  and is refused beside either.
- **Answers** — one flag per question: {{axes}}.
  An axis without a flag {{inherits}} `add-service --help` lists every
  option an installed language answers; one this project's target does not offer, or this service's language
  does not answer, is refused when the command runs, naming one it would take.
- **Purpose and contexts** — `--purpose "<what it owns, in a sentence or two>"` and `--context <name>`, once
  per bounded context the service holds. The purpose is what `/sail` reads when it decides which service a
  slice belongs to: a service added without one is a directory the loop cannot place work in, and it will
  stop to ask before it does. A context is one already on the list above, or a new one; without any the
  service is a context of its own. A context may span several services; the tree stays `apps/<name>`.
  A service already listed is described after the fact: `<factory> describe-service <name> --purpose "..." --context <name>`.

The language, the store, and what the service owns are product decisions. When the request does not name
them, ask; taking `{{example-name}}`'s answers is the default for the first two, and saying so is part of
asking. Someone asking for a service has a reason for wanting it separate — the purpose is that reason,
written down. The port is the command's own decision — the next one free — and is not asked.

## Is a service the right shape?

A new bounded context is not by itself a reason for a new service. This project starts as one service that
may hold several contexts as `src/<context>/`, each behind its own `public` module, with `make check-imports`
keeping them apart — and that is where a context whose boundary is still being found belongs. A service is
the right shape when there is a *deployment* reason: its own release cadence, its own scaling or runtime, a
data store of its own, another team, another language. When the request is "a context for X" rather than
one of those, say so, and offer to add `X` to `{{example-name}}`'s `contexts` in `project.json` instead —
`docs/architecture.md`, *Bounded contexts*, has the three rungs and the reasoning to point at.

## Find the keel

The command belongs to the keel that generated this repository, not to the repository. It is
`slipwai add-service` where `slipwai` is on the `PATH` — installed with pip, or a released executable — and
`path/to/slipwai/slipwai add-service` from a checkout. If neither is at hand, ask where the
factory is. A wrong guess at its location is a stop, not a reason to start copying `{{example-path}}`: building
the application by hand is the thing this command exists to prevent.

## Run it

1. `git status --porcelain` prints nothing. The command refuses an unclean tree so that `git checkout . &&
   git clean -fd` undoes exactly what it wrote and nothing else; commit or stash first rather than working
   around the refusal.
2. `<factory> add-service <name> --purpose "<what it owns>" [--context <name>] [--language <language>] [--<axis> <answer>]`, from this directory.
3. Read its report: what it added under `apps/<name>`, and which files it regenerated from the list.

## Then

- `git diff` over the regenerated files. A hand edit that came back changed there was made to a file the
  list drives; move it somewhere the generator does not own, then rerun.
- `make verify` — green with the new application before anything else is done to it.
- Say how it runs: `make dev-<name>` in the foreground, `make demo` with the rest, and its port from the
  report. Its health example is the placeholder the first slice replaces; `/sail` from there.
- It shares the local backing services with every other service — one `DATABASE_URL`, one database. That is
  right for a walking skeleton and wrong for a product: give it its own database or schema before it owns
  any data, and say so when handing it over.
{{after-service}}
Nothing is committed by the command. Commit the result as one change, and say what was added and how to
run it.
