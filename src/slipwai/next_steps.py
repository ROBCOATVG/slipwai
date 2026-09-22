"""`slipwai adopt --next`: where an adoption stands in the sequence `adopt` started, read off the tree.

Brownfield adoption (#74; experimental as `AGENTS.md` defines the word) ends with a report naming what to do
next — `./init`, then `/ground`, then the gate, then the root Makefile — and that report is printed once, into
a terminal, at the end of the longest output the factory produces. It scrolls away. The sequence it names spans
days and four tools, so by the time a step matters its instructions are gone, and `docs/adoption.md`, which
carries the same list, is introduced there as a record of what was wrapped rather than as the plan.

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

from .convergence import AXES
from .layout import Layout
from .origin import Adoption
from .services import App, wrapped_of

# Spec Kit's own file, written by `specify init` and by nothing this factory generates: the one mark that
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
    spoken = {
        row.get("axis") for row in (adoption.convergence or [])
        if isinstance(row, dict) and row.get("provenance") in SAID
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
    recommended = (adoption.strategy or {}).get("recommended")
    found = [
        Step(
            f"./{layout.under('init')}" if layout.moved else "./init",
            "installs Spec Kit and projects the skills and commands into the agent that gets them "
            "(`--integration claude` names it; `--extension codegraph` indexes the code for it)",
            initialised,
        ),
        Step(
            "/ground, in the agent",
            f"{open_rows} of {len(AXES)} rows of the map are nobody's word yet — it asks one at a time, shows the "
            "evidence and the rungs first, and records each answer with its provenance"
            if open_rows else "every row of the map has been placed by a person",
            open_rows == 0,
        ),
        Step(
            f"{layout.make} verify",
            f"the gate. Its first run records the lint and typecheck findings that are there as the baseline; "
            f"commit {layout.under(BASELINE)}. A red test suite stops the run and says so — read the failures, then "
            f"`{layout.make} ratchet-tighten` quarantines it deliberately",
            baseline,
        ),
    ]
    if layout.moved:
        include = f"-include {layout.delivery}/Makefile"
        makefile = root / "Makefile"
        found.append(Step(
            f"add `{include}` to the root Makefile",
            "and `make verify` is one word",
            makefile.is_file() and include in makefile.read_text(),
        ))
    found.append(Step(
        "an accepted ADR with a `Strategy:` line",
        (f"the map recommends `{recommended}`, and a recommendation is not a decision — `leave it` is one of the five"
         if recommended else "nothing is recommended yet; `/ground` asks why this work is happening, and the "
         "recommendation is made from that"),
        decided,
    ))
    return found


def report(root: Path, layout: Layout, adoption: Adoption, apps: list[App]) -> str:
    """The sequence with each step marked, the first unfinished one marked as the one to do now."""
    found = steps(root, layout, adoption, apps)
    lines = ["Where this adoption stands (experimental): the sequence `adopt` started, as the tree has it now."]
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
            f"they start ({', '.join(unproven)}) — /ground asks, and /drive's Pin stage refuses to change one until "
            "somebody has"
        )
    if not next_seen:
        lines.append("")
        lines.append(
            "Every step of the intro is done. `/drive` is the loop from here, and this command stays honest: it "
            "reads the tree, so a row that moves back shows up here."
        )
    else:
        lines.append("")
        lines.append(
            f"The same sequence, with what each step forfeits and where every fact came from, is "
            f"{layout.under('docs/adoption.md')}; {layout.under('docs/convergence.md')} is the map itself."
        )
    return "\n".join(lines)
