<!-- Brought from slipwai-cruise-2 c6f1e74, specs/001-slipwai-2-language-addons/contracts/
     backend-protocol.md. The experiment's slice ids are gone: version 2 never had these answers in its
     keel, so when each one moved is provenance of a repository that will not exist.
     tests/test_registry.py holds the member table below to PROTOCOL in src/slipwai/registry.py. -->

# Contract — the backend protocol and the registry

The **backend protocol** is the set of questions that a language package must answer. Each question is a
**member** of the protocol. This page lists **every** member at once. Packages are built against the
protocol at the same time as each other, so a member that appeared later would be a contract that changed
under somebody's feet.

Each member is in one of two states:

- **Required.** Every backend must answer it. If a backend does not, the registry refuses to load.
- **Declared, not yet required.** The member is in the protocol, but nothing requires it yet.

A member becomes required in the same commit that deletes the table it replaced. It never becomes required
before every backend answers it.

`tests/test_registry.py` holds the member table on this page to `slipwai.registry.PROTOCOL`. So if you
change a member's status, change both, or the gate is red.

## Where it lives

| Thing | Module | Tier (`scripts/check-structure.py`) |
|---|---|---|
| The protocol (`Member`, `PROTOCOL`), the objects (`Family`, `Backend`, `Language`), `Registry`, `load`, `check_catalog`, `registry`, `RegistryError` | `src/slipwai/registry.py` | **contract**. This tier lets `images.py`, `backends.py` (contract), `tooling.py` and `toolkit.py` (answers) and every `project/` part read it |
| Each language's object, `LANGUAGE` | `src/slipwai/project/languages/<module>.py`: none today. `go`, `python`, `typescript`, `java` (the family, with no backend of its own), `java-quarkus` and `java-spring` are packages, each its own repository (`slipwai-language-<name>`), installed into the package directory as `<name>/slipwai_language_<name>/`. The keel's `packages/` holds only the toy and the two targets its own suite tests against | parts |
| A language's answers by group, merged into its `LANGUAGE` | one module per group inside the package: toolchain, deploy, layout, project, prune rows | the package's own, not the keel's |
| The list of built-in languages, `LANGUAGES` | `src/slipwai/project/languages/__init__.py` | parts |

`registry.py` never imports a language module directly. At call time, `registry` passes the request by
name to `slipwai.loaded`. `slipwai.loaded` builds the registry from two sources:

1. **The built-in package**, `slipwai.project.languages`, and its `LANGUAGES`. This tuple is empty today:
   every language is a package.
2. **Every package in the language directory.** The directory is `SLIPWAI_LANGUAGES`, and the default is
   `~/.slipwai/packages`. The directory loader (FR-009) reads these packages. Slipwai imports them after
   it merges the catalog.

This is the plugin direction: languages depend on the keel, and the keel discovers them. A built-in
package's own `__init__` imports its modules directly, because the frozen executable's analysis follows
those imports. The executable keeps every keel module through `collect_submodules`.

`Registry.root(owner)` is the directory that holds `owner`'s `assets/`:

- For a backend or family that a loaded package declares, it is that package's own directory.
- For a built-in language, it is the keel's directory.

Code that reads a language's files asks `Registry.root`. It never builds a path into the keel's `assets/`.

If a package fails to load, slipwai refuses that package, in one line. A fault in a built-in language
still stops every command. The package contract fixes the package tree, `language.json`, the range
grammar, the merge and the refusals.

## The objects

```python
Member[T](name: str, level: "family" | "backend", required: bool, kind: type, shape: str, was: str = "")
Family(name: str, answers: Mapping[Member, object] = {})
Backend(key: str, family: str, answers: Mapping[Member, object] = {})
Language(families: tuple[Family, ...] = (), backends: tuple[Backend, ...] = ())
```

- **A language module exports one `LANGUAGE`.** Some families are their own leaf: `typescript`, `python`
  and `go`. Each of those declares a `Family` and a `Backend` with the same name. The `java` package
  declares only its `Family`. The `java-quarkus` and `java-spring` packages each declare only a `Backend`,
  whose `family` is `"java"`. `Registry.sources(key)` gives the places where a backend's files are found:
  first its own root, then its family's root.
- **`answers` is keyed by the `Member` constant**, for example `READY_PATH`, not `"ready_path"`. So a
  misspelt member is an undefined name. It is never a silent key.
