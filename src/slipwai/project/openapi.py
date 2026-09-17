"""The published API document as a committed file, and the gate that keeps it honest.

A service that declares its routes' schemas already knows its own contract; what it did not have was a
copy of it anybody outside the process could read. `make openapi` writes one — from the app, with nothing
listening — and `make check-openapi` fails when the committed copy no longer matches the routes.

Three things want the file rather than the endpoint. `packages/api-client` is generated from it, so the
browser app's types come from the service's own contract and not from a hand-kept duplicate. A consumer
reads it without reading the service's language. And a reviewer sees a contract change in the diff, which
is the only place a breaking change is cheap to notice.

Not every transport has one to export. Go's document is hand-written — there is no generator on that
backend and buying one would cost the dependency it exists without — and `openapi_test.go` in the adapter's
own package is what holds it to the routes the mux serves, so it needs no recipe here. Quarkus and Spring
publish theirs from their own extensions. `export_command` answers for only the transports the factory can
write the file for, so a transport absent from it gets no recipe rather than a broken one.
"""
from __future__ import annotations

from ..assets import BACKING_SERVICE_ROOT
from ..backends import python_package_name
from ..catalog import CATALOG
from ..selection import Selection
from ..services import App, services_of, web_apps
from ..targets import managed
from ..tooling import service_qualifier
from .shared_packages import NODE_DEPS, PACKAGES, node_workspace

# What a generated project calls the document, per transport — the extension differs because Go's is
# hand-written YAML and the two exported ones are what their frameworks hand over: JSON.
DOCUMENTS: dict[str, str] = {
    "fastify": "openapi.json",
    "fastapi": "openapi.json",
    "net-http": "openapi.yaml",
}

# The workspace package the browser app's typed client lives in. One name, spelled here, because the
# Makefile target, the manifest and the generated import all have to agree on it.
API_CLIENT = f"{PACKAGES}/api-client"
# And what npm calls it. Not under the project's own name the way the deployables are: this package is
# imported by other workspace code, and Biome sorts an import block by source, so a name that carried
# the project's would put the import somewhere different in every project — a formatter verdict no
# shipped file could satisfy for every name. The scope is the directory it lives in, which is where
# a reader looks for it, and it sorts first among the scoped packages any project of this factory has.
API_CLIENT_NAME = "@packages/api-client"


def api_client_package(project_name: str) -> str:
    """The npm name of this project's typed client — the same in every project, for the reason above."""
    del project_name  # every other workspace package carries it; see `API_CLIENT_NAME` for why this does not
    return API_CLIENT_NAME


# The committed document itself, per transport: which backend's assets hold it, and the two shapes it
# comes in. Two files rather than one with a marked region, because JSON has no comments to mark with —
# and the difference is one route, which a project either serves or does not. Which one is chosen is the
# condition that decides whether the flag route exists at all (`flag_route`), so the published contract
# and the running service cannot disagree about it.
DOCUMENT_ASSETS: dict[str, tuple[str, str, str]] = {
    "fastify": ("typescript", "openapi.json", "openapi-flags.json"),
    "fastapi": ("python", "openapi.json", "openapi-flags.json"),
}


def published_document(selection: Selection, target: str) -> dict[str, str]:
    """The committed API document this service publishes, keyed relative to the service.

    Committed rather than written on first run, because `make verify` checks it: a project whose gate
    passed only after somebody remembered to run `make openapi` would be a project whose gate is a chore.
    `name_service` puts the project's own name in it, the way it does for the app and the config.
    """
    for transport, (backend, plain, flagged) in DOCUMENT_ASSETS.items():
        if not selection.has(transport):
            continue
        source = flagged if managed(CATALOG, target) else plain
        return {"openapi.json": (BACKING_SERVICE_ROOT / backend / source).read_text()}
    return {}


def document_of(service: App) -> str | None:
    """Where this service's published document sits, or None for a transport that publishes nothing."""
    name = DOCUMENTS.get(service.transport or "")
    return f"{service.path}/{name}" if name is not None else None


# How each transport writes its document out, keyed by the feature that answered the axis: `{path}` is the
# service's directory and `{package}` its importable module where the language has one. A table rather than
# a branch per transport, so a fourth exporter is a row — `--silent` because npm prints the script it is
# about to run, and a gate's output should be the difference it found and nothing else.
EXPORTERS: dict[str, str] = {
    "fastify": 'npm --workspace {path} run --silent openapi -- "$$out"',
    "fastapi": 'PYTHONPATH={path}/src uv run --project {path} --no-sync python -m {package}.openapi "$$out"',
}


def export_command(project_name: str, service: App) -> str | None:
    """How to write this service's document to `$out`, without binding a port.

    The path is a variable rather than a constant, because the gate writes to a scratch file and compares:
    a check that overwrote the committed document to see whether it had changed would have changed it.
    """
    template = EXPORTERS.get(service.transport or "")
    if template is None:
        return None
    package = python_package_name(service_qualifier(project_name, service))
    return template.format(path=service.path, package=package)


def exporting(project_name: str, apps: list[App]) -> list[App]:
    """Every service whose document the factory can write out of the app itself."""
    return [s for s in services_of(apps) if export_command(project_name, s) is not None]


def marked(service: App, recipe: str) -> str:
    """One recipe line inside its service's transport region, for the pruner to take away with it."""
    begin = f"# backing-service:{service.transport}:begin\n"
    return f"{begin}{recipe}# backing-service:{service.transport}:end\n"


def openapi_targets(project_name: str, apps: list[App]) -> str:
    """`make openapi` and `make check-openapi`, or nothing at all where no service exports a document.

    `check-openapi` writes to a temporary file rather than into the tree, so a failing gate leaves the
    repository exactly as it found it — a check that has to be cleaned up after is a check people learn to
    skip.

    Every recipe line sits inside its own service's transport region, so dropping the transport takes the
    line with it and leaves a target that does nothing rather than one naming a workspace that is gone. The
    two targets themselves are unmarked on purpose: `verify` names `check-openapi`, and a prerequisite that
    stopped existing is a broken Makefile, while a target with no recipe simply passes.
    """
    services = exporting(project_name, apps)
    if not services:
        return ""
    writes = "".join(
        marked(service, f"\t@out={document_of(service)}; {export_command(project_name, service)}\n")
        for service in services
    )
    checks = "".join(
        marked(service, f"""\t@out=$$(mktemp); {export_command(project_name, service)}; \\
\t\tif ! diff -q {document_of(service)} "$$out" > /dev/null; then \\
\t\t\techo 'check-openapi: {document_of(service)} no longer matches the routes; run `make openapi`'; \\
\t\t\tdiff -u {document_of(service)} "$$out" || true; rm -f "$$out"; exit 1; \\
\t\tfi; rm -f "$$out"
""")
        for service in services
    )
    client = ""
    if web_apps(apps):
        # The typed client is a build output rather than a committed file, so it is rebuilt here instead
        # of compared: `build-packages` is already a prerequisite of everything that compiles npm code.
        client = "\t@$(MAKE) --no-print-directory build-packages\n"
    # Both need the workspace installed before they run a script in it, and `node_modules/.package-lock.json`
    # is the one place this project spells `npm ci` — Make runs it once per invocation and not at all when
    # the marker is newer than the manifests. A project whose exporter is Python's has no npm to install.
    installed = f" {NODE_DEPS}" if node_workspace(apps) else ""
    return f"""
.PHONY: openapi check-openapi
openapi:{installed} ## Write each service's published API document from its own routes, and rebuild the client
{writes}{client}check-openapi:{installed} ## Fail when a committed API document no longer matches the routes
{checks}"""
