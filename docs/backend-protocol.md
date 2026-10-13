<!-- Brought from slipwai-cruise-2 c6f1e74, specs/001-slipwai-2-language-addons/contracts/
     backend-protocol.md. The experiment's slice ids are gone: version 2 never had these answers in its
     keel, so when each one moved is provenance of a repository that will not exist.
     tests/test_registry.py holds the member table below to PROTOCOL in src/slipwai/registry.py. -->

# Contract — the backend protocol and the registry

This page lists **every** member of the protocol at once, because packages are built against it
concurrently and a member that appears later is a contract that moved under someone. Each member is either
**required** (every backend must answer it, or the registry refuses to load) or **declared, not yet
required**. A member becomes required in the commit that deletes the table it replaced, and never before
every backend answers it. `tests/test_registry.py` holds the member table below to
`slipwai.registry.PROTOCOL`, so a change to a member's status changes both, or the gate is red.

## Where it lives

| Thing | Module | Tier (`scripts/check-structure.py`) |
|---|---|---|
| The protocol (`Member`, `PROTOCOL`), the objects (`Family`, `Backend`, `Language`), `Registry`, `load`, `check_catalog`, `registry`, `RegistryError` | `src/slipwai/registry.py` | **contract**, which lets `images.py`, `backends.py` (contract), `tooling.py` and `toolkit.py` (answers) and every `project/` part read it |
| Each language's object, `LANGUAGE` | `src/slipwai/project/languages/<module>.py`: none today — `go`, `python`, `typescript`, `java` (the family, no backend of its own), `java-quarkus` and `java-spring` are packages, `packages/<name>/slipwai_language_<name>/` (the package contract) | parts |
| A language's answers by group, merged into its `LANGUAGE` | one module per group inside the package: toolchain, deploy, layout, project, prune rows | the package's own, not the keel's |
| The list of built-in languages, `LANGUAGES` | `src/slipwai/project/languages/__init__.py` | parts |

`registry.py` never imports a language module statically. `registry` delegates by name, at call time, to
`slipwai.loaded`, which builds the registry from two sources: the built-in package
(`slipwai.project.languages`, its `LANGUAGES`) and every package in the language directory
(`SLIPWAI_LANGUAGES`, default `~/.slipwai/packages`), read by the directory loader (FR-009) and imported
after the catalog is merged. That is the plugin direction: languages depend on the keel, and the keel discovers
them. A built-in package's own `__init__` imports its modules statically, which is what the frozen
executable's analysis follows; the executable keeps every the keel module through `collect_submodules`.

`Registry.root(owner)` is the directory holding `owner`'s `assets/`: a loaded package's own directory for a
backend or family it declares, and the keel's for a built-in. Readers of a language's files ask it, and never
build a path into the keel's `assets/`. A package that fails to load is refused as that package, in one line
; a fault in a built-in still stops every verb. the package contract fixes the
package tree, `language.json`, the range grammar, the merge and the refusals.

## The objects

```python
Member[T](name: str, level: "family" | "backend", required: bool, kind: type, shape: str)
Family(name: str, answers: Mapping[Member, object] = {})
Backend(key: str, family: str, answers: Mapping[Member, object] = {})
Language(families: tuple[Family, ...] = , backends: tuple[Backend, ...] = )
```

- A language module exports one `LANGUAGE`. A family that is its own leaf (`typescript`, `python`, `go`)
 declares both a `Family` and a `Backend` with the same name. The `java` package declares only its `Family`,
 and the `java-quarkus` and `java-spring` packages each declare only a `Backend` whose `family` is `"java"`;
 `Registry.sources(key)` is where a backend's files are found, its own root then its family's.
- `answers` is keyed by the `Member` constant (`READY_PATH`, not `"ready_path"`), so a misspelt member is an
 undefined name and never a silent key.
- **Inheritance** (FR-001): `Registry.answer(key, MEMBER)` returns the backend's own answer where it has
 one, and otherwise its family's. `level` says where an answer *normally* lives, and either level may
 answer any member. A framework that overrides a family answer gets its own (scenario 4). A family answer
 is shared by every backend of the family, so write one only where every framework agrees. That is
 test for the Maven rows.
