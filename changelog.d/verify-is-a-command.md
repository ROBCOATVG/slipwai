MINOR

**`/verify` runs the project's gates from the session and reads the result back.** It runs `make -k verify`, so one run names every gate that fails and not just the first, then says the verdict, quotes each failing gate's own line and what it asks for, and says what was skipped rather than passed. It reads and does not repair, and never edits a gate or a pinned record to make one pass.

The guides now lead with the slash commands wherever a person types the step — `/cruise`, `/cruise-status`, `/cruise-watch`, `/cruise-tell`, `/cruise-stop`, `/verify` — and no longer show a `make` target that `/sail` or the board runs for itself (`make arrive`, `make chart`, `make model`) as something to type. The generated README says `/cruise-stop`.

**Catch-up:** `slipwai migrate` brings `commands/verify.md`; run `make agents` so the harness projects it.
