"""Which applications a generated project has: one list, read by everything that names one.

A generated repository is a monorepo, and the list of applications it holds is one fact: written into
`project.json` as `deployables`, built here for the generator, and iterated over by every file that has to
name a service — the Make recipes, the Compose file, the CI job, the import gate and the pruner.

Two kinds of application, told apart by `kind`: a **service** is a backend deployable that owes the eight
Make targets, a `/health` probe and the hexagonal layout; a **web** app is a browser frontend, which owes
none of those and is never a service, and names the service its `/api` calls go to. Each service carries its
own `language`, `framework` and `selection` — a project may hold a TypeScript service on Fastify and Postgres
beside a Python one on FastAPI and SQLite — and a project may hold several browser apps, each proxying to a
service of its choice. Everything project-wide (the Makefile, Compose, CI, `.gitignore`, the pruner, the
prose) is the union of what its applications say, computed by the helpers below rather than by any part
asking "the project's language" or "the frontend".

The first service is `apps/service` and the first browser app `apps/web` unless the generation named them
otherwise; either way the first of each kind is the one `make dev`, `PORT` and every document that has to
name one application speak of. Later ones are `apps/<name>`, each on the next port of its kind.

A service also carries what it is *for*: a `purpose` in a sentence or two, and the bounded `contexts` it
holds. Neither changes a scaffolded byte; both exist so the delivery loop can place work. A context may span
several services; a service may hold several as `src/<context>/` — the modular monolith a project starts as —
and one that names none is its own. Once a service holds more than one, the import gate keeps them apart and
the model gate makes every slice say which one it is in; the manifest field is what both read.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from .backends import ENV_FEATURES, SERVICE_PORT, WEB_PORT
from .catalog import family_of, framework_of, resolve_backend
from .errors import GenerationError
from .selection import Selection, transport_feature

# The names the first service and the first browser app are given unless the generation asks for others.
FIRST_SERVICE = "service"
FIRST_WEB = "web"
APPLICATIONS = "apps"
# The one browser framework this factory offers; a second would arrive through `add-framework`.
WEB_FRAMEWORK = "react-vite"

# A service name is a directory under `apps/`, an npm package suffix, a Go module segment and a Compose
# service name at once, so it takes the intersection of what all four accept.
SERVICE_NAME = re.compile(r"[a-z][a-z0-9-]*[a-z0-9]|[a-z]")
# A bounded context's name is also a directory (`src/<context>/` inside a service) and a heading, so it
# takes the same shape.
CONTEXT_NAME = SERVICE_NAME


@dataclass(frozen=True, eq=False)
class App:
    """One application in a generated project, as `project.json` records it."""

    name: str
    path: str
    kind: str
    language: str
    framework: str | None
    port: int
    selection: Selection = field(default_factory=lambda: Selection({}))
    # For a browser app: the service its `/api` calls are proxied to.
    api: str | None = None
    # For a service: what it owns and the bounded contexts it holds — what the delivery loop places a slice
    # against. Absent when nobody has said, which the loop treats as a question, not a default.
    purpose: str | None = None
    contexts: tuple[str, ...] = ()
    # The first of its kind — what `make dev`, `PORT` and every document naming one application speak of. A
    # position on the list, not a name, so it may be called anything; `project.json`'s order records it.
    first: bool = False
    # Whether the factory made this application. `False` marks one that existed before the method did (brownfield
    # adoption; experimental): any `language`, no selection, `commands` per Make target (None is a written no).
    generated: bool = True
    commands: Mapping[str, str | None] | None = None
    # For a wrapped one, what its build runs on: `kind` and `version` (what CI sets up), `ecosystem`, `packaging`.
    toolchain: Mapping[str, str] | None = None
    structure: str | None = None  # `hexagonal` where a wrapped application declares the layers the gate checks
    # Where each recorded fact came from — `detected`, `confirmed` or `overridden`, per field — for an
    # application the factory described rather than chose. Empty for a generated one: its facts are answers.
    provenance: Mapping[str, str] = field(default_factory=dict)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, App) and other.record() == self.record()

    def __hash__(self) -> int:
        # The fact `__eq__` compares; `eq=False` would otherwise keep `object.__hash__`, and equal apps differ.
        return hash(json.dumps(self.record(), sort_keys=True))

    @property
    def backend(self) -> str:
        """The backend key everything in this factory is keyed by — a service's language plus framework."""
        return resolve_backend(self.language, self.framework)

    @property
    def is_service(self) -> bool:
        return self.kind == "service"

    @property
    def transport(self) -> str | None:
        """This service's inbound HTTP feature, or None when it has no transport."""
        return transport_feature(self.selection)

    @property
    def dev_target(self) -> str:
        """The Make target that runs this application in the foreground: `dev` for the first service,
        `dev-web` for the first browser app, `dev-<name>` for every other."""
        if self.first:
            return "dev" if self.is_service else "dev-web"
        return f"dev-{self.name}"

    @property
    def suffix(self) -> str:
        """The Make-variable suffix for this application: `_PAYMENTS`. Empty for the first of its kind."""
        return "" if self.first else f"_{self.name.upper().replace('-', '_')}"

    @property
    def port_variable(self) -> str:
        """The environment variable Compose reads the published host port from.

        `PORT` for the first service, which is what `.env.example` has always written and what the service
        itself reads when run in the foreground; `WEB_PORT` for the first browser app; `PORT_<NAME>` and
        `WEB_PORT_<NAME>` for every other.
        """
        return f"{'PORT' if self.is_service else 'WEB_PORT'}{self.suffix}"

    def api_service(self, apps: list[App]) -> App | None:
        """The service this browser app's `/api` goes to — when that service still has a transport."""
        service = next((s for s in services_of(apps) if s.name == self.api), None)
        return service if service is not None and service.transport is not None else None

    def record(self) -> dict:
        """This application's entry in `project.json`, before the profile adds what it knows."""
        return {
            "kind": self.kind,
            **({} if self.generated else {"generated": False}),
            "path": self.path,
            "language": self.language,
            **({"framework": self.framework} if self.framework else {}),
            **({"port": self.port} if self.generated or self.port else {}),
            # One answer per axis asked of this service; an axis it cannot be given is absent, not "none".
            **({"selection": self.selection.summary} if self.is_service and self.generated else {}),
            **({"commands": dict(self.commands)} if not self.generated and self.commands is not None else {}),
            **({"toolchain": dict(self.toolchain)} if not self.generated and self.toolchain else {}),
            **({"layout": self.structure} if not self.generated and self.structure else {}),
            **({"purpose": self.purpose} if (self.is_service or not self.generated) and self.purpose else {}),
            **({"contexts": list(self.contexts)} if (self.is_service or not self.generated) and self.contexts else {}),
            **({"api": self.api} if not self.is_service and self.api else {}),
            **({"provenance": dict(self.provenance)} if self.provenance else {}),
        }

    @property
    def context_names(self) -> tuple[str, ...]:
        """The bounded contexts this service holds: the ones it names, or itself when it names none."""
        return self.contexts or (self.name,)


