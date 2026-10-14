MINOR

**A project with more than one deployable gets a fast target per deployable, and a mutation sandbox is
never discovered as tests.** `make unit` is one target over every deployable, which is right for the merge
and wrong for the increment: on one project every Go domain increment paid about ninety seconds of Vitest
for a browser suite it had not touched. The generated `Makefile` now writes `unit-<name>` per service and
per browser app, running that application's own fast checks and nothing else; the *Implementation* rung and
`sail-implement-shipwright`'s brief name it as the increment's gate, with `make unit` over all of them
still the slice's before its demo. And the generated `vite.config.ts` excludes `**/.stryker-tmp/**` from
Vitest's discovery, because a `make unit` that started while a mutation run was copying the app found 1,104
test files where there were 514 and failed every copied fixture on ENOENT.

**Catch-up:** `slipwai migrate` rewrites the `Makefile` and merges the Vite config; a project that edited
either resolves the merge as usual.
