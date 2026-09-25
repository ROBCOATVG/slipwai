"""`.github/workflows/verify.yml`: the same gate `make verify` runs, on whichever forge this lands on."""
from __future__ import annotations

from ..backends import BACKEND_TOOLING, NODE_MAJOR, PYTHON_VERSION, UV_VERSION, Tooling
from ..layout import AT_ROOT, Layout
from ..services import App, families_of, services_of, web_apps
from ..tooling import app_tooling
from .ci_services import CI_SERVICES


def dependency_paths(paths: list[str]) -> str:
    """A `cache-dependency-path` value: the one file, or a block with one line per service."""
    if len(paths) == 1:
        return paths[0]
    return "|\n" + "".join(f"            {path}\n" for path in paths).rstrip("\n")


NODE_SETUP = (
    f"      - uses: actions/setup-node@v6\n        with:\n          node-version: {NODE_MAJOR}\n          cache: npm\n"
    "          cache-dependency-path: package-lock.json\n"
)

# What every `npm ci` in this workflow does about the registry, for a project that has one.
#
# `audit: false` is the one that matters. npm ends an install with a single POST to the registry's bulk
# advisories endpoint, and since 2026-09-04 that endpoint has answered in minutes rather than milliseconds —
# against about a tenth of a second for an ordinary packument GET, so the slowness is the registry's and not
# any one network's. npm does not fail on it: it waits out `fetch-timeout`, prints a summary with no audit in
# it, and carries on. That is what makes the stall so easy to misread — the install still passes, and the
# only tell is that a good run says `added N packages, and audited N+2 packages` where a stalled one says
# only `added N packages`. With npm's default five-minute timeout it costs five minutes per install, silently.
#
# Not asking costs this gate no strictness, because `make verify` never reads the audit; a project that wants
# advisories should run `npm audit` as a step of its own, where a slow answer is visible and its own failure.
# The rest cap what any one slow answer can cost. `prefer-offline` is safe under `npm ci` specifically: the
# lockfile already names every version and its integrity hash, so there is nothing fresher to ask for.
NPM_ENV = (
    "env:\n"
    "  npm_config_audit: 'false'\n"
    "  npm_config_prefer_offline: 'true'\n"
    "  npm_config_maxsockets: '5'\n"
    "  npm_config_fetch_timeout: '60000'\n"
    "  npm_config_fetch_retries: '5'\n"
)


def toolchain_setup(family: str, services: list[App]) -> str:
    """One `actions/setup-*` per language family, keyed on that family's services' dependency files.

    Which JDK to install and where the dependency cache lives are the toolchain's answers rather than a
    framework's, so both Java backends share the Java row. Temurin 25 is the current LTS, the floor Quarkus
    3.33's AOT cache generation needs and well inside Spring Boot 4.1's 17-to-26 range. `cache: maven` keys
    on the poms, so a run that changes no dependency downloads nothing; it also covers the Maven the wrapper
    fetches, which `setup-java@v5` caches under a second key derived from `maven-wrapper.properties` alone.
    """
    return {
        "typescript": NODE_SETUP,
        # uv is this backend's toolchain, and no runner ships it. Installed from PyPI at the factory's
        # pin rather than through a third-party action: this job already asks PyPI for everything else,
        # and an action is one more thing that has to resolve on whichever forge the project landed on.
        # The cache is uv's own download cache, keyed on the committed locks — `uv sync --locked`
        # installs exactly what they name, so a run that changes no lock downloads nothing.
        "python": "      - uses: actions/setup-python@v6\n        with:\n"
        f"          python-version: '{PYTHON_VERSION}'\n"
        f"      - run: python3 -m pip install --disable-pip-version-check -q uv=={UV_VERSION}\n"
        "      - uses: actions/cache@v4\n        with:\n          path: ~/.cache/uv\n"
        "          key: uv-${{ runner.os }}-${{ hashFiles("
        + ", ".join(f"'{s.path}/uv.lock'" for s in services)
        + ") }}\n",
        # One Go version for the workspace, read from the first Go service's module; `go.work` pins the rest.
        # The cache is keyed on every module's `go.sum` and the workspace's `go.work.sum` by name, because
        # setup-go's default key is a `go.sum` at the root, which a workspace does not have: it restores
        # nothing, saves nothing, says so only as a warning, and the run stays green and downloads and
        # compiles every module from cold each time — a cache that never hits looks like one that does.
        "go": "      - uses: actions/setup-go@v7\n        with:\n"
        f"          go-version-file: {services[0].path}/go.mod\n"
        "          cache-dependency-path: "
        + dependency_paths([*(f"{s.path}/go.sum" for s in services), "go.work.sum"])
        + "\n",
        "java": (
            "      - uses: actions/setup-java@v5\n        with:\n          distribution: temurin\n"
            "          java-version: '25'\n          cache: maven\n"
            f"          cache-dependency-path: {dependency_paths([f'{s.path}/pom.xml' for s in services])}\n"
        ),
    }[family]