def service_app(
    name: str, backend: str, port: int, selection: Selection, first: bool = False,
    purpose: str | None = None, contexts: Sequence[str] | None = None,
) -> App:
    return App(
        name, f"{APPLICATIONS}/{name}", "service", family_of(backend), framework_of(backend), port, selection,
        purpose=purpose or None, contexts=checked_contexts(contexts), first=first,
    )


def web_app(name: str, port: int, api: str, first: bool = False) -> App:
    return App(name, f"{APPLICATIONS}/{name}", "web", "typescript", WEB_FRAMEWORK, port, api=api, first=first)


def default_apps(
    backend: str, frontend: str, selection: Selection | None = None,
    service_name: str = FIRST_SERVICE, web_name: str = FIRST_WEB,
    purpose: str | None = None, contexts: Sequence[str] | None = None,
) -> list[App]:
    """What a freshly generated project has: one service, and the browser app when a frontend was chosen,
    under the names the generation gave them — `service` and `web` unless it asked for others — and with
    whatever the generation said the first service is for."""
    check_name([], service_name)
    apps = [
        service_app(
            service_name, backend, SERVICE_PORT, selection or Selection({}), first=True,
            purpose=purpose, contexts=contexts,
        )
    ]
    if frontend != "none":
        check_name(apps, web_name)
        apps.append(web_app(web_name, WEB_PORT, service_name, first=True))
    return apps


def services_of(apps: list[App]) -> list[App]:
    """The services the factory made — what every recipe, gate and page that speaks of "the services" means."""
    return [app for app in apps if app.is_service and app.generated]


def web_apps(apps: list[App]) -> list[App]:
    return [app for app in apps if not app.is_service and app.generated]


def wrapped_of(apps: list[App]) -> list[App]:
    """The applications that already existed when the method was installed around them: described in the
    manifest, carried through by every command, and asked nothing a generated one is asked."""
    return [app for app in apps if not app.generated]


def frontend_of(apps: list[App]) -> str:
    """The browser framework this project uses, or `none` — derived from the list, never asked separately."""
    web = web_apps(apps)
    return (web[0].framework or WEB_FRAMEWORK) if web else "none"


def backends_of(apps: list[App]) -> list[str]:
    """Every backend a service is written on, in order of first appearance, once each."""
    return list(dict.fromkeys(service.backend for service in services_of(apps)))


def families_of(apps: list[App]) -> list[str]:
    """Every language family a service is written in, in order of first appearance, once each."""
    return list(dict.fromkeys(service.language for service in services_of(apps)))


