# Work on the factory

The factory is held to the standard it generates. `make verify` here is the same kind of gate it writes
into every project: one command, run locally and in CI, that has to pass before a change is finished.

The version this repository carries, when to raise it, what a snapshot is and what a release tag means are in
[AGENTS.md](../AGENTS.md#versioning-is-not-optional) — one rule, held to strictly, in one place.

## Verify it

```sh
make verify        # lint, typecheck, check-structure, test — the whole gate
make lint          # ruff over src/, scripts/ and tests/
make typecheck     # byte-compile, then mypy over the same three trees
make check-structure
make test          # the suite alone
make test TESTS="test_matrix test_add_service"   # a slice, by module
make test SKIP="test_matrix"                     # everything but
FACTORY_BACKENDS=java-quarkus make test TESTS=test_matrix   # the matrix for one backend
```

CI runs those same targets as parallel jobs on the self-hosted runner, all starting at once: `checks` (lint,
typecheck, structure, every fast suite), `matrix (<backend>)` — one job per backend, each generating that
backend's variants and gating each with its native `make verify` — `add-service`, `migration`, and `aws`.
`.github/workflows/verify.yml` says how the slices divide; between them every test runs exactly once.

No job installs a toolchain. Every one of them needs all of them — any backend's project may be generated
and gated in any job — so they are baked into the job image built from
[`.github/runner/`](../.github/runner/README.md), and `.github/actions/toolchains` only checks that the
image provides the versions `.github/runner/versions.env` pins. Bumping one is an edit there plus a rebuild;
an image that was not rebuilt fails the first job of the next run by name. Locally the whole gate is still
`make verify`, against whatever toolchains the laptop has.

`make test-migration` is the one gate beside `verify`: it generates a project with the factory as it was at
the newest release tag, gives it work of its own, runs `slipwai migrate` from the factory as it is now, and
requires that the result is byte-identical to a fresh generation outside the project's
own files and green under its own `make verify`. Before the first public tag there is nothing to generate
from, so the gate exits 0. After that it needs the release tags, so a shallow clone cannot run it;
`MIGRATION_ARGS="--from v1.6.0"` starts from another revision, `--keep DIR` leaves the three trees to look
at. [Bring a generated project forward](upgrading.md) is the recipe it proves.

`make test-adoption` is the gate for brownfield adoption (experimental): each fixture repository under
`tests/fixtures/adopt/` — one per ecosystem the survey recognises, two in languages the factory cannot
generate — is made a repository with history of its own, adopted, re-surveyed as a no-op, held to
`make -f delivery/Makefile verify` where its toolchain is on the machine, migrated from a newer factory as one
clean merge that leaves the repository's own files untouched, and held to the gate again. `ADOPTION_ARGS="--only
go-module"` runs one fixture; `--keep DIR` leaves the adopted repositories to look at. CI runs it as its own job.

`make changelog` prints the commits since the last release, split by whether they reached a user, and the
fragments already written for the release `main` is working towards — the `1.3.0` a `VERSION` of
`1.3.0.dev0` is a snapshot of; `make changelog VERSION=1.2.0` lists from an older release. It writes
nothing — what an entry *says*, including what an already-generated repository must do to catch up, is the
author's.

**The entry in flight is [`changelog.d/`](../changelog.d), a file per change; [CHANGELOG.md](../CHANGELOG.md)
is released prose only.** Write the fragment in the commit that makes the change, with its bump level on the
first line; `make release` assembles them into the entry, in the commit it tags, and deletes them. The
reason is what one shared entry did to a branch: two branches in flight both inserted at the top of the same
file, and `merge=union` in `.gitattributes` settled it without a conflict for Git while a forge — which
tests a pull request for conflicts with `git merge-file` in a bare repository, where no merge driver is
consulted — still reported one and asked somebody to resolve what Git had already merged. A file per change
has no shared line, in any tool. The level is checked rather than trusted: the highest one the fragments
claim, applied to the newest released entry, is the number `VERSION` has to carry, and
`tests/test_changelog.py` fails when it does not.

`make help` lists every target. The first run installs the pinned ruff and mypy from `requirements-dev.txt` into an
ignored `.python-tools`. A generated Python project is given uv and a committed `uv.lock` instead — this repository
has not moved, and that is the one place the two deliberately differ — but the *versions* are the same ones, and
`tests/test_factory_repository.py` holds them to it: the factory is not checked by a looser tool than the one it
hands its output.

The catalog (`catalog.json`) is the public configuration contract. `make test` validates its tier graph,
the default, the language matrix, and the indivisible Event Modeling/event-sourcing bundle. It scaffolds
disposable projects for every profile/language combination and runs each new repository's native
`make verify` gate — which is why the factory's own gate needs every supported backend toolchain present.

## How the source is laid out

`src/slipwai/` is one module per part of the repository being generated, so the file to open is
named after the file you are changing:

```text
src/slipwai/
├── assets.py            where the factory's own material lives, and the shared pruner
├── errors.py            the one exception a refusal is reported with
├── versions.py          how a version string reads: a release, or the snapshot of one on the way
├── catalog.py           the configuration contract, and its validation
├── features.py          what an option declares about the feature it owns, and what reads it
├── axes.py              what an axis is, and what the catalog has to say about one before anything reads it
├── targets.py           where a project goes to production, and what that takes off its menus
├── extensions.py        what an extension is: an optional dev-tooling hook `./init --extension <key>` can run
├── preflight.py         what a production target needs on this machine, checked before a project is written
├── examples.py          {{example:}} markers — one snippet per language the services are written in — and the pseudocode disclaimer
├── backends.py          what differs per backend language, and the ports every project agrees on
├── images.py            how each backend becomes a production image, and how its migrations run in one
├── selection.py         one validated answer per axis
├── services.py          which applications a project has — the list every part that names a service reads —
│                        and what each service says it owns (`purpose`, `contexts`)
├── capabilities.py      what a project can do, as the union of what its applications declare, and what a
│                        skill has to declare in its frontmatter to be given to it
├── manifest.py          that list read back from a written `project.json`, for `add-service` and `replay`
├── layout.py            where the factory's delivery material lives in a project (`layout.delivery`), and how files
│                        assembled for the root are placed and re-pointed when it lives elsewhere
├── ecosystems.py        what a build ecosystem's files say about the code they build — the table `survey.py` reads
├── survey.py            what an existing repository is made of, read off its tree, for `adopt` (experimental)
├── origin.py            how a repository came to have the factory's material, and an adoption's recorded facts
├── delivery_facts.py    what the tree says about how a repository is delivered: which forge runs its CI,
│                        how a change reaches production, and what each buildable directory is for
├── platform.py          what the applications run on, and whether it is still supported
├── wrappers.py          the build wrapper a wrapped Java application runs through, written where there is none
├── quick_wins.py        what the survey can see in a tree that is cheap to fix and expensive to leave
├── convergence.py       the convergence map: where an adopted repository stands on each ladder a generated
│                        project sits at the top of
├── strategy.py          which change strategy this repository's trigger and its map recommend — *leave it*
│                        included — and what, if anything, has been decided
├── programme.py         every improvement the record shows, in order, paced by the strategy
├── adopt_report.py      what `adopt` writes for a reader: the survey page with its evidence, and the report
│                        the command ends with
├── resurvey.py          `adopt --refresh`: survey again, and reconcile what is found with what was recorded
├── converge.py          `slipwai converge`: the end of an adoption, where every row of the map reads *as
│                        generated* and the delivery material moves to the root
├── tooling.py           how one service's build is spelled: package name, verify script, per-backend commands
├── toolkit.py           how a canonical toolkit file reaches a project, or why it does not
├── project/             one module per part of the generated repository
│   ├── makefile.py      its Makefile          ├── docs.py           its docs/
│   ├── compose.py       its Compose file      ├── commands.py       its commands/
│   ├── readme.py        its README            ├── guidance.py       its AGENTS.md
│   ├── gitignore.py     its .gitignore        ├── ci_workflows.py   its CI workflow
│   ├── init_script.py   its ./init            ├── event_model.py    its event model
│   ├── run_skill.py     its run-the-app skill ├── frontend.py       its apps/web
│   ├── agent_settings.py  its agent settings  ├── backing_services.py  its adapters
│   ├── pins.py          its .editorconfig, .nvmrc and .python-version: the toolchain the gate runs on,
│                        written where each ecosystem's own tools look for it
│   ├── renovate.py      its renovate.json: what keeps exact pins from becoming old exact pins, written
│                        for this repository's own layout
│   ├── repository.py    its LICENSE, SECURITY.md and pull-request template: what a repository owes
│                        whoever arrives at it, with the owner's half left as the owner's
│   ├── evolving.py      its docs/evolving-the-project.md: ownership, and how a newer factory is offered
│   ├── metadata.py      its project.json: every answer it was given, written once for everything that reads it
│   ├── shared_packages.py  its npm workspace: node_modules, packages/, and what has to be true for either
│   ├── integration.py   its integration suites: the variables one backing service's tests need, and the targets
│   ├── flags.py         its feature-flag reader, the flag gate, and the release decision behind them
│   ├── flag_route.py    its /api/flags: how a browser app learns what this environment's flags are set to
│   ├── existing.py      target: existing — what a project deploying to infrastructure it does not own is told
│   ├── stage_models.py  its .specify/models.json: which model runs each stage of /drive's ladder, by role
│   ├── benchmark.py     the section of its /drive that records what each stage cost and how it did
│   ├── demo_stop.py     the demo stop of its /drive: what a pause for feedback hands the actor, and opens with
│   ├── where_are_we.py  its /where-are-we: the demo stop's progress board, on demand
│   ├── model_to_code.py  the document that says what each box on the model becomes in a file
│   ├── constitution_journey.py  the constitution as a journey, adapted to where an adopted repository stands
│   ├── drive_adoption.py  the adoption phases of its /drive: what the ladder gains around code that was here
│   ├── ground_command.py  its /ground: the questions the tree cannot answer, asked of the person, one row at a time
│   ├── pin_commands.py  its /characterise and /survey: the Pin stage of adopting the method around existing code
│   ├── strangle_command.py  its /strangle, docs/change-strategy.md and the retirement ledger: Choose and Slice
│   ├── convergence_page.py  its docs/convergence.md, rendered from the rows project.json records
│   ├── structure_page.py  its survey/structure.md: the architecture view, for the two decisions that need it
│   ├── skills_page.py   its docs/skills-and-commands.md: which skills it was given, and what the rest
│                        were waiting for
│   ├── adopted_ci.py    the gate's CI configuration for a repository the factory did not make, per forge found
│   ├── adopted_targets.py  the Make targets an adopted repository has and a generated project does not
│   ├── mutation.py      what `make mutation` does per backend, and why
│   ├── native_commands.py  what each backend runs for the Makefile's targets, per service
│   ├── service_layouts.py  which adapter file lands at which path, per backend
│   ├── read_side_layouts.py  the same for the read side's, merged into that table
│   ├── ci_services.py   the service container its CI's integration job needs, and how to wait for it
│   ├── add_commands.py  its /add-service and /add-frontend commands, which run the factory
│   ├── rules.py         the per-answer rules AGENTS.md carries, as data
│   ├── infra.py         its infra/ (from assets/targets/) and scripts/deploy.py
│   ├── provisioning.py  what an answer becomes under a target, and how a drawing names it
│   ├── target_docs.py   which module writes a target's deployment drawing and production ADR
│   ├── aws_docs.py      those two pages for AWS, drawn and argued from the answers
│   ├── azure_docs.py    the same two for Azure — one module per target, because a deployment
│                        drawing and a production ADR have no general version to parameterise
│   ├── production.py    the Makefile's build/push/smoke/deploy/rollback section
│   ├── adopted.py       what an adopted repository takes from the factory, and the pages and blocks that explain it
│   ├── deploy_workflow.py  its deploy pipeline
│   └── languages/       one module per backend: typescript, python, go, java_quarkus,
│                        java_spring — each reads its walking skeleton from
│                        assets/languages/<backend>/app/, plus java.py for what the two
│                        Java backends share and assets/languages/java/build/ for the
│                        family's own build material
├── scaffold.py          the whole of a project, assembled and written
├── add_service.py       one more service in a project that exists, from the same code paths
├── replay.py            the whole project again, from a newer factory, as a commit the existing one can merge
├── migrate.py           `migrate`: that replay merged, in one command, projections re-derived after
├── catch_up.py          the notes a migration leaves: what the versions crossed ask of the project
├── adopt.py             `adopt`: the method installed around a repository the factory did not make (experimental)
├── cli.py               the command line: `generate`
├── cli_prompts.py       the questions it asks when run bare
├── cli_add.py           the verbs run inside a project: `add-service`, `add-frontend`, `migrate`, `replay`
├── cli_adopt.py         `adopt`'s questions, with the survey's findings as their defaults, and its flags
└── upgrade.py           `upgrade`: which way this copy was installed, and the newest version published
```

`scripts/check-structure.py` enforces that shape rather than leaving it to be described: imports point
inward through declared tiers, the graph stays acyclic, no module outgrows its line budget, and every
module says what part it is. It is the factory's own equivalent of the `check-imports.py` gate it ships to
generated projects, and `tests/test_factory_repository.py` proves it by handing it each violation it
exists to catch.

The tests mirror that split — one module per concern, with `tests/support.py` holding the
`FactoryTestCase` base that knows how to generate a project and how to expect a refusal.
`tests/test_maintenance_skills.py` holds the factory-maintenance skills in `.claude/skills/` to
the same standard as code: every path and test they cite has to resolve, every table keyed by
language has to be on both `add-language`'s and `add-framework`'s lists, and the generated gate's
target list they quote has to be the one `project/makefile.py` builds.
`tests/test_backend_obligations.py` pins the other direction: `docs/backend-obligations.md` is the
checklist those skills work from — every axis, every `make` target, every per-backend table — and that
suite derives each list from the catalog and the generator rather than trusting the file. Adding an axis
or a `make` target fails it until the document names the new obligation and every backend answers it,
which is the point: the failure list is the work the change created.

`tests/test_aws_stack.py` holds the production target to the real provider: it runs `tofu validate` over
every generated stack (skipping, with the reason, where `tofu` is not installed — the factory's CI installs
it and the pinned AWS provider once per run). `tests/test_images.py` builds every backend's image the way
`make build` does and starts it the way a task would, asking `/health` — the proof an image that builds and
pushes will also run; `pack` backends publish to a throwaway local registry, because Docker Desktop cannot
take a `pack` export directly. In CI it rides in each backend's `matrix` job, sliced by `FACTORY_BACKENDS`
like the matrix itself. `tests/test_launcher.py` proves the migrate task's entrypoint through the smallest
image the pinned builder makes, once, in the `aws` job. `docs/aws-target.md` says what that does and does
not prove.
`tests/test_aws_workflows.py` reads the two workflows that project is given — `deploy.yml` runs as a
`workflow_run` of `verify` on `main`, only when it passed, checking out the commit it passed; `rollback.yml`
is started by hand — and needs no tool, so it runs in the `checks` job.

`tests/test_matrix.py` is by far the slowest, being the one that generates every variant and runs its
native gate:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_catalog.py' -v   # one suite
```

## Decisions this factory cannot take back

`docs/adr/` holds the factory's own architecture decisions, in the shape the
[`architecture-decisions`](../assets/toolkit/skills/architecture-decisions/SKILL.md) skill asks of a generated
project: Nygard's five sections, one file per decision, numbered in order and never renumbered, and superseded
rather than edited once accepted. The test is the skill's — a decision is recorded when reversing it would cost
a migration rather than a refactor — and here that mostly means the shape of something a generated project
persists, because a project's log is the one thing no version of this factory can migrate for it.

- [`0001-a-dcb-capable-log.md`](adr/0001-a-dcb-capable-log.md) — the log records tags in a derived index, so a
  Dynamic Consistency Boundary stays available to a project that later wants one; stream-per-aggregate stays
  the default write path.
- [`0002-the-guard-a-slice-declares.md`](adr/0002-the-guard-a-slice-declares.md) — a state-change slice
  declares what its append is guarded by (`stream` or a tag `guard`), what it folds must be what that guard
  covers, and an event's identifying attributes are modelled while the tags derived from them are not.
  Completes the half `0001` recorded as owed.

## Browse the starters

No starter copy is committed anywhere: `assets/toolkit/` and its overlays are the single source, so a
change there reaches every combination the moment it is generated. To inspect the current output of all
ten foundations, materialize them into the ignored `build/` directory:

```sh
make starters
```

That writes the exact output of `./slipwai generate` for each combination (minus `.git`) to
`build/starters/<profile>/<backend>/` — with the `none` frontend and the default answer on every axis, so a
browsed starter carries the Postgres store and the backend's transport that a default project gets, not a
bare skeleton.

## Regenerate the dependency locks

Each dependency set the axes can produce has its own committed lock, because npm, uv and Go all refuse a lock
that disagrees with its manifest. Rebuild them all, or check for staleness without changing anything:

```sh
make locks
make check-locks
```

This needs network access; nothing is downloaded into a `node_modules`, only the resolution is written down.

It also needs a current npm — the committed locks were produced by **npm 11.19.1**. npm 9 crashes in
arborist on these manifests, and an npm older than 11 writes no `license` field for a resolved package, so
regenerating with one rewrites every lock in the repository to say less than it did. Check `npm --version`
before believing a large diff from `make locks`.

`renovate.json` at the root is what moves those manifests in the first place. Every dependency this factory
pins — its own tooling, and the manifests under `assets/` that every generated project starts from — is pinned
exactly, so nothing ages them but a person. The configuration groups minor and patch updates per ecosystem
into a weekly pull request and holds every major on the dependency dashboard, because an asset's dependency
reaching a new major changes what every project generated afterwards is given and nobody is asked again.

Two things about it are worth knowing before reviewing one of its pull requests. **An npm bump under
`assets/` is half a change**: the committed locks have no `package.json` beside them — they are built per axis
combination — so `make check-locks` goes red until `make locks` has been run on the branch and the result
committed in the same pull request. That is the workflow, not a defect; a lock and its manifest have to be
produced together. And **what Renovate cannot see is written down in the file itself**: the per-feature npm
versions in `project/languages/typescript.py`, the build-tool pins in `images.py`, the toolchain versions in
`backends.py` and `.github/runner/versions.env` are Python source and an env file rather than manifests, and
they are bumped by hand — [what a backend owes](backend-obligations.md#4-choices-that-belong-to-the-ecosystem-and-to-the-user--not-to-this-repository)
says who owns each of those choices.

Nothing runs it by itself. This repository lives on a Gitea forge, so it needs a self-hosted Renovate run —
a scheduled workflow on the forge's own runner, or a cron job — with a token that may open pull requests; on
GitHub it would be the Renovate app installed on the repository instead. Until one of those exists the file
states an intent. Every generated project carries one of its own, for the same reason and with the same
caveat ([What you get](what-you-get.md#the-layout)).

## Edit what gets generated

See [assets/README.md](../assets/README.md) for the asset tree and the editing rule. Three
factory-maintenance skills in `.claude/skills/` cover the three ways this factory grows:
`add-language` for a whole backend language, `add-framework` for a second framework beside one a
language already has, and `add-backing-service` for a tool choice — another answer to an existing
axis, or a new axis entirely.

`add-framework` is the one to reach for when the answer to "can we have Spring as well?" arrives.
The bare language name is reserved for a backend nothing owns the startup of, so how much that costs
depends on the existing key: beside an already-suffixed backend a sibling is purely additive, while
beside `typescript`, `python` or `go` it renames the existing backend too. `validate_backends`
enforces the naming in both directions either way.

## Build the executable

See [The standalone executable](executable.md).
