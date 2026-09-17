"""The Java/Spring Boot backend: `apps/service`, its Maven build, and this project's own package name."""
from __future__ import annotations

from ...assets import LANGUAGE_ROOT, asset_tree
from ...selection import Selection
from ...services import App
from ..backing_services import backing_service_service_files
from ..flag_route import flag_resource
from ..flags import flag_reader
from .java import rename_java_sources, verify_script


def service_files(event: bool, selection: Selection, target: str = "none") -> dict[str, str]:
    """What this backend puts in a service's directory, keyed relative to it.

    Nothing is decided here by the selection: the pom and `application.properties` carry a marked region
    per feature and are emitted whole, then cut down by the pruner — the same mechanism `docker-compose.yml`
    uses, and for the same reason. A feature's dependency block and its configuration have to disappear
    together, and a marker is the one spelling that survives a later `./init` too.

    There is deliberately no `event-port/` fallback tree. That exists for a backend whose event-store axis
    offers nothing yet; this one answers all three of its options, so the port arrives from
    `backing_service_service_files` with adapters behind it, and emitting both would define it twice.

    Two trees, not one, and the split is by who decides the file. `java/build/` is the *family's*: the
    Maven wrapper and the three analyser configurations are the same files whatever owns startup, so they
    are read by both Java backends rather than copied into each. `java-spring/app/` is this backend's: the
    pom, the properties, `ServiceApplication` and the walking skeleton, all of which name the framework.
    """
    files = asset_tree(LANGUAGE_ROOT / "java/build")
    files.update(asset_tree(LANGUAGE_ROOT / "java-spring/app"))
    files.update(backing_service_service_files(selection, "java-spring"))
    # The flag reader, from the family's tree for the reason every `../java/` source is: it names no
    # framework type. Only where there is somewhere to deploy — see `flags.py`.
    files.update(flag_reader(target, "java-spring"))
    # And the route that serves them to the browser app, which this framework discovers rather than
    # having registered. Absent without both a target and a transport. See `flag_route`.
    files.update(flag_resource(target, "java-spring", selection))
    return files


def name_service(project_name: str, service: App, files: dict[str, str]) -> dict[str, str]:
    """One service's files under this project's own package — the family's rename, see `java.py`."""
    return rename_java_sources(project_name, service, files)


def repository_files(
    project_name: str, files: dict[str, str], services: list[App], verify: str
) -> dict[str, str]:
    """`scripts/verify` above the services, and nothing else.

    There is no aggregator pom above them: each service is a Maven project of its own, and one pom that
    exists only to list them is a file to keep in step for nothing — `scripts/verify` and the Makefile are
    the loop. Compare `go.work`, which Go genuinely requires.
    """
    files[verify] = verify_script(services)
    return files
