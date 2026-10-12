"""The prose that explains the selected adapters: the README sections and what each gate proves.

It sits apart from `backing_services.py` because the two have different readers and write different things.
Nothing here writes a file: `project/readme.py` asks for the README section, `project/docs.py` for the gate
section and `project/guidance.py` for the rules, while the half left behind writes Compose, the environment
template, the prune script and the realms, and is read by `scaffold.py` and the per-language modules. One
module answering both would be asked by six callers for two unrelated things.

The budget is not the reason, though it was the reason recorded until 16.8 looked: a split made to get
under a limit is a split a reader cannot predict, and this one is predictable — ask it what a selection
*says*, ask the other what a selection *writes*. Every table is keyed by the feature that answered an axis
rather than tested for by name, so a second event store or a second identity provider is a row and not a
branch.
"""
from __future__ import annotations

from ..catalog import CATALOG, axis_prunable
from ..registry import IDENTITY_OUTSTANDING, registry
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
from .metadata import sourced

# Said once and spliced into both rungs' Postgres sections, because expand-then-contract is a rule about
# the schema and not about what the schema holds: a log's table and a state table are migrated the same way,
# and two copies of this paragraph would be two chances to describe `make check-migrations` differently.
EXPAND_THEN_CONTRACT = """A schema change is two migrations in two deployments: first the additive one (a new table, a nullable
column, a column with a default), which the release already running can live with; then, once nothing
reads or writes the old shape, the one that removes it. The second names the first in a comment line —
`-- contract: 202609151030_orders_add_status` — and `make check-migrations` refuses a drop, rename, type change or
new NOT NULL column that is unmarked, or whose expand arrives in the same change. Rolling back a release
never rolls back the schema; this is what makes that safe. A new migration is named by a timestamp,
`202609151030_orders_add_status.sql` (`date -u +%Y%m%d%H%M`), so two slices built at once never mint the same
name; the shipped ones are numbered, and every stamp sorts after every number, so the order is lexical either way."""


# What each store needs running, per feature, for a service whose truth is its log. A store is one answer to
# one axis, so a project on one rung emits exactly one of these — which is why the section is looked up by
# the feature that answered the axis rather than tested for by name, and why a second container-backed store
# is a row here. A project with services on both rungs emits one section per rung, because the commands are
# the same and what they prove is not.
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

__EXPAND_THEN_CONTRACT__
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


# The same store, for a service that keeps current state: one row per thing it owns, with the version column
# the use case saves against. Written out rather than parameterised off the table above, because almost
# every sentence differs — what is migrated, what the integration suite races, and what the in-memory
# adapter is unable to show — and a template with six holes in it is harder to read than two sections.
STATE_STORE_README = {
    "postgres": """
<!-- backing-service:postgres:begin -->
### Postgres — the state store

```sh
make services-up       # start Postgres and wait for it to accept connections
make migrate           # apply the state-table migrations
make test-integration  # the repository contract against real Postgres, plus a genuine race
```

The in-memory repository cannot race, so it cannot prove that two writers saving one row at the version
they both read produce exactly one winner. That proof lives in `make test-integration`, and it is the
reason to choose Postgres. Demo on memory, ship on Postgres.

__EXPAND_THEN_CONTRACT__
<!-- backing-service:postgres:end -->
""",
    "sqlite": """
<!-- backing-service:sqlite:begin -->
### SQLite — the state store

One file holding the current state of everything the service owns, with nothing to start and nothing to
migrate: the schema ships with the adapter, because an embedded database is created by the process that
opens it. `make verify` runs the shared repository contract against it, so the guarantees it does hold are
proved on every commit.

What it does not hold: **SQLite serialises writers**, so it cannot prove concurrent behaviour — it never
genuinely races. It proves durability, and it proves that a save at a version the row has already moved
past is refused. If a real lost-update race matters to your product, move to Postgres and prove it there.
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


# The same question for a state-stored service: which of its store's guarantees the Docker-free gate can
# actually prove. The answer differs by more than a noun — a repository has no append-only claim to make and
# its race is over a row's version — and the point of this section is that a reader can tell which
# concurrency claim they are allowed to believe.
STATE_STORE_GATES = {
    "sqlite": """
<!-- backing-service:sqlite:begin -->
The SQLite state store is inside that gate, not outside it: it needs no container, so `make verify` runs the
full repository contract against real SQL, plus the thing only a file-backed store can prove — that the
state survives the process. What it cannot prove is concurrency: SQLite serialises writers, so it never
races, and no test on it may claim two writers met at one version.
<!-- backing-service:sqlite:end -->
""",
    "postgres": """
<!-- backing-service:postgres:begin -->
The repository contract is proved the same way, in `make test-integration` against a real database: run
`make services-up migrate` first. It runs what the infrastructure-free adapter already passes, and then the
thing only a real store can prove — that two writers saving one row at the version they both read produce
exactly one winner, and the loser is told rather than quietly overwriting. A test that needs the database
belongs in the integration suite; anywhere else it lands in `verify`, where it will fail on a machine with
no Docker.
<!-- backing-service:postgres:end -->
""",
}


# What a project still owes for its identity provider when its language family has nothing of its own to say, per
# feature. A family that does answers `identity_outstanding` (a framework that owns startup ships the protocol, so
# telling its reader to implement a flow would send them to hand-roll token validation beside a maintained client).
# Where nothing owns startup, the flow genuinely is a placeholder and the warning is the important part.
IDENTITY_DEFAULT = {
    "keycloak": """**The OIDC flow itself is not implemented** — read the warning at the top of the auth
adapter first.""",
    "users-keycloak": """**The service does not validate an external token yet** — read the warning at the top of
the users adapter first. What is written is the part this project owns: `customerFromClaims`, which refuses
any issuer but the external realm's and any unverified email.""",
}


