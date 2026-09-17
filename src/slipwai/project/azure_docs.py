"""`docs/deployment.md` and `docs/adr/0002-production-target.md` for a project going to **Azure**.

The counterpart of `aws_docs.py`, and deliberately its own module rather than that one with conditionals in
it: the nodes here are Container Apps and revisions, the rows are Consumption replicas and a Flexible
Server, and the costs are this subscription's. `target_docs.py` is the table that picks between them.

Read it beside the AWS page and the differences are the argument: no per-service load balancer to draw, a
revision where there is a task definition, and four rows that say what this target does *not* do the way
the other one does — the linked site, the flag SDK, the tenant a person creates, and a registry that cannot
refuse a rebuilt tag.
"""
from __future__ import annotations

from ..images import IMAGE_BUILDERS, MIGRATIONS_IN_PRODUCTION
from ..probes import ready_path
from ..services import App, services_of, web_apps
from .flags import release_notes
from .provisioning import node, provisioned


def deployment_diagram(project_name: str, apps: list[App]) -> str:
    """`docs/deployment.md`: what this project's `infra/` provisions, drawn, and how a commit reaches it.

    Drawn from the same answers the stacks read — which services exist, whether there is a site, which of
    them has a database, staff identity, the product's users — so `add-service` and `add-frontend`
    regenerate it with everything else and it shows this project, not the target in general. The lines are
    the ones `main.tf`, `postgres.tf`, the Entra files and `frontend.tf` actually create.
    """
    services = services_of(apps)
    web = web_apps(apps)
    database = any(provisioned(s, "event-store", "azure") == "flexible-server" for s in services)
    staff = any(provisioned(s, "auth", "azure") == "entra" for s in services)
    auth0 = any(provisioned(s, axis, "azure") == "auth0" for s in services for axis in ("auth", "users"))
    customers = any(provisioned(s, "users", "azure") == "auth0" for s in services)
    migrating = [s for s in services if s.selection.migrating_feature is not None]
    # Migrated by a one-off job before the release rolls, as against a framework migrating as it starts.
    as_job = [s for s in migrating if {"command", "image"} & set(MIGRATIONS_IN_PRODUCTION[s.backend])]
    linked = web[0].api if web else None
    lines = ["flowchart LR", '    people(("People"))']
    if web:
        lines += [
            f'    swa["Static Web Apps: {web[0].path}, and /api to {web[0].api}"]',
            "    people --> swa",
        ]
    for s in services:
        if s.name == linked:
            continue
        lines += [f"    people --> app_{node(s.name)}"]
    lines += [f'    subgraph env ["Container Apps environment {project_name}-production, managed ingress and certificate"]']
    for s in services:
        n = node(s.name)
        builder = IMAGE_BUILDERS[s.backend]["tool"] or "the framework's build"
        through = "reached through the site" if s.name == linked else "its own HTTPS address"
        lines += [
            f'        app_{n}["{s.name}: {through}, min_replicas to max_replicas — {s.backend} image by {builder}, port {s.port}, {ready_path(s.backend)}"]',
            f'        app_{n} -.->|"the release before, until it is deactivated"| old_{n}["previous revision"]',
        ]
    if database:
        lines += ['        pg[("PostgreSQL Flexible Server 17, B_Standard_B1ms")]']
    if database or staff:
        lines += ['        vault["Key Vault"]']
    lines += ["    end"]
    if staff:
        lines += ['    staff["Entra ID: the workforce tenant"]']
    # Outside the subgraph on purpose: an Auth0 tenant is not in this subscription, and the drawing should
    # not suggest the deploy identity reaches it.
    if auth0:
        lines += ['    auth0["Auth0 tenant: outside this subscription"]']
    for s in services:
        n = node(s.name)
        if s.name == linked:
            lines += [f'    swa -->|"/api"| app_{n}']
        if provisioned(s, "event-store", "azure") == "flexible-server":
            lines += [f'    app_{n} -->|"DATABASE_URL, TLS"| pg', f"    app_{n} -.-> vault"]
        if provisioned(s, "auth", "azure") == "entra":
            lines += [f'    app_{n} -.->|"OIDC"| staff']
        if provisioned(s, "auth", "azure") == "auth0":
            lines += [f'    app_{n} -.->|"OIDC"| auth0']
        if provisioned(s, "users", "azure") == "auth0":
            lines += [f'    app_{n} -.->|"tokens"| auth0']
    if customers and web:
        lines += ['    swa -.->|"PKCE login"| auth0']
    runs = "\n".join(lines)

    migration_step = ""
    if as_job:
        names = ", ".join(s.name for s in as_job)
        migration_step = f' --> migrate_s["migrations as a Container Apps job: {names}"]'
    started = [s.name for s in migrating if s not in as_job]
    note = f" {', '.join(started)} migrate as they start (Flyway)." if started else ""
    path = f"""flowchart LR
    push["push to main"] --> verify["verify.yml: make verify"]
    verify -->|"passed"| build["deploy.yml: make build push — one image per service, by digest, to the registry"]
    build{migration_step} --> staging["apply staging: a new revision takes the traffic"] --> smoke_s["make smoke"]
    smoke_s{migration_step.replace("migrate_s", "migrate_p")} -->|"AUTO_PROMOTE=true"| production["apply production: a new revision, the last one kept"] --> smoke_p["make smoke"]
    promote["production.yml: make promote, or the Actions tab"] -->|"the commit staging is running"| production
    rollback["rollback.yml, started by hand"] -.->|"re-applies the previous release"| production"""

    table = "\n".join(
        f"| `{s.name}` | {s.backend} | {IMAGE_BUILDERS[s.backend]['tool'] or 'framework build'} | {s.port} | "
        f"{provisioned(s, 'event-store', 'azure') or '—'} | {provisioned(s, 'auth', 'azure') or '—'} | "
        f"{provisioned(s, 'users', 'azure') or '—'} |"
        for s in services
    )
    site_note = (
        f"""

`{web[0].api}` is linked to the static web app as its API backend, which is what makes `/api` reach it
without CORS and without a routing rule — the product's own rule is that the prefix is `/api` and the whole
path is proxied. A linked service answers only through the site, so it is the one service with no address
of its own in `urls`: that is stricter than a load balancer in front of it, and it is why `make smoke`
still asks `/api{{health}}` and expects the service's own 404."""
        if web
        else ""
    )
    return f"""# Deployment architecture: Azure

Generated with the project and regenerated by `add-service` and `add-frontend`, so it draws what `infra/`
provisions for *this* project's services rather than the target in general. `staging` and `production` are
the same shape, each in its own resource group with its own Container Apps environment, database and
identity; the names below are production's. Whether production exists yet is the `AUTO_PROMOTE` variable on
the forge: `true` deploys it on every green push, `false` leaves it to `make promote` and to nothing else.
[`docs/adr/0002-production-target.md`](adr/0002-production-target.md) is why each part is what it is, and
what it costs.

## What runs

```mermaid
{runs}
```

There is no load balancer per service and none to pay for: the Container Apps environment answers on a name
of its own with a certificate of its own, and a container app declares the ingress it wants. A deploy is a
revision — the new one starts beside the one serving, takes no requests until its readiness probe passes,
and then takes all of them at once. `kept_revisions` decides whether the release before goes on running: one
in production, so a rollback is a change of traffic weight, and none in staging.{site_note}

| Service | Backend | Image | Port | Store | Staff identity | Users |
|---|---|---|---|---|---|---|
{table}

## How a commit gets there

```mermaid
{path}
```

`deploy.yml` starts when `verify` has passed on `main`, never beside it. Migrations run before the new
revision rolls, so the release still serving keeps the schema it knows; `make check-migrations` holds every
migration to expand/contract for the same reason.{note} `make deploy ENV=…` from a laptop with credentials
runs the same code path.
{release_notes(apps)}"""


