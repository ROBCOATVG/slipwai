"""The convergence rung of `commands/drive.md`: the one stage whose exit condition is a judgement, and the
bounds that keep it a stage rather than a loop.

Its own module for the reason `demo_stop.py` is: the text has grown by evidence, and each addition is a slice
that paid for its absence. The class-not-instance rule came from six passes closing a sibling each. The
bound, the severity floor and the level list came from a slice whose convergence and rework cost 12.9 times
its implementation — every finding real, one pass running 5h47m unbounded, four passes each looking one
abstraction level further out than the last, six MEDIUM tasks each re-opening the loop. The clean-tree check
and the lead-not-finding rule came from a pass stopped mid-mutation: the tree was left mutated with nothing
announcing it, and the pass's last line became a HIGH task and a waiver before anyone re-ran it and found
that the mutant dies.
"""
from __future__ import annotations

# Passes after which the loop stops by default and what is still open goes to Phase 4. One pass finds the
# work and one confirms it closed; a third is a decision somebody takes, not what the wording produces.
PASSES = "two"
# Every level a first pass is asked to account for, so the follow-on passes that would each look one level
# further out are one pass. Named once, so the ladder and the converge brief cannot list them differently.
LEVELS = ("domain", "use case", "delivery adapter", "screen", "published contract")


def levels() -> str:
    return ", ".join(LEVELS)


def convergence_stage() -> str:
    """The `**Convergence**` rung, as one item of the ladder's numbered list (three-space continuation)."""
    return f"""**Convergence** — `tasks.md` records a converged verdict for the current commit and has no
   unchecked convergence task. Otherwise run the installed Spec Kit converge command, implement whatever it
   appends, and repeat — until it reports converged, or until the loop reaches its bound, whichever is first.
   Record that verdict under a `## Convergence` heading so this stage is not re-run, then `/gaps` over the
   slice diff. The verdict names each constitution principle the diff touches — a MUST about money, time,
   identity, a boundary — with the file and line that satisfies it; "no constitution obligation unmet" as one
   sentence is not a verdict, and a slice has shipped a float in a monetary column under exactly that
   sentence. Converge is append-only — its one write is new tasks — so repeating it is safe. A Spec Kit
   install with no converge command is a skip with a stated reason, not a stop.

   **The loop has a bound, because its exit condition is the judgement of the thing being looped.** Every
   other rung ends on something an outside reader can evaluate — a file exists, tasks are ticked, a gate is
   green. This one ends on the opinion of a fresh strong model asked to find what is missing, and asked that,
   it will find something: at any level there is a level further out. So: at most {PASSES} passes by default —
   one to find the work, one to confirm it closed. A pass beyond that is a decision this session takes and
   says why, never what this wording produces — with one exception the bound does not hold against: **an
   open `CRITICAL` finding re-opens the loop however many passes have run**, because a slice does not go to
   its demo carrying one. When the bound is reached, whatever is still open and not `CRITICAL` is appended
   as Phase 4 tasks, the verdict says the loop stopped at its bound, and the slice goes to its demo: the
   actor's feedback is better evidence about whether the slice is right than a third reading of the same
   diff. Only a `CRITICAL` or `HIGH` finding re-opens the loop at all, and only a `CRITICAL` re-opens it past
   the bound; grade every appended task, and a `MEDIUM` or `LOW` rides along with the next pass or lands in
   Phase 4 rather than costing a pass-and-fix cycle of its own. Hand the **first** pass the level list and ask it to account for each —
   {levels()} — because four passes on one slice each looked exactly one level further out than the
   last, and asked for all of them at once they are one pass. Give each pass a stated budget in its brief and
   take what it has found when it reaches it: an incomplete verdict with three findings is worth more than a
   complete one nobody waited for.

   **After every pass — including one that was stopped — the tree is clean before anything else runs.**
   Converge proves a finding by mutating the code and restoring it, and a pass stopped mid-mutation leaves
   the mutation in place with nothing announcing it; the next thing on this ladder is the demo, which would
   show the actor the mutation. `git status` is two seconds against that. And **a finding from a pass that
   did not finish is a lead, not a finding**: a stop notification's last line is a fragment of work in
   progress, and what was in progress was checking. Re-run its reproduction before it is written into
   `tasks.md`, a waiver or anything outside this session — one mutation, one test run, one restore — and
   until then write it as *a stopped pass believed X; verify before acting*. One such line became a HIGH
   task, a waiver and a published finding within the hour, and the mutant died when somebody re-ran it.

   **Each appended task closes the class, not the instance it was found at.** Where a finding sits on a
   repeated surface — a field in a parser, a row in a route table, one screen of a pair, one array cap in a
   decoder, one column of a field table — the task's GREEN names the sweep rather than the example ("every
   field this parser validates", "both screens of the crossing", "every array this decoder bounds"), and the
   verdict records the sweep that was performed and what it found. A pass that validates one field and leaves
   its neighbour is a pass the next one repeats: six of them closing a sibling each is the same work as one
   closing the surface, at six times the price, and it is what writing the task as the example produces.
   Where the sweep is genuinely larger than the slice, say so in the verdict and leave a task naming the
   rest — that is a scope decision recorded, not a sibling found again next pass."""
