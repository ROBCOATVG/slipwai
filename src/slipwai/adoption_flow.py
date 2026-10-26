"""The adoption's steps the board can take itself, and the control each one is on the voyage.

`adoption_card` shows the sequence `adopt --next` reads; this is what makes it move. Each step that is a command
the board can run, or a record it can write, gets the control that does it, on the step that is *now*:

- **`./init`**, where the adoption left it as the next step: the agent picked, and run in the background.
- **`/ground`** is `ground_card`'s, one row at a time — and its last answer starts the gate, because nothing is
  left to ask before it.
- **`/verify`**: the gate, run in the background, and its first baseline committed when it is green.
- **The strategy**: the five on offer with the recommendation picked, written as the accepted ADR whose
  `Strategy:` line the gate reads — *leave it* is one of them.
- **The constitution and the first specification**: a PRD the person already has, named by its path and copied
  in, or four questions answered and written as one — who it is for, what it must do, how anyone will know it
  is done, and what is fixed — and `make draft` run on it: the same session a generated project with a PRD
  gets, which drafts both and stops for the person to read the specification. One box invited one word, and a
  session asked to draft a product from "modernisation" rightly refused to.

From the first specification on, the voyage's own strip and its Continue the build are the next steps.
"""
from __future__ import annotations

import datetime
import shlex
import subprocess
from collections.abc import Mapping
from pathlib import Path

from . import resurvey
from .errors import GenerationError
from .ground_card import asked
from .init_run import Fitting, Step, adopted
from .layout import Layout, layout_of
from .manifest import read_manifest
from .next_steps import BASELINE
from .page_shell import esc
from .strategy import SAYS
from .uncommitted import refuse_foreign

#: The steps by the first word of their action in `next_steps`, which is how the voyage knows which is now.
INIT, GROUND, VERIFY, STRATEGY, CONSTITUTION, SPECIFY = (
    "init", "/ground", "/verify", "an accepted ADR", "/speckit-constitution", "/speckit-specify")
PRD = "docs/prd.md"
#: What a PRD has to say for a specification to be drafted from it rather than guessed: the name of each
#: answer, its heading in the PRD, what the box suggests, and whether the draft can go without it.
QUESTIONS = (
    ("who", "Who uses it, and what for", "Who works with it, and what they need to be able to do", True),
    ("does", "What it must do", "The behaviour that carries over, what is new, and what is dropped", True),
    ("done", "How we will know it is done", "Concrete, testable statements — the existing data included", True),
    ("fixed", "Out of scope, or already fixed", "The stack, a browser UI or none, how the old one is cut over",
     False),
)


def key_of(action: str) -> str:
    """Which of the board's steps an action is, or `""` for one only the agent takes."""
    if action.endswith("/init"):
        return INIT
    return next((key for key in (GROUND, VERIFY, STRATEGY, CONSTITUTION, SPECIFY) if action.startswith(key)), "")


def make(layout: Layout) -> list[str]:
    return shlex.split(layout.make)


def gate(root: Path, layout: Layout, said: list[str] | None = None) -> Fitting:
    """`make verify` in the background, and the baseline its first run writes committed when it is green."""
    baseline = layout.under(BASELINE)
    argv = [*make(layout), "verify"]
    steps = [
        Step(argv, f"Running {' '.join(argv)} — the gate. Its first run records the lint and typecheck findings "
                   "already here as the baseline, and only new ones fail from then on.",
             lambda code: ("The gate is green, and its baseline is recorded." if code == 0 else
                           f"The gate stopped ({code}). What it said is above; `/verify` in the agent shows the "
                           "failures, and quarantines a red suite on purpose if you tell it to."), "verify"),
        Step(["git", "add", "--", baseline], "", lambda code: "", "verify"),
        Step(["git", "commit", "-q", "-m", "Gate baseline", "--", baseline], "",
             lambda code: f"Committed {baseline}." if code == 0 else "", "verify"),
    ]
    fitting = Fitting(root, steps, said)
    fitting.thread.start()
    return fitting


