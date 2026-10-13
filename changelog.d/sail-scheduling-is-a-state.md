MINOR

**`/sail` schedules in two bands, and clearance says which.** The page said *run every ready slice whose
contract is settled*, and a slice settles its contract by preparing — so a host following the rule waited
on the one thing the wait was stopping, and two cleared slices with HTTP shapes still to decide sat idle
while their example maps, route drafts and gap reviews could all have run. Preparation (the example map,
the contract files, the gaps pass — the stages that write the slice's own `mark-set` lines) now needs
clearance alone; implementation (the plan onward) needs those lines written and no open question. The
`sail-slice-watch` delegate is handed a band — `prepare`, `implement` or `whole` — and returns at its end.

**Clearance is a state with a reason, not a yes.** `scripts/agents/clearance.py` answers for every slice
with one of eight states — `blocked`, `migration-evidence-required`, `awaiting-decision`,
`preparation-ready`, `implementation-ready`, `running`, `awaiting-demo`, `done` — and the sentence that
says why, and with a schedule: which slices start now and in which band, and for every eligible slice that
does not, the reason — no slot, claimed elsewhere, or *claims could not be read*, which starts nothing.
`--json` is still query version 1 — `ready` is there and means what it meant — with `states`, `schedule`,
`slots` and `claims` beside it, so a board built before this reads it as before.

**The ready set is recomputed at every boundary.** A delegate returning, a mark landing, a decision, a demo
verdict, a merge, a refused claim: each refills the free slots from a fresh read, and a host with a slot free
and eligible work waiting owes the reason in the line that names the ready set. A product question is a
`question` line in the deck log (`fairway`, `slice`, `id`, `what`), open until a `decision` carries the same
`id`; under `/sail` it is put to the person while the independent siblings keep running, and the sentence
says which slices the answer unblocks. A demo wait is the slice's own and never a sibling's.

**Nested agents and browser runs are counted.** A whole-slice delegate carrying `[P]` tasks is `1 + fanout`
agents, so the fan-out asks for up to `boilers × (1 + fanout)`, held to what the harness can actually run.
`browsers` is a new telegraph number — browser-driven test runs at once on this machine, 2 at `full-ahead`
and 1 below — because several worktrees are still one machine's CPU.

**A prerequisite that shipped before marks were logged is not *blocked*.** It is
`migration-evidence-required`, and `clearance.py --baseline-marks` records, once, a `mark-set` line for each
of its marks carrying `provenance: baseline` and what it was read from — distinguishable from an earned
mark by any reader, and refused a second time, exactly as `check-decisions.py --adversary-baseline` is.

**Catch-up:** `slipwai upgrade` carries the new `clearance.py`, `logs.py` and `telegraph.py` into
`scripts/agents/`, and `slipwai migrate` rewrites `commands/sail.md`, `commands/cruise.md` and
`agents/sail-slice-watch.md`. A project whose `harbour.json` predates `browsers` reads as *adjusted* until
`slipwai telegraph <position>` is rung once. A project whose shipped slices predate the mark log runs
`python3 scripts/agents/clearance.py --baseline-marks` once.
