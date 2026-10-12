PATCH

**The plan's gate holds its ticks and no longer its totals, so a slice branch can be green.** Two things of
different natures live in `docs/slipwai-2-plan.md` and only one of them survives concurrency.

A **Status cell** is per slice and disjoint: the branch that lands `10.1` ticks row `10.1` and no other
branch touches it. That is the same shape `check-slice-scope.py` already grants a slice over its own block
of `docs/event-model/model.yaml` — *every other slice's block reads exactly as on `main`* — and it merges
cleanly however many fairways are open.

The **`**Progress:` line** is one shared line every branch rewrites, because its totals count every slice
in the plan. That is exactly the conflict `changelog.d` was created to eliminate. Worse than conflicting,
it made the gate unpassable: a branch carrying one new `Slice-done:` trailer computes a different total
from trunk's, so `progress.py --check` went red, and the only way to green was to edit the one file every
other fairway was also holding.

So the totals stop being gated. They are rendered — like `docs/event-model/model.drawio`, which the host
regenerates after each merge. `make progress` still writes them. What is *held* to the history is the
ticks, which is what the plan is read for.

Found by running five fairways at once and watching every one of them go red on a line none of them was
allowed to own.

**Catch-up:** nothing. `make progress` is unchanged; only what `--check` refuses has narrowed.
