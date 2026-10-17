MINOR

**A slice's dispatch line travels in the slice's own pull request, and starting or merging a slice records
itself.** From one `/sail` run with five slices in flight on a trunk that only moves through pull requests:

- `make dispatch` writes each slice its own ledger file, `.slipwai/dispatch/<feature>/<slice>.jsonl`, into
  the slice's worktree as well as here where the worktree exists, and `check-slice-scope` lets a
  `slice/<id>` branch commit its own file and no other. A line no longer has to reach trunk in a records
  pull request before the slice that names it can pass `check-dispatch`, and five branches no longer append
  to one file that conflicts at its last line.
- `make dispatch` writes the `claimed` deck-log line for every slice it starts, and takes
  `DISPATCH_FLAGS="--slice <id>[,<id>]"` to start only the slices `/sail <slice-id>` names, saying
  clearance's reason for any named slice that may not start.
- Clearance counts a slice with a `dispatched` or `taken-here` ledger line as running even with no `claimed`
  line, and reads a slice as done when a first-parent merge on trunk names its `slice/<id>` branch — the
  subject a forge writes for a pull request, which survives the branch being deleted — so nobody writes
  `merged` lines by hand. A claim for the `prepare` band is spent once the slice's marks are set, so a
  prepared slice waiting for its implementation slot holds none.
- `disk_floor_gb` in `harbour.json` holds every slot while the checkout's disk has less free than that, and
  says how to free it.
- `check-speckit` names the integration to repair instead of `<integration>`, and says that a new worktree
  needs `make agents` first. `sail-slice-watch` says a delegate that cannot start one of its own hands the
  fresh-context diff review back to the host rather than looking for a tool it has not got.

**Catch-up:** `slipwai upgrade`, then `make agents`. Lines already in `.slipwai/dispatch/<feature>.jsonl`
keep counting; nothing moves them.
