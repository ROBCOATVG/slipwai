# What a backend owes — the checklist `add-language` and `add-framework` work from

A backend in this factory is a language plus, where the ecosystem has one, the framework that owns
startup. Adding one is not a single decision: it is a fixed set of obligations, and every one of them has
a place in the code that fails, or silently does not, when it is missed.

**This file is that set.** `.claude/skills/add-language/` and `.claude/skills/add-framework/` are the
procedures; this is the inventory they check themselves against, so the two cannot drift apart. It exists
because the list used to live only inside the skills, where nothing compared it to the code — and a list
nothing compares to the code is a list that is already wrong.

`tests/test_backend_obligations.py` holds it to the catalog and the generator: **add an axis or a Make
target and that suite fails until this file names it, and then until every backend answers it.** A
per-backend table it checks both ways — a row naming a symbol that has moved or gone fails, and so does a
table keyed by every backend that no row names, which is the failure the read side's own table did not
produce when it shipped. That is the whole point of the file. Do not answer a failure here by editing the table to
match the code without also asking the question the new row asks of every existing backend.

## 1. Axes — one independent decision each

Read from `catalog.json`'s `axes`. A backend may answer none of them, but only as a stated choice.

| Axis | What a backend owes if it answers | What it forfeits if it does not |
|---|---|---|
| `event-store` | **Two** ports, each with an adapter per option and one contract suite run against every one: `EventStore` — including the in-memory fake, which is what keeps the real ones honest — and `CheckpointStore` beside it, where a named projection has got to. The store also owes `unit_of_work`, the seam that suspends `append`'s own commit, and each checkpoint adapter is built from whatever answers *which transaction am I in* for the store it follows, because a checkpoint on a second connection is a race with a number in it | Both ports and both contract suites still ship, running against nothing |
| `http` | A transport that ecosystem actually uses, plus `dev_command` and `COMPOSE_CACHES` in `backends.py` — and, where a volume cannot separate the toolchain's state from the checkout, the environment that redirects it | No `make dev`, no `docker-compose.yml`, no `make demo` — verifiable, never demonstrable |
| `auth` | The realm, the container, the group-to-role mapping, and the protocol flow taken from the ecosystem's maintained client | Nothing: every backend defaults to `none`, so the gap sits where the others' default does |
| `users` | The customers realm in that same container, the customer adapter — a validated token becomes a customer only from this realm's issuer and only with a verified email — and bearer-token validation against a second issuer taken from the ecosystem's maintained client | Nothing, for the same reason; the browser app's login is the frontend's and arrives with any backend |

`auth` and `users` each `require` `http`; `catalog.json` and `prune.py`'s `REQUIRES` both have to say so, and
`prune.py`'s `REQUIRES_BECAUSE` carries the sentence each refusal prints.

Record the answer per backend in [`axes.md`](axes.md)'s coverage table — a row of dashes is how a gap
stays visible, and `tests/test_catalog.py` fails when that table and the catalog disagree.

## 2. Make targets — the eight commands every backend declares, per service

The `native` table in `project/native_commands.py`, one entry per backend, eight keys each. **The contract is
owed per service**: a generated project may have several, in one language or several (`docs/services.md`),
and every recipe is emitted for each of them in its own backend's spelling, so a command spells the service's
directory with `backends.APP` rather than `apps/service` (and Python's own verify script with
`backends.VERIFY`), and `native_commands` merges the services' answers into one recipe per target. The right-hand column is the
part worth reading before trusting one: **most of these are run by no gate.**

| Target | Run by | Consequence of a broken entry |
|---|---|---|
| `install` | nothing in this factory | A fresh clone cannot start; found by a person, not a gate |
| `lint` | generated `make verify` → the factory's own gate | Fails loudly, immediately |
| `typecheck` | generated `make verify` → the factory's own gate | Fails loudly, immediately |
| `test` | generated `make verify` → the factory's own gate | Fails loudly, immediately |
| `integration` | generated `make ci` only | Green here, broken in the generated repo's CI |
| `audit` | generated `make ci` only | Green here, broken in the generated repo's CI |
| `adversarial` | **no gate at either level** | Committed green, stays green, never executed |
| `mutation` | **no gate in a generated project**; the factory's suite runs Go's once, on a service importing a workspace module (`tests/test_matrix.py`) | Committed green, stays green, never executed — Go's excepted |

