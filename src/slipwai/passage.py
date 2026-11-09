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

**And every stage says what to expect while it runs**, which is the other half of the same question. A
strip that says a stage is working answers "where are we" and leaves "is this normal" unanswered — and a
stage that stops for a person *by design* is indistinguishable, from the outside, from one that has hung.
`Stage.expect` is that sentence: roughly how long, and whether it will stop for you. It is written here
beside the state rather than in the page, because the stage is what knows it.
"""
# budget: 460 — the stages, the surfaces a storyboard shows when they were handed over, and the storyboard read
# both ways: states waiting on a person, and a drawing turned down whole that waits on being drawn again
# and the Slices step's two kinds of wanting a person: attention while work goes on, and stopped,
# and a build merged whole said as merged, with what it has not yet been shown said as not shown
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

# The three the board, the upstream stop and the tests reach through this module: re-exported, not read.
from .drawn import drawn_states as drawn_states
from .drawn import record_verdict as record_verdict
from .drawn import surface_pages
from .next_steps import template_gone
from .project.intake import pending as intake_pending

#: In order. A stage that this profile has not got is kept and drawn faint, so both profiles read one strip.
STATES = ("done", "working", "attention", "waiting", "todo", "skipped")
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
    #: What to expect while this stage runs: roughly how long, and whether it stops for a person. The
    #: second half is the one that matters — a stage that waits for somebody by design looks exactly like
    #: a stage that has hung, and the difference is a sentence nobody had written down.
    expect: str = ""


#: One state of one surface in `specs/<feature>/mockups/mock-states.md`, marked by the person who looked
#: at it. The spelling is `scripts/check-surfaces.py`'s, which is the gate that holds this file in a
#: generated project; this only reads it.
VERDICT = re.compile(r"^-\s*(?P<state>.+?)\s*\u2014\s*(?P<verdict>approved|parked|n/a)\b", re.MULTILINE)
#: What a feature with nothing to draw writes instead. A written answer, not an absence.
NO_SURFACES = "surfaces: none"


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


def storyboards(root: Path) -> list[Path]:
    """Every feature that has run the mock-up stage, by the file the stage leaves behind."""
    specs = root / "specs"
    return sorted(specs.glob("*/mockups/mock-states.md")) if specs.is_dir() else []


def disapproved(root: Path) -> str:
    """The feature whose storyboard a person turned down whole, or `""` where there is none.

    Every drawn state parked is what Disapprove writes, and it is a no to the drawing rather than a state
    waiting on a question — so what it waits on is the drawing again, from the reason it gives. A storyboard
    with some states approved is a person part-way through `/mockups`, and is theirs to finish.
    """
    for path in storyboards(root):
        try:
            said = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if NO_SURFACES in said:
            continue
        verdicts = [found.group("verdict") for found in VERDICT.finditer(said)]
        if verdicts and all(verdict == "parked" for verdict in verdicts):
            return path.parent.parent.name
    return ""


def drawn(root: Path) -> bool:
    """Whether anybody has drawn a surface yet, which is a different question from whether anybody has
    approved one.

    The stage ends at `mock-states.md`, so that file was the whole reading — and it left the half of the
    stage a person is actually in with nothing to say for it. Surfaces drawn and no verdicts written is a
    storyboard waiting to be looked at, which is the loudest state the strip has and the one it was showing
    as *to do*.
    """
    specs = root / "specs"
    # Surface pages, not any page: a storyboard on its own has nothing to approve, and reading it as drawn
    # left the board offering Approve, which then refused, and no Draw the storyboard to get out of it.
    return bool(specs.is_dir() and any(surface_pages(home) for home in specs.glob("*/mockups")))


def drawing_clock(root: Path, now: float | None = None) -> str:
    """How far into its budget a running drawing is — "6 of about 15 min" — or `""` where nothing says.

    Read from `.slipwai/surfaces.pid`, which `scripts/agents/surfaces.py` writes as its pid, when it started
    and its budget in seconds. Read there rather than worked out here because the budget comes from
    `harbour.json` through the telegraph, and a second reading of it on the board is a second place for it to
    be wrong. A pid file with one line is a drawing from before the budget, and says nothing.
    """
    try:
        lines = (root / ".slipwai/surfaces.pid").read_text(encoding="utf-8").split()
        began, allowed = float(lines[1]), float(lines[2])
    except (OSError, ValueError, IndexError):
        return ""
    taken = max(0, int(((time.time() if now is None else now) - began) // 60))
    return f"{taken} of about {allowed / 60:g} min"


def surfaces(root: Path) -> tuple[int, int, int]:
    """Across every feature that has run the stage: states seen, states approved, and states parked.

    A feature that wrote `surfaces: none` has run the stage and has nothing to show anybody, which is an
    answer: it adds no states, rather than reading as a feature nobody has looked at. A parked state is
    the one thing here that waits on a person, and it is what the strip goes amber for.
    """
    seen = approved = parked = 0
    for path in storyboards(root):
        try:
            said = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if NO_SURFACES in said:
            continue
        for found in VERDICT.finditer(said):
            seen += 1
            approved += found.group("verdict") == "approved"
            parked += found.group("verdict") == "parked"
    return seen, approved, parked


def names_slices(page: Path) -> bool:
    """Whether a model or a chart names at least one slice. Read as text, deliberately: the keel reads no
    YAML, and the one fact this needs is whether the `slices:` key is followed by anything but an empty list."""
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


def modelled(root: Path) -> bool:
    return names_slices(root / "docs/event-model/model.yaml")


def charts(root: Path) -> list[Path]:
    specs = root / "specs"
    return sorted(specs.glob("*/chart.yaml")) if specs.is_dir() else []


def split(root: Path) -> bool:
    """Whether a chart names a slice, which is what the fleet lights captains from."""
    return any(names_slices(one) for one in charts(root))


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
    charted = charts(root)
    found: list[Stage] = []

    prd = root / "docs/prd.md"
    found.append(Stage("prd", "PRD", "done" if prd.is_file() else "skipped", "docs/prd.md",
                       "slipwai generate --prd <file>",
                       f"{prd.stat().st_size:,} bytes" if prd.is_file() else "started without one",
                       expect="Nothing runs here. This is what the generate was handed, or was not."))

    init = step_state(receipt, "init") or ("done" if harness else "todo")
    found.append(Stage("init", "Init", init, ".specify/integration.json", "./init --integration <agent>",
                       f"Spec Kit, {harness}" if harness else "installs Spec Kit for the agent",
                       expect="A few minutes, over the network: Spec Kit installed, then the skills and "
                              "commands projected into the agent. It does not stop for you."))

    drafting = step_state(receipt, "draft")
    ratified = template_gone(root)
    found.append(Stage("constitution", "Constitution", drafting or ("done" if ratified else "todo"),
                       ".specify/memory/constitution.md",
                       "make draft, or /speckit-constitution in the agent",
                       "ratified" if ratified else "the template's markers still stand",
                       expect="Written in a headless session by `make draft` \u2014 minutes, not seconds. It "
                              "does not stop for you; read it afterwards."))
    ideas_waiting = intake_pending(root)
    held = plural(len(specs), "feature") if specs else "nothing to build from yet"
    if ideas_waiting:
        held = f"{held}; waiting: {', '.join(ideas_waiting)}"
    found.append(Stage("specification", "Specification", drafting or ("done" if specs else "todo"),
                       specs[0].relative_to(root).as_posix() if specs else "specs/<feature>/spec.md",
                       "make draft from docs/prd.md, or /sail with the next feature",
                       held,
                       expect="The first specification is written in the same draft as the constitution. A "
                              "further feature is handed to `/sail`, assessed, and specified only after a yes "
                              "and a go. It does not stop for you mid-assessment, but Continue the build does: "
                              "that button is your word that the specification is good."))

    # Straight after the specification and before the model, which is where `project/ladder.py` has the
    # mock-up review: a surface nobody has seen becomes a read model, a route and a set of tests, and all
    # three cost more to move than a drawing. The model is one of the three, which is what settles the
    # order — the screens are what the modelling conversation is held over.
    written = storyboards(root)
    seen, approved, parked = surfaces(root)
    sketched = drawn(root)
    drawing = step_state(receipt, "surfaces")
    found.append(Stage("storyboard", "Storyboard",
                       drawing or ("waiting" if (written and parked) or (sketched and not written)
                                   else "done" if written else "todo"),
                       written[0].relative_to(root).as_posix() if written
                       else "specs/<feature>/mockups/mock-states.md",
                       "approve or disapprove the storyboard on this page",
                       # While it draws, how long it has had against how long it may have, because the
                       # question at the ten-minute mark is whether ten minutes is normal.
                       f"drawing: {drawing_clock(root)}" if drawing == "working" and drawing_clock(root)
                       else (f"{approved} of {seen} states approved" + (f", {parked} parked" if parked else ""))
                       if seen else "no surfaces on this feature" if written
                       else "drawn: nobody has approved a state yet" if sketched
                       else "nobody has seen a surface yet",
                       expect="The surfaces are researched, drawn and storyboarded, then shown to you one "
                              "state at a time. **It stops for you at every surface** \u2014 that is the "
                              "stage, not a fault. The drawing has a budget \u2014 fifteen minutes, ten for a "
                              "redraw, scaled by the telegraph \u2014 and is ended at it with what it drew kept; "
                              "approving takes as long as you take."))

    if event:
        has_model = modelled(root)
        modelling = step_state(receipt, "model")
        found.append(Stage("model", "Event model", modelling or ("done" if has_model else "todo"),
                           "docs/event-model/model.yaml",
                           "the event-modeling skill in the agent, then make check-model",
                           "modelled" if has_model else "a modelling conversation - event first",
                           expect="A conversation, in the agent, with you in it. It stops for you by "
                                  "definition \u2014 nothing here moves until somebody models."))
    else:
        found.append(Stage("model", "Event model", "skipped", "docs/event-model/model.yaml", "",
                           "not on this profile",
                           expect="Not on this profile. The chart is drawn from the specification instead."))

    launching = step_state(receipt, "launch")
    split = bool(counts)
    found.append(Stage("chart", "Chart & split", launching or ("done" if split else "todo"),
                       charted[0].relative_to(root).as_posix() if charted else "specs/<feature>/chart.yaml",
                       "make launch (the board's Continue the build)",
                       f"{plural(sum(counts.values()), 'slice')} charted" if split else
                       "charted, not split" if charted else "fairways, marks and slices",
                       expect="A headless session draws the chart and splits it into slices \u2014 minutes. "
                              "It does not stop for you."))

    berths = fleet.get("berths") or []
    inbox = fleet.get("inbox") or []
    cruising = step_state(receipt, "cruise")
    # `working` is what `fleet.state_of` calls a live berth; this compared against `running`, which it never
    # returns, so a fleet at work read as `todo` whenever nothing waited on a person.
    working = any(row.get("state") == "working" for row in berths) or counts.get("working", 0) > 0
    # Unread decisions below the ceiling are listed for reading and want nothing yet; past it, and every park,
    # question and note for the host, wants a person.
    wants = [row for row in inbox if row.get("kind") != "decisions" or row.get("blocking") == "yes"]
    wanted = len(wants) + counts.get("waiting", 0)
    all_done = split and counts.get("done", 0) == sum(counts.values())
    # Split, not done, nothing running: the one silence the tree cannot explain, said as a wait on a person.
    becalmed = split and not all_done and not working and not fleet.get("running") and not cruising
    # Two different things, drawn differently: *attention* is something wanting a person while slices are
    # still at work, and *waiting* is everything stopped until a person acts. One red for both drew a fleet
    # with seven slices running and fifteen decisions to read the same as a fleet that had stopped.
    # Every slice merged, only a park still holds the stage: recap merged all 34 and the stage said `stopped
    # until you act` over eleven notes and three old questions, none of which held a slice.
    holding = not all_done or any(row.get("kind") == "parked" for row in wants)
    stopped = holding and (becalmed or (bool(wanted) and not working))
    found.append(Stage("slices", "Slices", cruising or ("waiting" if stopped else "done" if all_done
                                                        else "attention" if wanted
                                                        else "working" if working else "todo"), "deck logs",
                       ("the fleet is running; Stop the fleet ends it, and a park appears under Waiting on you"
                        if fleet.get("running") else "make cruise; make cruise-tell answers a park"),
                       f"{counts.get('done', 0)} of {sum(counts.values())} merged; left for you: "
                       f"{wanting(wants, counts)}" if all_done and wanted and not stopped else
                       "the fleet is not running: cast off" if becalmed and not wanted else
                       f"stopped until you act: {wanting(wants, counts)}" if stopped else
                       f"{wanting(wants, counts)}; the rest is still at work" if wanted else
                       f"{counts.get('done', 0)} of {sum(counts.values())} merged" if split
                       else "the fleet, under /cruise",
                       expect="The fleet: a captain per fairway, working its slices. Hours, and the Speed "
                              "card below is what sets how many run at once. It stops for you when a "
                              "captain parks, and the park appears under Waiting on you."))

    demos = fleet.get("demo_due") or []
    accepted = fleet.get("accepted") or []
    # Not demoed is said as not demoed: the summary read `every capability demoed` — the stage's goal — over a
    # voyage with no `accepted` line at all, which is a build that looks finished and has never been shown.
    found.append(Stage("accepted", "Accepted", "working" if demos else "done" if all_done and accepted else "todo",
                       "accepted lines",
                       "/sail takes each whole capability through its gates to its demo" if all_done and not accepted
                       else "the demo, as the actor; /cruise-tell records the verdict",
                       f"{len(accepted)} capability(ies) accepted" if accepted else
                       f"{', '.join(demos)} ready to demo" if demos else
                       "every slice merged; no capability has been through its gates or demoed yet" if all_done
                       else "every capability demoed",
                       expect="Each capability demoed to you as the actor. It stops for you at every demo, "
                              "and the verdict is typed under *Waiting on you*."))
    return found


def plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def wanting(wants: list[dict], counts: dict[str, int]) -> str:
    """What wants a person, said by kind — `2 parks; 15 decisions nobody has read yet, over the ceiling of
    10` — so the step names the thing to go and do rather than a count of things."""
    kinds = {"parked": "park", "question": "question", "told": "note"}
    said = [plural(sum(1 for row in wants if row.get('kind') == kind), word) + (" for you" if kind == "told" else "")
            for kind, word in kinds.items() if any(row.get("kind") == kind for row in wants)]
    said += [str(row.get("what", "")) for row in wants if row.get("kind") == "decisions"]
    if counts.get("waiting") and not any(row.get("kind") == "parked" for row in wants):
        said.insert(0, f"{plural(counts['waiting'], 'slice')} waiting")
    return "; ".join(said) or "something waits on you"


def current(found: list[Stage]) -> Stage | None:
    """The stage a person is on: the first that is working or waiting, else the first still to do."""
    return (next((one for one in found if one.state in ("working", "attention", "waiting")), None)
            or next((one for one in found if one.state == "todo"), None))
