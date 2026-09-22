"""`README.md` and `project.json`: what this project is, how to start it, and what it was given.

The README is the one generated file a person reads before anything else, so it answers in order: what
this is, how to start it, how to *run* it, and what each axis was answered with. `project.json` records the
same answers for a tool to read.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..services import App, described, frontend_of, services_of, web_apps
from ..targets import managed
from .backing_service_prose import backing_services_readme
from .event_model import event_model_page_url
from .existing import EXISTING_README
from .rules import CLOUD
from .target_docs import PREREQUISITES, WORDS


def readme(project_name: str, profile: str, apps: list[App], target: str = "none") -> str:
    event = profile == "event-modelling"
    frontend = frontend_of(apps)
    title = project_name.replace("-", " ").replace("_", " ").title()
    capabilities = CATALOG["profiles"][profile]["capabilities"]
    frontend_capabilities = CATALOG["frontends"][frontend]["capabilities"]
    services = services_of(apps)
    web = web_apps(apps)
    listed = "; ".join(f"`{service.backend}` in `{service.path}`" for service in services)
    web_listed = ", ".join(f"`{app.path}`" for app in web)
    text = f"""# {title}

This is an independently evolvable product monorepo scaffolded by `slipwai`. Which version scaffolded it, and which version last wrote a file here, are both recorded in `project.json`'s `generator` — the one place either number lives, so a replay cannot leave this page claiming the other. The factory's own `CHANGELOG.md`, read against that pair, says what later versions bring and what a repository already generated owes to catch up.

- Project: `{project_name}`
- Profile: `{profile}`
- Production target: `{target}`
- Services: {listed}
- Frontend: `{frontend}`{(" in " + web_listed if web else "")}
- Backend capabilities: {", ".join(capabilities)}
- Frontend capabilities: {", ".join(frontend_capabilities) if frontend_capabilities else "none"}
{selection_summary(services)}
{before_init(target)}
## Start here

```sh
./init{start_here_production(target)}
make verify
```

`./init` installs Spec Kit for the selected agent; it is not vendored in this repository.{init_production(target)} `make verify` is
the repository's local and CI quality gate. Add one small vertical slice at a time and keep the main branch
releasable.

{services_readme(services, web)}{running_readme(services, web)}{production_readme(target, services, web)}
## Documentation

[`docs/workflow.md`](docs/workflow.md) diagrams the delivery loop each slice travels, from the constitution
through to the hardening passes. [`docs/getting-started.md`](docs/getting-started.md) walks the first slice
end to end{documentation_production(target)}, and [`docs/README.md`](docs/README.md) indexes every page.
"""
    if not event:
        text += """
## Profile boundary

This standard profile does not adopt Event Modeling or event sourcing. Native Spec Kit cannot
infer that boundary from constitution text you paste: keep the constitution architecture-neutral, or
generate the `event-modelling` profile when those capabilities are intentional. `make verify` rejects a
constitution that mandates event sourcing in this profile.
"""
    if event:
        page_url = event_model_page_url(project_name)
        text += f"""
## Event workflow

Start with `docs/event-model/model.yaml`, name commands and events with domain experts, then implement the
backend event contract and stream identity together in the service the slice belongs to. Event Modeling may
cover the whole user journey, but event sourcing is a backend persistence choice. This profile deliberately
cannot be generated with Event Modeling or event sourcing alone.

### One command runs the loop: `/drive`

```text
/drive          # start the loop, or resume the slice already in flight
/drive S2       # drive a named slice to its demo
```

`/drive` enters at the first incomplete stage proven by durable artifacts, and its ladder starts above the
slice loop: principles, product specification, the event model, the split, then example map, a `/gaps` pass
over it, the installed Spec Kit plan and tasks, implementation, convergence, and the actor-visible demo. Invoking it before the model exists is
a valid start rather than an error — it steps back to the stage that owes an artifact and says so. It never
reruns a completed stage merely to check. It pauses at the demo before hardening so feedback can return to the stage that owns it. Once the
demo is accepted, it runs the mutation pass — plus the adversarial pass when the slice changed attack
surface or closed the split — verifies and archives the slice, and starts the next ready slice without
another invocation. A real product question or unavailable external input is
the other stopping boundary.

