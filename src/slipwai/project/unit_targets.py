"""The Makefile's fast target per deployable: `unit-<name>`, where a project has more than one.

Its own module because `makefile.py` sits at the line budget `scripts/check-structure.py` holds every module
to — the reason `agent_targets.py` is one too — and because this is about the increment rather than any
service's toolchain: `make unit` is one target over every deployable, which is right for the merge and wrong
for the increment, and a boundary that changed one service's domain paid for the browser suite every time —
about ninety seconds of Vitest per Go increment on one project — while the shipwright's brief, which says to
run the quickest relevant command, had no name to give it.
"""
from __future__ import annotations

from ..services import App, services_of, web_apps
from ..tooling import verify_path
from .native_commands import fast_targets, service_commands


def unit_targets(apps: list[App]) -> tuple[str, str]:
    """One fast target per deployable, where the project has more than one: `unit-<name>`, running that
    application's own fast checks and nothing else. (The `.PHONY` names, the targets.) A project with one
    deployable has `unit` and nothing to add."""
    services = services_of(apps)
    web = web_apps(apps)
    if len(services) + len(web) < 2:
        return "", ""
    fast = fast_targets(apps)
    targets = ""
    names = []
    for service in services:
        own = service_commands(service.backend, service.path, verify_path(service.language, apps))
        recipe = "\n\t".join(own[target] for target in fast)
        names.append(f"unit-{service.name}")
        targets += (f"unit-{service.name}: ## The fast tests of {service.path} alone — what an increment there runs\n"
                    f"\t{recipe}\n")
    for app in web:
        names.append(f"unit-{app.name}")
        targets += (f"unit-{app.name}: ## The fast tests of {app.path} alone — what an increment there runs\n"
                    f"\tnpm --workspace {app.path} test\n")
    return " ".join(names), targets
