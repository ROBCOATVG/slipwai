PATCH

**A slice's worktree left in the middle of a rebase is put back on its branch.** A session rebasing its
slice when the fleet is stopped leaves the worktree on a detached HEAD with the rebase open. Nothing then
had the branch checked out, the folder stood in the way of a new worktree, and the slice parked for a person
to move it or check the branch out. The open rebase is aborted, which leaves the branch as the session last
committed it; the harbourmaster rebases at the merge.

**Catch-up:** `slipwai migrate` carries `scripts/agents/moorings.py`. Nothing to change in a project.

**A freed slot is taken, and a cleared slice is carried on, while the turn is still running.** Two faults
left a cleared slice unstarted beside a free slot until the fleet was stopped. A `slots` line that already
counted the ended slice out was read as the number from before it whenever the harbourmaster wrote it ahead
of the captain's own `merged`, so the stream stayed at the sessions it had. And a park that names its slice
only at the head of its why, as a captain's own park of one slice does, was not recognised once cleared.

**Catch-up:** `slipwai migrate` carries `scripts/agents/captain.py`. Nothing to change in a project.
