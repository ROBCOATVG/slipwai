"""The prose that explains the selected adapters: the README sections and what each gate proves.

It sits apart from `backing_services.py` for the reason `service_layouts.py` does — the tables are most of
the bytes and none of the behaviour, and a module holding both outgrows what anybody wants to read at once.
`backing_services.py` had grown past check-structure's module budget saying exactly that.

The split is also where the readers are. Nothing here writes a file: `project/readme.py` asks for the
README section and `project/docs.py` for the gate section, while the half left behind is read by
`scaffold.py` and the per-language modules. Every table is keyed by the feature that answered an axis
rather than tested for by name, so a second event store or a second identity provider is a row and not a
branch.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..services import (
    App,
    axes_of,
    containers_of,
    features_of,
    prunable_features_of,
    services_of,
    transports_of,
)
from ..toolkit import spoken_for

# What each store needs running, per feature. A store is one answer to one axis, so exactly one of
# these is ever emitted — which is why the section is looked up by the feature that answered the axis
# rather than tested for by name, and why a second container-backed store is a row here.
EVENT_STORE_README = {
    "postgres": """
<!-- backing-service:postgres:begin -->
### Postgres — the event store

```sh
make services-up       # start Postgres and wait for it to accept connections
make migrate           # apply the event-store migrations
make test-integration  # the event-store contract against real Postgres, plus a genuine race
```

The in-memory and file-backed stores cannot race, so they cannot prove that two concurrent appends at the
same version produce exactly one winner. That proof lives in `make test-integration`, and it is the reason
to choose Postgres. Demo on memory, ship on Postgres.

A schema change is two migrations in two deployments: first the additive one (a new table, a nullable
column, a column with a default), which the release already running can live with; then, once nothing
reads or writes the old shape, the one that removes it. The second names the first in a comment line —
`-- contract: 202609151030_orders_add_status` — and `make check-migrations` refuses a drop, rename, type change or
new NOT NULL column that is unmarked, or whose expand arrives in the same change. Rolling back a release
never rolls back the schema; this is what makes that safe. A new migration is named by a timestamp,
`202609151030_orders_add_status.sql` (`date -u +%Y%m%d%H%M`), so two slices built at once never mint the same
name; the shipped ones are numbered, and every stamp sorts after every number, so the order is lexical either way.
<!-- backing-service:postgres:end -->
""",
    "sqlite": """
<!-- backing-service:sqlite:begin -->
### SQLite — the event store

A real append-only log in one file, with nothing to start and nothing to migrate: the schema ships with the
adapter, because an embedded database is created by the process that opens it. `make verify` runs the shared
event-store contract against it, so the guarantees it does hold are proved on every commit.

What it does not hold: **SQLite serialises writers**, so it cannot prove concurrent behaviour — it never
genuinely races. It proves durability and it proves the log refuses to be rewritten. If the
never-write-the-same-version-twice guarantee matters to your product, move to Postgres and prove it there.
<!-- backing-service:sqlite:end -->
""",
}


# Where each store's guarantees are proved, per feature — inside the Docker-free gate or outside it.
# Looked up by the feature that answered the axis for the same reason the README sections are.
EVENT_STORE_GATES = {
    "sqlite": """
<!-- backing-service:sqlite:begin -->
The SQLite event store is inside that gate, not outside it: it needs no container, so `make verify` runs the
full event-store contract against real SQL, plus the two things only a file-backed store can prove — that
the log survives the process, and that the database itself refuses an UPDATE or a DELETE. What it cannot
prove is concurrency: SQLite serialises writers, so it never races.
<!-- backing-service:sqlite:end -->
""",
    "postgres": """
<!-- backing-service:postgres:begin -->
`make test-integration` is the other half, and it needs a real database: run `make services-up migrate`
first. It runs the same event-store contract the infrastructure-free adapters pass, and then the two things
only a real store can prove — that simultaneous appends at one version produce exactly one winner, and that
the log refuses to be rewritten. A test that needs the database belongs in the integration suite; anywhere
else it lands in `verify`, where it will fail on a machine with no Docker.
<!-- backing-service:postgres:end -->
""",
}


# What a project still owes for its identity provider, per feature and then per language family, with `""`
# for every family without a row of its own. Per family because saying the wrong one is worse than saying
# nothing: a framework that owns startup ships the protocol, so telling its reader to implement a flow would
# send them to hand-roll token validation beside a maintained client. Where nothing owns startup, the flow
# genuinely is a placeholder and the warning is the important part.
IDENTITY_OUTSTANDING = {
    "keycloak": {
        "java": """**The protocol flow is `quarkus-oidc`'s**, not this project's: the Authorization Code flow with
PKCE, the JWKS retrieval and the full token validation all come from the extension, and none of it should
ever be written here. It is configured in `apps/service/src/main/resources/application.properties` and
deliberately left disabled — enabled, the service refuses to boot whenever Keycloak is not up, which is a
hard dependency bought for nothing until a route needs a principal. What this project still owns is the
group-to-role mapping in `KeycloakRoles`, and naming the roles it maps.""",
        "": """**The OIDC flow itself is not implemented** — read the warning at the top of the auth
adapter first.""",
    },
}


# The README section for each identity provider, keyed by feature, with `__OUTSTANDING__` standing for the
# family's row above. Looked up by the feature that answered the axis, like the event-store tables.
IDENTITY_README = {
    "keycloak": """
