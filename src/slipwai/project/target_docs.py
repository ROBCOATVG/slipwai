"""Which pages a project going to production is given, and which cloud's module writes them.

A managed target's `docs/deployment.md` and `docs/adr/0002-production-target.md` are entirely that cloud's:
its nodes, its products, its prices, its consequences. There is no general version of either to parameterise
— the attempt would be a page of conditionals describing nothing in particular — so each target brings its
own module and this table says which. Adding a cloud is a row here and a module beside `aws_docs.py`, which
is the same shape as the row it adds to `catalog.json` and the tree it adds under `assets/targets/`.

The paths are the same for every target on purpose: a reader who has seen one generated project knows where
the drawing and the decision record are, whatever it deploys to, and `slipwai migrate` merges them across a
change of neither name nor number.
"""
from __future__ import annotations

from collections.abc import Callable

from ..errors import GenerationError
from ..services import App
from . import aws_docs, azure_docs

Page = Callable[[str, list[App]], str]

PAGES: dict[str, dict[str, Page]] = {
    "aws": {
        "docs/adr/0002-production-target.md": aws_docs.production_adr,
        "docs/deployment.md": aws_docs.deployment_diagram,
    },
    "azure": {
        "docs/adr/0002-production-target.md": azure_docs.production_adr,
        "docs/deployment.md": azure_docs.deployment_diagram,
    },
}


def pages(project_name: str, apps: list[App], target: str) -> dict[str, str]:
    """Both pages for this target, written from this project's own answers."""
    if target not in PAGES:
        raise GenerationError(
            f"the {target} target provisions infrastructure but has no pages describing it: a managed "
            f"target arrives with its drawing and its decision record, as a row in target_docs.PAGES"
        )
    return {path: build(project_name, apps) for path, build in PAGES[target].items()}


# The README's *Before `./init`* table, middle rows only: what this cloud in particular asks of the machine
# that runs the first day's work. The rows around them — Python, the forge, the repository URL, somewhere to
# keep the passphrase — are the same wherever a project deploys, so they stay in `readme.py` and these are
# numbered into the middle of them. Each row is what to have and what proves it is there.
PREREQUISITES: dict[str, tuple[tuple[str, str], ...]] = {
    "aws": (
        ("**OpenTofu 1.12**, on the PATH as `tofu`", "`tofu version`"),
        (
            "**The AWS CLI, signed in as an administrator** of the account this project will live in — a "
            "profile, SSO or environment variables, whatever the CLI finds; `AWS_PROFILE=<admin profile> "
            "./init` is the usual spelling",
            "`aws sts get-caller-identity` names that account",
        ),
        (
            "**A region**: `export AWS_REGION=eu-west-2`, or `aws configure set region eu-west-2`",
            "`aws configure get region`",
        ),
    ),
    "azure": (
        ("**OpenTofu 1.12**, on the PATH as `tofu`", "`tofu version`"),
        (
            "**The Azure CLI, signed in as an Owner** of the subscription this project will live in — "
            "`az login`, then `az account set --subscription <id>` if you have more than one. Owner rather "
            "than Contributor because the bootstrap grants the pipeline its roles, and granting access is "
            "not something Contributor may do",
            "`az account show` names that subscription",
        ),
        (
            "**A region**: `export AZURE_LOCATION=uksouth`, or `az config set defaults.location=uksouth`",
            "`az config get defaults.location`",
        ),
    ),
}

# The nouns the README's *Production* section is written round, per target. `runtime` is what `infra/` runs
# a service as, in one phrase; `site` is what a browser app is served from, blank where a target has no
# browser app to serve; `credentials` is what `make bootstrap` looks for. Kept as words rather than as a
# second copy of the section, because everything around them — the pipeline, `AUTO_PROMOTE`, the rollback
# workflow, what `make bootstrap` does once — is the same promise whatever the cloud is.
WORDS: dict[str, dict[str, str]] = {
    "aws": {
        # Wrapped where it is wrapped in the README: the phrase lands mid-paragraph in a hand-wrapped page,
        # and each cloud's is the length it is.
        "runtime": "one ECS service per application deployed blue/green\nbehind its own load balancer",
        "site": (
            " The browser app is a private S3 bucket behind CloudFront, with `/api` routed to the service, "
            "so one bundle serves every environment from the same origin."
        ),
        "credentials": "administrator credentials the `aws` CLI can find",
    },
    "azure": {
        "runtime": "one Container App per application deployed by revision behind\nthe environment's own ingress",
        "site": (
            " The browser app is a static web app with the service it names linked as its API backend, so "
            "`/api` reaches that service by the product's own rule and one bundle serves every environment "
            "from the same origin."
        ),
        "credentials": "an Owner sign-in the `az` CLI can find",
    },
}
