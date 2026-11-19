PATCH

**A crossing from version 1 says, as it moves version 1's run files, exactly how to put them back.** The
crossing moves them into `.slipwai/run/v1/` and writes version 1's history into deck logs under
`.slipwai/run/logs/`. Walking away — `git merge --abort`, or `git reset --hard ORIG_HEAD` — restores what
git tracks and version 1's `.gitignore`, which names neither place, so the files stayed where the crossing
put them and nothing said so. `slipwai migrate` now ends its report with one `mv` line for each file it
moved and one `rm` line for the deck logs it seeded, and the catch-up page carries the same under *If you
walk away from this crossing*. It does not guess that you walked away, and there is no verb that undoes part
of a crossing: the lines are yours to run.

**Catch-up:** nothing for a project that crossed and stayed. One that walked away from a crossing before this
version has the files under `.slipwai/run/v1/` still: for each, `mv .slipwai/run/v1/<name> <where version 1
wrote it>` — `specs/cruise-checkpoint.md`, and the rest under `.specify/`. Do that
before crossing again: a crossing reads version 1's history from where version 1 wrote it.
