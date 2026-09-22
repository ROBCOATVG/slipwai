# Services — one list, read everywhere

A generated project is a monorepo: `apps/` holds its deployables, `packages/` its shared code. Until this
was written it was a monorepo in layout only. Every one of the eight Make recipes spelled `apps/service`,
and so did the Compose file, the CI job, the import gate, the event-model documents, the run skill and the
pruner — nine places, each with its own copy of the one fact "this project has one service, here, in this
language". Adding a second service by hand meant editing all nine and finding the tenth later.

Now the list of applications is a single fact, and everything that names a service reads it. Each service on
the list carries its own language, framework and backing-service answers, so a project may hold a TypeScript
service on Fastify and Postgres beside a Python one on FastAPI and SQLite; each browser app names the service
its `/api` goes to, so a project may hold several; and everything project-wide is the union of what its
applications say.

## Where the fact lives

`project.json`, under `deployables`, one entry per application:

```json
{
  "schema": 2,
  "generator": { "name": "slipwai", "generatedWith": "1.5.0", "updatedWith": "1.5.0" },
  "deployables": {
    "service":  { "kind": "service", "path": "apps/service",  "language": "typescript", "port": 3000,
                  "selection": { "event-store": "postgres", "http": "fastify", "auth": "none", "users": "none" }, "eventSourced": true, "capabilities": ["..."] },
    "payments": { "kind": "service", "path": "apps/payments", "language": "python", "port": 3001,
                  "selection": { "event-store": "sqlite", "http": "fastapi", "auth": "none", "users": "none" },
                  "purpose": "Takes payment for an order and records the outcome.", "contexts": ["billing"],
                  "eventSourced": true, "capabilities": ["..."] },
    "web":      { "kind": "web",     "path": "apps/web",      "language": "typescript", "framework": "react-vite", "port": 5173,
                  "api": "service", "eventSourced": false, "capabilities": ["..."] },
    "admin":    { "kind": "web",     "path": "apps/admin",    "language": "typescript", "framework": "react-vite", "port": 5174,
                  "api": "payments", "eventSourced": false, "capabilities": ["..."] }
  }
}
```

- **`generator`** is provenance, and the one field here nothing generated reads. `generatedWith` is the
  factory version that created the repository and never changes again; `updatedWith` is the newest version
  to have written a file into it, which `add-service` and `add-frontend` move forward, since they regenerate
  every project-wide file from the factory they are run from. A repository made before the factory recorded
  this carries `"generatedWith": null` once one of those verbs has run — unknown, rather than credited to
  whichever version happened to add the service. Read against the factory's `CHANGELOG.md`, the pair says
  what a project has yet to hear about, and each entry there says what catching up would take.
- **`kind`** tells a service from a browser app. A service owes the eight Make targets, a `/health` probe
  and the hexagonal layout; a browser app owes none of those and is never iterated as one.
- **`path`** is where it lives: `apps/<name>`. The first service is `service` and the first browser app
  `web` unless `generate` was given `--service-name` or `--frontend-name` (or answered the two questions);
  whatever they are called, the first of each kind keeps the role — `make dev`, `PORT`, a package named
  after the project alone — because the role is a position on the list (`App.first`), not a name. The
  committed assets still say `apps/service` and `apps/web`, and `toolkit.spoken_for` spells them for the
  project on the way in: in a service's own files `apps/service` is that service, in the toolkit and the
  profile overlays it is the first one, and `apps/web` is the browser app that proxies to it.
- **`api`**, on a browser app, is the service its `/api` calls are proxied to — by the Vite dev server in
  the foreground and by `API_ORIGIN` inside Compose. The proxy sits in *that* service's transport's marked
  region, so a service that loses its transport takes its proxies with it. The project's `frontend` field
  is derived from the browser apps (`none` when there are none) and follows them when one is added.
- **`language`** and **`framework`** are the service's own. There is no project-wide backend: a project may
  have several, and every reader asks each service rather than the top of the file.
- **`selection`** is the service's own answer to every axis — its store, its transport, its identity
  provider. The transport is inherently per framework (`fastify` is not an answer a Python service can be
  given), and the store and provider may differ too. The project-wide consequences — which containers to
  start, which `.env` keys to write, which marked regions exist — are the **union** of the services'
  selections (`services.features_of`, `containers_of`, `axes_of`). A project can answer an axis again
  (`./init --auth none`), and that rewrites this record and the `capabilities` below it in the same run, so
  the file always says what the tree actually has.
