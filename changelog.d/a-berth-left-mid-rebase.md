PATCH

**A slice's worktree left in the middle of a rebase is put back on its branch.** A session rebasing its
slice when the fleet is stopped leaves the worktree on a detached HEAD with the rebase open. Nothing then
had the branch checked out, the folder stood in the way of a new worktree, and the slice parked for a person
to move it or check the branch out. The open rebase is aborted, which leaves the branch as the session last
committed it; the harbourmaster rebases at the merge.

**Catch-up:** `slipwai migrate` carries `scripts/agents/moorings.py`. Nothing to change in a project.
