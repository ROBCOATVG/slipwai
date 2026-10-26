"""`slipwai adopt --next`: where an adoption stands in the sequence `adopt` started, read off the tree.

Brownfield adoption (#74) ends with a report naming what to do next — `./init`, then `/ground`, then the gate, then the
root Makefile — and that report is printed once, into a terminal, at the end of the longest output the keel produces.
It scrolls away. The sequence it names spans days and four tools, so by the time a step matters its instructions are
gone, and `docs/adoption.md`, which carries the same list, is introduced there as a record of what was wrapped rather
than as the plan.

So the plan is not printed and remembered, it is *derived*. Every step in it leaves a mark: Spec Kit writes
`.specify/integration.json`, the first gate run writes the ratchet baseline, `/ground` moves a row's provenance
off `unrecorded`, the root Makefile gains an `-include`, a strategy is an accepted ADR. This module reads those
marks and says which steps are done, which one is next, and why — so the answer to "where was I" is a command
and not a scrollback search. Nothing here writes: it is a reading of the tree and the record, and it is as
right as they are.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .catalog import CATALOG
from .convergence import AXES
from .extensions import suggestion
from .layout import Layout
from .origin import Adoption
from .services import App, wrapped_of
from .strategy_steps import CONTINUE, new_system
from .strategy_steps import steps as strategy_steps

#: What `./init` can offer beyond Spec Kit, from the catalogue. Empty where no extension is installed, which
#: is every copy of the keel until somebody installs one — so the line simply does not mention them.
EXTENSIONS_OFFERED = suggestion(CATALOG)

# Spec Kit's own file, written by `specify init` and by nothing this keel generates: the one mark that
# says `./init` reached the step that needs the network. `init` itself checks for exactly this before
# deciding a rerun has nothing to ask of Spec Kit.
SPEC_KIT = ".specify/integration.json"
BASELINE = "baseline.json"
# A row nobody has spoken for. `detected` is the tree's reading, not a person's answer — `/ground` says so
# too — so it is counted as still open, which is what makes the count fall as the questions get answered.
SAID = ("confirmed", "overridden")


@dataclass(frozen=True)
class Step:
    """One step of the sequence: what to run, why, and whether the tree says it has happened."""

    action: str
    why: str
    done: bool


def rows_open(adoption: Adoption) -> int:
    """How many rows of the convergence map are still nobody's word."""
    # Asked and not known is answered too: the row stays `unrecorded`, and asking it again here would be a loop.
    spoken = {
        row.get("axis") for row in (adoption.convergence or [])
        if isinstance(row, dict) and (row.get("provenance") in SAID or row.get("asked"))
    }
    return sum(1 for axis in AXES if axis.key not in spoken)


def unstarted(apps: list[App]) -> list[str]:
    """The wrapped applications with no `smoke` recorded — nobody has proved they start."""
    return [app.name for app in wrapped_of(apps) if not (app.commands or {}).get("smoke")]


