# Project shape: profile, target, language, frontend, axes

Every generated project answers five kinds of question. The profile decides which delivery foundation
is installed, the target decides where it goes to production and so what the later menus may offer, the
language and frontend decide the toolchains, and each **axis** fills one infrastructure role.

## Profiles

| Profile | Includes | When it fits |
|---|---|---|
| `standard` | Walking skeleton, executable test, local/CI `verify` gate, minimum-CD constitution | A tool, a spike, an internal script — anything whose expected lifespan is short |
| `event-modelling` | Everything above, plus **Event Modeling and event sourcing as one bundle** | A product a team will grow for years |

The default is `event-modelling/typescript` with the `react-vite` frontend.

### Which profile

This is the one question a generated project cannot answer again. Every axis can be answered down later
(`./init --event-store memory`), and the profile cannot be — so it is worth spending a minute on, and the
interactive form prints both answers and the argument below before asking.

**The decision variable is the product's expected lifespan, not a requirement you can name today.** The
usual instinct — don't buy architecture until something demands it — assumes the cheaper start is also the
one you can walk back. Here it is the opposite way round, and the asymmetry is the whole argument:

- **Going event-sourced → state-stored later is nearly free.** Fold the log into tables, keep the tables,
  archive the log. A project can stop being event-sourced on an afternoon's work.
- **Going state-stored → event-sourced later is mostly fiction.** The history you never captured is gone:
  you cannot retroactively answer questions about facts nobody recorded. In practice you bootstrap from
  synthetic "genesis" events reverse-engineered out of current state, while untangling an aggregate that has
  spent years accreting features. "Start standard and introduce events where a subdomain earns it" is an
  option that reads as available and usually is not.

So `event-modelling` is the reversible choice and `standard` is the irreversible one. Its front-loaded costs
are the price of keeping that option open, not speculative gold-plating.

**What you are buying is a flat cost curve, not a cheaper first slice.** The state-stored default has a
compounding signature that shows up early: one aggregate that ends up carrying every unrelated decision,
a repository port that grows a method per feature, and a new read model rummaging through a write model that
was never shaped for it. Each of those steps is locally reasonable, which is exactly how the curve
compounds. Event Modeling's slices are stamped instead — a new slice touches almost nothing that exists, so
slice 30 costs roughly what slice 3 cost, and that flatness comes from the method's discipline (slice
independence, complete information flow per slice) rather than from anyone's restraint. Expect the early
slices to cost *more* than they would under the standard shape; that is the trade being made.

**Why the flat curve matters more when agents are writing the code.** Every argument above holds with no
agent in the repository at all. What changes when there is one is *who pays the reading cost, and how often*.

- **A tenured engineer amortises system knowledge; a session buys it again from scratch.** The compounding
  curve's real cost is not typing, it is how much of what already exists you must understand to change it
  safely. A person accumulates that over months and pays it down once. An agent session starts near-empty,
  pays it in full, and discards it at the context boundary. Flat marginal cost per slice is the same
  property as bounded reading per slice.
- **Slice independence is context independence.** "A new slice touches almost nothing that exists" means the
  material needed to write it is small and — because the model names it — nameable: these events, this
  stream, these files. That is a lookup with an exact answer rather than a search across a codebase, and it
  is the difference between a session that fits and one that compacts halfway through the work.
- **The model is memory that outlives the session.** `/drive` reads artifacts from disk rather than
  conversation precisely because conversation does not survive. The event model is what makes that workable:
  a cumulative, durable statement of what every event already means and who reads it. Under the
  state-stored shape the equivalent knowledge is implicit in the shape of an aggregate, recoverable only by
  reading the whole thing — which is exactly what a fresh session cannot afford.
