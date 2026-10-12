"""`skills/run-the-app/SKILL.md`: how to run *this* project, written where an agent will find it.

Three pages rather than one, because a project with no service the keel made cannot be told how to start one,
and a project with no inbound transport has nothing to start at all. Each is standing text with this project's
own commands, ports and paths substituted, so each is a page under `assets/pages/skills/run-the-app/` and what
is left here is which page, which of its sections, and the closed set of values they may name
(`docs/generated-prose.md`).

The sections are the paragraph test applied to the page a running project gets. *What it serves right now* is
one of two whole sections; the proxy check and the several-services table are whole sections that appear
beside the first of them; *Driving it to show something* is one of two; and the remote-host bullet under *When
it does not come up* is a whole paragraph in the middle of a list. Everything smaller stays here: the table of
start commands, the probe lines, the clause naming where a slice's route goes, the port variables a taken port
is moved with.

The running ledger below is the one piece of prose here that did not move. `adopt` writes it, not `scaffold`,
so the one check that reads a real generation for a marker that survived it (`test_generated.py`) cannot see
the file at all — and an asset nothing proves resolved is the failure that check exists for.
"""
from __future__ import annotations

from ..layout import AT_ROOT, Layout
from ..probes import HEALTH_PATH, health_body, ready_path
from ..services import App, first_transport, services_of, web_apps, wrapped_of
from .prose import page
from .write_model_prose import run_seed

# Where an adopted repository writes how each application is run, once somebody has proved it. The repository's
# own file — never in `.written`, never rewritten by `/survey` or `slipwai migrate` — because the first real
# adoption wrote its hard-won run path into the skill itself, which is the keel's and would have been replaced.
RUNNING = "survey/running.md"
SKILL = "skills/run-the-app/SKILL.md"
ADOPTED = "skills/run-the-app/adopted.md"
NO_TRANSPORT = "skills/run-the-app/no-transport.md"


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


def run_skill(project_name: str, apps: list[App], layout: Layout = AT_ROOT) -> str:
    """How to run *this* project, written down where an agent will find it.

    Rendered rather than shipped as a static skill because every line of it is project-specific: which
    command starts the service, whether there is a browser app at all, what has to be seeded first. A
    generic version would be a skill that has to be verified before it can be followed, which is the same
    cost as not having one — and the cost lands at the demo, when the loop is waiting on it.
    """
    named = values(project_name, apps, layout)
    if not services_of(apps) and not web_apps(apps):
        # A project none of whose applications the keel made: it cannot say how they start, so the page says
        # so as the question it is and points at the repository's own file for the answer.
        return page(ADOPTED, named)
    if first_transport(apps) is None and not web_apps(apps):
        return page(NO_TRANSPORT, named)
    return page(SKILL, named, wanted(apps))


def wanted(apps: list[App]) -> tuple[str, ...]:
    """The sections this project's applications select, in the order the page carries them."""
    web = web_apps(apps)
    services = [service for service in services_of(apps) if service.transport is not None]
    chosen = []
    if first_transport(apps) is not None:
        chosen.append("serves")
        if web:
            chosen.append("proxy-check")
        if len(services) > 1:
            chosen.append("several-services")
    else:
        chosen.append("serves-none")
    chosen.append("driving-browser" if web else "driving-api")
    if web:
        chosen.append("remote-host")
    return tuple(chosen)


