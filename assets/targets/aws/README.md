# Infrastructure: the path to production

Two OpenTofu stacks, and two scripts the Makefile hands the production verbs to.

| Directory | What it is | Who applies it |
|---|---|---|
| `bootstrap/` | The state bucket, the pipeline's identity (a deploy role, and either a GitHub OIDC trust or an IAM user that may only assume that role), and one image repository per service. Its own state is committed here, encrypted. | `make bootstrap` — a person, once, with administrator credentials; again when a service is added. |
| `service/` | Everything an environment is: one ECS service per application on Fargate, deployed blue/green behind its own load balancer and CloudFront distribution, and whatever the answers asked for — the database, the user pools, the site. `staging` and `production` are workspaces over this one directory. | The pipeline, on every push to `main`. `make deploy ENV=…` runs the same code path from a laptop. |
| `../scripts/bootstrap.py` | What `make bootstrap` runs: reads the forge from the remote, applies `bootstrap/`, writes the outputs to the repository as variables and secrets. `--plan` says what it would do. | `make bootstrap`. |
| `../scripts/deploy.py` | `push`, `smoke-image`, `deploy`, `rollback`, `promote`, `migrate`, `smoke`, `url` — the verbs behind the other production targets. | Whatever runs `make`. |

`docs/deployment.md` draws what these stacks provision for the project's own services, and is regenerated with
them; `docs/adr/0002-production-target.md` is why each part is what it is, and what it costs.

## Before `./init`

`./init` does this project's first day: it installs Spec Kit, then asks for the repository to push to,
pushes `main`, and runs `make bootstrap` against your AWS account — so the push is the first deploy, and
everything below is what that last step needs. Have all of it on the machine that runs `./init`. A later
`make bootstrap` — after `add-service`, say — wants the same list, except that row 7 is then a passphrase to
supply rather than one to keep.

| | Have | What needs it | Proof it is there |
|---|---|---|---|
| 1 | **Python 3**, and **`uv`** or network access for `pip` | Spec Kit is installed with one of them, and every script under `scripts/` is Python | `uv --version` · `python3 --version` |
| 2 | **OpenTofu 1.12**, on the PATH as `tofu` | applies `bootstrap/` now and `service/` on every deploy after | `tofu version` |
| 3 | **The `aws` CLI, signed in as an administrator** of the account this project will live in — a profile, SSO, or environment variables, whatever the CLI finds; `AWS_PROFILE=<admin profile> ./init` is the usual spelling | `bootstrap/` creates an S3 bucket, a deploy role, an OIDC provider or an IAM user, and an ECR repository per service — a CI user or a developer role usually cannot | `aws sts get-caller-identity` names that account |
| 4 | **A region** — `export AWS_REGION=eu-west-2`, or `aws configure set region eu-west-2` — unless `infra/region` is already committed | where all of it is created; it is written to `infra/region`, which every later `make bootstrap`, `make deploy` and `make url` reads | `aws configure get region` |
| 5 | **Access to your forge.** GitHub: `gh` on the PATH and signed in. Gitea: `GITEA_TOKEN` set to a token with `read:user` and `write:repository` — plus `write:organization` if the repository will belong to an organisation | it creates the repository, private, if it is not there, and writes the variables and secrets the pipeline signs in to AWS with | `gh auth status` · `echo ${GITEA_TOKEN:+set}` |
| 6 | **The repository's URL**, if `origin` is not set yet — `https://github.com/<owner>/<name>`, `http://localhost:3300/<owner>/<name>` — and whatever a `git push` to it needs | the pipeline is configured on the forge, so the bootstrap has to know which repository this is | `git remote get-url origin` |
| 7 | **Somewhere to keep a passphrase.** The first `make bootstrap` generates one and prints it once; every run after it needs the same one back in `TF_VAR_state_passphrase` | it encrypts `bootstrap/terraform.tfstate`, which is committed to this repository | a password manager |