- **`None` is an answer.** Presence is what counts, never truthiness. `postgres_sslmode` depends on this.
- **`Registry.answer_or(key, MEMBER, default)`** is `answer` with a default where neither the backend nor
 its family answers: the read for a member whose absence is an answer (*never required*: `mutation_note`,
 `identity_outstanding`, `mutation_scoping`, scenario 11). Presence is still the test, so `""` is returned, not
 the default. **`Registry.family_answer(name, MEMBER)`** is a family's own answer, for what is read per
 family: `pin_files`, `renovate_rules`, `npm_workspace`, `browser_apps`, `shared_code` and, for a browser app,
 `formatter`. A
 framework's answer to those is never read. Core reads a further set through `Registry.answer` but once per
 family, from the family's **first service's** backend: `ci_toolchain_setup`, `repository_files`,
 `makefile_variables` and `tooling`'s `ci_image` and `container_setup`. Only the framework of that first
 service would be heard on them, so a framework that answers one differently from its family is refused at load
 (`registry.FAMILY_ONLY`, item 7 below; D113, D118, closing D109). A later MINOR that makes CI per service lifts
 the refusal for what it serves.

## What loading refuses — `RegistryError(ValueError)`

`load(languages, protocol=PROTOCOL)` collects every fault into **one** `RegistryError`, whose message is
one line. The faults are these:

1. A required member that neither the backend nor its family answers: `backend go is missing ready_path`.
2. A required member answered with the wrong kind (`isinstance(value, member.kind)` fails): `backend go
 answers ready_path with int, where the protocol wants str`.
3. An answer keyed by a member the protocol does not declare: `backend go answers ready_paths, which the
 protocol does not declare`. The same holds for a family.
4. A backend naming a family no loaded language declares: `backend java-spring names family java, which no
 loaded language declares`.
 A member the keel reads from the family alone (`registry.READ_PER_FAMILY`: `pin_files`, `renovate_rules`,
 `shared_code`, `npm_workspace`, `browser_apps`; and `formatter` where the family answers `npm_workspace`, the browser app's
 family) answered by a backend and not by its family: `backend mylang-plain answers renovate_rules, which the keel
 reads from family mylang, and the family does not answer it` (A73, D109). The backend's answer would never be
 read and generation would fail on the family's; a package is refused for it at load, naming itself.
5. A family name or a backend key declared twice.
6. A malformed answer, named by its owner and never a crash: an answer key that is not a `Member` (`backend go
 answers a key that is not a protocol member: 'ready_paths'`), `answers` that is not a mapping, a language,
 family or backend that is not a `Language`, `Family` or `Backend`, and a `name`, `key` or `family` that is
 not a `str`.
