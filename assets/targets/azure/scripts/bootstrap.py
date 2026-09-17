#!/usr/bin/env python3
"""`make bootstrap`: the one thing a person does so the pipeline can deploy — and it is one command.

The first commit carries the pipeline and the infrastructure, but something has to exist before the pipeline
can act: a place for state, an identity it may become, a registry for its images, and the repository on the
forge configured to say where those are. This script does all of that from administrator credentials you
already hold, then tells you what to commit. Run it again whenever the bootstrap stack changes; it is idempotent. Unlike the AWS target it is *not*
needed after `add-service`: one registry holds every repository and creates one on first push.

    make bootstrap                      # reads the repository from `git remote get-url origin`
    make bootstrap REPOSITORY=owner/name FORGE=github|gitea|none
    make bootstrap AUTO_PROMOTE=true|false  # whether a green commit reaches production by itself
    scripts/bootstrap.py --plan         # say what would be done and why, change nothing
    scripts/bootstrap.py push <url>     # what `./init` runs: create the repository on the forge if it is
                                        # missing, add it as `origin`, push main

What it decides for you, and how:

- **Where.** `AZURE_LOCATION` from the environment, else the CLI's configured default, else `infra/location`
  — the answer a previous run wrote down; else, in a terminal, it asks once and writes that file for the next
  `make deploy` and `make bootstrap` (commit it with the state). Azure has no ambient region the way AWS
  does: every resource carries a location, so this is a value the stacks cannot be applied without.
- **Who you are.** Whatever the `az` CLI finds — `az login`, and `az account set --subscription <id>` where
  there is more than one. Refuses if nothing does, and refuses *before applying anything* if that sign-in is
  not an Owner of the subscription: the stack grants the pipeline its roles, and granting access is not
  something Contributor may do.
- **Which forge.** From the remote: `github.com` means the pipeline signs in with a federated credential and
  no stored credential at all; any other host is treated as Gitea (or a forge without OIDC federation), which
  gets an app registration and one client secret, stored as a repository secret.
- **Whether to auto-promote to production.** `true` — every commit that passes `verify` on `main` goes to
  staging and then straight on to production, which is the default and what this project was designed
  around. `false` — staging still deploys on every green push, and production moves only when somebody runs
  `make promote`, which promotes what staging is already running. Either way production costs the same once
  it exists; `false` is for a project that wants a person in between, or one that does not want to pay for
  production yet. From `AUTO_PROMOTE=`/`--auto-promote`, else `infra/auto-promote` — the answer a previous
  run wrote down; else, in a terminal, it asks once and writes that file. Written to the forge as the
  `AUTO_PROMOTE` variable, which is the only thing `deploy.yml` reads to decide.
- **The passphrase** encrypting the committed bootstrap state: `TF_VAR_state_passphrase` if set; otherwise a
  new one is generated for a first run and printed once — keep it, nothing else ever knows it.
- **The repository's configuration**: variables (identifiers) and, on a forge without OIDC, secrets (the key),
  written with `gh` on GitHub and the REST API on Gitea (`GITEA_TOKEN`, or `--token`). On GitHub it also
  creates the `staging` and `production` environments the deploy workflows name, each deployable from `main`
  and nothing else: the deploy role trusts the subject a job in an environment carries, and that subject
  names no branch, so the branch is said here instead (`ensure_environments`).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STACK = ROOT / "infra/bootstrap"
STATE = STACK / "terraform.tfstate"
# Where the location is remembered once it has been decided, so it is asked once, not on every verb.
LOCATION_FILE = ROOT / "infra/location"
# The same, for whether a green commit is promoted to production by itself. Committed like the region, so a
# second `make bootstrap` — after `add-service`, or from somebody else's laptop — writes the answer this
# project already gave rather than silently putting it back to the default.
PROMOTE_FILE = ROOT / "infra/auto-promote"
PROMOTE_CHOICES = ("true", "false")

# What the pipeline reads, and which bootstrap output each comes from.
#
# `AUTO_PROMOTE` is the one variable that is not an output: it is a decision, not an identifier, and the
# only thing `.github/workflows/deploy.yml` reads to decide whether its production job runs. It is written
# on every run, so a project that has one is never left guessing from an absent variable.
PROMOTE_VARIABLE = "AUTO_PROMOTE"
VARIABLES = {
    "AZURE_LOCATION": "location",
    "AZURE_SUBSCRIPTION_ID": "subscription_id",
    "AZURE_TENANT_ID": "tenant_id",
    "AZURE_CLIENT_ID": "deploy_client_id",
    "AZURE_REGISTRY_ID": "registry_id",
    "AZURE_REGISTRY_NAME": "registry_name",
    "TOFU_STATE_RESOURCE_GROUP": "state_resource_group",
    "TOFU_STATE_ACCOUNT": "state_storage_account",
    "TOFU_STATE_CONTAINER": "state_container",
    "IMAGE_REGISTRY": "image_registry",
}
SECRETS = {
    "AZURE_CLIENT_SECRET": "deploy_client_secret",
}

# The one credential in this repository that the cloud did not issue. A project whose identity answer is
# Auth0 applies `infra/service/auth0.tf` with a machine-to-machine application's credentials, read from the
# environment by the provider. They are not outputs of the bootstrap stack — nothing here can create an
# Auth0 tenant — so they are asked for and stored, which is the whole of what this script does about them.
# Domain and client id are identifiers and go in as variables; the secret goes in as a secret.
AUTH0_VARIABLES = ("AUTH0_DOMAIN", "AUTH0_CLIENT_ID")
AUTH0_SECRETS = ("AUTH0_CLIENT_SECRET",)
AUTH0_PROMPTS = {
    "AUTH0_DOMAIN": "Auth0 tenant domain (for example example.eu.auth0.com)",
    "AUTH0_CLIENT_ID": "Auth0 machine-to-machine application client id",
    "AUTH0_CLIENT_SECRET": "Auth0 machine-to-machine application client secret",
}

# The same identifiers written into the repository, so a laptop whose environment carries none of them can
# still run `make deploy` and `make url` from a checkout. `scripts/deploy.py` reads these when the
# environment is silent; committed with the state, like the location and the promotion answer.
RECORDED = {
    "infra/location": "location",
    "infra/registry": "image_registry",
    "infra/registry-id": "registry_id",
    "infra/state-resource-group": "state_resource_group",
    "infra/state-account": "state_storage_account",
    "infra/state-container": "state_container",
}

# The two environments the deploy workflows name, which are the two `infra/service/variables.tf` admits.
# On GitHub they are created here rather than left to be created on first use, because an environment that
# nobody configured has no deployment branch policy — and the deploy role's trust names the subject GitHub
# writes for a job in one of them, which carries no branch (see `ensure_environments`).
ENVIRONMENTS = ("staging", "production")
# The only branch those environments may be deployed from, and the branch the trust's other subject names.
DEPLOY_BRANCH = "main"


# Every request to the forge names itself. The default `Python-urllib/3.x` agent is a banned signature on
# proxies that front a self-hosted forge — Cloudflare answers 403 with a body of `error code: 1010` before
# the forge sees the request at all — and that refusal looks exactly like a bad token until the body is read.
USER_AGENT = "slipwai-bootstrap"


class Failure(Exception):
    """Something this script can name, printed without a traceback."""


def run(command: list[str], *, capture: bool = False, env: dict | None = None, quiet: bool = False) -> str:
    if not quiet:
        print("+", " ".join(command), file=sys.stderr, flush=True)
    result = subprocess.run(command, text=True, env=env, stdout=subprocess.PIPE if capture else None, check=False)
    if result.returncode != 0:
        raise Failure(f"`{command[0]}` exited {result.returncode}")
    return result.stdout if capture else ""


def which(tool: str, why: str) -> None:
    if shutil.which(tool) is None:
        raise Failure(f"{tool} is not on the PATH; it is needed to {why} (infra/README.md)")


def remote_url() -> str | None:
    result = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, text=True, capture_output=True)
    return result.stdout.strip() or None if result.returncode == 0 else None


def parse_remote(url: str) -> tuple[str, str, str]:
    """(scheme, host, owner/name) from an https or ssh remote."""
    ssh = re.fullmatch(r"(?:ssh://)?git@([^:/]+)[:/](.+?)(?:\.git)?/?", url)
    if ssh:
        return "https", ssh.group(1), ssh.group(2)
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc:
        raise Failure(f"cannot read a forge out of the remote {url!r}")
    host = parsed.netloc.rsplit("@", 1)[-1]
    path = parsed.path.strip("/").removesuffix(".git")
    if path.count("/") != 1:
        raise Failure(f"the remote {url!r} does not end in owner/name")
    return parsed.scheme or "https", host, path


def decide(args: argparse.Namespace) -> dict:
    """Everything the run depends on, worked out before anything is touched."""
    url = remote_url()
    if args.repository:
        repository, scheme, host = args.repository, "https", "github.com"
        if url:
            scheme, host, _ = parse_remote(url)
    elif url:
        scheme, host, repository = parse_remote(url)
    else:
        raise Failure(
            "this repository has no `origin` remote yet. The pipeline is configured on the forge, so push it "
            "first (`git remote add origin <url> && git push -u origin main`), or say which repository with "
            "`make bootstrap REPOSITORY=owner/name`"
        )
    forge = args.forge or ("github" if host.endswith("github.com") else "gitea")
    return {
        "repository": repository,
        "forge": forge,
        "forge_api": f"{scheme}://{host}/api/v1",
        "deploy_with": "oidc" if forge == "github" else "access-key",
        "location": location(ask=not args.plan),
        "auto_promote": auto_promote(args.auto_promote, ask=not args.plan),
    }


def configured_location() -> str | None:
    if shutil.which("az") is None:
        return None
    result = subprocess.run(
        ["az", "config", "get", "defaults.location", "--only-show-errors"], text=True, capture_output=True
    )
    if result.returncode != 0:
        return None
    try:
        return (json.loads(result.stdout or "{}").get("value") or "").strip() or None
    except ValueError:
        return result.stdout.strip() or None


def location(ask: bool) -> str | None:
    """The location, from the environment, the CLI's configuration, or the file a previous run wrote — else,
    in a terminal, asked once and written down for the verbs that follow."""
    found = os.environ.get("AZURE_LOCATION") or configured_location()
    if not found and LOCATION_FILE.is_file():
        found = LOCATION_FILE.read_text().strip() or None
    if not found and ask and sys.stdin.isatty():
        found = input("Azure region for this project (for example uksouth): ").strip() or None
        if found:
            LOCATION_FILE.write_text(found + "\n")
            print(f"+ wrote {LOCATION_FILE.relative_to(ROOT)} — commit it with the state", file=sys.stderr)
    return found


def auto_promote(given: str | None, ask: bool) -> str:
    """Whether a green commit is promoted to production by itself: what was asked for, else what a previous
    run wrote down, else — in a terminal — asked once and written down; else the default, which is yes.

    Asked here rather than at generation time because it is not part of the project's shape: it is a fact
    about the account this repository deploys to, it changes on the day somebody runs `make promote`, and
    nothing has cost a penny until this script runs. Asked here rather than in `./init` because this is the
    script that knows whether the answer is already written down.

    `ask` is false under `--plan`, which says what would be done and writes nothing — so the answer is still
    worked out and reported, and the file is left for the run that means it.
    """
    if given:
        # Held to PROMOTE_CHOICES by argparse, which `make bootstrap AUTO_PROMOTE=…` also goes through.
        found = given
    elif PROMOTE_FILE.is_file() and PROMOTE_FILE.read_text().strip() in PROMOTE_CHOICES:
        return PROMOTE_FILE.read_text().strip()
    elif ask and sys.stdin.isatty():
        print(
            "\nAuto-promote means every commit that passes verify on main goes to staging and then "
            "straight on to production, which is what this project was designed around.\nSay no and "
            "staging still deploys on every green push, while production waits for `make promote` — the "
            "same images, when you say so — and is not created at all until the first one.\nEither costs "
            "the same once production exists.",
            file=sys.stderr,
        )
        answer = input("Auto-promote to production? [Y/n]: ").strip().lower()
        found = "false" if answer[:1] == "n" else "true"
    else:
        found = "true"
    if ask:
        PROMOTE_FILE.write_text(found + "\n")
        print(f"+ wrote {PROMOTE_FILE.relative_to(ROOT)} = {found} — commit it with the state", file=sys.stderr)
    return found


def passphrase() -> tuple[str, bool]:
    """The state passphrase, and whether it was made just now."""
    given = os.environ.get("TF_VAR_state_passphrase")
    if given:
        return given, False
    if STATE.exists():
        raise Failure(
            "infra/bootstrap/terraform.tfstate exists and is encrypted: set TF_VAR_state_passphrase to the "
            "passphrase it was created with before running again"
        )
    return secrets.token_urlsafe(32), True


def uses_auth0() -> bool:
    """Whether any service in this project answered an identity axis with Auth0.

    Read from the same `project.auto.tfvars.json` the stack reads, so the question is answered by what was
    generated rather than by a flag somebody has to remember to pass.
    """
    data = ROOT / "infra/service/project.auto.tfvars.json"
    if not data.is_file():
        return False
    services = json.loads(data.read_text()).get("services", {})
    return any(service.get(axis) == "auth0" for service in services.values() for axis in ("auth", "users"))


def auth0_credentials(ask: bool) -> dict[str, str]:
    """The three values the Auth0 provider needs, from the environment or — in a terminal — asked for.

    Nothing is written to disk: two of them are identifiers this script is about to put on the forge, and
    the third is a credential that belongs nowhere else. A value already in the environment is taken as
    given, so a second run is not a second interrogation, and CI never reaches this code at all.
    """
    found: dict[str, str] = {}
    for name in (*AUTH0_VARIABLES, *AUTH0_SECRETS):
        value = os.environ.get(name, "").strip()
        if not value and ask and sys.stdin.isatty():
            value = input(f"{AUTH0_PROMPTS[name]}: ").strip()
        if not value:
            raise Failure(
                f"{name} is not set, and this project answered an identity axis with Auth0.\n"
                "Create the tenant and one machine-to-machine application authorised for the Auth0\n"
                "Management API, then set AUTH0_DOMAIN, AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET and run\n"
                "this again. infra/README.md says what the application needs to be allowed to do."
            )
        found[name] = value
    return found


def outputs(env: dict) -> dict:
    raw = json.loads(run(["tofu", f"-chdir={STACK}", "output", "-json"], capture=True, env=env, quiet=True))
    return {name: value["value"] for name, value in raw.items()}


def remember(found: dict) -> None:
    """Write the identifiers down beside the state, so a laptop with none of them in its environment can
    still run `make deploy`, `make url` and `make flags` from a checkout. The forge carries the same values
    as repository variables for the pipeline; these are the copy a person reads."""
    for relative, output in RECORDED.items():
        value = str(found.get(output) or "").strip()
        if value:
            (ROOT / relative).write_text(value + "\n")
    print("+ wrote " + ", ".join(sorted(RECORDED)) + " — commit them with the state", file=sys.stderr)


# ── The subscription ───────────────────────────────────────────────────────────────────────────────────

# What the bootstrap stack needs the caller to be. Azure has no "simulate this action" call the way IAM
# does, so the check is what roles the caller actually holds on the subscription — which is the thing that
# decides it. Owner is the answer; Contributor with one of the two access-administrator roles beside it is
# the same permission spelled as two, and is accepted for that reason.
#
# Checked before the apply, because a plan that fails halfway on AuthorizationFailed leaves the state — and
# the passphrase — in a worse place than a refusal does.
ENOUGH = ("Owner",)
ALSO_ENOUGH = ("Contributor", ("User Access Administrator", "Role Based Access Control Administrator"))


# The directory roles that let a caller create an app registration and its service principal, and — for the
# staff-identity answer — grant that principal a Graph role. Directory roles are not subscription roles:
# Owner of the subscription holds none of them, which is the whole reason this is a second check.
CREATES_APPLICATIONS = (
    "Application Developer", "Application Administrator",
    "Cloud Application Administrator", "Global Administrator",
)
GRANTS_PERMISSIONS = ("Privileged Role Administrator", "Global Administrator")


def directory_roles() -> set[str] | None:
    """The signed-in account's directory roles, or None when they could not be read."""
    result = subprocess.run(
        ["az", "rest", "--method", "GET", "--url",
         "https://graph.microsoft.com/v1.0/me/memberOf?$select=displayName,@odata.type",
         "--output", "json"],
        text=True, capture_output=True,
    )
    if result.returncode != 0:
        return None
    try:
        members = json.loads(result.stdout or "{}").get("value", [])
    except ValueError:
        return None
    return {
        entry.get("displayName", "")
        for entry in members
        if entry.get("@odata.type") == "#microsoft.graph.directoryRole"
    }


