---
description: Pin the current behaviour of the code a slice is about to change, at the seam where it can be observed, before changing it
argument-hint: <the behaviour about to change, and where it is observed>
---

# Characterise

Read `skills/characterisation-tests/SKILL.md` and `skills/finding-seams/SKILL.md`. This command scopes them
to one behaviour: the one a slice is about to change. It is the Pin step of adopting the method around code
that existed before it (`docs/adoption.md`) — tests that record what the code does now, including what is
ugly, so that a change can be told apart from a regression.

## Refuse "full coverage first"

If `$ARGUMENTS` is empty, or names the whole system — "everything", "the service", "all of it" — stop and
ask: which behaviour is about to change, and for whom? Characterising a whole legacy system before touching
it is where these programmes die. A behaviour is pinned because a slice needs it pinned, and the slice names
it; the answer is the argument to run this command again with.

## Find the seam

Observe; do not restructure. The seam is the boundary where the current behaviour can be recorded without
changing the code: the HTTP boundary (request in, response out), the database (the rows a use case writes),
the messages it emits, the files it writes, the reports it produces. Prefer the widest seam that stays
deterministic. Where nothing is deterministic — time, generated ids, ordering — `finding-seams` says how to
introduce the smallest seam that makes it so, and that seam is itself a change to record in the ledger.

## Doubles are fakes you write, not a framework you add

What stands in for the outside world at the seam is never a mocking framework. A collaborator that has to be
replaced — a clock, a repository, a gateway to another system — is replaced by a **fake**: a small
implementation of its real interface, written in the test tree, that holds state and answers from it
(`skills/hexagonal-architecture/resources/testing-hex-arch.md`, "Fakes, Not Mocks"). A test that asserts
which methods were called, in what order, with what arguments, records the code's shape and not its
behaviour, and breaks on exactly the refactoring it exists to make safe. So this command never adds
Mockito, Moq, gomock, `unittest.mock`, `jest.mock` or `vi.mock` to a repository and never recommends one:
the skills it reads show their last-resort module seam in Vitest, and that seam's counterpart in another
language is the same last resort, not the first move. A repository that already has such a framework keeps
the tests it has; the pinned tests are written without it. A repository with no tests at all gets its
ecosystem's own runner — JUnit 5, pytest, `go test`, `dotnet test`, `node --test` — and no second
dependency: that is the `tests-exist` rung, and it is one row in the ledger.

## Pin it

Write the characterisation tests in the application's own test tool, where its tests already are, so that the
recorded `test` command reaches them:

{{test-commands}}

Approval-style where the output is large. Record actual behaviour, never desired: a test that fails because
the code is wrong is written to pass, with a comment saying the behaviour is wrong and a question for the
person through `/gaps`. Run them, then `make verify`.

## Record it

Append one row to `{{ledger}}`: today's date, the behaviour, the seam, the test files, and the command that
runs them. Never rewrite an earlier row; a behaviour that is no longer pinned gets a new row saying so.

## Then

The pinned behaviour is what the slice may now change. `/sail` continues with the plan, and the
characterisation tests are the ones that keep passing until the plan says which of them change, and why.