**One more, only where this project answered `--auth auth0` or `--users auth0`:** an **Auth0 tenant**, and
one **machine-to-machine application** inside it authorised for the Auth0 Management API — allowed to read
and write clients, connections, resource servers and roles. Auth0 is a third party: the deploy role
this bootstrap creates owns everything else in the stack and owns nothing there, so `infra/service/auth0.tf`
is applied with that application's own credentials. `make bootstrap` asks for `AUTH0_DOMAIN`,
`AUTH0_CLIENT_ID` and `AUTH0_CLIENT_SECRET` (or takes them from the environment), puts the first two on the
forge as variables and the third as a secret, and the deploy workflows pass all three to `tofu`. There is no
API for creating a tenant, which is why those two things are yours to make and everything inside them is the
pipeline's. A project that answered neither axis with Auth0 is asked for none of it, and carries no Auth0
provider at all.

Nothing is applied until all of it is there, and a gap is found before the work rather than halfway through
it:

- **When the project was generated**, rows 2–5 were checked on that machine — `generate` refuses `--target
  aws` without them, unless `--skip-checks` said another machine would run `./init`.
- **At the top of `./init`**, before Spec Kit is installed: `tofu`, `aws`, and `gh` or `GITEA_TOKEN`. Missing
  one, it names it, does the rest of the local work anyway, and leaves the push and the bootstrap for later —
  `./init --repository <url>` once it is there, or push and `make bootstrap`. `./init --skip-bootstrap`
  leaves them deliberately.
- **Inside `make bootstrap`**, before the apply: the tools again; the region, asked once in a terminal if
  nothing else says and written to `infra/region`; who the CLI is signed in as, printed; and whether that
  identity may create what the stack creates, simulated — denied, it refuses naming the actions, having
  applied nothing. `scripts/bootstrap.py --plan` prints every one of those decisions and changes nothing.
- **How production is deployed**, asked once in a terminal by `make bootstrap` if nothing else says, and
  written to `infra/auto-promote`: `on` — the default — deploys production on every commit that passes
  `verify` on `main`; `false` deploys staging on every green push and leaves production to `make promote`.
  `make bootstrap AUTO_PROMOTE=true|false` or `./init --auto-promote …` answers ahead, and either way the answer
  reaches the forge as the `AUTO_PROMOTE` variable, which is the only thing `deploy.yml` reads to decide.

An environment costs money from the moment it exists, and turning auto-promotion off is what leaves production uncreated
until `make promote`; `docs/adr/0002-production-target.md` says how much.

## Bootstrap, once

The first commit carries the pipeline and the infrastructure. What it cannot carry is the account: someone
with administrator credentials has to create the place state lives, the identity the pipeline may assume, and
the repositories images go to, and then tell the repository where they are. That is `make bootstrap`, and
`./init` runs it: after installing Spec Kit it asks for the repository to push to (created on the forge if it
is not there — `gh` on GitHub, `GITEA_TOKEN` on Gitea), pushes `main`, and bootstraps. `./init --repository
<url>` answers ahead; `./init --skip-bootstrap` leaves it for later, when it is one command:

```sh
git remote add origin <your repository> && git push -u origin main   # the pipeline is configured on the forge
make bootstrap
```

Once. A later `./init` — to answer an axis again, add an extension, or switch agent — finds
`bootstrap/terraform.tfstate` committed, says so, and leaves the account alone; it needs no credentials.
Re-applying the stack is `make bootstrap`, run by hand with the passphrase.

Everything it needs is the table above. `make bootstrap REPOSITORY=owner/name FORGE=github|gitea|none`
overrides what it reads from the remote; `scripts/bootstrap.py --plan` prints its decisions and changes
nothing.

What it does, in order:

1. Settles the region (asking once, if nothing says), then signs in and says which account and identity it
   is using.
