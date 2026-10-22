MINOR

**The harbourmaster ticks a park's needs against trunk, and clears the park when the last one lands.** On
every pass it reads each open park's `needs`: a `text` check is a file on trunk holding a string, read with
`git show` so a berth's uncommitted edit never counts; a `make` check is a `check-*` target (or one listed
under `checks` in `harbour.json`) passing in a worktree at trunk, bounded by `wait_bound` and run once per
trunk commit. Each tick is a `need-met` receipt in the harbour log. A need only a person can tell is ticked
from the board, which writes a `need-done` deck line. When every need has its receipt the park is cleared
with nobody asked.

**Catch-up:** `slipwai upgrade` carries the new `scripts/agents/harbourmaster.py` and `logs.py`.
