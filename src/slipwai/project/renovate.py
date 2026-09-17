"""`renovate.json`: what keeps this project's exact pins from becoming old exact pins.

Every dependency a generated project has is pinned exactly — a version, never a range — which is the right
default and has one consequence nobody chose: nothing moves them. A pinned tree is a tree that silently ages
until a security advisory or a broken build forces a jump of several majors at once, which is the expensive
kind of upgrade.

This is the configuration that turns that into a weekly pull request. Three things about it are worth reading
before changing it:

**It is written for this repository's actual layout, not for a default one.** Renovate finds a root
`package.json` and its workspaces, each service's `pyproject.toml` and the `uv.lock` beside it, `pom.xml` and
`go.mod` by itself — the Python half through the `pep621` manager, which reads both the runtime list and the
development group and re-locks with uv. Gitea Actions workflows are read by the same `github-actions` manager
GitHub's are, because they are the same file format in the same directory.

**The toolchain moves in one pull request or not at all.** A Node major is written in `.nvmrc`, in the CI
workflow's `setup-node` input and in the Compose image; a CPython minor in `.python-version` and in
`setup-python`. Renovate reads the pin files natively and the workflow inputs through a custom manager
declared here, because no manager reads an action's *inputs* — without it, Renovate would raise `.nvmrc` to
the next major and leave CI installing the old one, which is precisely the split `.nvmrc` was added to close.
Both are grouped under one name so they arrive together.

**A major waits to be asked for.** Minor and patch updates are grouped per ecosystem and open on their own; a
major lands on the dependency dashboard with a checkbox instead, because a major in a pinned tree is a piece
of work rather than a bump. Vulnerability fixes ignore the schedule entirely.

None of it does anything on its own. Renovate is a bot, and it has to be *running*: on GitHub that is the
Renovate app installed on the repository, and on a Gitea or Forgejo forge it is a self-hosted run —
`renovate` as a scheduled workflow on the forge's own runner, or a cron job — with a token that may open pull
requests. Until one of those exists this file is documentation of an intent. `docs/whats-included.md` says so
where a reader of the project will meet it.
"""
from __future__ import annotations

import json

from ..services import App, families_of, services_of, web_apps
from .shared_packages import node_workspace

# The workflow files whose *inputs* carry a toolchain version. A regex rather than a glob because the
# directory is literal and the extension is either spelling.
WORKFLOWS = "/^\\.github/workflows/[^/]+\\.ya?ml$/"


def toolchain_managers(node: bool, python: bool) -> list[dict]:
    """The custom managers that read a toolchain version out of a workflow's action inputs.

    `actions/setup-node` and `actions/setup-python` take the version as an input value, and the
    `github-actions` manager updates the action reference rather than what is passed to it. So the number CI
    installs is invisible to Renovate unless it is read here — and a pin file raised without it is a project
    whose gate and whose laptop are on different majors again.
    """
    managers = []
    if node:
        managers.append({
            "customType": "regex",
            "description": "The Node major `actions/setup-node` installs, which no manager reads.",
            "managerFilePatterns": [WORKFLOWS],
            "matchStrings": ["node-version: '?(?<currentValue>\\d+(?:\\.\\d+)*)'?"],
            "depNameTemplate": "node",
            "datasourceTemplate": "node-version",
            "versioningTemplate": "node",
        })
    if python:
        managers.append({
            "customType": "regex",
            "description": "The CPython minor `actions/setup-python` installs, which no manager reads.",
            "managerFilePatterns": [WORKFLOWS],
            "matchStrings": ["python-version: '?(?<currentValue>\\d+\\.\\d+(?:\\.\\d+)?)'?"],
            "depNameTemplate": "python",
            "datasourceTemplate": "python-version",
        })
    return managers


# One group per ecosystem, so a week's updates are one pull request per toolchain rather than one per
# package — and each is reviewed by whoever knows that toolchain. Keyed by the language family or manager
# that produces it.
GROUPS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("npm", ("npm",), "the npm workspace: every deployable's dependencies and the shared packages'"),
    ("python", ("pep621",), "the Python services' dependencies, and the uv lock beside each manifest"),
    ("go", ("gomod",), "the Go modules, and the checksums that come with them"),
    ("maven", ("maven",), "the Maven builds, including the plugins the gate's analysers are"),
    ("workflow actions", ("github-actions",), "the actions the CI workflows use, on whichever forge runs them"),
    ("containers", ("docker-compose", "dockerfile"), "the images the backing services and the demo run"),
)


