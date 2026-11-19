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
branches — so the point is the capability: its gates run on its last slice's branch, before that
slice merges (the harbourmaster refuses the merge until they have cleared), and before the demo stop accepts it.

What stays per slice is what only a slice can answer, scoped to what the slice added or changed: screen design
for its own screens, one review of its own diff, its examples proven by its own tests, its story seeded green
against the app its berth runs, and the record of which attack-surface triggers it widened — a record, not an
attack. **The showing is per slice and the readings are per capability**: a slice's story seeding green and
Try it following trunk are what make each observable reachable the moment it merges, and these readings are
what make the whole fit to accept; neither stands in for the other (feedback-points plan, D1). Convergence is not one of them since 2026-10-17: it is the
first capability gate, because what it asks — does the code do what the specification requires — has its
answer only once the slices that share the requirement are all built. **No release mode reads each slice** since 2026-11-18: `open` did, because its merges are
visible, but `open` is what a pre-launch product merges under and nobody is using one of those — the
protection was for users the state says do not exist yet, and it made the earliest stage of a product the
dearest to build. A project whose merges do reach somebody at once asks for it, `"readings": "slice"` in
`harbour.json`, and then converge, the gaps trace, the design review and the hand's walk run per slice and a
slice that widened authorisation, identity or money is attacked before its push — except a slice that only
shows. The capability runs converge, the adversary pass and mutation over the whole either way, the adversary
pass, as always, only where a slice widened something.
"""
from __future__ import annotations

from .converge_stage import convergence_gate

#: Where a capability's gate record lives: one directory per capability, beside the slices it gathers.
RECORD = "specs/<feature>/capabilities/<capability>/"
#: The record itself. Its last line is `Cleared:`, which is what `capabilities.py` reads to call a demo due.
GATES_FILE = RECORD + "gates.md"
#: The readings, in the order they run: each one's fixes are code the next one should see.
GATES = ("converge", "gaps", "design review", "adversary", "mutation", "the hand's walk")
#: The readings that run per slice where `harbour.json` says `"readings": "slice"`.
OPEN_PER_SLICE = ("converge", "gaps", "design review", "the hand's walk")
#: The readings that run over the whole capability whatever `readings` says.
EVERY_MODE = ("converge", "adversary", "mutation")
#: What a slice's row in the adversary log is headed, so `check-decisions` reads it as that slice's row.
TRIGGER_ROW = "## <slice-id> · <commit> · <date> · trigger record"
#: What the capability's row is headed when no slice widened anything and nothing was attacked.
SKIP_ROW = "## <capability> · <commit> · <date> · skipped: no slice widened a trigger"

OPEN_MODE = """**Nothing is read per slice unless the project asks for it.** The six gates above run once, over the
   whole capability, in every release mode — `open` among them. A pre-launch product merges visible and to
   nobody: no one uses it yet, trunk is the team's own demo, and a capability is read whole before anybody is
   asked to accept it. lean-coffee-club read every slice because its merges were visible, and its first
   screen was converged, attacked and walked five times before a second slice existed to stand beside it.
   **A project reads each slice by saying so** — `"readings": "slice"` in `harbour.json`, for a product whose
   merges do reach somebody at once with nothing holding a slice back. Then four of the gates do not wait:
   converge, the gaps trace, the design review and the hand's walk run per slice, over the slice's diff
   and examples: converge and then `/gaps` at the end of *Implementation*, the design
   review after it, the hand at the *Demo* rung, each recorded in the slice's own folder. The *Attack
   surface* rung also attacks a slice whose record has the authorisation, identity or money trigger
   `widened`, before its push; nothing else is attacked per slice. **A slice that only shows takes none of
   the four** even then: its pattern is `state-view`, or on the standard profile its split row names no
   command, and its diff adds no command, no event, no route that writes and no migration. Converge, the
   adversary pass and mutation still run here, over the whole capability: what slices get wrong between
   them is something no slice's own pass could read. Read `readings` once, at the slice's *Implementation*
   rung, and say in `tasks.md` which it was; absent, it is `capability`."""


def open_mode_note(where: str) -> str:
    """One sentence for a per-slice rung that keeps its old work where the project reads each slice, naming what it keeps."""
    return f"""Where the project reads each slice (`"readings": "slice"` in `harbour.json`; *Capability gates* says what that is for), {where}."""


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
   capability, not per slice**: on the capability's last slice's branch, before that slice merges, and before the
   demo stop accepts it. The harbourmaster refuses the merge that would make a capability whole until its
   `{GATES_FILE}` says `Cleared:` on that branch, in every release mode — under `keystone` that merge is also the
   one that lights the entry point. A capability that is whole already with no cleared record
   (`python3 scripts/agents/capabilities.py` says *gates due*) has them run now, on trunk. In this order, each
   over every file the capability's slices changed since the first of them branched:

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
      skip clears it. A seam a slice's own pass already attacked where the project reads each slice is cited rather than probed
      again, unless a later slice changed it.
   5. **Mutation** — `/mutation` over every production file the capability's slices changed, bounded by the
      `mutation-shipworm` budget in `harbour.json`: a run that reaches the budget is killed, its process tree
      and nothing else, and records a qualified receipt naming the scope it covered and the scope it did not,
      never a score. A score at or above the project's threshold is the gate; under it, the survivors are
      closed. Per slice it took hours apiece and was taken out of one loop by hand.
   6. **The hand's walk** — `sail-demo-hand` walks every example of every slice in the capability, in split
      order, against the running app, and records its verdict in the capability's `demo-log.md`. Its verdict
      is the capability's acceptance under `demos: hand`, the default, and the reading a person accepts on
      under `person`, so it is the one worth a browser.

   Findings and open convergence tasks at or above the fairway's severity bar are fixed **before the
   capability is accepted**, in a follow-up slice in the same fairway named for the capability, through failing tests like any
   other work; those below it are stowed to the careen; an open `CRITICAL` is the next slice, whatever else is ready. When all six have
   run and nothing above the bar is open, the record's last line is `Cleared: <date> · <commit>`, and the
   demo stop is due. Nothing is carried: a gap left here is a gap the next capability inherits.

   {OPEN_MODE}"""