def container_setup(tooling: Tooling) -> str:
    """Whatever `make` itself needs in this image, before the first target runs.

    Empty for every backend whose image already ships it, which is all of them but one.
    """
    return f"      - run: {tooling['container_setup']}\n" if tooling["container_setup"] else ""


# How a job with `container:` gets the code, which is not `actions/checkout`.
#
# `actions/checkout` is a JavaScript action, and a job with `container:` runs a JS action *inside* that
# image rather than on the runner host. GitHub mounts its own Node into the container, so an action runs
# there whatever the image holds; Gitea's act_runner does not, and execs a bare `node` in an image that has
# none. Every `ci_image` but the TypeScript one is then a job that dies in its very first step with
# `exec: "node": executable file not found in $PATH` and exit 127 — before a line of the suite runs, with
# every later step reported `skipped`, and nothing whatever wrong with the code it was gating.
#
# Checked in the images rather than assumed: `golang:1.26-bookworm`, `python:3.13-bookworm` and
# `maven:3.9.16-eclipse-temurin-25-noble` each ship git and no node; `node:24-bookworm` ships both. So the
# job clones itself with git, and the containerised job is left with no `uses:` at all — the whole class
# leaves generated CI rather than one instance of it being worked around. A backend added later inherits
# that: `git` is one more thing its `ci_image` owes, and `node` stops being one.
#
# It also retires the one real argument for `needs: verify` here. That argument was a shared, unlocked act
# action cache (`/root/.cache/act/<hash>`, one directory per action) which two jobs starting the same
# instant could race, the loser dying in `Post actions/checkout@v6` with `Cannot find module .../dist/index.js`
# after all its real steps had passed. A job that downloads no action cannot lose that race.
#
# `--depth 1` of `$GITHUB_SHA` rather than of a branch: `$GITHUB_REF` moves when something merges while
# this run sits in a queue, and a suite that quietly tested a commit other than the one the run reports is
# worse than one that failed to start. Both forges serve a shallow fetch of a bare object id — Gitea's was
# checked against a real instance rather than assumed, since git refuses one by default and it is the whole
# reason this works.
#
# The credential is passed with `-c`, for the one fetch, rather than `git config`-ed into `.git/config`
# where every later step in the job could read it back out. `tr -d` because `base64` wraps at 76 columns
# and a token long enough to wrap would otherwise be sent with a newline in the middle of the header.
CONTAINER_CHECKOUT = """      - name: Check out the commit under test
        run: |
          git init -q -b ci .
          git remote add origin "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY"
          git -c "http.extraheader=Authorization: Basic $(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 | tr -d '\\n')" \\
            fetch -q --depth 1 origin "$GITHUB_SHA"
          git checkout -q FETCH_HEAD
        env:
          GITHUB_TOKEN: ${{ github.token }}
"""