- **The compounding failure modes are the ones a generator produces most readily.** One more method on the
  repository port, one more field on the aggregate, one more read model rummaging through a write model
  never shaped for it: each is locally reasonable, each is the plausible continuation of the surrounding
  code, and none is visible as a mistake from inside the diff that makes it. An author with no stake in next
  year's maintenance is not restrained by taste — which is why the flatness has to come from mechanism
  (`check-model` refusing a slice whose events do not appear in the source, `check-imports` refusing a
  context that reaches into another's internals) rather than from anyone's judgement.
- **When writing code is cheap, the bottleneck moves to knowing whether it is right.** The model, plus the
  slice's Given/When/Then, plus `make check-model`, turn "does this implement what we agreed?" into a
  question with a mechanical answer. That is worth more per unit of generated code than it ever was per unit
  of typed code.
- **Independent slices parallelise.** Slices sharing only an event schema can be built in any order, by
  different sessions, with the schema as the contract instead of a merge conversation about who owns which
  file.

None of this makes an agent good at the modelling conversation itself. That stage is still people deciding
what the business means, and `/drive` stops rather than inventing an event to get past it. The claim is
narrower, and it is the one that pays: the artifact that conversation produces is what makes everything
downstream of it cheap for a machine to work inside.

**The caveat, which is real.** The flat curve is conditional on paying the platform costs on schedule: an
event-upcasting mechanism and a PII-erasure strategy. Those are fixed costs, not slice-shaped ones, and they
have to land before growth arrives. Persisted projections were a third of them and are not any more — the
skeleton ships a checkpoint port with three adapters, the catch-up runner that advances it inside the view's
own transaction, and a rebuild ([The read side](what-you-get.md#the-read-side)) — so a slice answering
`materialisation: async` is writing a fold rather than building a read side. A team that adopts Event
Modeling without budgeting for what is left gets the front-loaded cliffs without the flatness — the promise
is flat *marginal* cost, not zero fixed cost. Choose `standard` for short-lived work and mean it; choose
`event-modelling` for a product you expect to still be adding to in three years, and budget for the platform.

## Production target

The **target** is where a project goes to production, and it is asked right after the foundation because
it decides the menus that follow. Every axis option declares the targets it is offered under (`targets`)
beside the backends it is implemented for (`backends`), and so does every backend; `axis_options` filters
by both, so the same rule that keeps `fastify` off a Go project's menu will keep a file-bound store off a
cloud one. An answer the target does not offer is refused at the command line the way an answer the backend
cannot be given is, naming `--target` as one of the two flags that would fix it, and a generated project's
own `./init` reads `project.json`'s `target` and applies the same filter when an axis is answered again.

| Target | Meaning |
|---|---|
| `none` (default) | Local only. Nothing is deployed anywhere; `make verify` is the end of the road |
| `aws` | One ECS service per application deployed blue/green behind its own load balancer, RDS Postgres, Cognito and S3 + CloudFront, provisioned by OpenTofu from `infra/` and deployed to `staging` then `production` by `.github/workflows/deploy.yml` once `verify` passes on `main`. [The AWS target](aws-target.md) has the whole design |
| `azure` | One Container App per application released by revision behind the environment's own ingress and managed certificate, PostgreSQL Flexible Server, Entra ID and Static Web Apps, provisioned and deployed the same way. The same promise as `aws` on a different cloud, and cheaper per service because there is no load balancer to pay for; [The Azure target](azure-target.md) has the design, the cost comparison and the four places the two differ |
| `existing` — **experimental** | The project deploys to infrastructure it does not own. Nothing is provisioned and the menus are `none`'s; what turns on is `docs/deployment.md` — where it runs, who describes that (`here`, `elsewhere`, `unmanaged` or `none`, as `adopt` recorded it), how a release reaches it — and the release-constraint rung of `/drive`. The target `adopt` gives a repository it finds infrastructure for ([Adopt an existing repository](adopting.md)) |

A target may also reserve words a project's name cannot contain, and `generate` refuses the name the moment
the target is known. A cloud names what it creates after the project, and some of its services refuse their
own brand inside those names: a Cognito hosted-login domain is `<project>-<environment>-staff` and rejects
any prefix containing `aws`, `amazon` or `cognito`, so a project named `aws-gh` would be generated happily
and then die partway through its first apply, with the cluster, the balancer and the distributions already
up. The name is the only thing that fixes that, so it is refused where it is still a choice.

Clouds do not all refuse a word the same way, so a target declares *how* alongside *which*: `anywhere` for a
substring, `word` for a whole word between the separators a project name may carry (`.`, `_`, `-`, or an end
of the name), and `prefix` for the start of the name only. `aws`'s three words are all `anywhere`. The
refusal names the word, the way it was refused and both ways out, and points at the target's own page for
the full list.

A target arrives with its infrastructure and never before it: a catalog row with nothing behind it would
generate projects claiming a destination they cannot reach, which is the half-ported shape refused
everywhere else in this factory. `aws` arrived with `assets/targets/aws/`, the image builders, the deploy
pipeline and the per-target provisioning of the options it carries; `azure` arrived the same way, as a row
in these tables rather than a second set of branches, and
[The Azure target](azure-target.md#what-a-third-cloud-would-need) lists what a third would be.

What the target changes on the menus that follow it:

| Axis | under `none` | under `aws` | under `azure` |
|---|---|---|---|
| `--event-store` | `memory`, `sqlite`, `postgres` | `memory`, `postgres` → RDS. SQLite is not offered: the file dies with the task | `memory`, `postgres` → Flexible Server. SQLite is not offered, for the same reason |
| `--http` | `none`, the backend's own | the backend's own, **required**: the target deploys an HTTP service and `/health` is what proves a deploy, so `--http none` is refused naming both ways out | the same, and required for the same reason |
| `--auth` | `none`, `keycloak` | `none`, `cognito` — a user pool with the same three groups, Keycloak kept as the local stand-in with the same `OIDC_*` keys | `none`, `entra` — an app registration with the same three groups as app roles, Keycloak kept as the local stand-in; `OIDC_GROUPS_CLAIM` is `roles` |
| `--users` | `none`, `keycloak` | `none`, `cognito` — a second user pool with self-registration and a public PKCE client, Keycloak's customers realm kept locally | `none` only. An Entra External ID tenant has to be created by a person rather than by a workload identity, and a stack that configured one from the pipeline would be cross-tenant and unproven — so the row is absent rather than half-ported ([The Azure target](azure-target.md#3-there-is-no-customer-identity-answer)) |

Two mechanisms carry that: every option declares `targets`, and a target may `require` an axis
(`targets.aws.requires = ["http"]`), which takes the no-infrastructure answer off the interactive menu and
refuses it at the command line and in the generated project's own pruner. Where the target provisions an
answer differently, the option says so under the target's key — `postgres` carries
`"aws": {"provisions": "rds"}` — and the infrastructure generator reads that declaration rather than a
product name. `cognito` is the one option that owns another option's feature: what a Cognito project carries
*locally* is Keycloak's files, so the two share the `keycloak` feature and `./init --auth none` drops both.

## Language and frontend

A **backend** is a language, plus the framework that owns startup where the ecosystem has one. The two are
one choice rather than two independent ones because they do not combine independently: something that owns
the composition root owns how every adapter behind every other axis is written, so it multiplies with the
language instead of crossing it. The command line asks them as two questions and resolves them to one
backend; where a language has one backend — nothing owns startup but the standard library or a library
you call — the framework question is not asked at all.

That is what the bare keys mean. `typescript`, `python` and `go` are named for the language alone precisely
because nothing owns their startup; a backend built on something that does is named for it too
(`java-spring`), from the day it is added rather than once it has a sibling.

Java is the family that has two, so it is the one where the framework question is asked: `--language java`
takes `--framework quarkus` or `--framework spring-boot`, and `--backend java-quarkus` / `--backend
java-spring` names the answer directly. Both members answer every axis, and they share the language's own
material — the Maven wrapper, the three analyser configurations, the event port, all three store adapters —
so what actually differs between them is what touches the framework.

Backend language and browser frontend are independent choices. The initial frontend capabilities are
`react-vite` (the default) and `none`. A Go, Python or Java service can therefore sit beside an ordinary
TypeScript/React browser application without applying backend persistence rules to browser state.

Generated verification uses the native ecosystem conventions: TypeScript with Biome, `tsc`, and Vitest,
Python with pytest and Ruff, Go with `gofmt`, `go vet`, staticcheck and coverage-enabled `go test`, and Java with
Checkstyle, PMD and SpotBugs for lint, `javac` under Error Prone and NullAway for the type check, and
JUnit 5 — through Quarkus's own harness on `java-quarkus`, and through Spring Boot's with MockMvc on
`java-spring`. Dependency locks or exact development versions are committed with
each new project — except where a manifest already pins every version exactly, which a Maven pom does, so
the Java backend has no separate lock file to keep in step.

## The axes

Beyond the profile, backend language and frontend, a project answers one question per **axis**. An axis
names the *role* being filled, not a product, and each is asked and answered on its own — where events are
stored has nothing to do with who authenticates staff, so the two are never one menu.

| Axis | Question | Answers |
|---|---|---|
| `--event-store` | Where do events live? | `memory`, `sqlite`, `postgres` (default) |
| `--http` | What accepts inbound HTTP? | `none`, then one per backend: `fastify` (TypeScript), `fastapi` (Python), `net-http` (Go), `quarkus-rest` (Java/Quarkus), `spring-web` (Java/Spring Boot) — the backend's own is the default |
| `--auth` | Who authenticates staff? | `none` (default), `keycloak` |
| `--users` | Who authenticates the product's users? | `none` (default), `keycloak` |

Each axis also carries a one-line `description` in `catalog.json` — the role, and what every answer to it
has in common — which the interactive form prints under the question. For `auth` that sentence is the
reason the axis is not called `oidc`: every provider on it is an OIDC issuer and OIDC is what the adapters
speak, so the protocol is what its answers share rather than what distinguishes them. The axis is named
for the role, the way `event-store` and `http` are; the `OIDC_*` environment variables and the
`oidc_keycloak` adapter files keep the protocol's name, because that is what they are about.

`users` is the same kind of answer to a different question. Staff are accounts an administrator creates,
authorised by group; the product's users are accounts anyone can create, with sign-up, password reset and a
login the browser app owns, authorised per account inside a use case. The two never share a directory even
when they share a vendor — which is why Keycloak answers both axes with two *realms*, kept apart in the one
local container the way a real deployment keeps a workforce tenant apart from a customer one. `USERS_OIDC_*`
and `VITE_USERS_*` are that realm's keys, and `users-keycloak` its feature.

**Why those defaults.** A default is a recommendation, so the recommended answers are the ones a product
team would reach anyway: a real event store whose concurrency control is a database constraint, and the
inbound transport the chosen backend actually has. The HTTP default is per backend because the options are —
`fastify` is not an answer a Go project can be given, so one flat default would refuse to generate on four
backends out of five. Identity is the exception: `keycloak` ships its realm, container and group mapping
with the protocol flow deliberately unimplemented, and a default that hands every project a placeholder to
finish is not a recommendation. `--event-store memory --http none` is still one flag each away, and the
generated `make verify` needs no Docker whichever store is chosen.

The pruner is what makes this direction the safe one. A generated project can answer an axis again and
subtract — `./init --event-store memory` — but it can never add, so a project born on Postgres keeps every
choice while a project born on memory has already lost one. Defaulting to the answer you can walk back costs
a `docker compose` the day you want the integration suite; defaulting to the other costs a regeneration.

### Which backend can be given what

An option declares the backends it is implemented for, so coverage is a fact about the catalog rather than
a promise. Every axis is currently implemented for every backend, and this table is what keeps that
sentence honest: it is checked against `catalog.json` by
`tests/test_catalog.py::test_the_documented_axis_coverage_is_the_catalog_s`, so a backend added without
adapters appears here as a row of dashes instead of silently falsifying the claim.

| Backend | `--event-store` | `--http` | `--auth` | `--users` |
|---|---|---|---|---|
| `typescript` | `memory`, `sqlite`, `postgres` | `none`, `fastify` | `none`, `keycloak` | `none`, `keycloak` |
| `python` | `memory`, `sqlite`, `postgres` | `none`, `fastapi` | `none`, `keycloak` | `none`, `keycloak` |
| `go` | `memory`, `sqlite`, `postgres` | `none`, `net-http` | `none`, `keycloak` | `none`, `keycloak` |
| `java-quarkus` | `memory`, `sqlite`, `postgres` | `none`, `quarkus-rest` | `none`, `keycloak` | `none`, `keycloak` |
| `java-spring` | `memory`, `sqlite`, `postgres` | `none`, `spring-web` | `none`, `keycloak` | `none`, `keycloak` |

Under the `aws` target the same backends are offered these menus — checked by `tests/test_targets.py`:

| Backend | `--event-store` | `--http` | `--auth` | `--users` |
|---|---|---|---|---|
| every backend | `memory`, `postgres` | `none`, its own transport | `none`, `cognito` | `none`, `cognito` |

A row of dashes would be a real state rather than a defect: a language can be added before its adapters
are, and an axis with nothing behind it is not asked at all. Such a backend would still get the whole
toolkit, its walking skeleton and — in the event profile — an event-store *port* with no adapter behind it,
while getting nothing an adapter provides: no `make dev`, no `docker-compose.yml`, no `make demo`, no
migrations and no integration suite. It could be verified; it could not be demonstrated. That is the
trade-off `.claude/skills/add-language/` asks about before a language is added, rather than after.

Each answer arrives in that backend's own idiom:

| Answer | What arrives | Dependency |
|---|---|---|
| `memory` | The in-memory adapter behind the event-store port, and the contract suite it answers to | none |
| `sqlite` | A real append-only log in one file — schema in the adapter, no container, no migration step | none in TypeScript (`node:sqlite`) or Python (`sqlite3`); `modernc.org/sqlite` in Go, which needs no cgo; `org.xerial:sqlite-jdbc` in Java, which is the one place either Java backend does not use a framework integration — Quarkus publishes no first-party SQLite extension and the Quarkiverse one tracks Quarkus 3.0, and Spring Boot needs none because the adapter opens its own `SQLiteDataSource` |
| `postgres` | An append-only event-store table, its migrations, the Postgres adapter, and the integration suite that races two appends at one version | `pg`, `psycopg`, `pgx/v5`; in Java the framework's own — `quarkus-jdbc-postgresql` with `quarkus-agroal` for the pool and `quarkus-flyway` for the migrations, or `spring-boot-starter-jdbc` with HikariCP and `spring-boot-starter-flyway` |
| `fastify` / `fastapi` / `net-http` / `quarkus-rest` / `spring-web` | The HTTP driving adapter, its 404-hardening default correction, edge tests that dispatch through the real router with no socket, and the one entry point that binds a port — `make dev`, and the `service` in Compose | `fastify`; `fastapi`+`uvicorn`; none (Go's standard library); `quarkus-rest`+`quarkus-rest-jackson` with `quarkus-smallrye-health` serving the probe; `spring-boot-starter-web` on virtual threads with `spring-boot-starter-actuator` serving it |
| `keycloak` | A realm imported at start-up, the group-to-role mapping, and the OIDC adapter — with the protocol flow deliberately left unimplemented, except on either Java backend, where the framework's client performs it and only the mapping is this project's | none in TypeScript, Python and Go; `quarkus-oidc`, or `spring-boot-starter-oauth2-resource-server` |
| `keycloak` on `--users` | A second realm, `customers`, in the same container — self-registration and password reset on, a public PKCE client, a bearer-only `api` client stamped into every token's audience; in every browser app the login, session and silent renewal; in the service the customer adapter, which refuses any issuer but this realm's and any unverified email — with token validation left unimplemented where nothing owns startup, and on Java a named `quarkus-oidc` tenant or a second Spring Security filter chain for `/api/customers/**` | `react-oidc-context` and `oidc-client-ts` in the browser app; none in TypeScript, Python and Go services; the same Java dependencies as `--auth`, in a region both share |

The event-log schema is one file, shared by the Python, Go and both Java backends — Java reads it under
Flyway's `V<n>__` naming, the same bytes at a different filename — and `make verify` in this factory
asserts the TypeScript migrations have not drifted from it: the unique constraint, the append-only
triggers and the REVOKE are checked in both forms.

The Java family shares more than the schema. Everything behind the event-store port names no framework
type, so `java-quarkus` and `java-spring` read one copy of the port, all three store adapters, the
`DATABASE_URL` parser, the migration entry point and the contract suite from
`assets/backing-services/java/`. What each one has of its own is what actually touches its framework: how
the datasource learns its address, what serves the readiness probe, what answers a 404, and how a validated
token becomes authorities. That split is the check on whether "use the framework's integration, keep the
hexagon" was applied honestly — if it were not, the shared half would be much smaller.

The in-memory adapter is not one of the alternatives: **every** answer to `--event-store` ships it, because
it is what the port's contract runs against in `make verify`. That is why the gate needs no Docker whichever
store you chose, and why an event-sourced project always has a working event store rather than a port with
nothing behind it.

## Two load-bearing properties

- **`make verify` never needs Docker.** The event-store contract runs against every adapter that needs no
  infrastructure — the in-memory one always, SQLite too when it is chosen. The database-backed half is
  `make test-integration`, which needs `make services-up migrate` first and is where the concurrency
  guarantee neither of the others can race for is actually proved.
- **An answer is refused rather than half-ported.** Each option declares the backends it is implemented
  for, and the event store exists only in the profile that has the port. Ask for a combination outside
  that and generation stops with the reason, naming the flag that would fix it *for this backend* —
  `--http fastify` on a Python project is refused with `--http fastapi`, not with a suggestion it cannot
  act on. `--auth keycloak` with no transport is refused too: the authorization-code flow has nowhere to
  receive its redirect, and the generated project's own pruner refuses the same combination later.
  `--users keycloak` with no transport is refused for its own reason: the customer's token arrives over
  HTTP, so an adapter with no transport has nothing to validate.

## Answering an axis again later

A generated project can answer any axis again at `./init --event-store memory`, `./init --http none`,
`./init --auth none` or `./init --users none`, which removes that answer's adapters, containers, environment
keys, dependencies and Make surface. What two answers share is kept while either remains: the Keycloak
container's Compose block, its README and the Java OIDC dependencies are marked `keycloak|users-keycloak`,
so dropping the staff realm leaves the customers realm a working issuer, and the container goes with the
last realm. Answering one axis leaves the others open, and `scripts/backing-services.py --list` shows what
each can still be given. Pruning only ever subtracts: a project generated on SQLite can drop to memory but
cannot become a Postgres project, and it says so rather than pretending.

The answer is written down as well as applied. `project.json` is rewritten in the same run — each
deployable's `selection` records the new answer and its `capabilities` records what that answer gives — so a
re-answered project reads exactly as one generated with those answers. Everything downstream follows from
that one record: `slipwai replay` and `slipwai migrate` regenerate from it rather than putting the dropped
adapter back, and `make check-agents` names the skills the project can no longer use ([skills](skills.md)).
`generator` is left as it was: `./init` is the copy of the factory the project already records, so nothing
newer has written here and `migrate` still knows which catch-up notes are owed.
