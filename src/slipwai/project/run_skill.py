"""`skills/run-the-app/SKILL.md`: how to run *this* project, written where an agent will find it."""
from __future__ import annotations

from ..layout import AT_ROOT, Layout
from ..probes import HEALTH_PATH, health_body, ready_path
from ..services import App, first_transport, services_of, web_apps, wrapped_of

# Where an adopted repository writes how each application is run, once somebody has proved it. The repository's
# own file — never in `.written`, never rewritten by `/survey` or `slipwai migrate` — because the first real
# adoption wrote its hard-won run path into the skill itself, which is the factory's and would have been replaced.
RUNNING = "survey/running.md"


def running_ledger(project_name: str, apps: list[App]) -> str:
    """`survey/running.md` as `adopt` first writes it: one section per application, nothing yet proven."""
    sections = "\n\n".join(
        f"## `{app.path}` ({app.language})\n\nNot yet proven. Find it the way the existing README, container file or CI "
        "config says, run it once, and replace this paragraph."
        for app in wrapped_of(apps)
    )
    return f"""# Running {project_name}

What is proven about running each application that existed before the delivery method did — the command, the
port, what has to be seeded first, the runtime it actually needs and the ones it cannot run on — written by
whoever proved it, with the date. This file is the repository's own: `slipwai migrate` and `/survey` never
rewrite it, and `skills/run-the-app/SKILL.md` points here. Record what was proven, not what a README promises,
and record the run that failed too: a runtime the gate compiles on and the application cannot load is the kind
of fact that is only ever learned once if it is written down.

{sections}
"""


def one_of(names: list[str]) -> str:
    """`A`, `A or B`, `A, B or C`: a choice, for prose that offers one."""
    quoted = [f"`{name}`" for name in names]
    if len(quoted) == 1:
        return quoted[0]
    return f"{', '.join(quoted[:-1])} or {quoted[-1]}"


def adopted_run_skill(project_name: str, apps: list[App], layout: Layout = AT_ROOT) -> str:
    """The skill for a project none of whose applications the factory made: it cannot say how they start.

    Written as the question it is rather than as a guess — a run path invented here would be a skill that has
    to be verified before it can be followed — and it points at the repository's own file for the answer, since
    this skill is the factory's and is replaced whenever the factory moves.
    """
    listed = "\n".join(f"- `{app.path}` ({app.language})" for app in wrapped_of(apps))
    ledger = layout.under(RUNNING)
    return f"""---
name: run-the-app
description: How to run and demonstrate {project_name}. Use when asked to run, start, demo, or screenshot the app, or when a slice reaches its demo checkpoint. The applications here existed before this method did, so this skill says what is known and where to write the rest.
---

# Running {project_name}

The applications in this repository existed before the delivery method was installed around them, so nothing
here was generated and the factory does not know how any of them starts:

{listed}

`project.json` records, for each, how its own build answers the Make targets (`commands`), and the Makefile
under `layout.delivery` runs those. How to *run* one — the command, the port, what has to be seeded first, the
runtime it needs — is written in **`{ledger}`**, and that file is the whole of this skill: read it first. Where
it still says *not yet proven*, find the run path the way the existing README, container file or CI config
says, prove it once, and write it there — never here. This file is listed in `.written`: the factory's own,
replaced by `slipwai migrate`, and anything written into it is lost with the next version. The demo a slice
ends with is what the ledger exists for, and a run path that has to be rediscovered at the demo is the same
cost as having none.
"""