The factory's gate runs each generated project's `make verify`, and for Go one `make mutation` on the
layout the architecture page prescribes for shared code (`tests/test_matrix.py`) — added after a downstream
review found Gremlins scoring the build failure that layout caused as a kill, a false green no gate at either
level could see (`project/mutation.py`). So the last four rows are otherwise claims, not proofs, until someone
runs them by hand — which is why `add-language` section 10 requires exactly that before a backend is called done.

A project with a production target gets a second set of targets beside these eight — `build`, `push`,
`smoke-image`, `smoke`, `deploy`, `rollback`, `url`, and `migrate-remote` where a store is applied by a task
— generated by `project/production.py` from the two per-backend tables in `images.py` (section 3). They are
not in the `native` table because they exist only where there is a destination. Of them, `build` and
`smoke-image` are what the generated `make ci` runs, and `tests/test_aws_target.py` runs them for the Go
backend; every other backend's image build is a claim in the same sense the last four rows above are — run it
by hand (`make build smoke-image PLATFORM=<yours>`) before a backend is called done for the `aws` target.

## 3. Per-backend tables — the inventory generation reads

Every one of these is keyed by backend (or by family where noted) and raises `KeyError` rather than
degrading, so a missing entry fails generation at a predictable point. Paths are under
`src/slipwai/` unless stated.

| Table | Lives in | Keyed by | Needed when |
|---|---|---|---|
| `expected_backends` | `catalog.py` | backend | always |
| `BACKENDS` | `project/languages/__init__.py` | backend | always |
| `BACKEND_TOOLING` | `backends.py` | backend | always |
| `native` | `project/native_commands.py` | backend | always |
| `per_backend` | `project/gitignore.py` | backend | always |
| `toolchain_setup` | `project/ci_workflows.py` | family | always |
| `gates` | `project/docs.py` | backend | always |
| `paths` | `project/event_model.py` | backend | always |
| `tools` | `project/mutation.py` | backend | always |
| `per_backend` (agent permissions) | `project/agent_settings.py` | backend | always |
| `LANGUAGES` | `assets/backing-services/prune.py` | family | always |
| `HEALTH_BODIES` | `probes.py` | backend | always |
| `READY_PATHS` | `probes.py` | backend | always |
| `dev_command` | `backends.py` | backend | the `http` axis is answered — per service: it takes the service's path and what its package is named after |
| `COMPOSE_CACHES` | `backends.py` | backend | the `http` axis is answered |
| `event_store_directory` | `backends.py` | backend | the `event-store` axis is answered |
| `backing_service_service_files` | `project/backing_services.py` | backend | any axis is answered |
| `WRITE_SIDE_FILES` | `project/service_layouts.py` | backend | any axis is answered — which committed asset lands at which path under a service, keyed then by marker feature: the ports, the adapters behind them, the contract suites and the migrations |
| `READ_SIDE_FILES` | `project/read_side_layouts.py` | backend | the `event-store` axis is answered — the read side's half of that table, in the same shape: the checkpoint port and its adapters, the catch-up runner, whatever the framework ticks a pass with, and the two migrations that create the checkpoint table and the tag index |
| `SERVICE_FILES` | `project/service_layouts.py` | backend | any axis is answered — the two above merged feature by feature, and the one `backing_service_service_files` actually reads |
| `POSTGRES_SSLMODE` | `images.py` | backend | a production target with the `postgres` store — what this backend's driver has to be told about a managed database's TLS policy, since no two drivers spell it the same way and the URL cannot carry it. `None` is an answer and is written out |
| `PACKAGE_EDITS` | `assets/backing-services/prune.py` | family | any axis is answered |
| `OWNED_FILES` | `assets/backing-services/prune.py` | family | any axis is answered |
| `MARKED_FILES_BY_LANGUAGE` | `assets/backing-services/prune.py` | family | a marked file is per-backend |
| `BACKEND_EXECUTABLES` | `backends.py` | backend | always |
| `executable_paths` | `toolkit.py` | backend | the ecosystem ships an executable **text** script |
| `IMAGE_BUILDERS` | `images.py` | backend | always — how a service becomes a production image, and which tool the deploy workflow installs for it |
| `MIGRATIONS_IN_PRODUCTION` | `images.py` | backend | always — how the service's migrations run once it is an image: a command in its own image, a second image, or the framework at start-up |
| `FLAG_READERS` | `project/flags.py` | backend | always — where this backend's feature-flag reader is committed, where it lands in a service, and how a slice asks it. Emitted only under a production target, but the entry is owed whatever the target is, because nothing chooses the target at the point the table is read |

