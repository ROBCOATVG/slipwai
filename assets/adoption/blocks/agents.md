## Delivery method (installed by slipwai {{version}})

This repository adopted the factory's delivery method: its material lives under `{{where}}`, beside
the code, and `project.json` records what was here and what was confirmed about it. Read
`{{where}}docs/adoption.md` first, then `{{where}}docs/convergence.md` — where this repository
stands on each ladder a generated project sits at the top of; a rung is claimed only from a fact, an
`unrecorded` row is a question to ask, and `project.json`'s `convergence` is where an answer is written. The
gate is `{{make}} verify`; the skills are under
`{{where}}skills/` and the commands under `{{where}}commands/` (`{{make}} agents`
projects them into your harness). The rules in `{{where}}docs/architecture.md` bind code the factory
generates; existing code is held to its own recorded commands and to nothing it did not have before. Change
what `project.json` says only by editing it deliberately, and never edit anything listed in
`{{where}}{{written}}` by hand — those files are the factory's, and `slipwai migrate` replaces them.

**Tests written here** — for new code and for code that was here alike — stand in at a seam with a fake
written in the test tree, a class or function implementing the real interface, never with a mocking framework
this repository would have to add: Mockito, Moq, gomock, `unittest.mock` and `jest.mock` are the same last
resort in every language, and "what should I add?" is never answered with one. Where the test framework that
was here is out of support — JUnit 3 or 4, nose, a runner nobody maintains — new tests use the ecosystem's
*current* framework and keep the old tests running beside them (JUnit 5 through its vintage engine; pytest
runs `unittest` suites as they are), as a slice on the map's Platform row: never the next-oldest version,
never an upgrade decided in passing.

**One pull request per slice.** The adoption commit merges alone, before any slice; each slice is its own pull
request, and a slice's after-acceptance commits — the adversary pass, the archive — ride in its own PR, never
the next one's. A first PR of five slices and 566 files was reviewed by nobody, and a framework's major version
moved inside it unseen.
