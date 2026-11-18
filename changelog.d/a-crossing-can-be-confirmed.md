PATCH

**A crossing from version 1 can be confirmed.** `python3 scripts/check-migration.py --confirm` could never
succeed on some projects, and until it does nothing can be claimed in the proposed fairways, so `/cruise`
and `/sail` could take no work. Two things were wrong:

- The crossing searched a story split's whole text for anything shaped like an id. Scenario, requirement and
  rule ids quoted in its notes (`CS-3`, `FR-006`, `V-10`) were listed as slices to place. It now reads a
  split's slices from the first column of its `## Slice graph` table, and from the `slices/` directories.
- On the event-modelling profile it listed slices only the split holds. The chart is rendered from the
  model, so those could never be placed. They are now left out of `unplaced` and named on the catch-up page,
  under *Slices the model does not hold*.

`--confirm` now judges the chart: it passes when no slice on the chart sits outside a named fairway. A name
the crossing listed that the chart does not hold is reported, not refused.

**Catch-up:** `slipwai migrate`, which brings the corrected `scripts/check-migration.py`. A project that
already crossed and could not confirm then runs `make chart` and `python3 scripts/check-migration.py
--confirm`: it passes once the chart has no `unplaced` slice, and prints the listed names it set aside.
