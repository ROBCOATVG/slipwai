MINOR

**A conflict at a merge is settled where the rebase stopped, and a capability's last slice can record its own
gates.** A project's second feature, five slices at once, was refused 53 times for 34 merges. Three causes
are answered here.

- *The feature's record files are woven.* `decisions.md`, `adversary-log.md` and `benchmark.md` are added to
  by every slice. The rule for them held only a commit that added to the very end of the file and changed
  nothing else; a slice that reworded a line of its own entry in the same commit was refused. Now the
  commit's changes and trunk's are both applied wherever they do not touch the same lines, and two additions
  at one place are both kept, trunk's first. Only the same lines changed two ways is still a conflict.
- *Any other conflict is the mender's before it is the slice's.* Under `/cruise`, one bounded session of
  `agents/harbour-trunk-mender.md` runs in the harbourmaster's scratch worktree, mid-rebase, on the files git
  stopped on — code included, and a rendered file such as the draw.io canvas by its `make` target. It is held
  mechanically: the rebase must be where it was left, no other file may have changed, and no conflict marker
  may remain. The whole gate runs on the result. Where the mender does not settle it, the merge is refused as
  before, with the reason, and the slice resolves it in its own worktree. Each session is a `mend` line and
  its outcome in the harbour log, job `conflict`. `harbour.json`'s `conflict_minutes` bounds it (15 where
  unsaid); `0` turns it off.
- *A capability's record is its slices' to write.* The harbourmaster holds the merge that makes a capability
  whole until `specs/<feature>/capabilities/<capability>/gates.md` says `Cleared:` on that slice's branch,
  and `check-slice-scope` refused that path to every slice, so each one handed the record back and was
  refused until the mender had landed it on trunk. A slice may now write its own capability's folder, under
  the feature that capability's slices are under, and is told that path where it wrote another.

**Catch-up:** `slipwai migrate` carries `scripts/agents/conflicts.py`, `harbourmaster.py`, `mender.py`,
`scripts/check-slice-scope.py` and `agents/harbour-trunk-mender.md`. Nothing to change in a project. A
project that wants every conflict to go back to its slice sets `"conflict_minutes": 0` in `harbour.json`.
