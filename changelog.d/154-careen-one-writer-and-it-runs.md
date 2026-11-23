MINOR

**What a slice stows reaches the careen, and the careen runs.** Before this, `/sail` and `/adversary` told a
slice to write its stowed findings into `fairways/<name>/careen.md`, and `check-slice-scope` refused a slice
that file. A slice wrote the rows, was refused, handed them back, and then conflicted with the mender's
landing of its own rows. On manda that cost S62 five merge attempts. Of 174 stowed rows, 41 reached a
careen, and one fairway had no careen file at all. Now a slice stows only into its capability's record,
`specs/<feature>/capabilities/<capability>/stowed.md`, which it may write, in the careen's row shape. On
every merge that brings such a record in, the harbourmaster appends its new rows to
`fairways/<fairway>/careen.md` under the capability's heading. It does this as a plain file operation in the
merge's own worktree, before the gate, so trunk moves once. A row already there is never added twice, and
the careen file is created where a fairway had none.

**The captain starts the careen as the fairway's last slice.** Once every planned slice of a fairway is merged
and its careen still has an open row, the captain starts `<fairway>-careen`, on `slice/<fairway>-careen`,
running `/careen <fairway>`. Before, it reported "every slice is claimed or merged" and stopped. This
happens whatever the release state. A pre-launch product hoists no flag, so a careen that waited "before
its flag is hoisted" never ran. The careen slice is the one slice `check-slice-scope` lets write its
fairway's `careen.md`, so it can close the rows. Its demo line, `deck_line.py demo --slice
<fairway>-careen --verdict accepted`, is the gate the captain merges it on. A fairway whose careen has no
open row ends as before.

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/careen.py`, the changed `harbourmaster.py`,
`captain.py` and `check-slice-scope.py`, and the reworded `commands/` and `agents/` pages. Rows a project
already stowed in a capability's `gates.md` under *Stowed*, or anywhere but a `stowed.md`, are not carried.
Move them into that capability's `stowed.md`, in the careen's row shape. The next merge that changes that
`stowed.md` carries them. Rows already in a `careen.md` without a capability heading are kept, and are not
added again.