def check_directory(deploy_with: str) -> None:
    """Refuse before the apply when this sign-in cannot do what the *directory* is about to be asked.

    Subscription RBAC and directory rights are two different things, and Owner of the subscription holds
    none of the second. Two answers need the directory, and only two:

    - **A forge without OIDC federation** — the pipeline signs in with an app registration and a client
      secret, so this stack creates an application and its service principal. On GitHub none of this
      applies: the identity is a user-assigned managed identity, which is an ARM resource, and the whole
      OIDC path writes nothing to the directory at all.
    - **`--auth entra`** — the deploy identity is granted a Graph role, and granting one always needs a
      directory role. No tenant setting makes an ordinary member able to do it.

    An account with **no** directory role is refused, because that is the configuration this has been seen
    to fail in: the application is created, and then creating its service principal is refused with a
    message naming the backing application rather than the permission — after the resource group, the
    storage account and the registry are already made. An account that holds *some* directory role but not
    one this names is warned and allowed to continue, because these roles overlap and a list is never
    complete.
    """
    wants: list[tuple[str, tuple[str, ...], str]] = []
    if deploy_with == "access-key":
        wants.append((
            "create an app registration and its service principal, because this forge cannot federate",
            CREATES_APPLICATIONS,
            "Use GitHub for this repository and the pipeline federates instead: its identity becomes a "
            "user-assigned managed identity, which is a subscription resource, and this stack then asks "
            "the directory for nothing.",
        ))
    if answers_entra():
        wants.append((
            "grant that principal a Graph role, which is what lets it provision the staff identity",
            GRANTS_PERMISSIONS,
            "Or regenerate with an identity answer that asks the directory for nothing: `--auth none`, "
            "or `--auth auth0`, whose objects live in an Auth0 tenant rather than in Entra.",
        ))
    if not wants:
        return
    held = directory_roles()
    if held is None:
        print("(could not read this sign-in's directory roles; the apply will say)", file=sys.stderr)
        return
    for what, enough, alternative in wants:
        if held & set(enough):
            continue
        if held:
            print(
                f"\nwarning: this apply will {what}.\n"
                f"  That is a directory operation; Owner of the subscription does not grant it.\n"
                f"  This sign-in holds {', '.join(sorted(held))}, and one of {', '.join(enough)} grants it\n"
                "  outright. Continuing, because directory roles overlap and this list is not complete.",
                file=sys.stderr,
            )
            continue
        raise Failure(
            f"This apply has to {what}, and that is a *directory* operation.\n"
            f"{identity_name()} holds no directory role at all — only group memberships — and Owner of the\n"
            "subscription grants nothing in the directory. The application would be created and then its\n"
            "service principal refused, leaving a half-built bootstrap behind, so nothing was applied.\n\n"
            f"Ask for one of: {', '.join(enough)}.\n"
            f"{alternative}\n\n"
            "`az rest --method GET --url "
            "'https://graph.microsoft.com/v1.0/me/memberOf?$select=displayName,@odata.type'` lists what this\n"
            "sign-in holds; a directory role is an entry whose type is `#microsoft.graph.directoryRole`."
        )


