"""The commands about the factory that made this project: `add-service`, `add-frontend`, `catch-up`.

Split from `commands.py` for the reason `native_commands.py` is split from `makefile.py` — that module is at
its budget — and because these are a different kind of command. The others drive a slice through the
project's own workflow; these are about the relationship with the factory. An agent asked for "a payments
service" and given no command will copy `apps/service` by hand and edit the nine files that name it, which
is the state `add-service` exists to end; the command is where it learns that the factory does this, what
has to be decided first, and what to check afterwards.

`catch-up` is the third and at the other end. A migration merges the factory's newer output, and the work
left over is code the factory has never seen being held to a rule that did not exist when it was written.
Left uncommanded that becomes "make verify is red, so change whatever makes it green" — which, faced with a
factory-owned gate script, is exactly the wrong repair. Unlike the other two it runs no factory command:
`slipwai migrate` writes what the versions crossed ask for into the project before it returns, and this reads
it there. One command to run, not two — the second is the one that would be forgotten, because a merge is
visible in `git status` and an obligation is not.

The first two name the project's current applications, so they change when one is added — which means
`add-service` regenerates them, and the file an agent reads always lists what is there now.
"""
from __future__ import annotations

from ..catalog import CATALOG, families
from ..services import App, contexts_phrase, services_of, web_apps
from ..toolkit import example_of

# The command is the factory's, not this repository's, and a generated project does not know where its
# factory is: a released executable on the PATH, or a checkout somewhere the user knows.
FACTORY = """## Find the factory

The command belongs to the factory that generated this repository, not to the repository. It is
`slipwai {verb}` where `slipwai` is on the `PATH` — installed with pip, or a released executable — and
`path/to/slipwai/slipwai {verb}` from a checkout. If neither is at hand, ask where the
factory is. {stop}"""

# What a wrong guess at the factory's location must not be allowed to become. Only the two that add an
# application need it: `catch-up` runs no factory command — it reads what `migrate` left in the project.
BY_HAND = """A wrong guess at its location is a stop, not a reason to start copying `{first_path}`: building
the application by hand is the thing this command exists to prevent."""

RUN = """## Run it

1. `git status --porcelain` prints nothing. The command refuses an unclean tree so that `git checkout . &&
   git clean -fd` undoes exactly what it wrote and nothing else; commit or stash first rather than working
   around the refusal.
2. `{invocation}`, from this directory.
3. Read its report: what it added under `apps/<name>`, and which files it regenerated from the list.

## Then

- `git diff` over the regenerated files. A hand edit that came back changed there was made to a file the
  list drives; move it somewhere the generator does not own, then rerun.
- `make verify` — green with the new application before anything else is done to it.
{afterwards}
Nothing is committed by the command. Commit the result as one change, and say what was added and how to
run it."""


def listed(apps: list[App]) -> str:
    """The project's applications, one line each, so the file says what is there now."""
    lines = [
        f"- `{app.name}` — {app.backend}, port {app.port}; {contexts_phrase(app)}"
        + (f" — {app.purpose}" if app.purpose else " — no purpose recorded")
        for app in services_of(apps)
    ]
    lines += [f"- `{app.name}` — browser app on port {app.port}, `/api` to `{app.api}`" for app in web_apps(apps)]
    return "\n".join(lines)


# What adding a service means for a project with a destination: one more image, one more ECS service, and a
# repository the bootstrap stack has to create first. Said in the command because the report says it once and
# the agent reads the command every time.
PRODUCTION_AFTERWARDS = {
    "aws": """- This project deploys to AWS, and `infra/` was regenerated with the new service: its image repository is the
  bootstrap stack's, so `make bootstrap` has to run once more — by a person with the administrator
  credentials it needs — before the pipeline can push its image; the ECS service itself arrives with the
  next `make deploy`. Say so when handing over. `docs/deployment.md` was redrawn with the new service;
  `docs/adr/0002-production-target.md` is the design.
""",
    # Nothing to bootstrap here, and that difference is worth stating rather than leaving as a silence: a
    # container registry holds every repository it is pushed and creates them on first push, so unlike ECR
    # there is nothing per service for the bootstrap stack to create.
    "azure": """- This project deploys to Azure, and `infra/` was regenerated with the new service: its Container App
  arrives with the next `make deploy`, and there is nothing to bootstrap — one registry holds every
  service's images and creates a repository the first time one is pushed. `docs/deployment.md` was redrawn
  with the new service; `docs/adr/0002-production-target.md` is the design.
""",
}

WEB_PRODUCTION_AFTERWARDS = {
    "aws": """- This project deploys to AWS: `infra/service/frontend.tf` was regenerated to put the site behind CloudFront
  with `/api` routed to the service it names, and `make deploy` uploads the bundle. Nothing to apply by hand.
""",
    "azure": """- This project deploys to Azure: `infra/service/frontend.tf` was regenerated to serve the site from a
  static web app with the service it names linked as its API backend, so `/api` reaches that service by the
  product's own rule, and `make deploy` uploads the bundle. Nothing to apply by hand. One consequence worth
  saying when handing over: a linked service answers only through the site, so that service no longer has a
  public address of its own in `urls`.
""",
}