- **Inheritance (FR-001).** `Registry.answer(key, MEMBER)` returns the backend's own answer if it has one.
  Otherwise it returns the family's answer. `level` says where an answer *normally* lives, but either level
  can answer any member. A framework that overrides a family answer gets its own answer (scenario 4). Every
  backend of a family shares the family's answer. So write a family answer only where every framework
  agrees. The Maven rows follow this rule.
- **`None` is an answer.** What counts is whether an answer is present, never whether it is truthy.
  `postgres_sslmode` depends on this.
- **`Registry.answer_or(key, MEMBER, default)`** is `answer` with a default. It returns the default when
  neither the backend nor its family answers. Use it for a member whose absence is itself an answer. These
  members are *never required*: `mutation_note`, `identity_outstanding` and `mutation_scoping`
  (scenario 11). The test is still presence, so an answer of `""` is returned, not the default.
- **`Registry.family_answer(name, MEMBER)`** returns a family's own answer. Use it for members that the keel
  reads per family: `pin_files`, `renovate_rules`, `npm_workspace`, `browser_apps`, `shared_code`, and, for
  a browser app, `formatter`. The keel never reads a framework's answer to those members.
- **Some members are read once per family, through `Registry.answer`.** The keel reads them from the
  backend of the family's **first service**: `ci_toolchain_setup`, `repository_files`,
  `makefile_variables`, and `tooling`'s `ci_image` and `container_setup`. Only the framework of that first
  service would be heard on them. So if a framework answers one of them differently from its family,
  slipwai refuses it at load (`registry.FAMILY_ONLY`, item 7 below; D113, D118, closing D109). A later
  MINOR release that makes CI per service will remove this refusal for the members it covers.

## What loading refuses — `RegistryError(ValueError)`

`load(languages, protocol=PROTOCOL)` collects every fault into **one** `RegistryError`. The message of that
error is one line. These are the faults:

1. **A required member that neither the backend nor its family answers.** Example:
   `backend go is missing ready_path`.
2. **A required member answered with the wrong kind**, where `isinstance(value, member.kind)` fails.
   Example: `backend go answers ready_path with int, where the protocol wants str`.
3. **An answer keyed by a member that the protocol does not declare.** Example:
   `backend go answers ready_paths, which the protocol does not declare`. The same applies to a family.
