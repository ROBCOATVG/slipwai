"""The rest of what a run is set to, read off the project and changed from the board.

`wheel` does this for `.specify/cruise.json`, which is who answers at each stop. Two more files decide how
a run goes and neither had anywhere to be seen: `.specify/sail.json`, how much one implementation delegate
is handed and how many tests a cycle opens with (`/sail-settings`), and `.specify/models.json`, which role
each stage of the ladder runs under (`/model-delegation-settings`). Both were a command typed in an agent,
in a project, by somebody who had the board open in front of them.

**Written by the project's own script, never by this** — the rule `wheel` opens with and the reason it is
worth repeating: `scripts/agents/sail.py --set <key>=<value>` and `scripts/agents/models.py --set
<stage>=<role>` are what the settings commands run, each validates against the same tables this renders
from, and `make check-agents` holds both files' shape. A second writer here would be the first to drift.

**What a role may be is read from the project, not from a list here.** `models.py` accepts any role name
and adds it unmapped under every harness, so the roles worth offering are the ones this project has
actually mapped — `roles.<harness>` in its own file, and the roles its stages already name.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .project.sail_settings import CONFIG as SAIL_CONFIG
from .project.sail_settings import CYCLES, DELEGATES
from .project.sail_settings import SCRIPT as SAIL_SCRIPT
from .project.stage_models import STAGES
from .shell_environment import login_environment
from .wheel import PATIENCE

MODELS_CONFIG = ".specify/models.json"
MODELS_SCRIPT = "scripts/agents/models.py"
#: Where a role falls back to when no row names the stage, and the row that sets it.
DEFAULT = "default"


@dataclass(frozen=True)
class Dial:
    """One setting: the key its script takes, what it is in plain words, and what each value means."""

    key: str
    title: str
    says: dict[str, str]


@dataclass(frozen=True)
class Panel:
    """One settings file: what to call it, where it is, what writes it, and the note under its dials."""

    name: str
    title: str
    config: str
    script: str
    under: str
    note: str


SAIL = Panel("sail", "How /sail delegates", SAIL_CONFIG, SAIL_SCRIPT, "",
             "How much one implementation delegate is handed, and how many failing tests one "
             "RED-GREEN-REFACTOR cycle opens with. Read before every implementation stage, so a change "
             "here applies to the next one rather than to the one running.")
MODELS = Panel("models", "Which model runs what", MODELS_CONFIG, MODELS_SCRIPT, "stages",
               "Each stage of the ladder runs under a role, and the role is mapped to an identifier per "
               "harness. Changing a stage's role changes which model does that work; a role this project "
               "has not mapped for your harness falls through to the harness's own default.")
PANELS = (SAIL, MODELS)

SAIL_DIALS = (
    Dial("delegate", "What one delegate is handed",
         {"story": "every rule of one user story, in one context", "rule": "one rule with its examples",
          "task": "one task, as the tasks stage cut it"}),
    Dial("cycle", "What one RED cycle opens with",
         {"rule": "a rule's examples together", "example": "one example at a time"}),
)
SAIL_VALUES = {"delegate": DELEGATES, "cycle": CYCLES}


def held(root: Path, panel: Panel) -> dict[str, str]:
    """What that file says, or `{}` where the project has none.

    `{}` and not a refusal, for `wheel`'s reason: a project generated before the file existed, an adopted
    repository, and a harbour that is not a project at all all reach this, and none of them is a fault.
    """
    try:
        found = json.loads((root / panel.config).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if panel.under:
        found = found.get(panel.under) if isinstance(found, dict) else None
    if not isinstance(found, dict):
        return {}
    return {str(a): str(b) for a, b in found.items() if not str(a).startswith("_")}


def roles(root: Path) -> tuple[str, ...]:
    """The roles worth offering for a stage: the ones this project has mapped for a harness, plus the ones
    its own stages already name. From the project rather than a list here, because `models.py` takes any
    name and a board offering one the project has not mapped would be offering a fall-through."""
    found: set[str] = {one.role for one in STAGES}
    try:
        table = json.loads((root / MODELS_CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        table = {}
    mapped = table.get("roles") if isinstance(table, dict) else None
    for one in (mapped or {}).values():
        if isinstance(one, dict):
            found.update(str(key) for key in one)
    found.update(held(root, MODELS).values())
    return tuple(sorted(found))


def dials(root: Path, panel: Panel) -> tuple[tuple[Dial, tuple[str, ...]], ...]:
    """That panel's settings and the values each takes. The models panel is one dial per stage of the
    ladder, in the order the ladder runs them, with the fall-through row first."""
    if panel is SAIL:
        return tuple((one, SAIL_VALUES[one.key]) for one in SAIL_DIALS)
    known = roles(root)
    rows = [(Dial(DEFAULT, "Any stage with no row of its own", {}), known)]
    rows += [(Dial(one.key, one.title, {}), known) for one in STAGES]
    return tuple(rows)


def set_dial(root: Path, name: str, key: str, value: str) -> str:
    """One setting changed, through the project's own script, or why it could not be.

    Checked here only for what the script cannot be asked: that this board draws the panel, the key and the
    value, and that the project has a script to run. Whether the value is legal and what the file ends up
    holding are the script's, which is the point of running it rather than writing the file.
    """
    panel = next((one for one in PANELS if one.name == name), None)
    if panel is None:
        raise ValueError(f"`{name}` is not a settings file this board sets")
    known = {one.key: values for one, values in dials(root, panel)}
    if key not in known:
        raise ValueError(f"`{key}` is not a setting in {panel.config}")
    if value not in known[key]:
        raise ValueError(f"`{value}` is not one of {key}'s values: {', '.join(known[key])}")
    script = root / panel.script
    if not script.is_file():
        raise ValueError(f"{panel.script} is not in this project, so there is nothing to write the "
                         f"setting. It arrives with `./init`")
    done = subprocess.run([sys.executable, str(script), "--set", f"{key}={value}"],  # noqa: S603 — the
                          cwd=root, capture_output=True, text=True,                  # project's own script
                          timeout=PATIENCE, env=login_environment(), check=False)
    if done.returncode:
        raise ValueError((done.stderr or done.stdout or f"{panel.script} exited {done.returncode}").strip())
    return (done.stdout or f"{key} = {value}").strip()