def still_owed(backend: str, identity: str) -> str:
    """What a service of this backend still owes for this identity feature: its family's paragraph, else the keel's."""
    return registry().answer_or(backend, IDENTITY_OUTSTANDING, {}).get(identity, IDENTITY_DEFAULT[identity])


# The README section for each identity provider, keyed by feature, with `__OUTSTANDING__` standing for what
# `still_owed` says. Looked up by the feature that answered the axis, like the event-store tables.
IDENTITY_README = {
    "keycloak": """
<!-- backing-service:keycloak:begin -->
### Keycloak — internal identity

Keycloak imports `docker/keycloak/realms/app.json` at start-up, so the issuer at
`http://localhost:8081/realms/app` works with no console steps. `docker/keycloak/README.md` explains every
value and why none of them belongs in a real environment. __OUTSTANDING__
<!-- backing-service:keycloak:end -->
""",
}


# The same for the other identity question — who authenticates the product's users — keyed by the feature that
# answered the `users` axis. Separate because the answers are separate: a project may have either realm without the
# other, and what each still owes differs.
USERS_README = {
    "users-keycloak": """
<!-- backing-service:users-keycloak:begin -->
### Keycloak — the product's users

The same Keycloak imports `docker/keycloak/realms/customers.json`: a second realm, `customers`, at
`http://localhost:8081/realms/customers`, with self-registration and password reset on and a public PKCE client
for the browser app. The login lives in `apps/web` (`src/auth/users.tsx`, react-oidc-context over
oidc-client-ts): sign in, session, silent renewal and sign out are real, and a signed-in external user's access
token carries `api` as its audience for the service. A user `customer@example.invalid` / `customer` exists
before anyone registers. __OUTSTANDING__
<!-- backing-service:users-keycloak:end -->
""",
}


def stores_by_rung(services: list[App]) -> list[tuple[str, bool]]:
    """Each store this project chose, paired with whether it is holding a log, in the services' order.

    A pair rather than a feature, because the store and the rung are two separate answers and the prose
    needs both: Postgres behind an event-sourced service and Postgres behind a state-stored one are the same
    container, the same `make migrate` and two different guarantees. De-duplicated on the pair, so a project
    with four services on two rungs still describes each of its two shapes once. The rung comes from
    `sourced`, which is the one place that decides it.
    """
    return [
        (store, logged)
        for store, logged in dict.fromkeys(
            (service.selection.feature_of("persistence"), sourced(service)) for service in services
        )
        if store is not None
    ]


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
    for store, logged in stores_by_rung(services):
        table = EVENT_STORE_README if logged else STATE_STORE_README
        sections.append(table[store].replace("__EXPAND_THEN_CONTRACT__", EXPAND_THEN_CONTRACT))
    for axis, readme in (("auth", IDENTITY_README), ("users", USERS_README)):
        for identity in dict.fromkeys(s.selection.feature_of(axis) for s in services):
            if identity is None:
                continue
            # What is still owed differs per language family, so a project whose services span families
            # says each family's paragraph once.
            owed = "\n\n".join(
                dict.fromkeys(
                    spoken_for(still_owed(s.backend, identity), s, None)
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
            if axis_prunable(axis)
            and any(s.selection.option(axis) != CATALOG["axes"][axis]["absent"] for s in services)
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
    for store, logged in stores_by_rung(services_of(apps)):
        sections.append((EVENT_STORE_GATES if logged else STATE_STORE_GATES)[store])
    for transport in transports_of(apps):
        sections.append(f"""
<!-- backing-service:{transport}:begin -->
The HTTP entry point is exercised inside `make verify` by dispatching a real request through the real
router with no socket. An entry-point test that needs a listening port is an integration test wearing the
wrong name.
<!-- backing-service:{transport}:end -->
""")
    return "".join(sections)