Two of those rows are keyed by backend and answered by more than one backend with the *same object*, which
is the correct shape rather than a shortcut. `BACKEND_TOOLING` and `BACKEND_EXECUTABLES` are Maven's answers
for both Java backends — the same wrapper, the same goals, the same image — so each is named once
(`MAVEN_TOOLING`, `MAVEN_EXECUTABLES`) and referenced twice, and there is exactly one place to change it. A
sibling built with Gradle would take its own entry, which is why these stay keyed by backend rather than
being rekeyed by family. `COMPOSE_CACHES`, `event_store_directory`,
`per_backend` in `agent_settings.py` and `paths` in `event_model.py` do the same, for the same reason.

One per-backend answer is deliberately **not** in the table above, because it does not have the property the
table is a list of: the mutation note in `project/mutation.py` is looked up with a default, so a backend
with nothing to say about `make mutation` gets silence rather than a `KeyError`. That is right — most
backends have nothing to say — but it makes the note the one per-backend answer whose absence no gate would
report, and the target it explains is itself run by no gate at either level (section 2). So it is worth
knowing that it *is* per backend and why: PIT works under Spring Boot's test harness and times out under
Quarkus's, so `java-spring` ships `make mutation` wired up and `java-quarkus` ships a documented
placeholder. A note shared across the family would say something untrue about one of the two, in the one
place a reader has to trust because nothing else checks it. Go's note is the third shape: a working target
whose gate is a committed file, the service's `.gremlins.yaml`, because Gremlins 0.6.0 reads a threshold
given on the command line as a string and gates nothing — and whose recipe is a wrapper, `scripts/go-mutation.py`,
because Gremlins copies only the module it mutates and scores the build failure a workspace import then
suffers as a kill, and passes a run that mutated nothing or timed out. Facts only the note tells the next reader.

`READ_SIDE_FILES` is the one of those tables where every backend's entry has to cover the same ground —
the checkpoint port, three adapters, one contract suite, the runner and its test — differing only in what
each ecosystem ticks a pass from and in what the paths are called. That is deliberate rather than
incidental: an asymmetric read side would reproduce one level down the defect `materialisation` exists to
fix, because whoever picked the language with less would build the per-request fold nobody chose.

`BACKEND_TOOLING` carries fields rather than being one answer, and two of them exist only because a
containerised build can differ from a local one. They are not separate rows above — a missing field fails
in the same `KeyError` the table itself does — but they are the easiest to miss:

- **`container_setup`** — what has to be installed inside `ci_image` before `make` can run there. Empty for
  every backend whose image ships GNU Make, which is all of them but Java: no official Maven or JDK image
  carries it, so both places that run `make` in a container — Compose and the CI integration job — have to
  install it first. It also runs in the dev containers, so it is not the place for anything only CI needs.
- **`ci_image` owes `git`, and does not owe `node`.** The integration job takes a `container:`, and a job
  with one runs a JavaScript action *inside* that image. GitHub mounts its own Node in to do it; act, which
  Gitea's act_runner is built on, execs a bare `node` — and no official `golang:`, `python:` or `maven:`
  image ships one, which is an integration job that dies in its first step with `exec: "node": executable
  file not found in $PATH`, on Gitea only, having run nothing. So the containerised job takes no `uses:`
  at all: `CONTAINER_CHECKOUT` in `ci_workflows.py` clones the commit with `git` instead. Picking an image
  is therefore one question, not two — it needs `git`, which all four current ones have, and whether it
  carries Node no longer decides anything.
