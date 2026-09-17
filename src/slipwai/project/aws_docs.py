"""`docs/deployment.md` and `docs/adr/0002-production-target.md` for a project going to **AWS**.

Beside `infra.py` rather than inside it, because these two answer a different question. That module decides
which files a project going to production is given; these decide what a reader is told about them — one
Mermaid drawing of what the answers provision and how a commit reaches it, and one decision record whose
rows carry the cost. Both are generated from the same answers the stacks read, so `add-service` and
`add-frontend` regenerate them with everything else and neither can describe a project that no longer
exists.

One module per target, named for it, because there is nothing general here to share: the nodes are ECS
services and target groups, the rows are Fargate and RDS and Cognito, and the costs are this account's.
`target_docs.py` is the table that picks between them, and a second cloud is a row in it beside a module of
its own — never a branch inside these two functions. What *is* shared is in `provisioning.py`.
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
    regenerate it with everything else and it shows this project, not the target in general. The lines
    are the ones `ingress.tf`, `main.tf`, `rds.tf`, the Cognito files and `frontend.tf` actually create.
    """
    services = services_of(apps)
    web = web_apps(apps)
    rds = any(provisioned(s, "event-store", "aws") == "rds" for s in services)
    staff = any(provisioned(s, "auth", "aws") == "cognito" for s in services)
    customers = any(provisioned(s, "users", "aws") == "cognito" for s in services)
    auth0 = any(provisioned(s, axis, "aws") == "auth0" for s in services for axis in ("auth", "users"))
    auth0_customers = any(provisioned(s, "users", "aws") == "auth0" for s in services)
    migrating = [s for s in services if s.selection.migrating_feature is not None]
    # Migrated by a one-off task before the release rolls, as against a framework migrating as it starts.
    as_task = [s for s in migrating if {"command", "image"} & set(MIGRATIONS_IN_PRODUCTION[s.backend])]
    lines = ["flowchart LR", '    people(("People"))']
    if web:
        lines += [f'    cf_web["CloudFront: {web[0].path}, and /api/* to {web[0].api}"]', "    s3[(\"S3: the site's bundle\")]"]
        lines += ["    people --> cf_web --> s3"]
    for s in services:
        lines += [f'    cf_{node(s.name)}["CloudFront: {s.name} (HTTPS)"]', f"    people --> cf_{node(s.name)}"]
    lines += [f'    subgraph cluster ["ECS cluster {project_name}-production, in the default VPC"]']
    for s in services:
        n = node(s.name)
        builder = IMAGE_BUILDERS[s.backend]["tool"] or "the framework's build"
        lines += [
            f'        subgraph svc_{n} ["{s.name}: Fargate, min_tasks to max_tasks, deployed blue/green"]',
            f'            alb_{n}["ALB (HTTP)"] --> blue_{n}["target group: blue"] --> tasks_{n}["tasks: {s.backend} image by {builder}, port {s.port}, {ready_path(s.backend)}"]',
            f'            alb_{n} -.->|"the next release, until the switch"| green_{n}["target group: green"]',
            "        end",
        ]
    if rds:
        lines += ['        rds[("RDS Postgres 17, db.t4g.micro")]']
    if rds or staff:
        lines += ['        secrets["Secrets Manager"]']
    lines += ["    end"]
    if staff:
        lines += ['    staff["Cognito: staff user pool"]']
    if customers:
        lines += ["    customers[\"Cognito: the product's users\"]"]
    # Outside the subgraph on purpose: an Auth0 tenant is not in this account, and the drawing should not
    # suggest the deploy role reaches it.
    if auth0:
        lines += ['    auth0["Auth0 tenant: outside this account"]']
    for s in services:
        n = node(s.name)
        lines += [f"    cf_{n} --> alb_{n}"]
        if web and web[0].api == s.name:
            lines += [f'    cf_web -->|"/api/*"| alb_{n}']
        if provisioned(s, "event-store", "aws") == "rds":
            lines += [f'    tasks_{n} -->|"DATABASE_URL, TLS"| rds', f"    tasks_{n} -.-> secrets"]
        if provisioned(s, "auth", "aws") == "cognito":
            lines += [f'    tasks_{n} -.->|"OIDC"| staff']
        if provisioned(s, "users", "aws") == "cognito":
            lines += [f'    tasks_{n} -.->|"tokens"| customers']
        if provisioned(s, "auth", "aws") == "auth0":
            lines += [f'    tasks_{n} -.->|"OIDC"| auth0']
        if provisioned(s, "users", "aws") == "auth0":
            lines += [f'    tasks_{n} -.->|"tokens"| auth0']
    if customers and web:
        lines += ['    cf_web -.->|"PKCE login"| customers']
    if auth0_customers and web:
        lines += ['    cf_web -.->|"PKCE login"| auth0']
    runs = "\n".join(lines)

    migration_step = ""
    if as_task:
        names = ", ".join(s.name for s in as_task)
        migration_step = f' --> migrate_s["migrations as a one-off task: {names}"]'
    started = [s.name for s in migrating if s not in as_task]
    note = f" {', '.join(started)} migrate as they start (Flyway)." if started else ""
    path = f"""flowchart LR
    push["push to main"] --> verify["verify.yml: make verify"]
    verify -->|"passed"| build["deploy.yml: make build push — one image per service, by digest, to ECR"]
    build{migration_step} --> staging["apply staging: blue/green, no bake"] --> smoke_s["make smoke"]
    smoke_s{migration_step.replace("migrate_s", "migrate_p")} -->|"AUTO_PROMOTE=true"| production["apply production: blue/green, 5 minute bake"] --> smoke_p["make smoke"]
    promote["production.yml: make promote, or the Actions tab"] -->|"the commit staging is running"| production
    rollback["rollback.yml, started by hand"] -.->|"re-applies the previous release"| production"""

    table = "\n".join(
        f"| `{s.name}` | {s.backend} | {IMAGE_BUILDERS[s.backend]['tool'] or 'framework build'} | {s.port} | "
        f"{provisioned(s, 'event-store', 'aws') or '—'} | {provisioned(s, 'auth', 'aws') or '—'} | "
        f"{provisioned(s, 'users', 'aws') or '—'} |"
        for s in services
    )
    return f"""# Deployment architecture: AWS

Generated with the project and regenerated by `add-service` and `add-frontend`, so it draws what `infra/`
provisions for *this* project's services rather than the target in general. `staging` and `production` are
the same shape, each with its own cluster, load balancers, database and user pools; the names below are
production's. Whether production exists yet is the `AUTO_PROMOTE` variable on the forge: `true` deploys it
on every green push, `false` leaves it to `make promote` and to nothing else. [`docs/adr/0002-production-target.md`](adr/0002-production-target.md) is why each part is
what it is, and what it costs.

## What runs

```mermaid
{runs}
```

Every service has its own load balancer and CloudFront distribution: with no domain there is nothing to
route by host, and the balancer speaks HTTP because a certificate needs one — CloudFront is what gives the
HTTPS address `make url` prints. Blue/green is ECS's own: a release's tasks register with the target group
that has no traffic, pass their health checks there, take all of it at once, and the previous release stays
up for the bake time, so a rollback in that window is the listener rule pointing back.

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
    stores = {s.name: provisioned(s, "event-store", "aws") for s in services}
    rds = any(store == "rds" for store in stores.values())
    staff = any(provisioned(s, "auth", "aws") == "cognito" for s in services)
    customers = any(provisioned(s, "users", "aws") == "cognito" for s in services)
    auth0_staff = any(provisioned(s, "auth", "aws") == "auth0" for s in services)
    auth0_customers = any(provisioned(s, "users", "aws") == "auth0" for s in services)
    builders = "; ".join(
        dict.fromkeys(
            f"`{s.backend}` with {IMAGE_BUILDERS[s.backend]['tool'] or 'its framework build'}" for s in services
        )
    )
    idle = 27 * len(services) + (12 if rds else 0)
    # The browser half of a flag, only where there is a browser app: it is the one row whose answer to "what
    # does a flip cost" differs per deployable, and a project with no frontend should not have to filter it out.
    browser_flags = (
        " A browser app reads the same flag by asking the service for it, over `GET /api/flags`, which the "
        "service answers from the environment these parameters land in — so one product flag has one name "
        "and one value on both sides of `/api`, and the restart above is the whole of a flip. A browser "
        "already open picks the new value up on its next load, and no deploy is owed; `make flag` says so. "
        "It was not always this way, and the reason is the design: Vite inlines a `VITE_`-prefixed value "
        "while the bundle is *built*, so a flag compiled into a bundle is a property of that build and not "
        "of the environment it runs in. That gave one flag two clocks and an ordering rule to keep them "
        "from contradicting each other. Asking the service removes the second clock, and a rollback no "
        "longer diverges either: the restored `index.html` carries no flag values at all, so both halves "
        "read whatever the parameter says now — which is what a rollback should leave alone."
    ) if web else ""
    rows = [
        ("Infrastructure as code", "OpenTofu 1.12, state in S3 with S3-native locking (`use_lockfile`), the bootstrap stack's own state committed under OpenTofu's native encryption. Terraform stays swappable: same HCL, same providers."),
        ("Runtime", "One ECS service per application on Fargate, deployed blue/green by ECS itself: the new revision's tasks register with the target group that has no traffic, pass their health checks there, take all of it at once, and the old revision stays up, drained, for `bake_minutes` (five in production, none in staging) — a rollback in that window is the listener rule pointing back, and a revision that fails under real traffic is put back by ECS. Native to ECS, so `tofu apply` still describes what runs and `make rollback` is itself a blue/green deploy. Each service has its own load balancer — with no domain there is nothing to route by host — and a CloudFront distribution in front of it for HTTPS; a domain and host rules collapse the balancers into one later. Scaling is a CPU target between `min_tasks` and `max_tasks`. Moving to EKS later replaces `main.tf` and `ingress.tf`, not the application."),
        ("Images", f"Each ecosystem's own builder, no Dockerfile — {builders}. Built once per commit, pushed by digest, the same digest promoted from staging to production."),
        ("Environments", "`staging` and `production`, workspaces over one module, applied in that order by `.github/workflows/deploy.yml` once `verify` has passed on `main` — it is a `workflow_run` of the gate, never a race with it: build, push, apply staging, smoke, apply production, smoke. Ephemeral environments are a separate decision."),
        ("How production is reached", "One repository variable, `AUTO_PROMOTE`, written by `make bootstrap` and read by nothing else. `true` is the default and the decision above: no approval step, every green commit goes all the way. `false` skips the production job — staging still deploys on every green push, and production is deployed by `.github/workflows/production.yml`, started by `make promote` or from the Actions tab, with the commit staging is running. That workflow is also how production is *created*: without auto-promotion the workspace is empty until it first runs, which is the point — two environments cost twice one, and a project need not pay for production on the day it is generated. Both modes promote the digests staging ran and neither applies anything from a laptop, so the difference is who decides when, not what is deployed. It is a per-project choice recorded on the forge rather than in `project.json`: it is a fact about this account, it changes on the day somebody promotes, and generation-time answers are replayed by `slipwai migrate`, which would put it back. Turning production off again is not a flag — the tasks and the database are already there — so it is a `tofu destroy` this project does not yet have a verb for."),
        ("Rollback", "`.github/workflows/rollback.yml`, started by hand with the environment to roll back, runs `make rollback ENV=…`: it re-applies the release before the current one — the previous digests, and the previous `index.html` where there is a site — from the release records `make deploy` keeps in the state bucket, then smokes it. It queues behind a deploy in flight, and the next push to `main` deploys forward again."),
        ("Feature flags", "One SSM parameter per flag per environment, resolved into the container's environment by ECS exactly as a secret is — so a service reads `FLAG_<KEY>` at start-up and no image carries an AWS SDK, in any of the languages this factory generates. Declared in `infra/service/flags.auto.tfvars`, which seeds a *new* environment and is then left alone: `lifecycle { ignore_changes = [value] }` means neither the next deploy — the whole stack, unattended, on every merge — nor `make rollback` puts a flipped flag back. `make flag ENV=… KEY=… VALUE=…` writes the parameter and forces a new deployment, so a flip costs a rolling restart: about two minutes, no build, no apply, no merge. `make flags` prints what an environment is actually set to, which is the only place that answer lives — a flip is not in the release record, which names a commit and its images. It is not a live re-read, and where that is what a flag needs, `flag_transport = \"appconfig\"` in that environment's tfvars is the other shape: an AWS AppConfig agent beside the container, read over loopback, and a flip that takes effect in seconds with no restart at all. Per environment rather than per project, so staging can take it on before production does, or one environment need never take it on. It costs a second container in every task and it is the first thing this skeleton's application is allowed to call AWS for — under `ssm` the *execution* role reads the parameters and the task role is untouched, and the agent inverts that." + browser_flags),
    ]
    if rds:
        rows.append(("Database", "RDS Postgres 17, `db.t4g.micro`, single-AZ, one per environment, shared by every service on the Postgres store. `DATABASE_URL` generated into Secrets Manager and injected as a container secret. Aurora Serverless v2 is the documented swap, not the default: its 15–30 s resume from zero is wrong for production."))
        rows.append(("Database TLS", "Encrypted, not verified. The server half is `rds.force_ssl = 1`, stated in an explicit parameter group (`rds.tf`) rather than inherited from `default.postgres17`, so no connection to this database is ever plaintext. The client half is `PGSSLMODE` in both task definitions' environment, and its value is per driver because the drivers genuinely differ: `no-verify` for TypeScript, whose `pg` reads the variable with its own vocabulary where `require` would mean *verify* against a CA store Amazon's private RDS root CA is not in; `require` for Python and Go, where libpq's `require` already means encrypt-without-verifying; and nothing at all for Quarkus and Spring Boot, because pgjdbc does not read `PGSSLMODE` (the string is absent from the driver jar) and its own default, `prefer`, already negotiates TLS without verifying — which the parameter group above turns from a preference into a guarantee. Nothing goes in `DATABASE_URL`: one libpq-style string is shared by every backend, an `sslmode` in it means a different thing to each of their drivers, and for `pg` it also overrides `PGSSLMODE`. Two follow-ups, both deliberate: stating the posture on the client for the Java backends needs a JDBC datasource property rather than an environment variable, and verifying the server certificate — `verify-full` with `sslrootcert` — needs Amazon's RDS root CA inside every image, by a path that differs per image builder while the secret is shared by all of them. Amend this row when either is taken on."))
    if staff:
        rows.append(("Staff identity", "A Cognito user pool (Essentials tier), the three groups the local realm has, a hosted login and a confidential client whose secret lives in Secrets Manager. Keycloak stays the local stand-in; `OIDC_GROUPS_CLAIM` is `cognito:groups` here and `groups` there. The flow itself is unwritten, as locally."))
    if customers:
        rows.append(("The product's users", "A second Cognito user pool with self-registration and a public PKCE client for the browser app, which is built once per environment because Vite bakes the issuer into the bundle. Cognito access tokens carry the client id in `client_id`, not `aud`."))
    if auth0_staff:
        rows.append(("Staff identity", "Auth0 — an application in an Auth0 tenant, a database connection staff sign in against with sign-up off, the three roles, and a post-login action putting them in a namespaced claim. The client secret lives in Secrets Manager. Keycloak stays the local stand-in; `OIDC_GROUPS_CLAIM` names the claim. Created with the tenant's own credential, not AWS's — the tenant and one machine-to-machine application are made by a person before the first apply, and everything else on every apply."))
    if auth0_customers:
        rows.append(("The product's users", "Auth0 — a second database connection with self-registration and password reset, an API whose identifier is the audience, and a public PKCE client for the browser app, which is built once per environment because Vite bakes the issuer into the bundle. Staff and customers share one issuer here, unlike every other answer on this axis, so `aud` is what tells their tokens apart and the check is not optional."))
    if web:
        rows.append(("Browser app", "S3 behind CloudFront, one distribution with two origins: the bucket by default, the service for `/api/*`. Same origin, so the bundle calls `/api` relatively. Hashed assets are uploaded immutable, `index.html` last with `no-store` as the release pointer."))
    rows.append(("Network", "The account's default VPC and its public subnets; the tasks' own security group, admitted by the database. A dedicated VPC is a change to `network.tf` and the subnet group."))
    table = "\n".join(f"| {question} | {answer} |" for question, answer in rows)
    return f"""# 2. Production target: AWS

