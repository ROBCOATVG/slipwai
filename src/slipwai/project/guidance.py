"""`AGENTS.md` and `docs/architecture.md`: the rules that hold whoever works in the project.

Both are generated from the selection rather than shipped whole, because a rule about an adapter the
project does not have is a rule that teaches the reader to ignore the file.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..deployment_shapes import row
from ..loaded_targets import answer, cloud_of
from ..npm_workspace import npm
from ..registry import SHARED_CODE, registry
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
from ..target_protocol import AGENT_RULES
from ..targets import managed
from .backing_service_prose import stores_by_rung
from .compose import composed
from .existing import EXISTING_GUIDANCE
from .flags import reader_calls, reader_paths
from .rules import (
    BROWSER_FLAG_GUIDANCE,
    CODE_INDEX,
    EVENT_STORE_GUIDANCE,
    FLAG_GUIDANCE,
    IDENTITY_GUIDANCE,
    STATE_STORE_GUIDANCE,
    USERS_GUIDANCE,
    frontend_contract,
    page,
)
from .write_model_prose import agents_write_model, architecture_write_model, store_port_rule


def browser_agreements(web: list[App]) -> dict[str, str]:
    """What the browser section's sentences have to agree with: how many browser apps there are, and where.

    Every one of these is a sentence agreeing with a count, which is the half of a conditional
    `docs/generated-prose.md` keeps in Python — the asset carries the words and this carries the agreement,
    so that neither the asset nor a template language is a second answer to "how many browser apps is it".
    """
    several = len(web) > 1
    return {
        "browser-plural": "s" if several else "",
        "browser-paths": ", ".join(f"`{app.path}`" for app in web),
        "browser-is": "are" if several else "is an",
        "browser-proxies": "; ".join(f"`{app.path}` proxies `/api` to `{app.api}`" for app in web),
        "browser-consumes": "Each consumes" if several else "It consumes",
        "browser-imports": "none imports" if several else "it does not import",
    }


def architecture(profile: str, apps: list[App]) -> str:
    services = services_of(apps)
    web = web_apps(apps)
    families = families_of(apps)
    # A browser app shares code the same way a service does, and it is the npm family whether or not any
    # service is: without this, a React app beside a Go service is told nothing about `packages/` at all.
    if web and not any(npm(family) for family in families):
        families = [*families, web[0].language]
    contexts = "\n".join(
        f"- `{context}` — " + "; ".join(
            f"`{service.path}`" + (f": {service.purpose}" if service.purpose else " (no purpose recorded yet)")
            for service in members
        )
        for context, members in contexts_of(apps).items()
    )
    # Read from the family itself: the page is per family, and names `typescript` for a browser app even
    # where no service is.
    shared_code = {family: registry().families[family].answers[SHARED_CODE] for family in families}
    shared = "\n\n".join(
        f"In {family}: {shared_code[family]}." if len(families) > 1 else f"{shared_code[family]}."
        for family in families
    )
    model_gate = (
        ", and `make check-model` makes every slice from `modelled` on name its `context` beside its `service`"
        if profile == "event-modelling" else ""
    )
    base = page("architecture.md", {
        "services": ", ".join(described(service) for service in services),
        "shared-code": shared,
        "contexts": contexts,
        "model-gate": model_gate,
        **browser_agreements(web),
    }, wanted=("browser",) if web else ())
    if profile == "event-modelling":
        base += architecture_write_model(apps)
    return base


def agent_guidance(
    profile: str, apps: list[App], target: str = "none", shape: str = "liner",
) -> str:
    services = services_of(apps)
    web = web_apps(apps)
    ownership = "".join(
        f"- `{service.path}/**` is {'the' if len(services) == 1 else 'a'} `{service.backend}` backend service. "
        f"Use its native toolchain and keep domain/application code\n"
        f"  independent of delivery and persistence adapters.\n"
        for service in services
    )
    if len(services) > 1:
        ownership += (
            "- `project.json` lists the services, each with its own language, framework and backing-service "
            "answers; add one with the\n  factory's `add-service`, and record what one is for with its "
            "`describe-service`, never by hand.\n"
        )
    guidance = f"""# Repository guidance

Keep domain logic independent of adapters and make changes as small end-to-end slices.

## Two gates, not one

