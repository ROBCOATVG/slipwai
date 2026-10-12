"""`commands/`: the workflow commands adapted to this project's profile and toolchain.

The pages themselves are under `assets/toolkit/commands/`, beside the three that never varied and were
already there; what is here is the part that is not prose — which value each page may name, and which of
its sections this project gets. `docs/generated-prose.md` is the rule, and `prose.py` the mechanism.
"""
from __future__ import annotations

from ..assets import TOOLKIT_ROOT
from ..catalog import CATALOG
from ..layout import AT_ROOT, Layout
from ..origin import Adoption
from ..services import App, backends_of, web_apps
from ..targets import managed
from .add_commands import add_command_files
from .adversary import adversary_command
from .benchmark import benchmark_command, what_each_stage_costs
from .careen import careen_command
from .catch_up_command import catch_up_files
from .cruise import cruise_command, cruise_settings_command
from .cruise_seat import cruise_status_command, cruise_stop_command, cruise_tell_command, cruise_watch_command
from .demo_stop import demo_stop
from .harbour import budget_section
from .ladder import hook_points, sail_ladder
from .mutation import mutation_command
from .parallel_slices import done_marker, independence, slice_graph
from .prose import page
from .sail_section import delegable_types, model_delegation_settings_command
from .sail_settings import implementation_section, sail_settings_command
from .whats_next import whats_next_command
from .where_are_we import where_are_we_command
from .write_model_prose import sourced_services, state_services

# Where the pages live: beside the three a project has always received verbatim.
COMMANDS = TOOLKIT_ROOT / "commands"


def sail_values(
    event: bool, apps: list[App], target: str = "none", layout: Layout = AT_ROOT,
    adoption: Adoption | None = None,
) -> dict[str, str]:
    """Every value `sail.md` may name, and the whole of what it may name.

    Two kinds, and the page cannot tell them apart. What this module decides — which artifact resolves the
    slice — and what the modules around it own: the ladder itself, the table of delegable types rendered
    from `stage_models.STAGES`, and the passages `benchmark.py`, `sail_settings.py`, `harbour.py`,
    `ladder.py` and `demo_stop.py` write. Those stay where they are until their own slice of phase 16
    moves them, and `sail.md` names them meanwhile; `parallel_slices.py` has had its, and what it still
    answers is the three sentences of the concurrency rules that a declaration decides.
    """
    return {
        "resolution": ("the requested slice in `docs/event-model/model.yaml`" if event else
                       "the requested feature or the active directory recorded in `.specify/feature.json`"),
        "ladder": sail_ladder(event, apps, target, layout, adoption),
        "make": layout.make,
        "delegable-types": delegable_types(),
        "stage-costs": what_each_stage_costs(layout),
        "implementation": implementation_section(layout),
        "budget": budget_section(),
        "hook-points": hook_points(),
        "demo-stop": demo_stop(event, ", ".join(f"`{app.path}`" for app in web_apps(apps))),
        "done-marker": done_marker(event),
        "slice-graph": slice_graph(event),
        "independence": independence(event),
    }


def sail_command(
    event: bool, apps: list[App], target: str = "none", layout: Layout = AT_ROOT, adoption: Adoption | None = None,
) -> str:
    """The ladder a slice is driven down. The release constraint is a whole section, and a project with no
    destination the keel deploys to has nothing to say about pushing to one."""
    return page(COMMANDS, "sail.md", sail_values(event, apps, target, layout, adoption),
                ("push-check",) if managed(CATALOG, target) else ())


def gaps_values(event: bool, apps: list[App]) -> dict[str, str]:
    """What `gaps.md` may name: which artifact this profile tightens, and what a trace compares against.

    One sentence covering both rungs rather than a branch, because the thing the pass compares is the same
    on either — the identity a write is made against — and only its name differs. A project with a service
    on each rung would otherwise carry two sentences telling the reader to do one thing twice.
    """
    return {
        "artifact": "a slice's `examples.md`" if event else "the slice's acceptance criteria in `spec.md`",
        "identity": (
            "the identity each write is made against — a stream's version on a service that keeps its events, "
            "the row's on one that keeps current state"
            if state_services(apps)
            else "stream identity"
        ),
    }


def gaps_command(event: bool, apps: list[App]) -> str:
    """The pass that tightens an artifact, and the pass that traces what was built. The paragraph asking
    for events, schemas and model links is a whole section, selected by the profile."""
    return page(COMMANDS, "gaps.md", gaps_values(event, apps), ("event",) if event else ())