def run_skill(project_name: str, apps: list[App], layout: Layout = AT_ROOT) -> str:
    """How to run *this* project, written down where an agent will find it.

    Generated rather than shipped as a static skill because every line of it is project-specific: which
    command starts the service, whether there is a browser app at all, what has to be seeded first. A
    generic version would be a skill that has to be verified before it can be followed, which is the same
    cost as not having one — and the cost lands at the demo, when the loop is waiting on it.
    """
    transport = first_transport(apps)
    browsers = web_apps(apps)
    web = bool(browsers)
    browser = browsers[0] if browsers else None
    web_path = browser.path if browser else "apps/web"
    # The services that can be started: the ones with a transport. A service without one has no entry
    # point yet and is not in this skill's tables, so its presence never promises a demo it cannot give.
    services = [service for service in services_of(apps) if service.transport is not None]
    stores = list(
        dict.fromkeys(
            s.selection.option("event-store") for s in services_of(apps) if "event-store" in s.selection.axes
        )
    )
    several = len(services) > 1
    if not services_of(apps) and not web:
        return adopted_run_skill(project_name, apps, layout)
    first = services[0] if services else services_of(apps)[0]
    service_url = f"http://localhost:{first.port}"
    web_url = f"http://localhost:{browser.port}" if browser else ""

    if transport is None and not web:
        surface = """This project has no inbound HTTP transport and no browser app, so there is nothing to start
yet: its entry point is whatever the first slice makes it — a CLI, a worker, a queue consumer. Decide that
before promising a demo, and until then demonstrate through the acceptance tests, which run the same use
cases the eventual entry point will call.

Add a transport later with `./init --http <option>` if the project should serve HTTP after all;
`scripts/backing-services.py --list` shows what this project can still be given."""
        return f"""---
name: run-the-app
description: How to run and demonstrate {project_name}. Use when asked to run, start, demo, or screenshot the app, or when a slice reaches its demo checkpoint. This project has no HTTP transport or browser app yet, and this skill says what to demonstrate instead.
---

# Running {project_name}

{surface}
"""

    paths: list[str] = []
    if transport is not None:
        for service in services:
            what = f"`{service.name}`" if several else "The service"
            paths.append(
                f"| `make {service.dev_target}` | {what} alone, in the foreground, on "
                f"http://localhost:{service.port} | The API loop: edit, restart, curl |"
            )
    for app in browsers:
        api = app.api_service(apps)
        what = f"`{app.name}`" if len(browsers) > 1 else "The browser app"
        paths.append(
            f"| `make {app.dev_target}` | {what}, in the foreground, on http://localhost:{app.port}"
            f"{(f', proxying `/api` to `make {api.dev_target}`' if api is not None else '')} | The UI loop: edit, "
            "save, the page reloads |"
        )
    paths.append(
        "| `make demo` | Everything, in containers, waited on until it answers, addresses printed | "
        "Showing it to somebody — including yourself |"
    )
    path_table = "\n".join(paths)

    foreground = []
    if transport is not None:
        foreground += [f"make {service.dev_target:<10} # leave it running" for service in services]
    foreground += [f"make {app.dev_target:<10} # in another terminal" for app in browsers]
    foreground_block = "\n".join(foreground)
    # The first thing this project can be started with, named rather than described, so the warning about
    # leaving it running points at a real command. The no-transport-no-web case returned above.
    first_command = f"make {first.dev_target}" if transport is not None else f"make {browsers[0].dev_target}"

    seeds = {
        "postgres": """This project's event store is Postgres, which needs its container running and its migrations
applied before it can hold anything:

```sh
make services-up   # starts Postgres, waits for it to accept connections
make migrate       # applies the event-store migrations
```

`make demo` starts Postgres too, but it does **not** migrate — that is a write to a database and stays an
explicit act. Run `make migrate` once after the first `make demo`, and again whenever a migration is added.""",
        "sqlite": """This project's event store is a SQLite file, created by the process that opens it, so
there is nothing to start and nothing to migrate. The log is at `EVENT_STORE_PATH` (see `.env.example`) and
is git-ignored: deleting it deletes the entire truth of the system, which on a demo is usually what you
want between runs.""",
        "memory": """This project's event store is in memory, so every restart is a fresh world. Nothing to
start, nothing to migrate, and nothing to clean up — but also nothing to come back to: seed whatever the
demo needs through the app itself, in front of whoever is watching if the seeding is part of the story.""",
    }
    # One paragraph per distinct store the services use; two services on the same store say it once.
    seed = "\n\n".join(seeds[store] for store in stores if store in seeds)

    proxy_check = f"""
The dev server forwards `/api/*` to the service with the prefix intact, so a slice's route is the same path
on both sides. That also makes one command prove the wiring end to end before any route exists:

```sh
curl -s {web_url}/api{HEALTH_PATH}     # {{"error":"notFound"}} — from the *service*, so the proxy is working
```

HTML back instead means the request never left the dev server. `{HEALTH_PATH}` is deliberately outside `/api`: it
is a probe for whatever runs the process, not API surface, so ask the service for it directly.
""" if web else ""

    # Several services listen on several ports, and the environment variable that moves each one is the
    # fact worth having in front of you before a demo, not after a `connection refused`.
    ports = "".join(
        f"- `{service.name}` on http://localhost:{service.port} — `make {service.dev_target}` in the foreground; "
        f"`{service.port_variable}` in `.env` moves the port `make demo` publishes\n"
        for service in services
    )
    several_services = f"""
## Several services

This project has {len(services)} services, each on its own port and each answering the same probe:

{ports}
`make demo` starts them all. In the foreground each one is its own terminal, and `PORT` applies to whichever
you start — the targets above set each service's own port as the default.
""" if several else ""
    where = (
        "the service it belongs to (" + ", ".join(f"`{service.path}`" for service in services) + ")"
        if several
        else f"`{services[0].path}`" if services else "the service"
    )
    # Two lines where the two probes are two paths, one where the backend's framework serves a readiness
    # endpoint of its own and this project points `/health` at it. `/ready` asks the event-store port a
    # trivial question, so it is the line that says whether the store is reachable from here.
    probes = ""
    for service in services:
        probes += (
            f"curl -s http://localhost:{service.port}{HEALTH_PATH}     # {health_body(service.backend)}"
            f" — liveness\n"
        )
        if ready_path(service.backend) != HEALTH_PATH:
            probes += (
                f'curl -s http://localhost:{service.port}{ready_path(service.backend)}      '
                f'# {{"status":"ready"}} — readiness, which asks the event store\n'
            )
    serves = f"""## What it serves right now

Until a slice adds a route, {"each service" if several else "the service"} answers its probes and nothing else:

```sh
{probes}curl -s {service_url}/anything   # {{"error":"notFound"}}, with the path deliberately not echoed back
```

Do not go looking for more. A slice adds its route in {where}{(" and its screen in `" + web_path + "`" if web else "")}, and the
404 shape above is the contract everything unmatched keeps.
{proxy_check}{several_services}""" if transport is not None else """## What it serves right now

There is no HTTP transport in this project, so the browser app has nothing to proxy to yet: it runs
and renders, and every `/api` call it makes will fail until a transport is added with `./init --http
<option>`.
"""

    driving = """## Driving it to show something

Reach for the cheapest thing that proves the claim, in this order:

1. **`curl`** for anything the API decides. A status code and a body are the whole claim, and `curl` shows
   both without a browser in the way.
2. **`make test`** for anything a screen renders. A browser app's component tests drive the real component
   with a real user event and no browser at all — see the `react-testing` and `front-end-testing` skills.
3. **A real browser** only when the claim is about the two together: the app calling the service and
   rendering what came back. That is the one thing the levels above cannot prove.

For step 3, Playwright is deliberately **not** a dependency of this project — a browser binary in every
checkout is a cost every contributor pays for something few of them run. Install it when you need it:

```sh
npx --yes playwright install --with-deps chromium   # downloads a browser; --with-deps needs root
npx --yes playwright open {web_url}     # or drive it from a script
```

`skills/front-end-testing/resources/playwright-e2e.md` covers what a browser-level test may and may not
claim before you write one. If browser-level tests become part of the suite rather than a one-off, add
Playwright to `{web_path}` as a devDependency deliberately, in the same commit as the lockfile change, rather
than leaving every future run to `npx`.
""" if web else """## Driving it to show something

`curl` is the whole toolkit here: this project has no browser app, so a status code and a body are the
claim. Show the request and the response, not a description of them.
"""

    # The one failure whose symptom points away from its cause: everything reports healthy, so the search
    # goes to the proxy, the port, the firewall — anywhere but the address the server bound. Named here
    # because the machine this happens on is usually not the one the reader is picturing.
    remote_host = """- **It comes up, but only the machine running it can reach it.** The dev server binds loopback by
  default — right when the browser is on that machine, wrong when it is not: a container, a VM, a remote
  sandbox. Publishing or forwarding the port does not help, because loopback is the boundary it is on the
  far side of. Start it with `make dev-web WEB_HOST=0.0.0.0` and forward the port to that. `make demo`
  already does this for its own `web` container, which is why the container path never needs it.
""" if web else ""
    # Every port that can be moved, so a taken port is named with the variable that moves it.
    port_variables = one_of([app.port_variable for app in [*services, *browsers]])
    trouble = f"""## When it does not come up

- **`make demo` fails at `--wait`.** Something is unhealthy rather than missing. `docker compose --profile
  app logs service` (or `web`) is the answer; the first run installs dependencies inside the container and
  is slow, later runs are not.
- **A port is already taken.** The addresses are pinned rather than negotiated, so that a printed one is
  always the right one. Move a published port in `.env`, which Compose reads, by setting
  {port_variables} — never by letting a dev server pick its own and quietly invalidate every URL
  you wrote down.
- **The browser app loads but every call 404s.** The dev server proxies `/api` only. Fetch relative paths —
  `/api/...` — never an absolute `http://localhost:{first.port}/...`, which goes straight past the proxy
  and pays a CORS preflight it will fail.
{remote_host}- **Dependencies look installed but are not.** The containers keep theirs in their own volumes, on purpose:
  a Linux container's `node_modules` in your working tree is how a passing `make verify` starts failing.
  `make demo-down` and `make demo` again rebuilds them.
"""

    return f"""---
name: run-the-app
description: Start, reach and drive {project_name} — the foreground path (`make dev`), the container path (`make demo`), the addresses each one serves on, what has to be seeded first, and how far to go before opening a browser. Use when asked to run, start, demo, or screenshot the app, when a slice reaches its demo checkpoint, or when a change has to be seen working rather than only proved by tests.
---

# Running {project_name}

| Command | Starts | Use it for |
|---|---|---|
{path_table}

`make demo` runs the very same `make dev` inside a container over this checkout, so the two paths cannot
disagree about how this project starts. Nothing is built into an image: an edit is live, and there is no
Dockerfile to fall behind the code.

```sh
{foreground_block}
```

## Before a demo, not during one

{seed}

{serves}
{driving}
{trouble}
## What to hand over

`commands/drive.md` sets the shape of a demo stop, and it is not a summary. It opens with the progress
board — ✅ what works now, 🆕 what this slice added, ⬜ what is still to come with the slices counted, ⚠️ what
is not working yet, ➡️ what comes next — and ends with the literal command or URL, the seed data, the result
to expect in the actor's own words, and a direct question about what using it revealed. This skill exists
so that the command is a line you can paste rather than a thing you have to work out again.

**Everything in the table above starts a process that has to still be running when the turn ends.** Start
it, check it answers, and leave it up — in the background, not in a shell you then close. Starting `{first_command}`
to prove the command works and stopping it once the proof lands is a test you ran alone: the actor's first
action is opening what you just closed, and a dead port is what they find. Say plainly that it is still
running, and on which address.
"""
