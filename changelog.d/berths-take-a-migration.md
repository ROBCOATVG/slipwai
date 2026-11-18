PATCH

**A slice in flight takes a migration before its next session.** A slice's worktree met trunk only when the
slice merged, so one already running when `slipwai migrate` landed kept the scripts and the ladder it was cut
with for the rest of its life: after lean-coffee-club's migration on 2026-11-18, the one slice cut afterwards
had the new rules and the four in flight did not, until trunk was merged into each by hand. Now the captain,
before it starts a session in a worktree, merges trunk into it where trunk's `generator` in `project.json`
has moved on from the worktree's, and projects the agent files again. Only a migration is taken, never a
sibling's work. A merge that conflicts is abandoned and said in the captain's output, and the slice runs on
what it has until it merges.

**Catch-up:** `slipwai migrate` carries `scripts/agents/moorings.py` and `captain.py`. Push the migration and
start the fleet again (`make cruise-stop`, `make cruise`): a running captain keeps the code it started with.