Date: generated with the project. Status: accepted at generation; amend it here when a row changes.

## Context

`{project_name}` was generated with `--target aws`. The pipeline is feature zero: the first commit already
carries a build, a deploy target and a rollback, so credentials, permissions, DNS and monitoring are found out
on day one rather than under deadline pressure. Everything below was decided once, in the factory, for every
project that chooses this target; what this project owns is `infra/`, and every one of these rows is one
file there.

## Decision

| Question | Answer |
|---|---|
{table}

## What it costs while idle

Roughly ${idle} a month: about $9 per service for the smallest Fargate task and about $18 for its load
balancer, {"about $12 for the database after the first free year" if rds else "and no database"}; Cognito and
CloudFront sit inside their free tiers at this scale. Two environments, twice that; a second task per service
in production, another $9. Nothing here scales to zero, on purpose — a production service that sleeps is the
wrong trade.

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
  promotion that is still the pipeline's own `make deploy` on the runner with the deploy role. What it
  costs is that "every green commit is in production" stops being true, and nothing here checks that a
  promotion ever happens — production silently ages behind staging until somebody looks.
- `make bootstrap` is run once by a person with administrator credentials and its state committed. On
  GitHub everything after that is a repository variable and the pipeline holds no credential; on a forge
  without OIDC federation the pipeline holds a key whose only permission is to assume the deploy role.
- `make ci` builds every image and proves it starts, listens and answers its probe locally
  (`make smoke-image`) — a 503 from a readiness probe counts there, because nothing else is running; the apply itself
  cannot be proved without an account, so `tofu validate` is what the gate holds the stacks to.
- `min_tasks` is one. Two in production is what makes a deploy — and a lost availability zone — invisible,
  at another $9 a month per service; raise it in `production.tfvars` when the product is in front of people.
- A deploy runs both revisions for the bake time, so the deploy job takes that much longer in production and
  the environment briefly costs double. Migrations run before the new revision starts, and every migration
  is held to expand/contract by `make check-migrations`, because the two revisions share the database and a
  rollback keeps the schema the newer one left.
- The provider re-sends the service's load-balancer block on every update, which would make every deploy
  land on the same target group (hashicorp/terraform-provider-aws #45678); `ignore_changes` on that block
  and on the listener rule's action is the workaround, so a change to either is a `tofu taint`, not an edit.
"""
