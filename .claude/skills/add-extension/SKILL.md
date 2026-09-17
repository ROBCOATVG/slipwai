---
name: add-extension
description: Factory-maintenance skill for adding an optional dev-tooling extension to slipwai — a code-intelligence server, a linter service, a secrets scanner, anything a generated project can opt into with `./init --extension <key>` without it changing the generated skeleton's code. Covers catalog.json's extensions object, assets/toolkit/scripts/extensions/<key>/init.py, tests and docs. Use when asked to add, restore or scaffold a `./init --extension` hook. Not for infrastructure a service's code calls at runtime (event store, HTTP, identity) — that is add-backing-service.
---

# Add an extension

An **extension** is an opt-in developer-tooling hook, adopted with `./init --extension <key>`
(repeatable, alongside `--integration <agent>`) — never an axis: it changes nothing about the generated
skeleton's code, and it is answered at `./init` time rather than baked in at `slipwai generate` time. CodeGraph
is the only one today. `docs/extensions.md` is the full contract; this skill is the procedure that keeps a
new one to it.

Read `docs/extensions.md` in full before starting. It is short by design — an extension is a much lighter
commitment than a backing service (no per-backend adapter matrix, no prune tables, no committed locks) —
and everything below just walks its obligations in order.

## 0. Confirm it is this job

- Something a service's own code depends on at runtime (a database, a message broker, an identity
  provider) is `add-backing-service`, not this. An extension never appears in `apps`/`Selection`, never has
  a per-backend adapter, and a generated project works identically whether or not one was ever adopted.
- Something that changes what a generated skeleton *contains* (a new language, a new framework) is
  `add-language`/`add-framework`, not this.
- If the tool genuinely needs no code in the generated project at all — nothing to install, nothing to
  index, nothing worth telling the agent — it probably doesn't need an extension either; a line in
  `docs/requirements.md` may be the whole job.

## 1. `catalog.json`

Add the entry under `extensions`:

```json
"extensions": {
  "<key>": {
    "name": "<Human name>",
    "description": "<One sentence: what it is and what it buys the agent>",
    "ignore": "<gitignore lines its local state needs>\n"
  }
}
```

`name` and `description` are required; `ignore` is optional — only add it if the tool writes local state
into the generated project (an index directory, a cache). `src/slipwai/extensions.py`'s
`validate_extensions` refuses anything else at this level, and `tests/test_extensions.py` covers it — read
both before writing the entry, not after `make verify` fails.

`description` is user-facing, not internal bookkeeping: `./init` reads it straight into the terminal prompt
it offers when no `--extension` was named on the command line (see "Asking for it" in
`docs/extensions.md`). Write it for whoever is deciding whether to adopt the extension right now, not for a
future maintainer reading the catalog.

## 2. `assets/toolkit/scripts/extensions/<key>/init.py`

This is the entire runtime half. It ships to every generated project automatically — `assets/toolkit/` is
copied as a tree, nothing routes on the `extensions/` path specially — and `./init --extension <key>` runs
it as `python3 scripts/extensions/<key>/init.py` once Spec Kit and the agent projection are already in
place.

Use `assets/toolkit/scripts/extensions/codegraph/init.py` as the template and meet the obligations,
restated from `docs/extensions.md`:

1. **Replaceably idempotent** — expose a side-effect-free `project_guidance()` that records the election
   through `scripts/extensions/guidance.py` and replaces the factory-owned marker region when present,
   appending only when absent. `make agents` and `slipwai migrate` call the shared projector without
   rerunning setup.
2. **Non-fatal** — a missing CLI or a failed setup step is reported to stderr and returns 0. `./init`
   already has Spec Kit and the agent projection by the time this runs; don't take that down over an
   optional tool.
3. **Points the agent at it** — project a short, marker-fenced block into `AGENTS.md`
   (`<!-- extension:<key>:begin -->` / `:end`) telling the agent when to reach for the tool and that it
   should query it through the best route its own session offers. This is the one thing that makes the
   extension worth adopting at all — an installed-but-unqueried tool is dead weight. Keep it readable in one
   go: what the tool answers, the direct-query instruction, and how the agent can tell that this environment
   cannot reach the tool at all — a checkout travels into containers, sandboxes and CI runners that carry the
   extension's state without its tooling, and a block that assumes otherwise is wrong there in silence. Do not
   restate what the tool's own installer already writes into the agent's context file, if it writes one
   (CodeGraph's does) — this block is the reinforcement a generic installer cannot know to add, not a
   duplicate of it.
4. **Gates what can go stale** — where the extension leaves local state that keeps answering after it stops
   being true, ship `assets/toolkit/scripts/check-<key>.py` and add it to `verify_dependencies` and the
   targets in `src/slipwai/project/makefile.py`. Standard library, a clear no-op when the extension was never
   adopted, and a failure that says how to catch the state up. `check-codegraph.py` is the reference.

## 3. Tests and docs

Everything lives in `tests/test_extensions.py` — both classes, modeled on the `codegraph` cases already
there:

- `ExtensionsCatalogTest` — extend the schema assertions if the new entry exercises a case the existing
  ones don't (an entry with no `ignore`, for instance).
- `ExtensionsTest` — fake the tool's CLI on `PATH`, run `./init --extension <key>`, assert on what got
  invoked, that `AGENTS.md` carries the marker block, that re-projection replaces changed canonical text
  without duplicating its markers, and that a
  missing CLI leaves `./init` exiting 0. If the new extension changes what the terminal prompt shows in a
  way worth pinning down, `run_init_at_a_terminal` in that file is the pty-backed helper for it — the
  `codegraph` prompt tests use it already.
- `README.md`'s "Key features" table and the `--extension codegraph` example in "How to use it" — add a
  clause or a second example if the new extension is one worth naming to a first-time reader; don't expand
  either into a survey of every extension.

## 4. Verify

`make verify` at the factory root. Then a manual smoke test: generate a sample project, run `./init
--integration claude --extension <key>` against it, and read the resulting `AGENTS.md` and `.gitignore`.