`/cruise` runs the same ladder with nobody at the wheel — deciding as the owner, demoing as the actor, recording
both under `specs/` — until the specification is satisfied. It ships switched off: `/cruise-settings enabled=true`,
then `make cruise`; `touch .specify/cruise.stop` stops it. `commands/cruise.md` is exact.

### The browsable model

The event-model workflow renders `docs/event-model/model.yaml` into a zoomable timeline with per-slice
views and embedded wireframe mockups, and publishes it on every push to `main` that touches the model.
Your forge's pages host serves it from the `pages` branch at:

{page_url}

On GitHub the same workflow deploys through GitHub Pages instead; when that URL differs, update
`render.page` in `model.yaml` and the link below. Regenerate locally with `make model` (needs Node).

<!-- event-model:start -->
_Run `make model` after the first modelling session to generate this section._
<!-- event-model:end -->
"""
    text += backing_services_readme(apps)
    return text


def services_readme(services: list[App], web: list[App]) -> str:
    """The README's account of `apps/`: one directory per service, what each owes, and how to add one."""
    if not services:
        return """## Services

No service here was made by the factory. The applications this repository already had are recorded in
`project.json` as `"generated": false`, each with how its own build answers the Make targets; `apps/` is
where a service the factory adds would go, with the factory that installed this method:

```sh
path/to/slipwai/slipwai add-service <name> --language python  # the language is required: nothing here to inherit
```
"""
    listed = ", ".join(described(service) for service in services)
    browser = (
        " " + ", ".join(f"`{app.path}`" for app in web)
        + (" are the browser apps, which are" if len(web) > 1 else " is the browser app, which is")
        + " not a service and owe" + ("" if len(web) > 1 else "s") + " none of this."
    ) if web else ""
    return f"""## Services

`apps/` holds one directory per service: {listed}.{browser} Each service has its own language,
framework and backing-service answers, recorded in `project.json`; every one owes the same eight Make
targets (`make help` lists them; every recipe runs for every service), answers a liveness and a readiness
probe on its own port,
and keeps the hexagonal layout `make check-imports` enforces. Which services exist is recorded once, in
`project.json`'s `deployables`; the Makefile, `docker-compose.yml`, the CI workflow,
`scripts/check-imports.py` and `scripts/backing-services.py` read that list, and none keeps a copy.

Add one with the factory that generated this repository, from this directory:

```sh
path/to/slipwai/slipwai add-service <name>                  # the first service's language and answers
path/to/slipwai/slipwai add-service <name> --language python  # another language, its own answers
```

It scaffolds `apps/<name>` with the walking skeleton, adapters and tests a service of that language starts
with, on the next free port, registers it in `project.json`, and regenerates the files that list drives —
the skills' example snippets included, so a second language shows up beside the first at every example.
Say what the service is for while adding it — `--purpose "<what it owns>"` and `--context <bounded
context>`, repeated for each context it holds — because that is what the delivery loop reads when it decides
which service a slice belongs to; `docs/architecture.md` has the contexts as recorded, and says when a
context inside a service should become a service of its own.
`add-frontend <name> [--api <service>]` does the same for a browser app, proxying `/api` to the service it
names. Code shared between services goes under `packages/`, and the hexagonal rule applies inside it too;
`docs/architecture.md` says what a shared package is in each language and what each service owes.
"""


def selection_summary(services: list[App]) -> str:
    """The axes as the README lists them: the question, and the answer each service was given.

    Only the axes that were actually asked appear. An axis a profile or backend cannot be given is not a
    line reading "none" — it is not a question this project has. One list while every service answered the
    same way; one list per service once they differ.
    """
    summaries = [service.selection.summary for service in services]
    if not any(summaries):
        return ""
    if all(summary == summaries[0] for summary in summaries):
        return "".join(
            f"- {CATALOG['axes'][axis]['prompt']}: `{answer}`\n" for axis, answer in summaries[0].items()
        )
    text = ""
    for service, summary in zip(services, summaries, strict=True):
        text += f"- `{service.name}`:\n" + "".join(
            f"  - {CATALOG['axes'][axis]['prompt']}: `{answer}`\n" for axis, answer in summary.items()
        )
    return text


