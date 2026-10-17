MINOR

**A whole capability now gets six readings in one Capability gates rung, and a slice keeps only what it can answer alone.**
The rung replaces the *Mutation gate*. It runs when a capability's last slice has merged and before the
person's demo, in this order:

1. converge over the capability's whole diff, against the specification and every slice's tasks
2. `/gaps` over that diff
3. the design review from screenshots
4. one `/adversary` pass, only where a slice widened a trigger
5. `/mutation`
6. `sail-demo-hand` walking every example of every slice

**Convergence no longer runs per slice.** It asks whether the code does what the specification requires, and
that has its answer only once the slices sharing a requirement are all built. Its two-pass limit, its
re-open rules, the clean-tree rule and the "close the class, not the instance" rule govern the capability
gate unchanged.

**No slice is attacked.** The *Adversary* rung is now *Attack surface*. It writes the slice's trigger table
(identity and money rows added) under a heading ending `trigger record`, and `make check-decisions` accepts
that as the slice's row. The capability is attacked only where at least one slice widened a trigger, or with
`--full`. Otherwise the gate writes a skip naming the tables it relied on, and the skip clears the gate.
**The full pass the slice closing a feature's split used to take is gone.**

**What stays per slice is scoped to what the slice added or changed.** Screen design covers only its own
screens and the elements it changes. The review reads the diff against the merge base, and its findings point
only at added or changed lines. Anything about untouched code is noted for the capability or stowed, never
fixed in the slice, and the reshape refactors only the slice's own lines. The *Demo* rung no longer opens a
browser. Each example is recorded under `## Examples proven` in `tasks.md` against the test that proves it,
and that record gates the push.

The record is `specs/<feature>/capabilities/<capability>/gates.md`. It holds `## Convergence`, `Reviewed:`
lines and a final `Cleared:` line. `scripts/agents/capabilities.py --gates` lists capabilities owed their
gates, and `--due` lists a demo only once they clear. Findings and open convergence tasks at or above the bar
are fixed in a follow-up slice in the same fairway before the demo. Those below it go to the careen.

**Under the `open` release mode**, where a merge reaches the actor at once, converge, the gaps trace, the design
review and the hand's walk run per slice as well. A slice that widened authorisation, identity or money is
attacked before its push, because anything not covered would be live rather than dark. The capability's
converge, adversary pass and mutation still run. Under `keystone` the gates run on the capability's last slice
before its merge.

**Catch-up:** `slipwai migrate` brings the ladder in `commands/sail.md`, `commands/adversary.md`,
`commands/gaps.md`, the hand, lookout, privateer, navigator, mate, slice-watch and quartermaster briefs,
`.specify/extensions.yml`, `scripts/agents/capabilities.py`, `scripts/check-decisions.py` and the tasks
template. Then run `make agents` so the harness gets the new command and brief text. A slice already past
implementation finishes the old way. From the next slice on, skip its convergence, record its examples
proven, and write its adversary row as a trigger record. A capability whose last slice merged before you
upgraded owes its gates before its demo: run `python3 scripts/agents/capabilities.py --gates` to see which.
