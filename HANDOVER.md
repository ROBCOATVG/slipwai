# Handover — 2026-10-12

Written to be picked up on another machine. Everything below is on `origin/main` unless it says otherwise.

## Where the work is

Trunk is `main`. The branch `plan/phase-15-event-modelling-without-event-sourcing` points at the same
commit and is not a side branch — it is trunk's content under an older name.

Three captains were working in git worktrees under `.claude/worktrees/` when this was written. Their
branches are `worktree-agent-<id>`, pushed to `origin` so they travel. **A worktree does not travel; a
branch does.** On the other machine, `git fetch` and check out the branch — do not look for the worktree.

## What was done today

`make progress` says the count; the plan's own table is the record. Today landed, in order:

- the changelog read as UTF-8 (a Windows-only fault that had trunk red since 9 October)
- **15.13** a cross-service `reads` from a state-stored producer is refused until that service records
  `publishes` (`outbox` / `bus` / `cdc`) on its deployable
- **15.10** `observed`, a fifth slice status, for behaviour code already has and the model did not design
- **the plan's gate holds its ticks and no longer its totals** — the defect that made every concurrent
  captain's `make verify` red, because `--check` compared one shared line every branch rewrites
- **phases 12, 13 and 14 complete** — the harness plugin and MCP server, quickstarts, and the board
- **11.1, 11.3, 11.4** plus a real fix for a Windows `test_loop` flake
- **10.1, 10.2, 10.6** — the target protocol, the import surface sectioned per package kind, and
  `check-structure` refusing a keel module that names a cloud

## Decisions taken today, and where they are written

All of these are in `docs/slipwai-2-plan.md` section 9. Read them before contradicting them.

- **One ref per writer, and nothing is merged into one file.** The log sync is
  `refs/slipwai/logs/<fairway>` and `refs/slipwai/logs/harbour/<machine>`; a deck log's only writer is
  that fairway's captain and a harbour log's only writer is that machine's harbourmaster. Another
  machine's deck log lands *nowhere* locally — it is read from the ref. This cleared the park on 11.2.
- **`publishes` on a deployable in `project.json`** is how a state-stored service records that it can get
  an event across its own boundary. Absent on everything the keel generates, by design.
- **`observed` is confined to a service recorded `generated: false`**, because the status is exempt from
  `model-matches-code` and on generated code that exemption would be a way of never being asked.
- **The import surface has a section per package kind**, each with its own ceiling of twenty. The
  language section was already at twenty, so a flat list would have taken a target's first line out of a
  language's promise — and that promise cannot be withdrawn.

## What is open, by phase

Twenty-six slices. The plan's section 11 is authoritative; this is the shape of it.

| Phase | Open | Note |
|---|---|---|
| 10 | 10.3, 10.4, 10.5 | **10.3 and 10.4 are done on the captain's branch**, not yet merged |
| 11 | 11.2, 11.5 | 11.2 part-built; 11.5 rides on it |
| 15 | 15.8, 15.9, 15.11, 15.12 | 15.9 done on the captain's branch. **15.8 is not in this repo** |
| 7 | 7.7d, 7.11 | 7.7d's code half already landed at `94f3375`; 7.11 is new today |
| 3 | 3.4b | Must follow 10.3/10.4, or it is built in the keel and then moved |
| 9 | 9.2, 9.6, 9.7 | The plan puts docs late, deliberately |
| 8 | 8.3, 8.5, 8.6 | The release. Nothing in 8 starts before every other phase is done |
| 16 | 16.1–16.8 | **Must go last.** It names 27 modules and is a move, so it collides with everything |

## What can run in parallel

Phases 10, 11, 12, 13, 14 and 15 have disjoint file surfaces and were run concurrently today without a
single content conflict in the keel — every conflict was two captains appending to one registry list.

**Phase 16 cannot parallelise with anything.** It rewrites the modules every other phase edits.
**Phase 9 is late by its own reasoning**: a reference page written while the clouds are still leaving the
keel describes a system that will not exist by the time anybody reads it. **Phase 8 is last.**

