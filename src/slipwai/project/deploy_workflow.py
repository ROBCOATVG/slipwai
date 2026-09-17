"""`.github/workflows/deploy.yml`: build once, push by digest, apply staging, smoke, apply production, smoke.
`.github/workflows/production.yml`: started by hand, promote what staging is running.
`.github/workflows/rollback.yml`: started by hand, `make rollback` in the environment named, then smoke.

Only under a production target. The deploy starts when `verify` has passed on `main`, not when the push
lands: it is a `workflow_run` of `verify.yml`, so the two cannot run side by side and a commit the gate
failed is never applied. Every job checks out the commit that run verified (`workflow_run.head_sha`) rather
than whatever `main` points at by the time the job starts, and `scripts/deploy.py` reads the commit from the
checkout, so the images it resolves are that commit's.

The build job installs each language family's toolchain the way `verify.yml` does, plus whatever image
builder the families need. Every job becomes the deploy role one of two ways: on GitHub with the
repository's short-lived OIDC token and no stored credential; on a forge without OIDC federation (Gitea)
with the access key or client secret `make bootstrap` stored as a repository secret. The deploy jobs run
the same `make deploy` a person would, in order, each proved by `make smoke` before the next begins; they
need nothing from the build job, because `scripts/deploy.py` resolves the commit's images from the registry
by tag.

The production job is the one part of that a project can decline. `make bootstrap` asks whether to
auto-promote to production and writes the answer to the forge as `AUTO_PROMOTE`; that job runs unless it
reads `false` — the test is `!=` rather than `==` so a repository generated before this existed, which has
no such variable, keeps deploying production exactly as it did. Without auto-promotion, staging still
deploys on every green push and production waits for `production.yml`:
started by hand or by `make promote`, it resolves the commit staging is running, checks *that* out, and
deploys it. So production is only ever given images staging has already run, whichever way it is reached,
and no laptop ever applies it.
"""
from __future__ import annotations

from ..images import KO_VERSION, PACK_VERSION, tools_needed
from ..services import App, backends_of, families_of, services_of, web_apps
from .ci_workflows import NODE_SETUP, toolchain_setup

TOFU_VERSION = "1.12.6"

# The commit `verify` passed, which is not always the head of `main` by the time this job starts: a second
# push may have landed, and its own verify run will bring its own deploy.
CHECKOUT = """      - uses: actions/checkout@v6
        with:
          ref: ${{ github.event.workflow_run.head_sha }}
"""

# Both spellings, on purpose: the secrets are empty on GitHub, where the OIDC token does the work, and set on
# a forge without one, where the key signs in and the role is assumed with it. Written by `make bootstrap`.
CREDENTIALS = """      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
"""

# GitHub's hosted runners ship the `aws` CLI; act's default ubuntu image — what a local Gitea runner uses —
# does not, and `make deploy`, `make rollback` and `make url` all hand off to `scripts/deploy.py`, which
# shells out to it. So every job that runs those verbs installs the CLI itself, right after checkout;
# `--update` makes it a no-op on a runner that already has one. The build job needs no copy: `make build
# push` is docker-only, and the credential and ECR-login actions are JavaScript on the SDK, not the CLI.
# The architecture comes from the runner itself — AWS names the installer with exactly what `uname -m`
# answers (`x86_64`, `aarch64`), and a local runner is as likely to be ARM as a hosted one is not.
AWS_CLI = """      - run: |
          curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o awscliv2.zip
          unzip -q awscliv2.zip && sudo ./aws/install --update
"""

# `azure/login` has no `client-secret` input: given the three identifiers it always asks GitHub for an OIDC
# token. Choose that path only when bootstrap stored no secret. On Gitea the jobs already install `az`, so
# use its service-principal login directly; environment variables preserve secrets containing JSON-significant
# characters without trying to interpolate them into `azure/login`'s `creds` JSON input.
AZURE_CREDENTIALS = """      - if: ${{ secrets.AZURE_CLIENT_SECRET == '' }}
        uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - if: ${{ secrets.AZURE_CLIENT_SECRET != '' }}
        env:
          AZURE_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}
          AZURE_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}
          AZURE_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}
          AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
        run: |
          az login --service-principal \\
            --username "$AZURE_CLIENT_ID" \\
            --password "$AZURE_CLIENT_SECRET" \\
            --tenant "$AZURE_TENANT_ID"
          az account set --subscription "$AZURE_SUBSCRIPTION_ID"
"""