def decide(root: Path, layout: Layout, answers: Mapping[str, str], today: str | None = None) -> str:
    """The strategy, written as the accepted ADR the gate reads, and committed. Returns the ADR's path."""
    strategy = str(answers.get("strategy") or "")
    if strategy not in SAYS:
        raise GenerationError(f"pick one of the five strategies: {', '.join(SAYS)}")
    why = str(answers.get("why") or "").strip() or "Decided on the board, from the map and its recommendation."
    refuse_foreign(root, resurvey.writes(root, layout), "deciding the strategy")
    folder = root / layout.under("docs/adr")
    folder.mkdir(parents=True, exist_ok=True)
    taken = [int(path.name[:4]) for path in folder.glob("[0-9][0-9][0-9][0-9]-*.md")]
    number = max(taken, default=0) + 1
    path = folder / f"{number:04d}-change-strategy.md"
    path.write_text(
        f"# {number:04d}. Change strategy: {SAYS[strategy]}\n\nDate: {today or datetime.date.today().isoformat()}\n\n"
        f"## Status\n\nAccepted\n\n## Decision\n\nStrategy: {strategy}\n\n## Context\n\n{why}\n", encoding="utf-8")
    relative = path.relative_to(root).as_posix()
    # The record reads the decision off the ADR when it is refreshed, and the map and the pages follow it.
    paths = sorted({relative, "project.json", *resurvey.refresh(root, clean_checked=True).rewritten})
    subprocess.run(["git", "add", "--", *paths], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", f"Decide the change strategy: {strategy}", "--", *paths],
                   cwd=root, check=False, capture_output=True)
    return relative


def written(root: Path, layout: Layout, answers: Mapping[str, str]) -> Path:
    """The PRD the draft reads: a person's answers written as one, or, with none given, the one they named,
    copied in. Answers win, because the PRD already written is offered again in the same form."""
    prd = root / layout.under(PRD)
    named = str(answers.get("prd") or "").strip()
    said = {key: str(answers.get(key) or "").strip() for key, *_ in QUESTIONS}
    if named and not any(said.values()):
        source = Path(named).expanduser()
        source = source if source.is_absolute() else root / source
        if not source.is_file():
            raise GenerationError(f"{named} is not a file: name the PRD, or answer the four questions instead")
        if source.resolve() != prd.resolve():
            prd.parent.mkdir(parents=True, exist_ok=True)
            prd.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return prd
    missing = [heading.lower() for key, heading, _, needed in QUESTIONS if needed and not said[key]]
    if missing:
        raise GenerationError(f"name a PRD, or say {'; '.join(missing)} — the specification is drafted from "
                              "these, and guessed without them")
    prd.parent.mkdir(parents=True, exist_ok=True)
    prd.write_text("# Product requirements\n" + "".join(
        f"\n## {heading}\n\n{said[key]}\n" for key, heading, *_ in QUESTIONS if said[key]), encoding="utf-8")
    return prd


def draft(root: Path, layout: Layout, answers: Mapping[str, str], said: list[str] | None = None) -> Fitting:
    """The PRD written or copied in, and the drafting session run on it in the background."""
    written(root, layout, answers)
    argv = [*make(layout), "draft", f"PRD={layout.under(PRD)}"]
    step = Step(argv, f"Drafting the constitution and the first specification from {layout.under(PRD)} — "
                      f"{' '.join(argv)}, a headless session. It stops for you to read the specification.",
                lambda code: ("Drafted. Read the specification, and Continue the build when it says what you mean."
                              if code == 0 else f"The draft stopped ({code}); what it said is above."), "draft")
    fitting = Fitting(root, [step], said)
    fitting.thread.start()
    return fitting


