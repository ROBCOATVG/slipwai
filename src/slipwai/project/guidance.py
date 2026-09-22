"""`AGENTS.md` and `docs/architecture.md`: the rules that hold whoever works in the project.

Both are generated from the selection rather than shipped whole, because a rule about an adapter the
project does not have is a rule that teaches the reader to ignore the file.
"""
from __future__ import annotations

from ..backends import event_store_directory
from ..catalog import CATALOG
from ..services import (
    App,
    containers_of,
    contexts_of,
    described,
    families_of,
    has_feature,
    services_of,
    transports_of,
    web_apps,
)
from ..targets import managed
from .compose import composed
from .existing import EXISTING_GUIDANCE
from .flags import reader_calls, reader_paths
from .rules import (
    BROWSER_FLAG_GUIDANCE,
    CLOUD,
    CODE_INDEX,
    EVENT_STORE_GUIDANCE,
    FLAG_GUIDANCE,
    IDENTITY_GUIDANCE,
    PRODUCTION_GUIDANCE,
    SHARED_CODE,
    USERS_GUIDANCE,
    frontend_contract,
)


def architecture(profile: str, apps: list[App]) -> str:
    services = services_of(apps)
    web = web_apps(apps)
    web_paths = ", ".join(f"`{app.path}`" for app in web)
    listed = ", ".join(described(service) for service in services)
    families = families_of(apps)
    # A browser app shares code the same way a service does, and it is the npm family whether or not any
    # service is: without this, a React app beside a Go service is told nothing about `packages/` at all.
    if web and "typescript" not in families:
        families = [*families, "typescript"]
    contexts = "\n".join(
        f"- `{context}` — " + "; ".join(
            f"`{service.path}`" + (f": {service.purpose}" if service.purpose else " (no purpose recorded yet)")
            for service in members
        )
        for context, members in contexts_of(apps).items()
    )
    shared = "\n\n".join(
        f"In {family}: {SHARED_CODE[family]}." if len(families) > 1 else f"{SHARED_CODE[family]}."
        for family in families
    )
    model_gate = (
        ", and `make check-model` makes every slice from `modelled` on name its `context` beside its `service`"
        if profile == "event-modelling" else ""
    )
    base = f"""# Architecture

Dependencies point inward: delivery adapters call application use cases; application code calls ports; domain code stays free of delivery and persistence concerns. Tests at the boundary protect observable behaviour.

## Services

`apps/` holds one directory per service — {listed} — each an independent deployable in its own language
and framework that starts with a health capability only. Every service owes the same things:

- the eight Make targets (`install`, `lint`, `typecheck`, `test`, `integration`, `adversarial`, `audit`,
  `mutation`): the root Makefile runs each recipe for every service, so there is one gate rather than one
  per service, and `make verify` is the same command however many there are;
- two probes on its own port, both paths in `infra/service/project.auto.tfvars.json`: liveness, which says
  only that the process is up, and readiness, which asks the event-store port a trivial question — so a
  service whose store is unreachable stops being sent traffic, and it is what Compose, the load balancer and
  `make smoke` wait on;
- the hexagonal layout — domain and application code free of adapters — which `make check-imports` enforces
  inside every directory under `apps/` and `packages/`, along with the seam between bounded contexts inside a
  service that holds more than one (*Bounded contexts*, below);
- schema change by expand then contract, in separate deployments, which `make check-migrations` holds every
  migration file to: a drop, rename, type change or new NOT NULL column names the earlier additive migration
  it completes, and may not land in the same change as it;
- one slice's reach, which `make check-slice-scope` holds every `slice/<id>` branch to — its own record and
  model block, its service and context, the events module additively, new timestamped migrations only.

Which services exist is recorded once, in `project.json`'s `deployables`. The Makefile, `docker-compose.yml`,
the CI workflow, `scripts/check-imports.py` and `scripts/backing-services.py` read that list and none keeps a
copy, so adding a service is a change to the list and a regeneration of what reads it. That is what the
factory's `add-service` command does — `path/to/slipwai/slipwai add-service <name>`, run from
this directory — and it is the way to add one: it scaffolds `apps/<name>` with the walking skeleton, adapters
and contract tests a service of its language starts with, on the next free port. Without `--language` the
new service takes the first service's language and answers; with it, another language and that language's
own answers, so a project may hold a TypeScript service beside a Python one — and the skills' examples
then come in both languages, each block labelled with the services it is for. Every service's language,
framework and answers are in `project.json`. Replace each service's health example with its first product
slice instead of growing a framework around it.

## Shared code

`packages/` is for code shared between deployables, and a shared package is written in one language, so it
is shared among the deployables of that language. {shared}

The hexagonal rule applies inside it — a shared package that reaches for a framework or a driver is an adapter
every service now depends on — and `make check-imports` reads `packages/` the same way it reads `apps/`. Share
a contract when two services have a real consumer for it, not before; a contract crossing languages is an API
between services, not a package.

## Bounded contexts

Every service records what it owns and the bounded contexts it holds — `purpose` and `contexts` on its
`project.json` entry, given to `generate` or `add-service` as `--purpose` and `--context` (once per context):

{contexts}

A context is a hypothesis about where one model and one vocabulary stop and another begins, and it gets
renamed, split and merged as the model deepens — which is why it is recorded as a field rather than as a
level of the tree, whose paths are baked into module names, Compose and CI. There are three places a
context can live, each costing more than the one before:

1. **A name on a service.** The service is one context, or has been given one. Free: it says what the
   service is for and nothing else.
2. **A directory inside a service** — a `<context>/` directory for each context the service holds (at
   `src/<context>/`, or inside each layer as `domain/<context>/`; the gate keys on the directory bearing
   the context's name, wherever it sits), each with its own glossary and one `public` module (`api` in
   Java) that is the whole of what the other contexts may import. This is the modular monolith a product
   starts as, and the default here: one deployable, several models. Once a service lists more than one
   context, `make check-imports` refuses an import from one context into another that does not go through
   that module{model_gate}. Which contexts a service holds is found, not declared up front — in the event
   model's lanes where this project keeps one, in the specification's vocabulary otherwise; `/drive` says
   where that decision is taken and recorded.
3. **A service of its own** — `apps/<name>`, through the factory's `add-service`. It costs a network
   boundary, a database of its own, its own image, pipeline and on-call.

Which rung a context sits on is two decisions, not one. *Whether it is a context* is a question about
language and ownership — the same word meaning two things, rules that change for different reasons,
different people deciding; `skills/domain-driven-design/resources/bounded-contexts.md` lists the signals.
*Whether it is a service* is a question about deployment: it has to release on its own cadence, scale or
run on its own terms, own its data in a store of its own, belong to another team, or be written in another
language. A context that talks to its neighbour synchronously and often, or shares a transaction with it,
is a context and not a service — keep it on the second rung. Find the boundary there, prove it with the
import gate and with events crossing it, and make it a service the day a deployment reason turns up;
because the seam was already enforced, that is a move rather than a rewrite.

Before placing a slice, read the purposes. With more than one service, the slice names the one that owns
it — the `service` field of its entry in `docs/event-model/model.yaml` where this project keeps an event
model, the plan's *Structure Decision* otherwise — and where that service holds more than one context, the
`context` as well. A slice that no recorded purpose covers is a product decision to ask, not a default to
take. A service with no purpose recorded is the first question to ask, before anything is placed in or
around it.
"""
    if web:
        proxies = "; ".join(
            f"`{app.path}` proxies `/api` to `{app.api}`" for app in web
        )
        base += f"""
## Browser frontend{"s" if len(web) > 1 else ""}

{web_paths} {"are independently built TypeScript/React browser applications" if len(web) > 1 else "is an independently built TypeScript/React browser application"}
({proxies}). {"Each consumes" if len(web) > 1 else "It consumes"} deliberate HTTP or query contracts from the services; {"none imports" if len(web) > 1 else "it does not import"} backend
implementation code or persistence types. Keep component-local state local, remote server state behind the
frontend's API boundary, and navigational state in the URL. Share generated contract artifacts under
`packages/` only when two deployables have a real consumer for them. Add a browser app with the factory's
`add-frontend <name> [--api <service>]`, run from this directory.
"""
    if profile == "event-modelling":
        web_boundary = (
            f" {web_paths} may render commands and read models, but {'they are' if len(web) > 1 else 'it is'} "
            f"not event-sourced and never read{'' if len(web) > 1 else 's'} the event store."
            if web
            else ""
        )
        base += f"""
## Backend event bundle

Event Modeling covers the end-to-end product journey; event sourcing is the executable persistence model
for {f"`{services[0].path}`" if services else "the services"}. They are selected as one backend capability: event names, schemas, stream identity,
optimistic concurrency, and the global model change together. Events are immutable facts; never invent or
rename one merely to unblock implementation.{web_boundary}
"""
    return base


