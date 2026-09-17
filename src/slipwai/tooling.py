"""How one service's build is spelled: what its package is named after, which verify script it lands in, and
its per-backend commands with the service's own path in them.

Split out of `services.py`, which is the list of applications and the questions asked of the list; these are
the answers one entry gives a Makefile, a Compose file or a CI job. Every helper here takes an `App` and reads
the tables in `backends.py`, and nothing in `services.py` needs any of them.
"""
from __future__ import annotations

from .backends import APP, BACKEND_TOOLING, FEATURE_TOOLING, VERIFY
from .services import App, families_of


def service_qualifier(project_name: str, service: App) -> str:
    """What a service's package or module is named after.

    The first service is named after the project alone — `acme` is `acme_service`'s Python package and
    `com.example.acme`'s Java one, exactly as before there could be a second — and every later service
    carries its own name too, so `acme-payments` becomes `acme_payments` and `acmepayments`.
    """
    return project_name if service.first else f"{project_name}-{service.name}"


def package_name(project_name: str, app: App) -> str:
    """An npm package's name: `<project>-<app>`, for services and browser apps alike."""
    return f"{project_name}-{app.name}"


def verify_path(family: str, apps: list[App]) -> str:
    """Where one language family's verify script lands.

    `scripts/verify` while the project has one family, as it always was. With several, each family gets
    `scripts/verify-<family>` and `scripts/verify` is the dispatcher that runs them all — so a Python
    recipe that runs one mode of its own script names its own script and not the dispatcher.
    """
    return "scripts/verify" if len(families_of(apps)) == 1 else f"scripts/verify-{family}"


def verify_dispatcher(apps: list[App]) -> str:
    """`scripts/verify` for a project whose services span language families: it runs each family's own."""
    scripts = " ".join(verify_path(family, apps) for family in families_of(apps))
    return f"""#!/bin/sh
set -eu
# One script per language family, each looping over its own services; the arguments are passed through,
# and only the Python script reads them as modes.
for script in {scripts}; do "./$script" "$@"; done
"""


def for_app(text: str, path: str, verify: str = "scripts/verify") -> str:
    """One per-backend command, spelled for one application. `APP` and `VERIFY` are tokens rather than
    `str.format` fields because the recipes they sit in are shell and Make text with braces of their own —
    the convention `__TRANSPORT__` and `__APP_SERVICES__` follow in the assets."""
    return text.replace(APP, path).replace(VERIFY, verify)


def app_tooling(service: App, apps: list[App], feature: str | None = None) -> dict:
    """`BACKEND_TOOLING` for one service, with the feature's own spelling where it has one."""
    backend = service.backend
    tooling = {**BACKEND_TOOLING[backend], **FEATURE_TOOLING.get(backend, {}).get(feature or "", {})}
    verify = verify_path(service.language, apps)
    return {
        key: for_app(value, service.path, verify) if isinstance(value, str) else value
        for key, value in tooling.items()
    }


def one_line(commands: list[str]) -> str:
    """Several commands as one shell line, each in its own subshell — for a Make variable that has to hold
    the whole step and for nothing else; a single command is returned as it is."""
    unique = list(dict.fromkeys(commands))
    if len(unique) == 1:
        return unique[0]
    return " && ".join(f"({command})" if "cd " in command else command for command in unique)
