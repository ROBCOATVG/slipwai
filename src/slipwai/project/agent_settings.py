"""`.claude/settings.json`: the commands a slice runs constantly, pre-approved."""
from __future__ import annotations

import json

from ..assets import TOOLKIT_ROOT
from ..catalog import CATALOG
from ..layout import AT_ROOT, Layout
from ..npm_workspace import npm
from ..registry import AGENT_PERMISSIONS, registry
from ..services import App, backends_of, containers_of, families_of, services_of, web_apps
from ..targets import managed
from .compose import composed


def harness_hooks(layout: Layout) -> dict[str, list[dict[str, object]]]:
    """Claude Code's own moments, each pointed at the one script that answers them: `session.py`.

    Every row here is a *point of a closed set* — `guards.py`'s or `hooks.py`'s — and not a behaviour of its
    own. That is the whole of what changed in 7.7b. These rows used to name `cruise.py <verb>`, so the
    control-file refusal and the compaction protocol were things the keel wrote into one harness's settings
    file: they worked on Claude Code and silently nowhere else, which is the failure the two closed sets
    exist to end. `session.py` runs the keel's own answer and then whatever an extension declared at that
    point, so an extension says `before-write` once and gets it wherever a harness has such an event.

    `PreToolUse` runs before a tool call and a command exiting 2 refuses it, the stderr becoming the result
    the model reads. `Stop` runs when the model tries to end its turn and can refuse that too. `PreCompact`
    runs just before compaction, and `SessionStart` with the `compact` matcher when the session continues
    after it, its stdout added to the context. The other harnesses' equivalents, where one exists, are the
    registry's `hooks` rows, and `scripts/agents/project.py` writes those hook files from the same verbs.
    """
    # `$CLAUDE_PROJECT_DIR` because a hook runs with whatever directory the session happens to be in, and
    # these paths are relative to the repository root. A session opened in a subdirectory — or one whose
    # tools changed directory — ran `python3 delivery/scripts/agents/cruise.py` against a path that is not
    # there, and the hook failed silently rather than doing its job. The scripts already find the root from
    # their own location; it was only the command that launches them that assumed one.
    here = "$CLAUDE_PROJECT_DIR/"
    script = here + layout.under("scripts/agents/session.py")
    return {
        "PreCompact": [{"hooks": [{"type": "command", "command": f"python3 {script} before-compact"}]}],
        "SessionStart": [{"matcher": "compact",
                          "hooks": [{"type": "command", "command": f"python3 {script} after-compact"}]},
                         # A person's `/sail` has no captain in front of it, so whatever an extension does at
                         # the start of a session — an index made sound and current, the step a captain takes
                         # before every stage — happens here. The budget is long because a rebuild can be as
                         # long as a first index, and the guards registry's own budget bounds each one.
                         {"matcher": "startup", "hooks": [{"type": "command", "command": f"python3 {script} session",
                                                           "timeout": 900}]}],
        "Stop": [{"hooks": [{"type": "command", "command": f"python3 {script} before-stop"}]}],
        # One row per shape a tool call comes in, because a guard is handed a path, a command or a URL and the
        # three are not the same question. In a session the captain dispatched, an edit or a shell write to a
        # gate or a control of the run — `scripts/`, the Makefile, `tools/`, CI, this file, the two registries —
        # is refused before it lands; in every session, whatever an extension declared at that point runs.
        "PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit",
                        "hooks": [{"type": "command", "command": f"python3 {script} before-write"}]},
                       {"matcher": "Bash",
                        "hooks": [{"type": "command", "command": f"python3 {script} before-command"}]},
                       {"matcher": "WebFetch|WebSearch",
                        "hooks": [{"type": "command", "command": f"python3 {script} before-fetch"}]},
                       # `Bash` as well as the search tools, because a `grep` or an `rg` through the shell is
                       # the same search by another door — and an extension that wants to say *don't grep for
                       # that, ask the index* has to see both. It runs in every session, not only the
                       # captain's, because a guard is the project's rule and not the run's.
                       {"matcher": "Grep|Glob|Bash",
                        "hooks": [{"type": "command", "command": f"python3 {script} before-search"}]},
                       {"matcher": "Agent|Task",
                        "hooks": [{"type": "command", "command": f"python3 {script} before-delegate"}]}],
        # The one guard that fires after a tool call rather than before it: a delegate has answered and its
        # answer has not been used yet, so an extension may still refuse it and have the agent ask again. A
        # delegate also came back having edited whatever it edited, which is why an index syncs here rather
        # than being trusted to have followed.
        "PostToolUse": [{"matcher": "Agent|Task",
                         "hooks": [{"type": "command", "command": f"python3 {script} after-delegate"}]}],
        # The activity log, which none of the rows above would refuse anything for: a sub-agent's brief as it
        # starts, the name the harness gives it, and a command that failed — the lines the board's Now strip
        # and slice window are drawn from (`session.py record`).
        "PostToolUseFailure": [{"matcher": "Bash",
                                "hooks": [{"type": "command", "command": f"python3 {script} after-failure"}]}],
        "SubagentStart": [{"hooks": [{"type": "command", "command": f"python3 {script} agent-started"}]}],
        "SubagentStop": [{"hooks": [{"type": "command", "command": f"python3 {script} agent-stopped"}]}],
    }


