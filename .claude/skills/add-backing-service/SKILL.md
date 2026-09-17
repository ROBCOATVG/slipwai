---
name: add-backing-service
description: Factory-maintenance skill for adding a tool choice to slipwai — a new answer to an existing question (another event store, another HTTP framework, another identity provider) or a whole new question (a message broker, a cache, an object store). Covers catalog.json, assets/backing-services/, prune.py's tables, the src/slipwai/ wiring, markers, committed locks, tests and docs. Use when asked to add, restore or scaffold a database, transport, identity provider, broker or any other selectable infrastructure option in this factory.
---

# Add a backing service

A generated project's infrastructure is chosen one **axis** at a time. This skill is for changing
what those questions and answers are. The neighbouring `add-language` skill is for adding a
*backend* to the matrix; the two barely overlap — that one edits per-language dictionaries and
writes example snippets, this one edits per-feature tables and writes adapters.

Three words, used precisely throughout, because the factory's data model depends on the distinction:

- An **axis** is a role, phrased as one question: where events live (`event-store`), what accepts
  inbound HTTP (`http`), who authenticates staff (`auth`). It is never a product, and never a protocol:
  every `auth` answer is an OIDC issuer, which is why that axis is not called `oidc`.
- An **option** is one answer to that axis — `postgres`, `fastapi`, `keycloak`, and always one
  no-infrastructure answer (the axis's `absent`).
- A **feature** is the marker name that owns files and marked regions. An option is answered *with*
  a set of features. `memory` is an option that owns no feature at all, which is exactly why the
  in-memory adapter can never be pruned.

## 0. Search for the product's facts — this document has none that are current

Postgres, SQLite, Fastify, FastAPI, Keycloak, MySQL, Kafka and Redis are named throughout as
**illustrations of a shape** — "an option with a container", "an option that runs in-process" — never as a
current menu or a current set of facts. Two kinds of claim get made when an option is added, and only one
of them can be answered from inside this repository:

| A claim about | Source of truth |
|---|---|
| **the product** — what it is, what it cannot prove, which image tag and driver version to pin, whether it is still maintained, what a team would actually pick for this role | **a `WebSearch`, every time** |
| **this factory** — which tables a feature needs a row in, what the pruner has to reverse, what `validate_axes` refuses | **the code, read now** — the tables below are inventories to re-derive, and they say so |

Search before you write, specifically:

- **Before offering the user a choice of product for a role.** If the ask is "add a message broker" rather
  than a named one, the candidates are a search result filtered through section 1's container question —
  not a list recalled from here. Attach the fact that decided each one, and weigh maintenance status:
  whatever is chosen is pinned into every project generated with that option afterwards.
- **Before writing the `label`** (section 4). It is a claim about the product, shown by the prompt and by
  the generated project's `--list`, and "what it does NOT prove" is exactly the half that goes stale when a
  product gains a feature.
- **Before pinning any version** — the Compose image tag, the driver in `PACKAGE_EDITS`, the inline pins in
  `go_module_variant`, the `ci_image` in `BACKEND_TOOLING`. Search for the current supported release rather
  than recalling one; a pin is the longest-lived thing this skill writes.

`.claude/skills/add-language/` section 0 states the same rule at length, with the reason it is a rule
rather than a preference: a stale name in a skill does not read as stale to whoever is answering.

## 1. Decide the shape first — two questions, in this order

**Is this a new answer or a new question?** A new answer to an existing axis (a second event store,
an HTTP framework for a backend that has none, a second identity provider) is sections 2–10. A new
axis — a genuinely new *kind* of tool, such as a message broker or a cache — is all of that plus
section 11, which is where the real cost of a new axis is spelled out. Do not invent an axis for
something that is an answer to one that exists.

**Does it need a container?** This is the load-bearing question, and the answer changes the size of
the job by an order of magnitude:

- **No container** — a second file-backed store, a new HTTP framework, anything that runs inside the
  process. This is close to a pure data-and-assets edit: follow the `sqlite` and `fastify` shapes,
  which is what sections 2–10 describe.
- **Needs a container, or migrations, or a separate integration suite** — read **section 3 before
  editing anything**. Those three are *declared* by the option and read off the selection, so this is a
  catalog entry plus one row in each table keyed by feature. It is more work than the first case and it is
  still additive: if you find yourself writing a conditional on your option's name, section 3 says what
  you are actually asking for.

## 2. What every option owes, whatever its shape

One rule governs this whole area, and every table below is an instance of it: **emit nothing
half-ported.** An option is implemented for a backend only when that backend gets the port, every
adapter behind it, and **one contract suite run against all of them**. A fake with no real adapter
checked against the same contract has nothing keeping it honest, and a real adapter with no contract
is a claim nobody checks. That set is the deliverable; the catalog entry is bookkeeping.

Two consequences worth stating before you start:

- **`make verify` must still pass on a machine with no Docker.** The port's contract runs against the
  infrastructure-free adapters in the ordinary gate; only `make test-integration` may touch a real
  service. A test that needs infrastructure goes where the default suite cannot see it — an excluded
  directory, a separate config file, or a build tag.
- **An option is offered per backend, and per target.** `backends` on the option is the list of backends
  whose assets you have actually written; `targets` is the list of production targets it is offered under.
  Leaving a backend or a target out of it is a supported, safe answer: the CLI refuses that combination
  with the reason, and no half-ported adapter is emitted.

## 3. A container-backed option — declare the traits, then fill the tables

"Needs a container, and migrations, and its own integration suite" was once the literal string `postgres`,
branched on in twelve places across nine modules — and `keycloak`, `sqlite` and `fastify` were the same
defect one axis over, twenty-three branches on option names in all. Adding a second answer to any axis
meant writing a twin of every one of them, and the next one made it a triplet. The service traits are now
**declared by the option** in `catalog.json` and read off the selection, and everything genuinely
per-feature is a table looked up with `Selection.feature_of(axis)`, so there is no branch left to copy.
Three declarations, and what each one buys:

| Declaration | What it produces, and what answers it |
|---|---|
| `containers` | `make services-up` / `services-down`, the Compose file existing at all, the `docker compose *` agent permissions, the "local backing services" README section — `Selection.containers` |
| `migrations: true` | `make migrate` inside the feature's own marked region, `CI_DATABASE := migrate`, the `make migrate` step in the CI job, the `make migrate` permission — `Selection.migrating_feature` |
| `integration-suite: true` | `INTEGRATION_TEST :=` and the `$(INTEGRATION_TEST)` recipe, the whole `integration` CI job, the vitest exclusion that keeps `make verify` Docker-free, the `make test-integration` permission — `Selection.integration_feature` |

`validate_traits` in `src/slipwai/features.py` refuses an option that leaves either trait
unstated, that claims one on the axis's `absent` answer, or that claims one while owning no feature — a
marked region has to be named after something, and that something is the feature.
`tests/test_factory_repository.py::test_an_option_s_feature_is_never_branched_on_by_name` fails the build
if any module goes back to testing for an option's feature by name — any option, not only a container-backed
one — and
`tests/test_catalog.py::test_a_service_trait_is_declared_by_the_option_and_checked_before_anything_reads_it`
holds the declarations to being a contract rather than a convention.

What a second container-backed option still owes is a **row** in each table keyed by feature. Every one is
content — prose, a pinned image, a dependency — and none of them is a conditional:

| Table | Module | What the row holds |
|---|---|---|
| `SERVICE_VARIABLES` | `project/makefile.py` | the Make variables its address lives in (`DATABASE_URL ?= …`, `export`) |
| `CI_SERVICES` | `project/ci_services.py` | the CI `services:` stanza — image, environment, healthcheck — and the readiness probe that follows the install step |
| `EVENT_STORE_README` and `EVENT_STORE_GATES` | `project/backing_services.py` | what to start, and what each gate does and does not prove — for an event store |
| `IDENTITY_README` and `IDENTITY_OUTSTANDING` | `project/backing_services.py` | what the realm import does, and what the project still owes per language family — for a staff identity provider |
| `USERS_README` and `USERS_OUTSTANDING` | `project/backing_services.py` | the same pair for whoever authenticates the product's users |
| `ROOT_FILES` | `project/backing_services.py` | repository-root files the feature owns (a realm export), destination to asset |
| `SHARED_ROOT_FILES` | `project/backing_services.py` | root files several features share, keyed `a\|b` like a shared marker — the Keycloak README, one section per realm |
| `WEB_FEATURE_FILES` | `project/frontend.py` | a directory under `assets/frontends/react-vite/` copied into every browser app when the feature is present — the customer login |
| `WEB_PACKAGE_ADDITIONS` | `project/languages/typescript.py` | the npm dependencies it adds to every browser app, agreeing with `WEB_PACKAGE_EDITS` |
| `EVENT_STORE_GUIDANCE`, `IDENTITY_GUIDANCE` and `USERS_GUIDANCE` | `project/guidance.py` | the AGENTS.md rule about what it proves, or what must not be hand-rolled |
| `STORE_ARTIFACTS` | `project/gitignore.py` | what a store writes beside the code, for one that keeps its data in the working tree |
| `COMPILER_ESCAPES` | `project/languages/typescript.py` | a compiler setting a transport's dependencies force, inside that transport's region |
| `SERVICE_FILES` | `project/service_layouts.py` | the adapters, their contract suite and the migrations, per language |
| `PACKAGE_ADDITIONS`, `FEATURE_REQUIREMENTS`, `MODULE_FEATURES` | `project/languages/typescript.py`, `python.py`, `go.py` | the dependencies it adds, per ecosystem — and they have to agree with `PACKAGE_EDITS` (section 6) |
| `ENV_FEATURES` | `backends.py` | whether it contributes keys to `.env.example` |
| `FEATURE_TOOLING` | `backends.py` | **only** if its migrations or its integration suite are not run by the language's own tooling; empty today, and a row here is what replaces the branch that used to be needed |

Two of those are worth reading twice. The prose tables are keyed by the feature answering **one axis** —
`EVENT_STORE_*` by the store, `IDENTITY_*` by the identity provider — because that is the axis each
belongs to; an option answering a *new* axis brings its own table and its own `feature_of("<axis>")`
lookup beside them rather than a row in these (section 11). And `MODULE_FEATURES` in `project/languages/go.py` is
combinatorial, not a priority chain: the chain it replaced returned the first feature it matched and
silently ignored the rest, which was correct only while no two dependency-adding options could be selected
together. A Go option that adds a requirement joins that tuple, and needs its committed module variant
(section 9) — `go build` refuses a `go.sum` that disagrees with `go.mod`, so the pair moves together.

So adding MySQL, EventStoreDB, Kafka or Redis is a catalog entry, the assets, and those rows. If you find
yourself writing `if selection.has("<your option>")` anywhere under `src/slipwai/`, stop: the
question you are asking is a trait, and either it is declared already or it is a fourth one that belongs
beside the other two in `features.TRAITS`.

## 4. catalog.json

Add the option under its axis. Every key is load-bearing:

```json
"<option>": {
  "capabilities": ["<axis>-<option>"],
  "backends": ["typescript", "python"],
  "targets": ["none"],
  "containers": ["<compose-service>"],
  "migrations": false,
  "integration-suite": false,
  "label": "<Product> — what it is, and what it does NOT prove",
  "features": ["<feature>"]
}
```

- `backends` — only the backends whose assets are written (section 2).
- `targets` — the production targets this option is offered under, a non-empty subset of the catalog's
  top-level `targets` (`none` and `aws`). The axis's `absent` answer must be offered under every target, so
  "nothing" is always an answer; `validate_axis_targets` in `src/slipwai/targets.py` refuses the
  rest. Leave `aws` out until the option is provisioned there: SQLite says `["none"]` because the file dies
  with the task, Keycloak says `["none"]` because Cognito is its answer in the cloud. Where a target
  provisions the option, say so under the target's key — `postgres` carries `"aws": {"provisions": "rds"}` —
  and give `assets/targets/aws/service/` the resources inside a `backing-service:<feature>` marked region,
  reading `var.services[*].store` (or `auth`, `users`) for which services asked. `docs/aws-target.md` has the
  shape; a new option that is offered under `aws` and provisioned there is a row in `project/infra.py`'s
  `service_record` only if it answers a new axis.
- `containers` — Compose service names. Empty means this option runs with no infrastructure, which
  is what lets a project have no `docker-compose.yml` at all.
- `migrations` and `integration-suite` — the traits in section 3, stated for every option including the
  ones that have neither. `validate_axes` refuses an option that leaves one out, because a trait left
  unstated is a `make migrate` the project needed and silently never got.
- `features` — the marker names this option owns. Usually one, same name as the option. A feature
  named here must **not** also appear in the axis's `always` list; `validate_axes` refuses that,
  because a feature cannot be both un-prunable and an option's to drop.
- `label` — shown by the interactive prompt and by the generated project's `--list`. Say what the
  answer *cannot* prove, not just what it is: the existing labels do, and the moment somebody
  chooses the weaker store is the moment they need to know what stopped being provable.

Then check the axis's `default` (`catalog.json`'s top-level `default` block). `validate_axes`
requires the default to name an answer every backend that can be given one can actually be given — and
`validate_axis_targets` holds it to the same rule per target —
so adding your option to a backend the axis previously had nothing for forces a default entry for
that backend. A per-backend axis holds a map (`http` does); an axis where one answer suits every
backend holds a string (`event-store` does), and it has to become a map the moment one backend can
be given something another cannot.

