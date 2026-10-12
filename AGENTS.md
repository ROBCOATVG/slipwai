# Work in this repository

This is the slipwai keel, being rebuilt as version 2. Read
[GLOSSARY.md](GLOSSARY.md) first: every name here comes from the slipway and the harbour, and nothing is
called a workstation, a workstream, a lane or a runner. The whole design is
[docs/slipwai-2-plan.md](docs/slipwai-2-plan.md); section 11 is the slice list, and section 8 is the rules
these are.

**Until 2.0.0 is cut, this repository keeps no version 1 working contract.** No `migrate`, no catch-up
notes, no changelog fragments, no bump arithmetic, and `VERSION` does not move. All of that comes back in
phase 8. If you are about to write a changelog entry, you are in the wrong phase.

## Two gates, not one

| When | What to run | Why |
|---|---|---|
| Every increment inside a slice | `make unit`, `make lint`, `make typecheck` | Seconds. Run them often enough that a break is one edit old |
| Once, before the merge to `main` | `make verify`, on the rebased branch | Lint, typecheck, structure and the whole suite |
| Every push and pull request | `make verify` again, in CI, on Linux, macOS and Windows | The platform legs, which a laptop cannot give you |

The full gate is never part of the inner loop. In version 1 one `make verify` did everything, and every
increment paid for the whole suite; that is the single most expensive habit the first attempt had. A test
that generates a project, shells out, or reaches the network goes in the `SLOW` list in the `Makefile` in
the same commit that adds it, so `make unit` stays worth running.

## The rules

These are section 8 of the plan. The first attempt paid for every one of them.

1. **Chart first.** Do not claim a slice until the marks it sets and the marks it steers by are on the
   chart.
2. **One slice is one pull request, a few hours, one module or one skill.**
3. **Fast checks inside the slice. The full gate before `main`.** The table above.
4. **Review and refactor before `main`.** A fresh-context review of the slice's diff and a refactor pass
   are stages, not favours. A slice merges with its review findings closed.
5. **Nothing merges red. Nothing merges with carried gaps.** Grant no standing exemption for an
   environment problem. Fix the environment, or exclude the test once, in writing.
6. **One adversary round. One convergence round beyond the first.** LOW findings go to the careen.
7. **Every stop records a reason. Every iteration writes to the log.** If a checkpoint is older than the
   last commit, delete it. Do not trust it.
8. **Declare the fork as a deployable in its own `project.json`** before any run of the factory on itself.
9. **Review decisions weekly.** The count of unreviewed decisions is a hard ceiling.
10. **People hold the merge to trunk** until phase 5's captain-enforced controls exist.
11. **Bring back. Never bulk copy.** Each module comes in by name, from a named source commit. Read it,
    rename it, and test it before the next one.

## Bringing a module back

Every module in version 2 comes from one of two commits, and the slice says which: upstream `main` at
`e1a9e43` (1.5.2.dev0), or `slipwai-cruise-2` `main` at `c6f1e74`. "New" means written for version 2.

1. **Read it where it is.** `git show e1a9e43:src/slipwai/<module>.py`. Understand why it is shaped the way
   it is before you move it.
2. **Rename it to the vocabulary as it lands.** Core becomes the keel, a language directory becomes
   `packages/`, a value stream becomes a fairway. A module that arrives with version 1's words keeps them
   for years.
3. **Give it a tier.** `scripts/check-structure.py` holds `TIERS`, and a module in no tier stops the gate.
   Add it to the tier it belongs to in the same commit, and keep its imports pointing inward.
4. **Leave nothing it needed behind.** If it imported something not back yet, either bring that too or
   say in the commit what was cut and which slice restores it.
5. **Test it before the next one.** The slice is not done because the module compiles.

## What the keel may not know

The keel names no language, no extension and no cloud. A `slipwai_language_*` or `slipwai_target_*` import
anywhere in `src/` fails the gate — including one deferred inside a function, which is still the keel
knowing a product. In the other direction, a package may import only the keel modules
[import-surface.txt](import-surface.txt) lists **for its kind**, and that file is held in both directions: a
line naming a module the keel has not got fails too. Adding a line to it is a promise that cannot be
withdrawn without breaking a package built somewhere this repository cannot see. The ceiling is twenty, and
it is twenty *per kind*: the file carries a section per kind of package — `[language]`, `[target]` — because
the number is about how far into the keel any one package may reach, which is the same question whichever
kind is asking, rather than a budget shared out between them.

## The skills, and where they live

There is one tracked copy of the skill catalogue, [assets/toolkit/skills](assets/toolkit/skills), which is
what a generated project receives. Phase 0 put a second copy under `.claude/skills/` so that sessions in
this fork had `tdd`, `testing`, `refactoring` and `find-gaps` from the first commit; slice 5.1 untracked
it, because two tracked copies of one catalogue drift and nothing afterwards says which is right. Run
`make skills` once in a fresh checkout to write the local copy, and edit the toolkit, never that copy.

A skill is written in version 2's words. `tests/test_skills.py` refuses a retired name — workstation,
workstream, lane, runner — in any skill that has not said which other sense it means; a test runner and an
event model's lanes are named there with their reasons, and a skill not on that list may not use the word
at all.

## The rename table

[docs/rename.json](docs/rename.json) is what `migrate` applies to a version 1 project before the three-way
merge (slice 8.3), so a person's edit to a renamed file lands in the file that replaced it rather than
conflicting. **Add the row in the slice that makes the rename, not before.** `tests/test_skills.py` holds
every row in both directions: the old name is gone from the tree and the new one is there. A row written
ahead of the code moves someone's file to a name version 2 has not got, and they find out at the merge.

## The small things that save a day

- **A slice that lands says so in a trailer.** End the commit that merges a slice with
  `Slice-done: <n>.<m>`, then run `make progress`: `scripts/progress.py` ticks the plan's tables from the
  history, so nothing is marked done that is not in it. A subject line that merely mentions a slice is not
  a trailer, deliberately — the first version of the ticker read subjects and marked a slice done whose
  work had not started.
- **`GLOSSARY.md` is written, not edited.** It comes from the plan's section 1 through
  `scripts/glossary.py`. Edit the plan, run `make glossary`, commit both.
- **The version lives in `VERSION` and nowhere else.** `pyproject.toml` reads it, the wheel carries it as
  `slipwai/_bundle/VERSION`, and `slipwai --version` prints it. Never repeat the number.
- **Deck logs and the harbour log are never committed.** `.slipwai/logs/` is ignored; the harbourmaster
  syncs them through `refs/slipwai/logs`.
- **Every refusal ends with the command that fixes it.** A gate that says what is wrong and not what to do
  about it costs the reader a search.