def steps(root: Path, layout: Layout, adoption: Adoption, apps: list[App]) -> list[Step]:
    """The sequence, in order, each read off the tree rather than remembered."""
    initialised = (root / SPEC_KIT).is_file()
    open_rows = rows_open(adoption)
    baseline = (root / layout.under(BASELINE)).is_file()
    decided = bool((adoption.strategy or {}).get("decided"))
    incomplete = list((adoption.strategy or {}).get("missing") or [])
    recommended = (adoption.strategy or {}).get("recommended")
    outstanding = [str(row.get("name")) for row in (adoption.candidates or []) if isinstance(row, dict)]
    found = [
        Step(
            f"./{layout.under('init')}" if layout.moved else "./init",
            "installs Spec Kit and projects the skills and commands into the agent that gets them "
            "(`--integration claude` names it"
            + (f"; {EXTENSIONS_OFFERED}" if EXTENSIONS_OFFERED else "") + ")",
            initialised,
        ),
        Step(
            "confirm what the survey found",
            (f"1 buildable directory ({outstanding[0]}) is recorded as a candidate"
             if len(outstanding) == 1 else
             f"{len(outstanding)} buildable directories ({', '.join(outstanding)}) are recorded as candidates")
            + " and none as an application — /ground asks "
            "which of them is one, with the code in front of it, and `slipwai adopt --confirm <name>` records "
            "the answer. `verify` refuses until one is confirmed"
            if outstanding else "every buildable directory the survey found has been answered for",
            not outstanding,
        ),
        Step(
            "/ground, in the agent",
            f"{open_rows} of {len(AXES)} rows of the map are nobody's word yet — it asks one at a time, shows the "
            "evidence and the rungs first, and records each answer with its provenance"
            if open_rows else "every row of the map has been placed by a person",
            open_rows == 0,
        ),
        Step(
            "/verify",
            f"the gate, `{layout.make} verify`. Its first run records the lint and typecheck findings that are there "
            f"as the baseline; commit {layout.under(BASELINE)}. A red test suite stops the run and says so — `/verify` "
            f"shows the failures, and quarantines the suite deliberately if you tell it to",
            baseline,
        ),
    ]
    if layout.moved:
        include = f"-include {layout.delivery}/Makefile"
        makefile = root / "Makefile"
        found.append(Step(
            f"add `{include}` to the root Makefile",
            "so the gate runs from the root, as it does in a generated project",
            makefile.is_file() and include in makefile.read_text(encoding="utf-8"),
        ))
    found.append(Step(
        "an accepted ADR with a `Strategy:` line",
        (f"`{adoption.strategy['decided']}` is decided, and its ADR does not yet say "
         + ", ".join(f"`{name}:`" for name in incomplete) + " — what follows from it waits on these"
         if decided and incomplete else
         f"the map recommends `{recommended}`, and a recommendation is not a decision — `leave it` is one of the four"
         if recommended else "nothing is recommended yet; `/ground` asks why this work is happening, and the "
         "recommendation is made from that"),
        decided and not incomplete,
    ))
    # What the decided strategy needs before the first feature: its playbook's steps, read off the tree.
    found += [Step(*one) for one in strategy_steps(root, layout, adoption, apps)]
    elsewhere = new_system(root, adoption)
    if elsewhere is not None:
        # A rewrite in a new repository: the constitution, the first feature and the loop are that project's. This
        # one is the old system, frozen, and the sequence here ends by handing over.
        found.append(Step(
            f"{CONTINUE} {elsewhere}",
            "its own voyage drafts the constitution and the first specification there, from the same PRD; this "
            "repository is the old system, frozen but for fixes, characterised for the parity suite and cut over at "
            "the end",
            False,
        ))
        return found
    # The sequence used to stop here, at a repository that is ready and has been asked to do nothing. The
    # first person to take it end to end had to be told the rest in chat — ratify, specify, sail, cruise —
    # and the order matters: `check-constitution` fails the moment `specs/` exists over a template
    # constitution, which takes `verify`, and `/sail` with it.
    # Absent entirely means `./init` has not run, which is pending rather than done — the first reading of
    # this reported a constitution as ratified in a repository that had no `.specify/` at all.
    ratified = template_gone(root)
    specified = any((root / "specs").glob("*/spec.md")) if (root / "specs").is_dir() else False
    found.append(Step(
        "/speckit-constitution, in the agent",
        "the principles the gate holds this repository to. Before the first spec, not after: "
        "`check-constitution` fails once `specs/` exists over the template it installed, and takes `verify` "
        "and `/sail` with it",
        ratified,
    ))
    found.append(Step(
        "/speckit-specify, in the agent",
        "the first feature, as a specification under `specs/<feature>/spec.md` — what `/sail` and `/cruise` "
        "work from, and what they refuse to start without",
        specified,
    ))
    found.append(Step(
        "/sail, in the agent",
        "the loop, once by hand: it enters at the stage this map is weakest on and stops at every question "
        "only a person can answer. Worth watching before anything runs it unattended",
        False,
    ))
    found.append(Step(
        f"`{layout.make} cruise`",
        "the same loop with nobody at the wheel, off until a project asks for it: "
        "`python3 " + layout.under("scripts/agents/cruise.py") + " --set enabled=true`, and "
        "`--set max_iterations=<n>` bounds it while you watch. `cruise-watch`, `cruise-status`, "
        "`cruise-tell` and `cruise-stop` are the seat beside it",
        False,
    ))
    return found


def template_gone(root: Path) -> bool:
    """Whether the constitution has been written — `/speckit-constitution` replaces the template's markers."""
    page = root / ".specify/memory/constitution.md"
    if not page.is_file():
        return False
    text = page.read_text(errors="replace", encoding="utf-8")
    return "[PRINCIPLE_1_NAME]" not in text and "<!-- journey:" not in text


def report(root: Path, layout: Layout, adoption: Adoption, apps: list[App]) -> str:
    """The sequence with each step marked, the first unfinished one marked as the one to do now."""
    found = steps(root, layout, adoption, apps)
    lines = ["Where this adoption stands: the sequence `adopt` started, as the tree has it now."]
    next_seen = False
    for step in found:
        if step.done:
            marker = "done"
        elif next_seen:
            marker = "then"
        else:
            marker, next_seen = "now", True
        lines.append(f"  {marker + ':':<6}{step.action} — {step.why}")
    unproven = unstarted(apps)
    wrapped = wrapped_of(apps)
    if unproven:
        lines.append(
            f"  also: {len(unproven)} of {len(wrapped)} application(s) have no `smoke` recorded, so nobody has proved "
            f"they start ({', '.join(unproven)}) — /ground asks, and /sail's Pin stage refuses to change one until "
            "somebody has"
        )
    if not next_seen:
        lines.append("")
        lines.append(
            "Every step of the intro is done. `/sail` is the loop from here, and this command stays honest: it "
            "reads the tree, so a row that moves back shows up here."
        )
    else:
        lines.append("")
        lines.append(
            f"The same sequence, with what each step forfeits and where every fact came from, is "
            f"{layout.under('docs/adoption.md')}; {layout.under('docs/convergence.md')} is the map itself."
        )
    return "\n".join(lines)