## 5. assets/backing-services/ — the port, the adapters, the contract

Per implemented language, under `assets/backing-services/<language>/`. Read the three existing
backends before writing: each has the port, the in-memory adapter, the real adapters, **one contract
file the adapter test files each run**, and the migrations.

- **Share the schema.** SQL migrations live once in `assets/backing-services/sql/` and are reached
  from a language's layout as `../sql/001_events.sql`. `tests/test_backing_services.py::test_one_event_log_schema_is_shared_by_every_backend_that_needs_it`
  asserts the copies have not drifted — do not paste DDL into a language directory.
- **One contract, every adapter.** `test_every_backend_gets_the_same_port_and_the_same_contract`
  is the test that holds this. A new adapter joins the existing contract; it does not bring its own.
- **Compose.** Add the service to `assets/backing-services/docker-compose.yml` inside a
  `# backing-service:<feature>:begin` / `:end` pair, with a `healthcheck` (`make services-up` uses
  `docker compose up -d --wait`, which blocks on exactly that), no `container_name`, and the host
  port as `'${<NAME>_PORT:-<default>}:<container-port>'`. A named volume needs **its own marked
  block** — the file's header comment explains why the `volumes:` header lives inside the Postgres
  block, and repeating that mistake produces a Compose file no gate would catch.