4. **A backend that names a family which no loaded language declares.** Example:
   `backend java-spring names family java, which no loaded language declares`.

   This item also covers a member that the keel reads from the family only, when a backend answers it and
   the family does not. These members are `registry.READ_PER_FAMILY`: `pin_files`, `renovate_rules`,
   `shared_code`, `npm_workspace` and `browser_apps`, plus `formatter` where the family answers
   `npm_workspace` (the browser app's family). Example: `backend mylang-plain answers renovate_rules,
   which the keel reads from family mylang, and the family does not answer it` (A73, D109). The keel
   would never read the backend's answer, and generation would fail on the family's missing answer. So
   slipwai refuses the package at load, and the message names the package.
5. **A family name or a backend key declared twice.**
6. **A malformed answer.** Slipwai names its owner, and never crashes. The cases are:
   - an answer key that is not a `Member`. Example:
     `backend go answers a key that is not a protocol member: 'ready_paths'`
   - `answers` that is not a mapping
   - a language, family or backend that is not a `Language`, `Family` or `Backend`
   - a `name`, `key` or `family` that is not a `str`
7. **A family-only field answered differently from the family's reference.** The family-only fields are
   `tooling.ci_image`, `tooling.container_setup`, `ci_toolchain_setup`, `repository_files`,
   `makefile_variables`, and `ci_image` or `container_setup` inside any `feature_tooling` entry. The keel
   reads these once per family, from the family's first service.

   A backend's value is its own answer, or else its family's answer. The reference is chosen in this
   order:

   - the family's own answer
   - if the family does not answer, the answer of the backends that the **family's own package** declares
     (the language that declares the `Family`; C004, D45), whichever loads first
   - if that package declares no backends, slipwai compares the frameworks in pairs

   Strings and `None` are compared by value. Callables are compared by identity. So a framework can
   inherit or re-export the family's function, but it cannot replace it.

   Slipwai reports one fault per backend. The fault names every field that differs, the family, the
   reference and the fix. Examples:

   - `backend java-x answers tooling.ci_image differently from family java; the keel reads it once per
     family — leave it unanswered to inherit the family's`
   - `… from family typescript (backend typescript); …`, where the reference is the family package's
     backend
   - If the family package's own backends disagree, slipwai refuses each one: `… differently from backend
     b, both of family f's own package; the keel reads it once per family — answer it once, on family f`
   - If frameworks disagree in pairs, slipwai names each one: `… both frameworks of family f, which does
     not answer it; …`

   This fault joins the others in the one `RegistryError`. So phase 2 refuses the package, and the
   conformance suite reports the fault under `protocol`. In phase 2, slipwai admits a package against the
   packages kept before it. So today, of two frameworks that disagree in pairs, only the later one is
   refused (S23 plan, *Handed back*).

`check_catalog(catalog, registry)` replaced `expected_backends` (scenario 6). It refuses in one line, and
names each backend under its problem:

- *in `catalog.json` with no registry object*
- *in the registry but not in `catalog.json`*
- *a family that differs between the two*

`catalog_checks.validate_catalog` calls `check_catalog` where the hard-coded set used to be. `cli.main` runs that
validation before every command. It turns a `RegistryError` into `slipwai: <message>` on stderr, with exit
status 1. There is no traceback, and this happens before any command writes a file (scenario 8).

These catalog fields stay in `catalog.json`: `label`, `framework`, `targets` and every per-option
`backends` list. The naming rule (FR-005) is still `catalog_checks.validate_backends`, which reads the catalog.

## The members

Three of the columns need an explanation:

- **Status** is the state at this contract's last edit. *Required* means that loading refuses without the
  member. *Declared* means that the member is in `PROTOCOL` with `required=False`: a package may leave it out,
  and the keel reads a fallback, or nothing, where it does. Its *kind* is checked only where the loader holds it
  (`npm_workspace` and `browser_apps`, `loaded.py`); a required member's kind is checked by `registry.load`.
- **Replaces** is the table whose answers moved into the member, and which its slice deleted (FR-002,
  `docs/backend-obligations.md` §3).
- **Shape** is the value, and this page fixes it. If a slice finds that a shape cannot be kept, it changes
  the shape here, in its own commit, and says why.

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
| `mutation_note` | backend | declared, **never required** | `MUTATION_NOTES` (`project/mutation.py`) | `str`; absence is the answer "nothing to say" (`docs/backend-obligations.md` §3) |
| `prune_rows` | family | required | `LANGUAGES`, `PACKAGE_EDITS`, `OWNED_FILES`' family column, `MARKED_FILES_BY_LANGUAGE` (`assets/backing-services/prune.py`) | `dict` with exactly four keys: `marked_files`, a sequence of paths relative to a service, which may glob (was `MARKED_FILES_BY_LANGUAGE`); `owned_files`, feature → sequence of paths relative to a service, a feature absent owning nothing (was the family's column of `OWNED_FILES`); `package_edits`, feature → `{"packages": sequence, "scripts": sequence}`, a feature absent adding nothing (was `PACKAGE_EDITS`); `manifest`, `"package.json"`, `"pyproject.toml"`, `"go.mod"` or `None`, the manifest that the keel's uninstaller removes those packages from (was the dispatch by language). Every feature is one of the pruner's `FEATURES`, and every backend of a family answers the same rows; `catalog.check_prune_rows` refuses anything else. **Emitted** (FR-035) by replacing the keel's one `ROWS: dict[str, dict] = {}` line with `ROWS: dict[str, dict] = json.loads(r"""…""")`, the project's families in service order, as `json.dumps(indent=2)` |
| `procfile` | backend | required | `procfiles`' `family_of(backend) != "python"` (`project/infra.py`, D31) | callable `(project_name: str, service: App) -> str`, or `None` where the backend's build needs no Procfile; read only for a service whose `image_builder` tool is `pack`. `python` answers; the rest answer `None` |
| `pin_files` | family | required | `pin_files`' `"python" in families` (`project/pins.py`) | `dict[str, str]`: path at the repository root → text, merged in family order after the keel's `.editorconfig` and `.nvmrc`; `{}` where none. `python` answers `.python-version` |
| `makefile_variables` | family | required | `go_modules_variable` and `GO_MODULES` (`project/native_commands.py`), read by `native_commands.family_variables` | callable `(paths: list[str]) -> str`, given the family's service paths in service order, returning the Make variable definitions the family's recipes read; `None` where they read none. `go` answers `GO_MODULES` |
| `renovate_rules` | family | required | `managers_present`' family checks, `GROUPS`' family rows and `toolchain_managers`' Python branch (`project/renovate.py`) | `renovate.RenovateRules(managers, group, toolchain)`: `tuple[str, ...]`, the Renovate managers that read this family's files; `(name, managers, what) \| None`, its minor-and-patch group; `dict \| None`, the custom manager reading its toolchain version out of a workflow, whose `depNameTemplate` is the pin's name. Read for the families present **in registry order**, between the keel's npm group and its workflow-actions and containers groups; the npm group and the Node manager follow the npm workspace and stay the keel's. A loader that replaces `registry` keeps a stable family order, or this file's bytes move |
| `opt_in_flag_transports` | backend | required | `OPT_IN_TRANSPORT`'s reader set (`project/flag_route.py`) | `frozenset[str]`: the targets whose opt-in flag transport this backend's reader reads; `frozenset` where none. Every target named is a key of `flag_route.OPT_IN_TRANSPORT`, which keeps only target → transport name; `tests/test_project_part_answers.py` names a backend that names another |
| `identity_outstanding` | family | declared, **never required** | `IDENTITY_OUTSTANDING` and `USERS_OUTSTANDING`' family rows (`project/backing_service_prose.py`) | `dict[str, str]`: identity feature (`keycloak`, `users-keycloak`, unique across the `auth` and `users` axes) → the README paragraph on what the project still owes. A feature absent, or the member absent, gets the keel's `IDENTITY_DEFAULT` for that feature (scenario 11). `java` answers both, byte for byte |
| `mutation_scoping` | backend | declared, **never required** | `mutation_command`'s `"go" in backends` (`project/mutation.py`) | `str`: the paragraph `commands/mutation.md` carries after the tools, once per distinct answer; absence is the answer "nothing to say". `go` answers |
| `npm_workspace` | family | declared, **never required** | the eleven npm-workspace checks spelling `typescript` (`services.py`, `project/shared_packages.py`, `ci_workflows.py`, `compose.py`, `agent_settings.py`, `gitignore.py`, `native_commands.py`, `guidance.py`, `frontend.py`, `biome.py`), `frontend.py`'s import of `typescript.py`, and the `typescript-backend*` workspace locks (FR-034, D50) | `npm_workspace.NpmWorkspace(member_lock, workspace_lock, image, biome, biome_pins)`: a family that answers it has services that are npm packages in the project's one workspace; absence is the answer "not an npm package". A browser app is written in the family that ships its frontend (`browser_apps`); `member_lock` and `workspace_lock` are asked only of a family with npm services. The npm-workspace contract states both sides |
| `browser_apps` | family | declared, **never required** | the keel's own `react-vite` and `npm_workspace.KEEL_APPS` (phase 17): the keel ships no frontend | `dict[str, npm_workspace.BrowserApp]`: the browser apps this family ships, by the name `--frontend` is typed as, each one rooted at `assets/frontends/<name>` in the package. Exactly the names its `language.json` `frontends` block declares. A family answering it answers `npm_workspace` and `shared_code` too, and is refused at load otherwise. The whole contract is `docs/frontend-protocol.md` |