# GitHub's hosted runners ship the `az` CLI; act's default ubuntu image — what a local Gitea runner uses —
# does not, and `make deploy`, `make rollback` and `make url` all hand off to `scripts/deploy.py`, which
# shells out to it. So every job that runs those verbs installs the CLI itself, right after checkout. The
# build job needs one too, unlike its AWS counterpart: `az acr login` is what signs the daemon in to the
# registry, where ECR has a JavaScript action that never touches the CLI. Microsoft's own installer script
# is a no-op on a runner that already has one.
AZURE_CLI = """      - run: |
          command -v az >/dev/null 2>&1 || curl -sSL https://aka.ms/InstallAzureCLIDeb | sudo bash
"""

TOOL_SETUPS = {
    "pack": f"      - uses: buildpacks/github-actions/setup-pack@v6.1.0\n        with:\n          pack-version: {PACK_VERSION.lstrip('v')}\n",
    "ko": f"      - uses: ko-build/setup-ko@v0.10\n        with:\n          version: {KO_VERSION}\n",
}

# Everything in these three workflows that is one cloud's rather than every project's, per target: the CLI
# a runner may not ship, how a job becomes the deploy identity, how it signs in to the image registry, and
# what the stacks and `scripts/deploy.py` read out of the environment. The shape around them is the promise
# and not the cloud — `verify` passes on `main`, one apply at a time, apply then smoke, production behind
# `AUTO_PROMOTE`, a rollback that re-applies the release before — so a second cloud is a row here.
# The one credential in a deploy that the cloud did not issue: the Auth0 tenant's, which `infra/service/
# auth0.tf` is applied with. Added to the workflow environment only for a project that answered an identity
# axis with Auth0 — an empty `AUTH0_DOMAIN` in every other project's workflow would read as configuration
# and do nothing, which is the one thing a generated file here may never be. `tofu` takes all three from the
# environment, so no step passes them and no log line can carry the secret.
AUTH0_ENVIRONMENT = (
    "  AUTH0_DOMAIN: ${{ vars.AUTH0_DOMAIN }}\n"
    "  AUTH0_CLIENT_ID: ${{ vars.AUTH0_CLIENT_ID }}\n"
    "  AUTH0_CLIENT_SECRET: ${{ secrets.AUTH0_CLIENT_SECRET }}\n"
)

CLOUD_STEPS = {
    "aws": {
        "cli": AWS_CLI,
        "credentials": CREDENTIALS,
        # The build job needs no CLI: `make build push` is docker-only, and the credential and ECR-login
        # actions are JavaScript on the SDK.
        "build_cli": "",
        "registry_login": "      - uses: aws-actions/amazon-ecr-login@v2\n",
        "environment": (
            "  AWS_REGION: ${{ vars.AWS_REGION }}\n"
            "  TOFU_STATE_BUCKET: ${{ vars.TOFU_STATE_BUCKET }}\n"
            "  IMAGE_REGISTRY: ${{ vars.IMAGE_REGISTRY }}\n"
        ),
    },
    "azure": {
        "cli": AZURE_CLI,
        "credentials": AZURE_CREDENTIALS,
        # Unlike ECR's, this login is the CLI's own, so the build job installs it too.
        "build_cli": AZURE_CLI,
        # `az acr login` rather than an action, and therefore after the CLI and the sign-in above: it takes
        # the active Azure CLI session and hands the Docker daemon a registry credential from it.
        "registry_login": "      - run: az acr login --name ${{ vars.AZURE_REGISTRY_NAME }}\n",
        "environment": (
            "  AZURE_LOCATION: ${{ vars.AZURE_LOCATION }}\n"
            "  AZURE_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}\n"
            "  ARM_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}\n"
            "  AZURE_REGISTRY_ID: ${{ vars.AZURE_REGISTRY_ID }}\n"
            "  TOFU_STATE_RESOURCE_GROUP: ${{ vars.TOFU_STATE_RESOURCE_GROUP }}\n"
            "  TOFU_STATE_ACCOUNT: ${{ vars.TOFU_STATE_ACCOUNT }}\n"
            "  TOFU_STATE_CONTAINER: ${{ vars.TOFU_STATE_CONTAINER }}\n"
            "  IMAGE_REGISTRY: ${{ vars.IMAGE_REGISTRY }}\n"
        ),
    },
}