def coverage_values(event: bool, apps: list[App]) -> dict[str, str]:
    """The floor `scripts/check-constitution.py` states, which completes the sentence naming it.

    Three scopes, not two, because the capability stopped travelling with the profile: `event-sourcing`
    arrives with `write-model: events` on a service, so a modelled project every service of which keeps
    current state claims the modelling obligations and not the sourcing ones. Told otherwise, the reader
    drafts a principle mandating a log for services that have none and then cannot pass their own gate.
    """
    if not event:
        scope = """minimum CD and the practices this repository's skills teach. The event-sourcing obligations
are not asked of this profile, and `make check-speckit` rejects a constitution that mandates them anyway."""
    elif sourced_services(apps):
        scope = """minimum CD, the practices this repository's skills teach, and — because `project.json` claims
the event capabilities — the Event Modeling and event-sourcing obligations."""
    else:
        scope = """minimum CD, the practices this repository's skills teach, and — because `project.json` claims
the Event Modeling capability — the Event Modeling obligations. No deployable here records `eventSourced`,
so the event-sourcing obligations are not asked of this project: every service keeps current state, and a
principle mandating a log would be one no service could be held to."""
    return {"scope": scope}


def constitution_coverage_command(event: bool, apps: list[App]) -> str:
    return page(COMMANDS, "constitution-coverage.md", coverage_values(event, apps))


# Every command a generated project carries, in the order `docs/skills-and-commands.md` lists them — the last
# three reaching back out to the keel. One list, so the documentation and the files cannot disagree.
BASE_COMMANDS = ("drive", "mockups", "chart", "example-map", "careen", "where-are-we", "whats-next", "gaps", "adversary", "mutation",
                 "constitution-coverage",
                 "model-delegation-settings", "sail-settings", "benchmark", "cruise", "cruise-settings",
                 "cruise-status", "cruise-stop", "cruise-tell", "cruise-watch", "add-service", "add-frontend",
                 "catch-up")
# Copied whole from `assets/profiles/event-modelling/commands/`; listed because the documentation names them in order.
# `example-map` left this list in slice 5.17: it is a stage of both profiles now and ships from the toolkit.
EVENT_COMMANDS = ("validate-code-against-model",)


def values(
    event: bool = False, apps: list[App] | None = None, target: str = "none", layout: Layout = AT_ROOT,
    adoption: Adoption | None = None,
) -> dict[str, str]:
    """Every value the three pages here may name, pooled — what `tests/test_generated_prose.py` holds the
    assets to in both directions. Built from the per-page sets rather than beside them, so a value added
    to a page is named here by having been added there."""
    apps = [] if apps is None else apps
    return {**sail_values(event, apps, target, layout, adoption), **gaps_values(event, apps),
            **coverage_values(event, apps)}


def command_names(event: bool) -> list[str]:
    """The commands this profile ships, in the order they are documented."""
    return [*BASE_COMMANDS, *(EVENT_COMMANDS if event else ())]


def command_files(
    event: bool, apps: list[App], target: str = "none", layout: Layout = AT_ROOT, adoption: Adoption | None = None,
) -> dict[str, str]:
    """`commands/`: one file per command, adapted to this profile and the services' backends."""
    files = {
        "commands/sail.md": sail_command(event, apps, target, layout, adoption),
        "commands/careen.md": careen_command(layout),
        "commands/cruise.md": cruise_command(event, apps, target, layout, adoption),
        "commands/cruise-settings.md": cruise_settings_command(layout),
        "commands/cruise-status.md": cruise_status_command(layout),
        "commands/cruise-stop.md": cruise_stop_command(layout),
        "commands/cruise-tell.md": cruise_tell_command(layout),
        "commands/cruise-watch.md": cruise_watch_command(layout),
        "commands/where-are-we.md": where_are_we_command(event, target),
        "commands/whats-next.md": whats_next_command(event),
        "commands/gaps.md": gaps_command(event, apps),
        "commands/adversary.md": adversary_command(event, apps),
        "commands/mutation.md": mutation_command(backends_of(apps)),
        "commands/constitution-coverage.md": constitution_coverage_command(event, apps),
        "commands/model-delegation-settings.md": model_delegation_settings_command(layout),
        "commands/sail-settings.md": sail_settings_command(layout),
        "commands/benchmark.md": benchmark_command(layout),
    }
    files.update(add_command_files(apps, target))
    files.update(catch_up_files(apps, target))
    return files