<!-- backing-service:keycloak:begin -->
### Keycloak — staff identity

Keycloak imports `docker/keycloak/realms/app.json` at start-up, so the issuer at
`http://localhost:8081/realms/app` works with no console steps. `docker/keycloak/README.md` explains every
value and why none of them belongs in a real environment. __OUTSTANDING__
<!-- backing-service:keycloak:end -->
""",
}


# The same two tables for the other identity question — who authenticates the product's users — keyed by
# the feature that answered the `users` axis. Separate tables because the answers are separate: a project
# may have either realm without the other, and what each still owes differs.
USERS_OUTSTANDING = {
    "users-keycloak": {
        "java": """**Token validation is the framework's**, configured for the `customers` realm in
`apps/service/src/main/resources/application.properties` and deliberately left disabled until a route needs a
customer. What this project owns is `CustomerIdentity`: a validated token becomes a customer only if its issuer
is exactly this realm's — a staff token is a valid JWT too — and its email is verified.""",
        "": """**The service does not validate a customer's token yet** — read the warning at the top of
the users adapter first. What is written is the part this project owns: `customerFromClaims`, which refuses
any issuer but the customers realm's and any unverified email.""",
    },
}

USERS_README = {
    "users-keycloak": """
<!-- backing-service:users-keycloak:begin -->
### Keycloak — the product's users

The same Keycloak imports `docker/keycloak/realms/customers.json`: a second realm, `customers`, at
`http://localhost:8081/realms/customers`, with self-registration and password reset on and a public PKCE client
for the browser app. The login lives in `apps/web` (`src/auth/users.tsx`, react-oidc-context over
oidc-client-ts): sign in, session, silent renewal and sign out are real, and a signed-in customer's access
token carries `api` as its audience for the service. A user `customer@example.invalid` / `customer` exists
before anyone registers. __OUTSTANDING__
<!-- backing-service:users-keycloak:end -->
""",
}


def backing_services_readme(apps: list[App]) -> str:
    """The README section for whatever the services actually need running.

    Written per feature rather than as one block, because the answers are independent: a SQLite project has
    no Compose file to describe, and a Keycloak-only project has a Compose file but nothing to migrate. Each
    feature is described once however many services use it.
    """
    services = services_of(apps)
    sections: list[str] = []
    if containers_of(apps):
        sections.append("""
## Local backing services

`docker-compose.yml` starts what this project needs locally, and `make services-up` waits for every
container to report healthy before returning. `make verify` deliberately does not need any of it: the
repository gate runs each port's contract against adapters that need no infrastructure, so it stays
runnable with no Docker at all.

```sh
make services-up       # start the containers and wait for them to be healthy
make services-down     # stop them, keeping any volume
```
""")
    for store in dict.fromkeys(s.selection.feature_of("event-store") for s in services):
        if store is not None:
            sections.append(EVENT_STORE_README[store])
    for axis, readme, outstanding_by in (
        ("auth", IDENTITY_README, IDENTITY_OUTSTANDING),
        ("users", USERS_README, USERS_OUTSTANDING),
    ):
        for identity in dict.fromkeys(s.selection.feature_of(axis) for s in services):
            if identity is None:
                continue
            outstanding = outstanding_by[identity]
            # What is still owed differs per language family, so a project whose services span families
            # says each family's paragraph once.
            owed = "\n\n".join(
                dict.fromkeys(
                    spoken_for(outstanding.get(s.language, outstanding[""]), s, None)
                    for s in services
                    if s.selection.feature_of(axis) == identity
                )
            )
            sections.append(readme[identity].replace("__OUTSTANDING__", owed))
    if not sections:
        return ""
    if prunable_features_of(apps):
        flags = " ".join(
            f"--{axis} {CATALOG['axes'][axis]['absent']}"
            for axis in axes_of(apps)
            if any(s.selection.option(axis) != CATALOG["axes"][axis]["absent"] for s in services)
        )
        sections.append(f"""
### Changing your mind

`scripts/backing-services.py --list` shows what each axis can still be answered with in this project, and
`./init` takes the same flags. Pruning only ever subtracts — an adapter the factory did not emit cannot be
added back this way. The answer goes into `project.json` in the same run, so `slipwai migrate` will not
offer the dropped adapter back, and `make check-agents` names the skills it was justifying:

```sh
./init {flags}
```
""")
    return "".join(sections)


def backing_services_gates(apps: list[App]) -> str:
    """What each gate does and does not prove, per feature.

    Written per feature because the answer differs: SQLite is proved inside `make verify`, Postgres is
    proved outside it, and conflating the two is how a team ends up believing a concurrency test that
    never raced.
    """
    if not features_of(apps):
        return ""
    sections = ["""
## What `verify` deliberately does not do

`make verify` needs no Docker. Every port's contract runs against adapters that need no infrastructure, so
the gate behaves the same on a laptop with nothing installed as it does in CI.
"""]
    for store in dict.fromkeys(s.selection.feature_of("event-store") for s in services_of(apps)):
        if store is not None:
            sections.append(EVENT_STORE_GATES[store])
    for transport in transports_of(apps):
        sections.append(f"""
<!-- backing-service:{transport}:begin -->
The HTTP entry point is exercised inside `make verify` by dispatching a real request through the real
router with no socket. An entry-point test that needs a listening port is an integration test wearing the
wrong name.
<!-- backing-service:{transport}:end -->
""")
    return "".join(sections)