def identity_name() -> str:
    """Who `az` is signed in as, for a refusal that names them. Best effort: the refusal stands either way."""
    result = subprocess.run(
        ["az", "account", "show", "--query", "user.name", "--output", "tsv"], text=True, capture_output=True
    )
    return result.stdout.strip() if result.returncode == 0 else "This sign-in"


def answers_entra() -> bool:
    """Whether any service in this project answered the staff-identity axis with Entra ID, read from the
    same file the stack reads."""
    data = ROOT / "infra/service/project.auto.tfvars.json"
    if not data.is_file():
        return False
    services = json.loads(data.read_text()).get("services", {})
    return any(service.get("auth") == "entra" for service in services.values())


def check_permissions(identity: dict, deploy_with: str) -> None:
    """Refuse before the apply when the caller is not an Owner of the subscription.

    A listing the caller is not allowed to make is not a denial: the check is skipped with a note, and the
    apply says what it finds.
    """
    result = subprocess.run(
        ["az", "role", "assignment", "list", "--assignee", identity["user"]["name"],
         "--scope", f"/subscriptions/{identity['id']}", "--include-inherited", "--output", "json"],
        text=True, capture_output=True,
    )
    if result.returncode != 0:
        print("(could not check this sign-in's roles ahead; the apply will say)", file=sys.stderr)
        return
    try:
        held = {assignment.get("roleDefinitionName") for assignment in json.loads(result.stdout or "[]")}
    except ValueError:
        print("(could not read this sign-in's roles; the apply will say)", file=sys.stderr)
        return
    contributor, administrators = ALSO_ENOUGH
    if held & set(ENOUGH) or (contributor in held and held & set(administrators)):
        check_directory(deploy_with)
        return
    raise Failure(
        f"{identity['user']['name']} holds {', '.join(sorted(held)) or 'no role'} on subscription "
        f"{identity['id']}, and bootstrapping needs Owner: this stack grants the pipeline its roles, and "
        "granting access is not something Contributor may do. Sign in as an Owner (`az login`, then "
        "`az account set --subscription <id>`) and run again. Nothing was applied."
    )