## Open findings nobody owns yet

Found by captains, outside their own surface, and not fixed:

1. **`package_version.cut` is wrong for a snapshot.** `wanted = ... or source.version` takes the snapshot
   verbatim, so `slipwai package version .` writes `## 1.0.0.dev0`, which `version_rule` then refuses.
   One expression: use `versions.base()` where it is a snapshot.
2. **The language and extension scaffolds write `VERSION 0.1.0`** while conformance asks a package that
   has cut no release for a snapshot of `1.0.0` — so a freshly scaffolded language fails its own
   `slipwai package check`. The target scaffold opens `1.0.0.dev0` and is right. Same bug, both ends.
3. **`slipwai adopt` is broken in the keel and was before today.** `toolkit.CANON` is `typescript` and an
   adopted project has no service of the keel's, so 141 `{{example:}}` markers resolve against
   `assets/languages/typescript/examples/`, which version 2 does not have. `git init` a repo with a
   `pyproject.toml`, `slipwai adopt --yes`, and it exits 2. Nothing in the suite adopted end to end,
   which is why it was invisible. 14.3's preview-equals-adoption gate is excluded once, in writing, on
   `ADOPTION_RUNS` and turns itself on the day that directory lands.
4. **`GLOSSARY.md` is stale on two rows** after 11.3 — Harbourmaster still says "one process per harbour",
   Harbour log still says one file at `.slipwai/logs/harbour.jsonl`. It is generated from the plan's
   section 1 by `scripts/glossary.py`, so the plan is what to fix.
5. **12.5 is landed but unproven.** Its done-when is a fresh session handed `drive-captain.md` working a
   slice end to end with no Python runner in the path. That has not been run.
6. **`D-12.3-codex-prompts` is an unverified claim.** Codex's `commandsDir` was set to `.codex/prompts`
   from the plan's own row; the CLI was absent from the sandbox and the vendor's pages unreachable. It
   changes `./init` for Codex projects, not just the new verb.

## Three things of Phase 10's waiting on a decision

Raised by its captain, answered by nobody yet, and all three should be settled before its branch merges:

- **`target_protocol` gained `pipeline`, `readme_words` and `agent_rules`** — nine required members now.
  Its predecessor kept the protocol deliberately minimal and said so. A protocol member cannot be
  withdrawn once a cloud is published against it.
- **A `request: publish`** is open on its deck log. A captain holds no credential.
- **`packages/aws` and `packages/azure` committed in-tree.** `AGENTS.md` says the keel pins no
  first-party package, "because a keel whose gate checks seven packages is a keel that cannot be changed
  without them". `packages/toy` is a precedent, but it is one toy and these are two real clouds.

## How this was run, and what it cost

One session acted as harbourmaster: it held every merge (rule 10), ran `make verify` on each merge
result, and ticked the plan. Captains worked fairways in worktrees, communicated only through deck logs
at `.slipwai/logs/slipwai-2/<fairway>.jsonl` written through `src/slipwai/logs.py`, and never pushed.

**The logs are git-ignored and do not travel.** That is what the one-ref-per-writer decision is for and
11.2 is the slice that builds it. Until then, a fairway's reasoning survives only in its commit bodies —
which is why captains were told to put reasoning in the commit, not only in the log.

Two failures of the harbourmaster worth repeating so they are not repeated:

- **Four captains reported in, were merged, and their fairways sat empty.** The board said `finished`,
  which reads like an ending. A fairway with cleared work and no captain is `idle`, and nothing said so.
- **A fairway sat parked for forty minutes on a decision only the harbourmaster could take.** A captain's
  `parked` has no receipt — a `told` is answered by `read` and a `request` by `granted`/`refused`, but a
  `parked` is answered by nothing and timed by nothing.

Both are now **slice 7.11**, and neither needs two machines: both were met on one.
