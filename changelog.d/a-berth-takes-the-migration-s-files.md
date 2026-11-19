PATCH

**A slice in flight takes a migration even where trunk's other work conflicts with its own.** The captain
brought a migration into a slice's worktree by merging the whole of trunk. The day after that shipped, three
of lean-coffee-club's five slices refused it: a sibling's merged code touched what the slice was writing, the
merge was abandoned, and those slices ran on the pages the migration had replaced. Now only the files the
migration changed are taken, as trunk has them, and committed in the worktree; a sibling's work is met at
the slice's own merge, as before, and the harbourmaster's rebase drops the commit because trunk already says
the same. A file of the migration that the slice changed itself is left as the slice has it, and the captain
names it.

**Catch-up:** `slipwai migrate` carries `scripts/agents/moorings.py`. Push the migration and start the fleet
again.
