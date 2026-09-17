"""The gate's CI configuration for a repository the factory did not make, written for the forge found.

An Actions workflow for GitHub and Gitea — the same file, since Gitea and Forgejo run it — that sets up the
toolchains the wrapped applications recorded rather than the ones the catalog knows; a job under the delivery
directory for GitLab, to be included from the repository's own `.gitlab-ci.yml`, which is theirs and is never
written over; and nothing at all for a forge the factory cannot write a job for, or where there is no CI —
`gate_path` says None, and the report says what to run instead. Split from `adopted.py` (brownfield adoption,
experimental as `AGENTS.md` defines the word) when the pages and the CI together passed the module budget.
"""
from __future__ import annotations

from ..layout import Layout
from ..services import App, wrapped_of

# What CI installs for a wrapped application's toolchain, by `toolchain.kind`; `{version}` is the pin the tree
# carried, or the default beside it where it carried none — said in the workflow, so it is a line to correct
# and not a guess to discover.
SETUP = {
    "node": ("actions/setup-node@v6", "node-version", "22"),
    "python": ("actions/setup-python@v6", "python-version", "3.13"),
    "go": ("actions/setup-go@v7", "go-version", "1.24"),
    "java": ("actions/setup-java@v5", "java-version", "21"),
    "dotnet": ("actions/setup-dotnet@v5", "dotnet-version", "8.0.x"),
    "php": ("shivammathur/setup-php@v2", "php-version", "8.3"),
    "ruby": ("ruby/setup-ruby@v1", "ruby-version", "3.3"),
}


ACTIONS_GATE = ".github/workflows/verify-delivery.yml"


GITLAB_GATE = "ci/verify-delivery.gitlab-ci.yml"


# The official image per toolchain for a GitLab job, where one toolchain is all the repository builds with. These
# three carry `make`; a Java, .NET, PHP or Ruby build needs an image somebody chooses, and the job says so.
GITLAB_IMAGES = {"node": "node:{version}", "python": "python:{version}", "go": "golang:{version}"}


def gate_path(forge: str, layout: Layout) -> str | None:
    """Where the gate's CI configuration goes for a forge: an Actions workflow for GitHub and Gitea, an includable
    job under the delivery directory for GitLab, nothing the factory can write for anything else."""
    if forge in ("github", "gitea"):
        return ACTIONS_GATE
    if forge == "gitlab":
        return layout.under(GITLAB_GATE)
    return None


def setup_steps(apps: list[App]) -> str:
    """One `setup-*` step per toolchain the wrapped applications run on, once each, pinned where the tree was."""
    steps = ""
    seen: set[tuple[str, str]] = set()  # one setup per toolchain and version
    for app in wrapped_of(apps):
        toolchain = app.toolchain or {}
        kind, version = toolchain.get("kind", ""), toolchain.get("version", "")
        if kind not in SETUP or (kind, version) in seen:
            continue
        seen.add((kind, version))
        action, key, default = SETUP[kind]
        note = "" if version else f"          # no pin found in the tree for {app.path}; {default} is a default to confirm\n"
        java = "          distribution: temurin\n" if kind == "java" else ""
        steps += f"      - uses: {action}\n        with:\n{java}{note}          {key}: '{version or default}'\n"
    if any((app.toolchain or {}).get("ecosystem") == "ant" for app in wrapped_of(apps)):
        # No wrapper fetches Ant the way `mvnw` fetches Maven, so the runner installs it — until the programme's
        # first step moves the build to Maven or Gradle, when this line goes with `build.xml`.
        steps += ("      - run: command -v ant >/dev/null || sudo apt-get install -y -q ant"
                  "  # the build is Ant; Maven or Gradle is the programme's first step\n")
    return steps


def delivery_workflow(apps: list[App], layout: Layout, branch: str = "main") -> str:
    """`.github/workflows/verify-delivery.yml`: the delivery gate, beside whatever CI the repository already runs, on
    pushes to the branch the repository actually lands on (`ci.branch`, read from `.git`) and on every pull request."""
    return f"""name: verify delivery
# Written by slipwai adopt (experimental). Runs the delivery gate — the recorded commands of the applications
# that were here, and the method's own checks — from the Makefile under {layout.delivery}/. The repository's
# own CI is untouched; this is one more workflow beside it.
on:
  push:
    branches: [{branch}]
  pull_request:
permissions:
  contents: read
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
{setup_steps(apps)}      - run: {layout.make} verify
{smoke_job(apps, layout)}"""


def smokes(apps: list[App]) -> bool:
    """Whether any wrapped application records a `smoke` command — the one the gate runs as a job of its own."""
    return any((app.commands or {}).get("smoke") for app in wrapped_of(apps))


def smoke_job(apps: list[App], layout: Layout) -> str:
    """The workflow's second job, present only where a `smoke` command is recorded: each application started by that
    command and proved to answer, after `verify` and apart from it, since it needs what the application needs."""
    if not smokes(apps):
        return ""
    return f"""  smoke:
    # Each application that recorded a `smoke` command, started by it and proved to answer. A suite that never
    # builds the context cannot see a constructor the container cannot call; this can, which is why it is a job.
    needs: verify
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
{setup_steps(apps)}      - run: {layout.make} smoke
"""


def gitlab_job(apps: list[App], layout: Layout) -> str:
    """`<delivery>/ci/verify-delivery.gitlab-ci.yml`: one job that runs the gate, to be included from the
    repository's own `.gitlab-ci.yml` — which is theirs and is not written over. The image is the toolchain's
    official one where a single toolchain carries `make`; anything else is a line to fill, said in place."""
    toolchains = {
        ((app.toolchain or {}).get("kind", ""), (app.toolchain or {}).get("version", "")) for app in wrapped_of(apps)
    }
    kinds = {kind for kind, _ in toolchains if kind}
    if len(toolchains) == 1 and next(iter(kinds), "") in GITLAB_IMAGES:
        kind, version = next(iter(toolchains))
        default = {"node": "22", "python": "3.13", "go": "1.24"}[kind]
        image = f"  image: {GITLAB_IMAGES[kind].format(version=version or default)}\n"
        if not version:
            image = f"  # no pin found in the tree; {default} is a default to confirm\n" + image
    else:
        needed = ", ".join(sorted(f"{kind} {version}".strip() for kind, version in toolchains)) or "nothing recorded"
        image = f"  # image: choose one that carries `make` and {needed}, or install them in before_script\n"
    include = layout.under(GITLAB_GATE)
    return f"""# Written by slipwai adopt (experimental). The delivery gate as a GitLab CI job: the recorded commands of the
# applications that were here, and the method's own checks, from the Makefile under {layout.delivery}/. The
# repository's own .gitlab-ci.yml is untouched; include this job from it:
#
#   include:
#     - local: {include}
verify-delivery:
  stage: test
{image}  script:
    - {layout.make} verify
""" + (f"""
# Each application that recorded a `smoke` command, started by it and proved to answer — apart from the gate,
# since it needs what the application needs.
smoke-delivery:
  stage: test
  needs: [verify-delivery]
{image}  script:
    - {layout.make} smoke
""" if smokes(apps) else "")