def production_adr(project_name: str, apps: list[App]) -> str:
    services = services_of(apps)
    web = web_apps(apps)
    database = any(provisioned(s, "event-store", "azure") == "flexible-server" for s in services)
    staff = any(provisioned(s, "auth", "azure") == "entra" for s in services)
    auth0_staff = any(provisioned(s, "auth", "azure") == "auth0" for s in services)
    auth0_customers = any(provisioned(s, "users", "azure") == "auth0" for s in services)
    builders = "; ".join(
        dict.fromkeys(
            f"`{s.backend}` with {IMAGE_BUILDERS[s.backend]['tool'] or 'its framework build'}" for s in services
        )
    )
    # Per environment: a replica at the idle rate, the registry once for the project, the database where
    # there is one, the site where there is one. See the cost section below for where each comes from.
    idle = 6 * len(services) + (16 if database else 0) + (9 if web else 0) + 3
    browser_flags = (
        " A browser app reads the same flag by asking the service for it, over `GET /api/flags`, which the "
        "service answers from the environment these secrets land in — so one product flag has one name and "
        "one value on both sides of `/api`, and the restart above is the whole of a flip. A browser already "
        "open picks the new value up on its next load, and no deploy is owed; `make flag` says so. It was "
        "not always this way, and the reason is the design: Vite inlines a `VITE_`-prefixed value while the "
        "bundle is *built*, so a flag compiled into a bundle is a property of that build and not of the "
        "environment it runs in. That gave one flag two clocks and an ordering rule to keep them from "
        "contradicting each other. Asking the service removes the second clock, and a rollback no longer "
        "diverges either: the restored `index.html` carries no flag values at all, so both halves read "
        "whatever the secret says now — which is what a rollback should leave alone."
    ) if web else ""
    rows = [
        ("Infrastructure as code", "OpenTofu 1.12, state in a blob container with the blob's own lease as the lock, the bootstrap stack's own state committed under OpenTofu's native encryption. The state account has no shared key at all, so the pipeline reaches it as itself or not at all. Terraform stays swappable: same HCL, same providers."),
        ("Runtime", "One Container App per application on the Consumption workload profile, deployed by revision: a new revision starts beside the one serving, takes no traffic until its readiness probe passes, and then takes all of it. The environment's own ingress answers on a managed certificate, so there is no load balancer per service to create, to configure or to pay for — which is the whole reason this target costs less per service than the AWS one, and the gap widens with every service `add-service` creates. What a rollback costs is `kept_revisions`: one keeps the previous revision running, so an undo is a change of traffic weight; none lets it be deactivated, so an undo is a restart of the previous image. Scaling is concurrent requests between `min_replicas` and `max_replicas`. Moving to AKS later replaces `main.tf`, not the application."),
        ("Images", f"Each ecosystem's own builder, no Dockerfile — {builders}. Built once per commit, pushed by digest, the same digest promoted from staging to production. One registry for the project: a container registry creates a repository the first time one is pushed, so `add-service` adds nothing here."),
        ("Image tags are not immutable", "Stated as a row because it is a promise the AWS target keeps and this one does not. ECR refuses a push to a tag that exists; a Basic container registry has no such policy — registry-wide immutability and untagged-manifest retention are both Premium, at several times the price of everything else in this table put together. The pipeline is the only thing that pushes and it pushes the commit it checked out, so a replaced tag is not reachable by accident; it is simply not refused. A project that needs it refused moves the registry to Premium and adds the policy, and amends this row."),
        ("Environments", "`staging` and `production`, workspaces over one module, each in a resource group of its own, applied in that order by `.github/workflows/deploy.yml` once `verify` has passed on `main` — it is a `workflow_run` of the gate, never a race with it: build, push, apply staging, smoke, apply production, smoke. Ephemeral environments are a separate decision."),
        ("How production is reached", "One repository variable, `AUTO_PROMOTE`, written by `make bootstrap` and read by nothing else. `true` is the default and the decision above: no approval step, every green commit goes all the way. `false` skips the production job — staging still deploys on every green push, and production is deployed by `.github/workflows/production.yml`, started by `make promote` or from the Actions tab, with the commit staging is running. That workflow is also how production is *created*: without auto-promotion the workspace is empty until it first runs, which is the point — two environments cost twice one, and a project need not pay for production on the day it is generated. Both modes promote the digests staging ran and neither applies anything from a laptop, so the difference is who decides when, not what is deployed. It is a per-project choice recorded on the forge rather than in `project.json`: it is a fact about this subscription, it changes on the day somebody promotes, and generation-time answers are replayed by `slipwai migrate`, which would put it back. Turning production off again is not a flag — the apps and the database are already there — so it is a `tofu destroy` this project does not yet have a verb for."),
        ("Rollback", "`.github/workflows/rollback.yml`, started by hand with the environment to roll back, runs `make rollback ENV=…`: it re-applies the release before the current one — the previous digests, and the previous `index.html` where there is a site — from the release records `make deploy` keeps in the state container, then smokes it. It queues behind a deploy in flight, and the next push to `main` deploys forward again."),
        ("Who the pipeline is", "On GitHub, a user-assigned managed identity with three federated credentials — `…:ref:refs/heads/main`, `…:environment:staging`, `…:environment:production` — because a job with an `environment:` is issued a different subject from one without, and a credential naming only the ref form lets the build job sign in while every deploy job is refused. Entra matches a subject exactly, with no wildcards, so all three are listed; and a managed identity is an ARM resource, so this path needs no permission to write to the directory at all. On a forge without OIDC federation (Gitea) it is an app registration and one client secret in the repository's secrets, which is the weaker shape and the only one that needs directory permission — which is why it is created only for the forge that needs it."),
        ("Feature flags", "One Key Vault secret per flag per environment, resolved into the replica's environment by Container Apps exactly as a secret is — so a service reads `FLAG_<KEY>` at start-up and no image carries an Azure SDK, in any of the languages this factory generates. Declared in `infra/service/flags.auto.tfvars`, which seeds a *new* environment and is then left alone: `lifecycle { ignore_changes = [value] }` means neither the next deploy — the whole stack, unattended, on every merge — nor `make rollback` puts a flipped flag back. `make flag ENV=… KEY=… VALUE=…` writes the secret and starts a new revision, so a flip costs a rolling restart: about two minutes, no build, no apply, no merge. `make flags` prints what an environment is actually set to, which is the only place that answer lives — a flip is not in the release record, which names a commit and its images. It is not a live re-read, and where that is what a flag needs, `flag_transport = \"appconfig\"` in that environment's tfvars is the other shape: Azure App Configuration, read under the app's managed identity, and a flip that takes effect in seconds with no restart at all. Per environment rather than per project, so staging can take it on before production does, or one environment need never take it on." + browser_flags),
        ("The opt-in flag transport puts an SDK in the image", "A second row, because this is where the target is weaker than the AWS one rather than differently shaped. AWS's `appconfig` transport is an agent container beside the application, read over loopback, so no image gains a cloud SDK. Container Apps has no such sidecar, and writing one would mean a Dockerfile, which this factory does not have for the reason it has no hand-written Compose file. So `appconfig` here means the TypeScript reader calls `@azure/app-configuration` under the app's managed identity. It is confined to the one backend that has a reader and offered per environment, so it is taken on deliberately or not at all — and the Key Vault default stays SDK-free for every backend, which is the property that mattered."),
    ]
    if database:
        rows.append(("Database", "Azure Database for PostgreSQL Flexible Server 17, `B_Standard_B1ms`, one per environment, shared by every service on the Postgres store. `DATABASE_URL` generated into Key Vault and referenced as a container secret. Its smallest disk is 32 GB where RDS's is 20, which is most of why the database is the one line that costs more here than there."))
        rows.append(("Database TLS", "Encrypted, not verified. The server half is the product's own: `require_secure_transport` is on by default and `minimum_tls_version` is stated explicitly beside it, so no connection to this database is ever plaintext. The client half is `PGSSLMODE` in the app and in the migrate job, and its value is per driver because the drivers genuinely differ: `no-verify` for TypeScript, whose `pg` reads the variable with its own vocabulary where `require` means *verify*; `require` for Python and Go, where libpq's `require` already means encrypt-without-verifying; and nothing at all for Quarkus and Spring Boot, because pgjdbc does not read `PGSSLMODE` and its own default, `prefer`, already negotiates TLS. **The TypeScript value is inherited from the AWS table rather than measured here, and that is worth knowing**: RDS forced `no-verify` because its certificate chains to a private Amazon root Node does not bundle, while this server's chains to roots Node does — so `require`, and real verification, may work. One run of node-postgres against a Flexible Server settles it; until somebody has done it the table says what is known to work rather than what ought to. Nothing goes in `DATABASE_URL`: one libpq-style string is shared by every backend, an `sslmode` in it means a different thing to each of their drivers, and for `pg` it also overrides `PGSSLMODE`."))
    if staff:
        rows.append(("Staff identity", "An Entra ID app registration in the subscription's own workforce tenant, the three groups the local realm has, and a confidential client whose secret lives in Key Vault. Keycloak stays the local stand-in; `OIDC_GROUPS_CLAIM` is `groups` in both, which is one fewer difference than Cognito leaves. The flow itself is unwritten, as locally."))
    if auth0_staff:
        rows.append(("Staff identity", "Auth0 — an application in an Auth0 tenant, a database connection staff sign in against with sign-up off, the three roles, and a post-login action putting them in a namespaced claim. The client secret lives in Key Vault. Keycloak stays the local stand-in; `OIDC_GROUPS_CLAIM` names the claim. **Created with the tenant's own credential, not the subscription's** — the deploy identity has no authority in an Auth0 tenant, so `infra/service/auth0.tf` is applied with a machine-to-machine application's credentials, which `make bootstrap` asks for and stores on the forge. The tenant and that one application are made by a person before the first apply; everything else is made on every apply."))
    if auth0_customers:
        rows.append(("The product's users", "Auth0 — a second database connection with self-registration and password reset, an API whose identifier is the audience, and a public PKCE client for the browser app, which is built once per environment because Vite bakes the issuer into the bundle. **Staff and customers share one issuer here**, unlike every other answer on this axis: they are two connections in one tenant, so what tells their tokens apart is `aud` — the staff client id on an ID token, this API's identifier on a customer's access token — and the audience check the adapters already call mandatory is the one doing the work. Auth0 was chosen over an Entra External ID tenant because that tenant has no resource in azurerm and its sign-up flows none in azuread, so the sign-up this axis promises could not be declared at all."))
    if web:
        rows.append(("Browser app", "Azure Static Web Apps (Standard), with the api service linked as its API backend. The site is served from the product's own content store rather than from a bucket behind a CDN, so unlike the AWS shape there is no second, publicly reachable origin to keep private: there is nothing else to reach. `/api` is proxied to the same path on the container app by the product's own rule — no CORS, no routing rule for this stack to write — and a linked service is given an identity provider that rejects anything not proxied by the site, so it has no public address of its own. That is stricter than a load balancer in front of it and it is a real difference: `urls` does not carry that service. Hashed assets are uploaded immutable, `index.html` last with `no-store` as the release pointer. Azure Front Door is the documented upgrade for a WAF, custom domains and multi-region; it costs about four times as much and, below its Premium tier, cannot reach a private storage origin at all, which is why it is not the default."))
    rows.append(("Network", "The Container Apps environment's own, with no virtual network of this project's: the apps reach the database over its public endpoint with a firewall rule admitting Azure services, and the environment's ingress is what faces the internet. A VNet-integrated environment with a private endpoint on the database is a change to `main.tf` and `postgres.tf`, and the first thing to do when this project holds anything that matters."))
    table = "\n".join(f"| {question} | {answer} |" for question, answer in rows)
    return f"""# 2. Production target: Azure

Date: generated with the project. Status: accepted at generation; amend it here when a row changes.

## Context

`{project_name}` was generated with `--target azure`. The pipeline is feature zero: the first commit already
carries a build, a deploy target and a rollback, so credentials, permissions, DNS and monitoring are found out
on day one rather than under deadline pressure. Everything below was decided once, in the factory, for every
project that chooses this target; what this project owns is `infra/`, and every one of these rows is one
file there.

## Decision

| Question | Answer |
|---|---|
{table}

## What it costs while idle

Roughly ${idle} a month per environment: about $6 per service for a 0.25 vCPU replica at the idle rate,
{"about $16 for the database" if database else "and no database"}, {"$9 for the site, " if web else ""}$5 for
the registry across the whole project, and a few dollars of logs. Ingress, the certificate and the address
are the platform's and cost nothing, which is the line that is not here: the AWS target pays about $18 a
month per service for a load balancer, so this one is cheaper at one service and further ahead at three.
Two environments, twice that, less the registry. Nothing here scales to zero in production, on purpose — a
production service that sleeps is the wrong trade — but `min_replicas = 0` in `staging.tfvars` is a real
saving on the environment where a cold start costs nobody anything.

Which is why production is a project's own decision to make on the day it wants one. With `AUTO_PROMOTE` set
off — `make bootstrap AUTO_PROMOTE=false`, or the question `./init` reaches — nothing is applied but
staging, and the bill is the one environment until `make promote` creates the other. It is a saving in the
days before production exists and not a penny after: once promoted, production costs what the table above
says whichever mode this project is in.

## Consequences

- Deploys are the pipeline's. `make deploy ENV=…` exists so a person can run the same code path, not so
  that production is applied from a laptop; `infra/README.md` says what the pipeline is configured with.
- Without auto-promotion a person is back between staging and production, which the decision above
  argued against. What that buys is a project that pays for one environment until it wants two, and a
  promotion that is still the pipeline's own `make deploy` on the runner with the deploy identity. What it
  costs is that "every green commit is in production" stops being true, and nothing here checks that a
  promotion ever happens — production silently ages behind staging until somebody looks.
- `make bootstrap` is run once by a person signed in as an Owner of the subscription, and its state
  committed. Owner rather than Contributor because it grants the pipeline its roles, and granting access is
  not something Contributor may do. On GitHub everything after that is a repository variable and the
  pipeline holds no credential; on a forge without OIDC federation the pipeline holds one client secret.
- Active CPU on Container Apps bills at several times the idle rate, so a saturated replica costs more than
  the figure above — around $20 a month rather than $6. It still does not lose to a Fargate task, because
  that task needs its own load balancer beside it whatever it is doing; the crossover is at sizes where a
  project has moved off the Consumption profile anyway, and that is the day to re-price this table.
- `make ci` builds every image and proves it starts, listens and answers its probe locally
  (`make smoke-image`) — a 503 from a readiness probe counts there, because nothing else is running; the apply
  itself cannot be proved without a subscription, so `tofu validate` is what the gate holds the stacks to.
- `min_replicas` is one. Two in production is what makes a deploy — and a lost availability zone —
  invisible, at another $6 a month per service; raise it in `production.tfvars` when the product is in
  front of people.
- Migrations run before the new revision starts, and every migration is held to expand/contract by
  `make check-migrations`, because a rollback keeps the schema the newer revision left.
- A revision suffix must be unique for the lifetime of a container app, and `make rollback` re-runs a
  commit that has already had one. So the suffix is the platform's hash of the template rather than the
  commit, and a rollback is an ordinary apply rather than a name collision nobody would hit until the
  second time they rolled back. Which commit a revision runs is the image tag on it.
"""