def values(project_name: str, apps: list[App], layout: Layout = AT_ROOT) -> dict[str, str]:
    """Every value these three pages may name, and the whole of what they may name."""
    browsers = web_apps(apps)
    browser = browsers[0] if browsers else None
    # The services that can be started: the ones with a transport. A service without one has no entry
    # point yet and is not in this skill's tables, so its presence never promises a demo it cannot give.
    services = [service for service in services_of(apps) if service.transport is not None]
    several = len(services) > 1
    # A browser app beside only adopted services has none to start: `first` and its URL are read only where a
    # transport (so a service in `services`) exists, and the 404 advice below names no port then.
    first = services[0] if services else None
    return {
        "project-name": project_name,
        "applications": "\n".join(f"- `{app.path}` ({app.language})" for app in wrapped_of(apps)),
        "ledger": layout.under(RUNNING),
        "path-table": path_table(services, browsers, apps),
        "foreground": foreground(services, browsers),
        "seed": run_seed(apps),
        "each-service": "each service" if several else "the service",
        "probes": probes(services),
        "service-url": f"http://localhost:{first.port}" if first else "",
        "where": where(services),
        "screen": f" and its screen in `{browser.path}`" if browser else "",
        "web-url": f"http://localhost:{browser.port}" if browser else "",
        "health-path": HEALTH_PATH,
        "service-count": str(len(services)),
        "ports": "".join(
            f"- `{service.name}` on http://localhost:{service.port} — `make {service.dev_target}` in the "
            f"foreground; `{service.port_variable}` in `.env` moves the port `make demo` publishes\n"
            for service in services
        ),
        # Every port that can be moved, so a taken port is named with the variable that moves it. Nothing
        # to move on the two pages that name no port, and those are the two that do not ask for this.
        "port-variables": one_of(movable) if (movable := [app.port_variable for app in
                                                         [*services, *browsers]]) else "",
        "service-port": str(first.port) if first else "<port>",
        # The first thing this project can be started with, named rather than described, so the warning
        # about leaving it running points at a real command.
        "first-command": first_command(first, browsers),
    }


def path_table(services: list[App], browsers: list[App], apps: list[App]) -> str:
    """One row per way this project can be started, and what each row is the loop for."""
    rows = [
        f"| `make {service.dev_target}` | {f'`{service.name}`' if len(services) > 1 else 'The service'} alone,"
        f" in the foreground, on http://localhost:{service.port} | The API loop: edit, restart, curl |"
        for service in services
    ]
    for app in browsers:
        api = app.api_service(apps)
        what = f"`{app.name}`" if len(browsers) > 1 else "The browser app"
        rows.append(
            f"| `make {app.dev_target}` | {what}, in the foreground, on http://localhost:{app.port}"
            f"{(f', proxying `/api` to `make {api.dev_target}`' if api is not None else '')} | The UI loop: edit, "
            "save, the page reloads |"
        )
    rows.append(
        "| `make demo` | Everything, in containers, waited on until it answers, addresses printed | "
        "Showing it to somebody — including yourself |"
    )
    return "\n".join(rows)


def foreground(services: list[App], browsers: list[App]) -> str:
    """The block a reader pastes to bring the whole thing up by hand, one terminal at a time."""
    lines = [f"make {service.dev_target:<10} # leave it running" for service in services]
    lines += [f"make {app.dev_target:<10} # in another terminal" for app in browsers]
    return "\n".join(lines)


def probes(services: list[App]) -> str:
    """The probe lines, per service.

    Two lines where the two probes are two paths, one where the backend's framework serves a readiness
    endpoint of its own and this project points `/health` at it. `/ready` asks the service's store port
    a trivial question — the event store on one rung and the repository on the other — so it is the
    line that says whether the store is reachable from here.
    """
    written = ""
    for service in services:
        written += (
            f"curl -s http://localhost:{service.port}{HEALTH_PATH}     # {health_body(service.backend)}"
            f" — liveness\n"
        )
        if ready_path(service.backend) != HEALTH_PATH:
            written += (
                f'curl -s http://localhost:{service.port}{ready_path(service.backend)}      '
                f'# {{"status":"ready"}} — readiness, which asks the store\n'
            )
    return written


def where(services: list[App]) -> str:
    """Where a slice adds its route: the service it belongs to, named, or the one there is."""
    if len(services) > 1:
        return "the service it belongs to (" + ", ".join(f"`{service.path}`" for service in services) + ")"
    return f"`{services[0].path}`" if services else "the service"


def first_command(first: App | None, browsers: list[App]) -> str:
    """The command the warning about leaving a process running points at. Empty where there is none to
    start, which is the page that returned before this one is read."""
    if first is not None:
        return f"make {first.dev_target}"
    return f"make {browsers[0].dev_target}" if browsers else ""
