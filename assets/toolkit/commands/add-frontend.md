---
description: Add a browser app to this project with the factory's add-frontend, and leave it green
argument-hint: <name> [--api <service>]
---

# Add frontend

A browser app is a change to the list in `project.json` and a regeneration of everything that reads it —
the npm workspace and lock, the Makefile, Compose, `.gitignore`, the agent settings, the prose that lists
the applications. The factory's `add-frontend` makes both. Nothing here is copied from another `apps/`
directory by hand.

## What is here

{{applications}}
<!-- section: no-browser-app -->

No browser app yet; this command adds the first.
<!-- end section -->

## Decide with the user, not for them

- **Name** — `apps/<name>` and its Compose service: lowercase letters, digits and hyphens, and none of the
  names above.
- **Which service** — `--api <service>` names the service its `/api` calls are proxied to, by the Vite dev
  server in the foreground and by `API_ORIGIN` inside Compose. {{default-api}} A browser app
  talks to one service through that boundary and never reads a store directly.

The framework is not a question: every browser app is the one the project was generated with, and the
dev-server port is the command's own decision — the next one free.

## Find the keel

The command belongs to the keel that generated this repository, not to the repository. It is
`slipwai add-frontend` where `slipwai` is on the `PATH` — installed with pip, or a released executable — and
`path/to/slipwai/slipwai add-frontend` from a checkout. If neither is at hand, ask where the
factory is. A wrong guess at its location is a stop, not a reason to start copying `{{example-path}}`: building
the application by hand is the thing this command exists to prevent.

## Run it

1. `git status --porcelain` prints nothing. The command refuses an unclean tree so that `git checkout . &&
   git clean -fd` undoes exactly what it wrote and nothing else; commit or stash first rather than working
   around the refusal.
2. `<factory> add-frontend <name> [--api <service>]`, from this directory.
3. Read its report: what it added under `apps/<name>`, and which files it regenerated from the list.

## Then

- `git diff` over the regenerated files. A hand edit that came back changed there was made to a file the
  list drives; move it somewhere the generator does not own, then rerun.
- `make verify` — green with the new application before anything else is done to it.
- Say how it runs: `make dev-<name>` in the foreground — with `WEB_HOST=0.0.0.0` when the browser is not on
  this machine — `make demo` with the rest, and its port from the report. Its page is the placeholder the
  first slice replaces; `/sail` from there.
{{after-web}}
Nothing is committed by the command. Commit the result as one change, and say what was added and how to
run it.
