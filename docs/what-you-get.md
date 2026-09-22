# What a generated repository gets for free

A tour of everything that is in a project from its first commit. Each area links to the page that covers it
properly.

- [The layout](#the-layout)
- [The read side](#the-read-side)
- [The method, on top of Spec Kit](#the-method-on-top-of-spec-kit)
- [Documentation written for this project](#documentation-written-for-this-project)
- [One canonical source, 36 agent harnesses](#one-canonical-source-36-agent-harnesses)
- [Running it, from the first commit](#running-it-from-the-first-commit)
- [Everything else](#everything-else)

## The layout

Every generated repository is monorepo-ready immediately:

```text
apps/service/       the first service and its native build — one directory per service, listed in project.json
apps/web/           optional TypeScript/React/Vite browser application
packages/           code shared between services, per language
docs/               generated product, workflow, architecture, and event-model documentation
commands/           the workflow commands, adapted to this project
agents/             the named agent type for each stage /drive delegates, with its scope and its model
skills/             the working guidance this project can use, in this project's own languages
scripts/verify      the repository-wide local/CI gate
infra/              OpenTofu, under --target aws or --target azure
Makefile            setup, run, quality, test, model, agent, audit, deploy and CI targets
docker-compose.yml  the app and whatever backing services it was given
.editorconfig       the whitespace conventions, for editors that read them
.nvmrc              the Node major CI and Compose are pinned to, where there is an npm workspace
.python-version     the CPython minor they are pinned to, where there is a Python service
renovate.json       how the exact pins are kept from becoming old exact pins
LICENSE             All rights reserved, until whoever owns the code decides otherwise
SECURITY.md         how a vulnerability reaches the people who can fix it
.github/PULL_REQUEST_TEMPLATE.md  what this project asks of a change, and nothing it does not
```

Every pin is derived from the one constant the CI workflow and the image build already read, so a laptop
cannot be told a different version from the gate. Go and Java take no file of their own: their toolchains are
pinned in `go.mod` and in the committed Maven wrapper, which is where their own tools already look.

`renovate.json` is written for the repository's actual layout — the npm workspace, `requirements-dev.txt`
under each Python service (which Renovate's own default pattern misses), the Go modules, the poms, and the
GitHub-Actions-format workflows a Gitea forge runs. Updates are grouped per ecosystem into one weekly pull
request; the lockfile refresh is monthly; a major waits on the dependency dashboard, because a major in an
exactly pinned tree is a piece of work rather than a bump; a vulnerability fix ignores the schedule. The
toolchain is one group of its own, so the pin file, the workflow's `setup-node` input and the Compose image
move together — a custom manager reads the workflow input, which no Renovate manager does.

**It does nothing until a bot runs it.** On GitHub that means the Renovate app installed on the repository;
on a Gitea or Forgejo forge it means a self-hosted run — `renovate` as a scheduled workflow on the forge's
own runner, or a cron job — with a token that may open pull requests. Until one of those exists the file is a
statement of how the project wants to be updated, and nothing more. The factory itself carries one too, over
the manifests under `assets/` ([Work on the factory](maintaining.md#regenerate-the-dependency-locks)).

`LICENSE` is deliberately not a licence. A generated project is the customer's, there is no licence axis and
this factory does not invent one, so the file says `All rights reserved` — which is where a repository with
no licence file already stands, stated clearly rather than by silence — with the project's name and the year
filled in, and says where to take the real text from and to record the choice as an ADR when it is made. A
permissive licence written in by a generator would be a grant nobody made, and a grant is hard to take back.
`SECURITY.md` is complete but for the contact, which is marked as the one line the project has to replace.
The pull-request template names `make verify` and the gates and rules this particular project has — the event
model, the expand/contract rule, the flag gate, the ADR test — and says plainly that the project keeps no
changelog of its own, because the record of a change here is the slice's artifacts under `specs/`.

There is deliberately **no archived template tree and no parity inventory**: a generated repository contains
only material people and agents should actually use.

The layout is also the boundary. The delivery profile is deployable-scoped — continuous-delivery practices
and the Event Modeling journey cover the whole monorepo, but event sourcing applies only to the services
under `apps/`. `apps/web` consumes published API and query contracts and uses ordinary component, server and
URL state; it never reads a backend stream or an event store. Published is meant literally: a Fastify or
FastAPI service serves its OpenAPI document at `GET /openapi.json`, built from the very schemas its routes
are validated with, and a Go service carries a hand-written `openapi.yaml` whose paths a test holds to the
routes its mux serves. Generated metadata, architecture documentation and `AGENTS.md` all encode that
explicitly, and name the path.

## The read side

*Event profile.* The write side of a generated project was always finished: `EventStore` with `read`,
`append` against an expected version and `readAll` for a rebuild, three adapters, one contract suite run
against all of them. Beside it now is the half that used to be greenfield — the machinery a read model is
*maintained* with, the same set in every backend, so a slice choosing where its view lives is choosing
between three things that already exist rather than between one that is free and two that are not.

| | Is |
|---|---|
| A unit of work on the store | The seam that suspends `append`'s own commit, so a view write and the events it derives from land in one transaction or not at all. Outside one, `append` commits itself exactly as it always did; on the JVM the seam is the framework's own transaction manager behind a `Transactions` port, so a `@Transactional` slice gets it with nothing wired between them |
| `CheckpointStore` | Where a named projection has got to, plus an exclusive lease with an expiry so a dead worker's projection resumes on its own — with memory, SQLite and Postgres adapters and a contract suite of its own run against all three |
| The catch-up runner | `catch_up` applies the log in batches and advances the checkpoint **inside the view's own transaction**, which is exactly-once with no idempotency key in it; `rebuild` empties the view and folds the whole log back into it, holding the lease across both |
| What loops over it | Each framework's own mechanism rather than a worker this factory invented: a `@Scheduled` bean under Spring Boot and Quarkus, a Fastify plugin whose `onClose` stops the timer with the server, a FastAPI lifespan, a blocking `Run(ctx)` in Go. Inert until the project has a store, a checkpoint store and at least one projection |
| A derived tag index | `event_tags` is written inside the append's own transaction from the project's own tagging function — an index over the log, never a fact stored on an event. `read_tagged` and `append_if` are what it buys: a conditional append guarded by a query, which is the constraint spanning two entities that an expected version cannot express |

Which of the three a view uses is the slice's own `materialisation` answer, and `make check-model` asks for
it before the slice can be planned — the field exists because, with no checkpoint store in the skeleton,
folding the log on every query used to be the only read path that was free, and so the one every project
got whether or not anybody weighed it ([The global event model](event-model.md)).

## The method, on top of Spec Kit

Spec Kit supplies the phases. The project supplies the method around them:

- **[The delivery loop](delivery-loop.md)** — `/drive`'s ten-stage ladder — eleven under a production target, which adds the release constraint — resumable because it reads
  artifacts rather than conversation memory; the seventeen workflow commands — fifteen in `standard`; story splitting and example mapping
  as first-class stages; and the hooks that apply the method even to a session that never typed `/drive`.
- **[The skill catalogue](skills.md)** — as many of the 49 as this project can use, with code examples rendered in the languages this
  project's services are actually written in.
- **[The global event model](event-model.md)** *(event profile)* — one cumulative model for the whole
  system, rendered by `make model` into a browsable page, and held to the code by `make check-model`.
- **[Gates](verification.md)** — what `make verify` runs, what is deliberately kept outside it, and why the
  split falls where it does.
- **[Bootstrap Spec Kit](spec-kit.md)** — how Spec Kit is obtained, the preset layer that means it is never
  edited in place, and the constitution floor gated from both directions.

## Documentation written for this project

Every page under `docs/` is generated rather than copied, because each says something only this project
knows: which native gate `make verify` actually runs, whether there is a browser app, which services exist
and what contexts they hold, what its own AWS answers deploy.

| Page | Says |
|---|---|
| `getting-started.md` | Bootstrap Spec Kit, run the gate, start the first slice |
| `workflow.md` | The delivery loop each slice travels, as a diagram, from constitution to hardening |
| `first-slice.md` | What a slice looks like on disk, and the four things that cost real debugging to learn |
| `whats-included.md` | Everything generated, in one list |
| `architecture.md` | The hexagonal boundary, the services, and the bounded contexts they hold |
| `gates.md` | What `make verify` runs, and the gates beyond it |
| `skills-and-commands.md` | The catalogue and the commands adapted to this project |
| `agent-harnesses.md` | How `skills/`, `commands/` and `agents/` are projected into each coding agent |
| `speckit-preset.md` | How this project's templates reach Spec Kit without editing it |
| `event-model/README.md` · `event-modeling-to-code.md` | *(event)* The model format and the four patterns; what each box becomes in a file |
| `deployment.md` · `adr/0002-production-target.md` | *(AWS)* What runs, how a commit gets there, why, and what it costs |
| `adr/0001-record-architecture-decisions.md` | The decision to record decisions, and the ADR shape |
| `evolving-the-project.md` | The project owns every generated file — rename, move, replace or delete anything — and how a newer factory's output is offered to it as a merge |

`docs/README.md` indexes **every page that shipped**, including any the index does not know by name, which
is what stops a reader failing to find a document that exists.

## One canonical source, 36 agent harnesses

`skills/`, `commands/` and `agents/` at the repository root are canonical. `./init --integration <agent>` projects them
into whichever harness you use — Claude Code, Cursor, Codex, Copilot, Gemini CLI, Zed, opencode, Amp, Goose,
Kiro, Junie and 25 more — each in its own native location and command format, from a registry derived from
Spec Kit's own.

`make agents` refreshes elected extension guidance before the harness projections, `make agents-list` shows
every supported harness and which are installed, and `make check-extensions` / `make check-agents` fail
inside `make verify` when either projection has drifted from its root source.
Edit the root copy; never the projection.

`agents/` holds one named type per stage `/drive` sends to a fresh context — `drive-tasks`,
`drive-implement`, `drive-converge`, `drive-gaps`, `drive-adversary`, `drive-mutation` — and `drive-slice`, for the whole-slice
delegate a concurrent fan-out spawns. Each declares what its delegate may write
and what it may run, and the projection into your harness enforces as much of that as the harness can express
(Codex's sandbox, Cursor's `readonly`, Copilot's and Gemini's tool lists, opencode's permissions, Claude
Code's `disallowedTools`) and says in its stamp what it could not. An adversary that cannot edit beats an
adversary asked not to.

`.specify/models.json` says which model runs each stage of `/drive` — `strong` for judgement, `fast` where the
input is already on paper — and the registry says per harness whether a sub-task can be given a model at all;
`make models` shows what results ([Who runs each stage](delivery-loop.md#who-runs-each-stage)). `/benchmark` draws
`specs/<feature>/benchmark.md` — what each slice cost and how each stage did, read from the harness's own transcript
and the slice's artifacts — and `make benchmark` prints the same table ([What each stage
costs](delivery-loop.md#what-each-stage-costs)).

## Running it, from the first commit

```sh
make dev       # the service in the foreground
make dev-web   # the browser app beside it
make demo      # the whole thing in containers, printing the addresses once it answers
```

`make demo` runs that same `make dev` inside the image CI uses, over the mounted checkout rather than a
built image — so the two paths cannot drift, and there is nothing to rebuild between an edit and a demo.
The app's Compose services sit behind an `app` profile, which is what keeps `make services-up` meaning the
backing services and nothing else.

The dev server binds loopback, as Vite does by default, and takes `WEB_HOST=0.0.0.0` for when the browser is
not on the machine running it — a container, a VM, a remote sandbox — which is what Compose already sets for
the demo's own `web` service.

Each project also carries a generated `run-the-app` skill describing its own run path: what it serves before
the first slice exists, and how far to go before opening a browser.

## Everything else

- **[Services and bounded contexts](services.md)** — `project.json`'s one list of applications, each with
  its own language, framework and answers; what a second service is in each language; `add-service` and
  `add-frontend`; and where contexts are found rather than declared.
- **[The AWS target](aws-target.md)** — `infra/` in OpenTofu, one ECS service per application deployed
  blue/green, the pipeline from a push to production, a one-command rollback, and what it costs.
- **[The Azure target](azure-target.md)** — the same promise on Container Apps, held against that page
  line for line: what it costs against AWS, and the four places the two are not alike.
- **[Extensions](extensions.md)** — optional dev tooling adopted with `./init --extension <key>`, none of
  which changes the generated skeleton's code.
- **[Project shape](axes.md)** — every axis, what each answer brings, and how a project answers one again
  later.
