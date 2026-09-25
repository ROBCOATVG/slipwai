# The AWS target

`--target aws` gives a generated project a path to production on day one: an image per service, two long-lived
environments, a pipeline that takes every commit passing `verify` on `main` through both, and a rollback that
is one command. Whether it takes it through *both* on day one is the project's own to answer, because two
environments cost twice one: `make bootstrap` asks whether to auto-promote to production, and answering no
leaves production uncreated until `make promote` says so.
This page is what it is given, what it costs, what the factory proves about it, and how the next cloud
becomes a row beside it. The design is restated in every generated
project as `docs/adr/0002-production-target.md`.

## What a project is given

| Piece | What |
|---|---|
| `infra/bootstrap/`, `make bootstrap` | The state bucket (versioned, S3-native locking), a deploy role, the way the pipeline becomes it, and one ECR repository per service with immutable tags. `make bootstrap` (`scripts/bootstrap.py`) is the one thing a person does, and `./init` runs it after asking for the repository to push to (creating it on the forge if missing) and pushing: it reads the forge off the `origin` remote, applies the stack with the administrator credentials the `aws` CLI finds, and writes the outputs to the repository — variables for the identifiers; on GitHub the pipeline then signs in with a short-lived OIDC token and no stored credential (the trust names three subjects, and both halves of each one are GitHub's to spell: the prefix is whatever its OIDC customization endpoint reports for the repository — the immutable `repo:owner@<id>/name@<id>` form for anything created after 15 July 2026 — and the suffix is `:ref:refs/heads/main` for a job with no `environment:` but `:environment:staging` or `:environment:production` for one that declares it, which is [every job that deploys](#the-trust-names-three-subjects-because-github-issues-three)), on Gitea (or any forge without OIDC federation) it creates an IAM user that may only assume the deploy role and stores its key as the two repository secrets. On GitHub it also creates those two environments, each with a deployment branch policy naming `main`, which is what keeps the environment subjects to `main` — they carry no branch of their own. Its own state is committed, encrypted under a passphrase the script generates once and prints. Run again after `add-service`. That committed state is also how a later `./init` — answering an axis again, adding an extension, switching agent — knows the account is bootstrapped: it says so and leaves it alone, so a rerun needs no credentials. |
| `infra/service/` | One module, two workspaces (`staging`, `production`). One `aws_ecs_service` per application on Fargate in an environment's own cluster, deployed blue/green by ECS itself (`main.tf`), each behind its own load balancer with two target groups and a CloudFront distribution for HTTPS (`ingress.tf`); the old revision stays up for `bake_minutes` after the traffic moves, so a rollback in that window is the listener rule pointing back. Plus, where the answers asked for them: RDS Postgres (`db.t4g.micro`, one per environment, `DATABASE_URL` in Secrets Manager), a Cognito user pool for staff and another for the product's users, and a private S3 bucket behind CloudFront with `/api/*` routed to the service. The tasks' own security group is what the database admits. The default VPC, on purpose. |
| `docs/deployment.md` | Two Mermaid diagrams drawn from the project's own answers — what runs (CloudFront, the per-service balancer and blue/green target groups, the tasks, RDS, Secrets Manager, the Cognito pools, the site) and how a commit gets there (verify, build, migrate, staging, smoke, production, rollback) — plus a table per service. `add-service` and `add-frontend` regenerate it. Listed under *Production* in `docs/README.md` and named in the README's *Documentation* section, so it is found from where a reader looks first. |
| `project.auto.tfvars.json` | The services as data, written from `project.json`: port, probe path, what the target provisions for each answer (`store = "rds"`, `auth = "cognito"`), how the migrations run once the service is an image. Both stacks read it with `for_each`, so `add-service` is a change to the data and never to the HCL. |
| `make build` | One image per service by the ecosystem's own builder — `pack` with Paketo's Noble builder for TypeScript and Python, `ko` for Go, Quarkus's Jib extension, Spring's `build-image` — tagged with the commit, for `PLATFORM` (Fargate's `linux/amd64`; a laptop passes its own). No Dockerfile, for the reason Compose has none. |
| `make push`, `deploy`, `rollback`, `smoke`, `smoke-image`, `url`, `migrate-remote` | One line each, handing off to `scripts/deploy.py`: push by digest into `.build/images.json`; apply an environment from those digests, run the migrations, upload the site, record the release in the state bucket; re-apply the release before the current one; prove an environment answers; run every built image locally against `/health`; print an address; run the migrations as a one-off task. |
| `infra/service/flags.tf`, `flags.auto.tfvars`, `make flag`, `make flags` | Feature flags, as the one change to a running environment that costs no deploy — and, deliberately, no per-backend work: the value is an SSM parameter ECS resolves into the container's environment the way it resolves a secret, so every language reads `FLAG_<KEY>` with the same code it already had and no image gains an AWS SDK. `flags.auto.tfvars` is the project's own file and seeds a *new* environment; `ignore_changes = [value]` then leaves the value alone, so an unattended deploy of the whole stack on every merge cannot put a flipped flag back. `make flag` writes the parameter and forces a new deployment — a rolling restart, no build and no apply — and `make flags` reads what the environment is actually set to, which nothing else records. A flag that must move *without* a restart is the AppConfig agent instead, and it is built: `flag_transport = "appconfig"` in an environment's own tfvars provisions the AppConfig application, environment, profile and strategy, adds the agent as a second container, and inverts the IAM posture — the task role, untouched under `ssm`, gains `appconfig:StartConfigurationSession` and `GetLatestConfiguration`. Per environment rather than per project, because taking a sidecar on is a decision staging can make before production does. The stack owns the profile and `scripts/deploy.py` owns the document in it: one document per profile means a stack that owned the content would rewrite every flag on every unattended apply, so `make deploy` seeds declared keys and `make flag` writes a hosted version with `--latest-version-number` as its lost-update check. Offered only for backends whose reader has an AppConfig source — `APPCONFIG_READERS` in `src/slipwai/project/flag_route.py`, TypeScript today — and `variables.tf`'s allowed values are written per project from that, so a backend without one is refused by `tofu` rather than reading every flag as off. Where the project has a browser app the same flag reaches it by asking the service, over `GET /api/flags` — served by the transport's own shell for Fastify, FastAPI and net/http, which take the source as an argument, and by a discovered resource class for Quarkus and Spring. So one flip is one restart and no deploy is owed, and `make flag` prints that. `apps/<web>/src/flags.ts` is that side of it, and it comes in two shapes for one contract: under a target it asks the service, under `--target none` it reads what `.env` put in the bundle, because there is no environment to ask and hiding a half-built screen locally is still the point. `src/slipwai/project/flag_route.py` is the wiring — one placeholder pair per entry point, removed rather than left unresolved where there is no reader. The *service* side is a generated file too — one reader per backend, from `src/slipwai/project/flags.py`, emitted only under a target — and `scripts/check-flags.py` runs inside the generated `make verify`: a key declared and never read, read and never declared, new and seeded anything but `off`, tested on one path only, or read by naming the variable rather than calling that reader, fails the gate. The last of those is a pair with how the gate sees a read at all — the variable is matched so a hand-derived read still counts for the first two rules, and reported so that allowance is not permission to bypass the reader. `docs/deployment.md` in the generated project carries the rest: which undo button a bad flip needs, why the flip is the one production change outside the pipeline, and that both revisions of a blue/green deploy read the same parameter. |
| `scripts/check-deploy-role.py`, `make check-deploy-role` | Part of `make verify`: every `aws_iam_*` resource in `infra/service/` held to the IAM the bootstrap stack grants the deploy role — PowerUserAccess and roles named `<project>-*` — so IAM of another kind fails the pull request rather than the production apply; and `scripts/deploy.py` turns an apply refused on an `iam:` action into the fix, a bootstrap statement and `make bootstrap` |
| `.github/workflows/deploy.yml` | Build once, push, apply staging, smoke, apply production, smoke — started by `verify.yml` completing on `main` (`workflow_run`, Gitea 1.24 or later), and only if it passed, so the deploy never runs beside the gate or ahead of it; every job checks out the commit that run verified, not the head of `main`. The production job alone carries a condition, `vars.AUTO_PROMOTE != 'false'` — `!=` rather than `== 'on'` so a repository bootstrapped before that variable existed, which has none, keeps deploying production exactly as it did. One file for both forges: `configure-aws-credentials` is given the role and the (possibly empty) key secrets, and uses the key only when one is present. The deploy jobs take nothing from the build job — `scripts/deploy.py` resolves the commit's images from the registry by tag — so no artifact store is involved, which is also what lets it run under Gitea Actions. |
| `.github/workflows/production.yml` | The other way production is reached, and without auto-promotion the only one: started by `make promote` or by hand, it resolves the commit staging is running from staging's release record, checks *that* commit out, and runs `make deploy ENV=production` and `make smoke`. Nothing is built — the images are the ones staging ran, found by the commit's tag — and a commit given explicitly is refused unless staging has a release of it, so production is only ever given what staging has run. In a project that does not auto-promote this is also what *creates* production: until it first runs, that workspace is empty, and `make url ENV=production` and `make rollback ENV=production` say so rather than failing on a missing output. |
| `.github/workflows/rollback.yml` | Started by hand (`workflow_dispatch`, one `choice` input: `staging` or `production`): `make rollback` then `make smoke` in that environment. No build step and no toolchain — a rollback promotes images that already ran there. Same `concurrency` group as the deploy, so neither can cross the other. |
| `docs/adr/0002-production-target.md`, `infra/README.md`, a README section, `AGENTS.md` rules | The decision table with the cost, the bootstrap walk-through, and what an agent working in the project may and may not do (never `tofu apply` production by hand). |

Before any of it, `generate` checks the machine: choosing `aws` refuses unless `tofu`, the `aws` CLI and
`gh` or `GITEA_TOKEN` are present (`src/slipwai/preflight.py`; `--skip-checks` for a machine that will
not run `./init`), and `./init` checks the same three again before asking where to push, leaving the
bootstrap for later rather than failing halfway if one has gone.

It checks the project's name too. Everything this stack creates is named after the project, and Cognito
refuses a hosted-login domain prefix containing `aws`, `amazon` or `cognito` — the prefix here is
`<project>-<environment>-staff` — so a project whose name carries one of those words is refused at
generation. Left to run it would apply cleanly for three minutes and then fail on the two domains, with the
cluster, the balancer, the distributions and both user pools already created. The name is the only thing
that fixes it, and generation is the last moment it is still a choice. The whole list is those three words —
`amazon`, `aws` and `cognito` — each refused **anywhere** inside the name rather than only as a whole word.

Under `aws` the menus change: SQLite is not offered (the file dies with the task), `--http none` is refused
(the target deploys an HTTP service and `/health` is what proves a deploy), and Keycloak becomes Cognito on
both identity axes — with Keycloak kept as the local stand-in, same groups, same `OIDC_*` keys, and one new
key, `OIDC_GROUPS_CLAIM`, because Cognito writes groups to `cognito:groups`. [Project shape](axes.md#production-target)
has the tables.

## The trust names three subjects, because GitHub issues three

A workflow asking GitHub for a token gets one whose `sub` claim describes the job, and the shape of that
description depends on the job. A job with no `environment:` is described by its ref —
`<prefix>:ref:refs/heads/main`. A job that declares one is described by the environment *instead* —
`<prefix>:environment:staging` — with no ref in the claim at all. Both are the same repository and the same
push; GitHub simply says a job that deploys to an environment by naming the environment.

Every job in this target that applies anything declares one: `deploy.yml`'s `staging` and `production`,
`production.yml`'s `promote`, and `rollback.yml`, whose environment is the dispatch input. So the deploy
role's trust names all three subjects — the ref form and one per environment — and the environment set is
closed enough to list rather than wildcard, because `infra/service/variables.tf` admits `staging` and
`production` and refuses anything else. `environment:*` would be a trust that grows every time somebody
creates an environment, which is not a decision anyone makes with that in mind.

Listing them gives away what the ref form carried for free: an environment subject says nothing about the
branch, so on its own it would let a job on any branch declare `environment: staging` and become the deploy
role — and `rollback.yml` is a `workflow_dispatch`, which is run from a branch by choosing one. The branch
goes back on the forge rather than in the policy: `make bootstrap` creates both environments with a
deployment branch policy naming `main`, so GitHub refuses to start a job pointed at one from anywhere else
and no such token is minted. A custom policy naming `main` rather than `protected_branches`, which admits
whatever branches happen to carry a protection rule: the repository `./init` has just created protects none,
so that setting would admit nothing at all, and it would widen by itself the day somebody protects a second
branch. The two halves are one change; either alone is either a pipeline that cannot deploy or a role any
branch can assume.

None of this applies to Gitea, which has neither OIDC federation nor an environments API: there the pipeline
signs in with the access key `make bootstrap` stored as repository secrets, and `scripts/bootstrap.py` skips
the environment step rather than failing on an endpoint that is not there.

## How migrations run in production

Locally, `make migrate` is an explicit act against the Compose database. In production the shape depends on
the backend, and each is the ecosystem's own rather than a step written twice (`images.py`,
`MIGRATIONS_IN_PRODUCTION`):

| Backend | How |
|---|---|
| TypeScript, Python | The service's own image, run once as a Fargate task inside the VPC with the same `migrate` command the Makefile runs locally — through the buildpack launcher, `/cnb/lifecycle/launcher`, because the image's own entrypoint is the web process and starts that whatever command it is handed. `make deploy` does it *before* the new revision rolls — the migrate task definition is applied alone with the new image (the pipeline's one targeted apply), the task runs, then the whole stack is applied — so an expand migration is in place while the old release still serves. A fresh environment is applied whole and migrated after. `make migrate-remote ENV=…` does it alone. |
| Go | ko builds one binary per image, so `cmd/migrate` becomes a second image (`<service>-migrate`, its own ECR repository) and the task runs that. The `.sql` files are compiled into that binary (`migrations/embed.go`); ko ships nothing else beside it, so a runtime filesystem read would miss migrations the repository has. An empty `*.sql` set is still success — Minimum CD may ship before any schema. |
| Quarkus, Spring Boot | The framework migrates as the service starts, switched on by one environment variable in production only (`QUARKUS_FLYWAY_MIGRATE_AT_START`, `SPRING_FLYWAY_ENABLED`). Flyway holds a lock, so replicas take turns. Locally the default stays off, for the reasons the properties files give. |

Either way, the release before and the release after share the database for a while, and a rollback is the release before on the schema the release after left. Both are safe only under expand/contract, which the generated `make check-migrations` holds every migration to (`scripts/check-migrations.py`): a drop, rename, type change or new NOT NULL column must name the earlier additive migration it completes, and may not arrive in the same change as it.

The database is not reachable from outside the VPC — not from a laptop, not from a runner — which is why
the task exists at all.

## How a service reaches the database, and why TLS is not in the URL

RDS refuses unencrypted connections. `rds.force_ssl = 1` has been the `default.postgres*` value since
Postgres 15, and `rds.tf` now states it in a parameter group of its own rather than inheriting it, so the
policy and the setting that satisfies it sit in the same repository. A client that does not ask for
encryption is turned away before authentication, with SQLSTATE `28000` — `no pg_hba.conf entry for host
"…", user "app", database "app", no encryption`.

The client half is `PGSSLMODE` in the container environment, per backend, on **both** task definitions —
the long-running service and the one-off migrate task, which read the one `local.service_environment` map
so the two can never disagree about how they reach the same database. The posture is the same everywhere:
encrypted, not verified. What differs is how each driver can be told, and that is the whole reason
`images.py` carries a table (`POSTGRES_SSLMODE`) instead of one constant. Every row was settled by running
the driver against a Postgres configured the way RDS is — `ssl=on` with a self-signed certificate and
`hostnossl … reject` — because two of the three answers are not the documented-looking ones:

| Backend | `PGSSLMODE` | Why, and what was measured |
|---|---|---|
| TypeScript | `no-verify` | `node-postgres` reads this variable with its own vocabulary, not libpq's: `require` there means *verify* the server certificate against Node's bundled CA store, and RDS's certificate chains to Amazon's private RDS root CA, which is not in it. Unset → `28000`; `require` → `DEPTH_ZERO_SELF_SIGNED_CERT`; `no-verify` → connected over TLSv1.3. The only backend whose default is no TLS at all, and so the only one that was actually broken. |
| Python, Go | `require` | psycopg (libpq) and pgx (its own libpq-compatible parsing) honour it with libpq's semantics, where `require` already means "encrypt, do not verify". `require` → connected over TLSv1.3; `disable` → refused with `28000`, which is what proves the variable is read rather than merely harmless. Their default is `prefer`, so they reached RDS anyway; `require` is what stops a silent fall back to plaintext. |
| Quarkus, Spring Boot | *nothing* | pgjdbc does not read `PGSSLMODE` — the string appears nowhere in `postgresql-42.7.13.jar`, whose `PGEnvironment` reads only `PGPASSFILE`, `PGSERVICEFILE` and `PGSYSCONFDIR`. With `PGSSLMODE=disable` exported it still connected over TLSv1.3: ignored in both directions. Setting it would be a setting with nothing behind it. pgjdbc's own default is `prefer`, so these two already negotiate TLS and never verify — the same posture — and the parameter group above is what makes "prefer" mean "always". |

`no-verify` is not a libpq value and libpq errors on it, so one value shared by all five would have failed
four of them whichever value was picked — which is the short version of why this is a table.

`DATABASE_URL` says nothing about TLS, on purpose. It is one libpq-style string shared by every backend, and
an `sslmode` inside it means three different things at once: `pg-connection-string` turns *any* `sslmode`
into TLS with Node's default `rejectUnauthorized: true` unless the non-libpq keyword `uselibpqcompat=true`
is also in the string — which libpq itself rejects, so it cannot go in a URL the other backends read — and
`pg` lets whatever it parsed from the string override `PGSSLMODE` outright, closing off the route that does
work. The URL stays the address and the credentials.

Two follow-ups, both deliberately out of this change and both recorded in the *Database TLS* row a generated
project's `docs/adr/0002-production-target.md` carries, so the reader hits them where the decision lives:

- **Stating the posture on the client for the Java backends.** The knob is `sslmode` as a *datasource
  property* rather than an environment variable, and its env-var spelling differs per framework
  (`quarkus.datasource.jdbc.additional-jdbc-properties.sslmode` against
  `spring.datasource.hikari.data-source-properties.sslmode`). It cannot be locally proved without a TLS
  Postgres and a built application, so it wants its own change with a test that runs one — not a line added
  on the strength of the documentation, which is exactly how `PGSSLMODE` came to be believed of pgjdbc.
- **Verifying the server certificate** — `verify-full` with an `sslrootcert`. Amazon's RDS root CA bundle
  has to reach every image, by a path that differs per builder (`/workspace/…` for Paketo, `$KO_DATA_PATH`
  for ko's distroless Go images) while the secret is shared by all of them. That wants an ADR, not a patch.

## What it costs while idle, and how a project pays for one environment

About $9 a month per service for the smallest Fargate task and about $18 for its load balancer, about $12
for the database after the first free year; Cognito and CloudFront sit inside their free tiers at this scale.
Two environments, twice that; a second task per service in production, another $9. Nothing scales to zero, on
purpose.

Which is the whole reason production is a decision and not an assumption. `make bootstrap` writes a
`AUTO_PROMOTE` repository variable beside the identifiers, from `--auto-promote`/`AUTO_PROMOTE=`, else
`infra/auto-promote` — the answer a previous run wrote down, committed like `infra/region` so a second
bootstrap after `add-service` writes the answer this project already gave — else asked once in a terminal,
else `true`. `./init --auto-promote false` answers ahead. Two values:

| `AUTO_PROMOTE` | The pipeline | Production |
|---|---|---|
| `true` (default, and absent) | build, staging, smoke, production, smoke | on every commit that passes `verify` on `main` |
| `false` | build, staging, smoke | only when `production.yml` runs: `make promote`, or the Actions tab |

The saving is only in the days before the first promotion — once production exists it costs the same in
either way — so declining it buys a project the choice of when to start paying, and a person between staging
and production if it wants one. Both modes deploy the digests staging ran, and neither applies from a
laptop: `make promote` dispatches the workflow (`gh workflow run` on GitHub, the dispatch endpoint on Gitea)
and the runner applies with the deploy role. Turning production back *off* is not a flag — the tasks and the
database exist by then — and is the reason the `destroy` verb exists.

Both halves of the Gitea behaviour this rests on were proved against Gitea 1.27.3 rather than read: a
job-level `if: vars.AUTO_PROMOTE != 'false'` skips the job when the variable is `false` and runs it when the
variable is absent, and `POST /api/v1/repos/{owner}/{repo}/actions/workflows/{file}/dispatches` starts a run
whose `inputs` reach it.

## Identity has a third answer, and it is not Amazon's

`--auth` and `--users` under this target offer `cognito` and `auth0`. Cognito is the like-for-like answer and
stays the one this page describes; Auth0 is here because a third-party issuer is not a property of a cloud,
and because `azure` had no customer-identity answer without it — azurerm has no resource for an Entra
External ID tenant and azuread none for a user flow, so Microsoft's product could not be a row at all.
Rather than give one cloud a row the other could not have, the answer is offered under both.

It is the one row in this factory whose infrastructure the deploy role does not create. `infra/service/
auth0.tf` is applied with a machine-to-machine application's own credentials, and the tenant and that
application are made by a person before the first apply. [`auth0-identity.md`](auth0-identity.md) has what
that costs, including the one place it is genuinely weaker than Cognito: staff and customers share an
issuer there, so `aud` is what separates their tokens rather than `iss`.

## What the factory proves, and what it cannot

- **Every stack validates against the real provider.** `tests/test_aws_target.py` runs `tofu validate` over
  the bootstrap and service stacks of a maximal and a minimal project, and again after `./init` has pruned
  the maximal one down to the in-memory store and no identity — so a pruned stack is still one stack. The
  factory's CI installs OpenTofu and downloads the pinned AWS provider once per run for it.
- **One backend's image builds and answers.** The same test builds the Go service with `ko` and runs `make
  smoke-image`, which starts the image and asks it `/health` — the two targets a generated project's `make
  ci` runs. Quarkus's Jib build was proved by hand while this was written (9 seconds, `/health` `UP`);
  Spring's `build-image` and the two Paketo builds were not run to completion here — Spring's because the
  sandbox blocked a Maven Central download, Paketo's because of the point below. All three are run by no gate
  at either level, which is the same honest state `make adversarial` is in (`docs/backend-obligations.md`,
  section 2).
- **The trust is held to the jobs, not to a remembered string.** `tests/test_aws_forge.py` reads every
  environment the generated workflows deploy to out of the workflows — resolving `rollback.yml`'s dispatch
  input to its choices — and every `sub` value out of the generated trust policy, and fails unless the two
  agree both ways. The old test asserted the one subject line verbatim, which proved the prefix
  interpolation and never that the suffix covered the jobs beside it; that is how a trust naming only
  `:ref:refs/heads/main` shipped for as long as this target has existed. What is still unprovable here is
  the branch policy, which lives in a repository: the test asserts the calls `make bootstrap` makes and
  that a refusal is reported rather than raised, and an account is what proves the rest.
- **`make bootstrap` is proved to its decisions, not to an account.** `scripts/bootstrap.py --plan` prints what
  it would do — which forge it read off the remote, which credential shape follows, what it would apply and
  configure — and the test drives it with a GitHub-shaped and a Gitea-shaped remote, and with none (a
  refusal that says to push first).
- **What the container is told is asserted, because nothing runnable can catch it.** The emitted
  `docker-compose.yml` runs `postgres:17-alpine` with no TLS, so it accepts a connection RDS refuses — every
  local gate, `make migrate` and the integration suite included, passes on a project whose first deploy would
  fail with `28000`. `tests/test_postgres.py` therefore asserts the environment on both task definitions per
  backend, and the two facts about `pg` and libpq it depends on were read off the pinned packages
  (`pg@8.23.0`, `pg-connection-string@2.14.0`) rather than assumed.
- **The apply is unprovable by construction.** It ends in somebody's account. What proves it is `make
  smoke` against the environment the pipeline just deployed, which is why the pipeline runs it after each
  apply and why the first thing to do with a generated project is to push it — and why the commit `./init`
  pushes has to pass `verify` as it stands. Every gate in it does, including `make check-constitution`, which
  lets the untouched constitution template through until `/speckit-constitution` has written the file or a
  feature exists under `specs/` ([Bootstrap Spec Kit](spec-kit.md#the-constitution-is-gated-from-both-sides)).
  The walking skeleton reaches production before the first principle is written, not after.
- **`pack` and Docker's containerd image store.** A Docker daemon using the containerd store — Docker Desktop's
  default since 4.34 — cannot export a `pack` build to itself (buildpacks/pack#2272). The Makefile passes
  `--publish` whenever `IMAGE_REGISTRY` is set, which is the path CI takes and the workaround locally (`PACK_FLAGS="--network host"` lets `pack`'s containers reach a registry on localhost): point it
  at a registry. `ko`, Jib and Spring's build are unaffected.
- **One provider defect worked around**, recorded in the ADR: the provider re-sends an ECS service's
  load-balancer block on every update, which under blue/green makes every deploy land on the same target
  group (hashicorp/terraform-provider-aws #45678). `ignore_changes` on that block and on the listener rule's
  action is the workaround; the first real blue/green deploy is what proves it.

## The next cloud is a row

Everything here was shaped so Azure is a second row in the same tables rather than a second set of branches:

1. `catalog.json`: a `targets.azure` entry with a label and, if it deploys an HTTP service, `requires`; the
   options offered under it gain `"azure"` in `targets`, and the ones it provisions differently say so under
   an `"azure"` key. The pruner's `AXES` and `TARGET_REQUIRES` mirror both.
2. `assets/targets/azure/`: the stacks, read as a tree by `project/infra.py`, with feature-owned parts inside
   `backing-service:<feature>` markers and a `frontend.tf`/`no-frontend.tf` pair.
3. `images.py` is cloud-neutral; the workflow's credential step and the deploy script's cloud calls are the
   two things that are not, and `deploy_workflow.py` and `scripts/deploy.py` are where a second cloud's spelling
   goes.
4. `tests/test_aws_target.py` is the shape of the tests: files present, menus changed, stacks validate before
   and after a prune, one image builds and answers.

`.claude/skills/add-target/SKILL.md` is the procedure.
