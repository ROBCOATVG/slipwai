MINOR

**`make check-try` holds every slice's `try-it.json` to what it would need to seed, with no app running.**
Every story parses into the shape the Demo rung describes; every `as` names a person a realm or a
`specs/<feature>/people/` file declares; every `open` path starts with a route the browser app mounts; every
`given` event is one the model types. On recap's second day 22 of 22 stories failed at their first call —
seven as people nobody had declared, the rest on screens two unbuilt hubs would mount — and nothing had said
so before the merge. `verify` runs it.

**Catch-up:** `slipwai migrate` brings `scripts/check-try.py` and the `verify` line. A project whose stories
already name people nobody declared goes red at `check-try` on the first `make verify` after, and the
refusal prints the names: write each under `specs/<feature>/people/` and run `make verify` again. Never
soften the gate; the next migration brings it back.
