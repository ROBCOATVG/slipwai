"""`.specify/models.json`: which model runs each stage of `/drive`'s ladder, by role — and the section of
`commands/drive.md` that applies it.

Every stage ran on whatever model the harness happened to be set to, at the same price for gauging whether a
slice converged as for turning `examples.md` into tests. The table puts the choice in the project,
versioned with it, keyed by the command each stage runs: `strong` where a stage decides what to build or
whether it was built, `fast` where the input is already fully specified on paper. Roles rather than model
names, because identifiers are provider-specific and go stale; the roles are mapped to identifiers under
`roles`, per harness, in the one place the project owner edits. The split is a hypothesis until benchmarking measures
it, which is why every stage says out loud which model ran it.

`host` is a value, not an absence: the model running `/drive` itself, with no delegation. `strong` maps to it
everywhere, since a strong host handing its judgement stages to a named model would be a downgrade as often
as not. `fast` is seeded only where the identifier is verified — Claude Code's Agent tool takes `sonnet` as an
alias — and is `null` on every other harness that can switch, which `scripts/agents/models.py` reports as "no
identifier mapped" rather than pretending. A harness the registry records no mechanism for gets no row: the
script says every stage runs on the host model there, whatever the table asks.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..assets import TOOLKIT_ROOT
from ..layout import AT_ROOT, Layout

REGISTRY = TOOLKIT_ROOT / "scripts/agents/registry.json"
# What a delegate of a stage may write, and what it may run, in words no harness owns. `agents/` declares them
# per type and `scripts/agents/project.py` maps each to the nearest thing each harness can express — Codex's
# sandbox, Cursor's `readonly`, Copilot's and Gemini's tool lists, opencode's permissions, Claude Code's
# `disallowedTools` — saying in the projection's stamp where a harness could not express one at all.
NONE, MANIFEST, REPORT, TASKS = "none", "manifest", "report", "tasks"
READ_ONLY, TASK_COMMAND, ANY = "read-only", "tasks-command", "any"
# The prefix every projected agent type carries, so a project's own agents are never shadowed by the factory's.
AGENT = "drive-"
# A type that takes no stage's model. `/drive`'s slice delegate runs a whole slice — its example map
# through its converged verdict — and *Who runs each stage* still chooses the model stage by stage inside it,
# so resolving one for the delegate itself would pick a model for fourteen stages at once. It inherits, and the
# projection says which of the two reasons it carries no model.
NO_STAGE = "none"


@dataclass(frozen=True)
class Stage:
    """One rung of `/drive`'s ladder: the role that runs it and, where it is delegated, what that delegate may do.

    `writes` and `commands` are declared for exactly the stages the ladder sends to a fresh context, which is
    what makes a stage delegable: tasks from a complete plan, implementation from a complete task, converge,
    post-implementation gaps, adversary and mutation. A conversational stage — one that may have to ask the
    user a product question — has neither and stays on the host, so there is nothing to project for it and
    nothing to enforce.
    """

    key: str
    role: str
    writes: str | None = None
    commands: str | None = None

    @property
    def delegable(self) -> bool:
        return self.writes is not None and self.commands is not None

    @property
    def agent(self) -> str:
        """The type's name, which is the stage's key: one lookup for the model, none for the mapping."""
        return f"{AGENT}{self.key}"


# The default split, in ladder order. Projections are a Python script here and have no row.
STAGES: tuple[Stage, ...] = (
    Stage("principles", "strong"),
    Stage("specify", "strong"),
    Stage("event-model", "strong"),
    Stage("split", "strong"),
    Stage("example-map", "strong"),
    # Both `/gaps` passes share this row; only the one after implementation is delegated, and it reads.
    Stage("gaps", "strong", writes=NONE, commands=READ_ONLY),
    Stage("release-constraint", "strong"),
    Stage("plan", "strong"),
    Stage("tasks", "fast", writes=TASKS, commands=TASK_COMMAND),
    Stage("implement", "fast", writes=MANIFEST, commands=ANY),
    Stage("converge", "strong", writes=MANIFEST, commands=ANY),
    Stage("demo", "strong"),
    Stage("adversary", "strong", writes=NONE, commands=READ_ONLY),
    Stage("mutation", "fast", writes=REPORT, commands=ANY),
)
DEFAULT_ROLE = "strong"
HOST = "host"
# The one identifier verified today: an alias the Agent tool's `model` parameter takes (its schema, 2026-09-09).
FAST_SEEDED = {"claude": "sonnet"}


def switchable_harnesses() -> list[dict]:
    """Every registry row that records how a sub-task gets its model, in registry order."""
    harnesses = json.loads(REGISTRY.read_text())["harnesses"]
    return [entry for entry in harnesses if isinstance(entry.get("subagentModel"), dict)]


def stage_models() -> str:
    table = {
        "_comment": (
            "Which model runs each stage of /drive's ladder, by role. `stages` is keyed by the command each "
            "stage runs, with a `default` row for the rest; `roles` maps each role to an identifier per harness "
            "— `host` is the model running /drive itself, null is no identifier mapped yet. Edit the roles for "
            "your harness, by hand or with `python3 scripts/agents/models.py --set claude.fast=haiku`, at any time: "
            "/drive reads this before every stage. `make models` shows what results, `make check-agents` checks the "
            "shape. A harness with no row here cannot choose a model for a sub-task (scripts/agents/registry.json, "
            "`subagentModel`) and runs every stage on the host model. docs/agent-harnesses.md says more."
        ),
        "stages": {"default": DEFAULT_ROLE, **{stage.key: stage.role for stage in STAGES}},
        "roles": {
            entry["key"]: {"strong": HOST, "fast": FAST_SEEDED.get(entry["key"])} for entry in switchable_harnesses()
        },
    }
    return json.dumps(table, indent=2, ensure_ascii=False) + "\n"


# What each type may write and run, said in the drive section the way `agents/` declares it, so the ladder and
# the files cannot disagree about which delegate is allowed what.
SCOPE = {
    NONE: "nothing",
    MANIFEST: "the files its manifest names",
    REPORT: "only the report it produces",
    TASKS: "only the slice's `tasks.md`",
    READ_ONLY: "anything that reads",
    TASK_COMMAND: "anything that reads, plus the installed tasks command",
    ANY: "anything",
}


def delegable_types() -> str:
    """The table of types in the drive section: one row per delegable stage, from the declaration itself."""
    rows = "\n".join(
        f"| `{stage.key}` | `{stage.agent}` | {SCOPE[writes]} | {SCOPE[commands]} |"
        for stage in STAGES
        for writes, commands in [(stage.writes, stage.commands)]
        if writes is not None and commands is not None
    )
    return f"""| Stage | Type | Writes | Runs |
