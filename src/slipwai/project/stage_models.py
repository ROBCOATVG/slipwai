"""`.specify/models.json`: which model runs each stage of `/sail`'s ladder, by role — and the section of
`commands/sail.md` that applies it.

Every stage ran on whatever model the harness happened to be set to, at the same price for gauging whether a
slice converged as for turning `examples.md` into tests. The table puts the choice in the project,
versioned with it, keyed by the command each stage runs: `strong` where a stage decides what to build or
whether it was built, `fast` where the input is already fully specified on paper, `review` where a slice's
whole diff is read by someone who did not write it. Roles rather than model names, because identifiers are
provider-specific and go stale; they are mapped under `roles`, per harness, in the one place the project
owner edits. The split is a hypothesis until benchmarking measures it, which is why every stage says out
loud which model ran it.

`host` is a value, not an absence: the model running `/sail` itself, with no delegation. `strong` and
`review` both map to it, since a strong host handing its judgement away is as often a downgrade as not.
`fast` is seeded only where the identifier is verified — Claude Code's Agent tool takes `sonnet` as an alias
— and is `null` on every other harness that can switch, which `scripts/agents/models.py` reports as "no
identifier mapped" rather than pretending. A harness the registry records no mechanism for gets no row.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..assets import TOOLKIT_ROOT

REGISTRY = TOOLKIT_ROOT / "scripts/agents/registry.json"
# What a delegate of a stage may write, and what it may run, in words no harness owns. `agents/` declares them
# per type and `scripts/agents/project.py` maps each to the nearest thing each harness can express — Codex's
# sandbox, Cursor's `readonly`, Copilot's and Gemini's tool lists, opencode's permissions, Claude Code's
# `disallowedTools` — saying in the projection's stamp where a harness could not express one at all.
NONE, MANIFEST, REPORT, TASKS = "none", "manifest", "report", "tasks"
READ_ONLY, TASK_COMMAND, ANY = "read-only", "tasks-command", "any"
# The prefix every projected agent type carries, so a project's own agents are never shadowed by the keel's.
AGENT = "sail-"
# A type that takes no stage's model. `/sail`'s slice delegate runs a whole slice, and *Who runs each stage*
# chooses stage by stage inside it, so resolving one here would pick a model for fourteen stages at once.
NO_STAGE = "none"


@dataclass(frozen=True)
class Stage:
    """One rung of `/sail`'s ladder: the role that runs it and, where it is delegated, what that delegate may do.

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
    # The heading the rung carries in `commands/sail.md`, so the page and this table cannot drift apart.
    # Two stages may share one: a plan and the tasks cut from it are one rung and two models. A stage that
    # is not a rung of the ladder carries none, and `rung` says which it is.
    title: str = ""

    @property
    def rung(self) -> bool:
        return bool(self.title)

    @property
    def delegable(self) -> bool:
        return self.writes is not None and self.commands is not None

    @property
    def agent(self) -> str:
        """The type's name, which is the stage's key: one lookup for the model, none for the mapping."""
        return f"{AGENT}{self.key}"


#: What a stage was called before its name said who runs it. Read on the way in — by
#: `scripts/agents/models.py` for a table a person has edited and by `benchmark.py` for a record already
#: written — so a project that has not migrated yet keeps working, and says which name it read.
RENAMED = {
    "gaps": "gaps-lookout", "tasks": "tasks-quartermaster", "implement": "implement-shipwright",
    "converge": "converge-navigator", "review": "review-mate", "adversary": "adversary-privateer",
    "mutation": "mutation-shipworm", "skipper": "decide-skipper", "hand": "demo-hand",
    "bosun": "unblock-bosun",
}

# The default split, in ladder order. Projections are a Python script here and have no row.
# What the role buys is the option of a different model on reading a diff than on writing it.
REVIEW = "review"
#: The role the two judgement delegates of `/cruise` take, so a project can put a bigger model on deciding
#: a product question than on driving the ladder past it. Named for the work, as every role is.
DECIDE = "decide"

