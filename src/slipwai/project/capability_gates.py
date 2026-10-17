"""The capability gates: the readings that run once over a whole capability rather than once per slice.

A slice is a few hours of work and a capability is the chunk a person's demo is of, usually several slices.
Four readings used to run at the end of every slice — the gaps trace after converge, the design review from
screenshots, the hand's walk of the examples in a browser, and the adversary pass — and each of them reads
something a slice only has a fraction of: a promise that two slices keep between them, a screen a later
slice finishes, a path that only runs end to end once the last slice lands, a surface the capability widens
as a whole. Read per slice, each found the same seam again in the next instalment, or found an absence the
next slice was always going to fill. Mutation moved first, on 2026-10-14, for the same reason; the other four
followed it on 2026-10-17, from the warbook's feedback that they "should happen per stream PR point, not per
slice". Version 2 has no stream pull request — the plan merges each slice to trunk and forbids integration
branches — so the point is the capability: whole when its last slice has merged, which
`scripts/agents/capabilities.py` already computes, and before the person's demo stop walks it.

What stays per slice is what only a slice can answer, scoped to what the slice added or changed: screen design
for its own screens, one review of its own diff, its examples proven by its own tests, and the record of which
attack-surface triggers it widened — a record, not an attack. Convergence is not one of them since 2026-10-17: it is the
first capability gate, because what it asks — does the code do what the specification requires — has its
answer only once the slices that share the requirement are all built. **Under the `open` release mode four
readings do not wait**: where a merge reaches the actor at once, code nobody has looked at would be in front
of somebody before the capability is whole, so converge, the gaps trace, the design review and the hand's walk
run per slice where they used to, and a slice that widened authorisation, identity or money is attacked
before its push. The capability still runs converge, the adversary pass and mutation over the whole, in every
mode — the adversary pass, as always, only where a slice widened something.
"""
from __future__ import annotations

from .converge_stage import convergence_gate

#: Where a capability's gate record lives: one directory per capability, beside the slices it gathers.
RECORD = "specs/<feature>/capabilities/<capability>/"
#: The record itself. Its last line is `Cleared:`, which is what `capabilities.py` reads to call a demo due.
GATES_FILE = RECORD + "gates.md"
#: The readings, in the order they run: each one's fixes are code the next one should see.
GATES = ("converge", "gaps", "design review", "adversary", "mutation", "the hand's walk")
#: The readings that run per slice under the `open` release mode, where a merge reaches the actor at once.
OPEN_PER_SLICE = ("converge", "gaps", "design review", "the hand's walk")
#: The readings that run over the whole capability in every release mode, `open` included.
EVERY_MODE = ("converge", "adversary", "mutation")
#: What a slice's row in the adversary log is headed, so `check-decisions` reads it as that slice's row.
TRIGGER_ROW = "## <slice-id> · <commit> · <date> · trigger record"
#: What the capability's row is headed when no slice widened anything and nothing was attacked.
SKIP_ROW = "## <capability> · <commit> · <date> · skipped: no slice widened a trigger"

OPEN_MODE = """**Under the `open` release mode four of the gates do not wait for the capability.** Where a
   merge reaches the actor at once — a push to `main` deploys production and nothing holds this slice back (no
   flag seeded off, no keystone left out), which is the case the push check stops for where this page has
   one — converge, the gaps trace, the design review and the hand's walk run per slice, over the slice's diff
   and examples, where they used to: converge and then `/gaps` at the end of *Implementation*, the design
   review after it, the hand at the *Demo* rung, each recorded in the slice's own folder. The *Attack
   surface* rung also attacks a slice whose record has the authorisation, identity or money trigger
   `widened`, before its push; nothing else is attacked per slice. Converge, the adversary pass and mutation
   still run here, over the whole capability, in every mode: what slices get wrong between them is something
   no slice's own pass could read. Read the mode once, at the merge rung, as the merge does."""


