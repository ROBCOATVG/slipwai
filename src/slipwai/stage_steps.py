"""The stages with more in them than one prompt, over the Agent Client Protocol from the board.

The model, triage and launch are each a script in the toolkit — `scripts/agents/model.py`, `triage.py`,
`launch.py` — that gates, runs one headless session, and checks what it left; launch then enables `/cruise`
and casts off. Over the protocol the session is the board's own (`stage_session.py`), and the rest is done
here in the words the scripts use, so the receipt reads the same either way: the model's prompt is asked of
the project's script rather than copied, triage is given the numbers nobody has routed, and a launch that
charted and split goes on to the two processes that cast off. A project whose agent has no launch row, and
every one of these from a terminal, runs the script as it did.
"""
from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from . import stage_session
from .feedback import items, untriaged
from .init_run import (
    CRUISE,
    CRUISING,
    LAUNCH,
    LAUNCHING,
    MODEL,
    MODELLING,
    TRIAGE,
    TRIAGING,
    Fitting,
    Step,
    began_model,
    launched,
    stage_step,
    triaged,
)
from .passage import modelled, split
from .shell_environment import login_environment

MODELLING_ACP = ("Modelling — the project's agent over the Agent Client Protocol, from this board: the event "
                 "model from the approved storyboard, with what it reads and writes shown as it goes. The "
                 "context question is yours where only you can answer it; it asks here. It stops at the model.")
TRIAGING_ACP = ("Reading your feedback — the project's agent over the Agent Client Protocol, from this board: it "
                "proposes where each thing you said goes, and asks here where it cannot tell. It changes "
                "nothing; each proposal waits for you on the Feedback card.")
LAUNCHING_ACP = ("Continuing the build — the project's agent over the Agent Client Protocol, from this board: "
                 "the chart and the split, asking here where only you can decide; then /cruise enabled and the "
                 "fleet cast off. The streams on this board are the fleet; a captain that parks is waiting on you.")
ENABLING = "Enabling /cruise."
#: The model script's prompt was written for a session with nobody to ask; over the protocol somebody is here.
NOBODY = "Proceed on your best-evidenced proposal; nobody is here to ask."
#: What the model script says instead of modelling when asked, which is how the keel gets its words without
#: a copy that would drift from them.
PROMPT_FLAG = "--prompt"


def knows(script: Path, flag: str) -> bool:
    """Whether the project's script takes the flag — read off its text, never by running it. A script written
    before the flag ignores its arguments and runs its stage: asked for its prompt, it would start the very
    session the board was about to start, under a timeout that then killed it."""
    try:
        return flag in script.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def model_prompt(where: Path) -> str:
    """The model's prompt, from the project's own script; empty where the script has no `--prompt`, which
    leaves the stage to the headless child that script is."""
    if not knows(where / "scripts/agents/model.py", PROMPT_FLAG):
        return ""
    try:
        said = subprocess.run(["python3", "scripts/agents/model.py", PROMPT_FLAG], cwd=where, capture_output=True,
                              text=True, env=login_environment(), timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return said.stdout.strip().replace(NOBODY, "").strip() if said.returncode == 0 else ""


def model_step(where: Path) -> Step:
    """The model from an approved storyboard: what approving one starts on an event-modelling project."""
    def unmodelled() -> str:
        return "" if modelled(where) else ("The session ended without a slice in docs/event-model/model.yaml; its "
                                           "lines above say where it stopped. Model again tries once more.")
    return stage_step(where, "model", "", MODEL, MODELLING, MODELLING_ACP, began_model, "model",
                      prompt=lambda: model_prompt(where), after=unmodelled, pid="model-next.pid",
                      done="The model is under docs/event-model/. Continue the build charts it once a slice is "
                           "named there.",
                      undone="The model stopped short; its lines above say where. Model again tries once more.")


def unproposed(where: Path, numbers: list[str]) -> Callable[[], str]:
    """What triage left: the records it was given that came back with no route proposed."""
    def left() -> str:
        found = {one.number: one for one in items(where)}
        short = [number for number in numbers if number not in found or found[number].state != "proposed"]
        return (f"The session ended with {', '.join(short)} not proposed; Triage on the Feedback card tries again."
                if short else "")
    return left


def triage_step(where: Path) -> Step:
    """Where each piece of feedback nobody has routed should go: what Send on the board starts. With nothing
    waiting the child says so and ends, as it always did."""
    numbers = sorted(one.number for one in untriaged(where))
    if not numbers:
        return Step(TRIAGE, TRIAGING, triaged, "triage")
    return stage_step(where, "triage", ",".join(numbers), TRIAGE, TRIAGING, TRIAGING_ACP, triaged, "triage",
                      after=unproposed(where, numbers),
                      done="Triage is done. Each proposal is on the Feedback card, waiting for you to confirm it.",
                      undone="Triage stopped short; its lines above say where. Triage on the Feedback card tries "
                             "again.")


def charted(code: int) -> str:
    return "Charted and split." if code == 0 else "The chart and the split did not finish; nothing was cast off."


def enabled(code: int) -> str:
    return "" if code == 0 else f"Enabling /cruise exited {code}; nothing was cast off. Its last lines say why."


def cast(code: int) -> str:
    if code == 0:
        return "The build is continued: the fleet is cast off. The streams on this board are the fleet."
    return f"`make cruise` exited {code}; nothing was cast off. Its last lines say why."


def launch_steps(where: Path) -> list[Step]:
    """The build continued: the chart and the split over the protocol where they are not done, then `/cruise`
    enabled and the fleet cast off as the script does them — or the script itself, where the board has no
    agent to launch."""
    if stage_session.launchable(where) is None:
        return [Step(LAUNCH, LAUNCHING, launched, "launch")]
    steps: list[Step] = []
    if not split(where):
        def unsplit() -> str:
            return "" if split(where) else ("The session ended without a split, so there is nothing to light a "
                                            "captain for; a park in its lines names what you have to decide.")
        steps.append(stage_step(where, "launch", "", LAUNCH, LAUNCHING, LAUNCHING_ACP, charted, "launch",
                                after=unsplit))
    steps.append(Step(["python3", "scripts/agents/cruise.py", "--set", "enabled=true"], ENABLING, enabled, "launch"))
    steps.append(Step(CRUISE, CRUISING, cast, "launch"))
    return steps


def begin_model(where: Path, said: list[str] | None = None) -> Fitting:
    """The model begun, in the background: what approving a storyboard starts on an event-modelling project."""
    fitting = Fitting(where, [model_step(where)], said)
    fitting.thread.start()
    return fitting


def triage(where: Path, said: list[str] | None = None) -> Fitting:
    """The feedback nobody has proposed a route for, read in the background: what Send on the board starts."""
    fitting = Fitting(where, [triage_step(where)], said)
    fitting.thread.start()
    return fitting


def launch(where: Path, said: list[str] | None = None) -> Fitting:
    """The build continued, in the background: what the board's button starts, carrying the receipt so far."""
    fitting = Fitting(where, launch_steps(where), said)
    fitting.thread.start()
    return fitting
