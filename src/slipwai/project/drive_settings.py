"""How `/drive` hands implementation to `drive-implement`, on two axes a project sets once and changes at will.

The **boundary** is how much one delegate is handed: every rule of one user story, one rule, or one task. The
**cycle** is how many RED tests a RED-GREEN-REFACTOR cycle opens with: a rule's examples together, or one at
a time. Both came from one downstream project's measurement of its own `/drive`: twenty-three fresh implement
delegates on one slice each spent 1.5–2.5 minutes re-reading the same plan, map, precedent and test file,
because the boundary was the task; and ten of that slice's tasks were proofs with nothing to turn green,
because the cycle was one test and a rule had been cut up to fit it. The story boundary answers the first
without touching the increment; the rule cycle answers the second and is what Principle V now allows.

The settings live in `.specify/drive.json`, beside `models.json`, for the same reasons that table does: read
before every implementation stage, changed only through a checked command (`/drive-settings` over
`scripts/agents/drive.py`), held to its shape by `make check-agents`, versioned with the project and merged
forward by `slipwai migrate`. A story is never offered as a cycle unit: every rule of a story red before any
is implemented is the batch Principle V prohibits, and the script refuses it.
"""
from __future__ import annotations

import json

from ..layout import AT_ROOT, Layout

CONFIG = ".specify/drive.json"
SCRIPT = "scripts/agents/drive.py"
# How much one implementation delegate is handed, and how many RED tests one cycle opens with.
DELEGATES = ("story", "rule", "task")
CYCLES = ("rule", "example")
DEFAULT_DELEGATE, DEFAULT_CYCLE = "story", "rule"
COMMENT = (
    "How /drive hands implementation to drive-implement. `delegate`: story | rule | task — how much one delegate "
    "is handed. `cycle`: rule | example — how many RED tests a RED-GREEN-REFACTOR cycle opens with. Change it with "
    "/drive-settings (python3 scripts/agents/drive.py --set delegate=… cycle=…), checked; `make check-agents` "
    "holds the shape. commands/drive.md, *How implementation is delegated*, says what each value means and which "
    "veto overrides it."
)


def drive_config() -> str:
    """`.specify/drive.json` as generated: the defaults, and the comment that says where they are explained."""
    return json.dumps({"_comment": COMMENT, "delegate": DEFAULT_DELEGATE, "cycle": DEFAULT_CYCLE}, indent=2,
                      ensure_ascii=False) + "\n"


def implementation_section(layout: Layout = AT_ROOT) -> str:
    """The `/drive` section after *What each stage costs*: the two axes, the vetoes, parallelism, and the record."""
    return f"""### How implementation is delegated

Two settings in `{CONFIG}` decide how this ladder hands implementation to `drive-implement` and how each
delegate drives what it is handed. Read them before every implementation stage — `python3 {SCRIPT}` — say
both in the stage line beside the model (`drive-implement · model: sonnet · delegated, fresh context ·
story/rule`), and change them only through `/drive-settings`, never silently inside a delegation.

**`delegate`** — how much one delegate is handed. `story`: every rule of one user story (`[US<n>]` on the
tasks), each rule its own cycle in one context — the boundary that stops each fresh delegate re-reading the
same plan, map, precedent and test file per rule, which was most of a slice's implementation wall where it
was measured. `rule`: one rule with its examples. `task`: one task as the tasks stage cut it — the finest
boundary, and the most independent checking of what this session asserted. Whatever the boundary, the
delegate may fan its work out to sub-delegates over disjoint files under the constraints its brief carries,
and a sub-delegate is handed whole cycles, never part of one.

**`cycle`** — how many RED tests a RED-GREEN-REFACTOR cycle opens with. `rule`: a rule's examples written
together, each observed failing for its own stated reason, stub-first so none fails on a build, then the
smallest code that passes them. `example`: one at a time. There is always a cycle; what this setting loosens
is one test per cycle. A story is never a cycle unit: every rule of a story red before any is implemented is
the batch Principle V prohibits, and `{SCRIPT}` refuses it.

The defaults are `{DEFAULT_DELEGATE}` and `{DEFAULT_CYCLE}`. Two vetoes override them, written as vetoes
because a preference is what the next edit simplifies away: tasks that carry no story tag are delegated per
`rule`, and a map that does not number its rules is delegated per `task` and driven per `example`, since
there is no agreed rule boundary to cut on. `example` is also the right per-slice choice for a rule where one
assertion at a time is worth the cycles — money, authorisation, anything the constitution names as a MUST —
and saying so in that slice's delegation brief is allowed; changing the default is `/drive-settings`.

**Parallelism is this session's duty at every boundary.** Siblings whose manifests are disjoint — stories,
rules or tasks — run concurrently in the same turn, derived from the manifests rather than from a `[P]`
marker alone (*Who runs each stage*), and a delegate fans out inside its boundary the same way. What is never
parallel is one cycle: a RED-GREEN-REFACTOR increment starts from a green, committed suite.

The delegate reports the boundary it was given, the cycle unit it ran, and whether it fanned out and into how
many groups; this session passes them to the record as `delegate=`, `cycle=` and `split=N` on the implement
entry, so a wall time says what it was a wall time of. `{layout.make} benchmark` shows them beside each slice.
"""


def drive_settings_command(layout: Layout = AT_ROOT) -> str:
    """`/drive-settings`: the two settings shown, or changed through the checked `--set`."""
    return f"""---
description: Show or change how /drive delegates implementation — the boundary a delegate is handed and the cycle it runs
argument-hint: [delegate=story|rule|task] [cycle=rule|example]
---

# Drive settings

`{CONFIG}` holds two settings: `delegate`, how much one `drive-implement` delegate is handed — every rule of one
user story, one rule, or one task — and `cycle`, how many RED tests one RED-GREEN-REFACTOR cycle opens with — a
rule's examples together, or one at a time. `commands/drive.md`, *How implementation is delegated*, says what
each means and which veto overrides it. This command is how the settings are read and how they change: checked,
at any time, and never by quietly handing a delegate something else.

## No argument — show the settings

```sh
python3 {SCRIPT}
```

Report both lines as printed — the value, what it means, and the veto that can override it on a slice.

## Arguments — change them

```sh
python3 {SCRIPT} --set $ARGUMENTS
```

Each argument is `delegate=story|rule|task` or `cycle=rule|example`, and both may be given at once. The script
refuses a value it does not know and refuses `cycle=story` with the reason — it is the batch Principle V
prohibits — and writes nothing then. Report a refusal in its words; do not work around it by editing the file.
Then commit `{CONFIG}` on its own, with a message naming the change: the choice is versioned with the project,
and it takes effect at the next implementation stage `/drive` runs. Nothing already running is interrupted.

## When the request is in words

"One delegate per task" is `delegate=task`; "one test at a time" is `cycle=example`; "back to the defaults" is
`delegate=story cycle=rule`. A request for one rule at a time is `delegate=rule`, and where the map is
rule-owned it hands the same thing as `task`. A request to batch a whole story's tests before implementing is
the one thing this cannot do — say why, and offer `cycle=rule`. `{layout.make} check-agents` holds the file's
shape whether it was edited by hand or through this command.
"""
