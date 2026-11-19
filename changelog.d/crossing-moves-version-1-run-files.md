PATCH

**A crossing from version 1 moves that version's run files instead of leaving them to be committed.**
Version 1 ignored what its cruise wrote a name at a time — `.specify/cruise-run.log`,
`.specify/cruise-stream.jsonl`, `.specify/cruise-watch.cursor`, `specs/cruise-checkpoint.md` and five more —
and 2.1's `.gitignore` has one line, for `.slipwai/run/`. The files stayed where they were, no longer
ignored, and a `git add -A` while resolving the crossing's merge committed them: fifty-five thousand lines
of run log in one project. The crossing now moves each one git does not track to `.slipwai/run/v1/`, before
anybody is asked to resolve anything, and the catch-up page names what went where. Nothing is written over:
a file already at the new place is left and named. Until they have moved they never make a tree dirty and
are never staged with the projections.

**Catch-up:** `slipwai migrate` moves any that a project which has already crossed still has. Where a
crossing committed them, take them out yourself: `git rm --cached .specify/cruise-run.log
.specify/cruise-stream.jsonl .specify/cruise-watch.cursor specs/cruise-checkpoint.md`, commit, then migrate.
