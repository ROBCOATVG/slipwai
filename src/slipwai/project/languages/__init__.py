"""One module per backend language: the walking skeleton, its manifests, and its own naming.

Each language owns the whole of its own contribution — what lands in a service's directory, and how the
template names become this project's. No shared rename step: a backend brings its own `name_service`."""
from __future__ import annotations

from ...services import App, families_of, services_of
from ...tooling import verify_dispatcher, verify_path
from . import go, java_quarkus, java_spring, python, typescript

# Keyed by backend, not by module name: a backend named for the framework that owns its startup
# carries a hyphen, and a hyphen cannot appear in a Python module name.
BACKENDS = {
    "typescript": typescript,
    "python": python,
    "go": go,
    "java-quarkus": java_quarkus,
    "java-spring": java_spring,
}


def language_files(project_name: str, event: bool, apps: list[App], target: str = "none") -> dict[str, str]:
    """Everything every backend contributes, at its final paths and under its final names.

    `service_files` is keyed relative to the service — the only thing this facade knows about any backend —
    and is emitted once per service from its own selection and the target (which decides only whether the
    service gets a flag reader), then named for it. Root files come from `repository_files`, once per
    language family; with several families, `scripts/verify` dispatches to each."""
    services = services_of(apps)
    files: dict[str, str] = {}
    for service in services:
        backend = BACKENDS[service.backend]
        tree = {f"{service.path}/{p}": t for p, t in backend.service_files(event, service.selection, target).items()}
        files.update(backend.name_service(project_name, service, tree))
    for family in families_of(apps):
        own = [service for service in services if service.language == family]
        files = BACKENDS[own[0].backend].repository_files(project_name, files, own, verify_path(family, apps))
    if len(families_of(apps)) > 1:
        files["scripts/verify"] = verify_dispatcher(apps)
    return files