- **`container_environment`** — what the toolchain has to be *told* when it builds inside a mounted
  checkout. Reach for this when a volume cannot separate the toolchain's state from the tree: masking the
  build directory keeps the output out of the checkout, but Docker still creates the mount point on the
  host owned by root, and the next host-side build then fails with a permission error nowhere near its
  cause. Java points Maven's output outside `/workspace` instead. Prove either way by running `make demo`
  and then `make verify` in the same checkout.

And two rows above are tables only because a backend disagreed with the others:

- **`HEALTH_BODIES`** — a framework that owns startup ships the liveness probe too, and answers in its own
  shape. `HEALTH_PATH` stays a constant, because a probe's path is configurable and every backend is
  pointed at it; the body is not, because a specification may fix it. MicroProfile Health's
  `{"status":"UP","checks":[…]}` is the one to expect.
- **`READY_PATHS`** — where this backend answers "send me traffic", which is the probe everything that
  gates traffic waits on. `/ready` for a backend whose entry point this factory writes, because the route
  is this project's; a framework that already serves a readiness endpoint keeps the path it serves it on,
  because a hand-written probe beside a maintained one is a route the project then owns forever.

`assets/` is text-only — `asset_tree` reads with `read_text`, `write_project` writes with `write_text` —
so a build wrapper needing a `.jar` beside it is not a thing a backend can ship, whatever that ecosystem's
convention is. Such a backend takes its build tool from the PATH and the CI image instead.
`tests/test_factory_repository.py::test_every_asset_is_text_because_the_pipeline_can_carry_nothing_else`
keeps that true.

## 4. Choices that belong to the ecosystem, and to the user — not to this repository

Each row is a decision this factory makes per backend, and each has an answer that a `WebSearch` run now
owns rather than any document in here. **The choice of tool is an ecosystem claim, not only its version** —
a stale version is a one-line bump, the wrong tool is pinned into every project generated afterwards.

**Searching is half of it: every row is confirmed with the user, with `AskUserQuestion`, before it is
pinned.** These are as permanent as the framework choice — a generated project has no update relationship
with this factory, so the linter, the test runner, the mutation tool and the audit chosen for a backend are
chosen for every project generated from it, and nobody is asked again. The framework and the axis coverage
were always confirmed; this table was not, which is how a first run of `add-language` searched all nine
rows, decided all nine alone, and reported them afterwards. Two rows make that costly in ways a search
cannot show: `native["mutation"]` is run by **no gate at either level** (section 2), so a tool that cannot
run under the chosen framework's harness is committed green; and `native["audit"]` differs between options
by what each one *requires* — an API key, or a committed lockfile that drags
`scripts/regenerate-locks.py` into scope — rather than by quality.

Present a recommendation per row with the fact that decided it attached, so it is a confirmation rather
than an interrogation.

| Decision | Lands in | The question to search |
|---|---|---|
| formatter and linter | `native["lint"]` | what that ecosystem's teams actually gate on |
| type or static analysis | `native["typecheck"]` | the checker a team would fail a build on |
| test runner and coverage | `native["test"]` | the runner the chosen framework's test harness expects |
| mutation testing | `native["mutation"]`, `mutation.py` | the tool **and its support matrix for your framework** |
| dependency audit | `native["audit"]` | whether the ecosystem has a first-party one |
| toolchain version | `ci_workflows.py`, `requirements.md` | the current LTS, not a recalled one |
| CI container image | `BACKEND_TOOLING["ci_image"]` | the image that ecosystem publishes now |
| build output and cache paths | `gitignore.py`, `COMPOSE_CACHES` | where that toolchain actually writes |

## 5. When a framework owns startup, the integrations are its too