def integration_job(family: str, services: list[App], apps: list[App], several: bool, layout: Layout) -> str:
    """The job that runs one language family's integration suites against real infrastructure.

    `container:` is what makes this job correct on more than one kind of runner, and it is worth knowing
    why. Without it, a GitHub-hosted runner puts the job on the bare VM, where a service container's
    published port lands on `localhost` — so `localhost:5433` works there and nowhere else. A third-party
    runner (Gitea's act-runner, for one) always containerises the job, and inside that container `localhost`
    is the job's own loopback, never the sibling service. Only the service's *label* resolves, through the
    Docker network GitHub Actions creates once the job itself has a container. So the job takes a
    container, and the stanza in `CI_SERVICES` addresses the service by that label and drops the port
    mapping. That is correct on both, rather than correct on whichever runner was tried first.

    Taking that container is also why this job checks itself out with `git` rather than
    `actions/checkout` — a JS action runs *inside* the image, and most `ci_image`s have no Node to run it
    with. `CONTAINER_CHECKOUT` says the rest.

    One job per family with a suite to run, because a job has one container image and an image carries one
    toolchain: `integration` while there is one such family, `integration-<family>` once there are several.
    The image tracks the toolchain the verify job installs; move the two together.

    This job deliberately carries no `needs:`, and the emitted YAML says why at the point where somebody
    will want to add one. The short version: `needs: verify` was tried in a real generated project and left
    the dependent job permanently blocked on `push` runs against `main`, while `pull_request` unblocked
    correctly — so the pull request introducing it was green and the branch it protected silently stopped
    running its suites.
    """
    tooling = BACKEND_TOOLING[services[0].backend]
    features = [f for f in dict.fromkeys(s.selection.integration_feature for s in services) if f is not None]
    stanzas = "".join(CI_SERVICES[feature]["service"] for feature in features)
    readiness = "\n".join(CI_SERVICES[feature]["readiness"] for feature in features)
    installs = "".join(
        f"      - run: {command}\n"
        for command in dict.fromkeys(app_tooling(s, apps)["ci_install"] for s in services)
    )
    # `migrate` only where something declared it has migrations: a store that carries its own schema has
    # nothing to apply, and a CI step that ran an absent target would fail the gate it belongs to. One
    # service is the whole project's targets; several are each service's own, so the job runs only its
    # family's suites.
    if len(services_of(apps)) == 1:
        targets = ["migrate"] if services[0].selection.migrating_feature else []
        targets.append("test-integration")
    else:
        targets = []
        for service in services:
            if service.selection.migrating_feature:
                targets.append(f"migrate-{service.name}")
            targets.append(f"test-integration-{service.name}")
    # Under the feature's own marker when the job serves one feature, so pruning it prunes the job.
    marker = features[0] if len(features) == 1 else None
    begin = f"# backing-service:{marker}:begin\n" if marker else ""
    end = f"# backing-service:{marker}:end\n" if marker else ""
    name = f"integration-{family}" if several else "integration"
    return f"""
{begin}  {name}:
    runs-on: ubuntu-latest
    container: {tooling["ci_image"]}
    # No `needs: verify` here, on purpose, and this is the second time somebody will have thought of it.
    #
    # There used to be a real reason to want one: on a runner where act shares a single unlocked action
    # cache (`/root/.cache/act/<hash>`, one directory per action, no lock), this job and `verify` started
    # the same instant, and the loser died in `Post actions/checkout@v6` with `Cannot find module
    # .../dist/index.js` after all its real steps had passed. That reason is gone — the steps below download
    # no action at all, so there is no cache entry for the two jobs to race over.
    #
    # The reason not to add one: `needs:` was tried, and on Gitea the dependent job stays "Blocked by
    # required conditions" forever on a `push` run, with every job it depends on already finished. It
    # unblocks correctly on `pull_request`. So the pull request that adds it goes green, and `main` quietly
    # stops running its integration suites — a gate that is not running, and a status that stays pending for
    # anything watching the run. That is strictly worse than a flake, which at least shows up red.
    #
    # If you reintroduce it, verify a **push** run on `main`, not a pull request.
{stanzas}    steps:
{CONTAINER_CHECKOUT}{container_setup(tooling)}{installs}{readiness}
      - run: {layout.make} {' '.join(targets)}
{end}"""


def workflow(apps: list[App], layout: Layout = AT_ROOT, event: bool = False) -> str:
    """The gate runs `make verify`, whose recipes already loop over the services — so CI loops too, inside
    Make, rather than fanning out a matrix. A matrix would give CI a shape the laptop does not have, and the
    project's rule is that the two run the same command; it would also start one job per service on a
    runner that has one Docker daemon. What the workflow knows per service is only where the caches key,
    and — where the services' languages differ — one toolchain setup per family, and one integration job
    per family that has a suite needing real infrastructure."""
    services = services_of(apps)
    families = families_of(apps)
    setups = "".join(
        toolchain_setup(family, [s for s in services if s.language == family]) for family in families
    )
    # Of the family: a TypeScript service behind any framework has already set Node up above.
    frontend_setup = NODE_SETUP if web_apps(apps) and "typescript" not in families else ""
    # The event profile's `check-drawio` runs the TypeScript pipeline — no browser, but Node — so a project
    # with no Node of its own is given one here, pinned to the same major the event-model workflow uses.
    # Without `cache: npm`, which needs a lockfile the pipeline's own manifest does not keep.
    event_setup = (
        f"      - uses: actions/setup-node@v6\n        with:\n          node-version: {NODE_MAJOR}\n"
        if event and not frontend_setup and "typescript" not in families
        else ""
    )
    # The suite that needs real infrastructure is a second job with its own service container, so the
    # `verify` job stays free of infrastructure exactly as `make verify` is locally. Which of a service's
    # answers brings such a suite, and which one has migrations to apply first, are traits the options
    # declare in `catalog.json`, and the container comes from `CI_SERVICES`.
    integrating = {
        family: [s for s in services if s.language == family and s.selection.integration_feature is not None]
        for family in families
    }
    integrating = {family: found for family, found in integrating.items() if found}
    jobs = "".join(
        integration_job(family, found, apps, len(integrating) > 1, layout) for family, found in integrating.items()
    )
    # Only where there is an `npm ci` to govern: a project with no Node service and no web app never asks
    # the registry anything, and workflow-level environment it does not use is noise in the file it reads.
    npm_env = NPM_ENV if web_apps(apps) or "typescript" in families else ""
    return (
        """name: verify
on:
  # Only `main`. A branch with an open pull request is already covered by the `pull_request` trigger, and
  # running both puts two independent copies of every job on one commit: twice the runner time, and a
  # combined status that goes red when either copy flakes rather than when the code is wrong. A merge to
  # `main` still runs here, which is what a deploy workflow reads.
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
"""
        + npm_env
        + """jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
"""
        + setups
        + frontend_setup
        + event_setup
        + f"      - run: {layout.make} verify\n"
        + jobs
    )
