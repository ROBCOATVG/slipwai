"""The HTTP driving adapter factory.

A driving adapter parses untrusted input into typed commands, calls a use case, and renders the
outcome. It holds **no business rules** and makes **no authorisation decision** — authorisation
is decided inside the use case, because a rule enforced in a route handler is a rule that a
second entry point will not enforce.

"Parses untrusted input" is the schema's job and not a handler's. Every route here declares what
it accepts and what it answers with, as Pydantic models FastAPI reads: the request is validated
before the handler runs, the response is serialised *through* the model, so a field the contract
does not name cannot leave this process however a handler is later edited, and the same models are
what ``/openapi.json`` publishes. A route annotated ``dict[str, Any]`` accepts anything and returns
whatever it happens to hold, which is the state this replaces.

Status mapping belongs here precisely because the domain speaks business vocabulary:

  - 400 — schema failure: the shape is wrong
  - 422 — business rejection: the shape is fine, the rule says no
  - 404 — not found, INCLUDING another tenant's resource, so existence is not leaked
  - 409 — a conflict the caller may retry differently, which is where a version conflict from
    the event store surfaces: the store returns it as a value, and this is the layer that
    gives it a status

Deliberately no ``from __future__ import annotations`` in this file, and in none of the route
modules a slice adds beside it. FastAPI reads a handler's annotations at run time with
``get_type_hints`` to decide what is a body, what is a query parameter and what the response is
serialised through; that import turns every annotation into a string, and a string naming a model
defined anywhere ``get_type_hints`` cannot see — inside a function, most of all — resolves to
nothing. FastAPI does not fail on that: it silently treats the parameter as a query parameter,
and the route answers the wrong shape. Every annotation here works unquoted on the Python this
service pins.
"""

import logging
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from typing import Literal, Protocol

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel

#: Anything that has to live as long as the process: FastAPI enters it on start-up and leaves it
#: on shutdown. Typed here rather than imported from Starlette, so this file needs no import of a
#: private module — and the one thing that uses it, the projections lifespan, is an ordinary
#: `@asynccontextmanager`.
Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]

#: A registrar mounts a slice's routes onto the app. Slices are registered from the composition
#: root, so this file never grows a list of the application's features.
RouteRegistrar = Callable[[FastAPI], None]

#: What the published document calls this service: the top level of this module's own package, which
#: is named after the project. Derived rather than written down, so there is no second spelling to
#: keep in step.
SERVICE_NAME = (__package__ or "service").split(".")[0]


class Health(BaseModel):
    """What ``/health`` answers.

    A model rather than a bare dict, so the probe's contract is validated on the way out and
    published with every other route's.
    """

    status: Literal["ok"]


class FlagSnapshot(Protocol):
    """Just enough of the flag reader's `FlagSource` for this file to serve one.

    Structural rather than imported: the reader exists only in a project with
    somewhere to deploy, so importing it here would not run in one without. A
    protocol means this file is the same in every project and is exercised by
    its own tests either way — while a project with no flags never passes a
    source, and then has no `/api/flags` route rather than an inert one.
    """

    def snapshot(self) -> dict[str, str]:
        """Every flag this environment carries, by key."""


#: What a browser is told to enforce on every response, whatever the route.
#:
#: Written out rather than taken from a package: these four headers are four strings, and the one
#: dependency that would supply them would also supply thirty settings this project has not decided.
#: `nosniff` is the one that matters most for a JSON API — without it a browser may decide a
#: response is HTML because of what is inside it, and runs what it finds. The rest are cheap
#: insurance that
#: matters the day a route starts returning HTML: an error page, a hosted callback, a rendered
#: receipt. Turning them on later is a change nobody remembers to make.
#:
#: HSTS is deliberately absent. It is a promise about a *domain* that a browser then refuses to let
#: anybody take back for as long as it was given for, and a starter cannot know whether this service
#: owns its domain or shares one. Add it where the deployment is known.
SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "content-security-policy": "default-src 'none'; frame-ancestors 'none'",
}


