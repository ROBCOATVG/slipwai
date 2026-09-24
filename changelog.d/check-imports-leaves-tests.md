PATCH

**`make check-imports` no longer reads a test of the domain as domain code.** The gate took any file with a
`domain/` or `application/` segment in its path for that layer, so a Decider spec at
`tests/domain/<context>.spec.ts` — exactly where `adversarial-testing` and `docs/event-modeling-to-code.md`
send it — was refused for importing its test runner ("domain imports 'vitest' — only zod may be imported
here"), and so was a test beside the Decider (`decider.test.ts`, `decider_test.go`, `test_decider.py`,
`DeciderTest.java`) that named a fake adapter. Test directories (`test/`, `tests/`, `__tests__/`) and test
files are now left to the level they are; the layer itself is held exactly as before. The path is also read
relative to `apps/` and `packages/`, so a checkout that happens to sit under a directory called `domain` no
longer turns every file into domain code.
