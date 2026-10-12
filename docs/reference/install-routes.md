# Install routes: which one is supported

Date: 2026-10-12

## Status

Accepted. Decided in slice 12.4, after 12.1, 12.2, 12.3 and 12.5 made the other two routes exist.

## Context

Phase 12 added two new ways for the delivery material — `/sail` and its commands, the stage delegates, the
two roles that run the loop, and the skills they work under — to reach a person's machine:

- **`./init` in a project slipwai generated or adopted**, which is how it has always arrived. `slipwai
  generate` or `slipwai adopt` writes the canonical `commands/`, `skills/` and `agents/` into the
  repository, and `./init` projects them into whichever of the thirty-six harnesses `registry.json` knows.
- **A Claude Code plugin** (`slipwai package plugin`), which installs the material with no project
  generated at all.
- **Per-harness material** (`slipwai package harness`), which lays the same files where any other harness
  reads them, and writes that harness's project MCP configuration.

Three routes is two more than there were, and each is somebody else's format. The failure this decision
exists to prevent is not that one of them breaks — it is that all three work slightly differently, a person
hits a difference, and nobody can say which of the three was *meant* to be right. A project that can be
installed three ways and is supported in one has two ways to be wrong about.

The keel already has the answer written in its gates, which is where this decision is read from rather than
invented. Everything that proves the method works — `make verify`, `make test-docs`, the conformance suite,
the captain's own controls — runs against a **generated project**. Nothing proves a plugin end to end, and
nothing can prove per-harness material without the harness.

## Decision

<!-- route: init -->
### `./init` in a generated or adopted project

**Supported.** This is the route the method is held to. `make verify` runs the whole suite against
generated projects; `make test-docs` generates two projects, drives the interview and runs every command
the guide prints against them; the conformance suite generates once per language package. When any other
route disagrees with this one, **this one is right** and the other is the bug.

It is also the only route that can carry everything. A command is adapted to the project's own toolchain,
an agent type's model is resolved from that project's `.specify/models.json`, a skill's examples are
written in that project's language, and a harness whose commands are TOML or whose agent files are TOML has
them rendered in its own spelling. None of that exists without a project to read.

Reach it with `slipwai generate` for a new repository, or `slipwai adopt` for one that already exists.

<!-- route: plugin -->
### The Claude Code plugin

**A convenience.** It is **not held by a gate**: no gate installs a plugin into Claude Code and drives a
slice with it, so what is proved about it is that it renders — that every file in it is the one
`scaffold.project_files` writes at the same path, because it is produced by the same function. That is a
real guarantee and it is not the same as the route having been run.

Two things it does not carry, by construction rather than by omission:

- **The four language-shaped skills** — `domain-driven-design`, `event-sourcing`, `hexagonal-architecture`
  and `testing` — whose prose is built out of example markers a *language package* answers. The keel names
  no language and a plugin is rendered with no project, so there is nobody to ask.
- **A project's own adaptations**: the commands are rendered for no services and no target, so a command
  that names a project's backends names none.

Its hooks are the generated project's rows, each guarded so that it runs the project's `session.py` only
where there is a project. In a directory with none, they do nothing.

Reach it with `slipwai package plugin <directory>`.

<!-- route: harness -->
### Per-harness material

**A convenience.** The thinner of the two. It is **not held by a gate** either: a gate walks all
thirty-six rows and holds every file it produces to a path that harness's own row declares, which proves
the renderer and proves nothing about the harness. No captain has run a feature end to end on any harness
but Claude Code — `registry.json` records `proven: false` for every row, and this route inherits that.

It carries everything the plugin carries, less whatever the harness's row has no location for, and it says
which: a harness that reads TOML commands is given none, a harness that reads its skills from the person's
home is given none, and twenty-nine harnesses have no project MCP file anybody has verified. Each of those
is a line the verb prints.

Reach it with `slipwai package harness <directory> --harness <key>`.

## Consequences

**A bug report starts with which route.** A difference between a plugin and a generated project is a defect
in the plugin, never in the project, and the fix is in whatever renders the plugin from the project's own
functions.

**The conveniences cannot be maintained separately, and a gate holds that.** `tests/test_install_routes.py`
asserts that the plugin's commands and agent types are `command_files`' and `agent_files`' own output, and
that a harness's material is the plugin's material moved rather than rendered again. The day somebody adds
a second `sail.md` the gate fails.

**A fourth route needs this page changed first.** The same gate holds the page to the routes the keel
actually has, in both directions: a route the page does not name fails it, and so does a route the page
names that the keel has not got.

**Neither convenience is a top-level verb.** Both are verbs of `slipwai package`, where the other things
that make something installable already are, so a person looking for how to install something looks in one
place.

**This is not a promise that the conveniences stay.** They are rendered from the supported route and carry
nothing of their own, which is exactly what makes withdrawing one cheap. Nothing may come to depend on a
plugin carrying something a generated project does not.