- **Environment.** Add the option's keys to `assets/backing-services/env.example` in a marked
  region, and add the feature to `ENV_FEATURES` in `src/slipwai/backends.py` so a project that selects
  it gets an `.env.example` at all.

## 6. prune.py — the other half of every fact

`assets/backing-services/prune.py` is imported by the factory *and* shipped as the generated
project's `scripts/backing-services.py`, from one copy
(`tests/test_pruning.py::test_the_pruner_is_one_implementation_shared_with_the_generated_project`
asserts byte equality).
What generation adds, the pruner has to be able to remove again:

1. **`FEATURES`** in `prune.py` — add the feature. `validate_axes` compares this tuple against
   `known_features(catalog)` and raises "catalog and assets/backing-services/prune.py disagree about
   the feature list", so a mismatch fails immediately rather than at prune time.
2. **`AXES[<axis>]["options"]`** — the option, with `features`, `targets`, `label`, and `note`. `targets`
   mirrors the catalog's: the generated project's `./init` reads `project.json`'s `target` and offers only
   what that target carries. The `note` is the consequence of choosing it, printed on selection and by
   `--list`. Prose, deliberately, not a doc link.
3. **`OWNED_FILES[<feature>]`** — every path that exists only because this feature was selected, per
   language. Patterns may glob, which is how the Python entries reach inside a package directory
   named after the project. Miss a path and a pruned project keeps a dangling adapter. A file the
   feature adds to every *browser app* goes in **`OWNED_FILES_PER_WEB_APP`** instead, and a root file
   several features share — kept while any of them remains — in **`SHARED_FILES`**, keyed `a|b`.