def before_init(target: str) -> str:
    """Everything `./init` will need, listed before the command a reader runs first — because in a project
    going to production, `./init` pushes the repository and applies to an account, and finding out what it
    wanted halfway through is the worst moment to."""
    if not managed(CATALOG, target):
        return """## Before `./init`

`./init` installs Spec Kit for the agent you choose. It needs **Python 3**, and **`uv`** or network access
for `pip`. Nothing else has to be set up first.
"""
    # The cloud's own rows land in the middle, so the numbering either side of them is counted rather than
    # written: a target that asks for one more tool moves every row below it, and the sentence under the
    # table names the range it checks.
    cloud_rows = PREREQUISITES[target]
    rows = "\n".join(
        f"| {number} | {have} | {proof} |" for number, (have, proof) in enumerate(cloud_rows, start=2)
    )
    last_checked = len(cloud_rows) + 2
    return f"""## Before `./init`

In this project `./init` does the first day's work: it installs Spec Kit, pushes this repository to your
forge, and runs `make bootstrap` against your {CLOUD[target]} account — so the push is the first deploy. Have every row
below ready on the machine that runs it. It checks, and stops before pushing if something is missing, but
knowing first is quicker.

| | Have | Proof it is there |
|---|---|---|
| 1 | **Python 3**, and **`uv`** or network access for `pip` — Spec Kit is installed with one of them | `uv --version` |
{rows}
| {last_checked} | **Access to your forge.** GitHub: `gh` signed in (`gh auth login`). Gitea: `GITEA_TOKEN` set to a token with `read:user` and `write:repository` — plus `write:organization` if the repository will belong to an organisation | `gh auth status` · `echo ${{GITEA_TOKEN:+set}}` |
| {last_checked + 1} | **The repository's URL** — `https://github.com/<owner>/<name>`, `http://localhost:3300/<owner>/<name>` — created on the forge if it does not exist | — |
| {last_checked + 2} | **Somewhere to keep a passphrase.** `make bootstrap` prints one, once; it encrypts the committed bootstrap state and every later `make bootstrap` needs it | a password manager |

Whether rows 2–{last_checked} are on the machine is checked when the project is generated, too; who the CLI is signed
in as, `make bootstrap` checks before it applies anything. Missing a tool, `./init` still installs Spec Kit,
says which and leaves the push and bootstrap for later — `./init --repository <url>`, or push and
`make bootstrap`. `./init --skip-bootstrap` leaves them deliberately. Once the bootstrap has run, a later
`./init` — to answer an axis again, add an extension, or switch agent — sees its committed state and leaves
the account alone; re-applying the stack is `make bootstrap`, by hand.

`make bootstrap` also asks the one question that decides the bill: whether production is deployed on every
green push, or only when you say so. Answer `n` — or `./init --auto-promote false` — and the pipeline deploys
staging alone, production is never created, and `make promote` is what creates it when you want it. Either
way an environment costs money from the moment it exists;
[`docs/adr/0002-production-target.md`](docs/adr/0002-production-target.md) says how much.
"""


def documentation_production(target: str) -> str:
    """The deployment drawing, named where a reader looks for documentation and not only mid-paragraph
    under *Production* — it is the page people go looking for and did not find."""
    if target == "existing":
        return ", [`docs/deployment.md`](docs/deployment.md) records where this runs and how a release reaches it"
    if not managed(CATALOG, target):
        return ""
    return (
        f", [`docs/deployment.md`](docs/deployment.md) draws what runs in {CLOUD[target]} for this project's "
        f"services and how a commit gets there"
    )


def init_production(target: str) -> str:
    if not managed(CATALOG, target):
        return ""
    return (
        " In this project it then asks for the repository to push to — created on the forge if it is not there"
        " — pushes, and runs `make bootstrap`, so the push is the first deploy; `./init --repository <url>`"
        " answers ahead, `--skip-bootstrap` leaves it for later."
    )