# ── The forge ──────────────────────────────────────────────────────────────────────────────────────────


def github_subject_prefix(repository: str) -> str:
    """The prefix GitHub will put in the `sub` claim of tokens this repository's workflows ask for.

    Usually `repo:owner/name`, but an organisation can have the immutable form enabled, and then it is
    `repo:owner@<owner id>/name@<repo id>` — the same repository, spelled so a rename cannot hand the trust
    to someone else. The trust policy has to match whichever one the token will carry, so ask rather than
    assume: `sub_claim_prefix` from the repository's OIDC customization endpoint is the answer. If the
    endpoint cannot be reached or the token is not allowed to read it, fall back to the name form and say so
    — a wrong guess here is a pipeline that cannot assume the role, with a trust policy that reads correctly.
    """
    default = f"repo:{repository}"
    if shutil.which("gh") is None:
        return default
    result = subprocess.run(
        ["gh", "api", f"/repos/{repository}/actions/oidc/customization/sub"], text=True, capture_output=True,
    )
    prefix = ""
    if result.returncode == 0:
        try:
            prefix = json.loads(result.stdout).get("sub_claim_prefix") or ""
        except json.JSONDecodeError:
            prefix = ""
    if not prefix:
        print(
            f"! could not read {repository}'s OIDC subject prefix from GitHub; trusting {default}. If the "
            "pipeline cannot assume the deploy role, check `gh api "
            f"/repos/{repository}/actions/oidc/customization/sub` and run again.",
            file=sys.stderr,
        )
        return default
    if prefix != default:
        print(f"+ GitHub issues tokens for {repository} as {prefix}; the trust names that", file=sys.stderr)
    return prefix


