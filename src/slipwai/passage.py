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
# budget: 400 — the stages, and the storyboard read both ways: states waiting on a person, and a drawing
# turned down whole that waits on being drawn again
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from .next_steps import template_gone
from .project.intake import pending as intake_pending

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
_FEATURE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
_ARTICLE = re.compile(r'<article\b[^>]*\bclass="[^"]*\bstate\b[^"]*"[^>]*>(.*?)</article>',
                      re.IGNORECASE | re.DOTALL)
_HEADING = re.compile(r"<h2>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_NOT_A_SURFACE = frozenset({"storyboard.html", "index.html"})


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


def _plain(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&#39;", "'"))
    return re.sub(r"\s+", " ", text).strip()


def _surface_name(title: str, stem: str) -> str:
    title = re.sub(r"^\s*mock(-?up)?:\s*", "", _plain(title), flags=re.IGNORECASE)
    for mark in ("\u2014", " - "):
        if mark in title:
            title = title.split(mark)[-1].strip()
    return title or stem


def drawn_states(root: Path, feature: str) -> list[tuple[str, list[str]]]:
    """Each drawn surface and the states on its page. The storyboard and the contents page are not surfaces."""
    if not _FEATURE.fullmatch(feature):
        raise ValueError(f"no feature {feature}")
    home = (root / "specs" / feature / "mockups").resolve()
    if not home.is_dir() or not home.is_relative_to((root / "specs").resolve()):
        raise ValueError(f"nothing drawn under specs/{feature}/mockups")
    found: list[tuple[str, list[str]]] = []
    for page in sorted(home.glob("*.html")):
        if page.name in _NOT_A_SURFACE:
            continue
        html = page.read_text(encoding="utf-8", errors="replace")
        title = _TITLE.search(html)
        name = _surface_name(title.group(1) if title else "", page.stem)
        states: list[str] = []
        for article in _ARTICLE.finditer(html):
            heading = _HEADING.search(article.group(1))
            label = _plain(heading.group(1)) if heading else ""
            if label and label not in states:
                states.append(label)
        found.append((name, states or ["shown"]))
    if not found:
        raise ValueError(f"nothing drawn under specs/{feature}/mockups")
    return found


def record_verdict(root: Path, feature: str, verdict: str, reason: str = "", by: str = "") -> str:
    """Write `mock-states.md` from the drawings a person has just approved or disapproved.

    Approving marks every drawn state approved. Disapproving parks them, and a park with no reason is a
    blank, which is the one mark this file refuses. `by` is a first line saying who gave the verdict, where
    it was not a person.
    """
    if verdict not in ("approved", "parked"):
        raise ValueError("approve or disapprove the storyboard")
    why = re.sub(r"\s+", " ", reason).strip()
    if verdict == "parked" and not why:
        raise ValueError("say why you disapprove, so the next drawing knows what to change")
    lines: list[str] = [by, ""] if by else []
    for name, states in drawn_states(root, feature):
        lines.append(f"## Surface: {name}")
        mark = "approved" if verdict == "approved" else f"parked: {why}"
        lines.extend(f"- {state} \u2014 {mark}" for state in states)
        lines.append("")
    (root / "specs" / feature / "mockups" / "mock-states.md").write_text("\n".join(lines), encoding="utf-8")
    return "approved" if verdict == "approved" else "disapproved"


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
    return bool(specs.is_dir() and next(specs.glob("*/mockups/*.html"), None))


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
    held = f"{len(specs)} feature(s)" if specs else "nothing to build from yet"
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
                       f"{sum(counts.values())} slice(s) charted" if split else
                       "charted, not split" if charted else "fairways, marks and slices",
                       expect="A headless session draws the chart and splits it into slices \u2014 minutes. "
                              "It does not stop for you."))

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
                       else "the fleet, under /cruise",
                       expect="The fleet: a captain per fairway, working its slices. Hours, and the Speed "
                              "card below is what sets how many run at once. It stops for you when a "
                              "captain parks, and the park appears under *Waiting on you*."))

    demos = fleet.get("demo_due") or []
    accepted = fleet.get("accepted") or []
    found.append(Stage("accepted", "Accepted", "working" if demos else "done" if all_done and accepted else "todo",
                       "accepted lines", "the demo, as the actor; /cruise-tell records the verdict",
                       f"{len(accepted)} capability(ies) accepted" if accepted else "every capability demoed",
                       expect="Each capability demoed to you as the actor. It stops for you at every demo, "
                              "and the verdict is typed under *Waiting on you*."))
    return found


def current(found: list[Stage]) -> Stage | None:
    """The stage a person is on: the first that is working or waiting, else the first still to do."""
    return (next((one for one in found if one.state in ("working", "waiting")), None)
            or next((one for one in found if one.state == "todo"), None))
