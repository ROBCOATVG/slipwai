# Install routes: which one is supported

Date: 2026-10-12

## Status

Accepted. Slice 12.4 made this decision. Slices 12.1, 12.2, 12.3 and 12.5 came first, and they made the
other two routes exist.

## Context

The delivery material is `/sail` and its commands, the stage delegates, the two roles that run the loop,
and the skills that they work under. Phase 12 added two new ways for this material to reach a person's
machine. There are now three routes:

- **`./init` in a project that slipwai generated or adopted.** The material has always arrived this way.
  `slipwai generate` or `slipwai adopt` writes the canonical `commands/`, `skills/` and `agents/` into the
  repository. `./init` then projects them into each of the thirty-six harnesses that `registry.json` knows.
- **A Claude Code plugin** (`slipwai package plugin`). It installs the material without a generated project.
- **Per-harness material** (`slipwai package harness`). It puts the same files where any other harness reads
  them, and it writes that harness's project MCP configuration.

Three routes is two more than before, and each new route uses somebody else's format. The risk is not that
one route breaks. The risk is that all three routes work slightly differently, a person meets a difference,
and nobody can say which route was *meant* to be correct. If a project can be installed three ways but is
supported in one way, there are two ways for it to be wrong.

The keel's gates already give the answer, so this decision reads the answer from the gates instead of
inventing one. Everything that proves the method works runs against a **generated project**: `make verify`,
`make test-docs`, the conformance suite, and the captain's own controls. Nothing proves a plugin from start
to end. Nothing can prove per-harness material without the harness.

## Decision

<!-- route: init -->
### `./init` in a generated or adopted project

**Supported.** The method is held to this route:

- `make verify` runs the whole suite against generated projects.
- `make test-docs` generates two projects, drives the interview, and runs against them every command that
  the guide prints.
- The conformance suite generates a project once for each language package.

When another route disagrees with this route, **this route is correct**, and the other route has the bug.

This is also the only route that can carry everything:

- A command is adapted to the project's own toolchain.
- An agent type's model comes from that project's `.specify/models.json`.
- A skill's examples are written in that project's language.
- When a harness uses TOML for its commands or its agent files, the files are rendered in TOML for it.

None of this is possible without a project to read.

Use `slipwai generate` for a new repository, or `slipwai adopt` for a repository that already exists.

<!-- route: plugin -->
### The Claude Code plugin

**A convenience.** It is **not held by a gate**. No gate installs a plugin into Claude Code and drives a
slice with it. What is proved is that the plugin renders: every file in it is the file that
`scaffold.project_files` writes at the same path, because the same function produces it. That is a real
guarantee, but it is not the same as running the route.

The plugin does not carry two things. This is by design, not by omission:

- **The four language-shaped skills**: `domain-driven-design`, `event-sourcing`, `hexagonal-architecture`
  and `testing`. Their text is built from example markers that a *language package* answers. The keel names
  no language, and the plugin is rendered without a project, so there is nothing to ask.
- **A project's own adaptations.** The commands are rendered for no services and no target. So a command
  that would name a project's backends names none.

The plugin's hooks are the generated project's hook rows. Each hook is guarded, so it runs the project's
`session.py` only where there is a project. In a directory without a project, the hooks do nothing.

Use `slipwai package plugin <directory>`.

<!-- route: harness -->
### Per-harness material

**A convenience.** This route is thinner than the plugin. It is **not held by a gate** either. A gate walks
all thirty-six rows. It checks that every file it produces goes to the path that the harness's own row
declares. This proves the renderer. It proves nothing about the harness. No captain has run a feature from
start to end on any harness except Claude Code. `registry.json` records `proven: false` for every row, and
this route has the same status.

This route carries everything that the plugin carries, except the files for which the harness's row has no
location. It says which files it leaves out:

- A harness that reads TOML commands gets no commands.
- A harness that reads its skills from the person's home directory gets no skills.
- Twenty-nine harnesses have no project MCP file that anybody has verified.

The verb prints a line for each of these.

Use `slipwai package harness <directory> --harness <key>`.

## Consequences

**A bug report starts with the route.** A difference between a plugin and a generated project is a defect
in the plugin, never in the project. The fix goes in the code that renders the plugin from the project's own
functions.

**Nobody can maintain the conveniences separately, and a gate makes sure of this.**
`tests/test_install_routes.py` checks two things:

- The plugin's commands and agent types are the output of `command_files` and `agent_files`.
- A harness's material is the plugin's material moved, not rendered again.

If somebody adds a second `sail.md`, the gate fails.

**A fourth route needs this page to change first.** The same gate holds this page to the routes that the
keel has, in both directions. The gate fails for a route that the page does not name. It also fails for a
route that the page names and the keel does not have.

**Neither convenience is a top-level verb.** Both are verbs of `slipwai package`, beside the other things
that make something installable. So a person who looks for how to install something looks in one place.

**This page does not promise that the conveniences stay.** They are rendered from the supported route and
carry nothing of their own. That makes it cheap to withdraw one. Nothing may come to depend on a plugin that
carries something a generated project does not.
