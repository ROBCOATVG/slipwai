"""`docs/`: the documentation a generated project owns, rendered from the pages under `assets/pages/docs/`.

Four of these pages are this module's: *Getting started*, *Verification gates*, *What's included* and the
*Delivery workflow*. Each says something only this project knows — which native gate `make verify` runs,
whether there is a browser app, whether the event profile asks anything of the constitution, whether there is
anywhere to deploy — but it says it in the same words every time, so the words are assets and what is left
here is which sections a project's answers select and what the closed set of values holds
(`docs/generated-prose.md`).

16.1's rule divided them without a case it could not answer. The style gate and the production gate are whole
paragraphs that are there or are not, so they are sections. So are the two workflow diagrams, which are the
same drawing for every project of a profile, and the closing paragraph of *Getting started*, which is one of
two. What stays here is everything a paragraph does not contain: the gate description the registry answers,
the three endings of the constitution-coverage sentence, the bullet per service, the line about the model and
the write side. The branch inside a sentence is rendering, and rendering stays in Python.

Where a page's last words are another module's — the backing services' gates, the line production adds to
*What's included* — they are appended after the render rather than named as values, because a value at the
very end of a page would have to carry the page's own final newline.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..registry import GATE_DESCRIPTION, registry
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
from .prose import page
from .skills_page import skills_page
from .write_model_prose import sourced_services

GETTING_STARTED = "docs/getting-started.md"
GATES = "docs/gates.md"
INCLUDED = "docs/whats-included.md"
WORKFLOW = "docs/workflow.md"


def documentation_files(
    project_name: str, profile: str, apps: list[App], target: str = "none"
) -> dict[str, str]:
    """Every file under `docs/` that the services' selections decide the content of."""
    event = profile == "event-modelling"
    named = values(project_name, profile, apps, target)
    gates = ["style-gate"] if web_apps(apps) else []
    if managed(CATALOG, target):
        gates.append("production-gate")
    files = {
        GETTING_STARTED: page(GETTING_STARTED, named,
                              ("event-contract",) if event else ("standard-boundary",)),
        GATES: page(GATES, named, tuple(gates)) + backing_services_gates(apps),
        "docs/skills-and-commands.md": skills_page(
            profile, apps, named["language"], named["frontend"], command_list(event)
        ),
        INCLUDED: (page(INCLUDED, named) + production_included_line(target)
                   + included_model_line(event, apps)),
        WORKFLOW: page(WORKFLOW, named, ("event-diagram",) if event else ("plain-diagram",)),
        "docs/evolving-the-project.md": evolving_page(),
    }
    # What this project's browser surface looks like and where that is decided; nothing at all without one.
    files.update(design_page(apps))
    if event and services_of(apps):
        files.update(event_documentation(project_name, services_of(apps)))
    return files


def values(project_name: str, profile: str, apps: list[App], target: str = "none") -> dict[str, str]:
    """Every value these four pages may name, and the whole of what they may name.

    One set across the four, because a value's name is the same question whichever page asks it, and a page
    that names none of a value is no reason for the value to have a second spelling.
    """
    services = services_of(apps)
    web = web_apps(apps)
    web_paths = ", ".join(f"`{app.path}`" for app in web)
    backends = backends_of(apps)
    return {
        "project-name": project_name,
        "profile": profile,
        "language": ", ".join(f"`{backend}`" for backend in backends),
        "frontend": frontend_of(apps),
        "first-slice": first_slice(services),
        "browser-paths": (f" Connect it through {web_paths} without sharing backend implementation types."
                          if web else ""),
        "gate": "; ".join(dict.fromkeys(registry().answer(backend, GATE_DESCRIPTION) for backend in backends)),
        "web-gate": (f" plus Biome, TypeScript and React component tests for {web_paths}" if web else ""),
        "coverage-scope": coverage_scope(profile == "event-modelling", apps),
        # The note ends on a line break of its own, and the page supplies that one: a value is substituted
        # into the line it sits on, so a note carrying its own would leave the section a blank line longer.
        "flag-gate-note": FLAG_GATE_NOTE.removesuffix("\n"),
        "service-items": "".join(
            f"- A native `{service.backend}` application and executable health test under `{service.path}`\n"
            for service in services
        ),
        "frontend-items": "".join(
            f"- A separate TypeScript/React/Vite browser application under `{app.path}`, with a styled baseline"
            f" (`docs/design.md`), one route, a typed client generated from the service's published contract,"
            f" and Testing Library component tests\n"
            for app in web
        ),
        "pins": pin_list(apps),
        "discovery": ("Update the event model and example-map the slice" if profile == "event-modelling"
                      else "Write or refine the behaviour specification"),
    }


def command_list(event: bool) -> str:
    """The commands this project has, as `docs/skills-and-commands.md` lists them."""
    return "\n".join(f"- `/{name}` — `commands/{name}.md`" for name in command_names(event))


def first_slice(services: list[App]) -> str:
    """Where *Getting started* says to put the first slice: in the first service, or in the code that was
    already here. One sentence inside a paragraph, so it is rendered rather than written."""
    if services:
        return (f"Replace the health example in `{services[0].path}` with the smallest actor-visible product "
                "slice.")
    return ("Start with the smallest actor-visible product slice in the code that already exists — the factory "
            "made none of it, and `project.json` records where it is.")


def coverage_scope(event: bool, apps: list[App]) -> str:
    """What `make check-constitution` reads a constitution for, finishing the sentence the page opens.

    Two well-wrapped sentences rather than a conditional spliced mid-sentence: this paragraph is generated
    for both profiles, and a branch inside a line wraps badly in whichever one loses. Three endings rather
    than two, and the same three `commands/constitution-coverage.md` carries, because the gate reads the
    capabilities and `event-sourcing` now arrives with a service's rung rather than with the profile: these
    two pages describing one gate differently is how a reader learns to trust neither.
    """
    if not event:
        return """`skills/` teach. Nothing about event sourcing is asked of this profile. An unfilled
`[PLACEHOLDER]` means drafted rather than ratified."""
    if sourced_services(apps):
        return """`skills/` teach, and the Event Modeling and event-sourcing obligations. An unfilled
`[PLACEHOLDER]` means drafted rather than ratified."""
    return """`skills/` teach, and the Event Modeling obligations. No service here keeps a log, so the
event-sourcing obligations are not asked of this project. An unfilled
`[PLACEHOLDER]` means drafted rather than ratified."""


def included_model_line(event: bool, apps: list[App]) -> str:
    """What `docs/whats-included.md` says this project was given on the model and the write side.

    One line, and it stopped being able to say *as one bundle* when phase 15 split the two: a modelled
    project whose services all keep current state has every Event Modeling document and no event-sourcing
    layer at all, which the old line described as both of those at once.
    """
    if not event:
        return "- No event model or event-sourcing layer\n"
    if sourced_services(apps):
        return (
            "- Event Modeling documents, plus the backend event-sourcing skills and contracts for the "
            "services that keep their events\n"
        )
    return (
        "- Event Modeling documents, and a write-model table per service "
        "(`docs/event-modeling-to-code.md`); no service here keeps a log\n"
    )
