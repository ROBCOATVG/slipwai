# Coding-agent harnesses

`skills/`, `commands/` and `agents/` are canonical. Native Spec Kit initialization installs its own
`speckit-*` assets; `scripts/agents/project.py` then projects this repository's catalogue into the selected
harness.

```sh
make agents-list
make agents
make check-agents
make models
```

The included registry is derived from Spec Kit's integration registry and records each harness's skill
directory, command directory and format. Skills-native harnesses without a separate command namespace
receive project commands as invocable skills. Never edit a stamped projection: edit its canonical source
and run `make agents`. Before `./init`, `check-agents` deliberately reports that no projections are expected.
The projections are not committed — every harness directory is in `.gitignore`, since a projection is the
canonical file again with a stamp — so a fresh clone has none until `./init` or `make agents` writes them, and
`check-agents` says so rather than failing; `slipwai migrate` re-derives them after every merge. Spec Kit's
own `speckit-*` skills land in the same directory, hashed in `.specify/integrations/*.manifest.json`, and
`check-speckit` reads their absence the same way while the directory is absent.

## How AGENTS.md reaches a harness

`AGENTS.md` is where this repository says how work is done in it. Not every harness reads that name, so
`registry.json` records, per harness, the file it does read (`contextFile`) and what has to happen for
`AGENTS.md` to arrive in it (`contextMode`). All three are implemented by `scripts/agents/project.py`;
`check-agents` fails on any of them being out of step.

Here **context means the repository instruction file**, not the host session's conversation. Projection
does not carry the parent's messages, tool results or accumulated prompt into a delegate. A sub-agent still
starts with its focused stage brief and the repository instructions; where those instructions name an
optional tool such as CodeGraph, it checks whether that tool is available in its own session.

| `contextMode` | Harnesses | What the projector does |
|---|---|---|
| `canonical` | 18 — Codex, Zed, Grok, Droid and the rest | Nothing. The harness reads `AGENTS.md` under its own name. |
| `import` | 1 — Claude Code, `CLAUDE.md` | Writes a region holding `@AGENTS.md`, which that harness reads as an include, so the real file arrives. |
| `copy` | 17 — Gemini, Copilot, Cursor and the rest | Synchronises marker-fenced extension blocks into the context Spec Kit already wrote, replacing stale regions without touching its baseline. |

An `import` harness gets the whole file by reference, which never goes stale. Its import region is the only
part of `CLAUDE.md` the projector claims: everything outside the markers is yours and is never rewritten.
Delete the region and `make agents` puts it back around what you wrote.

A `copy` harness already has Spec Kit's baseline project context. Copying `AGENTS.md` whole would duplicate
that context and charge every session for it twice, so the later pass carries only optional, marker-fenced
extension guidance. That is enough for every delegate to learn, for example, that CodeGraph should be used
when available in its own session. `make agents` refreshes the extension source first, then this copy.

A `copy` harness whose context file does not exist is left alone rather than reported: `specify init` owns
that file's format, frontmatter and all, and inventing one would mean guessing at a shape this repository
does not own. An `import` harness's file is created if absent, because nothing else creates it.

## The agent types

`agents/` holds one named type per stage `/drive` sends to a fresh context — `drive-tasks`,
`drive-implement`, `drive-converge`, `drive-gaps`, `drive-adversary`, `drive-mutation` — and one,
`drive-slice`, for a whole slice. Each declares, in words no harness owns, what its delegate may write
(`none`, `tasks`, `manifest`, `report`) and what it may run (`read-only`, `tasks-command`, `any`), and
carries that stage's standing brief; the per-call brief then
adds only the task, its contract and the file manifest. A stage type is named for its stage, so its model is
that stage's row in `.specify/models.json` and there is no second place a model is chosen. `drive-slice`
declares no stage and takes no model: it runs one slice's whole ladder in a worktree of its own and reads the
table stage by stage inside itself, so resolving one model for it would choose one for fourteen stages at
once.

`registry.json` says under `agentFile` where each harness reads a type and how that file spells the model, the
write scope and the command scope — read from the harness's own documentation on the date the row names, or
`null` where nothing was verified, and the projector then writes no types for it. `make agents` renders each
canonical type into the installed harness's own file: Codex's `sandbox_mode`, Cursor's `readonly`, Copilot's
and Gemini's tool lists, opencode's `permission` map, Claude Code's `disallowedTools`, with the resolved model
beside it. **Read-only does not mean the same thing on every harness.** Codex and Cursor also refuse a command
that changes state; everywhere else the shell is one tool, granted whole or not at all, and an adversary has to
run a reproduction — so `commands: read-only` is carried in the prompt there and the projection's stamp says,
in as many words, that the harness is not holding it. A scope the harness *can* hold is enforced by the
harness, not asked for in a brief, which is the point: an adversary that cannot edit is better than one asked
not to. `tasks-command` is the deliberately narrow exception to read-only commands: the tasks delegate may
run the installed Spec Kit command that creates its one allowed file. No harness can express that exact
allowlist, so every projection says the body still holds it.

