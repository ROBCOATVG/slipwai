# Slipwai

[![PyPI](https://img.shields.io/pypi/v/slipwai)](https://pypi.org/project/slipwai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Slipwai creates a new product repository. You answer a few questions. You get a Git repository with one
commit on `main`, ready for coding agents to work in.

Say the name as "slipway".

The canonical source is
[git.treyco.dev/ROBCOATVG/slipwai](https://git.treyco.dev/ROBCOATVG/slipwai).
[GitHub](https://github.com/ROBCOATVG/slipwai) is the public mirror. Report issues and propose changes
there.

```sh
slipwai generate            # answer a few questions -> a fresh Git repo, one commit, on main
cd ledger && ./init         # Spec Kit + your coding agent, on demand
make verify                 # the gate, the same one CI runs
```

**Jump to** — [New to this](#new-to-this--start-here) · [What it is](#what-it-is) ·
[Getting started](#getting-started) · [Cruise](#cruise-drive-with-nobody-at-the-wheel) ·
[What you get](#what-you-get) · [The answers you give](#the-answers-you-give) · [Documentation](#documentation)

---

## New to this — start here

Do not clone this repository to create a product. Install the command once. Then run `slipwai generate` or
`slipwai adopt`.

Two learning paths. Each one installs the command, walks the first session with terminal screenshots, then
shows how to update `slipwai`, how to migrate a project when the factory moves, and how to catch up.
`/catch-up` handles the work a merge cannot finish.

| Path | When |
|---|---|
| **[Generate a new project](docs/learn-generate.md)** | You want a fresh repository. You get a walking skeleton, a gate and a delivery method from a few answers |
| **[Adopt an existing repository](docs/learn-adopt.md)** — experimental | You already have a codebase. Install the method around it, without rewriting it first |

---

## What it is

A factory.

**A generated project owns every one of its files.** It may rename, replace or delete any of them. No file
is marked as belonging to the factory. There is no list of files a project may not touch. The factory never
reaches in and overwrites one. That is what makes the skeleton safe to edit on day one.

It is not a one-way door. You can run the factory again inside a project it made:

- **`slipwai add-service` and `slipwai add-frontend`** read `project.json` and regenerate only the files
  that list the project's applications. The factory derives that set by generating the project twice and
  comparing the results, so it cannot drift from a hand-kept list. **`slipwai describe-service`** records
  what a service already there is for — its purpose and its bounded contexts — and regenerates the same way.
- **`./init`** answers the event store, HTTP, staff identity and customer identity questions again, by
  removing what the old answers brought.

Both respect what the project has become, not what it was generated from.

**Later improvements arrive the same way.** Run `slipwai migrate` inside the project. It generates what the
current factory would produce for the project's recorded answers, then merges that over the project:

- A file only the factory changed is taken.
- A file only the project changed is kept.
- Where both changed, the project decides.

So an upgrade is a merge, never a replace. [Bring a generated project forward](docs/upgrading.md) is the
recipe. `make test-migration` proves it against the last release on every change.

**A merge cannot finish some work.** Examples: a step in a cloud account, an answer the project has to give,
a gate that now judges code written before it. `migrate` leaves these in the project as catch-up notes,
taken from the CHANGELOG entries for the versions just crossed. `/catch-up` works through them against the
project's own `make verify`.

**Everything generated comes from `assets/`.** No starter copy is committed anywhere, so a change in that
tree reaches every combination the moment it is generated.

### The profile is the one answer you cannot change later

| Profile | Includes | When it fits |
|---|---|---|
| `standard` | A walking skeleton, an executable test, a local and CI `verify` gate, a minimum-CD constitution, and the delivery skills and commands | A supporting subdomain, a tool, a spike, an internal script — anything short-lived |
| `event-modelling` | Everything above, plus **Event Modeling and event sourcing as one bundle** — the global model, example mapping, and the model-to-code gate | A product or core domain a team will grow for years |

The two directions are not symmetric. An event log folds back down into tables whenever you want it to.
State cannot be turned into history nobody recorded. So `event-modelling` is the reversible choice.

What it buys is a flat cost per slice, rather than a cheap first slice. That is worth it for a product with
years ahead of it, and overkill for a throwaway tool. It is worth *more* when agents write the slices, not
less: a flat marginal cost per slice is the same property as bounded reading per slice.

Both the prompt and [Which profile](docs/axes.md#which-profile) make this argument before you answer.

Every other question has its own answer, and a project can answer most of them again later. See
[The answers you give](#the-answers-you-give).

---

## Getting started

Four steps. You install a `slipwai` command and run it. You do not clone this repository.

New here? Use the [generate learning path](docs/learn-generate.md), or
[adopt](docs/learn-adopt.md) for an existing tree. Both cover install, first session, upgrade, migrate and
`/catch-up`, with terminal screenshots.

[Scaffold a new project](docs/generating.md) is the full reference.
[Tools required](docs/requirements.md) lists what each toolchain and `make` target needs.

### 1. Get the command

Scaffolding needs **Python 3.11 or later** and **Git**.

**`uv` is the recommended installer.** It is worth having anyway: a generated project's `./init` uses `uv`
to fetch Spec Kit, so one tool covers both ends.

```sh
uv tool install slipwai
slipwai --version
```

`pip install slipwai` is the alternative. There is also a standalone executable that needs nothing but Git.
All three embed the same catalog, templates, skills, commands and locks, and produce identical
repositories. See [Install the command](docs/executable.md).

`slipwai upgrade` moves an installed copy to the newest release. `slipwai upgrade --pre` counts the snapshot
of `main` as well.

This repository is the factory that *makes* the command. Clone it only to change the factory.
[Work on the factory](docs/maintaining.md) is that path.

**Going to a cloud needs four more things on the machine before you generate**, because `./init` there
pushes the repository and bootstraps the account:

1. OpenTofu.
2. That cloud's CLI, signed in with enough authority to create what the bootstrap creates.
3. A region.
4. Access to your forge.

`slipwai generate` checks all four as soon as you choose `aws` or `azure`, and refuses with what is missing.
[Tools required](docs/requirements.md) has the full list. Running costs are in
[The AWS target](docs/aws-target.md) and [The Azure target](docs/azure-target.md), which is also where the
two are compared.

### 2. Generate a project

Run `generate` with no arguments to be asked one question at a time. Pass the answers as flags for scripts
and CI:

```sh
slipwai generate ledger \
  --profile event-modelling \
  --language typescript \
  --frontend react-vite \
  --event-store postgres \
  --http fastify
```

That creates `./ledger` in the current directory, initialised on `main` with one commit. The target
directory must not already exist. `--output` names a different **parent directory**.

### 3. Bootstrap the new repository

Spec Kit is deliberately absent until you ask for it. From inside the generated project:

```sh
./init
```

That installs Spec Kit. It then asks which coding agent to project `skills/`, `commands/` and `agents/`
into — any of [36 harnesses](docs/spec-kit.md). It then offers optional extensions as a checkbox menu:
CodeGraph, UI/UX Pro Max and the UX gates.

`--integration <name>` and `--extension <key>` skip those questions. `--extension` also adds one later. See
[Extensions](docs/extensions.md).

### 4. Work in it, and run it

```sh
make help        # every target, with a line each
make verify      # the gate — native checks, tests, architecture, drift, constitution, event model
make dev         # the service in the foreground
make demo        # the whole thing in containers, printing the addresses once it answers
```

Then open an agent session and type `/drive`. It walks the ladder from principles to a demo the actor can
see, and enters at the first stage whose artifact is missing. See [The delivery loop](docs/delivery-loop.md).

`/drive` stops when it needs a person: for a product decision, and at every demo. `/cruise` answers those
stops itself and keeps going until the specification is satisfied. It has
[a section of its own](#cruise-drive-with-nobody-at-the-wheel), next.

---

## Cruise: `/drive` with nobody at the wheel

`/cruise` is the same ladder as `/drive`, with the two stops that wait for a person answered by the machine.
It decides as the product owner. It runs each demo as the actor. It goes on, one iteration after another,
until the specification is satisfied, and it stops only for you. Nothing about what a stage produces
changes. What changes is who answers.

**What it promises.**

- **It stops only for a human.** A stop file, Ctrl-C, or you typing into the session ends a run. A finished
  slice, a demo, a product question, a stale checkout or a full context does not.
- **Every answer is written down twice.** Once where `/drive` would have written yours, and once in one
  decision log per feature, `specs/<feature>/decisions.md`: the question, the options, the decision, the
  reason, who decided, and what it was written into. Overturn any entry by changing its status and writing
  the answer you want into the artifact it names. The next iteration re-enters the ladder from there. A
  decision that would cost a migration to reverse — an event's schema, stream identity, tenancy, the store,
  personal data — is also an ADR at `Proposed` under `docs/adr/`, for you to accept or supersede.
- **It never invents a fact.** A credential, an external system, a person's approval: the slice is marked
  blocked, the run takes the next ready slice, and a strong delegate works around the block — a fake behind
  the port, recorded as a fake, or the narrower reading that keeps every rule — and writes down what it did.
- **It never makes a gate pass by changing the gate.** `scripts/`, the `Makefile`, `tools/`, CI and the hook
  settings are not an iteration's to edit: Claude Code refuses the edit before it lands, and the runner parks
  the run on any change to them, on every harness. A gate the tree cannot satisfy parks the run with the
  gate's own words as the reason.
- **Every merge is dark.** Under the default release setting each slice ships behind a flag seeded off.
  Nothing the run merged reaches a real actor until you turn a key on.
- **Done means the specification is satisfied.** When the split runs out, an audit reads the specification
  against what shipped. Each finding becomes a new slice, or a recorded decision that it is out of scope.
  Only an audit with nothing left ends the run.

**How to run one.** It ships switched off.

```sh
/cruise-settings enabled=true            # switch it on; commits .specify/cruise.json
/cruise use the PRD in docs/prd.md       # start the runner, detached, and watch it from this session
/cruise-status                           # is it running, how the last iteration ended, the feed's tail
/cruise-watch                            # sit back down at the watch seat, where the feed left off
/cruise-tell take the payments feature next   # queued for the next iteration; --now ends the one in flight
/cruise-stop                             # end the run after the iteration in flight; `now` ends it now
```

Or `make cruise` from a terminal. Either way the runner is the one thing that continues a run: one fresh
headless session per iteration, through any coding-agent CLI on the PATH, until the last line says `done`.
The session you typed in takes the watch seat. It shows the feed as the iteration works — each command, file
and delegate — answers you while it watches, and changes a setting when you ask. Leaving the seat ends
nothing; `/cruise` typed again later sits back down where the feed left off.

**Steer it without stopping it.** `.specify/product-owner.md` is the owner brief: who the actor is, what the
product is for, priorities and tie-breakers, taste, what is out of scope, and what must always ask a person.
The skipper reads it before every decision, so editing it steers the next one. `/cruise-settings` sets who
decides, how it releases, what a demo is driven with, which model the iteration runs on, and the budgets —
iterations, hours, and how many unchanged iterations count as stuck.

**Afterwards, read** `specs/<feature>/cruise-report.md` for what shipped and what was ruled out, then
`decisions.md` for every decision and its reason, then each slice's `demo-log.md` and the evidence under
`demo/`, then the flags: nothing is visible until you turn one on.

**Run it in a sandbox.** An unattended loop runs with the permissions a normal run has; bypassing them all
needs the runner's `--sandbox` flag, and a container around the run. [Cruise](docs/cruise.md) has the whole
of it: the three roles, what it does at each of `/drive`'s stops, every setting, and the limits.

---

## What you get

Everything below is in a generated repository from its first commit.
**[The full tour is here](docs/what-you-get.md)**. Each row links to the page that covers it properly.

[![The delivery loop: run once — principles, specify, gaps, model the events, split into slices — then once per slice: example map, gaps, plan, tasks, implement, converge, gaps, demo, adversary, mutation, next slice](docs/images/delivery-loop.svg)](docs/delivery-loop.md)

| | |
|---|---|
| **[The delivery loop](docs/delivery-loop.md)** | `/drive`'s ten-stage ladder on top of Spec Kit. It is resumable, because it reads artifacts rather than conversation memory. Seventeen workflow commands, fifteen of them in `standard`. Story splitting and example mapping are first-class stages with real heuristics behind them. Hooks apply the method even to a session that never typed `/drive` |
| **[Up to 51 skills](docs/skills.md)** | The part of the delivery catalogue this project can use, owned by the project: TDD, testing, hexagonal architecture, DDD, ubiquitous language, API and BFF design, observability, secure OAuth/OIDC, refactoring, debugging and more. Code examples are rendered in the languages this project's services are actually written in |
| **[The global event model](docs/event-model.md)** | *Event profile.* One cumulative model for the whole system, in `model.yaml`. `make model` renders the timeline, the per-segment diagrams and a self-contained browsable page. `make check-model` fails when the code and the model disagree |
| **[The read side](docs/what-you-get.md#the-read-side)** | *Event profile.* The machinery a view is *maintained* with, finished in every backend rather than left as the greenfield half: a unit of work on the event store; a `CheckpointStore` port with memory, SQLite and Postgres adapters behind a contract suite of its own; a catch-up runner that advances the checkpoint inside the view's own transaction; a rebuild; whatever each framework already schedules a pass with; and a tag index derived from the log, so a conditional append can hold a boundary one stream cannot |
| **[Gates](docs/verification.md)** | `make verify` runs native checks, tests, architecture direction, agent and Spec Kit drift, constitution coverage, and the event model. It is identical locally and in CI, and never needs Docker. Integration, adversarial, mutation and audit checks sit deliberately outside it |
| **[Spec Kit, properly installed](docs/spec-kit.md)** | Obtained on demand rather than vendored. Customised through a preset layer, so it is never edited in place and `specify integration upgrade` stays automatic. The constitution is held to a floor from both directions |
| **[36 agent harnesses](docs/what-you-get.md#one-canonical-source-36-agent-harnesses)** | One canonical `skills/`, `commands/` and `agents/`, projected into Claude Code, Cursor, Codex, Copilot, Gemini CLI, Zed and 30 more. Each delegated stage gets a named agent type, carrying its model and as much of its write scope as that harness can enforce. A gate fails when a projection drifts |
| **[Generated documentation](docs/what-you-get.md#documentation-written-for-this-project)** | Thirteen pages written for this project's actual shape rather than copied, and an index built from the files that shipped |
| **[Services and bounded contexts](docs/services.md)** | One list of applications, each with its own language, framework and answers. `add-service` and `add-frontend` grow it. Contexts are found rather than declared |
| **[A path to production](docs/aws-target.md)** | `--target aws` or `--target azure` gives you `infra/` in OpenTofu, one deployable per application released blue/green, a pipeline from every push to `main` through staging to production, and a one-command rollback. The same promise on either cloud. [The Azure page](docs/azure-target.md) is where they are compared |
| **[Extensions](docs/extensions.md)** | Optional dev tooling, adopted with `./init --extension <key>`: a code index, a design-system generator, and objective UX gates in `make verify`. None of them changes the generated skeleton's code |

### The commands a project gets

Seventeen, of which fifteen are in `standard`. A repository that adopted the method gets four more. None of
them is copied: each is generated against this project's profile, languages, frameworks and services, so
the paths and toolchains named in them are real.

| Command | What it does |
|---|---|
| `/drive` | Takes one slice from wherever it stands to a demo the actor can see |
| `/cruise` | Runs `/drive` on its own, deciding as the product owner and demoing as the actor, until the specification is satisfied. Stops only for a person. `/cruise <kick-off>` gives the first iteration a brief; the session then watches the run and answers you |
| `/whats-next` | Says what is next — one slice, one stage, one command. Reads the disk and changes nothing; beside a running `/cruise`, says what the runner is on instead |
| `/where-are-we` | Shows the progress board: what works, what is in progress, what is still to come; beside a running `/cruise`, the next row is the runner's |
| `/gaps` | Reviews an artifact for holes, before they become rewritten tests |
| `/example-map` | *Event profile.* Turns one slice of the event model into rules, examples and executable scenarios |
| `/validate-code-against-model` | *Event profile.* Checks that the code and the event model still agree |
| `/adversary` | Attacks a finished slice: hostile inputs, replays, interleavings, authorisation paths |
| `/mutation` | Runs the backend's own mutation testing, to find tests that do not really test |
| `/catch-up` | After a migration, works through what the newer factory now asks of code it did not write |
| `/add-service` | Adds a service, with its own language, framework and answers |
| `/add-frontend` | Adds a browser app |
| `/benchmark` | Draws what each slice cost and how each stage did |
| `/constitution-coverage` | Checks the constitution against the floor this project depends on, or prints the floor |
| `/drive-settings` | Shows or changes how `/drive` hands implementation to a delegate |
| `/model-delegation-settings` | Shows or changes which model runs each stage of `/drive` |
| `/cruise-settings` | Shows or changes how `/cruise` runs: who decides, how it releases, what it demos with, when it parks |
| `/cruise-status` | Says whether a `/cruise` runner is running, how its last iteration ended, and shows the tail of its feed |
| `/cruise-stop` | Ends a `/cruise` run after the iteration in flight, or at once with `now` |
| `/cruise-tell` | Queues a message for a running `/cruise`, which the next iteration carries; `--now` ends the iteration in flight for it |
| `/cruise-watch` | Takes the watch seat beside a running `/cruise`: prints the feed as it is written and watches again, starting nothing |

[The delivery loop](docs/delivery-loop.md) describes each one in full, and the ladder they sit on.

#### The three that change settings

Run any of them with no arguments to see the current setting. Pass arguments to change it. Each refuses a
value it does not know and writes nothing, and each asks you to commit the settings file on its own — the
choice is versioned with the project.

**`/drive-settings`** — how much one implementation delegate is handed, and how many failing tests a cycle
opens with. It writes `.specify/drive.json`.

```
/drive-settings                             # show both settings
/drive-settings delegate=task               # one delegate per task
/drive-settings cycle=example               # one failing test at a time
/drive-settings delegate=story cycle=rule   # back to the defaults
```

`delegate` takes `story`, `rule` or `task`. `cycle` takes `rule` or `example`. `cycle=story` is refused:
that is the batch Principle V prohibits.

**`/model-delegation-settings`** — which model runs each stage of `/drive`. It writes `.specify/models.json`.

```
/model-delegation-settings                  # show the table
/model-delegation-settings implement=strong # move a stage to the strong role
/model-delegation-settings claude.fast=haiku  # map a role to a model on one harness
```

A `stage=role` argument moves a stage between `strong` and `fast`. A `harness.role=identifier` argument says
what a role runs on. Changing it also rewrites the agent types, so the harnesses cannot drift apart.

The change takes effect at the next stage `/drive` runs. Nothing already running is interrupted.

**`/cruise-settings`** — how `/cruise` runs `/drive` with nobody at the wheel. It writes `.specify/cruise.json`.

```
/cruise-settings                            # show every setting
/cruise-settings enabled=true               # switch it on; it ships switched off
/cruise-settings release=park               # stop before every push and ask a person
/cruise-settings max_hours=8                # give a run a budget
```

`enabled` switches the command on. `decide` says who answers a product question. `release` says whether every
merge stays behind a flag or waits for a person. `hand` says what a demo is driven with, a browser first.
The rest bound the run: when it counts as stuck, how many iterations or hours it may take, how often a parked
run looks for a reason to resume. [Cruise](docs/cruise.md) explains each one.

---

## The answers you give

Beyond the profile, each role is a separate question, answered independently:

| Question | Flag | Answers |
|---|---|---|
| Foundation | `--profile` | `standard`, `event-modelling` |
| Production target | `--target` | `none`, `aws`, `azure`, `existing` (experimental) |
| Backend language | `--language` | `typescript`, `python`, `go`, `java` |
| Framework, where a language offers more than one | `--framework` | `quarkus`, `spring-boot` (or name the pair at once: `--backend java-spring`) |
| Frontend | `--frontend` | `none`, `react-vite` |
| Event store | `--event-store` | `memory`, `sqlite`, `postgres` |
| HTTP transport | `--http` | `none`, `fastify`, `fastapi`, `net-http`, `quarkus-rest`, `spring-web` |
| Staff authentication | `--auth` | `none`, `keycloak` (local only), `cognito` (AWS), `entra` (Azure), `auth0` (either cloud) |
| Customer authentication | `--users` | `none`, `keycloak` (local only), `cognito` (AWS), `auth0` (either cloud) |
| Dev tooling | `--extension` | `codegraph`, `uipro`, `ux-gates` |

The default is `event-modelling` with `typescript`, the `react-vite` frontend, a Postgres event store, and
the HTTP transport that backend has.

Both identity questions default to `none`, and they are genuinely different questions. Keycloak answers
either one with a realm of its own, in one local container: a staff realm with groups, or a customers realm
with self-registration, password reset and browser login. A service's token validation is only written where
a framework owns it.

`--event-store memory --http none` gives a project with no infrastructure at all.

An unimplementable combination is refused rather than half-ported. [Project shape](docs/axes.md) says which
is which, what each answer brings, and how a project answers a question again later.

---

## Documentation

### Using the factory

| Document | Covers |
|---|---|
| [Generate a new project — learning path](docs/learn-generate.md) | Install, generate, upgrade, migrate and `/catch-up`, with terminal screenshots |
| [Adopt an existing repository — learning path](docs/learn-adopt.md) — **experimental** | Install, adopt, upgrade, migrate and `/catch-up`, with terminal screenshots |
| [Scaffold a new project](docs/generating.md) | The interactive and argument forms, one-shot semantics, the generated repository layout, and the event-sourcing boundary between the services and `apps/web` |
| [Bring a generated project forward](docs/upgrading.md) | `slipwai migrate`: a newer factory's output merged over a project already generated. What comes through clean, what conflicts and should, the catch-up notes it leaves for what a merge cannot do, and the gate that proves it |
| [Adopt an existing repository](docs/adopting.md) — **experimental** | `slipwai adopt`: the method installed around a repository the factory did not make. The survey, the questions with the findings as defaults, what is written beside the code and never over it, what `project.json` records with provenance, and what it forfeits for a language the factory cannot generate |
| [The two workflows](docs/two-workflows.md) | Generated and adopted side by side: the same delivery loop, where each starts on its ladders, the adoption phases woven into `/drive`, the convergence map, and `slipwai converge` as the point where the distinction ends |
| [Project shape](docs/axes.md) | Profiles, target, language, frontend and the axes. What each answer brings, why an unimplementable combination is refused, and how a project answers an axis again later |
| [Tools required](docs/requirements.md) | What scaffolding needs, and what each generated toolchain and `make` target needs |
| [Install the command](docs/executable.md) | `uv tool install` and `pip install` from the forge's registry, the standalone executable, `slipwai upgrade`, and building and publishing both |

### What a generated project gets

| Document | Covers |
|---|---|
| [What a generated repository gets for free](docs/what-you-get.md) | The tour: the layout, the generated documentation, the agent harnesses, and how to run it |
| [The delivery loop](docs/delivery-loop.md) | The `/drive` ladder and the diagram behind it, the seventeen commands, story splitting and example mapping with worked examples, the Spec Kit hooks, the preset layer, and the constitution floor |
| [Cruise](docs/cruise.md) | `/cruise`: the same ladder with nobody at the wheel — the agent decides as the product owner and runs each demo as the actor, writes every answer where a person can overturn it, and stops only for a human; how to start, watch and stop a run, the settings, and the limits |
| [The skill catalogue](docs/skills.md) | The 51 skills grouped by what they are for, why a project is given only the ones whose subject it has, how examples are rendered in your own languages, and where to edit them |
| [The global event model](docs/event-model.md) | Why the model is global, what `make model` renders, the status ladder `make check-model` enforces, and how the browsable page is published |
| [Gates](docs/verification.md) | What `make verify` runs, what is deliberately outside it, and why the split falls where it does |
| [Bootstrap Spec Kit](docs/spec-kit.md) | `./init`, the 36 agent integrations, how Spec Kit is obtained, and the constitution floor gated from both sides |
| [Services](docs/services.md) | `project.json`'s one list of applications, everything that reads it, what a second service is in each language, `add-service` and `add-frontend` and their agent commands, and what a maintainer owes a new generated file that names an application |
| [Extensions](docs/extensions.md) | `./init --extension <key>`, the contract every extension's `init.py` owes, and what makes a second one a catalog entry plus one file |
| [The AWS target](docs/aws-target.md) | What `--target aws` gives: the stacks, the images, the pipeline and the rollback. What it costs, what the factory proves about it and what it cannot, and how the next cloud becomes a row |
| [The Azure target](docs/azure-target.md) | The same for `--target azure`, held against that page line for line: what it costs against AWS and why the gap widens per service, the four places the promise is not quite the same, and what a third cloud would need |
| [Auth0 on both identity axes](docs/auth0-identity.md) | `--auth auth0` and `--users auth0` under either cloud: what the stack creates, the human step no other row has, the three places it is not like for like, and why the provider is chosen at generation time rather than pruned |

### Working on the factory

| Document | Covers |
|---|---|
| [Work on the factory](docs/maintaining.md) | `make verify` and the gates it runs, how `src/slipwai/` is laid out and the check that keeps it that way, browsing generated starters, and regenerating dependency locks |
| [Architecture decisions](docs/adr/) | The factory's own decisions, in the shape its `architecture-decisions` skill asks of a generated project. Here that mostly means the shape of something a project persists, because a project's log is the one thing no version of this factory can migrate for it. [`0001`](docs/adr/0001-a-dcb-capable-log.md) covers the log's derived tag index and why stream-per-aggregate stays the default write path. [`0002`](docs/adr/0002-the-guard-a-slice-declares.md) covers the guard a slice declares, and identity modelled while tags are not |
| [The canonical toolkit](assets/README.md) | The asset tree: where to edit skills, docs, gate scripts, language and frontend packs, and axis adapters |
| [What a backend owes](docs/backend-obligations.md) | The checklist behind adding a language or a framework: every axis, every `make` target and which gate runs it, every per-backend table, the choices that belong to the ecosystem rather than to this repository, and what a framework that owns startup provides instead of a hand-written adapter |
| [Publish the factory to Gitea](docs/publishing.md) | `scripts/publish-to-gitea.py`, cutting a release with `make release`, and the local `pages` server |
| [Changelog](CHANGELOG.md) | Every version, its bump level, what it changed, and what a repository generated by an earlier one owes to catch up |

Adding a language, a framework, a backing service, a target or an extension each has a skill under
`.claude/skills/` that walks the whole checklist.

## Licence and contributing

Slipwai is licensed under the [MIT License](LICENSE). Some adapted skills carry their own nested licence,
including `cli-design` under CC BY-SA 4.0. [NOTICE](NOTICE) lists them, and each complete notice remains
beside its material.

Public issues and proposed changes belong on the
[GitHub mirror](https://github.com/ROBCOATVG/slipwai). See [CONTRIBUTING.md](CONTRIBUTING.md), and report
vulnerabilities through [SECURITY.md](SECURITY.md).
