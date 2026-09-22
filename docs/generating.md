# Scaffold a new project

New here? [Generate a new project — learning path](learn-generate.md) is the short route: install, first
session with terminal screenshots, then upgrade, migrate and `/catch-up`. This page is the full reference.

Install `slipwai` once ([Install the command](executable.md)), then run it from wherever the new
repository should appear. You do not need a checkout of this factory:

```sh
slipwai generate
```

## The interactive form

With no arguments after `generate`, the generator asks for each value in turn. In a terminal every question with a fixed
list of answers — the target, the language and framework, the frontend, each axis — is a list to move
through with the arrow keys (↑/↓, or `j`/`k`; a letter jumps to the answer starting with it) and choose with
Enter, so nothing has to be typed exactly; each row shows what the answer means. The transcript below is the
typed form of the same questions, which is what you get when stdin is not a terminal (a pipe, a script) and
on Windows. Press Enter to accept a displayed default:

```text
Create a new product monorepo. Press Enter to accept a shown default.
Project name: my-product

Delivery foundation:
  event-modelling — Event Modeling — everything above, plus events as the source of truth, built one stamped slice at a time. Cost per slice stays flat as the system grows, and folding the log back down into tables stays available. Recommended for a product a team will grow for years
  standard — Standard — walking skeleton, executable test and the CD gate, over state-stored persistence. The cheaper start and the irreversible one: cost compounds as one aggregate accretes every new feature, and history you never recorded cannot be recovered. For a tool, a spike, an internal script — anything whose expected lifespan is short

Only one direction is cheap. An event log folds down into tables whenever you decide it should, so a
project can stop being event-sourced; state cannot be turned back into history it never recorded, so
"start standard and adopt events where a subdomain earns it" is an option that mostly does not exist.
What Event Modeling promises is flat cost per slice, not a cheap start: event upcasting and PII
erasure are fixed costs to pay before growth arrives, not slice-shaped ones. Persisted projections
were a third until the skeleton started shipping them.
Use Event Modeling? [Y/n]:

Production target:
  none — Local only — nothing is deployed anywhere; `make verify` is the end of the road
  aws — AWS — one ECS service per app deployed blue/green behind its own load balancer, RDS Postgres, Cognito and S3 + CloudFront, provisioned by OpenTofu and deployed by the trunk pipeline
  azure — Azure — one Container App per app deployed by revision behind the environment's own ingress and managed certificate, PostgreSQL Flexible Server, Entra ID and Static Web Apps, provisioned by OpenTofu and deployed by the trunk pipeline
  existing — Existing — this project deploys to infrastructure it does not own: whatever runs it is described in `docs/deployment.md` and provisioned by nobody here; `make verify` is the gate and nothing is deployed by the factory (experimental, with brownfield adoption)
Choose (none/aws/azure/existing) [none]:
Language (typescript/python/go/java) [typescript]:
Service name [service]:
Frontend (none/react-vite) [react-vite]:
Browser app name [web]:

Event store:
  Where events live. Every answer is an append-only log behind one port, and the in-memory adapter ships with all of them, so `make verify` needs no Docker whichever store is chosen

  memory — In-memory — zero infrastructure, loses all truth on restart. The adapter the port's contract runs against in `make verify`
  sqlite — SQLite — a real append-only log in one file, no container. Serialised writes, so it cannot prove concurrent behaviour
  postgres — Postgres — append-only table, unique (stream, version) as the concurrency control
Choose (memory/sqlite/postgres) [postgres]:

HTTP transport:
  What accepts inbound HTTP. One transport per backend, the ecosystem's own, or none for a library or worker

  none — None — library or worker only, no inbound HTTP
  fastify — Fastify — JSON API, schema-parsed at the edge
Choose (none/fastify) [fastify]:

Staff authentication:
  Who authenticates staff. Every provider on this axis is an OIDC issuer and OIDC is what the adapters speak, so the protocol is the one thing every answer has in common — which is why the axis is named for the role and not for it

  none — None — no staff identity yet
  keycloak — Keycloak — self-hosted OIDC, container and group mapping scaffolded (the flow itself is NOT implemented)
Choose (none/keycloak) [none]:

Customer authentication:
  Who authenticates the product's own users — accounts anyone on the internet can create, with sign-up, verification, password reset and a login the browser app owns. Never the staff directory: a separate realm or tenant, even on the same vendor. Every answer is an OIDC issuer, so a service validates a customer's token the way it validates a staff one, against a different issuer

  none — None — no customer accounts yet
  keycloak — Keycloak — a customers realm beside the staff realm in the same container, self-registration and password reset on, a public PKCE client for the browser app; the browser login is real, and a service's token validation is the framework's where one owns startup and NOT implemented where none does
Choose (none/keycloak) [none]:
Output parent [/work/projects]:
created: /work/projects/my-product
```

