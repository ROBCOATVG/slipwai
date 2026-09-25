"""`docs/`: the documentation a generated project owns, written for the shape it was given.

Every one of these is generated rather than copied, because each says something only this project knows:
which native gate `make verify` runs, whether there is a browser app, whether the event profile asks
anything of the constitution, and whether there is anywhere to deploy.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..services import App, backends_of, frontend_of, services_of, web_apps
from ..targets import managed
from .backing_service_prose import backing_services_gates
from .commands import command_names
from .design_page import design_page
from .event_model import event_documentation
from .evolving import evolving_page
from .existing import production_included_line
from .flags import FLAG_GATE_NOTE
from .pins import pin_list
from .skills_page import skills_page


def documentation_files(
    project_name: str, profile: str, apps: list[App], target: str = "none"
) -> dict[str, str]:
    """Every file under `docs/` that the services' selections decide the content of."""
    event = profile == "event-modelling"
    frontend = frontend_of(apps)
    services = services_of(apps)
    web = web_apps(apps)
    web_paths = ", ".join(f"`{app.path}`" for app in web)
    backends = backends_of(apps)
    language = ", ".join(f"`{backend}`" for backend in backends)
    gates = {
        "typescript": "Biome — lint, formatting and import order in one pass — TypeScript (`tsc`), and Vitest",
        "python": "Ruff and pytest",
        "go": "gofmt, `go vet`, `go tool staticcheck`, and `go test -coverpkg=./...` held to a minimum by `scripts/go-coverage.py`",
        "java-quarkus": (
            "Checkstyle, PMD and SpotBugs for lint; `javac` with Error Prone and NullAway for the type check; "
            "JUnit 5 with Quarkus's own test harness, coverage through the `quarkus-jacoco` extension"
        ),
        "java-spring": (
            "Checkstyle, PMD and SpotBugs for lint; `javac` with Error Prone and NullAway for the type check; "
            "JUnit 5 with Spring Boot's test harness and MockMvc, coverage through JaCoCo"
        ),
    }
    gate = "; ".join(dict.fromkeys(gates[backend] for backend in backends))
    frontend_item = "".join(
        f"- A separate TypeScript/React/Vite browser application under `{app.path}`, with a styled baseline"
        f" (`docs/design.md`), one route, a typed client generated from the service's published contract,"
        f" and Testing Library component tests\n"
        for app in web
    )
    # Two well-wrapped sentences rather than a conditional spliced mid-sentence: this paragraph is
    # generated for both profiles, and a branch inside a line wraps badly in whichever one loses.
    coverage_scope = (
        """`skills/` teach, and the Event Modeling and event-sourcing obligations. An unfilled
`[PLACEHOLDER]` means drafted rather than ratified."""
        if event
        else """`skills/` teach. Nothing about event sourcing is asked of this profile. An unfilled
`[PLACEHOLDER]` means drafted rather than ratified."""
    )
    command_list = "\n".join(f"- `/{name}` — `commands/{name}.md`" for name in command_names(event))
    production_included = production_included_line(target)
    production_gate = (
        "\n`make ci` also builds every service's production image and runs it locally against its probe "
        "(`make build smoke-image`), which is the half of a deploy that can be proved without an account; the "
        "apply itself is proved by `make smoke` against the environment the pipeline just deployed.\n" + FLAG_GATE_NOTE
        if managed(CATALOG, target)
        else ""
    )
    style_gate = (
        "\n`make check-styles` follows the stylesheets imported into each browser bundle and fails when two "
        "files both declare the same custom property at `:root`. Each file can be correct alone while bundle "
        "order silently changes every use of the token, so one imported file owns each global property.\n"
        if web
        else ""
    )
    first_slice = (
        f"Replace the health example in `{services[0].path}` with the smallest actor-visible product slice."
        if services
        else "Start with the smallest actor-visible product slice in the code that already exists — the factory "
        "made none of it, and `project.json` records where it is."
    )
    files = {
        "docs/getting-started.md": f"""# Getting started

`{project_name}` was scaffolded with the `{profile}` foundation, {language} backend services, and the `{frontend}` frontend.
Bootstrap Spec Kit interactively
with `./init`, or select an
integration explicitly, for example `./init --integration claude` or
`./init --integration cursor-agent`. All additional arguments pass through to
`specify init --here --force`.

{first_slice}{(" Connect it through " + web_paths + " without sharing backend implementation types." if web else "")} Run `make verify`
before and after each increment; it is the same gate CI runs.

Use `/drive` for the complete delivery loop and `/where-are-we` for the progress board at any point; both read
artifacts on disk rather than memory, so one resumes safely and the other changes nothing. See `commands/`, `skills/` and `agents/`.
`/cruise` runs the loop with nobody at the wheel — it decides product questions as the owner and runs each demo
as the actor, and stops only for a person; it ships switched off, and `commands/cruise.md` says how to start it.
""" + ("\nBefore implementation, update `docs/event-model/model.yaml`; commands, events, stream identity, and schemas are one contract.\n" if event else """
When ratifying a constitution, do not paste an Event Modeling or event-sourcing mandate into this
standard profile; `make check-speckit` checks that boundary. `make check-constitution` checks the
other direction \u2014 that minimum CD and the practices the skills teach are still in there.
"""),
        "docs/gates.md": f"""# Verification gates

`make verify` is the deterministic local and CI entry point. It runs {gate}{(" plus Biome, TypeScript and React component tests for " + web_paths if web else "")}, architecture direction,
agent-projection and Spec Kit manifest drift, constitution coverage, event-model validation in the event profile,
and `check-benchmark`, which warns of a benchmark entry left open or a done slice with no record, and
keeps missing measurements visibly unbracketed. `make help` lists integration,
adversarial, mutation, model, benchmark and dependency-audit targets. Mutation and dependency audit remain
explicit end-of-phase/CI operations, not hidden costs in every local increment.

`make check-codegraph` is in the gate for a project that has adopted a code index and a no-op for one that
has not: it fails when `.codegraph/` no longer describes the tracked source — files it has never seen, or
files that changed after it read them. CodeGraph indexes only while a client is attached to its daemon, so a
checkout opened where that tooling is missing keeps a database nothing updates, and a stale index answers
*nothing calls that* in the same words an accurate one uses. The failure says how to catch it up.
{style_gate}{production_gate}
`make check-constitution` is the one gate that reads a document rather than code, and it waits for the
document: `./init` installs the constitution *template*, and while that file is still the untouched template
the gate reports that nothing has been drafted and passes, so the commit `./init` pushes goes through
`verify` before a principle has been written. From the first edit — and regardless, once any feature exists
under `specs/` — it applies in full: `.specify/memory/constitution.md` must carry minimum CD, the practices the skills in
{coverage_scope}

`make constitution-requirements` prints the normative text and `/constitution-coverage` runs the same check
from an agent session. Amend the constitution rather than the gate: a principle deleted from that file is a
gate that silently stopped existing, because every later phase reads it as the authority it claims to be.

Minimum CD here follows [MinimumCD](https://minimumcd.org/minimumcd/) (CC BY-SA 4.0), restated for this
repository and extended with the clause on agent-generated change; `skills/REFERENCES.md` records what was
taken and what was added.

Tests should protect observable behaviour. Keep fast domain tests focused, add adapter contract tests at
real boundaries, and add end-to-end tests only for paths whose integration risk justifies them.
"""
        + backing_services_gates(apps),
        "docs/skills-and-commands.md": skills_page(profile, apps, language, frontend, command_list),
        "docs/whats-included.md": f"""# What's included

{"".join(f"- A native `{s.backend}` application and executable health test under `{s.path}`{chr(10)}" for s in services)}{frontend_item}- A monorepo layout with `apps/` for deployables and `packages/` for code shared between them
- `make dev`, `make dev-web` and `make demo` — the app in the foreground or the whole thing in containers,
  plus a `run-the-app` skill describing this project's own run path
- A complete Make target surface for setup, native static checks, tests, integration tests, agent and
  Spec Kit drift, constitution coverage, event-model validation, mutation, adversarial regression tests,
  audit, and CI
- The shared delivery skill catalogue and adapted workflow commands
- An `./init` bootstrap that installs Spec Kit's planning assets on demand
- The toolchain pins a laptop reads, so it runs what CI runs: {pin_list(apps)}
- `renovate.json`, so exact pins do not quietly become old exact pins — grouped, weekly, majors held back.
  It does nothing until a bot runs it: the Renovate app on GitHub, or a self-hosted run on a Gitea forge
- `LICENSE`, `SECURITY.md` and a pull-request template. Two of them carry a placeholder on purpose — the
  licence is `All rights reserved` until whoever owns this code decides otherwise, and the security contact
  is the one thing only this project knows. The template names this project's own gates and nothing else
{production_included}""" + ("- Event Modeling documents plus backend event-sourcing skills and contracts as one bundle\n" if event else "- No event model or event-sourcing layer\n"),
        "docs/workflow.md": workflow_doc(event),
        "docs/evolving-the-project.md": evolving_page(),
    }
    # What this project's browser surface looks like and where that is decided; nothing at all without one.
    files.update(design_page(apps))
    if event and services:
        files.update(event_documentation(project_name, services[0].backend, services[0].path))
    return files


