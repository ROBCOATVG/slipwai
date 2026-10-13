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
    ADD_COMMANDS,
    AGENT_RULES,
    DOCS_PAGES,
    IMAGE_REGISTRY,
    PIPELINE,
    README_WORDS,
    SCRIPTS,
    SETUP,
    SHAPES,
    TOOLS,
    Target,
)


def deployment_page(project: str, apps: object) -> str:
    """`docs/deployment.md`: where this project goes, in the words somebody on call would want."""
    return (
        "# Deployment\\n\\n"
        "TODO: what {name} runs this project on, what `make bootstrap` creates once, and what\\n"
        "`make deploy` applies per environment.\\n"
    )


name = "{name}"

TARGET = Target(
    name=name,
    answers={{
        # The two stacks every managed target has: the account's, applied once by `make bootstrap`, and
        # the service's, applied per environment by `make deploy`. The files are this package's own.
        SHAPES: {{"bootstrap": ("bootstrap/main.tf",), "service": ("service/main.tf",)}},
        # What a generated project gets under `scripts/`, by the path it lands at.
        SCRIPTS: {{"scripts/bootstrap.py": "scripts/bootstrap.py", "scripts/deploy.py": "scripts/deploy.py",
                  "scripts/setup.py": "scripts/setup.py"}},
        # The hook `./init` runs first: this package's own script puts its tools on the machine and settles
        # what it has to be told once. The keel runs it and reads nothing from it.
        SETUP: "scripts/setup.py",
        DOCS_PAGES: {{"docs/deployment.md": deployment_page}},
        # Each tool says what it is for and where to get it. A person told a tool is missing and not told
        # where it comes from is a person left searching.
        TOOLS: (
            ("tofu", "OpenTofu — what applies the stacks in infra/", "https://opentofu.org/docs/intro/install/"),
        ),
        # The cloud a person signs in to, what its registry is called, one of its addresses as an example,
        # and what `infra/` runs a service as. `scripts/deploy.py` is written round these four words.
        IMAGE_REGISTRY: {{"cloud": "{title}", "registry": "TODO", "example": "TODO", "runtime": "TODO"}},
        # The parts of the deploy workflow that are this cloud's. The job's shape is the keel's — `verify`
        # on `main`, one apply at a time, apply then smoke, production behind `AUTO_PROMOTE`, a rollback
        # that re-applies the release before — so what goes here is only what that shape cannot know.
        PIPELINE: {{
            # A CLI the runner may not ship, installed before anything needs it. "" where it ships one.
            "cli": "",
            # TODO: how a job becomes the deploy identity. Short-lived and federated where the forge can;
            # a stored credential is a fallback and says so.
            "credentials": "      # TODO: sign in to {name}\\n",
            # The build job's own CLI, where signing in to the registry needs one. "" where it does not.
            "build_cli": "",
            "registry_login": "      # TODO: sign the Docker daemon in to the registry\\n",
            # What the stacks and `scripts/deploy.py` read out of the environment, as `KEY: value` lines.
            "environment": "  IMAGE_REGISTRY: ${{{{ vars.IMAGE_REGISTRY }}}}\\n",
        }},
        # The nouns the README's *Production* section is written round. Everything around them — the
        # pipeline, `AUTO_PROMOTE`, the rollback workflow — is the same promise whatever the cloud is.
        README_WORDS: {{
            "runtime": "TODO: what `infra/` runs a service as, in one phrase",
            "site": " TODO: what a browser app is served from here, as a sentence; blank where none is.",
            "credentials": "TODO: what `make bootstrap` looks for",
        }},
        # What an agent is held to about how this project reaches production. Naming the cloud is what
        # makes it land: "no service calls {title}" is a sentence an author checks themselves against.
        AGENT_RULES: (
            "- This project deploys to {title} from `.github/workflows/deploy.yml`, and a pipeline is the\\n"
            "  only path to production: never apply production by hand, and never build an image on a\\n"
            "  laptop for it. TODO: the rest of what somebody working here has to know.\\n"
        ),
        # What `add-service` and `add-frontend` say afterwards. Said in the command because the report says
        # it once and the agent reads the command every time.
        ADD_COMMANDS: {{
            "service": ("- This project deploys to {title}, and `infra/` was regenerated. TODO: what\\n"
                        "  that means before the next deploy.\\n"),
            "web": ("- This project deploys to {title}: `infra/service/frontend.tf` was regenerated.\\n"
                    "  TODO: what that means before the next deploy.\\n"),
        }},
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

SETUP_SCRIPT = '''#!/usr/bin/env python3
"""What {name} needs on this machine, put there by this package: `./init` runs this first.

Each tool `TARGET` names in `tools` is installed here with whatever the machine installs things with, and
whatever {name} has to be told once — a region, a subscription — is asked for with a default on offer and
written where `scripts/bootstrap.py` reads it. `--check` says what would be done and does nothing. The keel
runs this and reads nothing from it: what a region is, or which package manager a tool comes from, is this
package's to know.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

#: Each tool, and the line that installs it per package manager, tried in this order; `sh` is the tool's
#: own installer and needs no manager.
INSTALLS = {{
    "tofu": {{"brew": "brew install opentofu", "winget": "winget install --id OpenTofu.Tofu -e",
             "sh": "curl -fsSL https://get.opentofu.org/install-opentofu.sh -o /tmp/install-opentofu.sh && "
                   "sh /tmp/install-opentofu.sh --install-method standalone && rm -f /tmp/install-opentofu.sh"}},
    # TODO: the {name} CLI, the same way
}}
PROBES = {{"brew": "brew", "apt": "apt-get", "dnf": "dnf", "winget": "winget", "sh": "sh"}}


def install(tool: str, check: bool) -> bool:
    for manager, line in INSTALLS[tool].items():
        if shutil.which(PROBES[manager]) is None:
            continue
        print(f"{{'would install' if check else 'Installing'}} {{tool}}: {{line}}", flush=True)
        if check:
            return False
        subprocess.run(line, shell=True)
        return shutil.which(tool) is not None
    print(f"{{tool}}: nothing on this machine installs it", flush=True)
    return False


def main(argv: list[str]) -> int:
    check = "--check" in argv
    left = [tool for tool in INSTALLS if shutil.which(tool) is None and not install(tool, check)]
    # TODO: settle what {name} has to be told once, with a default on offer, where bootstrap.py reads it
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
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
