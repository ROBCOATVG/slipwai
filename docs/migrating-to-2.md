# Moving a project to slipwai 2

Version 2 is a major release. **Nothing is migrated behind your back:** your version 1 projects keep
working, and this factory keeps releasing on the 1.x line until you choose to cross. `slipwai upgrade`
replaces the *tool*; it does not touch a project. The project crosses when you run `slipwai migrate`
inside it, and that is one command and one merge commit.

This page is what `slipwai upgrade --check` points at once a stable 2.x is published. Read it before you
install version 2, not after.

## What is different, in one screen

| Version 1 | Version 2 |
| --- | --- |
| Go, Python, TypeScript and Java are inside the wheel | Each language is its own package, installed with `slipwai install <name>`. The keel ships none |
| AWS and Azure are branches inside `generate` | Both are packages too. Until one is installed, the production-target question offers `none` and `existing` only |
| One `make verify` for every change | Two gates: fast checks per increment, the full gate once before the merge |
| `cruise.py run` holds the state of a run | Nothing holds it. State is folded from append-only logs, so nothing can die holding it |
| A value stream, a workstream | A **fairway**. A workstation or lane is a **berth**; the runner is a **captain** |

The full table of renamed words is version 2's own `GLOSSARY.md`, which keeps version 1's word for each
in its last column.

## Before you cross

1. **Be on `main`, with a clean tree.** The crossing refuses otherwise, so that everything uncommitted
   afterwards is the migration's and the way back is one command.
2. **Finish or merge open slice branches.** A `slice/<id>` branch ahead of trunk is named and refused.
   Pass `--with-claims` to have the renames applied to each and left to rebase instead. A claim checked
   out in another worktree is refused either way.
3. **Know which languages your services use.** The crossing installs the packages they need, or refuses
   before writing anything if one has no compatible package.
4. **Have a backup you trust.** A clean committed state on a branch you have pushed is enough.

## The crossing

```console
$ slipwai migrate --check      # prepares the whole crossing and writes nothing
$ slipwai migrate              # the crossing: one merge commit
```

| Flag | What it does |
| --- | --- |
| `--check` | Prepares a crossing and reports it without changing the project: the catch-up page it would write, the conflicts there would be, and anything that would refuse. No project file and no claim branch changes |
| `--with-claims` | Applies the rename table to claim branches ahead of trunk and leaves each to rebase, instead of refusing while they are open |
| `--no-install` | Refuses, naming the install line, where a language the project needs is not installed — instead of installing it first |

**What it does, in order.** It reads which factory made the project from `project.json`, installs *that*
release of slipwai into a throwaway environment and regenerates the base there — version 2 carries none
of version 1's generator. A recorded snapshot falls to the nearest stable release below it, and the
difference is reported. It installs the languages your services need. It applies the rename table to the
base, merges three ways against your working tree, and leaves one merge commit.

**What it preserves.** Existing decision and adversary ids are frozen where they are and go on resolving;
ADRs keep their paths and numbers; nothing is renumbered. Flags keep their values and gain the `hoisted`
date the strike rule counts from. Words you said that version 1's run never finished acting on cross as
unanswered messages, each keeping the instant it was said; a run that stopped crosses as a park with its
reason. Slice status is reconciled upward from trunk's own merges only — nothing is downgraded.

## What it costs

- **Fairways are proposed, not decided.** The catch-up page's first task is confirming them, counted
  rather than described, and nothing can be claimed in a proposed fairway until you confirm.
- **Conflicts leave the merge in progress**, exactly as `git` leaves it, with each conflicting file named
  and both ways out spelled: resolve and commit, or `git merge --abort`.
- **The catch-up page is the part no merge can do.** `.slipwai/catch-up.md` lists every rename once, the
  base that was installed, the release mode and state to confirm, and what the crossing could not do.
  `/catch-up` finishes it, and stays red while any fairway is still proposed.

## What it cannot undo

- `git reset --hard ORIG_HEAD` undoes the merge and the commit after it — **until you push**. Nothing is
  pushed by the migration itself.
- **It does not undo the deck logs.** What version 1 left behind is appended to logs that are append-only
  by design and ignored by Git, so resetting the tree leaves those lines where they are. Re-running is
  safe: each migrated line carries a key, and a second crossing recognises what the first wrote rather
  than saying your words twice.
- With `--with-claims`, each claim branch is moved to a rename commit of its own. Resetting `main` does
  not move the claims back.
- **A language the crossing installed stays installed.**
- A rename is substituted as text only in the files that *declare* the thing renamed — a target in a
  Makefile, a command, a skill. A reference anywhere else in your repository is left exactly as written
  and read off the catch-up page, because a bare word in prose is not a declaration.
- A slice trunk cannot prove shipped keeps the status the model recorded for it. Unproven is unknown,
  not unstarted.

## When it is done

A green `make verify` on the migrated tree is the end of it. When the merge is clean, a second commit
re-derives the projections the merge cannot reach; after a conflict, that is `make agents` once the
resolving commit is in, and then `slipwai migrate` again.

## If your copy is further behind than 1.5

The crossing is the same one. `slipwai migrate` reads which factory made the project from `project.json`
and installs *that* release to regenerate the base, so a project generated by 1.2 crosses the same way a
1.5 one does — there is no ladder of intermediate upgrades to climb first. If your registry's newest is
already past version 2, cross to version 2 and then go on from there.

## If you are not ready

Do nothing. This factory goes on releasing 1.5.x, and `slipwai upgrade` keeps you on the newest of them
until a stable 2.x exists — at which point `slipwai upgrade --check` says so, once, and points here.
