"""The Makefile's integration suites: the variables one backing service's tests need, and the targets that run them.

Split out of `makefile.py` when it reached its budget. `test-integration` and `ci` differ with and without a
real backing service, and both are spelled once, with the difference held in a variable that has a `?=`
fallback — a marked block per branch cannot work, because a prune only ever subtracts and the branch cut at
generation time is gone for good. One variable per application: `INTEGRATION_TEST` for the first,
`INTEGRATION_TEST_<NAME>` after, each in its own store's marked region, and a store's own variables (the
database address) once however many services use it. The applications that existed before the method did
are on the same list, with the integration command their build recorded (`native_commands.gated`).
"""
from __future__ import annotations

from ..services import App
from ..tooling import app_tooling
from .native_commands import steps

# The Make variables one feature's own service needs, keyed by that feature. Where it is addressed and what
# a real one buys are facts about the product, so they are written per feature — but *whether* any of it is
# emitted, and under which marker name, is read off the selection below. A second container-backed store is
# a row here.
SERVICE_VARIABLES = {
    "postgres": """# Matches docker-compose.yml. Override for another database: make test-integration DATABASE_URL=...
DATABASE_URL ?= postgres://app:app@localhost:5433/app
export DATABASE_URL

# With Postgres, integration means the event-store contract against a real database, and `ci` applies the
# migrations before running it.""",
}


def integration_variables(services: list[App], apps: list[App], per_service: list[dict[str, str]]) -> str:
    """`INTEGRATION_TEST` per service, and each container-backed store's variables once.

    `test-integration` and `ci` differ with and without a real backing service, and both are spelled ONCE,
    with the difference held in a variable that has a `?=` fallback. The obvious alternative — a marked
    block per branch, one of them removed — cannot work: a prune only ever subtracts, so the branch cut at
    generation time is gone and no later prune can bring it back. `:=` inside the block wins while the
    service is present; delete the block and the `?=` below takes effect. One target, one recipe, and a
    generated project that still has a working `make test-integration` after `./init --event-store memory`.

    One variable per service — `INTEGRATION_TEST` for the first, `INTEGRATION_TEST_<NAME>` after — each in
    its own store's marked region, and a store's own variables (the database address) once however many
    services use it.
    """
    text = ""
    declared: list[str] = []
    for service, commands in zip(services, per_service, strict=True):
        integration = service.selection.integration_feature
        if integration is not None:
            variables = "" if integration in declared else f"{SERVICE_VARIABLES[integration]}\n"
            declared.append(integration)
            real = app_tooling(service, apps, integration)["integration"]
            text += f"""
# backing-service:{integration}:begin
{variables}INTEGRATION_TEST{service.suffix} := {real}
# backing-service:{integration}:end
"""
        text += f"INTEGRATION_TEST{service.suffix} ?= {steps(commands['integration'])[-1]}\n"
    return text


def integration_targets(services: list[App], per_service: list[dict[str, str]]) -> str:
    """`test-integration`: the one service's suite, or one target per service and an aggregate."""
    header = (
        "## Run the integration suite; against a real database it needs `make services-up migrate` first"
        if any(s.selection.integration_feature is not None for s in services)
        else "## Run native integration tests (an empty integration suite is valid initially)"
    )
    if len(services) == 1:
        setup = "".join(f"\t{line}\n" for line in steps(per_service[0]["integration"])[:-1])
        return f"test-integration: {header}\n{setup}\t$(INTEGRATION_TEST)\n"
    text = f"test-integration: {' '.join(f'test-integration-{s.name}' for s in services)} {header}\n"
    for service, commands in zip(services, per_service, strict=True):
        setup = "".join(f"\t{line}\n" for line in steps(commands["integration"])[:-1])
        text += (
            f"test-integration-{service.name}: ## Run {service.name}'s integration suite\n"
            f"{setup}\t$(INTEGRATION_TEST{service.suffix})\n"
        )
    return text
