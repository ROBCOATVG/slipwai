MINOR

**`/clearance` and `/claim` ask from the session what a person used to ask from a shell, and the guides show the slash command wherever a person types the step.** `/clearance` runs `scripts/agents/clearance.py` and reads back which slices may start and what each blocked one waits on. `/claim <fairway>` takes a fairway's claim for this machine, `/claim release <fairway>` gives it back, and `/claim` alone says who holds each. Both read and report; a refused claim is repeated, never forced.

The guides and the generated README now show `/verify`, `/verify <gate>`, `/cruise-status`, `/cruise-status <fairway>`, `/clearance`, `/claim`, `/draft`, `/cruise-settings` and `/add-service` where they used to show `make verify`, `slipwai fleet`, `python3 scripts/agents/…` or a terminal `make cruise-tell` as a step to type. A `make` target that a command, a stage or the board runs is still named as what runs underneath. `make test-docs` reads a `> /command` line in a transcript as a command typed into the agent: it runs what the command runs, holds the page's output to it, and holds the command's own page to running it.

**Catch-up:** `slipwai migrate` brings `commands/clearance.md` and `commands/claim.md`; run `make agents` so the harness projects them.