def build_app(
    registrars: Sequence[RouteRegistrar] = (),
    flags: FlagSnapshot | None = None,
    lifespan: Lifespan | None = None,
    cors_origins: Sequence[str] = (),
) -> FastAPI:
    """Build the app.

    `lifespan` is FastAPI's own hook for anything that has to run for as long as the process
    does, and it is where a catch-up subscription belongs: started when the app starts, stopped
    when it stops, with no thread this project has to remember to join. A project maintaining
    an `async` read model passes
    `maintaining_projections(store, checkpoints, [view])`, which an event-sourced project ships
    with its read side. A project whose read models are all `live` or `inline` passes nothing,
    and nothing runs.
    """
    # `docs_url=None` and friends are deliberately not set: interactive docs are a choice a
    # project makes, and turning them off in a starter hides the one thing that makes a new
    # API explorable. `/openapi.json` is the document itself — what a browser app generates a
    # client from and what a test asserts the contract against — and `/docs` is the same document
    # with a page around it.
    app = FastAPI(title=SERVICE_NAME, version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Callable) -> Response:
        """Put `SECURITY_HEADERS` on every response, including the ones handlers never see."""
        response: Response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    # Who is allowed to ask this service for anything at all, from a browser.
    #
    # Empty is the default and means *no* CORS headers are sent to anybody, which is same-origin
    # only. That is the right answer for `make dev` and `make demo`: the browser app is served from
    # its own origin and the dev server forwards `/api` here, so nothing is cross-origin and nothing
    # needs permitting.
    #
    # `CORS_ALLOWED_ORIGINS` names the exact origins that may. There is deliberately no `*`: a
    # wildcard and credentials cannot be combined at all, and a wildcard without them still hands
    # every page on the internet a reader for whatever this service answers unauthenticated. An
    # origin this service does not recognise gets a reply with no `access-control-allow-origin`
    # header, and the browser refuses it — which is the enforcement, since CORS is a rule browsers
    # apply and not one this process can apply on their behalf.
    #
    # Registered only where there is an origin to allow, so a project that permits none has no
    # middleware to step through rather than one that always answers no.
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(404)
    async def not_found(_request: Request, _exception: Exception) -> JSONResponse:
        """Answer a 404 without repeating the path that was asked for.

        Starlette's default 404 body is the bare string `Not Found`, which is already safe —
        but a handler that echoes `request.url` is a one-line change away, and it is the kind
        of change nobody notices. Fixing the shape here makes the 404 explicit and consistent
        with the mapping above.

        That mapping promises another tenant's resource is indistinguishable from one that
        never existed, and a handler that reflects the path undercuts the promise. For any
        project whose URLs carry a credential — a no-login link, a password-reset path, a
        signed download — the 404 is the disclosure, and it discloses to whoever probed for it.

        The reply says nothing the caller did not already know: no path, no method, no hint
        whether the route exists under a different verb.
        """
        return JSONResponse(status_code=404, content={"error": "notFound"})

    @app.exception_handler(RequestValidationError)
    async def schema_failure(_request: Request, exception: RequestValidationError) -> JSONResponse:
        """Report a schema failure in one shape, whichever route found it.

        FastAPI's default is a 422 carrying the full error list, including the input that
        failed. That input is exactly what must not be echoed when a field holds a token or a
        password, so the reply is narrowed to the first field and its message.
        """
        first = exception.errors()[0] if exception.errors() else {}
        # The first element of `loc` names where the value came from — body, query, path,
        # header, cookie — not the field. Dropping it leaves the caller with the field path
        # they actually sent, which is the only part they can act on.
        parts = [str(part) for part in first.get("loc", ())]
        if parts and parts[0] in {"body", "query", "path", "header", "cookie"}:
            parts = parts[1:]
        location = parts
        return JSONResponse(
            status_code=400,
            content={
                "error": "schemaValidationFailed",
                "field": ".".join(location) or "(root)",
                "message": str(first.get("msg", "invalid request body")),
            },
        )

    # Liveness: this process is up and answering. Unconditional on purpose — it asks nothing
    # of any dependency, because a liveness probe that fails when a database is unreachable
    # gets the process restarted when the only thing wrong is somewhere else. What gates
    # traffic is `/ready`, which `readiness()` below registers.
    @app.get("/health", response_model=Health)
    async def health() -> Health:
        return Health(status="ok")

    if flags is not None:
        # This environment's flags, for the browser app — which cannot read them
        # itself.
        #
        # Under `/api` because that is this service's product surface and a
        # browser calls it; `/health` sits outside it, being a probe.
        # `vite.config.ts` forwards `/api` with the prefix intact and
        # CloudFront's `/api/*` behaviour rewrites nothing, so this is the one
        # path in both places.
        #
        # `no-store` because the answer is what the environment is set to *now*:
        # a flipped flag that a cache still hides is the flip looking broken.
        # Declared as `dict[str, str]` rather than returned as a bare `JSONResponse`, so the route
        # has a response model the document carries — a hand-built response is a route FastAPI
        # cannot describe.
        @app.get("/api/flags", response_model=dict[str, str])
        async def feature_flags(response: Response) -> dict[str, str]:
            response.headers["cache-control"] = "no-store"
            return flags.snapshot()

    for register in registrars:
        register(app)

    # One span per request, continuing whatever `traceparent` the caller sent, and the reason
    # `trace_ids()` has anything to answer with. Instrumented here rather than by starting the
    # process a particular way (`opentelemetry-instrument`), because this app is built by a
    # function tests call directly: middleware on the instance is instrumentation a test can
    # drive, and a launcher wrapper is instrumentation that only exists in production.
    #
    # Last, so a slice's own routes are instrumented too. The tracer it takes is a no-op until
    # `main` installs a provider — see `tracing.py` for why that happens after the environment
    # is checked and before anything binds.
    FastAPIInstrumentor.instrument_app(app)

    return app


