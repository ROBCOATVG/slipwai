"""Where a project stands: the stages from a product requirements document to accepted work, read off the tree.

`next_steps` answers "where was I" for an adoption by deriving the plan from the marks each step leaves. This
is the same reading for the whole voyage of a generated project — the PRD, `./init`, the constitution, the
specification, the event model, the chart and the split, the slices, the acceptance — because the board is
asked "what step are we on" more often than any other question, and the answer must never be a status
field somebody typed. Every state here is a file that exists, a marker that is gone, or a line a log holds.

**Working is the one state the tree cannot tell on its own**, so it comes from the two things the board
already knows: its own child (`./init`, `make draft`, `make launch`, which `init_run` says the step of) and
the fleet's fold. Waiting on you is the fourth state, loud on purpose: it is the only one that asks for a
person.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .next_steps import template_gone

#: In order. A stage that this profile has not got is kept and drawn faint, so both profiles read one strip.
STATES = ("done", "working", "waiting", "todo", "skipped")
#: The profile whose stage 5 is a modelling conversation rather than nothing.
EVENT_PROFILE = "event-modelling"


@dataclass(frozen=True)
class Stage:
    """One stage of the voyage: what it is called, where it stands, what proves it and what moves it."""

    key: str
    title: str
    state: str
    evidence: str
    next: str
    detail: str = ""


def profile_of(root: Path) -> str:
    """The project's profile, from `project.json`; `standard` where nothing says."""
    try:
        return str(json.loads((root / "project.json").read_text(encoding="utf-8")).get("profile") or "standard")
    except (OSError, ValueError, AttributeError):
        return "standard"


def harness_of(root: Path) -> str:
    """Which coding agent `./init` installed Spec Kit for, or empty where it has not run."""
    try:
        state = json.loads((root / ".specify/integration.json").read_text(encoding="utf-8"))
        keys = state.get("installed_integrations") or [state.get("default_integration")]
        return ", ".join(str(key) for key in keys if key)
    except (OSError, ValueError, AttributeError):
        return ""


def specifications(root: Path) -> list[Path]:
    specs = root / "specs"
    return sorted(specs.glob("*/spec.md")) if specs.is_dir() else []


def modelled(root: Path) -> bool:
    """Whether `model.yaml` names at least one slice. Read as text, deliberately: the keel reads no YAML, and
    the one fact this needs is whether the `slices:` key is followed by anything but an empty list."""
    page = root / "docs/event-model/model.yaml"
    if not page.is_file():
        return False
    lines = [line for line in page.read_text(encoding="utf-8", errors="replace").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    for index, line in enumerate(lines):
        if line.startswith("slices:"):
            rest = line.partition(":")[2].strip()
            if rest:
                return rest not in ("[]", "{}", "null", "~")
            return index + 1 < len(lines) and lines[index + 1].startswith((" ", "-"))
    return False


def charts(root: Path) -> list[Path]:
    specs = root / "specs"
    return sorted(specs.glob("*/chart.yaml")) if specs.is_dir() else []


def step_state(receipt: dict | None, step: str) -> str:
    """What the board's own child says about a stage it runs: working while that step runs, waiting where
    it ended badly, and nothing to say otherwise."""
    if not receipt or receipt.get("step") != step:
        return ""
    if not receipt.get("done"):
        return "working"
    return "waiting" if receipt.get("code") else ""


def stages(root: Path, receipt: dict | None = None, fleet: dict | None = None,
           slices: dict[str, int] | None = None) -> list[Stage]:
    """Every stage with its state, in order. `receipt` is `init_run`'s (with the step it is on), `fleet`
    the board's fold, `slices` the count of slices per state from `voyage.folded`."""
    fleet = fleet or {}
    counts = slices or {}
    event = profile_of(root) == EVENT_PROFILE
    harness = harness_of(root)
    specs = specifications(root)
    drawn = charts(root)
    found: list[Stage] = []

    prd = root / "docs/prd.md"
    found.append(Stage("prd", "PRD", "done" if prd.is_file() else "skipped", "docs/prd.md",
                       "slipwai generate --prd <file>",
                       f"{prd.stat().st_size:,} bytes" if prd.is_file() else "started without one"))

    init = step_state(receipt, "init") or ("done" if harness else "todo")
    found.append(Stage("init", "Init", init, ".specify/integration.json", "./init --integration <agent>",
                       f"Spec Kit, {harness}" if harness else "installs Spec Kit for the agent"))

    drafting = step_state(receipt, "draft")
    ratified = template_gone(root)
    found.append(Stage("constitution", "Constitution", drafting or ("done" if ratified else "todo"),
                       ".specify/memory/constitution.md",
                       "make draft, or /speckit-constitution in the agent",
                       "ratified" if ratified else "the template's markers still stand"))
    found.append(Stage("specification", "Specification", drafting or ("done" if specs else "todo"),
                       specs[0].relative_to(root).as_posix() if specs else "specs/<feature>/spec.md",
                       "make draft from docs/prd.md, or /speckit-specify in the agent",
                       f"{len(specs)} feature(s)" if specs else "nothing to build from yet"))

    if event:
        has_model = modelled(root)
        found.append(Stage("model", "Event model", "done" if has_model else "todo", "docs/event-model/model.yaml",
                           "the event-modeling skill in the agent, then make check-model",
                           "modelled" if has_model else "a modelling conversation, with a person"))
    else:
        found.append(Stage("model", "Event model", "skipped", "docs/event-model/model.yaml", "",
                           "not on this profile"))

    launching = step_state(receipt, "launch")
    split = bool(counts)
    found.append(Stage("chart", "Chart & split", launching or ("done" if split else "todo"),
                       drawn[0].relative_to(root).as_posix() if drawn else "specs/<feature>/chart.yaml",
                       "make launch (the board's Continue the build)",
                       f"{sum(counts.values())} slice(s) charted" if split else
                       "charted, not split" if drawn else "fairways, marks and slices"))

    berths = fleet.get("berths") or []
    inbox = fleet.get("inbox") or []
    cruising = step_state(receipt, "cruise")
    working = any(row.get("state") == "running" for row in berths) or counts.get("working", 0) > 0
    waiting = bool(inbox) or counts.get("waiting", 0) > 0
    all_done = split and counts.get("done", 0) == sum(counts.values())
    # Split, not done, nothing running: the one silence the tree cannot explain, said as a wait on a person.
    becalmed = split and not all_done and not working and not fleet.get("running") and not cruising
    found.append(Stage("slices", "Slices", cruising or ("waiting" if waiting or becalmed else "working" if working
                       else "done" if all_done else "todo"), "deck logs",
                       "make cruise; make cruise-tell answers a park",
                       "the fleet is not running: cast off" if becalmed and not waiting else
                       f"{counts.get('done', 0)} of {sum(counts.values())} merged" if split
                       else "the fleet, under /cruise"))

    demos = fleet.get("demo_due") or []
    accepted = fleet.get("accepted") or []
    found.append(Stage("accepted", "Accepted", "working" if demos else "done" if all_done and accepted else "todo",
                       "accepted lines", "the demo, as the actor; /cruise-tell records the verdict",
                       f"{len(accepted)} capability(ies) accepted" if accepted else "every capability demoed"))
    return found


def current(found: list[Stage]) -> Stage | None:
    """The stage a person is on: the first that is working or waiting, else the first still to do."""
    return (next((one for one in found if one.state in ("working", "waiting")), None)
            or next((one for one in found if one.state == "todo"), None))