def described(service: App) -> str:
    """One service as the prose lists it: its path, backend and port, then its contexts and what it owns."""
    contexts = f", {contexts_phrase(service)}" if service.contexts else ""
    purpose = f" — {service.purpose}" if service.purpose else ""
    return f"`{service.path}` (`{service.backend}`, port {service.port}{contexts}){purpose}"


def contexts_phrase(service: App) -> str:
    """`context `a`` or `contexts `a`, `b``: the bounded contexts a service holds, for a line of prose."""
    names = ", ".join(f"`{name}`" for name in service.context_names)
    return f"context{'s' if len(service.context_names) > 1 else ''} {names}"


def contexts_of(apps: list[App]) -> dict[str, list[App]]:
    """The services grouped by the bounded contexts each holds, in order of first appearance. A service
    holding several appears under each of them."""
    grouped: dict[str, list[App]] = {}
    for service in services_of(apps):
        for context in service.context_names:
            grouped.setdefault(context, []).append(service)
    return grouped


def features_of(apps: list[App]) -> list[str]:
    """Every feature any service's selection emits — the union the project-wide files are built from."""
    return sorted({feature for service in services_of(apps) for feature in service.selection.features})


def prunable_features_of(apps: list[App]) -> list[str]:
    """Every feature a later `./init` could still take away from some service."""
    return sorted({feature for service in services_of(apps) for feature in service.selection.prunable_features})


def has_feature(apps: list[App], feature: str) -> bool:
    return any(service.selection.has(feature) for service in services_of(apps))


def containers_of(apps: list[App]) -> list[str]:
    """Every Compose service the services need, once each."""
    return list(dict.fromkeys(c for service in services_of(apps) for c in service.selection.containers))


def axes_of(apps: list[App]) -> list[str]:
    """Every axis some service was asked, in catalog order."""
    return list(dict.fromkeys(axis for service in services_of(apps) for axis in service.selection.axes))


def transports_of(apps: list[App]) -> list[str]:
    """Every inbound HTTP feature some service has, once each, in service order."""
    return list(dict.fromkeys(s.transport for s in services_of(apps) if s.transport is not None))


def first_transport(apps: list[App]) -> str | None:
    """The transport of the first service that has one — what the browser app proxies to."""
    return next((s.transport for s in services_of(apps) if s.transport is not None), None)


def needs_environment(apps: list[App]) -> bool:
    return any(has_feature(apps, feature) for feature in ENV_FEATURES)


def next_port(apps: list[App]) -> int:
    """The next service port: one above the highest a service already has — 3000, 3001, … — so nothing is
    reassigned. The browser apps' 5173, 5174, … are a sequence of their own."""
    return max((app.port for app in services_of(apps)), default=SERVICE_PORT - 1) + 1


def next_web_port(apps: list[App]) -> int:
    return max((app.port for app in web_apps(apps)), default=WEB_PORT - 1) + 1


def check_name(apps: list[App], name: str) -> None:
    if not SERVICE_NAME.fullmatch(name):
        raise GenerationError(
            f"'{name}' cannot name an application: use lowercase letters, digits and hyphens, starting with a "
            "letter — it has to be a directory, an npm package, a Go module segment and a Compose service"
        )
    if any(app.name == name for app in apps):
        raise GenerationError(f"this project already has an application named '{name}'")


def check_context(name: str) -> None:
    if not CONTEXT_NAME.fullmatch(name):
        raise GenerationError(
            f"'{name}' cannot name a bounded context: use lowercase letters, digits and hyphens, starting "
            "with a letter — it is a directory inside a service and a heading in the model"
        )


def checked_contexts(names: Sequence[str] | None) -> tuple[str, ...]:
    """The contexts a service was given, each a legal name, once each and in the order given."""
    for name in names or ():
        check_context(name)
    return tuple(dict.fromkeys(names or ()))


def add_web(apps: list[App], name: str, api: str | None) -> list[App]:
    """The list with one more browser app on it, proxying `/api` to `api` (the first service by default)."""
    check_name(apps, name)
    services = services_of(apps)
    if not services:
        raise GenerationError(
            "this project has no service the factory made for a browser app to proxy to; add one with add-service first"
        )
    api = services[0].name if api is None else api
    if api not in {service.name for service in services}:
        raise GenerationError(
            f"'{api}' is not a service of this project; the browser app can proxy to "
            f"{', '.join(service.name for service in services)}"
        )
    return [*apps, web_app(name, next_web_port(apps), api)]


def add_service(
    apps: list[App], name: str, backend: str, selection: Selection,
    purpose: str | None = None, contexts: Sequence[str] | None = None,
) -> list[App]:
    """The list with one more service on it, refusing a name that cannot be a service here."""
    check_name(apps, name)
    # The first service the factory makes takes the role (`make dev`, `PORT`) even beside pre-existing ones.
    first = not services_of(apps)
    return [
        *apps,
        service_app(name, backend, next_port(apps), selection, first=first, purpose=purpose, contexts=contexts),
    ]

