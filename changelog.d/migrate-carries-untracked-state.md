PATCH

**`slipwai migrate` no longer refuses a project over the run state it is about to move.** A 2.0 project can
have untracked `.slipwai/console/`, `.slipwai/stages/` and `.pid` files that the old ignore list missed.
`migrate` counted them as uncommitted changes and refused to start, even though moving them into
`.slipwai/run/` is part of what it does. Untracked files under `.slipwai/` no longer count. A new committed
record such as `hooks.json`, a changed tracked file, and anything outside `.slipwai/` still do.

**Catch-up:** nothing; it is the installed `slipwai` that runs `migrate`.