4. **`CONTAINERS[<feature>]`** — the Compose service name, if any. Absent means no container, which
   is what lets a SQLite project have no Compose file. Two features may name one service: `keycloak`
   and `users-keycloak` both say `keycloak`, and the container goes with the last of them.
5. **`PACKAGE_EDITS[<language>][<feature>]`** — the dependencies and scripts that exist only for this
   feature. `test_the_pruner_is_one_implementation_shared_with_the_generated_project` asserts these
   agree exactly with what `service_package_json` adds; the equivalent for Python is
   `python_requirements`, and Go's module graph is derived from the imports so removing the adapter
   *is* the removal. What a feature adds to every browser app's manifest is **`WEB_PACKAGE_EDITS`**,
   agreeing with `WEB_PACKAGE_ADDITIONS` the same way.
6. **`MARKED_FILES` / `MARKED_FILES_BY_LANGUAGE` / `MARKED_FILES_PER_WEB_APP`** — any *new* file that
   carries a marked region. A region in a file not listed here is silently never pruned.
7. **`REQUIRES`** — only if this option needs another axis answered, the way `auth` and `users` need
   `http`. Declare it in the catalog axis's `requires` **and** here, with the sentence the refusal prints
   in `REQUIRES_BECAUSE`: the factory refuses the combination at generation time, the pruner refuses to
   create it later (`tests/test_pruning.py::test_the_pruner_refuses_to_orphan_an_adapter_it_would_leave_behind`),
   and both ends matter.

