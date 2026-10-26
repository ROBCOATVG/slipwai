"""The adoption's steps the board can take itself, and the control each one is on the voyage.

`adoption_card` shows the sequence `adopt --next` reads; this is what makes it move. Each step that is a command
the board can run, or a record it can write, gets the control that does it, on the step that is *now*:

- **`./init`**, where the adoption left it as the next step: the agent picked, and run in the background.
- **`/ground`** is `ground_card`'s, one row at a time — and its last answer starts the gate, because nothing is
  left to ask before it.
- **`/verify`**: the gate, run in the background, and its first baseline committed when it is green.
- **The strategy**: the five on offer with the recommendation picked, written as the accepted ADR whose
  `Strategy:` line the gate reads — *leave it* is one of them.
- **The steps the strategy adds**: the new home generated where it is beside the old code or a new repository, and
  each step only the agent can take — the build floor, `smoke`, the parity list — handed to a headless session.
- **The constitution and the first specification**: a PRD the person already has, named by its path and copied
  in, or four questions answered and written as one — who it is for, what it must do, how anyone will know it
  is done, and what is fixed — and `make draft` run on it: the same session a generated project with a PRD
  gets, which drafts both and stops for the person to read the specification. One box invited one word, and a
  session asked to draft a product from "modernisation" rightly refused to.

From the first specification on, the voyage's own strip and its Continue the build are the next steps.
"""
from __future__ import annotations

import datetime
import json
import shlex
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import quote