2. Generates the passphrase that encrypts the committed bootstrap state — on a first run; afterwards it needs
   the same one in `TF_VAR_state_passphrase` — and prints it once at the end. Keep it in a password manager.
   Nothing but a later `make bootstrap` ever needs it.
3. Applies `bootstrap/`. On GitHub the pipeline will sign in with a short-lived OIDC token and no stored
   credential; the trust names this repository and nothing else, spelled the way GitHub spells it in the
   token — the script asks the repository's OIDC customization endpoint for the `sub` prefix, since a
   repository created after 15 July 2026 is `repo:owner@<id>/name@<id>` rather than `repo:owner/name` —
   and it names three subjects, because GitHub describes a job by its ref (`:ref:refs/heads/main`) only
   when the job declares no `environment:`, and by the environment (`:environment:staging`,
   `:environment:production`) when it does. Every job that deploys here declares one. On Gitea, or any forge
   without OIDC federation, it creates an IAM user whose only permission is to assume the deploy role, and a
   key for it.
4. Writes the outputs to the repository: variables `AWS_REGION`, `TOFU_STATE_BUCKET`, `AWS_DEPLOY_ROLE_ARN`
   and `IMAGE_REGISTRY` — identifiers, not confidential — and, on a forge without OIDC, the secrets
   `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. The generated `deploy.yml` takes both shapes and uses the
   key only when one is present. On GitHub it also creates the `staging` and `production` environments,
   each with a deployment branch policy naming `main`. That is what holds the environment subjects above to
   this branch: they carry no ref of their own, so without it a job on any branch could declare
   `environment: staging` and become the deploy role. Run again, an environment that is already there and
   already names `main` is left as it is; a forge that refuses the call — environment protection rules need
   a paid plan on a private repository — says so and says what is left to set under Settings → Environments.
   Gitea has no environments API and no OIDC subject to hold, so the step is skipped there.
5. Tells you to commit `bootstrap/terraform.tfstate`, `bootstrap/.terraform.lock.hcl`, `infra/region` and
   `infra/auto-promote`, and push.

The push that follows is the first deploy, once `verify` has passed on it: build, push by digest, apply
`staging`, smoke, apply `production`, smoke. Both environments exist already, made by `make bootstrap` with
the branch policy the trust depends on. Without auto-promotion that first deploy stops after staging and
production is not created at all; `make promote` is what creates it, whenever this project wants it.

## Every commit that passes verify on main

`.github/workflows/deploy.yml` starts when `verify.yml` completes on `main` (a `workflow_run`), and only goes
on if it passed — so the deploy never runs beside the gate or ahead of it, and a commit the gate failed is
never applied. Then: `make build push` once, `make deploy ENV=staging`, `make smoke`, `make deploy
ENV=production`, `make smoke`. Every job checks out the commit `verify` passed
rather than the head of `main`, which a later push may already have moved; that later push gets its own
verify run and its own deploy, queued behind this one. The deploy jobs need nothing from the build job —
`scripts/deploy.py` finds the commit's images in the registry by tag — so the workflow uses no artifact store
and runs on GitHub Actions and Gitea Actions alike (`workflow_run` needs Gitea 1.24 or later).

The production job carries one condition, `vars.AUTO_PROMOTE != 'false'`, and that variable is the whole of
the choice: `true` (or a repository with no such variable, which is every one bootstrapped before this
existed) runs it, `false` skips it and leaves production to the workflow below. There is no approval step
either way — declining auto-promotion is a project deciding it has no production yet, or wants a person to
say when, not a gate inside this pipeline.

`.github/workflows/production.yml`: started by `make promote` or by hand from the Actions tab. It resolves
the commit staging is running from staging's own release record, checks *that* commit out, and runs `make
deploy ENV=production` and `make smoke`. Nothing is built: the images it deploys are the ones staging has
already run, found in the registry by the commit's tag. Given a commit explicitly it refuses any that
staging has no release of, so this is not a way round the gate. It is also how production is created in a
project that does not auto-promote — until it first runs, that workspace is empty and `make url ENV=production` says so.

`.github/workflows/rollback.yml`: started by hand from the Actions tab, with the environment to roll back. It
runs `make rollback ENV=…` and `make smoke`, builds nothing, and shares the deploy's concurrency group so the
two never overlap. The next push to `main` deploys forward again — a rollback buys time to fix `main`.

## Schema changes

A deploy rolls, so for a while the release before and the release after run against one database — and
`rollback.yml` puts the release before back without touching the schema. Both are safe under expand/contract,
which `make check-migrations` holds every migration to: add first (a table, a nullable column, a default), in
one deployment; remove or reshape in a later one, in a migration that names the expand it completes
(`-- contract: 003_orders_add_status`). `make deploy` runs the migrations *before* the new revision rolls,
where the backend runs them as a task, so the expand is in place when the new release arrives.

## From a laptop

The same verbs, with the same four values in the environment and credentials the `aws` CLI can find:

```sh
export TOFU_STATE_BUCKET=… IMAGE_REGISTRY=…    # from the bootstrap outputs; the region is in infra/region
make build smoke-image PLATFORM=linux/arm64   # the images, run locally and asked their probe
make build push                               # into ECR, digests recorded in .build/images.json
make deploy ENV=staging                       # apply, migrate, upload the site, record the release
make smoke URL=$(make -s url ENV=staging)
make rollback ENV=staging                     # the release before this one
make promote                                  # ask the forge to deploy production with what staging runs
```

Production is the pipeline's to deploy; `make deploy ENV=production` exists so the code path is one, not so
that it is used. `make promote` is the exception that proves it: it applies nothing itself, it asks the
forge to start `production.yml`, and the runner does the apply with the deploy role. It needs no AWS
credentials — on GitHub it uses `gh`, on Gitea a `GITEA_TOKEN` with write access — and `make promote
COMMIT=<sha>` promotes a specific release staging has run, rather than the newest.

## Feature flags

A flag is the one thing about a running environment that changes without a deploy. Declare it in
`service/flags.auto.tfvars`, seeded at whatever the service already does, and it reaches the container as
`FLAG_<KEY>` — an SSM parameter ECS resolves at task start, exactly the way it resolves a secret, so no
image carries an AWS SDK for it.

```sh
make flags ENV=staging                                   # what this environment is actually set to
make flag ENV=staging KEY=checkout-v2 VALUE=on           # write it, then restart the service that reads it
```

Two things to know. A flip is a rolling restart, not a live re-read: around two minutes, with no build, no
apply and no merge to `main` — but tasks already running hold the old value until they are replaced. And
the parameter, not the file, is the truth once an environment exists: `flags.tf` stops managing the value
the moment it has seeded it, so neither the next deploy nor `make rollback` puts a flipped flag back, and
editing the seed changes nothing in an environment that already has one.

### And a browser app

A browser app reads the same flag by asking the service for it, over `GET /api/flags` — the service answers
from the environment these parameters land in, so one product flag has one name and one value on both sides
of `/api`. A flip is the service's restart and nothing else: a browser already open picks the new value up on
its next load, and `make flag` says that no deploy is owed. `apps/<web>/src/flags.ts` is that side of it, and
`flagEnabled('checkout-v2')` is how the app asks; a flag is declared under the service the site's `/api` goes
to, which is the service that answers for it.

It was not always this way, and the reason is worth keeping. The bundle used to be built with
`VITE_FLAG_<KEY>` inlined from this environment's parameters, because Vite inlines a `VITE_`-prefixed value
while the bundle is *built*. That gave one product flag two clocks — the service's moving in a restart, the
browser's only on the next deploy — and every gated screen carried an ordering rule (on in the service first,
off in the bundle first) that existed only because of how the value arrived. Asking the service removes the
second clock and the rule with it.

`make rollback` no longer diverges here either. It restores the previous release's `index.html`, and that
bundle carries no flag values at all, so both halves read whatever this environment is set to now — which is
what a rollback should leave alone, the parameter being the one place a flip is recorded.

A flag that has to take effect *without* a restart is the other transport, and it is a per-environment
answer rather than a per-project one: set `flag_transport = "appconfig"` in `service/staging.tfvars` or
`service/production.tfvars` and that environment gets an AWS AppConfig agent beside each container, read
over loopback, with a flip that takes effect in seconds and no restart at all. `ssm` stays the default
everywhere, so an environment takes the sidecar on when a flag actually needs it.

Two things change with it, and both are worth knowing before you set it. There is a second container in
every task — the published agent image, the one image in this repository that the project does not build.
And the application gains its first AWS permission: under `ssm` the *execution* role reads the parameters
when it starts a task and the task role is untouched, while the agent runs inside the task and uses the
task role. `infra/service/flags.tf` has the whole argument, including why the stack owns the AppConfig
profile but not the document in it.

## Changing the stacks

### Adding IAM to the service stack

The deploy role applies `service/`, and it may create and delete only what `bootstrap/main.tf` grants it:
PowerUserAccess, which excludes IAM, and IAM back on roles named `<project>-*`. An IAM user, a managed
policy, an instance profile or anything else outside roles is refused by AWS at the production apply,
part-way, after the apply has changed what it reached first. `make check-deploy-role` — part of `make
verify` — reads both stacks and fails first, naming each `aws_iam_*` resource whose create or delete action
the role is not granted on that kind of resource. The fix is never in `service/` and never in the IAM
console: add the actions to a statement of `data.aws_iam_policy_document.deploy_iam` in `bootstrap/main.tf`,
scoped to this project's names the way the role statement is, and have a person with administrator
credentials run `make bootstrap` before the change merges. A deploy refused on an `iam:` action anyway says
the same thing.

### Renaming or retiring a resource

OpenTofu keys state by address, so renaming a resource block, or moving it into a `for_each` or a module,
reads as destroying the old address and creating a new one — unless a `moved` block says the two are one:

```hcl
moved {
  from = aws_cloudfront_response_headers_policy.web_noindex
  to   = aws_cloudfront_response_headers_policy.web
}
```

With it, the rename is an in-place update. Without it the apply creates the new resource, then destroys the
old one — and the old one's destroy is not ordered after the in-place update of whatever still uses it, so a
provider that refuses to delete something in use (CloudFront answers 409) fails the apply part-way, in every
environment it reaches. A block that is only being dropped from the code, while what it made carries on
existing or is removed by hand, is a `removed` block (`removed { from = … lifecycle { destroy = false } }`),
which forgets it rather than deleting it. Both stay in the stack until every environment has been applied
past them; `tofu plan` showing `has moved to` or `will no longer be managed`, and no destroy, is the check.

## What lives where

- **Environment variables the services are given** — `service/main.tf`, composed from what each answer
  provisions; a secret (the database URL, the client secret) is a Secrets Manager reference injected by ECS.
- **Sizes** — `service/staging.tfvars` and `service/production.tfvars` for tasks and scaling;
  `database_instance_class`, `postgres_version`, the callback URLs and the rest have defaults in the file
  that owns them, overridable there too.
- **The services themselves** — `project.auto.tfvars.json`, written by the factory from `project.json` and
  rewritten by `add-service`. Do not edit it by hand; it is regenerated.
- **Feature flags** — declared in `service/flags.auto.tfvars`, one SSM parameter per flag per environment,
  and the live value read with `make flags`. A flip is not in the release record below: that names a commit
  and its images, so "what was production running" is those two plus the flags at the time.
- **Releases** — `s3://<state bucket>/releases/<environment>/`, one JSON record per deploy, which is what a
  rollback reads.
