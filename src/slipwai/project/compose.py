"""`docker-compose.yml`: the app's own services and browser apps, beside whatever backing services were selected."""
from __future__ import annotations

from ..backends import BACKEND_TOOLING, COMPOSE_CACHES, WEB_COMPOSE_CACHES
from ..probes import ready_path
from ..services import App, containers_of, first_transport, services_of, web_apps
from ..tooling import for_app

# Where a backing service answers *inside this network*, per feature, for the app service that reads it.
# `localhost:5433` is the host's published port and nothing a container can reach, so the address here is
# the Compose service name and the container port.
#
# Written by the factory rather than put in a marked region, and the difference matters: this block already
# sits inside the transport's region, the pruner refuses a nested marker, and an unmarked line would
# survive `./init --event-store memory` naming a container the same prune had just deleted. So the removal
# is a row in `SERVICE_ENVIRONMENT` in assets/backing-services/prune.py instead — the mechanism
# `PACKAGE_EDITS` already uses to take a dependency away with the answer that added it. The factory's test
# suite asserts the two agree.
CONTAINER_ADDRESSES = {"postgres": ("DATABASE_URL", "postgres://app:app@postgres:5432/app")}


def service_block(service: App) -> str:
    """One service's Compose entry, inside its own transport's marked region."""
    tooling = BACKEND_TOOLING[service.backend]
    caches = "".join(f"      - {for_app(path, service.path)}\n" for path in COMPOSE_CACHES[service.backend])
    # `make dev` directly where the image already has Make, and through a shell where it does not. Spelled
    # from the same table the CI job reads, so the two containers cannot disagree about what this image is
    # missing. The first service's target is `dev`, every other's is `dev-<name>` — see `makefile.py`.
    setup = tooling["container_setup"]
    target = service.dev_target
    # Anything this backend's toolchain needs told about running inside a mounted checkout. Empty for
    # every backend whose build output can simply be masked by a volume.
    toolchain_environment = "".join(
        f"      {name}: '{value}'\n" for name, value in tooling["container_environment"].items()
    )
    command = f"['sh', '-c', '{setup} && make {target}']" if setup else f"['make', '{target}']"
    # The store's address inside this network, where the answer needs one. The composition root opens the
    # store from it, and `/ready` is what reports whether that worked — which is why there is no
    # `depends_on` here: a service that starts before the database is not broken, it is not ready yet, and
    # the healthcheck below is what waits.
    addresses = "".join(
        f"      {name}: '{value}'\n"
        for feature, (name, value) in CONTAINER_ADDRESSES.items()
        if service.selection.has(feature)
    )
    probe = ready_path(service.backend)
    return f"""  # backing-service:{service.transport}:begin
  # The service. `make {target}` here is the same command, in the same image, that CI runs the gate in.
  #
  # It answers {probe} and 404s everything else until a slice adds a route.
  {service.name}:
    image: {tooling["ci_image"]}
    # In the `app` profile, so a plain `docker compose up` — what `make services-up` runs — still starts
    # only the backing services. `make demo` enables the profile and starts everything.
    profiles: ['app']
    working_dir: /workspace
    command: {command}
    environment:
      HOST: '0.0.0.0'
      PORT: '{service.port}'
{addresses}{toolchain_environment}    ports:
      - '${{{service.port_variable}:-{service.port}}}:{service.port}'
    volumes:
      - .:/workspace
{caches}    healthcheck:
      # Readiness, not liveness: `make demo` returns when the app is actually able to serve — which
      # includes reaching the event store — rather than when the container exists or the process happens
      # to be listening. The generous window is the first run installing dependencies inside the
      # container, and the database coming up beside it; later runs pass on the first probe.
      test: ['CMD-SHELL', 'curl -fsS http://localhost:{service.port}{probe} > /dev/null']
      interval: 5s
      timeout: 3s
      retries: 60
      start_period: 20s
  # backing-service:{service.transport}:end
"""


def web_block(web: App, apps: list[App]) -> str:
    """One browser app's Compose entry, proxying `/api` to its service inside that service's transport's region."""
    caches = "".join(f"      - {for_app(path, web.path)}\n" for path in WEB_COMPOSE_CACHES)
    api = web.api_service(apps)
    proxy_environment = f"""      # backing-service:{api.transport}:begin
      # Where the dev server sends /api. A container's `localhost` is itself, so this names the service.
      API_ORIGIN: http://{api.name}:{api.port}
      # backing-service:{api.transport}:end
""" if api is not None else ""
    return f"""  # The browser app, served by Vite over the mounted checkout, so an edit is visible on save.
  {web.name}:
    image: {BACKEND_TOOLING["typescript"]["ci_image"]}
    profiles: ['app']
    working_dir: /workspace
    command: ['make', '{web.dev_target}']
    environment:
{proxy_environment}      # Vite binds localhost by default, on purpose — a dev server should not be on the LAN. In here
      # localhost is the container, so the published port would reach nothing.
      WEB_HOST: '0.0.0.0'
    ports:
      - '${{{web.port_variable}:-{web.port}}}:{web.port}'
    volumes:
      - .:/workspace
{caches}    healthcheck:
      test: ['CMD-SHELL', 'curl -fsS http://localhost:{web.port}/ > /dev/null']
      interval: 5s
      timeout: 3s
      retries: 60
      start_period: 20s
"""


def app_services(apps: list[App]) -> str:
    """The app's own Compose services, written in place of the file's `__APP_SERVICES__` line.

    Generated rather than marked, because *which* image and cache paths a service needs is a property of
    its backend, and a marker can only express the presence or absence of a feature. Every service and
    browser app runs `make dev` / `make dev-web` in the image CI already uses, over the mounted checkout: no
    Dockerfile to keep in step with the app's layout, no build step between an edit and a demo, and no
    second definition of how this project starts.

    One block per service that has a transport, each inside its own transport's marked region — two
    services on different frameworks are two regions — and one per browser app, each proxying `/api` to the
    service it names.
    """
    blocks = [service_block(s) for s in services_of(apps) if s.transport is not None]
    blocks += [web_block(web, apps) for web in web_apps(apps)]
    return "\n".join(blocks) + ("\n" if blocks else "")


def composed(apps: list[App]) -> bool:
    """Whether this project has anything to compose: a container, a service to run, or a browser app."""
    return bool(containers_of(apps)) or first_transport(apps) is not None or bool(web_apps(apps))