| When | What to run | Why |
|---|---|---|
| Every increment inside a slice | `make unit`, `make lint`, `make typecheck` | Seconds. Run them often enough that a break is one edit old |
| Once, before the merge to `main` | `make verify`, on the rebased branch | The whole of it, including the integration suites and the gates |

`make unit` is the fast half, and it stays fast because of where a test lives rather than because anybody
remembers. **A test that needs a real database, a real process or the network is exercising an adapter, so
it is an integration test**: it goes in the integration suite with the others, and `make unit` does not run
it. The domain and the use cases are tested behind their ports with fakes, which is what makes them quick,
and `make check-imports` is what keeps the three apart. A unit suite that creeps towards minutes is a
suite nobody runs per increment, and then the only gate anyone runs is the one before the merge — which is
version 1's single `make verify` back again, by a slower road.

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

Each stage `/sail` sends to a fresh context is a named type in `agents/` (and a whole slice is `sail-slice-watch`) carrying that stage's standing brief,
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
        guidance += agents_write_model(apps)
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
        guidance += store_port_rule(apps)
    # Keyed by the store *and* the rung: the same Postgres proves a never-write-the-same-version-twice
    # guarantee about a log in one service and a lost-update guarantee about a row in the next, and one
    # paragraph claiming both is a paragraph whose concurrency test nobody can place.
    for store, logged in stores_by_rung(services):
        guidance += (EVENT_STORE_GUIDANCE if logged else STATE_STORE_GUIDANCE)[store]
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
        deployment = answer(target, AGENT_RULES, default="")
        if shape == "skiff" and (choice := row(target, shape)):
            deployment = ("- This skiff deploys one production environment after verify passes; there is no staging "
                          "promotion. Use immutable images, make smoke and the recorded rollback.\n"
                          f"- Compute: {choice['compute']}. Database: {choice['database']}.\n"
                          "- Read infra/SHAPE.md and infra/README.md before changing infrastructure. Shape convergence "
                          "prepares only: retain the current database/state until verified cutover.\n")
        guidance += deployment + FLAG_GUIDANCE.format(
            readers=reader_paths(apps), calls=reader_calls(apps), cloud=cloud_of(target)
        )
        # The browser half only where there is a browser: the flag rule for an app that does not exist is
        # the kind of rule that teaches a reader to skim the file.
        if web:
            guidance += BROWSER_FLAG_GUIDANCE.format(web=web[0].path)
    if profile == "standard":
        guidance += """
## Per-slice continuation contract

Use `/sail` to resume from the first missing artifact or unchecked task, whether that artifact is the
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

The loop starts when any per-slice command is invoked: `/sail`, `/example-map`, or the installed Spec Kit
plan, tasks, and implement commands. Naming one stage requests that stage and what follows it. A
stage's own done condition is stage completion, not permission to end the delivery loop, and an optional
extension hook is not a gate.

Continue until the actor-visible path is ready for a demo, a product decision or unavailable external input
blocks progress, or the ordered split is exhausted. Before the demo, run the installed Spec Kit converge
command until it reports converged or reaches its bound, and `/gaps` over the slice diff. At the demo, pause for feedback. On
acceptance, harden and finish the slice — `/adversary` when the slice changed attack surface or closed the
split, then `/mutation` and `make verify` — then continue to the ready slices (not done, every `depends_on` done): every unclaimed one whose contract is settled runs concurrently, one delegate per slice on a `slice/<id>` branch, merged in split order (`commands/sail.md`, *Running ready slices concurrently*); where the harness cannot delegate, the earliest in split order, naming the rest.

Under `/cruise` the same contract holds with nobody at the wheel: the two stops that were a person's — a
product decision and the demo — are answered by `sail-decide-skipper` and `sail-demo-hand`, every answer is written where
a person's would have been and again in `specs/<feature>/decisions.md`, and an iteration ends with one line
(`cruise: continue | done | parked: <why> | stopped: human`) that the outer loop reads before it invokes the
next. `commands/cruise.md` is exact; it runs `commands/sail.md` and adds nothing to what a stage produces.

`commands/sail.md` is the resumable entry point at any point in the workflow. It derives the current stage
from artifacts and never re-runs a completed stage merely to make sure. Invoked before the upstream stages
exist — no ratified constitution, no specification, no modelled events, no split — it steps back to the
earliest stage still owing an artifact instead of improvising one. If it conflicts with this file, this
file wins.
"""
    return guidance