## 7. src/slipwai/ — wiring

Every path below is relative to `src/slipwai/`.

- **`project/backing_services.py`** — `backing_service_service_files`, the layout table, keyed by language then feature,
  mapping destination paths under `apps/service/` to asset filenames. This is where the adapters
  actually get copied.
- **Dependencies** — each language module owns its own: `service_package_json` in
  `project/languages/typescript.py`, `python_requirements` in `project/languages/python.py`, and for Go a
  new committed module variant under `assets/languages/go/modules/` plus its entry in `go_module_variant`
  in `project/languages/go.py`. Versions are pinned inline here; the names must match
  `PACKAGE_EDITS`.
- **Prose that names infrastructure** — `backing_services_readme` and `backing_services_gates` in
  `project/backing_services.py`, `agent_guidance` in `project/guidance.py`, `project/agent_settings.py`,
  and `build_artifacts` in `project/gitignore.py`. Each is a table keyed by feature (section 3) rather
  than one block, because the answers are independent: a SQLite project has no Compose file to
  describe, and a Keycloak-only project has a Compose file but nothing to migrate. A new option is a
  row; the lookup already exists.
- **`BACKEND_TOOLING`** in `backends.py` — one `install`/`migrate`/`integration`/`ci_image` set per *language*,
  not per feature, and the default for whichever feature declared it needs one. If your option's migrate or
  integration command is not the language's own, add a `FEATURE_TOOLING` row keyed language then feature
  (section 3) rather than a fourth key here; `feature_tooling(language, feature)` is what the call sites
  read.

## 8. Markers — the one rule that is not obvious

Pruning only ever **subtracts**. The factory already cut the branch it was not asked for, so there
is no "keep this instead when the feature is absent" marker and there cannot be one — the target
would simply vanish. An alternative has to be written so both states are valid at once:

- the generated `Makefile` puts `INTEGRATION_TEST :=` inside the marked block and
  `INTEGRATION_TEST ?=` outside it, so deleting the block activates the fallback;
- `services-up` tests for the Compose file the prune deletes, rather than being wrapped in a marker,
  because its condition is "any container at all" — which no single feature's region can express.

A region two features both need is the one thing a marker can say beyond one name: write
`backing-service:keycloak|users-keycloak:begin` and the region stays while **either** feature is kept. The
pruner rewrites the marker to name only the features still holding it open, so a dropped answer is not
offered again, and removes it with the last one. That is how one Keycloak container serves the staff realm
and the customers realm — the Compose block, the `.env.example` port, the README and the Java OIDC
dependencies are all shared regions; each realm's own file, keys and adapter are the feature's alone. It
is still subtraction only: nothing is kept by the *absence* of a feature.

Markers must not nest, must balance, and must live in a declared file (section 6, item 6).

## 9. Committed locks

`scripts/regenerate-locks.py` produces every committed lock by generating a real project and letting
the ecosystem's own tool resolve it. Never hand-write one: a manifest and its checksums have to move
together, or the generated project's first install refuses to run.

If your option adds a TypeScript dependency, add its feature to `LOCK_FEATURES` in
`project/languages/typescript.py` — and note
that this **doubles** the committed lockfile count, because `selections()` in that script enumerates
every combination of `LOCK_FEATURES`. For Go, add a module variant directory. Then:

```sh
make locks        # scripts/regenerate-locks.py — writes every committed lock (needs network)
make check-locks  # reports staleness, changing nothing
```

## 10. Tests and docs

- `tests/test_catalog.py` asserts `axis_options("event-store", language)` equals a **literal
  list** — a new event-store option means editing it, and the count assertion for `http` two lines
  below is the same shape.
