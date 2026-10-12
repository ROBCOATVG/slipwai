"""`README.md`: what this project is, how to start it, and what it was given — rendered from a page.

The README is the one generated file a person reads before anything else, so it answers in order: what this
is, how to start it, how to *run* it, and what each axis was answered with. Those words are the same in every
project, so they are `assets/pages/README.md` and what is left here is what the words are not: which sections
this project's answers select, and the closed set of values they may name (`docs/generated-prose.md`).

The conditionals divide the way 16.1 said they would. *Before `./init`*, *Services*, *Run it*, *Profile
boundary* and *Event workflow* are whole sections — a reader can point at where each begins and ends, and the
words inside are the same in every project that gets them — so the page carries each behind a marker and this
module names the ones it wants. The branches that are smaller than a paragraph stay here, because they are
rendering rather than prose: the comment appended to `./init` in the block a reader runs first, the sentence
spliced into the paragraph under it, the clause naming the browser apps, and the numbers the cloud's own
prerequisite rows push the rows below them down to.

Two passages the page names are another module's: *Production* is the target's and the shape's from its first
word to its last (`target_docs.py`), and the backing services' section is written per feature from what the
services actually need (`backing_service_prose.py`). Each arrives as a value rather than as words here.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..loaded_targets import cloud_of
from ..services import App, described, frontend_of, services_of, web_apps
from ..targets import managed
from .backing_service_prose import backing_services_readme
from .event_model import event_model_page_url
from .prose import page
from .target_docs import prerequisites, production_readme
from .write_model_prose import readme_write_model

PAGE = "README.md"


def readme(
    project_name: str, profile: str, apps: list[App], target: str = "none", shape: str = "liner",
) -> str:
    """`README.md` as this project receives it, with whatever its services need running appended.

    The backing services' section is appended here rather than named as a value because it is the last thing
    on the page: a value would have to carry its own trailing newline into the asset, and a page that ends
    without one is a page every editor fights.
    """
    rendered = page(PAGE, values(project_name, profile, apps, target, shape), wanted(profile, apps, target))
    return rendered + backing_services_readme(apps)


def wanted(profile: str, apps: list[App], target: str) -> tuple[str, ...]:
    """The sections this project's answers select, in the order the page carries them."""
    services = services_of(apps)
    web = web_apps(apps)
    chosen = ["before-init-cloud" if managed(CATALOG, target) else "before-init"]
    chosen.append("services" if services else "services-none")
    if web or [service for service in services if service.transport is not None]:
        chosen.append("run-it")
    chosen.append("event-workflow" if profile == "event-modelling" else "profile-boundary")
    return tuple(chosen)


def values(
    project_name: str, profile: str, apps: list[App], target: str = "none", shape: str = "liner",
) -> dict[str, str]:
    """Every value the page may name, and the whole of what it may name.

    The same keys whatever the answers, so the closed set is closed: a section the page did not select still
    provides its values, and a token that moved into a section this project does not get is a refusal here
    rather than a marker shipped into somebody's repository.
    """
    services = services_of(apps)
    web = web_apps(apps)
    frontend_capabilities = CATALOG["frontends"][frontend_of(apps)]["capabilities"]
    # Only a cloud has prerequisite rows of its own, and only a cloud may be asked for them: the rest
    # of the set is the same whatever the answers, so a value is never a key that is sometimes absent.
    cloud_rows = prerequisites(target) if managed(CATALOG, target) else ()
    # The cloud's own rows land in the middle, so the numbering either side of them is counted rather than
    # written: a target that asks for one more tool moves every row below it, and the sentence under the
    # table names the range it checks.
    last_checked = len(cloud_rows) + 2
    return {
        "title": project_name.replace("-", " ").replace("_", " ").title(),
        "project-name": project_name,
        "profile": profile,
        "target": target,
        "services": "; ".join(f"`{service.backend}` in `{service.path}`" for service in services),
        "frontend": frontend_of(apps),
        "frontend-paths": (" in " + ", ".join(f"`{app.path}`" for app in web)) if web else "",
        "capabilities": ", ".join(CATALOG["profiles"][profile]["capabilities"]),
        "frontend-capabilities": ", ".join(frontend_capabilities) if frontend_capabilities else "none",
        "axes": selection_summary(services),
        "cloud": cloud_of(target),
        "prerequisites": "\n".join(
            f"| {number} | {have} | {proof} |" for number, (have, proof) in enumerate(cloud_rows, start=2)
        ),
        "last-checked": str(last_checked),
        "repository-row": str(last_checked + 1),
        "passphrase-row": str(last_checked + 2),
        "start-here-production": start_here_production(target),
        "init-production": init_production(target),
        "services-described": ", ".join(described(service) for service in services),
        "browser-apps": browser_apps(web),
        "run-commands": run_commands(services, web),
        "production": production_readme(target, services, web, shape),
        "documentation-production": documentation_production(target),
        "write-model": readme_write_model(apps),
        "model-page": event_model_page_url(project_name),
    }


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


def browser_apps(web: list[App]) -> str:
    """The clause naming the browser apps, inside the *Services* paragraph's first sentence: a count the
    declaration already answers, so it is rendered rather than written."""
    if not web:
        return ""
    return (
        " " + ", ".join(f"`{app.path}`" for app in web)
        + (" are the browser apps, which are" if len(web) > 1 else " is the browser app, which is")
        + " not a service and owe" + ("" if len(web) > 1 else "s") + " none of this."
    )


def run_commands(services: list[App], web: list[App]) -> str:
    """The block under *Run it*: one line per thing this project can be started with, and the address each
    answers on. The section is the README's answer to "how do I see it?", directly after "Start here",
    because a starter whose only verb is `make verify` teaches that the way to know something works is to
    run its tests — and the demo a slice is supposed to end with then has to be invented from scratch by
    whoever reaches one first."""
    lines: list[str] = []
    for service in [one for one in services if one.transport is not None]:
        lines.append(
            f"make {service.dev_target:<10} # {service.name} alone, in the foreground on "
            f"http://localhost:{service.port}"
        )
    for app in web:
        what = "the browser app" if len(web) == 1 else app.name
        lines.append(f"make {app.dev_target:<10} # {what}, in the foreground on http://localhost:{app.port}")
    lines.append("make demo       # or the whole thing in containers, addresses printed when it answers")
    return "\n".join(lines)


def documentation_production(target: str) -> str:
    """The deployment drawing, named where a reader looks for documentation and not only mid-paragraph
    under *Production* — it is the page people go looking for and did not find."""
    if target == "existing":
        return ", [`docs/deployment.md`](docs/deployment.md) records where this runs and how a release reaches it"
    if not managed(CATALOG, target):
        return ""
    return (
        f", [`docs/deployment.md`](docs/deployment.md) draws what runs in {cloud_of(target)} for this project's "
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
        f"{cloud_of(target)} credentials"
    )