from . import next_steps, resurvey
from .errors import GenerationError
from .folder_field import folder_field
from .ground_card import asked
from .init_run import Fitting, Step, adopted
from .interview_page import elected_in
from .layout import Layout, layout_of
from .manifest import apps_from_manifest, read_manifest
from .next_steps import BASELINE
from .origin import adoption_of
from .page_shell import esc
from .stack_proposal import Proposal
from .strategy import SAYS
from .strategy_form import form as strategy_form
from .strategy_form import lines as record_lines
from .strategy_steps import CONTINUE, home_of, name_of, stack_of
from .uncommitted import refuse_foreign

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
    found = next((key for key in (GROUND, VERIFY, STRATEGY, HOME, NEW_SYSTEM, ELSEWHERE, CONSTITUTION, SPECIFY)
                  if action.startswith(key)), "")
    return found or (AGENT if action.endswith(IN_THE_AGENT) and not action.startswith("/") else "")


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
    # Every line the strategy cannot start without is asked for on the form and refused here while one is empty.
    strategy, said = record_lines(answers)
    given = said.pop("Why", "")
    document = read_manifest(root, "the board")
    # The map's strategy row climbs `open` → `why-recorded` → … and the gate holds a decision with no `why` at
    # `open`: the reason this work is happening is recorded with the decision when /ground did not record it.
    if not document.get("why") and not given:
        raise GenerationError("say why this work is happening — the business trigger, in your words — before "
                              "deciding what to do about it")
    why = given or "Decided on the board, from the map and its recommendation."
    refuse_foreign(root, resurvey.writes(root, layout), "deciding the strategy")
    if not document.get("why"):
        document["why"] = given
        (root / "project.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    folder = root / layout.under("docs/adr")
    folder.mkdir(parents=True, exist_ok=True)
    taken = [int(path.name[:4]) for path in folder.glob("[0-9][0-9][0-9][0-9]-*.md")]
    number = max(taken, default=0) + 1
    path = folder / f"{number:04d}-change-strategy.md"
    path.write_text(
        f"# {number:04d}. Change strategy: {SAYS[strategy]}\n\nDate: {today or datetime.date.today().isoformat()}\n\n"
        f"## Status\n\nAccepted\n\n## Decision\n\nStrategy: {strategy}\n"
        + "".join(f"{name}: {value}\n" for name, value in said.items())
        + f"\nThe playbook is `docs/strategies/{strategy}.md`: what this decision means for every step after it.\n"
        f"\n## Context\n\n{why}\n", encoding="utf-8")
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


def home(root: Path, said: list[str] | None = None) -> Fitting:
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
        where_to, cwd = str(target), root
    else:
        # Each committed before the next: `add-frontend` refuses a tree with changes nobody has committed, so that
        # undoing it undoes only what it wrote.
        commands = [[*slipwai, "add-service", name, *on, "--purpose=the new home the old code's capabilities move to"],
                    ["git", "add", "-A"], ["git", "commit", "-q", "-m", f"Generate the new home: {name}"]]
        if browser:
            commands += [[*slipwai, "add-frontend", f"{name}-web", f"--frontend={stack['frontend']}", f"--api={name}"],
                         ["git", "add", "-A"],
                         ["git", "commit", "-q", "-m", f"Give the new home its browser app: {name}-web"]]
        where_to, cwd = f"apps/{name}", root
    steps = [Step(argv, f"Running {' '.join(argv[2:] if argv[0] == sys.executable else argv)}", lambda code: (
        "" if code == 0 else f"It stopped ({code}); what it said is above."), "home") for argv in commands]
    steps[-1] = Step(steps[-1].argv, steps[-1].announced, lambda code: (
        f"The new home is at {where_to}, current from day one: every new feature is built there."
        if code == 0 else f"It stopped ({code}); what it said is above."), "home")
    fitting = Fitting(cwd, steps, said)
    fitting.thread.start()
    return fitting


def agent_step(root: Path, layout: Layout, said: list[str] | None = None) -> Fitting:
    """The step that is now, where only the agent can take it, handed to a headless session in the background."""
    document = read_manifest(root, "the board")
    adoption = adoption_of(document)
    if adoption is None:
        raise GenerationError("this repository was not adopted")
    now = next((step for step in next_steps.steps(root, layout, adoption, apps_from_manifest(document, True))
                if not step.done), None)
    if now is None or key_of(now.action) != AGENT:
        raise GenerationError("the step that is now is not one the agent takes from here; read the card again")
    if not (root / layout.under(STEP)).is_file():
        raise GenerationError(f"{layout.under(STEP)} is not here: `slipwai adopt --refresh` writes it")
    argv = [sys.executable, layout.under(STEP), now.action[:-len(IN_THE_AGENT)], now.why]
    step = Step(argv, f"Handing {now.action[:-len(IN_THE_AGENT)]} to a headless session — it reads the strategy's "
                      "playbook, does this step and stops.",
                lambda code: ("The session ended; the card reads the tree again to see whether the step is done."
                              if code == 0 else f"The session stopped ({code}); what it said is above."), "agent")
    fitting = Fitting(root, [step], said)
    fitting.thread.start()
    return fitting


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
            return 200, "started", adopted(root, layout.delivery, answers.get("harness") or None, said,
                                           elected_in(answers))
        if step == "verify":
            return 200, "started", gate(root, layout, said)
        if step == "strategy":
            return 200, decide(root, layout, answers), None
        if step == "home":
            return 200, "started", home(root, said)
        if step == AGENT:
            return 200, "started", agent_step(root, layout, said)
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


def control(key: str, recommended: str | None, agents: str, prd: str = "", tooling: str = "",
            proposal: Proposal | None = None, name: str = "next", action: str = "") -> str:
    """The control on the step that is now, or nothing where only the agent can take it; `prd` is the PRD
    already written, offered again, and `tooling` the extensions `./init` can elect, as their checkboxes."""
    if key == INIT:
        return (f'<form class="ask-page" id="step-form"><div class="q"><label for="harness">Hand it to</label>'
                f'<select id="harness" name="harness">{agents}</select></div>{tooling}</form>'
                '<div class="ask"><button class="go" data-step="init">Run ./init</button></div>')
    if key == ELSEWHERE:
        where = action[len(CONTINUE):].strip()
        return (f'<div class="ask"><a class="go" href="/voyage?look={esc(quote(where))}" target="_blank" '
                f'rel="noopener">Open the new system\'s voyage</a></div>')
    if key in (HOME, NEW_SYSTEM):
        return ('<div class="ask"><button class="go" data-step="home">'
                f'{"Generate the new system" if key == NEW_SYSTEM else "Generate the new home"}</button></div>')
    if key == VERIFY:
        return '<div class="ask"><button class="go" data-step="verify">Run the gate</button></div>'
    if key == AGENT:
        return ('<div class="ask"><button class="go" data-step="agent">Hand it to the agent</button></div>'
                '<p class="empty">a headless session takes this step and stops; or take it yourself in the agent.</p>')
    if key == STRATEGY:
        return strategy_form(recommended, proposal, name)
    if key in (CONSTITUTION, SPECIFY):
        boxes = "".join(
            f'<div class="q"><label for="{name}">{esc(heading)}{"" if needed else " (optional)"}</label>'
            f'<textarea id="{name}" name="{name}" rows="3" placeholder="{esc(hint)}"></textarea></div>'
            for name, heading, hint, needed in QUESTIONS)
        return ('<form class="ask-page" id="step-form"><div class="q"><label for="prd">A PRD you already have'
                f'</label>{folder_field("prd", prd, file=True)}<p class="empty">copied into the repository; the '
                "questions below win where they are answered.</p></div><p class=\"empty\">or, without one, "
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
  // Checked boxes arrive as one entry each under one name; joined, as `./init` takes a list.
  for (const group of form ? form.querySelectorAll('.checks') : []) {
    const boxes = group.querySelectorAll('input[type=checkbox]');
    if (boxes.length) held[boxes[0].name] = [...boxes].filter(one => one.checked).map(one => one.value).join(',');
  }
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