def start_here_production(target: str) -> str:
    """The two lines that make the first commit a path to production, in the block a reader runs first."""
    if not managed(CATALOG, target):
        return ""
    return (
        f"    # then asks where to push, pushes, and runs `make bootstrap`: once, with admin "
        f"{CLOUD[target]} credentials"
    )


def production_readme(target: str, services: list[App], web: list[App]) -> str:
    """The README's account of where this project goes to production, for a project that goes anywhere."""
    if target == "existing":
        return EXISTING_README
    if not managed(CATALOG, target):
        return ""
    words = WORDS[target]
    site = words["site"] if web else ""
    return f"""
## Production

This project deploys to {CLOUD[target]}, and the pipeline is the way it gets there: every commit that passes `verify` on
`main` runs `.github/workflows/deploy.yml`, which builds one image per service with the ecosystem's own
builder, pushes each by digest, applies `staging`, proves it with `make smoke`, applies `production` and
proves that. It starts when `verify` completes, and only if it passed — never beside it or ahead of it.{site}

Whether that last step runs is the `AUTO_PROMOTE` variable `make bootstrap` wrote to the forge. `true`,
the default, is the pipeline just described. `false` stops it at staging: production is deployed by
`.github/workflows/production.yml` instead, started by `make promote` or from the Actions tab, with the
commit staging is running — and without auto-promotion that first promotion is also what creates
production, so a project pays for one environment until it wants two. Either way production is only ever given the images
staging has already run, and the apply happens on the runner with the deploy role, never on a laptop.
`make bootstrap AUTO_PROMOTE=true` changes this project's mind, in either direction.

When a release is wrong, `.github/workflows/rollback.yml` is started by hand from the Actions tab with the
environment to roll back; it re-applies the release before the current one and proves it the same way.
`infra/` is the whole of the infrastructure — OpenTofu, {words["runtime"]} — [`docs/deployment.md`](docs/deployment.md) draws it for this project's services, and
[`docs/adr/0002-production-target.md`](docs/adr/0002-production-target.md) is why each part is what it is, with what it costs.

```sh
make build smoke-image PLATFORM=linux/arm64   # every service's image, run locally and asked its probe
make deploy ENV=staging                        # what the pipeline does, from a laptop with credentials
make smoke URL=$(make -s url ENV=staging)     # what proves a deploy
make promote                                   # ask the forge to deploy production with what staging runs
make rollback ENV=staging                      # what the rollback workflow does, from a laptop
```

`make bootstrap` is the one thing a person does, once, with administrator credentials the `aws` CLI can
find — `./init` runs it after asking where to push. It applies `infra/bootstrap` — the state bucket, the pipeline's identity, the image repositories — and
configures the repository on the forge from the outputs (variables; and, on a forge without OIDC such as
Gitea, the two secrets of a key that can only assume the deploy role). Run it again after `add-service`.
[`infra/README.md`](infra/README.md) says what it decides and how. `make ci` builds every image and proves
it answers, which is the half of a deploy that can be proved without an account; `tofu validate` is what the
gate holds the stacks to.
"""


def running_readme(services: list[App], web: list[App]) -> str:
    """The README's answer to "how do I see it?".

    Directly after "Start here", because a starter whose only verb is `make verify` teaches that the way to
    know something works is to run its tests — and the demo a slice is supposed to end with then has to be
    invented from scratch by whoever reaches one first.
    """
    served = [service for service in services if service.transport is not None]
    if not served and not web:
        return ""
    lines: list[str] = []
    for service in served:
        lines.append(
            f"make {service.dev_target:<10} # {service.name} alone, in the foreground on "
            f"http://localhost:{service.port}"
        )
    for app in web:
        what = "the browser app" if len(web) == 1 else app.name
        lines.append(f"make {app.dev_target:<10} # {what}, in the foreground on http://localhost:{app.port}")
    lines.append("make demo       # or the whole thing in containers, addresses printed when it answers")
    commands = "\n".join(lines)
    return f"""
## Run it

```sh
{commands}
```

`make demo` runs that same `make dev` inside a container over this checkout, so the two paths cannot
disagree about how this project starts, and there is no image to rebuild between an edit and a demo.
`skills/run-the-app/SKILL.md` is the full account: what it serves today, what has to be seeded first, and
how far to go before opening a browser.
"""
