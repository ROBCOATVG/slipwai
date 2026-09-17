"""This process's configuration: one model over the environment, checked before it starts.

Twelve-factor says configuration comes from the environment, which is a decision about
*where* it comes from and says nothing about *when* it is read. Read at the point of use, a
missing or misspelt value is discovered by the first request that needs it — in production,
by a customer, as a 500 naming something the operator never set. Read here, it is discovered
by the process that will not start, and the message names the variable.

``pydantic-settings`` is what does the checking, and it is Pydantic for the reason the
routes' response models are: one validation library in the service, producing the types and
the checks together, rather than a hand-written shape beside a hand-written check that can
disagree with it. Names are matched case-insensitively, so ``PORT`` in the environment is
``port`` here.

A default is how a value becomes optional: ``PORT`` unset is 3000, not a refusal. What is
deliberately NOT defaulted is anything whose wrong value is worse than its absence — an
address this service would otherwise silently publish as its own, a DSN pointing at nothing.
Those are optional and *shaped*: absent is fine, present and unusable stops the process.

``log_level`` is a plain string rather than the closed set ``logging`` accepts, on purpose:
this model holds the environment to the shapes the *service* cannot run without, and what a
level means is ``logging_setup``'s question rather than this one's.

Every field below that belongs to one backing service sits inside that service's marked
region, so ``scripts/backing-services.py`` takes the variable away with the adapter that
reads it. A variable left behind after its adapter is gone is configuration nobody can act
on.
"""

from __future__ import annotations

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """The environment this process was given, as the service is allowed to read it."""

    # `extra="ignore"` because a container's environment holds far more than this service's
    # own — PATH, HOSTNAME, whatever the orchestrator injects — and refusing those would
    # refuse every deployment.
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    # The transport's own. HOST defaults to 0.0.0.0 rather than to localhost because this
    # process runs inside a container as often as beside you, and a server bound to
    # 127.0.0.1 in a container is reachable from nothing: the published port answers, the
    # connection is refused, and nothing in the logs says why.
    port: int = Field(default=3000, ge=1, le=65535)
    host: str = "0.0.0.0"
    # The address callers reach this service on, which is not derivable from PORT — behind a
    # proxy or a tunnel they differ. Optional, because `main` falls back to the bound port;
    # shaped, because a value that is not a URL gets printed, pasted, and leads nowhere.
    public_base_url: str | None = Field(default=None, pattern=r"^https?://")
    log_level: str = "info"
    # What this service calls itself in a trace. Empty means its own package name, which
    # `main` fills in: a service that exports spans as `unknown_service` is one nobody can
    # find again, and the package is already named after the project.
    otel_service_name: str = ""
    # Where to send them, and the one thing that decides whether anything is sent at all
    # (`tracing.py`). Shaped rather than merely optional: present and not a URL stops the
    # process here instead of surfacing as an exporter that silently never connects. Empty is
    # allowed alongside absent because `.env.example` carries the variable with nothing after
    # the `=`, and an operator turning exporting off by emptying it must not stop a deployment.
    otel_exporter_otlp_endpoint: str = Field(default="", pattern=r"^(https?://.+)?$")
    # Which browser origins may call this service cross-origin, comma-separated. Empty — the default
    # — is same-origin only: no CORS headers are sent to anybody. A wildcard is deliberately not a
    # value this accepts; `adapters/driving/http/app.py` says why an allow-list is spelled out.
    cors_allowed_origins: str = ""
    # backing-service:sqlite:begin
    # Where the event log lives. A path, not a URL: SQLite is a file this process opens,
    # with no server to address.
    event_store_path: str = "./events.sqlite3"
    # backing-service:sqlite:end
    # backing-service:postgres:begin
    # The event store's DSN. Optional rather than required, because the skeleton's entry
    # point opens no store — the slice that wires one is what needs this — but shaped, so a
    # value that is not a Postgres URL is refused at start-up and not by the first append.
    database_url: str | None = Field(default=None, pattern=r"^postgres(ql)?://")
    # backing-service:postgres:end
    # backing-service:keycloak:begin
    # Staff identity. The issuer is what a token is validated against, so a wrong one
    # accepts nothing and says little; refusing the shape here is cheaper than reading it
    # out of a 401.
    oidc_issuer: str | None = Field(default=None, pattern=r"^https?://")
    # backing-service:keycloak:end
    # backing-service:users-keycloak:begin
    # Customer identity: the issuer a customer's bearer token must carry, and the audience
    # this service is.
    users_oidc_issuer: str | None = Field(default=None, pattern=r"^https?://")
    users_oidc_audience: str | None = None
    # backing-service:users-keycloak:end

    def cors_origins(self) -> list[str]:
        """The origins ``CORS_ALLOWED_ORIGINS`` names, as a list.

        Here rather than in the HTTP adapter, because reading a variable is this model's
        job and not a route's. Whitespace around a comma is dropped and an empty entry is
        not an origin: a trailing comma in a deployment's environment must not become a
        permission for the empty string, which is what an ``Origin`` header carries when a
        request has none.
        """
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


class ConfigurationError(Exception):
    """The environment this process was given cannot be used, and which variable is why."""


def load_settings() -> Settings:
    """Read and check the environment, or refuse with the variable named.

    Pydantic reports a failure against the *field*, which is the lower-cased spelling; an
    operator only ever sees the variable. Translating it here is the difference between a
    message somebody can act on and one they have to guess at.
    """
    try:
        return Settings()
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in problem['loc']).upper()}: {problem['msg']}"
            for problem in error.errors()
        )
        raise ConfigurationError(
            f"the environment this service was given cannot be used — {problems}"
        ) from error
