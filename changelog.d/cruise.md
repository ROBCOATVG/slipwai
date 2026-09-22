MINOR

**A generated project can now run `/drive` on its own until the specification is satisfied: `/cruise`.**
`/drive` stops for a product decision, an unavailable input, an exhausted split and the demo, because three of
those belong to a person. `/cruise` runs the same ladder with nobody at the wheel: it decides what the ladder
would have asked — on the host where the stage recommends an answer or a standing decision covers it, through
a new `drive-skipper` delegate where the question is open — runs each demo as the actor through a new
`drive-hand` delegate, with a browser where the slice has a screen, and audits the specification against what
shipped when the split runs out, so *done* means satisfied rather than exhausted. Every decision is written
where `/drive` would have written a person's and once more in `specs/<feature>/decisions.md`, every demo in
the slice's `demo-log.md`, and a person overturns either by editing it. A block is work before it is a stop: a third delegate, `drive-bosun`, stubs the
missing thing behind its port, takes the reading that keeps every MUST, or repairs the run, and writes down what
it did; a run parks only at the catastrophic — destroying, releasing, spending, weakening security — or when the
bosun could not move it. It stops for a human and for nothing
else: `scripts/agents/cruise.py run` (`make cruise`) re-invokes it with a fresh context until it says `done`,
parks when nothing can move, and detects a run that stopped making progress. `.specify/cruise.json` holds its
settings, `/cruise-settings` changes them checked, and it ships disabled: a project has to ask for this.
`.specify/models.json` gains a `skipper` role and the `skipper`, `hand` and `bosun` stages, and the benchmark records
`driver=cruise` on every stage a run bracketed.

**Catch-up.** `slipwai migrate` brings the command, the three agent types, the settings file and the two new rows
of `.specify/models.json`; then `./init` reprojects the agent types and, as with every new type, the harness
reads them at its next session start. Nothing runs until `enabled` is set with `/cruise-settings enabled=true`.