def deploy_job(environment: str, needs: str, web: bool, target: str, condition: str = "") -> str:
    # The site is built in the deploy job rather than the build job because Vite bakes VITE_* values into the
    # bundle, and where there is a customer login those are the environment's.
    cloud = CLOUD_STEPS[target]
    node = NODE_SETUP if web else ""
    gate = f"    if: {condition}\n" if condition else ""
    return f"""
  {environment}:
    needs: {needs}
{gate}    runs-on: ubuntu-latest
    environment: {environment}
    steps:
{CHECKOUT}{cloud['cli']}      - uses: opentofu/setup-opentofu@v2
        with:
          tofu_version: {TOFU_VERSION}
{node}{cloud['credentials']}      - run: make deploy ENV={environment}
      - run: make smoke URL=$(make -s url ENV={environment})
"""


def cloud_environment(target: str, auth0: bool) -> str:
    """The workflow-level environment for this target, plus the Auth0 tenant's when the project uses one."""
    return CLOUD_STEPS[target]["environment"] + (AUTH0_ENVIRONMENT if auth0 else "")


def deploy_workflow(apps: list[App], target: str, auth0: bool) -> str:
    services = services_of(apps)
    families = families_of(apps)
    setups = "".join(
        toolchain_setup(family, [s for s in services if s.language == family]) for family in families
    )
    tools = "".join(TOOL_SETUPS[tool] for tool in tools_needed(backends_of(apps)))
    cloud = CLOUD_STEPS[target]
    web = bool(web_apps(apps))
    return (
        """name: deploy
# Every commit that passes `verify` on main goes all the way to production, in one pipeline: build once, push
# by digest, apply staging, prove it, apply production, prove it. The gate is `verify`: this workflow starts
# when that one completes on main, and only goes on if it passed, so the deploy never runs beside the gate
# or ahead of it. There is no approval step, and no second pipeline for a hotfix, because this is the only
# path. Every job checks out the commit `verify` passed, not the head of main at the time the job starts.
on:
  workflow_run:
    workflows:
      - verify
    types:
      - completed
    branches:
      - main
permissions:
  id-token: write
  contents: read
# One deploy at a time, never cancelled: a cancelled apply is the one state this pipeline cannot reason about.
concurrency:
  group: deploy
  cancel-in-progress: false
env:
"""
        + cloud_environment(target, auth0)
        + """jobs:
  build:
    if: github.event.workflow_run.conclusion == 'success'
    runs-on: ubuntu-latest
    steps:
"""
        + CHECKOUT
        + setups
        + tools
        + cloud["build_cli"]
        + cloud["credentials"]
        + cloud["registry_login"]
        + """      - run: make build push
"""
        + deploy_job("staging", "build", web, target)
        # `!=`, not `== 'true'`: a project bootstrapped before this variable existed has no variable, and
        # absent has to keep meaning what it has always meant here — deploy production. Only an explicit
        # `false`, which `make bootstrap` writes on purpose, holds this job back.
        + deploy_job("production", "staging", web, target, condition="vars.AUTO_PROMOTE != 'false'")
    )