- **`capabilities`** is what the application gives the project: what its profile, its language and each of
  its axis answers declare in `catalog.json`. The union across the deployables is what decides which skills
  the project is handed, and `make check-agents` reports one that no capability justifies any more
  ([skills](skills.md)).
- **`port`** is the application's own: services on 3000, 3001, …, browser apps on 5173, 5174, …. Compose
  publishes each one; `make dev` / `make dev-<name>` and `make dev-web` / `make dev-<name>` start each one;
  `PORT`, `PORT_<NAME>`, `WEB_PORT` and `WEB_PORT_<NAME>` move the published ports from `.env`.
- **`purpose`** and **`contexts`**, on a service, are what it owns in a sentence or two and the bounded
  contexts it holds (itself when absent). Neither changes a scaffolded byte; both exist for the delivery
  loop and the gates. Before they did, a project with two services put every slice in the first: `/drive`
  had nothing to place work against, and the second service — added by a person, for a reason — stayed an
  empty directory. Now `generate` and `add-service` ask for them (`--purpose`, `--context` once per
  context), the generated `docs/architecture.md` lists the services under their contexts, each `model.yaml`
  slice names its `service` (required by `check-model` once there are two), and `make model` renders one
  bounded-context canvas per context, projected from the slices rather than maintained by hand. A context
  may span several services; the tree stays `apps/<name>`, because a context is a hypothesis that gets
  renamed and split while a path is baked into module paths, Compose and CI.

  A service may also hold several contexts — `contexts: ["billing", "gifting"]`, each a `src/<context>/`
  inside it — which is the modular monolith a project starts as and the default the generated
  `docs/architecture.md` argues for until a *deployment* reason (release cadence, scaling, its own store,
  another team, another language) makes a context a service. Two gates read the list once it has more than
  one entry: `scripts/check-imports.py` refuses an import from one context into another that does not go
  through the other's `public` module (`api` in Java), and `check-model` requires every slice from
  `modelled` on to name its `context` beside its `service`, so the canvases exist per context before any
  context is a service. A manifest written before the field was a list — `"context": "billing"` — is read
  as a list of one; the factory writes `contexts`.
- **`schema`** says which shape those readers expect. `add-service` refuses a manifest with another number
  rather than guessing what an older or newer factory meant by these fields.

Why a manifest rather than discovering `apps/*` with a marker file in each: three of the readers — the
Makefile, Compose and the CI workflow — are *generated*, so they need the list at generation time, and a
directory scan there would be a second definition of the same thing. A directory also cannot carry what the
readers actually need — the port, the kind, the language, the answers — and a stray directory under `apps/`
would silently become a service. The manifest is one file, already written, already read by the pruner.

In the factory the same list is `services.App`, built by `services.default_apps(backend, frontend,
selection)` for a new project and by `services.apps_from_manifest(document)` from an existing one.
`project_files(project_name, profile, target, apps)` takes it and hands it to every part; no part
takes "the language" or "the selection" any more, because there is no longer one of either.

- **`generated`**, **`commands`** and **`provenance`**, and the top-level **`origin`**, exist for the
  repository the factory did not make — brownfield adoption, which is **experimental** as `AGENTS.md` defines
  the word, so their shape may still change in a MINOR. `"origin": "adopted"` says the method was installed
  around code that already existed; absent, the project is generated, as every manifest before the key was.
  An application recorded `"generated": false` already existed: its `language` is whatever it is written in,
  catalog or not, it has no `selection`, needs no `port`, and owes no skeleton, and its `commands` say how
  its own build answers the Make targets — a command per target, or `null` where the ecosystem has no answer,
  which is a written no rather than a missing row. Every reader carries such a record as written:
  `services_of` and `web_apps` mean the generated applications, `wrapped_of` the others, `check_known` does
  not ask the catalog about it, `replay` reproduces it byte for byte, `add-service` grows the project beside
  it, and the pruner — which reads each service's language to know its layout — passes over it. `provenance`,
  on any application, says where each recorded fact came from: `detected` from the tree, `confirmed` by the
  person when the detected value was accepted, `overridden` when they changed it or gave it as a flag. The
  gate composed from an existing application's `commands` is a later slice, so today nothing generated names
  such an application.