def workflow_doc(event: bool) -> str:
    discovery = "update the event model and example-map the slice" if event else "write or refine the behaviour specification"
    # Mermaid assigns a node to a subgraph if it is mentioned anywhere inside the block, so every edge
    # that crosses the loop boundary must be declared below the subgraph, never inside it.
    if event:
        diagram = """```mermaid
flowchart LR
  C["/speckit-constitution · principles<br/>make check-constitution gates the coverage"]
  S["/speckit-specify · whole product"]
  G["/gaps · whole spec"]
  EMOD(["event-modeling · events, commands, read models, actors"])
  SS["/story-splitting · slices"]

  subgraph loop["once per slice — /drive owns the loop, repeating until the split is exhausted"]
    direction TB
    EM["/example-map · rules → examples → GWT"]
    EG["/gaps · tighten examples.md, on paper"]
    P["/speckit-plan · one slice"]
    T["/speckit-tasks · one slice"]
    I["/speckit-implement · RED → GREEN → REFACTOR"]
    CV{"/speckit-converge · is everything the artifacts require built?"}
    DG["/gaps · promise → test → production path"]
    D{"demo · actor-visible path"}
    A["/adversary · only when the surface changed, or the split closed"]
    M["/mutation · measure the suite"]
    EM --> EG --> P --> T --> I --> CV
    CV -->|"appends tasks"| I
    CV -->|"converged"| DG --> D
    D -->|"accepted · new attack surface"| A --> M
    D -->|"accepted · surface already in the log"| M
    D -.->|"feedback changes behaviour"| EM
    D -.->|"feedback changes implementation"| I
  end

  C --> S --> G --> EMOD --> SS --> EM

  G -.->|"gap found"| S
  EM -.->|"map reveals more than one slice"| SS
  P -.->|"title still says 'and'"| SS
  M -.->|"next ready slice"| EM
  EM -.->|"an event has no name"| EMOD
  D -.->|"feedback changes slice"| SS
  D -.->|"feedback changes event contract"| EMOD
  D -.->|"feedback changes product scope"| S
```"""
    else:
        diagram = """```mermaid
flowchart LR
  C["/speckit-constitution · principles<br/>make check-constitution gates the coverage"]
  S["/speckit-specify · whole product"]
  G["/gaps · whole spec"]
  SS["/story-splitting · slices"]

  subgraph loop["once per slice — /drive owns the loop, repeating until the split is exhausted"]
    direction TB
    SG["/gaps · tighten the slice's criteria, on paper"]
    P["/speckit-plan · one slice"]
    T["/speckit-tasks · one slice"]
    I["/speckit-implement · RED → GREEN → REFACTOR"]
    CV{"/speckit-converge · is everything the artifacts require built?"}
    DG["/gaps · promise → test → production path"]
    D{"demo · actor-visible path"}
    A["/adversary · only when the surface changed, or the split closed"]
    M["/mutation · measure the suite"]
    SG --> P --> T --> I --> CV
    CV -->|"appends tasks"| I
    CV -->|"converged"| DG --> D
    D -->|"accepted · new attack surface"| A --> M
    D -->|"accepted · surface already in the log"| M
    D -.->|"feedback changes implementation"| I
  end

  C --> S --> G --> SS --> SG

  G -.->|"gap found"| S
  P -.->|"title still says 'and'"| SS
  M -.->|"next ready slice"| SG
  D -.->|"feedback changes slice"| SS
  D -.->|"feedback changes behaviour"| S
```"""
    return f"""# Delivery workflow

{diagram}

For one small vertical slice:

1. {discovery.capitalize()}.
2. Run `/gaps` over what that produced, while a missing state is still a paper edit.
3. Create or resume `plan.md` and `tasks.md` with the Spec Kit commands installed by `./init`.
4. Implement each task RED-GREEN-REFACTOR, keeping `make verify` green.
5. Run the installed Spec Kit converge command, implement whatever it appends, and repeat until it reports
   converged or reaches its bound; then `/gaps` over the slice diff.
6. Demonstrate the actor-visible path and pause for feedback.
7. After acceptance, run `/mutation` and `make verify` — and `/adversary` first, when the slice changed
   attack surface or closed the split.

The principles stage has a gate of its own. `.specify/memory/constitution.md` is what every stage after it
treats as the authority, so `make check-constitution` fails the build when that file stops carrying minimum
CD, the practices the skills in `skills/` teach, or the obligations this project's capabilities claim — and
`.specify/extensions.yml` hooks `/speckit-constitution` on both sides so the drafting session sees the
required coverage before writing and the check runs immediately after. `/constitution-coverage` prints the
normative text at any time. Until that stage has been started the gate stands aside: `./init` installs the
template, and the untouched template passes, so the walking skeleton reaches `main` — and production, where
there is a target — before the first principle is written. It applies from the first edit, and from the first
feature under `specs/` whether or not the constitution was touched.

Three stages in the loop are deliberately not the shape they look like. **Converge** is append-only — its
only write is new tasks — so it is safe to repeat until it reports converged or reaches its bound, and it is what makes the demo
worth showing. The **second `/gaps`** runs after that verdict rather than before it, because ahead of
converge every unbuilt task reads as a gap and buries the findings that need judgement. **`/adversary`** is
an end-of-phase pass rather than a per-slice one: `commands/adversary.md` runs it when the diff changed
attack surface and at the close of the split regardless, and records the decision either way in
`specs/<feature>/adversary-log.md` — which is what lets a later slice decline on evidence instead of
judgement. The trigger table is in that row before any spawn. `/mutation` still runs on every accepted slice, and when both run adversary goes first, since it
adds tests and mutation measures whatever exists when it runs.

`/drive` owns resumption and sequencing, and is safe to call at any point on this diagram: it enters at the
first stage still owing an artifact, stepping back out of the loop when an upstream stage has not been done.
Demo feedback returns to the stage that owns the change before the path is demonstrated again. A real product decision is a stop; finishing an intermediate document is
not.

`/cruise` runs this same diagram with nobody at the wheel. A product decision is answered by `drive-skipper`
and written in `specs/<feature>/decisions.md`; the demo is run by `drive-hand` and written in the slice's
`demo-log.md`; the run ends only when the specification is satisfied, or when a person stops it. What each
stage produces does not change. `commands/cruise.md` is exact.
"""