# Every delegable stage is named *purpose first, then the crew member who does it*; every stage that stays
# on the host is named for the work alone. That is the table's own rule made visible in the key, which is
# the only part of it a person editing `.specify/models.json` can see — `writes` and `commands` say the
# same thing in two columns nobody reads at three in the morning. A lookout reports what it sees and
# touches nothing; a quartermaster issues the stores in order; a shipwright builds to a plan that is already
# complete; a navigator says whether the course was held; a mate reads the work and signs nothing off; a
# privateer attacks under letters of marque and never repairs; a shipworm bores holes on purpose to find
# out whether the hull leaks. The purpose leads so the delegate reads its job in the first word and so the
# name it had before is still the start of the name it has now. Titles are untouched: a title names the
# work, and the key now names who does it.
STAGES: tuple[Stage, ...] = (
    Stage("principles", "strong", title="Principles"),
    Stage("specify", "strong", title="Product specification"),
    # Once per feature, between the specification and whatever types the work. It is a host stage: its
    # second half is a person approving surfaces one at a time, which is not a thing to delegate.
    Stage("mockups", "strong", title="Mock-up review"),
    Stage("event-model", "strong", title="Event model"),
    # The standard profile's answer to the same question, and a rung only there: the event profile
    # renders its chart from the model with `make chart` rather than stopping for one.
    Stage("chart", "strong", title="Chart"),
    Stage("split", "strong", title="Split"),
    Stage("example-map", "strong", title="Example map"),
    # Both `/gaps` passes share this row; only the one after implementation is delegated, and it reads.
    Stage("gaps-lookout", "strong", writes=NONE, commands=READ_ONLY, title="Slice gaps"),
    Stage("release-constraint", "strong", title="Release constraint"),
    Stage("plan", "strong", title="Plan and tasks"),
    Stage("tasks-quartermaster", "fast", writes=TASKS, commands=TASK_COMMAND, title="Plan and tasks"),
    Stage("implement-shipwright", "fast", writes=MANIFEST, commands=ANY, title="Implementation"),
    Stage("converge-navigator", "strong", writes=MANIFEST, commands=ANY, title="Convergence"),
    Stage("demo", "strong", title="Demo"),
    # `writes=NONE` is the whole of it: a reviewer that can write is one that edits, and then nobody has
    # read this diff with fresh eyes after all.
    Stage("review-mate", REVIEW, writes=NONE, commands=READ_ONLY, title="Review and reshape"),
    Stage("adversary-privateer", "strong", writes=NONE, commands=READ_ONLY, title="Adversary"),
    # The rung is the capability's gates since 2026-10-17 (`capability_gates.py`). Mutation is the one of them
    # with no stage of its own elsewhere, so it carries the rung; the gaps, adversary and hand delegates the
    # rung also runs take their own rows' models.
    Stage("mutation-shipworm", "fast", writes=REPORT, commands=ANY, title="Capability gates"),
    # The rung that ends a slice. It is nobody's delegate: rule 10 of the plan holds the merge to a person
    # until a captain enforces the boundaries, and a fresh context has no business deciding how dark a
    # merge is. Slice 5.12 gives it the release mode to read, 5.7 the one full gate it runs.
    Stage("merge", "strong", title="Merge to main"),
    # The two `/cruise` delegates: the skipper decides a product question the ladder would have asked a person,
    # the hand runs the demo as the actor. Neither is a rung; both are stages so the table names their model and
    # the benchmark records their cost. Deciding has a role of its own so a project can put a bigger model on
    # deciding than on driving without moving every judgement stage with it.
    Stage("decide-skipper", DECIDE, writes=NONE, commands=READ_ONLY),
    Stage("demo-hand", "strong", writes=REPORT, commands=ANY),
    # The bosun gets a blocked run moving — a stub behind a port, a narrower reading, a repaired checkout — so
    # it writes the files its brief names, on the skipper's role: unblocking is judgement, not typing.
    Stage("unblock-bosun", DECIDE, writes=MANIFEST, commands=ANY),
)
def rungs() -> tuple[Stage, ...]:
    """The stages that are rungs of the ladder, in ladder order. `/cruise`'s three delegates are not."""
    return tuple(stage for stage in STAGES if stage.rung)


def rung_titles() -> dict[str, str]:
    """Each rung stage's key against the heading it carries, for a page that must not invent one."""
    return {stage.key: stage.title for stage in rungs()}


DEFAULT_ROLE = "strong"
HOST = "host"
# The one identifier verified today: an alias the Agent tool's `model` parameter takes (its schema, 2026-09-09).
FAST_SEEDED = {"claude": "sonnet"}


def switchable_harnesses() -> list[dict]:
    """Every registry row that records how a sub-task gets its model, in registry order."""
    harnesses = json.loads(REGISTRY.read_text(encoding="utf-8"))["harnesses"]
    return [entry for entry in harnesses if isinstance(entry.get("subagentModel"), dict)]


def stage_models() -> str:
    table = {
        "_comment": (
            "Which model runs each stage of /sail's ladder, by role. `stages` is keyed by the command each "
            "stage runs, with a `default` row for the rest; `roles` maps each role to an identifier per harness "
            "— `host` is the model running /sail itself, null is no identifier mapped yet. Edit the roles for "
            "your harness, by hand or with `python3 scripts/agents/models.py --set claude.fast=haiku`, at any time: "
            "/sail reads this before every stage. `make models` shows what results, `make check-agents` checks the "
            "shape. A harness with no row here cannot choose a model for a sub-task (scripts/agents/registry.json, "
            "`subagentModel`) and runs every stage on the host model. docs/agent-harnesses.md says more."
        ),
        "stages": {"default": DEFAULT_ROLE, **{stage.key: stage.role for stage in STAGES}},
        "roles": {
            entry["key"]: {"strong": HOST, "fast": FAST_SEEDED.get(entry["key"]), DECIDE: HOST,
                           REVIEW: HOST}
            for entry in switchable_harnesses()
        },
    }
    return json.dumps(table, indent=2, ensure_ascii=False) + "\n"