`backing_service_service_files` (`project/backing_services.py`, FR-002) is not a member. It is the keel's
own function over `write_side_files` and `read_side_files`.

## Renamed members

A language package answers each member by name. A package is a repository of its own, with releases of its
own. So a rename is a change that every language must make, and they will not all make it in the same week.

So a rename is a MINOR release with a window:

- The new member is declared and required.
- The old member stays in `PROTOCOL` as **deprecated**. It is stored as the new member's `was`.
- Slipwai reads an answer given under either name, and the new name first (`src/slipwai/renamed.py`).
- A package that answers only the old name still loads, generates and passes `slipwai package check` for
  the whole window.

The MINOR release that closes the window deletes the old member. After that, the keel's *backend x is
missing y* is the only answer.

| New name | The name it replaces | Opened | Closes |
|---|---|---|---|
| `persistence_directory` | `event_store_directory` | 2.0 | 2.1 |

A rename is not the way to change a member's **shape**. If a shape cannot be kept, change it on this page,
in its own commit, with the reason (see *The members*, above). A name that means one thing to one language
and another thing to the next is worse than either shape.

## Tables that are not members, and why

| Table | Where | Why no member |
|---|---|---|
| `expected_backends` | `catalog.py` | Gone. `check_catalog` compares the catalog with the registry instead |
| `PACKAGE_ADDITIONS`, `FEATURE_REQUIREMENTS` | the `typescript` and `python` packages | They are inside the language that owns them, keyed by feature, and only that package reads them. They moved with the package |
| `web_package_json`, `web_lock_suffix`, `web_lock_features`; `workspace_manifest`, `workspace_scripts` | `project/frontend.py`; `project/shared_packages.py` | The browser app's manifest and the workspace root's manifest, written from the frontend's own `frontends` entry (its features' `dependencies`) and naming no frontend and no language. Data rather than members, because the pruner a project carries reads the same rows |
| `WRAPPERS`, `UPGRADE_PATHS`, `TOOLING` (`programme.py`), `SETUP`/`GITLAB_IMAGES` (`adopted_ci.py`), `LANGUAGES` (`structure.py`) | adoption | Keyed by the ecosystem of a repository that the factory did not make. Adoption needs no language (FR-002), so they stay in the keel |
| `label`, `framework`, `targets`, per-option `backends` | `catalog.json` | They belong to the catalog fragment |
| The adoption modules' spellings: `ecosystems.py`, `platform.py`, `programme.py`, `structure.py`, `delivery_facts.py`, `convergence.py`, `wrappers.py`, `project/adopted_ci.py` | adoption | The same reason as the row above, for every backend or family name that these modules spell (scenario 10). The experiment exempted them by name in a names test; this keel has no such test |
| `CANON` (`toolkit.py`) | the keel | The language that the toolkit's own prose and canonical snippets are written in. This is the keel's own material. The keel reads it from its own root where no service speaks, so adoption needs no language. `tests/test_assets.py` holds `CANON` to `typescript`. The npm-workspace checks that spelled `typescript` are now the `npm_workspace` member |
| The catalog's default backend (`catalog.default_backend`) | the keel | Gone. The default is the first backend of the merged catalog, so the keel names none |
| `DOCUMENTS`, `EXPORTERS` (`project/openapi.py`), `API_CONTRACTS` (`project/rules.py`), the five transports in `ENV_FEATURES` (`backends.py`) | the keel | Keyed by the feature that answered the `http` axis, and naming no backend. This is the shape that the experiment's gaps review left in the keel. **They would move** when the catalog's options move into each language's fragment (FR-019). A row keyed by an option that the keel no longer declares travels with the language that offers it, as `ENTRY_WIRING` and `FLAG_RESOURCES` did |
| `IDENTITY_DEFAULT` (`project/backing_service_prose.py`), `OPT_IN_TRANSPORT` and `DEFAULT_TRANSPORT` (`project/flag_route.py`), `FIRST_GROUPS`/`LAST_GROUPS` (`project/renovate.py`), `.editorconfig` and `.nvmrc` (`project/pins.py`) | the keel | What the keel says where a language says nothing. Also what depends on the target, the forge or the npm workspace, not on a language |

