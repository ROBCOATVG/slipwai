PATCH

**The context answer is always written down, one context included.** A headless `/launch` once charted a
31-slice feature as one fairway with no seam test, no seam table and no decision entry. It wrote "one
context, so one fairway" into the split, and every slice queued behind one captain. The chart's pass one,
and Step 9 of the event model, now always record their answer as the next entry of
`specs/<feature>/decisions.md`. The entry is headed *Which bounded contexts does <feature> touch?* and
carries the seam table under its `Options`. A context of more than twelve slices also gets a `Why not
split:` line that cites, by requirement, the invariant spanning its groups. The count asks for that reason
to be written. It never asks for a split.

**With nobody present, the run proceeds and asks.** A session a script dispatched (`SLIPWAI_STAGE` set) no
longer takes its own proposal as confirmed. It proceeds on it, records it as `Decided by: host (stage
recommendation)` with the new `Status: awaiting human confirmation`, and posts a `question` line carrying the
entry's `D<n>`. The board's *Waiting on you* now shows open questions, so the question appears there. A
person confirms by setting the entry to `confirmed by human <date>`, which `check-decisions` accepts.

**`check-chart` refuses fairways nobody explained.** A chart with fairways and no context decision is
refused, and so is a decision with no seam table, or a fairway over twelve slices with no `Why not split`.
Each refusal says what to write.

**A stream states its invariant.** A stream is one expected-version check, and naming it after the spec's
noun ("one record per leaver") decided the feature's shape before any seam test ran. The model's new
`streams` block gives each stream a `because`, by requirement. `check-model` refuses a state-change slice
at `modelled` or later whose stream has none (`stream-states-its-invariant`). `nine-steps.md` now
interrogates every stream before naming it. It looks first for invariants that span groups of slices, which
keep them on one stream, and treats "one record per X" as uniqueness or a view rather than a boundary.
`scripts/agents/model.py` tells its headless session to run all of Step 9.

**Catch-up:** `slipwai migrate` brings the new gates and pages. After it, `make verify` refuses any feature
whose chart has fairways but no context decision, and any placed stream with no `because`. Before
upgrading a run in flight, add a `## D<n> — Which bounded contexts does <feature> touch?` entry with its
seam table to each charted feature's `decisions.md`, and a `streams:` block to `docs/event-model/model.yaml`.
Each refusal names exactly what is missing.