class Ready(BaseModel):
    """What ``/ready`` answers when the driven ports answer: the service will take traffic."""

    status: Literal["ready"]


class Unready(BaseModel):
    """And what it answers when one does not.

    ``reason`` is a *category* and never the driver's own message: a declared model is what keeps
    it that way, because the body is validated on the way out and a connection string a later edit
    reaches for cannot leave the process.
    """

    status: Literal["unready"]
    reason: Literal["eventStore"]


class ReadinessProbe(Protocol):
    """Just enough of the event-store port for this module to probe one.

    Structural rather than imported, for the reason `FlagSnapshot` above is and a stronger one:
    this module is the HTTP adapter of *any* project on this transport, and a project on the
    standard profile has no event store and no port to import.

    `head()` and nothing else. It is the cheapest honest question the port already answers — the
    last global position in the log, or zero when it is empty — so a readiness probe needs no
    method of its own and the port is not widened to carry one. A store that cannot answer it
    cannot serve a request either.
    """

    def head(self) -> int:
        """The last global position in the log."""


def readiness(store: ReadinessProbe | None = None) -> RouteRegistrar:
    """`/ready`: whether this service should be sent traffic.

    A different question from whether it is running. `/health` above is liveness — the process
    is up and answering — and it is deliberately unconditional: a probe that goes red because a
    dependency is down gets the process killed rather than taken out of the pool. This one asks
    the driven port the service cannot work without, **through the port** and never through an
    adapter, so an event store that has gone away is reported as "do not send me traffic"
    instead of staying invisible until the first real request fails.

    A registrar rather than a route inside `build_app`, because the store is the composition
    root's to open and hand over, and `build_app` is shared with every project on this transport
    — including the ones with no store to hand it. Those call `readiness()` with nothing and get
    a route that answers ready with no dependency to ask, which is the truth for a project whose
    only driven port is the clock.

    The failure reason is logged and not sent. A caller learns the category and no more: what is
    wrong with this service's dependencies is not something an unauthenticated prober needs, and
    a connection string in a driver's error message is exactly what would otherwise end up in one.
    """

    def register(app: FastAPI) -> None:
        # A plain `def`, so FastAPI runs it in a worker thread: the port is synchronous, and
        # awaiting nothing on the event loop while a driver blocks would stall every other
        # request behind a probe.
        #
        # Models rather than a hand-built `JSONResponse`, so both answers are in the published
        # document like every other route's — and so the 503 body is validated on the way out.
        @app.get("/ready", responses={503: {"model": Unready}})
        def ready(response: Response) -> Ready | Unready:
            response.headers["cache-control"] = "no-store"
            if store is not None:
                try:
                    store.head()
                except Exception:
                    logging.getLogger(__name__).exception(
                        "the event store did not answer; reporting not ready"
                    )
                    response.status_code = 503
                    return Unready(status="unready", reason="eventStore")
            return Ready(status="ready")

    return register