def add_service_command(apps: list[App], target: str = "none") -> str:
    services = services_of(apps)
    example_name, example_path = example_of(apps)
    default_language = (
        f"without `--language` the new service is `{services[0].backend}`, like `{services[0].name}`."
        if services
        else "this project has no service the factory made to take a language from, so `--language` is required."
    )
    inherits = (
        f"inherits `{services[0].name}`'s answer where the new backend offers it, and takes that\n  backend's own "
        "default where it cannot (a transport is per framework)."
        if services
        else "takes the backend's own default."
    )
    axes = ", ".join(f"`--{axis}`" for axis in CATALOG["axes"])
    frameworks = sorted(
        {backend["framework"] for backend in CATALOG["backends"].values() if backend.get("framework")}
    )
    languages = "|".join(families())
    return f"""---
description: Add a service to this project with the factory's add-service, and leave it green
argument-hint: <name> --purpose "<what it owns>" [--context <name>]... [--language <language>] [--framework <framework>] [--<axis> <answer>]
---

# Add service

A service is a change to the list in `project.json` and a regeneration of everything that reads it — the
Makefile, Compose, CI, the workspace, `scripts/verify`, the prose that lists the services. The factory's
`add-service` makes both. Nothing here is copied from `{example_path}` by hand: a copy has to find the nine
files that name it, and misses the tenth.

## What is here

{listed(apps)}

## Decide with the user, not for them

- **Name** — `apps/<name>` and its Compose service: lowercase letters, digits and hyphens, and none of the
  names above.
- **Language and framework** — {default_language}
  Another language beside it is
  `--language {languages}`; a language with more than one framework also takes
  `--framework {"|".join(frameworks)}`.
- **Answers** — one flag per question: {axes}.
  An axis without a flag {inherits} `add-service --help` lists the
  options this project's target allows.
- **Purpose and contexts** — `--purpose "<what it owns, in a sentence or two>"` and `--context <name>`, once
  per bounded context the service holds. The purpose is what `/drive` reads when it decides which service a
  slice belongs to: a service added without one is a directory the loop cannot place work in, and it will
  stop to ask before it does. A context is one already on the list above, or a new one; without any the
  service is a context of its own. A context may span several services; the tree stays `apps/<name>`.
  A service already listed is described after the fact: `<factory> describe-service <name> --purpose "..." --context <name>`.

The language, the store, and what the service owns are product decisions. When the request does not name
them, ask; taking `{example_name}`'s answers is the default for the first two, and saying so is part of
asking. Someone asking for a service has a reason for wanting it separate — the purpose is that reason,
written down. The port is the command's own decision — the next one free — and is not asked.

## Is a service the right shape?

A new bounded context is not by itself a reason for a new service. This project starts as one service that
may hold several contexts as `src/<context>/`, each behind its own `public` module, with `make check-imports`
keeping them apart — and that is where a context whose boundary is still being found belongs. A service is
the right shape when there is a *deployment* reason: its own release cadence, its own scaling or runtime, a
data store of its own, another team, another language. When the request is "a context for X" rather than
one of those, say so, and offer to add `X` to `{example_name}`'s `contexts` in `project.json` instead —
`docs/architecture.md`, *Bounded contexts*, has the three rungs and the reasoning to point at.

{FACTORY.format(verb="add-service", stop=BY_HAND.format(first_path=example_path))}

{RUN.format(
    invocation='<factory> add-service <name> --purpose "<what it owns>" [--context <name>] [--language <language>] [--<axis> <answer>]',
    afterwards='''- Say how it runs: `make dev-<name>` in the foreground, `make demo` with the rest, and its port from the
  report. Its health example is the placeholder the first slice replaces; `/drive` from there.
- It shares the local backing services with every other service — one `DATABASE_URL`, one database. That is
  right for a walking skeleton and wrong for a product: give it its own database or schema before it owns
  any data, and say so when handing it over.
''' + PRODUCTION_AFTERWARDS.get(target, ""),
)}
"""


def add_frontend_command(apps: list[App], target: str = "none") -> str:
    services = services_of(apps)
    _, example_path = example_of(apps)
    default_api = (
        f"Without it, `{services[0].name}`."
        if services
        else "This project has no service the factory made, so `--api` has to name one — `/add-service` first."
    )
    present = "" if web_apps(apps) else "\n\nNo browser app yet; this command adds the first."
    return f"""---
description: Add a browser app to this project with the factory's add-frontend, and leave it green
argument-hint: <name> [--api <service>]
---

# Add frontend

A browser app is a change to the list in `project.json` and a regeneration of everything that reads it —
the npm workspace and lock, the Makefile, Compose, `.gitignore`, the agent settings, the prose that lists
the applications. The factory's `add-frontend` makes both. Nothing here is copied from another `apps/`
directory by hand.

## What is here

{listed(apps)}{present}

## Decide with the user, not for them

- **Name** — `apps/<name>` and its Compose service: lowercase letters, digits and hyphens, and none of the
  names above.
- **Which service** — `--api <service>` names the service its `/api` calls are proxied to, by the Vite dev
  server in the foreground and by `API_ORIGIN` inside Compose. {default_api} A browser app
  talks to one service through that boundary and never reads a store directly.

The framework is not a question: every browser app is the one the project was generated with, and the
dev-server port is the command's own decision — the next one free.

{FACTORY.format(verb="add-frontend", stop=BY_HAND.format(first_path=example_path))}

{RUN.format(
    invocation="<factory> add-frontend <name> [--api <service>]",
    afterwards='''- Say how it runs: `make dev-<name>` in the foreground — with `WEB_HOST=0.0.0.0` when the browser is not on
  this machine — `make demo` with the rest, and its port from the report. Its page is the placeholder the
  first slice replaces; `/drive` from there.
''' + WEB_PRODUCTION_AFTERWARDS.get(target, ""),
)}
"""


def add_command_files(apps: list[App], target: str = "none") -> dict[str, str]:
    """The commands that run the factory from inside the project: two that grow it, one that catches it up."""
    return {
        "commands/add-service.md": add_service_command(apps, target),
        "commands/add-frontend.md": add_frontend_command(apps, target),
    }