**A write scope spelled as a tool list is a grant, not a denial.** Copilot and Gemini withhold every tool the
list leaves out, MCP tools included — so making a type read-only there is also, silently, what puts an MCP
code index out of its reach: no error at the call, just a delegate that reads *probe your MCP route* as a
project with no index. Both lists name the route back (`mcp_*` on Gemini, one `<server>/*` entry per server
this project's extensions install on Copilot), which costs nothing that was being held, because both already
carry the whole shell. The other four reach the session's servers whatever the file says — Claude Code and
Codex inherit them, Cursor inherits every tool, opencode's `permission` map is a denylist — and on Claude Code
the tool arrives *deferred*, a bare name the delegate has to load through the harness's own tool-search step
before it can call it. `registry.json` records all of that under `agentFile.mcp`, with the source and the date
it was read, and every projection's stamp carries it, so a route a harness withholds is one somebody can read.

Because the model lives in these files on five of the six harnesses, `/model-delegation-settings` rewrites them as part of the
change — the line saying so is part of its output — and `check-agents` reads a type that drifted from its
canonical source the same way it reads a drifted skill.

The registry also says, under `subagentModel`, how each harness lets a sub-task run on a chosen model — read
from the harness's own documentation on the date the row names — or `null` where nothing was verified.
`.specify/models.json` puts a role on each stage of `/drive`'s ladder, keyed by the command the stage runs
(`strong` for judgement, `fast` where the input is already fully specified on paper) and maps the roles to
identifiers per harness; `host` is the model running `/drive` itself. `python3 scripts/agents/models.py <stage>`
resolves both into the line `/drive` reads before a stage — the model to delegate to and how, or why the stage
runs on the host model — and `make models` prints the whole table. A harness with a `null` row runs every stage
on the host model, and the line says so. Edit the roles for your harness — only Claude Code's `fast` is seeded —
and `make check-agents` checks the shape. Change it whenever you like: `/model-delegation-settings implement=strong claude.fast=haiku` (the
command over `python3 scripts/agents/models.py --set`) writes a checked edit, `/drive` reads the table before every stage so the
change takes effect at the next one, and `slipwai migrate` merges a newer factory's table over yours rather than
replacing it.

The role selects a model, independently of context. An artifact-driven stage can delegate to a fresh context
on the same strong model instead of rereading the whole driving session. Every delegated call sets the resolved
model explicitly through `subagentModel`; leaving it unset selects a harness default, not the
`.specify/models.json` decision, and makes the benchmark incomparable.

Under `usage`, the registry also says where each harness keeps the tokens a session spent — Claude Code's
transcript under `~/.claude/projects/` and Codex's rollout under `~/.codex/sessions/`, each read from the harness
itself on the date the row names, or `null` where nothing was verified. `scripts/agents/benchmark.py` reads it
between the start and the end of every stage `/drive` runs and writes the result — with which model ran, how long
the stage took, and what the stage reported — into `specs/<feature>/slices/<id>/benchmark.json`, beside the
slice's other artifacts; `/benchmark` draws `specs/<feature>/benchmark.md` from the records and `make benchmark`
prints the same table. Where the harness attributes a sub-agent's lines to the type that ran it — Claude Code
does — the record names the type too, so an adversary pass on one slice is comparable with the same type on
another rather than with whatever else ran on the same model. A `null` row is a
record that says the tokens are unknown and why, never an estimate. The numbers compare the slices of this project
on this harness, and a stage before and after a change to a prompt, a skill or the layout; they are tokens rather
than prices, a stage's count is a floor (the turn that closes it is still being written), and they do not compare
harnesses or projects.

Under `projectMcp`, the registry says which project-scoped file each harness reads an MCP server from, in what
shape, and which flags a headless iteration needs for that file to be honoured in a checkout nobody has trusted
— `.mcp.json` and `--mcp-config` on Claude Code, `.codex/config.toml` and a one-run trust override on Codex,
`.gemini/settings.json`, `.cursor/mcp.json` and `opencode.json` read by their harnesses as they are — each from
the harness's own documentation on the date the row names, or null with a `projectMcpReason`. An extension that
installs an MCP server (`./init --extension codegraph`) names it in every installed harness's file through
`scripts/extensions/guidance.py`, so the connection travels with the checkout instead of living in one user's
home; `scripts/agents/cruise.py` passes the flags when the file exists; and a harness with a null row reaches
the same tool through its CLI from the shell, which is the route `AGENTS.md`'s block names last.