## Who reads it, and how

| Reader | What it does with the list |
|---|---|
| `Makefile` (`project/makefile.py`, `project/native_commands.py`) | Every recipe is generated per service — in that service's language — and merged: a line that names a service's path is kept once per service, a line that does not (`npm ci`) is a repository-level step and appears once. An npm service's install is not a line at all: `node_modules/.package-lock.json` is a target that runs `npm ci`, and every target that runs this project's own npm code takes it as a prerequisite (`project/shared_packages.py`), so the workspace is installed once per invocation however many recipes need it and not at all when it is already installed. `INTEGRATION_TEST` is one variable per service (`INTEGRATION_TEST`, `INTEGRATION_TEST_<NAME>`), each in its own store's marked region; with several services `test-integration` and `migrate` aggregate one target per service (`test-integration-<name>`, `migrate-<name>`), so CI can run one family's share. `dev` runs the first service, `dev-<name>` the others, each inside its own transport's region with its own port as the default. `make demo` prints every service's address. |
| `docker-compose.yml` (`project/compose.py`) | One block per service that has a transport, inside *that service's* transport's marked region, in that service's image, publishing `${<VAR>:-<port>}:<port>`; one block per browser app on its own port, its `API_ORIGIN` naming the service it proxies to inside that service's region. Containers are the union of the services' selections. |
| `.github/workflows/verify.yml` (`project/ci_workflows.py`) | The gate is `make verify`, whose recipes already loop, so CI loops **inside Make** rather than fanning out a matrix: a matrix would give CI a shape the laptop does not have, and one runner has one Docker daemon. What the workflow knows per service is one `actions/setup-*` per language family present (keyed on that family's dependency files) and, for the suites that need real infrastructure, **one integration job per family** — a job has one container image and an image carries one toolchain — named `integration` while there is one such family and `integration-<family>` after, each running its own services' `migrate-<name> test-integration-<name>`. |
| `scripts/check-imports.py` | The hexagonal rules apply inside every directory under `apps/` and `packages/` with no list at all, and they are already language-neutral; only the frontend rule needs to know which directories are services, and reads `project.json` for it. |
| `scripts/backing-services.py` (`assets/backing-services/prune.py`) | `OWNED_FILES` and `MARKED_FILES_BY_LANGUAGE` are relative to a service and keyed by language family; `project_services` reads each service's path **and language** from the manifest, and every prune resolves each service's patterns by its own layout — so a Go service's adapters and a Python service's are pruned in one pass, at generation and at any later `./init`. |
| `scripts/verify` (`project/languages/*.py`) | One script per language family, looping over that family's services in its own idiom. With one family it is `scripts/verify`, as it always was; with several, each family's is `scripts/verify-<family>` and `scripts/verify` dispatches to all of them (`tooling.verify_dispatcher`). Python's recipes run modes of *its own* script, so they name `scripts/verify-python` in a mixed project — `backends.VERIFY` is the token, stamped by `tooling.verify_path`. |
| `.gitignore`, `.claude/settings.json` | The union of every backend's artifacts and permissions, once each; a `dist/` and a `dev-<name>` permission per browser app. |
| `infra/*/project.auto.tfvars.json`, the Makefile's production section, `.github/workflows/deploy.yml` (`project/infra.py`, `project/production.py`, `project/deploy_workflow.py`) — `aws` target only | One entry per service in the tfvars both stacks read with `for_each`: its port, what the target provisions for its answers (`store = "rds"`, `auth = "cognito"`), how its migrations run once it is an image. One `build-<name>` recipe and one `IMAGE_<NAME>` per service, in that service's backend's builder; one migrate image where the backend needs one (Go). The deploy workflow installs one toolchain per family and one image builder per family that needs it. `add-service` regenerates all of it — and its report says the bootstrap stack needs applying once more, for the new service's image repository. `frontend.tf` is one file with two contents, so `add-frontend` rewrites it rather than leaving two behind. |
| `apps/<web>/vite.config.ts` (`project/frontend.py`) | The committed skeleton is written for one browser app on 5173 talking to a service on 3000; each browser app is given its own dev-server port and the address of the service it proxies to, and the npm workspace names every Node service and browser app. |
| `skills/run-the-app/SKILL.md`, `README.md`, `docs/architecture.md`, `AGENTS.md` | List the services with their languages, ports and targets; say what each one owes and how to add one; describe each store and provider present once. |
| `docs/getting-started.md`, `docs/event-modeling-to-code.md`, `docs/first-slice.md` | Speak one language where they have to: the **first service's**. A slice belonging to another service lives under that service's directory in that language's shape. |
| The skills' example snippets (`toolkit.speakers_of`, `examples.resolve_examples_for`) | Speak **every language a service is written in**. With one language a marker becomes the bare snippet, as it always did; with several it becomes one block per language in service order, each headed by the language and the services it is for (`**Go — \`apps/ledger\`**`), and two frameworks of one language sharing the family's snippet share one block. Only the four skills that carry markers change — `domain-driven-design`, `hexagonal-architecture`, `event-sourcing`, `testing` — so they are among the files `add-service` regenerates when the new service brings a new language. The TypeScript-as-pseudocode note on the skills not yet converted to markers names every language the project has, and is not stamped at all once one of the services is TypeScript. |

## What a second service is, per language

Every service gets the walking skeleton a service of its language starts with — the health capability, the
transport, the event-store adapters and their contract suite, the tests — named for itself
(`tooling.service_qualifier`: the first service is named after the project alone, as it always was; a later
one is `<project>-<name>`, so `acme-payments` becomes the Python package `acme_payments`, the Java package
`com.example.acmepayments`, the npm package `acme-payments` and the Go module `example.com/acme/payments`).

- **TypeScript** — a second npm workspace. The root `package.json` names the Node services (not `apps/*`:
  a Python directory under `apps/` is not a package, and npm would go looking for a manifest it does not
  have), and the root lockfile gets each service's record and link, plus the hoisted records its own
  variant lock has that the first's did not — every variant pins the same versions, so the union is the tree
  npm would produce.
- **Go** — one module per service and one `go.work` naming them all, which is what Go itself asks of a
  repository with more than one module. Each service keeps its own `go.mod` and `go.sum` — the committed
  variants — so a second service is a second `use` line and not a second dependency set to lock, and the
  committed locks are untouched. A shared module under `packages/` is one more `use` line.
- **Java** — one Maven project per service, no aggregator pom. Each pom keeps its own framework parent,
  `add-service` copies a skeleton rather than editing a module list, and `scripts/verify` and the Makefile
  are the loop. A shared Maven module under `packages/` that the services have to build first is what would
  make a reactor worth having; that is the day to add an aggregator, and the reason there is none today.
- **Python** — one package per service, each with its own `pyproject.toml` and committed `uv.lock`, and
  its own environment built beside it by `uv sync --locked`: a service's dependencies are its own, and
  a second service is a second lock rather than a shared set to reconcile. The family's verify script
  syncs each and then runs every mode for each in turn, through `uv run`.

## Adding a service: `add-service`

```sh
cd my-product                                           # the generated project
path/to/slipwai/slipwai add-service payments                    # first service's language and answers
path/to/slipwai/slipwai add-service ledger --language python    # another language, its own answers
path/to/slipwai/slipwai add-service audit --language go --event-store sqlite --auth none
make verify
```

`add-service` is a factory command run *inside* an existing generated project. It reads `project.json` for
the profile, frontend and target, and for the first service's language and answers, then adds one service:

- **Language and framework** — `--language`/`--framework`, or `--backend`, exactly as `generate` takes
  them; without any, the first service's.
- **Answers** — one `--<axis>` flag per axis. An axis without a flag inherits the first service's answer
  where the new backend offers it (the same store, the same identity provider), and takes the new backend's
  own default where it cannot (a Python service beside a Fastify one gets FastAPI). Refused answers are
  refused exactly as `generate` refuses them.
- **Purpose and contexts** — `--purpose "<what it owns>"` and `--context <name>` once per context,
  recorded on the entry and read by nothing that scaffolds; see above for what reads them. The agent command
  (`commands/add-service.md`) treats the purpose as a product decision to ask for, like the language and
  the store — and asks whether a service is the right shape at all, or whether the request is a context
  that belongs inside one that exists.
- **The port** — the next in the sequence; the one decision the command takes for itself.

What it writes, and how it knows:

1. It puts the new service on the list and asks `scaffold.project_files` for the whole project **twice** —
   once with the list as it was, once with the new service on it. Everything under `apps/<name>/` is written,
   and so is every other file whose content differs between the two. That difference *is* the set of files
   the manifest drives — the Makefile, Compose, CI, the npm workspace and lock or `go.work`, the verify
   scripts, the agent settings, `.gitignore`, the README and architecture sections that list the services —
   derived from the generator rather than kept as a list the generator could drift from. A file that does
   not change with the list is never touched.
2. `project.json` is edited in place: the new entry is appended to `deployables` and nothing else in the
   file is rewritten, so a field a later factory added survives.
3. The same pruner generation runs then cuts the new service down to **what the project actually has**, read
   off its disk rather than off the recorded selections: an inherited answer that an earlier `./init`
   pruned stays pruned (a project that dropped Keycloak gets a second service with no auth adapter), a
   feature `./init` settled stays settled in the regenerated files — but an answer asked for by flag is kept,
   and so is the new backend's own default for an axis the first service's answer could not carry.

It does not commit. It refuses, plainly, when: the current directory has no `project.json`; the manifest's
`schema`, a service's language or backend, or an axis in a selection is one this factory does not know; the
name is taken (by a service or by `web`), is not a valid service name (lowercase letters, digits and hyphens
— it has to be a directory, an npm package, a Go module segment and a Compose service at once), or
`apps/<name>` already exists unregistered; the requested backend is not offered under the project's target;
or the working tree has uncommitted changes — the tree has to be clean so that `git checkout . && git clean
-fd` undoes exactly what the command wrote.

The proof is `tests/test_add_service.py`: a TypeScript project with the browser app is given a Python
service and, separately, a second TypeScript service; a Spring project is given a second Spring service; each
project's own `make verify` is green with two services. A third language is added beside two; every refusal
is a test of its own; a project narrowed by `./init` gets a narrowed second service, unless it asks.

### From an agent session: `/add-service` and `/add-frontend`

Every generated project carries `commands/add-service.md` and `commands/add-frontend.md`
(`project/add_commands.py`), projected into the selected harness by `./init` like the other commands. An agent
asked for "a payments service" and given no command copies `apps/service` by hand and edits the nine files
that name it, which is the state `add-service` exists to end; the command is where it learns that the
factory does this, what has to be decided with the user first (the name, the language, the answers — the port
is the command's own), where the factory is (a released `slipwai` on the `PATH` or a checkout's
`generate`, and to ask rather than guess), and what to check afterwards (`git diff` over the regenerated
files, `make verify`, and the shared local database). Both files list the project's current applications,
so they are among the files `add-service` regenerates: the list an agent reads is the list that is there.

## Saying what a service is for: `describe-service`

```sh
cd my-product
path/to/slipwai/slipwai describe-service payments --purpose "Takes payment for an order and records the outcome."
path/to/slipwai/slipwai describe-service payments --context billing --context refunds   # replaces the list
```

`purpose` and `contexts` are the two fields the delivery loop places a slice against, and `generate` and
`add-service` take them at scaffold time — but a purpose is often left unsaid at the start, and the contexts
are *found* later: in the event model's lanes, or in the specification's vocabulary, which is where `/drive`
says to record them. This verb is where the answer goes after the fact. It edits the service's `project.json`
entry in place — a field given replaces what was recorded, a field not given is left alone — and regenerates
every file whose content the two fields reach, derived the same way `add-service` derives its set: the
architecture page's *Bounded contexts*, the agent guidance, the `/add-service` command's list of what is
there. Nothing under `apps/` is touched, because nothing scaffolded reads either field.

It refuses when: the name is not on the list, or names a browser app; neither flag is given, or the flags
say exactly what is already recorded; or the working tree has uncommitted changes, for the same reason
`add-service` does. `/drive` and `/cruise` point at it wherever they say a purpose or a context is recorded,
so an agent that finds "no purpose recorded yet" on the architecture page knows the command rather than
editing the manifest by hand.

## Adding a browser app: `add-frontend`

```sh
cd my-product
path/to/slipwai/slipwai add-frontend web                     # a project generated with --frontend none gets its first
path/to/slipwai/slipwai add-frontend admin --api payments     # a second, proxying /api to another service
make verify
```

The same operation as `add-service` for the other kind of application, through the same code (`add_service.grow`):
the skeleton under `apps/<name>` on the next dev-server port, `/api` proxied to the service it names (the
first service by default), the workspace, lock, Makefile, Compose, `.gitignore`, agent settings and prose
regenerated from the list, `project.json` appended in place with its `frontend` field following the browser
apps. It refuses what `add-service` refuses, and a service the project does not have (`--api billing`).

## Three limits worth knowing

- **Pruning is per feature, repository-wide.** Marked regions are named after a feature, not a service, so
  `./init --auth none` drops the identity provider from *every* service that has it, and two services on the
  same store cannot be pruned apart. Two services on different stores can, because their features differ.
  The browser apps follow the same rule: every one of them carries the customer login while any service
  answers `--users`, and `./init --users none` takes it out of all of them.
- **The scaffolded services share the local backing services.** Every service's `DATABASE_URL` is the one
  in `.env.example`, and every service that carries the same event-log migrations applies them to one
  database, which their ledgers make idempotent. That is right for a skeleton and wrong for a product: give
  each service its own database (or schema) before either of them owns data.
- **No monorepo build tool — not yet.** Nx, moon, Turborepo and Bazel each replace the Makefile's loop with
  a task graph, and none of the projects this factory generates has the problem a task graph solves. Two
  things would: a shared package under `packages/` that several services have to build *before* they build
  (ordering, which the Makefile's flat loop cannot express and a Maven reactor or `go.work` only partly
  can), or a gate whose time grows with the service count until "run only what this change affects" is
  worth its configuration. Until one of those arrives, the Makefile is the orchestrator and a new service
  costs one more line in each loop, generated rather than written.

## Keeping a new generated file service-aware

When you add a file to the generated project — or a line to an existing one — that names a service, a
language or an answer:

1. **Take the list.** The part's function takes `apps: list[App]` beside its other arguments and iterates
   `services_of(apps)`; `scaffold.project_files` passes `apps` to every part. There is no "the language" or
   "the selection" to take — read `service.backend`, `service.language` and `service.selection`, or a union
   from `services.py` (`features_of`, `containers_of`, `axes_of`, `has_feature`, `backends_of`, `families_of`,
   `transports_of`, `needs_environment`).
2. **Spell the path with `APP` in a per-backend table**, never as `apps/service`, and a Python script path
   with `VERIFY`. `backends.APP` and `backends.VERIFY` are the tokens; `tooling.for_app(text, path, verify)`
   stamps them, `services.app_tooling(service, apps, feature)` returns `BACKEND_TOOLING` for one service with
   both stamped. `native_commands.service_commands(backend, path, verify)` is the eight-target table done this
   way; `native_commands.merged` folds several services' recipes into one.
3. **Say which service where one has to be named.** The first service is `services.FIRST_SERVICE`; its
   `dev` target and `PORT` variable are the ones everything already documents, and `App.dev_target`,
   `App.suffix` and `App.port_variable` know the rule. Prose that must speak one language speaks
   `services_of(apps)[0]`'s and says so; a code example does not have to, and shows every language
   (`toolkit.speakers_of`).
4. **Put a per-service region under that service's feature.** A Compose block or a `dev` target belongs in
   *its* service's transport marker, not the first service's; a store's variables are declared once however
   many services share the store.
5. **Check the file against `add-service`'s rule.** It regenerates every file whose content changes with the
   list and writes nothing else, so a file that depends on the list is covered automatically — and a file
   that a person will edit by hand after generation should not depend on it, or the next `add-service` will
   overwrite their edit.
6. **Prove it with the snapshot**, as every generator change is proved: hash every file of every
   profile/backend/frontend combination before and after, and account for every file that differs.

`tests/test_services.py` holds the list to the code: the manifest's shape, that every reader iterates when
a second service is on it, that two languages share one repository, and that the pruner prunes each
service by its own language.