def configure_github(repository: str, variables: dict[str, str], secret_values: dict[str, str]) -> None:
    which("gh", "configure the GitHub repository; `gh auth login` first")
    for name, value in variables.items():
        run(["gh", "variable", "set", name, "--repo", repository, "--body", value])
    for name, value in secret_values.items():
        subprocess.run(["gh", "secret", "set", name, "--repo", repository], input=value, text=True, check=True)
        print("+ gh secret set", name, "--repo", repository, "(value withheld)", file=sys.stderr)
    # Only here, and not in `configure_gitea`: environments are a GitHub API Gitea does not implement, and on
    # Gitea the pipeline signs in with a key rather than a token whose subject names an environment, so there
    # is nothing there for a branch policy to hold. The whole step is GitHub's, and skipped rather than
    # attempted-and-forgiven elsewhere.
    ensure_environments(repository)


def gh_api(method: str, path: str, payload: dict | None = None) -> subprocess.CompletedProcess:
    """A REST call through `gh`, which carries the authentication `gh auth login` already set up.

    Not `run`: these calls are allowed to fail. `gh api` exits non-zero on any status GitHub refuses with,
    and what a refusal means here is worth saying in words rather than as a traceback. stdin is always a
    pipe, so a call with no body cannot end up reading the terminal.
    """
    command = ["gh", "api", "--method", method, path]
    if payload is not None:
        command += ["--input", "-"]
    print("+", " ".join(command), file=sys.stderr, flush=True)
    return subprocess.run(
        command, input=json.dumps(payload) if payload is not None else "", text=True, capture_output=True,
    )