def open_mode_note(where: str) -> str:
    """One sentence for a per-slice rung that keeps its old work under `open`, naming what it keeps."""
    return f"""Under the `open` release mode (*Capability gates* says when that is), {where}."""


def capability_gates_stage(web: bool) -> str:
    """The `**Capability gates**` rung, as one item of the ladder's numbered list (three-space continuation).

    It sits where the mutation gate sat, before the merge, because what a slice records here is which run it
    waits for; the run itself is the capability's. `web` adds the design review, which needs a screen.
    """
    design = (
        """
   3. **Design review** over every screen the capability's slices added or changed: render each in the running
      app, reached the way `skills/run-the-app` records, put it into every state it can be in, screenshot each
      under `""" + RECORD + """design/`, and read the screenshots — not the source — against the approved mock
      state, `docs/design.md` and the constitution's design notes, and `skills/web-interface-guidelines`,
      doing what an extension block in `AGENTS.md` adds to this rung as well. Look for what a check cannot
      see: browser defaults anywhere, a label crammed against its field, a value the actor was never meant to
      read, a figure with no labels, an empty state with nothing in it, one thing styled two ways — and what
      the slices' own screen design recorded for this reading rather than fixing. Each screen gets a
      `Reviewed:` line in the record naming its screenshots and what was fixed or left with a reason."""
        if web
        else """
   3. **Design review** — this project has no browser app, so the record says `No screen` and moves on."""
    )
    return f"""**Capability gates** — the slice's capability has a cleared `{GATES_FILE}`, or this slice says
   which capability it belongs to and that it is not that capability's last. The gates run **once per
   capability, not per slice**: when a capability's last slice has merged (`python3 scripts/agents/capabilities.py`
   says *gates due*) and before the person's demo stop walks it — under the `keystone` release mode on the last
   slice's branch before its merge instead, because that merge is the one that lights the entry point. In this
   order, each over every file the capability's slices changed since the first of them branched:

{convergence_gate()}
   2. **Gaps** — `/gaps` over the capability's whole diff, delegated to `sail-gaps-lookout`: every promise in
      the capability's slices traced to an observable test and a reachable production path, run after the
      converged verdict and never before it. This is the completion audit; the pass before planning stays
      per slice.{design}
   4. **Adversary** — one `/adversary` pass over the capability's surface, **only where at least one of its
      slices' trigger records has a trigger `widened`**, or the capability was given `--full`; its row in
      `specs/<feature>/adversary-log.md` is headed by the capability rather than a slice. It attacks every
      seam the slices widened, alone and together — a seam one slice opened and the next one reached. Where
      no slice widened anything, the gate writes a skip row naming the trigger records it relied on, and the
      skip clears it. A seam a slice's own pass already attacked under `open` is cited rather than probed
      again, unless a later slice changed it.
   5. **Mutation** — `/mutation` over every production file the capability's slices changed, bounded by the
      `mutation-shipworm` budget in `harbour.json`: a run that reaches the budget is killed, its process tree
      and nothing else, and records a qualified receipt naming the scope it covered and the scope it did not,
      never a score. A score at or above the project's threshold is the gate; under it, the survivors are
      closed. Per slice it took hours apiece and was taken out of one loop by hand.
   6. **The hand's walk** — `sail-demo-hand` walks every example of every slice in the capability, in split
      order, against the running app, and records its verdict in the capability's `demo-log.md`. This is the
      walk the person's demo will repeat, so it is the one worth a browser.

   Findings and open convergence tasks at or above the fairway's severity bar are fixed **before the person's
   demo**, in a follow-up slice in the same fairway named for the capability, through failing tests like any
   other work; those below it are stowed to the careen; an open `CRITICAL` is the next slice, whatever else is ready. When all six have
   run and nothing above the bar is open, the record's last line is `Cleared: <date> · <commit>`, and the
   person's demo is due. Nothing is carried: a gap left here is a gap the next capability inherits.

   {OPEN_MODE}"""
