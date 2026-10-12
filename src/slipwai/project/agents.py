"""`agents/`: one named agent type per stage `/sail` sends to a fresh context.

Every delegation the toolkit made was an anonymous general-purpose agent handed a prose brief, and the write
scope was a sentence inside it — "remain read-only", "may edit only the files its task requires". Nothing but
the delegate's reading of that sentence kept an adversary from patching what it found, which is the
anti-pattern `skills/adversarial-testing/SKILL.md` lists first. Five of the six harnesses that can give a
sub-task its own model can only do it through a file, and the same file is where that harness says what the
delegate may touch. So the constraint belongs in the file, where the harness enforces it, and the per-call
brief is left carrying only what is actually per-call: the task, the contract and the manifest.

These are the canonical types, one per delegable stage in `stage_models.STAGES`, named for the stage so the
model resolves through `.specify/models.json` with no second lookup and `/model-delegation-settings` stays the only place a
model is chosen. `scripts/agents/project.py` renders each into the installed harness's own agent file —
Codex's sandbox mode, Cursor's `readonly`, Copilot's and Gemini's tool lists, opencode's permissions, Claude
Code's `disallowedTools` — resolving the model at projection time, and says in the stamp where a harness
could not express a declaration rather than letting the gap pass for enforcement.

What this module holds is the projection and nothing else. The words of each standing brief are assets under
`assets/toolkit/agents/`, read by `briefs.py`: prose a person edits belongs where the skills and the commands
are, and a module that carried eleven briefs had to be split at a paragraph boundary to stay inside its
budget. The scope does not follow them. `name`, `stage`, `writes` and `commands` are generated here from the
stage table, because they are what a harness is held to, and a brief that wrote its own would be a second
answer the projection could pick up instead.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..layout import AT_ROOT, Layout
from .briefs import brief
from .stage_models import AGENT, ANY, MANIFEST, NO_STAGE, REPORT, STAGES

# Where the canonical types live, beside `skills/` and `commands/`.
DIRECTORY = "agents"
# What every type's body says before its own part: the standing constraints are one page, and a type is not
# the place to restate them either.
SAFETY = "docs/delegated-agent-safety.md"


@dataclass(frozen=True)
class Type:
    """One canonical type: its name, the ladder stage whose model it takes, and the scope it declares."""

    name: str
    stage: str
    writes: str
    commands: str


#: The two roles that *run* the loop rather than being delegated inside one, as `GLOSSARY.md` defines them:
#: the captain, one per fairway, and the harbourmaster, one per harbour. They carry no stage's model for the
#: same reason the slice delegate does not — a captain resolves each stage's model inside itself, and a
#: harbourmaster runs no stage at all.
#:
#: They are types rather than loose prose because every other way of shipping a persona is worse. A file
#: under `assets/toolkit/agents/` that is nobody's type is copied into a project raw and written over by
#: nothing; a persona in a command is a persona only that command has; and a persona in a Python programme
#: is the thing phase 12 exists to stop needing. As types they get the frontmatter a harness enforces,
#: they are projected into every harness's own location by the one projection, and they travel with the
#: plugin — so a session that has the material has the two roles that know what to do with it.
RUNS_THE_LOOP = (("drive-captain", MANIFEST, ANY), ("harbour-harbourmaster", REPORT, ANY))


def types() -> list[Type]:
    """Every type a project carries: one per delegated stage, the one that carries a whole slice, and the
    two that run the loop the rest of them are delegated inside.

    The six stage types are named for their stage, so the model is that stage's row and there is no second
    lookup. The seventh is `/sail`'s slice delegate, which runs one slice's whole ladder in a worktree of
    its own and resolves each stage's model inside itself — so it takes no stage's model, and inherits.
    """
    named = [
        Type(stage.agent, stage.key, writes, commands)
        for stage in STAGES
        for writes, commands in [(stage.writes, stage.commands)]
        if writes is not None and commands is not None
    ]
    running = [Type(name, NO_STAGE, writes, commands) for name, writes, commands in RUNS_THE_LOOP]
    return [*named, Type(f"{AGENT}slice-watch", NO_STAGE, MANIFEST, ANY), *running]


def agent_file(agent: Type, layout: Layout) -> str:
    """One canonical type: neutral frontmatter no harness owns, then the standing brief."""
    standing = brief(agent.name, layout)
    return f"""---
name: {agent.name}
description: {standing.summary}
stage: {agent.stage}
writes: {agent.writes}
commands: {agent.commands}
---

# {agent.name}

{standing.body}

## What holds for every delegate here

Read [{SAFETY}]({SAFETY}) before you touch anything: it carries the
constraints that hold for every delegated agent in this repository — preserving the checkout, leaving
long-lived processes alone, never sending a state-changing request to a running application, never altering
branches, commits, tags, remotes or credentials. This file is the standing part of your brief and that page
is the standing part of this file; the per-call brief adds only the task, its contract and the file manifest.

Where this project has adopted a code index, a question about a symbol — what calls it, where it is used, what
a change would break — goes to the index first, by whichever route its own block in `AGENTS.md` names: a command
through the shell, which works in every session, or a tool where yours lists it. Name the route that answered.
Text search is for words in documents — `spec.md`, `decisions.md`, the PRD, `model.yaml`, a test's string — and
finding a file by name is a `find`, not a question for the index. An index that ships a guard refuses a symbol
search of the source until you have asked it, and a run's log counts which delegate did.

`writes: {agent.writes}` and `commands: {agent.commands}` above are the scope, and the projection of this file
into your harness enforces as much of it as that harness can express — the stamp on the projection says what
it could not. Where the harness could not, the words still bind: treat the scope literally, and stop and
report rather than reaching past it. A delegate that meets a product decision, or needs a file its manifest
does not name, hands the question back to the session that delegated it. It does not choose, and it does not
search outward for permission.
"""


def agent_files(layout: Layout = AT_ROOT) -> dict[str, str]:
    """`agents/`: one file per type, keyed by its path in the project."""
    return {f"{DIRECTORY}/{agent.name}.md": agent_file(agent, layout) for agent in types()}
