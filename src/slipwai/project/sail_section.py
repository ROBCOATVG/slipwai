"""The table of delegable types, and the command that changes which model runs each stage.

Split from `stage_models.py`, which holds the table itself: that module is a declaration — one row per
stage, its role and what a delegate of it may touch — and this one is what a project reads off it.

What is left here is only the part that is not prose. The section of `commands/sail.md` that applies the
table is the asset's own words now (`assets/toolkit/commands/sail.md`, *Who runs each stage*), and so is
`/model-delegation-settings`; the table of types below is not, because every scope, type name and stage in
it is rendered from `STAGES`, so a stage that changes what its delegate may do changes both pages and
cannot fail to. `docs/generated-prose.md` is the rule that draws that line.
"""
from __future__ import annotations

from ..assets import TOOLKIT_ROOT
from ..layout import AT_ROOT, Layout
from .prose import page
from .stage_models import (
    ANY,
    MANIFEST,
    NONE,
    READ_ONLY,
    REPORT,
    STAGES,
    TASK_COMMAND,
    TASKS,
)

# Where the page lives: beside the three a project has always received verbatim.
COMMANDS = TOOLKIT_ROOT / "commands"

# What each type may write and run, said in the sail section the way `agents/` declares it, so the ladder and
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
    """The table of types in the sail section: one row per delegable stage, from the declaration itself."""
    rows = "\n".join(
        f"| `{stage.key}` | `{stage.agent}` | {SCOPE[writes]} | {SCOPE[commands]} |"
        for stage in STAGES
        for writes, commands in [(stage.writes, stage.commands)]
        if writes is not None and commands is not None
    )
    return f"""| Stage | Type | Writes | Runs |
|---|---|---|---|
{rows}"""


def stage_keys() -> str:
    """Every stage key, in ladder order, for a page that must not keep its own list of them."""
    return ", ".join(f"`{stage.key}`" for stage in STAGES)


def values(layout: Layout = AT_ROOT) -> dict[str, str]:
    """What `model-delegation-settings.md` may name: the stage keys, from the ladder's own declaration, and
    how this project says `make`. Nothing else — every scope, type name and stage on that page is rendered
    from `STAGES`, so a stage that changes what its delegate may do changes the page and cannot fail to."""
    return {"stage-keys": stage_keys(), "make": layout.make}


def model_delegation_settings_command(layout: Layout = AT_ROOT) -> str:
    """`/model-delegation-settings`: the table shown, or changed through the checked `--set` — never by editing a delegation."""
    return page(COMMANDS, "model-delegation-settings.md", values(layout))
