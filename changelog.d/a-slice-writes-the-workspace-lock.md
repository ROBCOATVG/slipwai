MINOR

**A slice can add a dependency without stopping, and a park on something the fleet is already landing clears
itself.** Where a workspace keeps one lock at its root (`package-lock.json`, `pnpm-lock.yaml`, `uv.lock`),
that lock was the host's: a slice that needed a dependency handed it back, the mender landed it, and the slice
waited. The lock is derived from the manifests, so it is the slice's now, written in the same change as its
own service's manifest line. Where two slices' locks conflict in the harbourmaster's rebase, trunk's is taken
and the lock is written again from the merged manifests by its own tool; the gate runs on the result. And a
slice that parks on a need it has already handed to the fleet, with no check of its own, takes that hand-back's
check: the park clears when trunk has it, without a person saying what trunk already says.

**Catch-up:** `slipwai migrate` carries `scripts/agents/lockfiles.py`, `harbourmaster.py`,
`scripts/check-slice-scope.py` and the re-rendered `commands/sail.md`. Nothing to change in a project; a
workspace whose lock is not one of the three named still hands a dependency back as before.