|---|---|---|---|
{rows}"""


def who_runs_each_stage(layout: Layout = AT_ROOT) -> str:
    """The `/drive` section that applies the table: read the line, delegate to the type, and say which ran."""
    types = delegable_types()
    return f"""## Who runs each stage

`.specify/models.json` says which model each stage runs on, by role: `strong` where a stage decides what to
build or whether it was built, `fast` where the input is already fully specified on paper — a plan into
tasks, `examples.md` into tests and code, a mutation run. Before running a stage, read its line:

```sh
python3 scripts/agents/models.py implement   # keyed by the command the stage runs; `{layout.make} models` prints them all
```

The line chooses the model; it does not require that model to inherit this session's context. Prefer a fresh
sub-agent whenever the stage can get all of its inputs from artifacts on disk. Six stages are exactly that,
and each is a **named agent type** this project carries in `agents/`, projected into the installed harness by
`{layout.make} agents` with its model and as much of its scope as that harness can enforce:

{types}

`gaps` runs twice and only the pass after implementation is delegated: the pre-planning one may have to ask a
product question, which is the whole reason a stage stays here. Any other conversational stage stays here too,
and has no type for that reason. There is a seventh type, `drive-slice`, for a whole slice rather than a stage:
*Running ready slices concurrently* is where it is delegated, and it reads this section from inside its own
worktree to choose a model for each stage it then runs.

