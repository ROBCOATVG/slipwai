PATCH

**The rest of the rules that were stated two ways now say one thing.**

- **Where a keystone entry is declared.** The *Release constraint* rung said the chart names it under
  `entry:`. `check-slice-scope` reads `specs/<feature>/keystones.yaml`, as `/chart` says, and the rung now
  says so.
- **What a slice may write.** `/sail`'s list ended "Nothing else" and left out the slice's own flag line in
  `infra/service/flags.auto.tfvars`, which the gate allows and the method asks for in the same change as the
  code that reads it. A slice handed that line back and parked. The list and the slice-watch brief name it.
- **Parallel tasks inside a slice.** The tasks template said a slice's Phase 3 has none "by construction",
  which `/sail` itself calls a tasks list that under-reports. It now says what the tasks brief says: `[P]`
  where a task's files are disjoint from its siblings'.
- **Session handovers.** A session a captain dispatches is told to end its turn after `tasks.md` and after
  the review. `AGENTS.md` and `/sail` said never to stop there, and `AGENTS.md` says it wins. Both now name
  the exception.
- **Who accepts a capability.** Four places ended the gates with "then the person's demo". The default is
  `demos: hand`, where the hand's verdict accepts it and nobody is stopped; the first-feature guide still
  showed a per-slice "accept this? [y/n]".
- **The converge hook** said to converge "until it reports converged". The bound is two passes.
- **The harbourmaster's brief** said both that `fix-trunk` is no longer written and to send it; and that the
  telegraph sets each stage's model role, which it does not.
- The workflow page said each task keeps `make verify` green; it is the quick tests, and the full gate runs
  once before the push. `/sail` said "six stages" above a table of seven.

**Catch-up:** `slipwai migrate` carries the pages, briefs and the template.
