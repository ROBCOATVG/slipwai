"""`/api/flags`: how a browser app learns what this environment's flags are set to.

A browser cannot read this environment. A bundler inlines the values it is given while the bundle is *built*,
so a flag compiled into a bundle is a property of that build and not of the environment it runs in — which
is why a flag the browser read used to move only when the environment was deployed again, while the same
flag reached the service in a restart. Two clocks for one flag, and an ordering rule to keep them from
contradicting each other.

The service already holds the answer, and `Source.snapshot()` is it. So the service serves it, the bundle
asks, and the two halves of one flag finally move together.

Under `/api` because that is the service's product surface: the dev server forwards `/api` with the prefix
intact, and the edge's `/api/*` behaviour has no origin path and no rewrite function, so the path is the
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

from ..assets import source_text
from ..catalog import CATALOG
from ..loaded_targets import answer
from ..registry import ENTRY_WIRING, FLAG_RESOURCE, OPT_IN_FLAG_TRANSPORTS, registry
from ..selection import Selection
from ..target_protocol import FLAG_TRANSPORTS
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


def wire_entry(files: dict[str, str], target: str, backend: str) -> dict[str, str]:
    """Resolve a transport entry point's flag placeholders, in place, and hand the files back.

    The wiring is the backend's `entry_wiring` answer, keyed by the transport feature that answers the `http`
    axis: one row per transport whose app is built by a function the project owns, and none for `--http none`,
    which has no entry point to wire. The transport does not have to be named: an entry point is one
    transport's file, so the one present in `files` is the one that answered the axis. Called by each
    backend's own module, which is where the target is known.

    A project with no target has every placeholder *removed* rather than left in the file. That direction
    matters: an unresolved placeholder is the one failure mode here that would reach a generated project
    looking like the keel forgot something, since nothing downstream would reject it.
    """
    for wiring in registry().answer(backend, ENTRY_WIRING).values():
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
    """A transport whose framework discovers the route, so the route is a file and nothing else.

    `source` is relative to the backend's own `assets/backing-services/<backend>/`: the key it is answered under
    says which transport, and the backend answering it says whose."""

    destination: str
    source: str


def flag_resource(target: str, backend: str, selection: Selection) -> dict[str, str]:
    """The route as a file, for a framework that discovers one — and nothing at all without both halves.

    Two conditions rather than one. No target means nowhere to declare a flag, so the endpoint would
    answer an empty object forever; no transport means there is no HTTP adapter for it to sit in and none
    of the framework's REST types on the classpath. Either way the file is simply absent.

    The route is the backend's `flag_resource` answer, keyed by the transport feature, so the feature name is
    a key and never the thing a branch tests for (`test_an_option_s_feature_is_never_branched_on_by_name`),
    and a third framework is an answer rather than a twin of this function. There is no entry point to wire
    for these: Quarkus and Spring find a class on the classpath, exactly as they find the readiness
    contributor beside it, so not emitting the file is the whole of the conditional.
    """
    if not managed(CATALOG, target):
        return {}
    for transport, resource in registry().answer(backend, FLAG_RESOURCE).items():
        if selection.has(transport):
            package = registry().root(backend)
            source = f"backing-services/{backend}/{resource.source}"
            return {resource.destination: source_text(package / "assets", source, package)}
    return {}


# Per target: the transport every project on it has, and — where the target offers a second one — its name.
# Which backends' flag readers can actually read that one is each backend's `opt_in_flag_transports` answer.
# The default is the platform resolving the value into the container's environment,
# which every backend reads for free; the opt-in is a live re-read, which
# takes a reader written against that cloud's own service, so it is offered only where one exists. A backend
# that does not name the target can still be given the default, which is every project's and the only shape a
# project with no target has — what it cannot be given is a transport whose values it would never see. Widening
# it is one reader and the target in that backend's answer, in the same change.
def transports_of(target: str) -> tuple[str, str | None]:
    """This target's default transport and its opt-in one, or `None` where it offers only the one."""
    said = answer(target, FLAG_TRANSPORTS, default={}) or {}
    return said["default"], said.get("opt_in")

# The placeholder `assets/targets/<target>/service/variables.tf` carries.
TRANSPORTS = "__FLAG_TRANSPORTS__"


def flag_transports(backends: set[str], target: str) -> list[str]:
    """The transports every one of these backends can read, in the order the variable offers them."""
    default, opt_in = transports_of(target)
    offered = [default]
    reads = registry().answer
    if opt_in is not None and backends and all(target in reads(b, OPT_IN_FLAG_TRANSPORTS) for b in backends):
        offered.append(opt_in)
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
