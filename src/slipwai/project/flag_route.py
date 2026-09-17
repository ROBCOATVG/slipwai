"""`/api/flags`: how a browser app learns what this environment's flags are set to.

A browser cannot read this environment. Vite inlines a `VITE_`-prefixed value while the bundle is *built*,
so a flag compiled into a bundle is a property of that build and not of the environment it runs in — which
is why a flag the browser read used to move only when the environment was deployed again, while the same
flag reached the service in a restart. Two clocks for one flag, and an ordering rule to keep them from
contradicting each other.

The service already holds the answer, and `Source.snapshot()` is it. So the service serves it, the bundle
asks, and the two halves of one flag finally move together.

Under `/api` because that is the service's product surface: `vite.config.ts` forwards `/api` with the prefix
intact, and CloudFront's `/api/*` behaviour has no `origin_path` and no rewrite function, so the path is the
same in both places. `/health` stays outside it, being a probe rather than something a browser calls.

Nothing here is emitted under `--target none`, for the reason the reader is not: a project with nowhere to
declare a flag would get an endpoint that always answered `{}`, which reads as a capability it does not have.
The transports differ in how they arrive at that. Fastify, FastAPI and net/http take the source as an
argument to the app they already build — so their shell is unconditional, declares the source's shape
structurally rather than importing it, and simply never registers the route when nothing is passed; only the
entry point that constructs the app differs, through the two placeholders below. Quarkus and Spring discover
a resource class on the classpath, so for them the route *is* a file, and not emitting it is the whole of the
conditional.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..assets import BACKING_SERVICE_ROOT
from ..catalog import CATALOG
from ..selection import Selection
from ..targets import managed

# What a transport's entry point carries where the flag source is wired in. Three rather than one because
# an import cannot be written where the argument goes — ESM, Python and Go all put imports at the top of a
# file — and because a formatter decides whether the argument may share a line at all: `ruff format`
# explodes a call that already spans lines onto one argument each, so FastAPI's entry point takes the
# argument as a line of its own and everything else appends it where the call is written.
IMPORT = "__FLAGS_IMPORT__"
SOURCE = "__FLAGS_SOURCE__"
ARGUMENT = "__FLAGS_ARGUMENT__"


@dataclass(frozen=True)
class EntryWiring:
    """A transport whose app takes the source as an argument: where to wire it, and what to write.

    `absent` is what the argument becomes with no target, and it is not always nothing: Fastify's and
    FastAPI's source is an optional parameter that can simply be left off, while Go has no optional
    parameters, so its `BuildApp` takes the source as its first argument and a project with no flags
    passes `nil`.
    """

    entry: str
    line: str
    argument: str
    absent: str = ""
    #: The whole line, indentation included, for an entry point whose formatter will not let the argument
    #: share one — and it is a line rather than a fragment so a project with no target loses it entirely
    #: rather than keeping the blank it sat on. Only FastAPI's needs it; see the placeholders above.
    argument_line: str = ""


# Keyed by the transport feature that answers the `http` axis. The three whose app is built by a function
# the project owns; `--http none` has no entry point to wire and is absent for that reason.
ENTRY_WIRING: dict[str, EntryWiring] = {
    "fastify": EntryWiring(
        entry="src/main.ts",
        line="import { defaultSource } from './flags.js';",
        argument=", defaultSource()",
    ),
    # The placeholder sits where this line *sorts* in `main.py`'s import block rather than at the end of
    # it: ruff's isort rule is part of a generated Python project's own lint, and a block that ends with
    # `.flags` after `.logging_setup` is I001 — a project that fails its first `make lint` for a reason
    # nothing it can see put there.
    # `uvicorn.run` wraps `build_app`, so that call already spans lines and carries a trailing comma —
    # which is `ruff format`'s instruction to give every argument a line of its own. An argument appended
    # beside the one before it is reformatted, and a generated project's `make lint` runs the formatter in
    # check mode, so it fails there. Hence `argument_line` and no `argument`: `openapi_export.py` builds
    # the same app on one line and takes the fragment instead.
    "fastapi": EntryWiring(
        entry="src/delivery_starter/main.py",
        line="from .flags import default_source",
        argument=", default_source()",
        argument_line="            default_source(),",
    ),
    # Go imports by module path rather than relatively, so the line carries the template spelling of the
    # module — `name_service` renames it along with every other `example.com/delivery-starter` here, for
    # the same reason `FLAG_READERS` keeps its paths in the template spelling. The placeholder sits
    # between `config` and `observability` in `serve_main.go` because `gofmt` sorts the group's paths,
    # and a block that puts `flags` after `observability` is the first lint a production Go project fails.
    "net-http": EntryWiring(
        entry="cmd/serve/main.go",
        line='\t"example.com/delivery-starter/flags"',
        argument="flags.DefaultSource()",
        absent="nil",
    ),
}


def wire_entry(files: dict[str, str], target: str) -> dict[str, str]:
    """Resolve a transport entry point's flag placeholders, in place, and hand the files back.

    The transport does not have to be named: an entry point is one transport's file, so the one present in
    `files` is the one that answered the axis. Called by each backend's own module, which is where the
    target is known.

    A project with no target has every placeholder *removed* rather than left in the file. That direction
    matters: an unresolved placeholder is the one failure mode here that would reach a generated project
    looking like the factory forgot something, since nothing downstream would reject it.
    """
    for wiring in ENTRY_WIRING.values():
        if wiring.entry not in files:
            continue
        wanted = managed(CATALOG, target)
        # Every file carrying the placeholders, not only the entry point: the document exporter beside it
        # builds the app the same way the process does, so a project whose service serves `/api/flags`
        # publishes a document that describes it. The entry point is what identifies *which* transport
        # answered, and the rest of that transport's files are resolved with it.
        carried = (IMPORT, SOURCE, ARGUMENT)
        for path in [name for name, text in files.items() if any(mark in text for mark in carried)]:
            content = files[path]
            content = content.replace(f"{IMPORT}\n", f"{wiring.line}\n" if wanted else "")
            content = content.replace(f"{ARGUMENT}\n", f"{wiring.argument_line}\n" if wanted else "")
            content = content.replace(SOURCE, wiring.argument if wanted else wiring.absent)
            files[path] = content
    return files


@dataclass(frozen=True)
class Resource:
    """A transport whose framework discovers the route, so the route is a file and nothing else."""

    backend: str
    destination: str
    source: str


# Keyed by the transport feature that answers the `http` axis, so the feature name is a key and never the
# thing a branch tests for — `test_an_option_s_feature_is_never_branched_on_by_name` is the rule, and a
# third framework here is a row rather than a twin of this function. There is no entry point to wire for
# these: Quarkus and Spring find a class on the classpath, exactly as they find the readiness contributor
# beside it — so not emitting the file is the whole of the conditional.
FLAG_RESOURCES: dict[str, Resource] = {
    "quarkus-rest": Resource(
        backend="java-quarkus",
        destination=(
            "src/main/java/com/example/deliverystarter/adapters/driving/http/FeatureFlagsResource.java"
        ),
        source="http_flags_resource.java",
    ),
    "spring-web": Resource(
        backend="java-spring",
        destination=(
            "src/main/java/com/example/deliverystarter/adapters/driving/http/FeatureFlagsController.java"
        ),
        source="http_flags_controller.java",
    ),
}


def flag_resource(target: str, backend: str, selection: Selection) -> dict[str, str]:
    """The route as a file, for a framework that discovers one — and nothing at all without both halves.

    Two conditions rather than one. No target means nowhere to declare a flag, so the endpoint would
    answer an empty object forever; no transport means there is no HTTP adapter for it to sit in and none
    of the framework's REST types on the classpath. Either way the file is simply absent.
    """
    if not managed(CATALOG, target):
        return {}
    for transport, resource in FLAG_RESOURCES.items():
        if resource.backend == backend and selection.has(transport):
            root = BACKING_SERVICE_ROOT / resource.backend
            return {resource.destination: (root / resource.source).read_text()}
    return {}


# Per target: the transport every project on it has, and — where the target offers a second one — its name
# and the backends whose flag reader can actually read it. The default is the platform resolving the value
# into the container's environment, which every backend reads for free; the opt-in is a live re-read, which
# takes a reader written against that cloud's own service, so it is offered only where one exists. A backend
# absent from that set can still be given the default, which is every project's and the only shape a project
# with no target has — what it cannot be given is a transport whose values it would never see. Widening it
# is one reader and one name in the set, in the same change.
DEFAULT_TRANSPORT = {"aws": "ssm", "azure": "keyvault"}
OPT_IN_TRANSPORT: dict[str, tuple[str, frozenset[str]]] = {
    "aws": ("appconfig", frozenset({"typescript"})),
    "azure": ("appconfig", frozenset({"typescript"})),
}

# The placeholder `assets/targets/<target>/service/variables.tf` carries.
TRANSPORTS = "__FLAG_TRANSPORTS__"


def flag_transports(backends: set[str], target: str) -> list[str]:
    """The transports every one of these backends can read, in the order the variable offers them."""
    offered = [DEFAULT_TRANSPORT[target]]
    opt_in = OPT_IN_TRANSPORT.get(target)
    if opt_in is not None:
        name, readers = opt_in
        if backends and backends <= readers:
            offered.append(name)
    return offered


def wire_transports(files: dict[str, str], backends: set[str], target: str) -> dict[str, str]:
    """Resolve the transport list in the service stack's variables, in place.

    A project whose services do not all have a reader for the opt-in transport gets a one-element list, so
    `tofu` refuses the answer with the reason rather than the project discovering it as every flag reading
    off.
    """
    relative = "infra/service/variables.tf"
    if relative not in files:
        return files
    offered = ", ".join(f'"{transport}"' for transport in flag_transports(backends, target))
    files[relative] = files[relative].replace(TRANSPORTS, f"[{offered}]")
    return files