def take_step(root: Path, answers: Mapping[str, str], running: Fitting | None) -> tuple[int, str, Fitting | None]:
    """Run or record the step a person pressed: the status, what to say, and the child started, if one was."""
    if running and not running.said()["done"]:
        return 409, "something is already running here; the card below says what", None
    layout, step = layout_of(read_manifest(root, "the board")), answers.get("step")
    said = running.said()["lines"] if running else None
    try:
        if step == "init":
            return 200, "started", adopted(root, layout.delivery, answers.get("harness") or None, said)
        if step == "verify":
            return 200, "started", gate(root, layout, said)
        if step == "strategy":
            return 200, decide(root, layout, answers), None
        if step == "draft":
            return 200, "started", draft(root, layout, answers, said)
    except GenerationError as refused:
        return 400, str(refused), None
    return 400, f"{step!r} is not a step this board takes", None


def gate_when_grounded(root: Path, running: Fitting | None) -> Fitting | None:
    """The gate, started once the last row of the map is answered and nothing else is running here."""
    document = read_manifest(root, "the board")
    if asked(document) is not None or (running and not running.said()["done"]):
        return None
    return gate(root, layout_of(document), running.said()["lines"] if running else None)


def control(key: str, recommended: str | None, agents: str, prd: str = "") -> str:
    """The control on the step that is now, or nothing where only the agent can take it; `prd` is the PRD
    already written, offered again."""
    if key == INIT:
        return (f'<form class="ask-page" id="step-form"><div class="q"><label for="harness">Hand it to</label>'
                f'<select id="harness" name="harness">{agents}</select></div></form>'
                '<div class="ask"><button class="go" data-step="init">Run ./init</button></div>')
    if key == VERIFY:
        return '<div class="ask"><button class="go" data-step="verify">Run the gate</button></div>'
    if key == STRATEGY:
        options = "".join(
            f'<label class="check"><input type="radio" name="strategy" value="{esc(name)}"'
            f'{" checked" if name == recommended else ""}> <span><b>{esc(name)}</b> — {esc(says)}'
            f'{" (recommended)" if name == recommended else ""}</span></label>' for name, says in SAYS.items())
        return (f'<form class="ask-page" id="step-form"><div class="checks">{options}</div>'
                '<textarea name="why" rows="2" placeholder="Why this one, in your words (optional)"></textarea>'
                '</form><div class="ask"><button class="go" data-step="strategy">Decide</button></div>')
    if key in (CONSTITUTION, SPECIFY):
        boxes = "".join(
            f'<div class="q"><label for="{name}">{esc(heading)}{"" if needed else " (optional)"}</label>'
            f'<textarea id="{name}" name="{name}" rows="3" placeholder="{esc(hint)}"></textarea></div>'
            for name, heading, hint, needed in QUESTIONS)
        return ('<form class="ask-page" id="step-form"><div class="q"><label for="prd">A PRD you already have'
                f'</label><input id="prd" name="prd" value="{esc(prd)}" placeholder="its path — copied into the '
                'repository, and the questions below left empty"></div><p class="empty">or, without one, '
                f"answer these and they are written as the PRD:</p>{boxes}</form>"
                '<div class="ask"><button class="go" data-step="draft">Draft the constitution and the '
                "specification</button></div>")
    return ""


#: The page half: the step posted with its form, and the voyage read again — a child that is now running is
#: followed on the card the board lands with, as `./init` is.
SCRIPT = """
document.addEventListener('click', async event => {
  const button = event.target.closest('[data-step]');
  if (!button) return;
  const form = document.getElementById('step-form');
  const held = form ? Object.fromEntries(new FormData(form).entries()) : {};
  button.disabled = true;
  const answer = await fetch('/adopt/step', {method:'POST', headers:{'Content-Type':'application/json'},
                                            body: JSON.stringify({step: button.dataset.step, ...held})});
  if (answer.ok) { location.reload(); return; }
  button.disabled = false;
  const said = document.getElementById('step-said');
  said.hidden = false;
  said.textContent = await answer.text();
});
"""