Delegate to the type by name. The type is the standing brief, so the call adds only the task, its contract and
the file manifest — it never describes the role again or restates the scope, and it does not give the delegate
conclusions. It may give it a map: which precedent to copy, which decision in `research.md` governs, which
helper already exists — a file and a section, which the delegate then opens and reads for itself. Naming where
a fact lives is a pointer and costs a sentence; asserting what it says is a conclusion, and a brief that asked
the delegate to read a decision itself and report what it says has caught what a brief that summarised it got
wrong. Where a brief offers a delegate more than one way of working, every permission is written into each
mode that has it, even at the price of a repeated paragraph: a fresh delegate reads a silence conservatively,
and the conservative reading is the expensive one. The page each type is written on is `docs/delegated-agent-safety.md`, the standing boundary every
delegation is held to: reference it, restate none of it (`AGENTS.md`, *Delegated agents*).

**A delegate does not inherit this session's code-index connection.** Where `AGENTS.md` carries the
CodeGraph extension block, three of the types above — `drive-converge`, `drive-gaps` and `drive-adversary` —
are exploration-heavy, and *what does this code not yet do* is a blast-radius question the index answers.
Prefer to run those here when this session has the MCP connection: a fresh delegate does not inherit it.
Delegation is still valid. Its brief says to follow the block in `AGENTS.md`, probe its own MCP, installed
CLI and `npx` routes in that order, and name which route answered. A delegate with the CLI on `PATH` can
query the same project index; it falls back to text search only when all routes are unavailable. Never pass
the parent conversation merely to carry the connection.

Delegate both when the line names another model and when the same strong model can run in a fresh context.
On a harness whose agent file names a model (`scripts/agents/registry.json`, `agentFile`) the type already
carries the one the table resolved; everywhere else set it explicitly through the mechanism the registry
names, and never accept that mechanism's implicit default. If the harness cannot start a fresh sub-agent on
the selected model, run the stage here and say why. Then read its result from disk the way every stage is
read. Either way the stage says, in one line, which type ran it, which model, whether it was delegated and
whether its context was fresh (`drive-implement · model: sonnet · delegated, fresh context` ·
`drive-adversary · model: host · delegated, fresh context` · `model: host, current context — harness cannot
delegate`). Those lines make type, model and context measurable; a stage that switched any of them silently
cannot be compared with one that did not. Nothing about what a stage produces changes with who runs it — the
artifacts, gates and stops are the same — and a sub-agent that meets a product decision hands the
question back here rather than answering it.

A stage is not always one delegate. Before delegating implementation, read `tasks.md` for its `[P]` markers and
its *Parallel opportunities* section: the tasks command writes both, and they are the plan for what may run
alongside what — written by one half of this workflow to be read here, not decoration. Every unchecked `[P]`
task whose files are disjoint from the batch already running is a concurrent sibling, delegated in the same turn
with a manifest of its own — and so is a task with no marker whose manifest shares no file with the batch. The
marker is the tasks command's reading of production-code contention, and it under-reports: one slice's list
marked one pair concurrent, said of the rest "none, by construction", and left two pairs that shared no file
to run in sequence. The manifests are the artifact; read them, and let only an overlap with a running
sibling's files, or what the section rules out, keep a task waiting. What the
section rules out stays sequential whatever the markers seem to allow — a RED-GREEN-REFACTOR increment starts
from a green, committed suite, and two of them at once is the batched-tests anti-pattern with a `[P]` on it.
The siblings are `drive-implement` delegates, and that type is where the rule they cannot infer for
themselves already lives: **no concurrent delegate writes `tasks.md`**. It is the one file every sibling would
otherwise contend for, so each reports which task it finished and this session ticks the checkbox.

