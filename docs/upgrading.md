# Bring a generated project forward

A generated project owns every one of its files, and the factory never reaches in to overwrite one. What
the factory *can* do is offer: emit, from the answers a project recorded, what the current version would
generate for them — as a commit the project's own Git history can merge. A three-way merge then does the
thing the ownership rule was protecting: the project sees what changed, takes what it wants, and decides
every place where it and the factory disagree. The output of an upgrade is a proposed merge, never a
mutation.

Learning the whole loop? [Generate](learn-generate.md#4-migrate-then-catch-up) and
[adopt](learn-adopt.md#4-migrate-then-catch-up) each end on migrate **then `/catch-up`**.

## What a project records

`project.json` carries every answer the project was generated from — profile, target, each service's
language, framework and axis answers, each browser app — and, under `generator`, the provenance:

```json
"generator": { "name": "slipwai", "generatedWith": "1.6.3", "updatedWith": "1.7.0" }
```

`generatedWith` is the factory that scaffolded the repository and never changes; `updatedWith` is the newest
version to have written a file into it (`add-service`, `add-frontend` and a merged `replay` move it). The
factory's [CHANGELOG.md](../CHANGELOG.md) is read against those two numbers: every version between them is
one the project has heard from, every later one is something it has yet to be offered.

Choices made later by `./init` are recorded beside it: `.specify/integration.json` names installed agent
harnesses, and `.slipwai/extensions.json` names successfully adopted extensions. Migration reads those
records to re-project derived files; it never opens the extension menu or reruns an extension installer.
For projects created before the extension record existed, the marker-fenced regions already in `AGENTS.md`
are imported into it once.

## The recipe

From the project's root, on a clean tree:

```sh
cd /work/projects/payments-platform
slipwai migrate
```

Then `/catch-up` in an agent session, which reads what that left and runs `make verify`.

That is the whole of it when the merge is clean: one commit — two where the harness projections had to be
re-derived — `git reset --hard ORIG_HEAD` to undo all of it, nothing pushed. One command and not two:
whatever a migration cannot finish by itself is written into the project rather than left to a second
command somebody has to remember, because the merge is visible in `git status` and an obligation is not. `migrate` reads `project.json`, generates the whole project again with the factory as it is
now, and merges the result over what the project has become — as a three-way merge, because the generated
tree is committed onto the newest commit in the project's history that the factory made (the scaffold the
first time, the last migration after that), and that gives `git` a base. It brings the project up to the
version of `slipwai` that ran it; when the registry holds a newer one it says so first and goes ahead anyway
— `slipwai upgrade` beforehand is how to migrate to the newest ([Install the command](executable.md)).

What the merge does, file by file:

- A file only the factory changed since the base is taken, silently. This is where the toolkit skills, the
  commands, the gate scripts, the CI workflow and the Makefile mostly land.
- A file only the project changed is kept, silently.
- A file both changed merges where the hunks differ and conflicts where they do not, and the project decides
  each conflict.

When there are conflicts, `migrate` stops with the merge in progress — every other file merged and staged —
and names each conflicting file. Edit and `git add` each, or take a side whole (`git checkout --ours --
<file>` keeps the project's version, `--theirs` the factory's), then `git commit`; or `git merge --abort` to
walk away from all of it. Either way, `make verify` next: the upgraded project is held to its own gate like
any other change. `project.json` now says `updatedWith` the version that was merged.

To look before taking: `slipwai replay` is the same generation written beside the project instead of merged
— `../<name>-at-<version>`, a repository whose one commit sits on the same base — and it prints the `git
fetch` and `git merge` that `migrate` would have run.

## What to expect of each part of the tree

| Part | What a merge usually does |
|---|---|
| `skills/`, `commands/`, `scripts/`, `.github/workflows/`, `Makefile`, `.claude/` | The factory-owned surfaces, and where most of a factory's later work goes. Clean unless the project edited them; a project that customises a skill will meet the factory's edits to the same file as a merge, and conflicts only on the same lines |
| `README.md`, `AGENTS.md`, `docs/` | Generated prose the project is expected to edit. Hunks the project rewrote are kept; hunks the factory rewrote arrive; the same paragraph rewritten by both is a conflict |
| `apps/<service>/**`, `apps/<web>/**` | The walking skeleton the project has been building on. A changed skeleton file the project also changed *will* conflict, and should — this is product code, and the factory makes no promise of a clean merge here. Files the project never touched (an adapter's contract suite, say) come through |
| `project.json` | `updatedWith` moves; nothing else, unless the catalog's shape of the manifest changed, in which case the CHANGELOG entry says so |
| Anything `./init` pruned | Stays gone. `replay` reads what the project actually has on disk, as `add-service` does, so a project that dropped Keycloak is not offered it back |
| Anything the project added | Untouched: the factory does not know it exists |

A generated project also has files it *regenerates* rather than edits — `docs/README.md` indexes the pages
that ship, `.github/workflows/verify.yml` lists the services. Those are driven by the same list `replay`
reads, so they come through matching the project's actual applications.

One kind of file is regenerated by the project from the factory's, and is the exception that `migrate` has
to handle itself: `./init` projects elected extension guidance into `AGENTS.md`, then every `skills/`,
`commands/` and `agents/` file into each installed agent harness
— `.agents/skills/`, `.claude/commands/`, whichever the harness uses. Those harness copies are ignored;
the extension election and its `AGENTS.md` region are committed.
The factory has never written the harness-local copies, and an extension region is project-local after
adoption, so neither can move through the merge alone. `migrate` re-derives both after a clean merge and
commits tracked changes separately, with the project as the author: the factory's own commit stays exactly
the tree the factory wrote, which is what the *next* migration measures against. After a conflicted merge
it is `make agents` by hand, once the resolving commit is in, and the report says so.

## The second upgrade, and unusual histories

Each migration measures from the newest commit the factory made in the project's history — authored
`Slipwai <factory@local>` — so after one, the next measures from it rather than from the scaffold,
and a line both moved twice (the README's version, `updatedWith`) merges instead of conflicting. A history
that has lost that authorship (squashed, rewritten) falls back to its root commit; `slipwai replay --base
<rev>` names the parent outright when neither is right, and its `git fetch`/`git merge` finish the job. A
project that is not a Git repository cannot merge; `replay` gives it the tree and a `diff -r` to run — a diff
it still could not have had.

`add-service` and `add-frontend` are not commits the factory makes — the project commits them — so after
one, the base for the next migration is still the earlier factory commit and `updatedWith` may conflict on
its one line. Take either side; the merge commit is what records the version from then on.

## What this is not

- **Not a template-update tool that owns product files.** Nothing is overwritten without the project saying
  so; a `git merge` is the only thing that writes into the project, every conflict in it is the project's to
  decide, and one command undoes it.
- **Not a per-file manifest with checksums.** There is no list of files the factory "tracks" and no record of
  which the project has edited. `git` already holds that in the history, and reads it back for free.
- **Not a promise of clean merges on product code.** The claim is narrower and gated: the factory-owned
  surfaces come forward, `project.json` records what happened, and everything else has the conflict story
  above.

## How this is proven

`tests/test_replay.py` holds the mechanics: a replay by the factory that made a project is byte-identical to
it (the manifest is a complete record), a replay by a newer factory merges over the project's own work
keeping both sides and conflicts only where both touched the same lines, and a feature the project pruned
is not offered back. `tests/test_migrate.py` holds the command: one undoable commit when clean, a merge left
in progress with the files named when not, a clean tree required first, the newer-version warning, and the
harness projections re-derived afterwards — in their own commit, kept out of the tree the next migration
measures against, and still there after a second migration. `tests/test_catch_up.py` holds the notes: the
versions crossed selected from the two bounds a migration already has, each note taken from the changelog
verbatim, a version that recorded none said to have recorded none, and the file left git-ignored. `make
test-migration` runs the recipe against real history: it generates a project with the factory at the newest
release tag, gives it work of its own, runs `slipwai migrate` from `HEAD`, and requires that outside the
project's own files the result is byte-identical to a fresh generation — and that its `make verify` is
green. CI runs it on every change. The recipe is only as true as that gate.

## What a merge cannot do: the catch-up notes

Some changes cannot arrive as a merge at all: a new answer a project has to *give* (`./init --auth keycloak`
on a project that never chose one), a tool that has to be re-run, a step in the account the project deploys
to. And some arrive as a merge and then fail — a gate that is new in one of the versions crossed, holding
code that predates it to a rule it was never written against. Neither is a mistake by anyone, and both were
until now left to whoever thought to read the CHANGELOG afterwards.

Nobody could, in fact. The changelog is the factory's file and a generated project has no copy of it; both
supported installs put a `slipwai` on the `PATH` with no checkout behind it ([Install the
command](executable.md)), and the frozen executable unpacks its data to a directory that exists only while
the process runs. So the notes are brought to the project instead. Before `migrate` returns — whether the
merge committed or stopped at conflicts — it selects the entries between the version the project recorded
and the one being merged, takes each one's claim and its **Catch-up** paragraph verbatim — the sentence its
author wrote in the commit that made the change, which is the only place that answer exists — and writes
them to `.slipwai/catch-up.md`.

The file is written whenever the merge changed anything, including when the versions crossed cannot be
told as such. A project scaffolded before 1.6.0 has no `generator` in its `project.json` — that version is
the first to have written one — so nothing in it says which of the earlier factories made it; the page says
so and lists every entry above the first, for the reader to pick up from the one that made their project.
Two snapshots of one release share one changelog entry, so the page says that and shows the entry whole.
And where the changelog has no entry between the two, or the notes could not be written at all, the page
or the report says exactly that. The one thing a migration never does is leave no file: an absent file reads
as "nothing owed", and the project that crossed twenty versions with no record of it is owed the most.

That file is git-ignored and disposable. The durable record of what a version asked for is
[CHANGELOG.md](../CHANGELOG.md); a committed copy in every project would be the same words in a second
place, free to disagree with the first, and left behind once the work is done.

`commands/catch-up.md` — `/catch-up` in every generated project — is what works it: read every **Owes**
line, run `make verify`, take the target it stopped at, and say which of three things each failure is before
changing anything. The rule is right and this project has not done it yet (adopt it: change the code, not
the gate). The rule is right and this project already decided the opposite on purpose (put the two side by
side and ask the user which stands — that one is not the agent's to settle). Or the rule does not fit this
project (say so, with the reason, and raise it against the factory). Never soften a factory-owned gate: the
next migration brings it back, and it is a false green until then.

What none of this does is edit the project's code to satisfy a rule the code predates. That stays the
project's, which is the same boundary the merge draws.
