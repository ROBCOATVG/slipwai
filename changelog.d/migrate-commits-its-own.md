PATCH

**`slipwai migrate` commits its own ignore rewrite, and never commits the run's state.** Two things went
wrong migrating a project a second time:

- A migration that stopped at a conflict rewrote `.gitignore` but did not stage it. Resolving the conflict
  left the rewrite behind, and the next `migrate` refused it as uncommitted. A clean migration with nothing
  to re-derive did the same. The rewrite is now staged where it is made, so whichever commit follows carries
  it.
- The projections commit staged everything, including run state left at the old place under `.slipwai/` in
  the rare case a newer copy was already in `.slipwai/run/`. One project's commit held six activity logs and
  nothing else. Anything under `.slipwai/` that is not a committed record is now taken back out before the
  commit.

**Catch-up:** nothing; it is the installed `slipwai` that runs `migrate`. A project that already committed
run state under `.slipwai/` can drop it with `git rm -r --cached .slipwai/<name>`.
