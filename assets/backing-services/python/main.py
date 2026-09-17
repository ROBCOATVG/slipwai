"""The process that listens. `make dev` runs this; nothing else in the service binds a socket.

It is deliberately the only untested module in `apps/service`. Everything worth asserting
about the routes is asserted against the app ``build_app()`` returns, driven by a test client
with no socket at all — a test that needs a listening port is an integration test wearing an
entry point's clothes, and it proves the one thing this module does rather than anything the
app decides. What is left here is composition: read the environment, build the app, bind, and
let uvicorn report the address.

HOST defaults to ``0.0.0.0`` rather than to localhost because this process runs inside a
container as often as beside you, and a server bound to 127.0.0.1 in a container is reachable
from nothing: the published port answers, the connection is refused, and nothing in the logs
says why. Bind narrowly in a real environment by setting HOST there, where the network is
known.

Nothing here reads ``os.environ``. The environment is one model — ``settings.py`` — checked
before anything binds, so a variable this service cannot use stops the process with the
variable named. PORT carries the default ``.env.example`` writes down, and the model is where
it is written. The app object is passed to uvicorn
directly rather than as an import string, because a string is what ``--reload`` needs and
reload is not what a demo wants: it would restart the process under the actor mid-click.
"""

from __future__ import annotations

import logging
import sys

import uvicorn

__STORE_IMPORT__
from .adapters.driving.http.app import __APP_IMPORTS__
__FLAGS_IMPORT__
from .logging_setup import configure_logging
from .settings import __SETTINGS_IMPORTS__
from .tracing import start_tracing


__STORE_OPEN__
def main() -> None:
    # First, so that anything start-up says is already in this process's one shape.
    configure_logging()
    # The environment, checked once and before anything binds. `os.environ` is not read anywhere
    # below: a variable this service cannot use stops the process here, with the variable named,
    # rather than surfacing as a 500 an hour later.
    try:
        settings = load_settings()
    except ConfigurationError as refusal:
        print(refusal, file=sys.stderr)
        raise SystemExit(1) from refusal
    # After the environment is checked and before anything binds: the endpoint is read off the
    # settings model rather than `os.environ`, and no request exists yet to miss its span. See
    # `tracing.py` for why the exporter is the part that waits to be asked for.
    tracing = start_tracing(
        settings.otel_service_name or SERVICE_NAME,
        settings.otel_exporter_otlp_endpoint or None,
    )
    logging.getLogger(__name__).info(
        "service starting", extra={"service": SERVICE_NAME, "exporting_traces": tracing.exporting}
    )
    # A flag source, where this project has one, is handed in here and nowhere
    # else — so `build_app` needs no import of a module a project with nowhere to
    # deploy does not have, and `/api/flags` exists exactly where a flag can be
    # declared.
    #
    # `readiness` is the other thing this module hands over: the store, so
    # `/ready` can ask the port whether this service should be sent traffic. A
    # project with no event store passes nothing and gets a route that answers
    # ready with no dependency to ask.
    uvicorn.run(
        build_app(
            [readiness(__STORE_ARGUMENT__)],
__FLAGS_ARGUMENT__
            cors_origins=settings.cors_origins(),
        ),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        # Uvicorn installs a dictConfig of its own unless told not to, and that configuration
        # replaces the handlers on `uvicorn`, `uvicorn.error` and `uvicorn.access`. `None` leaves
        # `configure_logging` as the only configuration in the process, so an access line comes out
        # in the same shape as everything else rather than in Uvicorn's.
        log_config=None,
    )
    # uvicorn.run blocks until the server stops, so this is the end of the process: whatever is
    # still batched is flushed here rather than dropped. A collector that has gone away is a
    # warning inside `shutdown`, never a traceback on the way out.
    tracing.shutdown()


if __name__ == "__main__":
    main()