# What the delivery loop runs in every project whatever its language: the toolkit's own scripts — the captain,
# the harbourmaster, the fleet, the projections, the gates — and the Git a slice is made of. A session that
# cannot ask is refused every command its rules do not name, and one refused first command parks a run before
# its first stage: a TypeScript project's first run could not call a single toolkit script, its allowlist
# having no `python3` rule. The headless session is now given the shell wholesale by the
# registry's row (`--allowedTools Bash`), because no list can name the compound commands an agent writes; these
# rules are what keep a person's own session from prompting at every hook and gate, and the deny rules below
# are what hold in both. Resets and cleans are absent, and a plain force-push is denied rather than merely
# unlisted, because `git push *` would otherwise admit it: they destroy work.
# `git push *` itself has to stay, because the ladder's own push after a rebase is the lease-guarded one,
# `git push --force-with-lease=refs/heads/slice/<id>: origin HEAD:...`, which a narrower prefix could not name.
TOOLKIT_PERMISSIONS = [
    "git status",
    "git status *",
    "git rev-parse *",
    "git log",
    "git log *",
    "git diff",
    "git diff *",
    "git show *",
    "git branch",
    "git branch *",
    "git fetch",
    "git fetch *",
    "git pull",
    "git pull *",
    "git checkout *",
    "git switch *",
    "git add *",
    "git commit *",
    "git merge *",
    "git rebase *",
    "git push",
    "git push *",
]
# Denied whatever the allow rules say: a deny rule wins, and a prefix rule cannot say "but not this". A rule is
# a prefix, so these catch the flag where it is written first — `git push --force origin main` — and leave the
# lease-guarded form alone; a `--force` written after the remote is beyond what a prefix can see.
DENIED_PERMISSIONS = [
    "git push --force",
    "git push --force *",
    "git push -f",
    "git push -f *",
    "git reset --hard",
    "git reset --hard *",
    "git clean",
    "git clean *",
]


def claude_settings(apps: list[App], target: str = "none", layout: Layout = AT_ROOT) -> str:
    services = services_of(apps)
    # Every service's toolchain, once each: a slice in any of them runs its commands constantly.
    rules = registry().answer
    native = list(dict.fromkeys(rule for backend in backends_of(apps) for rule in rules(backend, AGENT_PERMISSIONS)))
    # The read-only gates a slice runs constantly. `check-constitution` and its `--requirements`
    # printout change nothing on disk, so approving each invocation buys no safety.
    allowed = [
        "make",
        "make verify",
        "make test",
        "make check-constitution",
        "make constitution-requirements",
        # The toolkit's own scripts, by both the paths they are reached by: the one a session in the root
        # types, and the `$CLAUDE_PROJECT_DIR` one this file's own hooks issue. Under `delivery/` where the
        # method was installed beside an existing codebase — a flat `python3 scripts/*` named nothing there.
        f"python3 {layout.under('scripts')}/*",
        f"python3 $CLAUDE_PROJECT_DIR/{layout.under('scripts')}/*",
    ] + TOOLKIT_PERMISSIONS + native
    # Of the family: whether npm is already approved is a property of the language, not of
    # whichever framework owns startup.
    web = web_apps(apps)
    if web and not any(npm(family) for family in families_of(apps)):
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
    # No extension is named here. An extension that installs an MCP server writes its own entry into the
    # committed `.mcp.json` and into this file, because the keel does not know which extensions a project
    # will elect — the election happens inside the project, at `./init`, after this file was written.
    return json.dumps({"permissions": {"allow": [f"Bash({command})" for command in allowed],
                                       "deny": [f"Bash({command})" for command in DENIED_PERMISSIONS]},
                       "hooks": harness_hooks(layout)}, indent=2) + "\n"


# The region `scripts/agents/project.py` owns in an `import` harness's context file, byte for byte: the
# projector keeps it and this writes it first, so a clone has it before anything has run.
# `tests/test_harness_switch.py` holds the two to one spelling.
IMPORT_REGION = """\
<!-- slipwai:agents-import:begin -->
<!-- Maintained by scripts/agents/project.py. Write repository guidance in AGENTS.md, not here. -->
@AGENTS.md
<!-- slipwai:agents-import:end -->
"""


def context_imports() -> dict[str, str]:
    """Every `import` harness's context file, committed with its `@AGENTS.md` include whatever harness `./init`
    chose: a harness reads nothing of a repository until a file it recognises is there, so a project set up
    under one and opened in another would otherwise start with no rules — and the line that says how to set it
    up is in the file it has not read. Read from the registry, so the keel names no harness here."""
    harnesses = json.loads((TOOLKIT_ROOT / "scripts/agents/registry.json").read_text(encoding="utf-8"))["harnesses"]
    return {str(row["contextFile"]): IMPORT_REGION for row in harnesses
            if row.get("contextMode") == "import" and isinstance(row.get("contextFile"), str)}