def managers_present(apps: list[App]) -> set[str]:
    """Which Renovate managers this project actually gives something to read."""
    families = set(families_of(apps))
    managers = {"github-actions", "docker-compose"}
    if node_workspace(apps):
        managers |= {"npm", "nvm"}
    if "python" in families:
        managers |= {"pep621", "pyenv"}
    if "go" in families:
        managers.add("gomod")
    if "java" in families:
        managers.add("maven")
    return managers


def renovate_config(apps: list[App]) -> str:
    """This project's Renovate configuration, as the JSON the bot reads.

    Nothing here is conditional on there being a bot: the file is correct whether or not one is running, and
    a project that never installs Renovate has a statement of how it would want to be updated.
    """
    managers = managers_present(apps)
    python = "pep621" in managers
    node = "npm" in managers
    services = ", ".join(f"`{service.path}`" for service in services_of(apps)) or "no service"
    config: dict = {
        "$schema": "https://docs.renovatebot.com/renovate-schema.json",
        "description": [
            "How this repository's exactly pinned dependencies are kept current.",
            "Nothing here runs by itself: on GitHub, install the Renovate app on this repository; on Gitea "
            "or Forgejo, run Renovate self-hosted — as a scheduled workflow on the forge's own runner, or a "
            "cron job — with a token that may open pull requests. Until then this file states an intent.",
            f"Written for this repository's layout: {services}"
            f"{', the browser app, ' if web_apps(apps) else ', '}and the workflows under `.github/workflows/`.",
        ],
        "extends": ["config:recommended", ":dependencyDashboard"],
        "timezone": "Etc/UTC",
        # One window a week, so updates are something a person sits down to rather than a stream. The
        # lockfile refresh is monthly and separate: it moves transitive versions nothing declared.
        "schedule": ["before 6am on monday"],
        "prConcurrentLimit": 5,
        # Every dependency here is pinned to an exact version, and a new one Renovate adds should be too.
        "rangeStrategy": "pin",
        "lockFileMaintenance": {
            "enabled": True,
            "schedule": ["before 6am on the first day of the month"],
        },
        # A fix for a known vulnerability is not a weekly chore, so it ignores the window above.
        "vulnerabilityAlerts": {"schedule": ["at any time"], "labels": ["security"]},
        # The OSV database rather than a forge's own advisories, because this repository may live on a forge
        # that has none.
        "osvVulnerabilityAlerts": True,
    }
    if custom := toolchain_managers(node, python):
        config["customManagers"] = custom
    config["packageRules"] = package_rules(managers, node, python)
    # `ensure_ascii=False` because the descriptions are prose and a reader of this file should meet an em
    # dash rather than a `—`; every file this factory writes is UTF-8.
    return json.dumps(config, indent=2, ensure_ascii=False) + "\n"


def package_rules(managers: set[str], node: bool, python: bool) -> list[dict]:
    """One group per ecosystem present, the toolchain as a group of its own, and majors held back."""
    rules: list[dict] = []
    if node or python:
        pins = [name for name, present in (("node", node), ("python", python)) if present]
        rules.append({
            "description": (
                "The toolchain versions, which are written in the pin file, the CI workflow's action input "
                "and the Compose image — three files that are wrong the moment one of them moves alone."
            ),
            "matchDepNames": pins,
            "groupName": "toolchain",
        })
    for name, group_managers, what in GROUPS:
        if not managers.intersection(group_managers):
            continue
        rules.append({
            "description": f"Minor and patch updates to {what}, as one pull request.",
            "matchManagers": list(group_managers),
            "matchUpdateTypes": ["minor", "patch", "digest"],
            "groupName": name,
        })
    rules.append({
        "description": (
            "A major version in an exactly pinned tree is a piece of work rather than a bump — a changed "
            "API, usually a changed gate. It waits on the dependency dashboard until somebody asks for it."
        ),
        "matchUpdateTypes": ["major"],
        "dependencyDashboardApproval": True,
    })
    return rules
