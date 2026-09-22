"""`.claude/settings.json`: the commands a slice runs constantly, pre-approved."""
from __future__ import annotations

import json

from ..catalog import CATALOG
from ..layout import AT_ROOT, Layout
from ..services import App, backends_of, containers_of, families_of, services_of, web_apps
from ..targets import managed
from .compose import composed

# One entry point rather than several binaries: everything a Maven toolchain does — compile, test, the three
# analysers, dev mode — is a goal, so approving `./mvnw` is approving the toolchain. The wrapper and not
# `mvn`: that is the only spelling either Java backend's gates use, which is also why both share this.
MAVEN_PERMISSIONS = ["./mvnw *"]


def compaction_hooks(layout: Layout) -> dict[str, list[dict[str, object]]]:
    """What Claude Code runs around compaction and at the end of a turn, so a `/cruise` iteration resumes
    from its checkpoint and cannot end anywhere but on one of its four last lines.

    `SessionStart` with the `compact` matcher runs when the session continues after compaction and its
    stdout is added to the context; `PreCompact` runs just before. `Stop` runs when the model tries to end
    its turn, and a hook there can refuse: `stopping` does, in a session the runner started, while a
    checkpoint says an iteration is in flight and the turn's last line is not an end the contract knows —
    the one control a command file's prose is not. All three call the cruise script, which does nothing
    unless a runner's iteration is in flight, so a plain `/drive` session, and a typed `/cruise` (which
    starts the runner and ends), never see them. The other harnesses' equivalents, where one exists, are the
    registry's `compaction` and `hooks` rows, and `scripts/agents/project.py` writes those hook files.
    """
    script = layout.under("scripts/agents/cruise.py")
    return {
        "PreCompact": [{"hooks": [{"type": "command", "command": f"python3 {script} compacting"}]}],
        "SessionStart": [{"matcher": "compact", "hooks": [{"type": "command", "command": f"python3 {script} resume"}]}],
        "Stop": [{"hooks": [{"type": "command", "command": f"python3 {script} stopping"}]}],
    }


def claude_settings(apps: list[App], target: str = "none", layout: Layout = AT_ROOT) -> str:
    services = services_of(apps)
    per_backend = {
        "typescript": ["npm ci", "npm run verify", "npm test *"],
        "python": ["python3 *", "python -m pytest *", "python -m ruff *"],
        "go": ["go test *", "go vet *", "gofmt *"],
        "java-quarkus": MAVEN_PERMISSIONS,
        "java-spring": MAVEN_PERMISSIONS,
    }
    # Every service's toolchain, once each: a slice in any of them runs its commands constantly.
    native = list(dict.fromkeys(rule for backend in backends_of(apps) for rule in per_backend[backend]))
    # The read-only gates a slice runs constantly. `check-constitution` and its `--requirements`
    # printout change nothing on disk, so approving each invocation buys no safety.
    allowed = [
        "make",
        "make verify",
        "make test",
        "make check-constitution",
        "make constitution-requirements",
    ] + native
    # Of the family: whether npm is already approved is a property of the language, not of
    # whichever framework owns startup.
    web = web_apps(apps)
    if web and "typescript" not in families_of(apps):
        allowed += ["npm ci", *(f"npm --workspace {app.path} *" for app in web)]
    if containers_of(apps):
        # Starting and stopping the local services is the routine loop for a slice that touches
        # persistence. `docker compose down -v` is deliberately absent: it destroys the volume, which is a
        # decision to take deliberately rather than in passing.
        allowed += [
            "docker compose up *",
            "docker compose down",
            "docker compose ps *",
            "make services-up",
            "make services-down",
        ]
    allowed += [f"make {service.dev_target}" for service in services if service.transport is not None]
    for app in web:
        # Both spellings, because the second is the one an agent needs: an agent working somewhere the
        # browser is not — a container, a VM, a remote sandbox — has to bind the dev server past loopback,
        # and a rule that covered only the bare target would stop it at a prompt in exactly that case. The
        # variable is named rather than left to a trailing wildcard, so this permits the documented override
        # and not every argument `make` would otherwise accept.
        allowed += [f"make {app.dev_target}", f"make {app.dev_target} WEB_HOST=*"]
    if composed(apps):
        # Running the app, reading why it did not start, and stopping it again: the loop a demo is made of.
        # `docker compose down -v` stays absent for the same reason as above — destroying a volume is a
        # deliberate act — and so does `up` without the profile, which `make services-up` already covers.
        allowed += [
            "make demo",
            "make demo-down",
            "docker compose --profile app *",
            "docker compose logs *",
        ]
    # Two traits, asked separately, because they are separate: a store whose adapter carries its own schema
    # has nothing to migrate, and one proved inside the Docker-free gate has no second suite to run.
    if any(service.selection.migrating_feature is not None for service in services):
        allowed.append("make migrate")
    if any(service.selection.integration_feature is not None for service in services):
        allowed.append("make test-integration")
    if managed(CATALOG, target):
        # Building an image and proving it answers touch nothing outside this machine. `make deploy` and
        # `make rollback` are deliberately absent: they change an environment, and that is a prompt worth
        # answering every time.
        allowed += ["make build", "make build *", "make smoke-image", "make smoke-image *", "tofu fmt *", "tofu validate"]
    return json.dumps({"permissions": {"allow": [f"Bash({command})" for command in allowed]},
                       "hooks": compaction_hooks(layout)}, indent=2) + "\n"