When several delegates form one batch, report once when the batch completes rather than once per delegate.
Verify their claims by spot-checking the recorded reproduction or RED evidence; do not repeat each complete
investigation in the host context. Do not re-investigate. A delegate that was stopped has filed nothing:
everything in its stop notification is a lead, never a result, and a lead is re-run before it is written
anywhere outside this session. An adversary pass is the same kind of batch:
disjoint-manifest seams of one pass are concurrent `drive-adversary` siblings in one turn, and the host
writes the log after the batch rather than re-attacking. It records the type and the explicit model that
ran each seam in `specs/<feature>/adversary-log.md`, especially when seams use different models.

The table is the project owner's to change at any point, and it is read before every stage rather than once,
so a change takes effect at the next stage — and rewrites the agent types, which carry the model on every
harness that reads one from a file: `/who-runs implement=strong claude.fast=haiku` edits it checked
(`commands/who-runs.md`, over `python3 scripts/agents/models.py --set`), or edit the file by hand and let
`make check-agents` hold the shape. When the owner asks for a different model at a stage, `/who-runs` is the
change — not a note, and not a switch made silently in the delegation. Commit the file: the choice is versioned with the project, and `slipwai
migrate` merges a newer factory's table over it rather than replacing it.
"""


def who_runs_command(layout: Layout = AT_ROOT) -> str:
    """`/who-runs`: the table shown, or changed through the checked `--set` — never by editing a delegation."""
    return f"""---
description: Show or change which model runs each stage of /drive
argument-hint: [stage=role | harness.role=identifier ...]
---

# Who runs

`.specify/models.json` says which model runs each stage of `/drive`'s ladder, by role — `strong` where a
stage decides what to build or whether it was built, `fast` where the input is already fully specified on
paper — and what each role maps to on the harness this project is initialised for. This command is how the
table is read and how it changes: as and when, in one step, checked, and never by quietly picking a different
model inside a delegation.

## No argument — show the table

```sh
python3 scripts/agents/models.py
```

Report it as printed: the installed harness, whether it can choose a model for a sub-task at all and how
(`scripts/agents/registry.json`, `subagentModel`), then each stage's role, the model or the host model, and
why. No harness installed is a line of its own — `./init --integration <agent>` records one.

## Arguments — change it

Each argument is one of two edits, and the first thing to decide is which one the person means:

- `stage=role` moves a stage between roles — `implement=strong` puts implementation back on the model running
  `/drive`. The keys are the commands the ladder runs: `principles`, `specify`, `event-model`, `split`,
  `example-map`, `gaps`, `release-constraint`, `plan`, `tasks`, `implement`, `converge`, `demo`, `adversary`,
  `mutation`, and `default` for any stage without a row of its own.
- `harness.role=identifier` changes what a role runs on — `claude.fast=haiku`. `host` is the model running
  `/drive`; `null` is no identifier mapped, which the line before each stage then says.

Pass them through exactly as given:

```sh
python3 scripts/agents/models.py --set $ARGUMENTS
```

It rewrites the agent types as it goes: `agents/drive-<stage>.md` is projected into the installed harness
with the model this table resolves, so a change here that left them behind would take effect on one harness
and not another, and `make check-agents` would report drift in a file nobody edited. The line saying so is
part of the output; report it.

The script refuses a stage the ladder does not have, a harness the registry does not know or records no
mechanism for, and any change that would leave the table malformed — and writes nothing then. Report a refusal
in its words; do not work around it by editing the file. A role a stage newly names is added as `null` under
every harness: say so, and ask for the identifier rather than inventing one.

Then show the line for each stage the change touches (`python3 scripts/agents/models.py implement`) and commit
`.specify/models.json` on its own, with a message naming the change. The choice is versioned with the project,
and a change buried in a slice's commit is a change nobody finds.

## When the request is in words

"Use the cheap model for implementation" is two possible edits, and the identifier is the part not to guess.
Where the harness's mechanism takes an alias the registry names (`identifiers` under its `subagentModel`), use
that spelling; otherwise ask which identifier, since model names are provider-specific and go stale. Never map
a role for a harness this project is not initialised for, and never for one the registry says cannot switch —
the script refuses the second, and the first is a setting nothing reads. A change takes effect at the next
stage `/drive` runs; nothing already running is interrupted. `{layout.make} models` prints the same table.
"""