**The service and the browser app are asked their names.** `service` and `web` are the defaults, and the
names every project had before they could be chosen; `apps/<name>` is where each one lives, and the name is
also its Compose service and its package. A project that will hold several services usually wants its first
one called after what it does. Whatever it is called, the first service keeps the role: `make dev` runs it,
`PORT` is its port, and its package is named after the project alone. A name has to be lowercase letters,
digits and hyphens, starting with a letter, and the two have to differ. Later services and browser apps are
named when they are added, by `add-service` and `add-frontend`.

**Where a language has more than one framework, the language question is followed by a framework one.**
Java is the one that does, so answering `java` above adds a second question and the pair resolves to a
single backend. TypeScript, Python and Go each have one member, so the question is not asked for them —
the same rule the axes follow: something with one answer is not a choice, and offering it teaches the
reader that it is.

```text
Language (typescript/python/go/java) [typescript]: java

Application framework:
  quarkus — Java — Quarkus owns startup (Agroal, Flyway, SmallRye Health, OIDC); Maven, Checkstyle/PMD/SpotBugs, JUnit 5
  spring-boot — Java — Spring Boot owns startup (HikariCP, Flyway, Actuator, Spring Security); Maven, Checkstyle/PMD/SpotBugs, JUnit 5
Choose (quarkus/spring-boot) [quarkus]:
```

The HTTP transport question that follows then offers that backend's own — `quarkus-rest` or `spring-web` —
because a transport is implemented per backend rather than per language.

