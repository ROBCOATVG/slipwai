# Architecture

Dependencies point inward: delivery adapters call application use cases; application code calls ports; domain code stays free of delivery and persistence concerns. Tests at the boundary protect observable behaviour.

## Services

`apps/` holds one directory per service — {{services}} — each an independent deployable in its own language
and framework that starts with a health capability only. Every service owes the same things:

- the eight Make targets (`install`, `lint`, `typecheck`, `test`, `integration`, `adversarial`, `audit`,
  `mutation`): the root Makefile runs each recipe for every service, so there is one gate rather than one
  per service, and `make verify` is the same command however many there are;
- two probes on its own port, both paths in `infra/service/project.auto.tfvars.json`: liveness, which says
  only that the process is up, and readiness, which asks the service's own store a trivial question — so a
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
is shared among the deployables of that language. {{shared-code}}

The hexagonal rule applies inside it — a shared package that reaches for a framework or a driver is an adapter
every service now depends on — and `make check-imports` reads `packages/` the same way it reads `apps/`. Share
a contract when two services have a real consumer for it, not before; a contract crossing languages is an API
between services, not a package.

## Bounded contexts

Every service records what it owns and the bounded contexts it holds — `purpose` and `contexts` on its
`project.json` entry, given to `generate` or `add-service` as `--purpose` and `--context` (once per context),
and recorded afterwards with the factory's `slipwai describe-service <name> --purpose "..." --context <name>`,
which rewrites this page and every other file that prints them:

{{contexts}}

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
   that module{{model-gate}}. Which contexts a service holds is found, not declared up front — in the event
   model's lanes where this project keeps one, in the specification's vocabulary otherwise; `/sail` says
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
<!-- section: browser -->

## Browser frontend{{browser-plural}}

{{browser-paths}} {{browser-is}} independently built TypeScript/React browser application{{browser-plural}}
({{browser-proxies}}). {{browser-consumes}} deliberate HTTP or query contracts from the services; {{browser-imports}} backend
implementation code or persistence types. Keep component-local state local, remote server state behind the
frontend's API boundary, and navigational state in the URL. Share generated contract artifacts under
`packages/` only when two deployables have a real consumer for them. Add a browser app with the factory's
`add-frontend <name> [--api <service>]`, run from this directory.
<!-- end section -->