- Add the assertions that would have caught a half-port: the adapter arriving with its contract
  (`tests/test_backing_services.py::test_the_selected_adapters_arrive_with_the_contract_that_keeps_them_honest`),
  the Docker-free gate still passing
  (`tests/test_backing_services.py::test_the_sqlite_store_is_proved_inside_the_docker_free_gate` is the
  template for an infrastructure-free store), and the axis still answerable again later in a generated
  project (`tests/test_axes.py::test_a_generated_project_answers_each_axis_again_on_its_own`).
- `docs/axes.md` — the axis table's answers row, and the "what arrives" table with its dependency
  column.
- `docs/requirements.md` — if the option needs a tool on the developer's machine.

## 11. A new axis — a new kind of tool

Most of the machinery is already data-driven and needs **no** change: `axis_applies`, `axis_options`,
`catalog_axis_default` (in `axes.py`), `Selection`, `resolve_selection`, `prompt_axis`, `argument_scan_with_axes`,
`selection_summary`, the `--<axis>` CLI flag, and the `selection` block in `project.json` all iterate
`CATALOG["axes"]`. A new axis costs three code edits and one large asset debt.

The code edits:

1. **`validate_axes`** in `axes.py` — `set(axes) != {"event-store", "http", "auth", "users"}` is a
   hard-coded set; add the axis and update the message. This is deliberate: an axis is a shape the whole
   generator leans on, not a config entry, so the catalog cannot grow one silently. The same function
   holds a feature's name to the option's own or `<axis>-<option>` (`users-keycloak`, because `keycloak`
   was already the staff axis's), and refuses a feature owned by two axes.
2. **The profile-gating refusal reason** in `selection.py`, inside `resolve_selection` — the
   `if axis == "event-store"` branch supplies
   the human explanation for why an axis is not available on a profile. If your axis is gated to one
   profile, give it its own reason; the generic `else` branch names the profile but not the *why*.
3. **`prune.py`'s `AXES`** — a top-level entry with `prompt` and `options`, plus `REQUIRES` and
   `REQUIRES_BECAUSE` if it depends on another axis. `governed`, `answered` and `axis_options` are generic
   and need nothing.

If the axis is big enough to earn a module of its own outside `project/` — most are not — add it to
`TIERS` in `scripts/check-structure.py`, which refuses a module belonging to no declared tier. A
module under `project/` needs no such edit: that whole directory is one tier.

In the catalog the axis needs `prompt`, `description` (what every answer has in common), `profiles`,
`absent` (the no-infrastructure answer, which may not declare a container and must be offered under every
target), `options` (at least two, each declaring `backends` and `targets`), `always` (usually `[]`), and
an entry in the top-level `default` block. Note that `validate_axes` asserts `event-store`'s `always == ["memory"]`
specifically — if your axis has an un-prunable adapter that its contract runs against, model it the
same way and consider whether that assertion should become general.

The asset debt is the actual cost, and it is bigger than everything above:

- An axis names a **role**, so it needs a **port**, every adapter behind it, and one contract suite
  run against all of them — in every backend you claim it for. A broker axis means an outbound-events
  port and a contract that both a fake and a real broker satisfy. That is section 2's rule applied
  three or four times over.
- It needs a no-infrastructure answer that is genuinely usable, because that is what `make verify`
  runs against on a machine with no Docker.
- It probably needs a canonical skill that teaches the role, the way `event-sourcing` teaches the
  event store, plus `{{example: <skill>/<id>}}` snippets for **every** language in `catalog.json` —
  a marker with a missing snippet fails `make verify` for every backend at once (see the
  `add-language` skill, section 6).

If that debt cannot be paid now, the honest move is not a new axis. It is to say so.

## 12. Verify

```sh
make verify
make check-locks
```

`make verify` scaffolds every `profile x language x frontend` combination plus the backing-service
variants and runs each one's native gate, so most omissions surface at a predictable point: a
catalog/pruner feature mismatch raises from `validate_axes` (in `axes.py`) before anything generates; a missing
layout entry raises `KeyError` from `[language]`; a missing example snippet raises `GenerationError`.
Two things it cannot catch, so check them by hand:

- **The Compose file.** Nothing runs `docker compose` during `make verify`. A marked region that
  leaves the file invalid after pruning is invisible to the gate — run `docker compose config` on a
  generated project, and on a pruned one.
- **The integration suite actually running.** A suite excluded from the default gate and never wired
  into `make test-integration` passes by being absent. Generate a project with the option, start its
  containers, and watch the test fail before you make it pass.