def promotion_workflow(web: bool, target: str, auth0: bool) -> str:
    """`production.yml`: promote to production the commit staging is running.

    The path production takes when `AUTO_PROMOTE` reads `false`, and the way it is created in the first
    place — a project that does not auto-promote has no production until this has run once. Started from the Actions tab or by
    `make promote`, which is the same dispatch made from a laptop.

    It resolves before it deploys, and that order is the point: the first checkout is only there to run
    `scripts/deploy.py promoting`, which reads staging's release record and answers with the commit staging
    is actually running. The second checkout is *that* commit, so `make deploy` builds the site from it and
    `scripts/deploy.py` resolves its images from the registry by tag — the same digests staging ran, never a
    rebuild of whatever `main` has become since. Given a commit explicitly, `promoting` refuses any that
    staging has no release record for, so this cannot be the way an unproved commit reaches production.

    No build job and no image builder, for the reason `rollback.yml` has none: the images already exist. The
    site is rebuilt because a bundle is not an image — Vite bakes this environment's values into it — which
    is why Node is set up here where there is a browser app.
    """
    cloud = CLOUD_STEPS[target]
    node = NODE_SETUP if web else ""
    return f"""name: production
# Deploy production with the commit staging is running. This is how production is reached in a project whose
# `AUTO_PROMOTE` variable reads `false` — `deploy.yml` stops at staging there — and it is how production is
# created in the first place, since nothing applies that workspace until this runs. It is also available to a
# project that does auto-promote, where it is a way to put production back onto what staging has.
#
# Nothing is built. The commit is resolved from staging's own release record, checked out, and deployed from
# the images already in the registry, so production is only ever given what staging has already run.
on:
  workflow_dispatch:
    inputs:
      commit:
        description: The commit to promote; the default is the one staging is running now
        required: false
        type: string
permissions:
  id-token: write
  contents: read
# The deploy's group: this queues behind an apply in flight rather than crossing it, and a push to main
# arriving mid-promotion queues in turn.
concurrency:
  group: deploy
  cancel-in-progress: false
env:
{cloud_environment(target, auth0)}jobs:
  promote:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v6
{cloud['cli']}{cloud['credentials']}      # What staging is running, from its release record — or the commit asked for, refused unless
      # staging has run it. The `promoting` verb prints that one line and nothing else.
      - id: promoting
        env:
          COMMIT: ${{{{ inputs.commit }}}}
        run: |
          sha=$(python3 scripts/deploy.py promoting staging "$COMMIT")
          echo "promoting $sha"
          echo "sha=$sha" >> "$GITHUB_OUTPUT"
      # The commit itself, replacing the checkout above: `make deploy` reads the commit from the checkout,
      # so everything below this line is that commit's.
      - uses: actions/checkout@v6
        with:
          ref: ${{{{ steps.promoting.outputs.sha }}}}
      - uses: opentofu/setup-opentofu@v2
        with:
          tofu_version: {TOFU_VERSION}
{node}      - run: make deploy ENV=production
      - run: make smoke URL=$(make -s url ENV=production)
"""


def rollback_workflow(target: str, auth0: bool) -> str:
    # Nothing is built and no toolchain is installed: a rollback promotes images that already ran here, and
    # the site comes back from the copy of index.html `make deploy` kept. The same concurrency group as the
    # deploy, so it waits for an apply in flight rather than crossing it.
    cloud = CLOUD_STEPS[target]
    return f"""name: rollback
# Started by hand, from the Actions tab, when a release is wrong: re-apply the release before the current one
# in the environment named — the previous digests, and the previous index.html where there is a site — then
# prove it with `make smoke`. It shares the deploy's concurrency group, so it queues behind an apply in flight
# and a push to main arriving mid-rollback queues in turn. A rollback buys time, it does not pin: the next
# push to main deploys forward again, so fix or revert on main and let the pipeline carry it.
on:
  workflow_dispatch:
    inputs:
      environment:
        description: The environment to roll back
        type: choice
        required: true
        options:
          - staging
          - production
permissions:
  id-token: write
  contents: read
concurrency:
  group: deploy
  cancel-in-progress: false
env:
{cloud_environment(target, auth0)}jobs:
  rollback:
    runs-on: ubuntu-latest
    environment: ${{{{ inputs.environment }}}}
    steps:
      - uses: actions/checkout@v6
{cloud['cli']}      - uses: opentofu/setup-opentofu@v2
        with:
          tofu_version: {TOFU_VERSION}
{cloud['credentials']}      - run: make rollback ENV=${{{{ inputs.environment }}}}
      - run: make smoke URL=$(make -s url ENV=${{{{ inputs.environment }}}})
"""