def agent_guidance(profile: str, apps: list[App], target: str = "none") -> str:
    services = services_of(apps)
    web = web_apps(apps)
    service_globs = ", ".join(f"`{service.path}/**`" for service in services)
    ownership = "".join(
        f"- `{service.path}/**` is {'the' if len(services) == 1 else 'a'} `{service.backend}` backend service. "
        f"Use its native toolchain and keep domain/application code\n"
        f"  independent of delivery and persistence adapters.\n"
        for service in services
    )
    if len(services) > 1:
        ownership += (
            "- `project.json` lists the services, each with its own language, framework and backing-service "
            "answers; add one with the\n  factory's `add-service`, never by hand.\n"
        )
    guidance = f"""# Repository guidance

Run `make verify` before declaring work complete. Keep domain logic independent of adapters and make
changes as small end-to-end slices.

Never edit a Spec Kit-managed file in place; override it by name from the preset layer under
`.specify/presets/`, because an in-place edit quietly turns every later `specify integration upgrade` into a
manual reconciliation — `make check-speckit` catches the drift either way.

`.specify/memory/constitution.md` is human-owned and human-amended. Never edit it to make a change pass and
never drop a principle to clear a gate: `make check-constitution` fails when it stops carrying minimum CD,
the practices the skills in `skills/` teach, or the obligations this profile's capabilities claim.
`/constitution-coverage` prints the required text; a finding that needs a decision nobody has made is a
question for the user, not an obligation to invent.
{CODE_INDEX}

## Delegated agents

Each stage `/drive` sends to a fresh context is a named type in `agents/` (and a whole slice is `drive-slice`) carrying that stage's standing brief,
its model and its write scope, projected into the installed harness so it holds what it can. Delegate to the
type: a brief adds only its task-specific contract and file manifest, and restates neither the scope nor `docs/delegated-agent-safety.md` — a brief that restates a rule is one that can fall behind it.
## Deployable ownership

{ownership}"""
    for app in web:
        guidance += f"""- `{app.path}/**` is a TypeScript/React browser frontend{f" talking to `{app.api}`" if len(web) > 1 else ""}. Use browser-facing component tests and do not
  import backend implementation or persistence types.
"""
    if web:
        guidance += frontend_contract(apps)
    if profile == "event-modelling":
        guidance += f"""- Event sourcing applies only to {service_globs}. Event Modeling may describe the full user journey,
  including UI frames, but the browser never owns streams, Deciders, replay, or event-store access.
"""
    if composed(apps):
        guidance += """- A green gate is not a demonstration. `make demo` starts the whole app in containers and prints its
  addresses, `make dev` runs it in the foreground, and `skills/run-the-app/SKILL.md` says what this project
  serves, what to seed first, and how far to go before opening a browser. Show a slice by running it.
"""
    if containers_of(apps):
        guidance += """- `docker-compose.yml` holds the app's own services behind an `app` profile as well as the backing
  services, so `make services-up` still starts only the latter. `make verify` must stay runnable without any
  of it: a test that needs a real backing service goes under the service's integration suite, which only
  `make test-integration` runs.
"""
    if has_feature(apps, "memory"):
        adapters = ", ".join(
            f"`{event_store_directory(service.backend, service.path)}`"
            for service in services
            if service.selection.has("memory")
        )
        guidance += f"""- The event store is a driven port. Domain and application code name the port, never a database type,
  and every adapter under {adapters} passes the same contract suite. Add a store
  capability by extending that contract first, so the adapters cannot drift apart.
"""
    for store in dict.fromkeys(s.selection.feature_of("event-store") for s in services):
        if store is not None:
            guidance += EVENT_STORE_GUIDANCE[store]
    for transport in transports_of(apps):
        guidance += f"""<!-- backing-service:{transport}:begin -->
- The HTTP adapter parses untrusted input into typed commands, calls a use case, and maps the outcome to a
  status. It holds no business rules and makes no authorisation decision — a rule enforced in a route
  handler is a rule the next entry point will not enforce.
- One file binds a port, and it is the only untested file in the service: everything worth asserting about
  a route is asserted against the app object with no socket at all. Keep composition there and behaviour
  out of it. Product routes live under `/api`, which is what the dev server proxies and what an ingress can
  route unchanged; `/health` sits outside it, being a probe rather than API surface.
<!-- backing-service:{transport}:end -->
"""
    for identity in dict.fromkeys(s.selection.feature_of("auth") for s in services):
        if identity is not None:
            guidance += IDENTITY_GUIDANCE[identity]
    for identity in dict.fromkeys(s.selection.feature_of("users") for s in services):
        if identity is not None:
            guidance += USERS_GUIDANCE[identity]
    if target == "existing":
        guidance += EXISTING_GUIDANCE
    if managed(CATALOG, target):
        # The flag rule names the file each service reads one through, rather than describing the
        # convention: an author who has to derive `FLAG_<KEY>` for themselves eventually derives it wrong.
        guidance += PRODUCTION_GUIDANCE[target] + FLAG_GUIDANCE.format(
            readers=reader_paths(apps), calls=reader_calls(apps), cloud=CLOUD[target]
        )
        # The browser half only where there is a browser: the flag rule for an app that does not exist is
        # the kind of rule that teaches a reader to skim the file.
        if web:
            guidance += BROWSER_FLAG_GUIDANCE.format(web=web[0].path)
    if profile == "standard":
        guidance += """
## Per-slice continuation contract

Use `/drive` to resume from the first missing artifact or unchecked task, whether that artifact is the
constitution, the product specification, the split, or the slice's own tasks. Work through specification,
`/gaps` over the slice's acceptance criteria, plan, tasks, RED-GREEN-REFACTOR implementation, the installed
Spec Kit converge command until it reports converged or reaches its bound, `/gaps` over the slice diff, and an actor-visible
demo. Pause at the demo for feedback; after acceptance run `/adversary` when the slice changed attack
surface or closed the split — `commands/adversary.md` makes and records that decision — then `/mutation` and
`make verify`. Stop earlier only for a product decision or unavailable external input.
"""
    else:
        guidance += """
## Per-slice continuation contract

The loop starts when any per-slice command is invoked: `/drive`, `/example-map`, or the installed Spec Kit
plan, tasks, and implement commands. Naming one stage requests that stage and what follows it. A
stage's own done condition is stage completion, not permission to end the delivery loop, and an optional
extension hook is not a gate.

Continue until the actor-visible path is ready for a demo, a product decision or unavailable external input
blocks progress, or the ordered split is exhausted. Before the demo, run the installed Spec Kit converge
command until it reports converged or reaches its bound, and `/gaps` over the slice diff. At the demo, pause for feedback. On
acceptance, harden and finish the slice — `/adversary` when the slice changed attack surface or closed the
split, then `/mutation` and `make verify` — then continue to the ready slices (not done, every `depends_on` done): every unclaimed one whose contract is settled runs concurrently, one delegate per slice on a `slice/<id>` branch, merged in split order (`commands/drive.md`, *Running ready slices concurrently*); where the harness cannot delegate, the earliest in split order, naming the rest.

Under `/cruise` the same contract holds with nobody at the wheel: the two stops that were a person's — a
product decision and the demo — are answered by `drive-skipper` and `drive-hand`, every answer is written where
a person's would have been and again in `specs/<feature>/decisions.md`, and an iteration ends with one line
(`cruise: continue | done | parked: <why> | stopped: human`) that the outer loop reads before it invokes the
next. `commands/cruise.md` is exact; it runs `commands/drive.md` and adds nothing to what a stage produces.

`commands/drive.md` is the resumable entry point at any point in the workflow. It derives the current stage
from artifacts and never re-runs a completed stage merely to make sure. Invoked before the upstream stages
exist — no ratified constitution, no specification, no modelled events, no split — it steps back to the
earliest stage still owing an artifact instead of improvising one. If it conflicts with this file, this
file wins.
"""
    return guidance
