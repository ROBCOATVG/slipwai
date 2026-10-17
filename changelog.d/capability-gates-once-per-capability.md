MINOR

**A whole capability now gets six readings in one Capability gates rung, which replaces the Mutation gate.**
Three of them moved there from every slice: the gaps trace after code, the design review from screenshots,
and the hand's walk. Each reads something a slice only has part of: a promise two slices keep between them, a
screen a later slice finishes, a path that runs end to end only once the last slice lands. Read per slice,
each kept finding the next slice's missing piece. The rung runs when a capability's last slice has merged and
before the person's demo, in this order:

1. converge over the capability's whole diff, under the per-slice rung's bound of two passes
2. `/gaps` over that diff
3. the design review
4. one `/adversary` pass over what the slices widened together
5. `/mutation`
6. `sail-demo-hand` walking every example of every slice

The record is `specs/<feature>/capabilities/<capability>/gates.md`. Its `## Convergence` verdict names each
constitution principle the diff touches, and its `Cleared:` line is what `scripts/agents/capabilities.py`
reads. That script reports *gates due* first (`--gates`) and *a demo is due* (`--due`) only once the gates
clear. Findings and open convergence tasks at or above the bar are fixed in a follow-up slice in the same
fairway before the demo. Those below it go to the careen.

What a slice keeps: screen design before code, its own convergence (still two passes), one review of its
own diff, and an adversary pass where it widened identity, authority or money, or with `--full`. The trigger
table has identity and money rows for that. Any other slice writes a row ending `deferred to capability
<name>`, which `make check-decisions` accepts as its row. The *Demo* rung no longer opens a browser. Each
example in the slice's `examples.md` is recorded under `## Examples proven` in `tasks.md` against the test
that proves it, and that record gates the push.

**Under the `open` release mode**, where a merge reaches the actor at once, the gaps trace, design review and
walk run per slice as before. Every slice the adversary table owes is attacked, and nothing defers. The
capability's converge, adversary pass and mutation still run. Under `keystone` the gates run on the
capability's last slice before its merge.

**Catch-up:** `slipwai migrate` brings the ladder in `commands/sail.md`, `commands/adversary.md`,
`commands/gaps.md`, the hand, lookout, privateer and quartermaster briefs, `scripts/agents/capabilities.py`,
`scripts/check-decisions.py` and the tasks template. Then run `make agents` so the harness gets the new
command and brief text. A slice already past its *Demo* rung finishes the old way. From the next slice on,
record examples proven, and write the adversary row as a deferral where the table allows. A capability whose
last slice merged before you upgraded owes its gates before its demo: run `python3
scripts/agents/capabilities.py --gates` to see which.
