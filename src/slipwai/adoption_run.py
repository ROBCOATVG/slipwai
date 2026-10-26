"""The run of adoption steps that need nobody, taken one after another once the strategy is decided.

The steps a decided strategy adds — the build floor, `smoke`, the new home, the parity list — ask a person nothing:
each is a headless session (`scripts/agents/step.py`) or a generation on the stack the ADR records. The board took
them one button at a time, and the first adoption to walk them pressed *go* five times on steps that asked nothing.
`Chain` takes each in turn and stops at the first that needs a person, or at one the tree does not show done after
its run. Which step is which is read off its action, as `next_steps` words it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from . import next_steps
from .errors import GenerationError
from .init_run import Fitting, Step
from .layout import Layout, layout_of
from .manifest import apps_from_manifest, read_manifest
from .origin import adoption_of
from .strategy_steps import CONTINUE, home_of, name_of, stack_of

#: The steps by the first word of their action in `next_steps`, which is how the voyage knows which is now.
INIT, GROUND, VERIFY, STRATEGY, CONSTITUTION, SPECIFY = (
    "init", "/ground", "/verify", "an accepted ADR", "/speckit-constitution", "/speckit-specify")
#: The new home a strangler fig grows `beside` the old code or a rewrite builds, which the board generates itself.
HOME, NEW_SYSTEM = "generate the new home", "generate the new system"
#: The hand-over to the new repository a rewrite is built in: its voyage is where the rest happens.
ELSEWHERE = CONTINUE
#: A step the strategy adds that only the agent can take — the build floor, `smoke`, the parity list — handed to a
#: headless session (`scripts/agents/step.py`): the board stopped at the first of them with nothing to press.
AGENT = "agent"
IN_THE_AGENT = ", in the agent"
STEP = "scripts/agents/step.py"


def key_of(action: str) -> str:
    """Which of the board's steps an action is, or `""` for one only the agent takes."""
    if action.endswith("/init"):
        return INIT
    found = next((key for key in (GROUND, VERIFY, STRATEGY, HOME, NEW_SYSTEM, ELSEWHERE, CONSTITUTION, SPECIFY)
                  if action.startswith(key)), "")
    return found or (AGENT if action.endswith(IN_THE_AGENT) and not action.startswith("/") else "")


def home_steps(root: Path) -> list[Step]:
    """The new home generated on the stack the strategy ADR records, and committed: `add-service` (and
    `add-frontend` where it has a browser app) beside the old code, or `generate` for a new repository."""
    document = read_manifest(root, "the board")
    adoption = adoption_of(document)
    record = (adoption.strategy if adoption else None) or {}
    strategy, lines = str(record.get("decided") or ""), record.get("lines") or {}
    place, where = home_of(strategy, lines)
    stack = stack_of(lines)
    if strategy not in ("strangler-fig", "rewrite") or place == "inside" or not stack.get("backend"):
        raise GenerationError("the strategy ADR names no new home beside the old code, or no stack for it")
    if subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True).stdout.strip():
        raise GenerationError("this repository has changes nobody has committed; commit or stash them first, so the "
                              "new home arrives as a commit of its own")
    name = name_of(where, f"{document.get('name') or root.name}-next").lower().replace("_", "-")
    slipwai = [sys.executable, "-m", "slipwai"]
    on = [f"--backend={stack['backend']}", f"--persistence={stack.get('persistence') or 'memory'}"]
    browser = stack.get("frontend") not in (None, "", "none")
    if place == "new-repo":
        target = (root / where).resolve() if where else root.parent / name
        commands = [[*slipwai, "generate", target.name, f"--output={target.parent}", *on, "--target=existing",
                     *([f"--frontend={stack['frontend']}"] if browser else []), "--no-init"]]
        where_to = str(target)
    else:
        # Each committed before the next: `add-frontend` refuses a tree with changes nobody has committed, so that
        # undoing it undoes only what it wrote.
        commands = [[*slipwai, "add-service", name, *on, "--purpose=the new home the old code's capabilities move to"],
                    ["git", "add", "-A"], ["git", "commit", "-q", "-m", f"Generate the new home: {name}"]]
        if browser:
            commands += [[*slipwai, "add-frontend", f"{name}-web", f"--frontend={stack['frontend']}", f"--api={name}"],
                         ["git", "add", "-A"],
                         ["git", "commit", "-q", "-m", f"Give the new home its browser app: {name}-web"]]
        where_to = f"apps/{name}"
    steps = [Step(argv, f"Running {' '.join(argv[2:] if argv[0] == sys.executable else argv)}", lambda code: (
        "" if code == 0 else f"It stopped ({code}); what it said is above."), "home") for argv in commands]
    steps[-1] = Step(steps[-1].argv, steps[-1].announced, lambda code: (
        f"The new home is at {where_to}, current from day one: every new feature is built there."
        if code == 0 else f"It stopped ({code}); what it said is above."), "home")
    return steps


def agent_steps(layout: Layout, now: next_steps.Step) -> list[Step]:
    """The step that is now, where only the agent can take it, handed to a headless session."""
    taken = now.action[:-len(IN_THE_AGENT)]
    return [Step([sys.executable, layout.under(STEP), taken, now.why],
                 f"Handing {taken} to a headless session — it reads the strategy's playbook, takes this step and "
                 "stops.", lambda code: "" if code == 0 else f"The session stopped ({code}); what it said is above.",
                 "agent")]


def now_of(root: Path) -> tuple[Layout, next_steps.Step | None]:
    document = read_manifest(root, "the board")
    layout, adoption = layout_of(document), adoption_of(document)
    if adoption is None:
        return layout, None
    return layout, next((step for step in next_steps.steps(root, layout, adoption, apps_from_manifest(document, True))
                         if not step.done), None)


class Chain(Fitting):
    """Every step that needs nobody, taken one after another — the build floor, `smoke`, the new home, the parity
    list — until the step that is now needs a person, or one ends without the tree saying it is done.

    One button a step was a person pressing *go* five times on steps that asked them nothing."""

    def run(self) -> None:
        tried: set[str] = set()
        first = True
        while True:
            layout, now = now_of(self.where)
            key = key_of(now.action) if now else ""
            if now is None or key not in (AGENT, HOME, NEW_SYSTEM):
                self.say(f"Next: {now.action} — that one is yours." if now else "Every step is done.", code=0)
                return
            if now.action in tried:
                self.say(f"The session ended and the tree does not show {now.action} done yet: {now.why}. Take it "
                         "in the agent, or press the button to try again.", code=1)
                return
            tried.add(now.action)
            try:
                steps = agent_steps(layout, now) if key == AGENT else home_steps(self.where)
            except GenerationError as refused:
                self.say(str(refused), code=1)
                return
            if self.run_steps(steps, final=False, announced=not first):
                return
            first = False


def chain(root: Path, said: list[str] | None = None) -> Fitting:
    """The steps that need nobody, from the one that is now, in the background."""
    layout, now = now_of(root)
    if now is None or key_of(now.action) not in (AGENT, HOME, NEW_SYSTEM):
        raise GenerationError("the step that is now needs you; read the card again")
    if key_of(now.action) == AGENT and not (root / layout.under(STEP)).is_file():
        raise GenerationError(f"{layout.under(STEP)} is not here: `slipwai adopt --refresh` writes it")
    first = agent_steps(layout, now) if key_of(now.action) == AGENT else home_steps(root)
    fitting = Chain(root, [Step([], first[0].announced, lambda code: "", "agent")], said)
    fitting.thread.start()
    return fitting