7. A **family-only field** answered differently from the family's reference : `tooling.ci_image`,
 `tooling.container_setup`, `ci_toolchain_setup`, `repository_files`, `makefile_variables`, and `ci_image` or
 `container_setup` inside any `feature_tooling` entry — what the keel reads once per family, from its first service.
 A backend's value is its own answer, else its family's. The reference is the family's own answer; where the family
 does not answer, the answer of the backends declared by the **family's own package** (the language declaring the
 `Family`, C004, D45), whatever loads first; where that package declares none, the frameworks are compared
 pairwise. Strings and `None` by value, callables by identity: a framework may inherit or re-export the family's
 function, never replace it. One fault per backend, naming every differing field, the family, the reference and
 the fix: `backend java-x answers tooling.ci_image differently from family java; the keel reads it once per family —
 leave it unanswered to inherit the family's` (`… from family typescript (backend typescript); …` where the
 reference is the family package's backend). The family package's own backends that disagree are each refused
 (`… differently from backend b, both of family f's own package; the keel reads it once per family — answer it once,
 on family f`); frameworks that disagree pairwise are each named (`… both frameworks of family f, which does not
 answer it; …`). The fault joins the others in the one `RegistryError`, so phase 2 refuses the package and
 the conformance suite reports it under `protocol`. In phase 2 a package is admitted against those kept before it,
 so of two frameworks that disagree pairwise only the later is refused today (S23 plan, *Handed back*).

`check_catalog(catalog, registry)` is what replaced `expected_backends` (scenario 6). It refuses in one
line, naming each backend under its direction: *in `catalog.json` with no registry object*, *in the registry
but not in `catalog.json`*, and *a family that differs between the two*.
`catalog.validate_catalog` calls it where the hard-coded set used to be. `cli.main` runs that validation
before every verb, and turns a `RegistryError` into `slipwai: <message>` on stderr and exit status 1. There
is no traceback, and it happens before any verb writes a file (scenario 8).

Catalog fields stay in `catalog.json` until: `label`, `framework`, `targets` and every
per-option `backends` list. The naming rule (FR-005) is still `catalog.validate_backends`, reading the
catalog.

## The members

**Status** is the state at the head of this contract's last edit. *Required* means loading refuses without
it. *Declared* means it is in `PROTOCOL` with `required=False`, and nothing reads it yet. **Replaces** is the
table (FR-002, `docs/backend-obligations.md` §3) whose answers move into the member, and which its slice
deletes. **Shape** is the value, and it is fixed here. A slice that finds a shape cannot be kept changes it
here in its own commit and says why.

| Member | Level | Status | Replaces | Shape |
|---|---|---|---|---|
| `service_files` | backend | required | `BACKENDS` → module `service_files` | callable `(event: bool, selection: Selection, target: str) -> dict[str, str]`, paths relative to the service. `event` is **deprecated**: it says the project is on the modelled profile, which was all a backend had to go on when Event Modeling and event sourcing were one answer. The write model is per service and is `selection.option("write-model")`. The signature does not change — the parameter is still passed, and still says what it always said |
| `name_service` | backend | required | `BACKENDS` → module `name_service` | callable `(project_name: str, service: App, files: dict[str, str]) -> dict[str, str]` |
| `repository_files` | backend | required | `BACKENDS` → module `repository_files` | callable `(project_name: str, files: dict[str, str], services: list[App], verify: str) -> dict[str, str]`; called once per family, on its first service's backend |
| `ready_path` | backend | required | `READY_PATHS` (`probes.py`) | `str`: the path answering "send me traffic" |
| `health_body` | backend | required | `HEALTH_BODIES` (`probes.py`) | `str`: the liveness body, as prose quotes it |
| `tooling` | backend | required | `BACKEND_TOOLING`, `MAVEN_TOOLING` (`backends.py`) | `backends.Tooling` (the TypedDict, fields unchanged) |
| `feature_tooling` | backend | required | `FEATURE_TOOLING` (`backends.py`) | `dict[str, dict[str, str]]`: feature → tooling overrides; `{}` where none |
| `executables` | backend | required | `BACKEND_EXECUTABLES`, `MAVEN_EXECUTABLES` (`backends.py`), read by `toolkit.executable_paths` | `frozenset[str]`: paths under `APP` |
| `dev_command` | backend | required | `backends.dev_command`'s table | callable `(qualifier: str, path: str, verify: str) -> str` |
| `compose_caches` | backend | required | `COMPOSE_CACHES`, `MAVEN_COMPOSE_CACHES` (`backends.py`) | `tuple[str, ...]` |
| `persistence_directory` | backend | required | `event_store_directory`, which it renames | callable `(path: str) -> str`: where one service's driven persistence adapters live, on either rung — the event store's on `events`, the repository's on `state`. Prose that points at them says which it means |
| `event_store_directory` | backend | deprecated | the name `persistence_directory` replaces | the same callable. Answered by a package written before the rung was a question; read where `persistence_directory` is unanswered, until 2.1 deletes it (*Renamed members*) |
| `native_commands` | backend | required | `native` (`project/native_commands.py`), with the Go constants it imports | callable `(path: str, verify: str) -> dict[str, str]`, keyed by exactly `native_commands.TARGETS` |
| `formatter` | family | required | `FORMATTERS` (`project/native_commands.py`) | `str \| None`: the `format` recipe line; `None` where the family has none (Java today) |
| `image_builder` | backend | required | `IMAGE_BUILDERS` (`images.py`) | `dict[str, Any]`, the entry as today without its `descriptor` key, which only pointed into `SERVICE_DESCRIPTORS`: `service_descriptors` names the file itself |
| `migrations_in_production` | backend | required | `MIGRATIONS_IN_PRODUCTION` (`images.py`) | `dict[str, Any]`, the entry exactly as today |
| `postgres_sslmode` | backend | required | the language's half of `POSTGRES_SSLMODE` (`images.py`) | `dict[str, str \| None]`, keyed by the managed-database kind the keel declares (`rds`, `flexible-server`); every kind answered, `None` written out |
| `service_descriptors` | backend | required | `SERVICE_DESCRIPTORS` (`images.py`) | `dict[str, str]`: descriptor file → text; `{}` where none |
| `ci_toolchain_setup` | family | required | `toolchain_setup`'s table (`project/ci_workflows.py`) | callable `(services: list[App]) -> str` |
| `write_side_files` | backend | required | `WRITE_SIDE_FILES` (`project/service_layouts.py`) | `dict[str, dict[str, str]]`: feature → path under the service → asset, which is what a service on the `events` rung is given. Beside the features, one `state` key holding the same shape again: what a service answered `write-model: state` is given instead — the repository port, its adapters per store, and the migration for a versioned state table. `state` is not a feature and is never read as one (`rungs.rung_rows`). A backend that declares no `state` block answers such a service with nothing, which `slipwai package check` names |
| `read_side_files` | backend | required | `READ_SIDE_FILES` (`project/read_side_layouts.py`) | the same shape, `state` key included; the keel still merges the two into what `backing_service_service_files` reads |
| `flag_reader` | backend | required | `FLAG_READERS` (`project/flags.py`) | `flags.FlagReader` |
| `entry_wiring` | backend | required | `ENTRY_WIRING` (`project/flag_route.py`), keyed by HTTP option | `dict[str, EntryWiring]`: the HTTP options this backend answers → wiring; `{}` where none |
| `flag_resource` | backend | required | `FLAG_RESOURCES` (`project/flag_route.py`), keyed by HTTP option | `dict[str, Resource]`, the same way |
| `entry_store` | backend | required | `ENTRY_STORES` (`project/entry_stores.py`) | `EntryStore \| None`; `None` for a framework that opens its own store (both Java backends today) |
| `shared_code` | family | required | `SHARED_CODE` (`project/rules.py`) | `str`: the architecture page's paragraph |
| `gitignore` | backend | required | `per_backend` (`project/gitignore.py`) | `str`: lines ending in `\n` |
| `agent_permissions` | backend | required | `per_backend` (`project/agent_settings.py`), `MAVEN_PERMISSIONS` | `list[str]` |
| `gate_description` | backend | required | `gates` (`project/docs.py`) | `str` |
| `event_model_paths` | backend | required | `paths` (`project/event_model.py`) | callable `(project_name: str, service: str) -> dict[str, str]`, keyed `events`, `domain`, `usecase`, `test` and `repository` — the port a service on the `state` rung loads and saves current state through, where an event-sourced one has the event-store port. Only the state-stored half of `docs/event-modeling-to-code.md` reads it; `event_model.code_paths` fills it from `domain` for one MINOR where a backend has not answered it, and `slipwai package check` names the gap |
| `fast_targets` | backend | declared, **never required** | new in slice 5.7 | a `tuple` of names from `native_commands.TARGETS` that are fast enough to run on every RED-GREEN-REFACTOR increment. Absent means the default, `("test",)`: the native test suite alone, with integration, mutation, the image build and the audit left to `make verify` before the merge. A backend whose integration suite really is quick says so here rather than being told it is slow |
| `mutation_tool` | backend | required | `tools` (`project/mutation.py`) | `str` |
| `mutation_note` | backend | declared, **never required** | `MUTATION_NOTES` (`project/mutation.py`) | `str`; absence is the answer "nothing to say" (`docs/backend-obligations.md` §3), so
| `prune_rows` | family | required | `LANGUAGES`, `PACKAGE_EDITS`, `OWNED_FILES`' family column, `MARKED_FILES_BY_LANGUAGE` (`assets/backing-services/prune.py`) | `dict` with exactly four keys : `marked_files`, a sequence of paths relative to a service, which may glob (was `MARKED_FILES_BY_LANGUAGE`); `owned_files`, feature → sequence of paths relative to a service, a feature absent owning nothing (was the family's column of `OWNED_FILES`); `package_edits`, feature → `{"packages": sequence, "scripts": sequence}`, a feature absent adding nothing (was `PACKAGE_EDITS`); `manifest`, `"package.json"`, `"pyproject.toml"`, `"go.mod"` or `None`, the the keel uninstaller that removes those packages (was the dispatch by language). Every feature is one of the pruner's `FEATURES`, and every backend of a family answers the same rows; `catalog.check_prune_rows` refuses anything else. **Emitted** (FR-035) by replacing the keel's one `ROWS: dict[str, dict] = {}` line with `ROWS: dict[str, dict] = json.loads(r"""…""")`, the project's families in service order, as `json.dumps(indent=2)` |
| `procfile` | backend | required | `procfiles`' `family_of(backend) != "python"` (`project/infra.py`, D31) | callable `(project_name: str, service: App) -> str`, or `None` where the backend's build needs no Procfile; read only for a service whose `image_builder` tool is `pack`. `python` answers; the rest answer `None` |
| `pin_files` | family | required | `pin_files`' `"python" in families` (`project/pins.py`) | `dict[str, str]`: path at the repository root → text, merged in family order after the keel's `.editorconfig` and `.nvmrc`; `{}` where none. `python` answers `.python-version` |
| `makefile_variables` | family | required | `go_modules_variable` and `GO_MODULES` (`project/native_commands.py`), found by -> str`, given the family's service paths in service order, returning the Make variable definitions the family's recipes read; `None` where they read none. `go` answers `GO_MODULES` |
| `renovate_rules` | family | required | `managers_present`' family checks, `GROUPS`' family rows and `toolchain_managers`' Python branch (`project/renovate.py`) | `renovate.RenovateRules(managers, group, toolchain)`: `tuple[str, ...]`, the Renovate managers that read this family's files; `(name, managers, what) \| None`, its minor-and-patch group; `dict \| None`, the custom manager reading its toolchain version out of a workflow, whose `depNameTemplate` is the pin's name. Read for the families present **in registry order**, between the keel's npm group and its workflow-actions and containers groups; the npm group and the Node manager follow the npm workspace and stay the keel's. A loader that replaces `registry` keeps a stable family order, or this file's bytes move |
| `opt_in_flag_transports` | backend | required | `OPT_IN_TRANSPORT`'s reader set (`project/flag_route.py`) | `frozenset[str]`: the targets whose opt-in flag transport this backend's reader reads; `frozenset` where none. Every target named is a key of `flag_route.OPT_IN_TRANSPORT`, which keeps only target → transport name; `tests/test_project_part_answers.py` names a backend that names another |
| `identity_outstanding` | family | declared, **never required** | `IDENTITY_OUTSTANDING` and `USERS_OUTSTANDING`' family rows (`project/backing_service_prose.py`) | `dict[str, str]`: identity feature (`keycloak`, `users-keycloak`, unique across the `auth` and `users` axes) → the README paragraph on what the project still owes. A feature absent, or the member absent, gets the keel's `IDENTITY_DEFAULT` for that feature (scenario 11). `java` answers both, byte for byte |
| `mutation_scoping` | backend | declared, **never required** | `mutation_command`'s `"go" in backends` (`project/mutation.py`) | `str`: the paragraph `commands/mutation.md` carries after the tools, once per distinct answer; absence is the answer "nothing to say". `go` answers |
| `npm_workspace` | family | declared, **never required** | the eleven npm-workspace checks spelling `typescript` (`services.py`, `project/shared_packages.py`, `ci_workflows.py`, `compose.py`, `agent_settings.py`, `gitignore.py`, `native_commands.py`, `guidance.py`, `frontend.py`, `biome.py`), `frontend.py`'s import of `typescript.py`, and the `typescript-backend*` workspace locks under the keel's `react-vite` (FR-034, D50) | `npm_workspace.NpmWorkspace(member_lock, workspace_lock, image, biome, biome_pins)`: a family that answers it has services that are npm packages in the project's one workspace; absence is the answer "not an npm package". A browser app is written in the first family in registry order that answers it. the npm-workspace contract states both sides |
| `browser_apps` | family | declared, **never required** | nothing yet: `react-vite` is still the keel's, under `npm_workspace.KEEL_APPS` (17.1) | `dict[str, npm_workspace.BrowserApp]`: the browser apps this family writes, by the name `--frontend` is typed as, each one the directory its material is copied from. A family answering it answers `npm_workspace` too, because a browser app is an npm package in the workspace that answer declares, and it is refused at load otherwise. A family's name wins over the keel's: the family ships the lock that resolves the app it ships |

`backing_service_service_files` (`project/backing_services.py`, FR-002) is not a member. It is the keel's
function over `write_side_files` and `read_side_files`, and

## Renamed members

A member's name is a language package's to answer, and a package is a repository of its own with a release
of its own — so renaming one is a change every language has to make, and they will not all make it in the
same week. A rename is therefore a MINOR with a window. The new member is declared and required; the old
one stays in `PROTOCOL` as **deprecated**, carried as the new member's `was`; and an answer given under
either name is read, the new one first (`src/slipwai/renamed.py`). A package that answers only the old name
loads, generates and passes `slipwai package check` for the whole window. The MINOR that closes it deletes
the old member, and the keel's *backend x is missing y* is then the only answer.

| New name | The name it replaces | Opened | Closes |
|---|---|---|---|
| `persistence_directory` | `event_store_directory` | 2.0 | 2.1 |

Renaming is not how a member's **shape** changes. A shape that cannot be kept is changed in this page in
its own commit, with the reason (*The members*, above) — a name that means one thing to one language and
another to the next is worse than either shape.

## Tables that are not members, and why

| Table | Where | Why no member |
|---|---|---|
| `expected_backends` | `catalog.py` | Gone. `check_catalog` compares the catalog with the registry instead |
| `PACKAGE_ADDITIONS`, `FEATURE_REQUIREMENTS` | the `typescript` and `python` packages | Inside the language that owns them, keyed by feature, and read only by that package. They moved with it in
| `WEB_PACKAGE_ADDITIONS`, `web_package_json`, `web_lock_suffix`; `workspace_manifest`, `workspace_scripts` | `project/frontend.py`; `project/shared_packages.py` | The browser app's manifest and the workspace root's, which are the keel's `react-vite` side of the npm-workspace contract (the npm-workspace contract), keyed by feature and naming no language |
| `WRAPPERS`, `UPGRADE_PATHS`, `TOOLING` (`programme.py`), `SETUP`/`GITLAB_IMAGES` (`adopted_ci.py`), `LANGUAGES` (`structure.py`) | adoption | Keyed by the ecosystem of a repository the factory did not make. Adoption needs no language (FR-002), so they stay in the keel |
| `label`, `framework`, `targets`, per-option `backends` | `catalog.json` | The catalog fragment's, from |
| The adoption modules' spellings: `ecosystems.py`, `platform.py`, `programme.py`, `structure.py`, `delivery_facts.py`, `convergence.py`, `wrappers.py`, `project/adopted_ci.py` | adoption | The same reason as the row above, for every backend or family name these modules spell. `tests/test_the keel_names.py` exempts them by name (scenario 10) |
| `CANON` (`toolkit.py`) | the keel | The language the toolkit's own prose and canonical snippets (`assets/languages/typescript/examples/`) are written in: the keel's material, read from the keel's root where no service speaks, so adoption needs no language. `tests/test_the keel_names.py` exempts `typescript` in `toolkit.py` alone. The ten npm-workspace checks that spelled it are the `npm_workspace` member |
| The catalog's default backend (`catalog.default_backend`) | the keel | Gone: the first backend of the merged catalog, so the keel names none |
| `DOCUMENTS`, `EXPORTERS` (`project/openapi.py`), `API_CONTRACTS` (`project/rules.py`), the five transports in `ENV_FEATURES` (`backends.py`) | the keel | Keyed by the feature that answered the `http` axis, and naming no backend: the shape the experiment's gaps review left in the keel. **Would move** when the catalog's options move into each language's fragment (FR-019): a row keyed by an option the keel no longer declares travels with the language that offers it, as `ENTRY_WIRING` and `FLAG_RESOURCES` did |
| `IDENTITY_DEFAULT` (`project/backing_service_prose.py`), `OPT_IN_TRANSPORT` and `DEFAULT_TRANSPORT` (`project/flag_route.py`), `FIRST_GROUPS`/`LAST_GROUPS` (`project/renovate.py`), `.editorconfig` and `.nvmrc` (`project/pins.py`) | the keel | What the keel says where a language says nothing, and what follows the target, the forge or the npm workspace rather than a language |

## How a slice moves a member

1. Add the answer to every backend (or its family) in `project/languages/*.py`, keyed by the member constant.
2. Make the reader call `registry.answer(backend, MEMBER)`, and delete the table.
3. Flip `required=True` in `PROTOCOL` and the *Status* cell above, in the same commit.
4. Replace the table's row in `docs/backend-obligations.md` §3 with the member's row, whose location is
 `registry.py`. `tests/test_backend_obligations.py` then holds that row to the registry (every backend
 answers it) rather than to a dict literal.
5. Keep `make starters` byte-identical (FR-004).

Slices merge in split order. Two slices that append answers to the same `answers={...}` literal meet there,
and the host resolves the conflict by keeping both.