## How a slice moves a member

1. Add the answer to every backend, or to its family, in the language packages. Key it by the member
   constant.
2. Make the reader call `registry.answer(backend, MEMBER)`, and delete the table.
3. Set `required=True` in `PROTOCOL`, and change the *Status* cell above, in the same commit.
4. Replace the table's row in `docs/backend-obligations.md` §3 with the member's row. The location in that
   row is `registry.py`. The experiment's `tests/test_backend_obligations.py` then held that row to the
   registry (every backend answers it) instead of to a dict literal. This keel does not have that test.
5. Keep `make starters` byte-identical (FR-004).

Slices merge in the order they were split. If two slices append answers to the same `answers={...}`
literal, they conflict there. The host resolves the conflict by keeping both.

## Compatibility

This protocol and `docs/frontend-protocol.md` are one API, versioned by the keel's `schemaVersion`
(`MAJOR.MINOR`) and held by each package's `core` range, which is `>=<the schema it was built on>,<next major>`.
**From the 2.0.0 release on, it is kept like any other API:**

- **A MINOR adds only what an existing package can ignore**: an optional member, an optional fragment field, a
  new axis option. A new obligation applies only to a package that opts into the feature it comes with — a
  check for `write-model: state` runs for a backend that offers `state`, never for one that does not.
- **Anything else is a new MAJOR.** A member made required, a shape tightened, a field renamed without its old
  name read for a release: the schema goes to the next major, and every package's `core: "<N+1"` refuses to load
  on it with a line saying so — never a package that loads and then fails conformance, or a project.
- **A package owns the proof, in its own CI.** Its `verify.yml` runs this keel's conformance suite against the
  newest published keel its range takes and against the keel's `main`, on every push and every night — a
  contract test from the consumer's side (`slipwai package new` writes it so). A package that goes red against
  `main` with no change of its own has found a keel change that breaks the promise above, and that is a bug in
  the keel.

Before 2.0.0 the protocol is still being shaped and a MINOR may add an obligation; the packages are moved with it.