def ensure_environments(repository: str) -> None:
    """Create `staging` and `production` on GitHub, each deployable from `main` and nothing else.

    The deploy role's trust has to name the subject GitHub puts in the token, and for a job that declares an
    `environment:` that is `<prefix>:environment:<name>` — not the `:ref:refs/heads/main` form a job without
    one gets. Trusting those two subjects is what lets the deploy jobs assume the role at all; it also gives
    away the property the ref form carried for free, because an environment subject says nothing about the
    branch. Without what this function does, any branch could declare `environment: staging` and be the
    deploy role — and `rollback.yml` is a `workflow_dispatch`, which is run from a branch by choosing one.

    So the branch is put back on the forge: an environment with a deployment branch policy naming `main`
    makes GitHub refuse to start a job pointed at it from anywhere else, which means no such token is ever
    minted. The two halves are one change and neither stands alone.

    `custom_branch_policies`, not `protected_branches`. The latter admits whatever branches happen to carry a
    protection rule, which in the repository `./init` has just created is none — every deploy refused, and
    for a reason that reads like the bug this replaced — and it widens by itself the day somebody protects a
    second branch. A custom policy naming `main` says main, and goes on saying it.

    Idempotent, because `make bootstrap` is run again after `add-service` and whenever the stack changes: an
    environment already on this policy is not rewritten, and the branch is added only when it is not already
    named. A failure is reported and not raised — the account is bootstrapped by this point, and a refusal here
    (environment protection rules need a paid plan on a private repository, and a token needs `repo`) is a
    thing to go and finish in Settings, not a reason to leave the state of the run in doubt.
    """
    for environment in ENVIRONMENTS:
        path = f"/repos/{repository}/environments/{environment}"
        # Read before writing, because that PUT is a replace: what it is not given, the environment loses.
        # An environment already on custom branch policies is one this has configured, and possibly one
        # somebody has since added reviewers or a wait timer to, so it is left exactly as it is and only its
        # branch list is checked below. One that has never been configured — the state GitHub leaves an
        # environment created on first use in — is written.
        found = gh_api("GET", path)
        configured = False
        if found.returncode == 0:
            try:
                policy = json.loads(found.stdout).get("deployment_branch_policy") or {}
            except json.JSONDecodeError:
                policy = {}
            configured = bool(policy.get("custom_branch_policies"))
        made = found if configured else gh_api(
            "PUT", path,
            {"deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}},
        )
        if made.returncode != 0:
            print(
                f"! could not configure the {environment} environment of {repository}: "
                f"{made.stderr.strip().splitlines()[-1] if made.stderr.strip() else 'gh failed'}.\n"
                f"  The deploy role trusts `…:environment:{environment}` from this repository, and until that "
                f"environment only deploys from {DEPLOY_BRANCH}, a job on any branch can claim it. Set it by "
                "hand under Settings → Environments, or check this token's scopes and run again.",
                file=sys.stderr,
            )
            continue
        policies = f"{path}/deployment-branch-policies"
        listed = gh_api("GET", policies)
        named = []
        if listed.returncode == 0:
            try:
                named = [branch.get("name") for branch in json.loads(listed.stdout).get("branch_policies", [])]
            except json.JSONDecodeError:
                named = []
        if DEPLOY_BRANCH in named:
            print(f"+ {repository}: environment {environment} deploys from {DEPLOY_BRANCH} only", file=sys.stderr)
            continue
        added = gh_api("POST", policies, {"name": DEPLOY_BRANCH, "type": "branch"})
        if added.returncode != 0:
            print(
                f"! {repository}: the {environment} environment exists but naming {DEPLOY_BRANCH} as the only "
                f"branch that may deploy to it failed: "
                f"{added.stderr.strip().splitlines()[-1] if added.stderr.strip() else 'gh failed'}",
                file=sys.stderr,
            )
            continue
        print(f"+ {repository}: environment {environment} deploys from {DEPLOY_BRANCH} only", file=sys.stderr)


def gitea(api: str, token: str, method: str, path: str, payload: dict | None = None) -> int:
    request = urllib.request.Request(
        f"{api}{path}", method=method, data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"token {token}", "Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status
    except urllib.error.HTTPError as error:
        with error:  # the status is all this asks for; the body is closed rather than left to the collector
            return error.code
    except urllib.error.URLError as error:
        raise Failure(f"cannot reach the forge at {api}: {error.reason}") from error


def configure_gitea(api: str, repository: str, token: str | None, variables: dict[str, str], secret_values: dict[str, str]) -> None:
    if not token:
        raise Failure(
            f"a Gitea token is needed to configure {repository} on {api}: set GITEA_TOKEN (a token with "
            "repository write access), or pass --token"
        )
    for name, value in variables.items():
        path = f"/repos/{repository}/actions/variables/{name}"
        # Created with POST, updated with PUT; the GET tells which.
        exists = gitea(api, token, "GET", path) == 200
        status = gitea(api, token, "PUT" if exists else "POST", path, {"name": name, "value": value})
        if status >= 300:
            raise Failure(f"Gitea answered {status} setting variable {name}")
        print(f"+ {repository}: variable {name} = {value}", file=sys.stderr)
    for name, value in secret_values.items():
        status = gitea(api, token, "PUT", f"/repos/{repository}/actions/secrets/{name}", {"data": value})
        if status >= 300:
            raise Failure(f"Gitea answered {status} setting secret {name}")
        print(f"+ {repository}: secret {name} (value withheld)", file=sys.stderr)


# ── Pushing to a repository that may not exist yet ────────────────────────────────────────────────────


def ensure_repository(scheme: str, host: str, repository: str, token: str | None) -> None:
    """Create the repository on the forge when it is not there, private, so the first push has a target."""
    owner, name = repository.split("/", 1)
    if host.endswith("github.com"):
        which("gh", "create the repository on GitHub; `gh auth login` first")
        exists = subprocess.run(["gh", "repo", "view", repository], capture_output=True).returncode == 0
        if not exists:
            run(["gh", "repo", "create", repository, "--private"])
        return
    api = f"{scheme}://{host}/api/v1"
    if not token:
        raise Failure(f"a Gitea token is needed to create or check {repository} on {host}: set GITEA_TOKEN")
    # Only a 404 means the repository is not there. Anything else answered — a rejected token, a proxy
    # refusing the request — is a reason to stop and say so, not a reason to try creating what may exist.
    looked = gitea(api, token, "GET", f"/repos/{repository}")
    if looked == 200:
        return
    if looked != 404:
        hint = " — check GITEA_TOKEN is valid and has read:repository" if looked in (401, 403) else ""
        raise Failure(f"the forge at {api} answered {looked} for {repository}, so whether it exists is unknown{hint}")
    me = json.loads(fetch_json(api, token, "/user"))
    path = "/user/repos" if me.get("login") == owner else f"/orgs/{owner}/repos"
    status = gitea(api, token, "POST", path, {"name": name, "private": True, "default_branch": "main"})
    if status >= 300:
        raise Failure(f"Gitea answered {status} creating {repository}")
    print(f"+ created {repository} on {host} (private)", file=sys.stderr)


def fetch_json(api: str, token: str, path: str) -> str:
    request = urllib.request.Request(
        f"{api}{path}", headers={"Authorization": f"token {token}", "User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.read().decode()
    # An answered status is not an unreachable forge, and saying so sends whoever reads it to the network
    # when the answer is in the body: a rejected token, or a proxy refusing the request before the forge.
    except urllib.error.HTTPError as error:
        # Closed once read, the way `gitea` above closes the one it only takes a status from.
        with error:
            detail = error.read().decode(errors="replace").strip()[:200]
        hint = " — check GITEA_TOKEN is valid and has read:user" if error.code in (401, 403) else ""
        raise Failure(f"the forge at {api} answered {error.code} for {path}: {detail or error.reason}{hint}") from error
    except urllib.error.URLError as error:
        raise Failure(f"cannot reach the forge at {api}: {error.reason}") from error


def push(url: str, token: str | None) -> None:
    """Make `url` this repository's `origin` — creating it on the forge if need be — and push `main`."""
    scheme, host, repository = parse_remote(url)
    ensure_repository(scheme, host, repository, token)
    if remote_url() is None:
        run(["git", "remote", "add", "origin", url])
    run(["git", "push", "-u", "origin", "main"])


# ── The run ────────────────────────────────────────────────────────────────────────────────────────────


def plan(decision: dict) -> None:
    key = decision["deploy_with"] == "access-key"
    where = "via the gh CLI" if decision["forge"] == "github" else decision["forge_api"]
    print(f"repository   {decision['repository']} on {decision['forge']} ({where})")
    print(f"location     {decision['location'] or '(unset: export AZURE_LOCATION, or `az config set defaults.location=…`)'}")
    print(f"pipeline     {'signs in with a federated credential; no credential is stored' if not key else 'signs in with an app registration and a client secret, stored as a repository secret'}")
    print("apply        infra/bootstrap: state account, deploy identity, container registry" + (", the app registration and its secret" if key else ", three federated credentials"))
    print(f"auto-promote {decision['auto_promote']}: " + (
        "every commit that passes verify on main is deployed to staging and then production"
        if decision["auto_promote"] == "true"
        else "staging on every green push; production only when `make promote` says so"
    ))
    print("configure    variables " + ", ".join([*VARIABLES, PROMOTE_VARIABLE]) + (" and secrets " + ", ".join(SECRETS) if key else ""))
    if decision["forge"] == "github":
        print("environments " + " and ".join(ENVIRONMENTS) + f", each deploying from {DEPLOY_BRANCH} only")
    print("passphrase   " + ("TF_VAR_state_passphrase, as set" if os.environ.get("TF_VAR_state_passphrase") else "generated now and printed once" if not STATE.exists() else "REQUIRED: the state exists and TF_VAR_state_passphrase is not set"))


def bootstrap(args: argparse.Namespace) -> None:
    decision = decide(args)
    if args.plan:
        plan(decision)
        return
    which("tofu", "apply the bootstrap stack")
    which("az", "sign in to the subscription")
    if not decision["location"]:
        raise Failure(
            "no location: export AZURE_LOCATION, `az config set defaults.location=<region>`, or write it to "
            "infra/location"
        )
    identity = json.loads(run(["az", "account", "show", "--output", "json"], capture=True))
    print(
        f"subscription {identity['id']} as {identity['user']['name']}, location {decision['location']}",
        file=sys.stderr,
    )
    check_permissions(identity, decision["deploy_with"])
    phrase, fresh = passphrase()
    if fresh:
        # Before the apply, not after: a failed first apply still writes an encrypted state, and a passphrase
        # only shown on success would be one nobody has.
        print(
            f"\nThe committed bootstrap state will be encrypted with a passphrase generated now. Keep it — it is "
            f"what every later `make bootstrap` needs, and nothing else knows it:\n  TF_VAR_state_passphrase={phrase}\n",
            file=sys.stderr,
        )
    env = {
        **os.environ,
        "ARM_SUBSCRIPTION_ID": identity["id"],
        "TF_VAR_state_passphrase": phrase,
    }
    subject_prefix = github_subject_prefix(decision["repository"]) if decision["forge"] == "github" else ""
    run(["tofu", f"-chdir={STACK}", "init", "-input=false"], env=env)
    run([
        "tofu", f"-chdir={STACK}", "apply", "-input=false", "-auto-approve",
        f"-var=repository={decision['repository']}", f"-var=deploy_with={decision['deploy_with']}",
        f"-var=oidc_subject_prefix={subject_prefix}", f"-var=location={decision['location']}",
    ], env=env)
    found = outputs(env)
    remember(found)
    variables = {name: str(found[output]) for name, output in VARIABLES.items()}
    variables[PROMOTE_VARIABLE] = decision["auto_promote"]
    secret_values = {
        name: str(found[output]) for name, output in SECRETS.items() if found.get(output)
    }
    if uses_auth0():
        given = auth0_credentials(ask=True)
        variables.update({name: given[name] for name in AUTH0_VARIABLES})
        secret_values.update({name: given[name] for name in AUTH0_SECRETS})
    if decision["forge"] == "github":
        configure_github(decision["repository"], variables, secret_values)
    elif decision["forge"] == "gitea":
        configure_gitea(decision["forge_api"], decision["repository"], args.token or os.environ.get("GITEA_TOKEN"), variables, secret_values)
    else:
        print("\nno forge to configure; set these on yours:", file=sys.stderr)
        for name, value in variables.items():
            print(f"  variable {name} = {value}")
        for name in secret_values:
            print(f"  secret   {name} = (from `tofu -chdir=infra/bootstrap output -raw {SECRETS[name]}`)")
    print("\nbootstrapped. Now:")
    if fresh:
        print(f"  1. Keep the passphrase printed above (TF_VAR_state_passphrase={phrase}); it decrypts the state.")
    print(
        "  2. git add infra/bootstrap/terraform.tfstate infra/bootstrap/.terraform.lock.hcl "
        + " ".join(sorted(RECORDED))
        + " infra/auto-promote && git commit"
    )
    if decision["auto_promote"] == "true":
        print("  3. git push — the pipeline builds, deploys staging, then production, and proves each.")
    else:
        print("  3. git push — the pipeline builds, deploys staging and proves it. Production is not created.")
        print("  4. `make promote` when you want production: it deploys what staging is running, and proves it.")


def main(argv: list[str]) -> int:
    if argv[:1] == ["push"]:
        try:
            if len(argv) != 2:
                raise Failure("push takes the repository URL and nothing else")
            push(argv[1], os.environ.get("GITEA_TOKEN"))
        except Failure as failure:
            print(f"bootstrap: {failure}", file=sys.stderr)
            return 1
        return 0
    parser = argparse.ArgumentParser(prog="scripts/bootstrap.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--repository", help="owner/name on the forge (default: from the origin remote)")
    parser.add_argument("--forge", choices=["github", "gitea", "none"], help="default: from the remote's host")
    parser.add_argument("--token", help="a Gitea token with repository write access (default: GITEA_TOKEN)")
    parser.add_argument(
        "--auto-promote", choices=list(PROMOTE_CHOICES),
        help="`true`: a green commit reaches production by itself (the default). `false`: production waits "
             "for `make promote`. Default: what infra/auto-promote says, else asked in a terminal, else true",
    )
    parser.add_argument("--plan", action="store_true", help="say what would be done and change nothing")
    args = parser.parse_args(argv)
    try:
        bootstrap(args)
    except Failure as failure:
        print(f"bootstrap: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