This is the obligation a framework-owning backend added to this factory has already missed once, and the
reason this file exists. The
framework question is answered in `add-language` section 0 — and answering it decides more than the
backend's name. For **each axis the backend answers**, search the framework's own extension index before
writing an adapter:

| Axis | Concern | What the framework probably already provides | What hand-rolling it costs |
|---|---|---|---|
| `event-store` | connections | a datasource with pooling, configuration binding and transactions — and usually a database health check for free. On the JVM that is the shape the store takes: it holds a `Transactions` port, and the framework supplies the one class in the project that names a transaction API — `SpringTransactions` is a `TransactionTemplate` plus `DataSourceUtils.getConnection`, `JtaTransactions` is `QuarkusTransaction` plus Agroal — so everything else that asks *which connection is this transaction on* gets the same one | connection and pool semantics this factory then owns forever — and a store that manages its own connections cannot be enlisted in anybody else's transaction, which is the whole of the read side |
| `event-store` | schema | a migration integration, applied at startup or on command | a migration runner and its ledger table, hand-maintained |
| `http` | probes | a health and readiness endpoint | a route that duplicates a maintained one |
| `auth` | protocol | the whole authorization-code flow and token validation | **a security defect**, not a style one |
| `users` | protocol | bearer-token validation against a second issuer — a named tenant, a second filter chain — with an audience check | the same defect, and a customer token accepted from the staff realm |

Sibling frameworks in one family do not have to answer these the same way, and the two Java backends do
not: Quarkus configures its datasource through a MicroProfile `ConfigSource` and Spring Boot through an
`EnvironmentPostProcessor`, each found via a registration file whose name its own framework fixes. What
they *do* share is everything behind the port — the port itself, all three store adapters, the URL parser,
the migration entry point and the contract suite name no framework type, so both backends read one copy
from `assets/backing-services/java/` rather than each keeping its own. That split is the test of whether
"use the framework's integration" was applied honestly: what a framework decides is per backend, and what
is left over turns out to be most of the code.

What stays hand-written either way — and why using the extension keeps the architecture intact:

- the **port**, an application-owned interface naming no framework type;
- the **domain** and its tests, which no extension may reach into;
- the **in-memory adapter**, so the contract has something infrastructure-free to run against;
- the **contract suite**, run against every adapter including the framework-backed ones.

The extension sits *behind* the port, in the driven adapter, exactly where a hand-written driver would
have. That is what makes "use the framework's integration" and "keep the hexagon" the same instruction.

Two traps that come with adopting one:

- **Framework-managed dev containers.** Several frameworks start a throwaway database when none is
  configured. The default gate here must run with no Docker at all, so find the switch, set it
  explicitly, and prove it with the daemon stopped.
- **A cross-backend contract the default does not match.** `compose.py`'s healthcheck, `makefile.py`'s
  printed demo URL and `run_skill.py`'s documented `curl` all name one probe path and agree on one body
  shape — and all three read it from `HEALTH_PATH`, `READY_PATHS` and `HEALTH_BODIES` in `probes.py`, which
  is where the contract is stated. An integration that serves its own liveness path is configured onto
  `HEALTH_PATH`, which is why that one is still a constant; one whose readiness endpoint is its own answers
  on the path `READY_PATHS` names for it, and one that answers in its own shape adds a row to `HEALTH_BODIES`,
  which is why that one is already a table. MicroProfile Health's `{"status":"UP","checks":[…]}` is the
  shape to expect, and it is fixed by the specification rather than configurable. Read the constant, the
  table and the comment above them before assuming either.

## 6. Adding a new axis, or a new obligation

The order matters, because the point of this file is that a new obligation is asked of every backend
rather than only the next one:

1. Add the axis to `catalog.json`, and to `prune.py` — options, `requires`, `REQUIRES`.
2. Add its row to section 1 above, and its per-backend tables to section 3.
3. Run `tests/test_backend_obligations.py`. It fails for **every backend that does not yet answer the new
   obligation**, which is the list of work the change actually created.
4. Answer it for each backend, or record the gap in [`axes.md`](axes.md)'s coverage table as a dash. A
   stated gap is fine; an unnoticed one is what this file exists to prevent.