**The production target is asked right after the foundation.** It comes before the language because it
decides the menus that follow: an option is offered under the targets it declares, the way it is implemented
for the backends it declares. Under either cloud the event store offers no SQLite, the identity questions
offer that cloud's own answer instead of Keycloak, and the transport question has no `none` — the target
deploys an HTTP service, so a project going there has to have one. Where the two clouds differ is on the
`--users` axis, which `azure` has no answer to yet and says so. `none` — local only, `make verify` the end
of the road — is the default, and every project records its answer as `"target"` in `project.json`. See
[Production target](axes.md#production-target) for what changes, and [The AWS target](aws-target.md) or
[The Azure target](azure-target.md) for what a project on each is given.

```sh
slipwai generate shop --target aws --language go --frontend react-vite --auth cognito --output /work/projects
```

Choosing a cloud also checks, there and then, that this machine has what the generated `./init` will use —
`tofu`, that cloud's own CLI (`aws`, or `az` under `--target azure`), the region it deploys to, and `gh` or
`GITEA_TOKEN` — and refuses with install pointers if not, because finding out at the end of `./init` is the
wrong moment. The list is the target's own (`targets.TOOLS`), and it is the same list the generated `./init`
looks for, so a project is never refused for a tool its own script does not check. `--skip-checks` generates
anyway, for when another machine will run `./init`.

Each axis is asked separately, and only when the chosen profile and backend can actually be given a choice —
so the prompt never offers a combination that would then be refused. Every answer shows what it means,
because `postgres` and `sqlite` look interchangeable until you read that only one of them can prove a
concurrency guarantee. The profile question is written out the same way and for a stronger reason: it is the
only answer a generated project can never revisit, and the cheaper foundation is the irreversible one — see
[Which profile](axes.md#which-profile) for that argument in full, and [Project shape](axes.md) for what each
answer brings.

This example accepts the default `event-modelling/typescript` foundation with its `react-vite` frontend, the
Postgres event store, the Fastify transport that comes with a TypeScript backend, no identity provider, and
the default output parent, creating:

```text
/work/projects/my-product
```

## The argument form

Select another foundation explicitly:

```sh
slipwai generate payments-platform \
  --profile standard \
  --target none \
  --language go \
  --frontend react-vite \
  --output /work/projects
```

Or with local infrastructure:

```sh
slipwai generate ledger \
  --profile event-modelling \
  --language typescript \
  --frontend react-vite \
  --event-store postgres \
  --http fastify \
  --auth keycloak \
  --users keycloak \
  --output /work/projects
```

Each axis is independent, so a Go service on SQLite with no identity provider is just as valid:

```sh
slipwai generate telemetry --language go --event-store sqlite --http net-http --output /work/projects
```

The argument form is useful for scripts and CI. A project name is required whenever any arguments are
supplied; the interactive questions are started only by `slipwai generate` with nothing after it.

`--language` and `--framework` mirror the two questions above, and `--backend` names the resolved pair
directly — which is the form a script wants, since it needs no knowledge of which languages have
frameworks:

```sh
slipwai generate ledger --language go                          # a language whose family has one member
slipwai generate ledger --backend go                           # the same thing, named directly
slipwai generate ledger --language java --framework spring-boot # a language that offers a choice
slipwai generate ledger --backend java-spring                  # the same pair, named directly
slipwai generate ledger --language java                        # the family's default framework, `quarkus`
```

Mixing the two spellings is refused rather than resolved: `--backend` already names the language *and* the
framework, so passing `--framework` beside it has no reading that is not a mistake.

`--service-name` and `--frontend-name` are the two name questions; `--frontend-name` beside `--frontend none`
is refused, because there is no browser app to name:

```sh
slipwai generate acme --service-name ledger --frontend-name portal   # apps/ledger and apps/portal
```

`--output` is always the **parent directory**, not the final repository path. The example creates:

```text
/work/projects/payments-platform
```

## Add a service to an existing project

Generation is one-shot (below), and a generated project can still be given another service by the factory
that generated it — in the first service's language with its answers, or in
another language with its own:

```sh
cd /work/projects/payments-platform
slipwai add-service ledger                      # like the first service
slipwai add-service audit --language python --event-store sqlite
make verify
```

It reads `project.json`, scaffolds `apps/<name>` with the walking skeleton a service of that language starts
with, on the next port, and regenerates the files that list drives — the skills' example snippets among
them, so a project written in two languages shows both at every example, each block labelled with its
language and the services it is for. `add-frontend <name> [--api <service>]`
does the same for a browser app — which is also how a project generated with `--frontend none` gets its
first. `describe-service <name> --purpose "<what it owns>" --context <name>` records what a service already
there is for, once the model or the specification has said, and regenerates the files that print it. Nothing
is committed. [Services](services.md#adding-a-service-add-service) has what each writes, how it decides, and
what it refuses.

## Generation is one-shot

- the target must not exist;
- files are assembled in a temporary sibling and moved into place only after a successful scaffold;
- the project is initialized as a local Git repository on `main` with one initial commit;
- no remote is created; and
- no list of files the factory may later overwrite is left behind. The product owns every generated file.
  `project.json` records the answers it was generated from and which factory version did it — provenance,
  which nothing generated reads.

Running the same command again refuses to touch the existing product repository. A newer factory reaches a
project already generated by *merging*, not by generating over it: `slipwai migrate`, run inside the
project, generates the current factory's output for those recorded answers and merges it over what the
project has become, so the project decides every place the two disagree — see
[Bring a generated project forward](upgrading.md).

## What a generated repository contains

Every project starts monorepo-ready:

```text
apps/service/   the first service and its native build — one directory per service, listed in project.json
apps/web/       optional TypeScript/React/Vite browser application
packages/       code shared between deployables, per language — an npm package here declares a
                `build` script and `make build-packages` builds it before anything compiles against it
docs/           product, workflow, architecture, and optional event-model documentation
commands/       project workflow commands
skills/         project-owned working guidance
scripts/verify  repository-wide local/CI gate
Makefile        discoverable setup, run, quality, test, model, agent, audit, and CI targets
docker-compose.yml  the app and whatever backing services it was given, for `make demo`
.editorconfig   the whitespace conventions; `.nvmrc` and `.python-version` beside it pin the toolchains
                a laptop picks up, from the same constants CI and the image build read
renovate.json   how the exact pins are kept current, written for this repository's own layout
LICENSE         All rights reserved, with the project's name and year, until its owner decides otherwise
SECURITY.md     how a vulnerability is reported, with the contact left as the project's to fill in
```

`make dev` runs the service in the foreground, `make dev-web` the browser app, and `make demo` the whole
thing in containers — the last one running the same `make dev` inside the image CI uses, over the mounted
checkout, so there is no Dockerfile to keep in step and no image to rebuild before a demo. The app's Compose
services sit behind an `app` profile, which is what keeps `make services-up` meaning the backing services
and nothing else. The dev server binds loopback, as Vite does by default, and takes `WEB_HOST=0.0.0.0` for
the case where the browser is not on the machine running it — a container, a VM, a remote sandbox — which is
what Compose already sets for the demo's own `web` service.

Which services a project has is one fact, `project.json`'s `deployables`, and the Makefile, Compose, CI, the
import gate and the pruner all read it — see [Services](services.md) for the shape and for what a second
service is in each language. Each service has its own language, framework and backing-service answers, so a
project may hold a TypeScript service beside a Python one; what is project-wide is the union of what the
services say.

Run `make help` inside a generated repository for the complete target list. `make verify` composes the
native compiler/static checks and tests with architecture-direction, agent-projection, Spec Kit-manifest,
constitution, optional frontend build/component tests, and (for the event profile) event-model gates.
Integration, adversarial, mutation, dependency-audit, and model-rendering targets remain directly runnable
without making every local increment pay their cost.

Each generated repository receives only active material for its selected profile and language:

- both profiles receive the shared delivery skills, adapted `/drive`, `/where-are-we`, `/gaps`, `/adversary`,
  `/mutation` and `/constitution-coverage` commands, `/add-service`, `/add-frontend` and `/catch-up`, plus an `./init`
  bootstrap for Spec Kit and the selected agent integration;
- the event profile additionally receives Event Modeling, event sourcing, and global-event-model skills,
  `/example-map`, `/validate-code-against-model`, and the event-model documentation;
- the skills' examples are rendered in the services' languages, and a skill that still carries TypeScript is
  stamped as pseudocode when no service is TypeScript; and
- runtime, tests, commands, documentation, and gates are generated for the selected native toolchain.

There is deliberately no archived template tree or parity inventory in an output repository. Generated
repositories contain only the tools people and agents should actually use.

## The event-sourcing boundary

The delivery profile is deployable-scoped. Continuous-delivery practices and the end-to-end Event Modeling
journey may cover the whole monorepo, but event sourcing applies only to the services under `apps/`. `apps/web` consumes
published API/query contracts and uses ordinary component, server, and URL state; it never reads backend
streams or an event store. The contract is published rather than described: `GET /openapi.json` on a
Fastify or FastAPI service, `apps/<service>/openapi.yaml` on a Go one. Generated metadata, architecture
documentation, and `AGENTS.md` encode this boundary explicitly and name that path.
