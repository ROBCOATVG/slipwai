PATCH

**A merged slice's berth no longer stays on the machine because something was still running in it.** When a
slice merged with its dev server or an index daemon still writing into its worktree, git deleted the folder
while they wrote files back, failed with "Directory not empty" having already forgotten the worktree, and the
folder stayed beside the project for good: no tidy saw it again, and a later berth for that slice id was
refused as "already there and is not a worktree". Leaving a berth now stops the slice's own processes first —
the Try it processes its berth recorded, as whole process groups, and any process whose working directory is
inside the berth (read from `/proc`, or `lsof` on macOS; on Windows only the recorded ones) — then removes the
worktree, and removes outright whatever git leaves of the folder, since its tracked files were already shown
to hold nothing uncommitted. `fleet.py tidy`, and every cast-off, also sweeps the `<project>-<slice id>`
folders of merged slices that are no longer worktrees (never one holding a `.git`, never one of a slice that
has not merged), and removes the worktrees Claude Code made for delegated agents under `.claude/worktrees/`
whose commit trunk already holds, with their branches — never one git does not list, one with tracked edits
nobody committed, or one holding work trunk has not got; those are counted in one line.

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/moorings.py`; then `python3
scripts/agents/fleet.py tidy` clears what merged slices already left behind.
