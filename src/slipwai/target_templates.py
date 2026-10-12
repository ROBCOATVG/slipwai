"""What `slipwai package new --kind target` writes, as text.

Beside `package_templates.py` rather than in it: that module was already most of a budget of prose, and a
third kind's worth would have split it at whichever paragraph reached line 350 — the seam in the *prose*
that the plan's phase 16 is about. So the split is by kind, which is a seam a reader navigating by kind
actually wants.

**The scaffold is a target this keel loads.** It declares itself managed and answers every member the
protocol requires of a managed target, with the files it also writes: two stacks that apply nothing yet,
two scripts that do nothing yet, and a deployment page that says so. `slipwai package check` passes on it
the moment it is written, which is the whole point — a scaffold whose first lesson is that the tool is
broken teaches that.
"""
from __future__ import annotations

TARGET_MODULE = '''"""{title}: the target protocol, as this keel asks it.

The loader imports this module from the package directory and reads `TARGET`. Every member the protocol
declares `required` has to be answered by a *managed* target — one the keel provisions and deploys — and a
target that is not managed answers none of them.

Every `TODO` below is a decision the keel cannot make for you. `slipwai package check .` says which are
still open, and refuses an answer a generated project could not be deployed with.
"""
from __future__ import annotations

from slipwai.target_protocol import (
    DEPLOY_STEPS,
    DOCS_PAGES,
    IMAGE_REGISTRY,
    SCRIPTS,
    SHAPES,
    TOOLS,
    Target,
)


def deployment_page(selection: object) -> str:
    """`docs/deployment.md`: where this project goes, in the words somebody on call would want."""
    return (
        "# Deployment\\n\\n"
        "TODO: what {name} runs this project on, what `make bootstrap` creates once, and what\\n"
        "`make deploy` applies per environment.\\n"
    )


def deploy_steps(environment: str) -> str:
    """The workflow steps that take the deploy role for one environment, as YAML under `steps:`."""
    return (
        f"      # TODO: sign in to {name} for the {{environment}} environment, with the repository's\\n"
        f"      # short-lived token where the forge federates and the stored credential where it does not.\\n"
        f"      - run: make deploy ENVIRONMENT={{environment}}\\n"
    )


name = "{name}"

TARGET = Target(
    name=name,
    answers={{
        # The two stacks every managed target has: the account's, applied once by `make bootstrap`, and
        # the service's, applied per environment by `make deploy`. The files are this package's own.
        SHAPES: {{"bootstrap": ("bootstrap/main.tf",), "service": ("service/main.tf",)}},
        # What a generated project gets under `scripts/`, by the path it lands at.
        SCRIPTS: {{"scripts/bootstrap.py": "scripts/bootstrap.py", "scripts/deploy.py": "scripts/deploy.py"}},
        DOCS_PAGES: {{"docs/deployment.md": deployment_page}},
        # Each tool says what it is for and where to get it. A person told a tool is missing and not told
        # where it comes from is a person left searching.
        TOOLS: (
            ("tofu", "OpenTofu — what applies the stacks in infra/", "https://opentofu.org/docs/intro/install/"),
        ),
        # TODO: where a built image is pushed, and how the pipeline signs in to push it.
        IMAGE_REGISTRY: {{"repository": "TODO", "login": "TODO"}},
        DEPLOY_STEPS: deploy_steps,
    }},
)
'''

TARGET_README = '''# {title}

A slipwai target package: it says where a generated project goes to production, and
`slipwai generate --target {name}` writes a project that deploys there.

TODO: what {name} is, and what a project deployed on it actually runs on, in two sentences.

## What is in it

| Part | Where |
|---|---|
| The account stack, applied once by `make bootstrap` | `bootstrap/` |
| The service stack, applied per environment by `make deploy` | `service/` |
| What a project gets under `scripts/` | `scripts/` |
| The protocol answers the keel reads | `{module}/__init__.py` |
| The row the catalog's `targets` block gets | `target.json` |

## Checking it

```sh
{command} package check .
```

Every member the protocol requires of a managed target, answered; both stacks present and made of files
this package ships; and the version rule held over `VERSION`, `CHANGELOG.md` and `changelog.d/`.
'''

#: The two stacks, started as the one file each needs to be a stack at all. A target scaffolded with empty
#: directories would answer `shapes` with files that are not there, which is the first thing `check` refuses.
BOOTSTRAP_STACK = '''# The account stack: applied once, by `make bootstrap`, before anything is deployed.
#
# TODO: what has to exist in {name} before this project can be deployed into it at all — the state store
# the service stack keeps its state in, the registry images are pushed to, and the role the pipeline
# becomes. Nothing here is per environment; the service stack is.

terraform {{
  required_version = ">= 1.12"
}}
'''

SERVICE_STACK = '''# The service stack: applied per environment, by `make deploy`.
#
# TODO: one deployable per application, behind whatever {name} puts in front of it, with the backing
# services the project chose. The project's own answers arrive as `project.auto.tfvars.json`, one map of
# the services, so adding a service is a change to the data and never to this file.

terraform {{
  required_version = ">= 1.12"
}}
'''

SCRIPT = '''#!/usr/bin/env python3
"""{what} a project deployed to {name}.

This runs inside a generated project, which has no slipwai to import — the standard library only, like
every other script under `scripts/`.

TODO: {what_lower}. Every failure path names the command that fixes it; a message saying what is wrong and
not what to do about it costs the reader a search.
"""
from __future__ import annotations

import sys


def main() -> int:
    print("[{name}] TODO: {what_lower}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
