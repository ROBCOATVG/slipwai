#!/usr/bin/env python3
"""`/cruise`'s settings, and the outer loop that re-invokes it with a fresh context until the specs are satisfied.

`.specify/cruise.json` holds how `/cruise` runs `commands/drive.md` with nobody at the wheel — who decides a
product question, how a slice is released, what a demo is driven with, when a run parks. This reads the file
and says what each setting is and controls, checks a hand edit, and changes them through `--set`, refusing
anything the command could not act on. `run` is the loop: one headless harness session per iteration, each a
fresh context, until the last line of an iteration says `done`, a person stops it, or nothing can move. It is
the one thing that continues a run, on every harness: a `/cruise` typed in a session starts it, detached,
with `start`, and the session that typed it runs no stage of the ladder.

    python3 scripts/agents/cruise.py                       # every setting and what it controls
    python3 scripts/agents/cruise.py --check               # well-formed; `make check-agents` runs this
    python3 scripts/agents/cruise.py --set enabled=true    # change settings, checked, any time
    python3 scripts/agents/cruise.py run [--feature F] [--no-park] [--sandbox] [kick-off…]   # the loop; `make cruise`
    python3 scripts/agents/cruise.py start [--feature F] [--no-park] [--sandbox] [kick-off…] # the loop, detached
    python3 scripts/agents/cruise.py watch [--minutes M] [--quiet S]  # the watch seat: the feed since the last watch
    python3 scripts/agents/cruise.py stop [--now]  # end the run after the iteration in flight, or now
    python3 scripts/agents/cruise.py tell [--now] <message…>  # queue a message for the next iteration; --now ends the one in flight
    python3 scripts/agents/cruise.py told        # inside an iteration: what a person queued since it started, or nothing
    python3 scripts/agents/cruise.py status      # whether a runner is running, and what the log says it is doing
    python3 scripts/agents/cruise.py denials     # every command an iteration was refused, from the stream: what to allow
    python3 scripts/agents/cruise.py resume      # print the checkpoint into a compacted context; nothing when none
    python3 scripts/agents/cruise.py compacting  # stamp the checkpoint before the harness compacts
    python3 scripts/agents/cruise.py loop        # what is reading this session's last line: the runner, or nobody
    python3 scripts/agents/cruise.py stopping    # a harness's stop hook: refuse to end a runner's iteration early
    python3 scripts/agents/cruise.py responded   # a harness's after-response hook: keep the last message for `stopping`

`run` marks every session it starts with `CRUISE_RUNNER=1` and `CRUISE_ITERATION=<n>`, which is how `loop` and
`stopping` tell a runner's iteration from a `/cruise` a person typed — where nothing reads the last line, so the
command starts the runner instead of running the ladder itself.

Which harness an iteration runs through is the registry's `headless` column (`scripts/agents/registry.json`):
the first installed harness (`.specify/integration.json`) with a verified headless command whose binary is on
PATH. A harness on PATH that was never initialised here is not used: its commands, delegate types and hook
files are not projected, so an iteration through it would run the ladder with none of them — `/cruise` itself
unknown to it — and the run would spend its stuck budget on that before parking with the wrong reason. An
editor with no command line of its own is paired with a CLI harness by `./init --integration <cli>`, which
Spec Kit installs beside the editor. `CRUISE_HARNESS_COMMAND` (a shell template with `{prompt}`) overrides
all of that, and `CRUISE_POLL_SECONDS` how long a parked loop waits, so a run can be rehearsed against a fake
harness.

A person stops a run with `touch .specify/cruise.stop` (`stop`), or by interrupting a foreground `run`: the
iteration under way is killed, its increment commits are on the slice branch, and the next iteration re-derives
from disk. A person steers a run with `tell`: the message is queued in `.specify/cruise-inbox.jsonl`, and the
next iteration carries it as `told: <message>` in its argument — the route the kick-off takes — so nothing
interrupts the iteration in flight unless `--now` says to, which ends that iteration the way `stop --now` does
and starts the next at once with the message. An iteration can also ask for what was queued since it started
(`told`), between stages, without waiting for its end. Every message delivered is in the iteration's log entry.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json` (see models.py)."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


SCRIPT = Path(__file__).resolve()
ROOT = project_root(SCRIPT, 2)
# The code index's health, freshness and per-delegate use live beside this script, shared with the hooks. No bytecode:
# a `__pycache__/` written beside the scripts is an untracked directory in the project, which `add-service` refuses
# to start over and the run's fingerprint would read as progress.
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPT.parent))
import code_index  # noqa: E402
# The delivery toolkit this script is part of: `commands/`, `scripts/`, `skills/` beside each other, at the root
# or under the delivery directory of an adopted repository.
DELIVERY = SCRIPT.parents[2]
COMMAND = DELIVERY / "commands/cruise.md"
CONFIG = ROOT / ".specify/cruise.json"
STOP = ROOT / ".specify/cruise.stop"
# The runner's own state: its pid while it runs, and where a detached runner writes what a foreground one prints —
# the feed: one line per thing an iteration did, which is what `watch` reads back into a session.
PID = ROOT / ".specify/cruise.pid"
RUN_LOG = ROOT / ".specify/cruise-run.log"
# The harness's own event stream, raw, for a harness that has one: everything the feed was rendered from.
STREAM = ROOT / ".specify/cruise-stream.jsonl"
# The code index `./init --extension codegraph` leaves, and the project MCP file that carries its server: what the
# runner says it can expect of them before the first iteration, rather than a feed that fell back to grep without saying.
CODE_INDEX = ROOT / ".codegraph/codegraph.db"
MCP_CONFIG = ROOT / ".mcp.json"
# How far into the run log the watching session has read.
WATCH_CURSOR = ROOT / ".specify/cruise-watch.cursor"
# The last message a harness's after-response hook saw, for a stop hook whose event does not carry it.
LAST_RESPONSE = ROOT / ".specify/cruise-last-response.txt"
# What a person queued for the run (`tell`), one JSON line per message, until an iteration takes it: the runner
# before it starts one, or the iteration itself between stages (`told`). What was taken waits in the second file
# until the runner writes the iteration's log entry, so every message delivered is on the record whichever took it.
INBOX = ROOT / ".specify/cruise-inbox.jsonl"
TOLD = ROOT / ".specify/cruise-told.jsonl"
LOG = ROOT / "specs/cruise-log.jsonl"
# The iteration in flight, rewritten by `/cruise` at every stage boundary so a compacted context can resume.
CHECKPOINT = ROOT / "specs/cruise-checkpoint.md"
RESUME = ("cruise: this session is a /cruise iteration whose context was compacted. The checkpoint below is what "
          "the summary lost; read it before acting, then commands/cruise.md for the rules it names — run "
          "commands/drive.md as written, decide at its stops by the stop table, end with one of the four last lines.")
# The two variables `run` sets in every session it starts: what tells a runner's iteration from a typed one.
RUNNER_VARIABLE, ITERATION_VARIABLE = "CRUISE_RUNNER", "CRUISE_ITERATION"
# What a session is told when nothing reads its last line — the same words `commands/cruise.md` carries.
UNREAD = ("no outer loop is reading this: a `/cruise` typed in a session starts the runner — `python3 "
          "scripts/agents/cruise.py start` — and then watches it with `python3 scripts/agents/cruise.py watch`; the "
          "runner drives the ladder from here, a fresh session per iteration, and this session runs no stage of it")
# How long one `watch` sits before returning with the iteration still in flight: long enough that a session is
# not re-invoked for nothing, short enough that a person who typed into the session is answered — and under the
# two minutes Claude Code gives a shell command by default, so the harness never cuts the watch off itself.
WATCH_MINUTES = 1.5
# How long the feed has to be quiet, once this watch has shown something new, before it returns with the
# iteration still in flight: a harness shows a command's output when the command returns, so a watch that sat
# its whole budget out would show the feed in ninety-second lumps, and a person watching sees nothing between.
WATCH_QUIET_SECONDS = 20.0
# How many times the Stop hook holds a turn against one checkpoint before it lets go: the command rewrites the
# checkpoint at every stage boundary, so a checkpoint held this often without a rewrite is a session that is
# not moving, and a hook that never let go would spend tokens forever on it.
HOLD_LIMIT = 3
# How long `stop --now` waits for the runner it signalled to be gone before it returns: the runner ends the
# iteration's session first, and a harness session shutting down takes a moment.
STOP_WAIT_SECONDS = 30.0
REGISTRY = SCRIPT.with_name("registry.json")
INTEGRATION = ROOT / ".specify/integration.json"
# What a run may never change to get moving — the gates that judge it and the controls that hold it: `make
# verify`'s scripts and everything beside them, the Makefile that runs them, the tools they run (`tools/`, ignored by
# Git and installed by an extension), CI, and the hook files the harnesses read this script from. A gate is
# satisfied in the tree it measures; an iteration that changed one of these instead has the run parked with the
# change as the reason (`controls_changed` on its log entry), and Claude Code's `PreToolUse` hook (`guard`) refuses
# the edit before it lands. Under `tools/` a file added is an install, which `./init --extension` does; a file
# changed or removed is an edit.
CONTROL_PATHS = (DELIVERY / "Makefile", DELIVERY / "scripts", ROOT / "Makefile", ROOT / "tools",
                 ROOT / ".github/workflows", ROOT / ".gitea/workflows", ROOT / ".claude/settings.json")
INSTALLED = ROOT / "tools"
SKIPPED_DIRECTORIES = {".git", "__pycache__", "node_modules"}
GUARD_REASON = ("cruise: `{path}` is a gate or a control of this run, and an iteration never edits one — a gate is "
                "satisfied in the tree it measures, or the run parks with the gate's own output as the reason "
                "(`cruise: parked: <gate>: <what it said>`). The bosun's brief and commands/cruise.md, *Blocked: the "
                "bosun protocol*, say so; the runner parks the run at the end of an iteration that changed one anyway.")
# Every setting: the values it takes — a tuple of words, or a kind — its default, and what it controls. The
# factory writes the same list into `.specify/cruise.json` and `commands/cruise-settings.md`.
CHOICES: dict[str, tuple[str, ...]] = {
    "enabled": ("true", "false"),
    "decide": ("recommended-first", "skipper-always"),
    "release": ("flagged", "park"),
    "constitution": ("ratify", "park"),
    "hand": ("browser", "http", "cli"),
    "unblock": ("bosun", "park"),
}
# Whole numbers: the least value allowed, and whether `null` is one of the answers.
NUMBERS: dict[str, tuple[int, bool]] = {
    "stuck_after": (1, False), "max_iterations": (1, True), "max_hours": (1, True), "poll_minutes": (1, False),
}
# Free text, or null: the model the iteration itself runs on, passed through the harness row's own `modelFlag`.
TEXTS = ("model",)
DEFAULTS: dict[str, Any] = {
    "enabled": False, "decide": "recommended-first", "release": "flagged", "constitution": "ratify",
    "hand": "browser", "unblock": "bosun", "stuck_after": 3, "max_iterations": None, "max_hours": None,
    "poll_minutes": 10, "model": None,
}
CONTROLS = {
    "enabled": "whether `/cruise` runs at all; `false` is a refusal that says so",
    "decide": "who answers a product question: the host where the stage recommends an answer or a standing "
              "decision covers it and `drive-skipper` otherwise, or `drive-skipper` for every question",
    "release": "the release-constraint stage: every slice continues or opens a flag seeded off, so every merge "
               "is dark; or park at the push and let a person say it is a release they want",
    "constitution": "an unratified constitution: the skipper drafts and ratifies it, marked pending human "
                    "review; or park",
    "hand": "the top of the hand's ladder for a demo; each falls through to the next where it cannot run",
    "unblock": "what a block becomes: work for `drive-bosun` first — a stub, a narrower reading, a repair — parking "
               "only at the catastrophic or when it fails; or a park at once",
    "stuck_after": "iterations with no artifact change before the loop parks",
    "max_iterations": "a budget on iterations; null is unbounded",
    "max_hours": "a budget on wall time; null is unbounded",
    "poll_minutes": "how often a parked loop looks for a reason to resume",
    "model": "the model the iteration itself runs on — the driver, and every stage `.specify/models.json` maps to "
             "`host`; null is the harness's default, which nobody at the wheel chooses",
}
# The one line of an iteration the loop reads, as `commands/cruise.md` spells it.
LAST_LINE = re.compile(r"^cruise: (continue|done|parked: .+|stopped: human)\s*$")
PARKED_EXIT = 3
ABSENT = f"no {CONFIG.relative_to(ROOT)}: /cruise is not enabled here; `slipwai migrate` writes the file"
# The environment a harness session started from inside another harness's session must not inherit: the parent's
# own identity, or the child would read the parent's transcript as its own, and refuse to start as a nested copy.
PARENT_SESSION_VARIABLES = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")
# The iteration under way, so a SIGTERM to the runner ends it too rather than orphaning a harness session.
CURRENT: subprocess.Popen[str] | None = None
# Set by the SIGUSR1 handler (`tell --now`) while an iteration was under way: it was ended for a person's message,
# which the runner says in its log entry instead of reading its missing last line as no progress.
INTERRUPTED = False
# The word an iteration's argument carries a person's message under, beside `unblock:`, as `commands/cruise.md` spells it.
TOLD_WORD = "told:"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def check(table: object) -> list[str]:
    """Everything a hand edit can break, each as one finding."""
    if not isinstance(table, dict):
        return ["the file is not a JSON object"]
    findings = []
    for key, values in CHOICES.items():
        value = table.get(key)
        if key == "enabled":
            if not isinstance(value, bool):
                findings.append(f"`enabled` must be true or false, not {value!r}")
        elif value not in values:
            findings.append(f"`{key}` must be one of {', '.join(values)}, not {value!r}")
    for key, (least, nullable) in NUMBERS.items():
        if key not in table:
            findings.append(f"`{key}` is missing")
            continue
        value = table[key]
        if value is None and nullable:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < least:
            findings.append(f"`{key}` must be a whole number of at least {least}"
                            f"{', or null' if nullable else ''}, not {value!r}")
    for key in TEXTS:
        value = table.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            findings.append(f"`{key}` must be a model identifier or null, not {value!r}")
    return findings


def assign(table: dict[str, Any], assignment: str) -> str:
    """Apply one `key=value` in place and say what changed; `check` decides whether it stands."""
    key, separator, value = assignment.partition("=")
    if not separator or not value or key not in DEFAULTS:
        raise RuntimeError(f"--set takes key=value with a key from {', '.join(DEFAULTS)}, not {assignment!r}")
    if key == "enabled":
        if value not in CHOICES[key]:
            raise RuntimeError(f"`enabled` is true or false, not {value!r}")
        table[key] = value == "true"
    elif key in CHOICES:
        table[key] = value
    elif key in TEXTS:
        table[key] = None if value == "null" else value
    elif value == "null":
        table[key] = None
    else:
        try:
            table[key] = int(value)
        except ValueError:
            raise RuntimeError(f"`{key}` takes a whole number{' or null' if NUMBERS[key][1] else ''}, "
                               f"not {value!r}") from None
    return f"{key} = {json.dumps(table[key])}"


def describe(table: dict[str, Any]) -> str:
    return "\n".join(f"{key}: {json.dumps(table[key])} — {CONTROLS[key]}" for key in DEFAULTS)


def load() -> dict[str, Any]:
    table = json.loads(CONFIG.read_text())
    findings = check(table)
    if findings:
        raise RuntimeError(f"{CONFIG.relative_to(ROOT)}:\n  - " + "\n  - ".join(findings))
    return table


def enabled() -> dict[str, Any]:
    table = load()
    if not table["enabled"]:
        raise RuntimeError("not enabled: `python3 scripts/agents/cruise.py --set enabled=true`, checked, turns it on")
    return table


def registry() -> dict[str, dict[str, Any]]:
    return {row["key"]: row for row in json.loads(REGISTRY.read_text())["harnesses"]}


def installed_keys() -> list[str]:
    """The harnesses Spec Kit recorded as installed here, in the order it recorded them; none where it never ran."""
    if not INTEGRATION.is_file():
        return []
    state = json.loads(INTEGRATION.read_text())
    keys = state.get("installed_integrations") or [state.get("default_integration")]
    return [key for key in keys if isinstance(key, str)]


def headless_row(harness: dict[str, Any]) -> dict[str, Any] | None:
    row = harness.get("headless")
    return row if isinstance(row, dict) else None


def binary_of(harness: dict[str, Any]) -> str:
    """The executable a harness's headless command starts with: what the runner looks for on PATH."""
    row = headless_row(harness)
    assert row is not None
    return shlex.split(str(row["command"]))[0]


def choose_harness() -> tuple[dict[str, Any], str]:
    """The harness an iteration runs through, and a sentence saying why that one.

    The first installed harness with a verified headless command whose binary is on PATH. Nothing else: a
    harness on PATH that `./init` never initialised here has no projected commands, delegate types or hook
    files, so `/cruise` is unknown to it and the ladder's delegates and holds are absent — an iteration through
    it ends with no last line, and the run spends its stuck budget before parking for the wrong reason. So a
    CLI harness that is on PATH but not initialised is named in the refusal, with the `./init` that adds it
    beside whatever is installed, rather than driven.
    """
    rows = registry()
    installed = [key for key in installed_keys() if key in rows]
    for key in installed:
        harness = rows[key]
        if headless_row(harness) is not None and shutil.which(binary_of(harness)):
            return harness, f"harness: {harness['name']}"
    on_path = [harness for key, harness in rows.items()
               if key not in installed and headless_row(harness) is not None and shutil.which(binary_of(harness))]
    able = ", ".join(f"{harness['name']} (`{binary_of(harness)}`)" for harness in rows.values()
                     if headless_row(harness) is not None)
    named = ", ".join(rows[key]["name"] for key in installed) or "no harness is initialised here"
    installed_words = ' is installed' if len(installed) == 1 else ' are installed' if installed else ''
    if installed and headless_row(rows[installed[0]]) is None:
        installed_words += ", and the registry records no way to run it headless"
    elif installed:
        installed_words += f", and `{binary_of(rows[installed[0]])}` is not on PATH"
    if on_path:
        found = ", ".join(f"{harness['name']} (`./init --integration {harness['key']}`)" for harness in on_path)
        raise RuntimeError(f"no initialised harness this loop can run an iteration through is on PATH: {named}"
                           f"{installed_words}. On PATH but never initialised here, so its commands, delegate "
                           f"types and hooks are not projected: {found} — that init adds it beside what is "
                           "installed; then run again. Or set CRUISE_HARNESS_COMMAND to a shell template with "
                           "{prompt}")
    raise RuntimeError(f"no harness this loop can run an iteration through is on PATH: {named}{installed_words}, "
                       "and none of the harnesses the registry records a headless command for is on PATH — "
                       f"{able} (scripts/agents/registry.json, `headless`). Install one of those and "
                       "`./init --integration <key>` it, or set CRUISE_HARNESS_COMMAND to a shell template with "
                       "{prompt}")


def harness_command(harness: dict[str, Any], sandbox: bool) -> tuple[str, str]:
    """The shell template one iteration runs, and the sentence saying which permissions it runs under."""
    override = os.environ.get("CRUISE_HARNESS_COMMAND")
    if override:
        return override, "harness: CRUISE_HARNESS_COMMAND, as given"
    headless = headless_row(harness)
    assert headless is not None
    permissions = headless.get("sandboxPermissions" if sandbox else "permissions", "")
    why = ("--sandbox: every permission check is bypassed, which is only for a container with nothing to lose"
           if sandbox else
           "edits are accepted and every other permission is the harness's own to grant or refuse; pass "
           "--sandbox inside a disposable container to bypass them all")
    template = str(headless["command"]).replace("{permissions}", permissions)
    # A headless session in a checkout nobody has trusted ignores the project's own MCP file on some harnesses, so
    # the row's `headlessFlags` make it honoured — passed only when the file exists, since a flag naming a missing
    # file refuses to start, and `{root}` is this checkout for a harness that trusts by path.
    project = harness.get("projectMcp")
    if isinstance(project, dict) and project.get("headlessFlags") and (ROOT / str(project["file"])).is_file():
        template = f"{template} {str(project['headlessFlags']).replace('{root}', str(ROOT))}"
    # The ladder's concurrent slices work in worktrees beside the checkout (`../<project>-<id>`), which a print
    # session under `acceptEdits` is refused every edit in; the row's `worktreeFlags` name the directory the
    # checkout sits in as a second working directory, so a slice delegate's first edit is not its last.
    worktrees = headless.get("worktreeFlags")
    if worktrees:
        template = f"{template} {str(worktrees).replace('{parent}', shlex.quote(str(ROOT.parent)))}"
    return template, why


def model_flags(harness: dict[str, Any] | None, model: str | None) -> str:
    """What puts the iteration on the model `.specify/cruise.json` names: the harness row's `modelFlag` with the
    identifier in it, appended to the command. Nothing where no model is named, where the template is the
    override's (a person's to write whole), or where the row records no flag — `model_lines` says which."""
    headless = headless_row(harness) if harness is not None else None
    flag = headless.get("modelFlag") if headless is not None else None
    if not model or os.environ.get("CRUISE_HARNESS_COMMAND") or not flag:
        return ""
    return " " + str(flag).replace("{model}", shlex.quote(model))


def model_lines(harness: dict[str, Any] | None, model: str | None) -> list[str]:
    """Said before the first iteration: which model the iteration itself runs on. Under `/drive` a person chose it
    when they opened the session; here nobody did, so the file says, or the harness's default runs and is named
    as such — never left to be inferred from a transcript afterwards."""
    if not model:
        return []
    if os.environ.get("CRUISE_HARNESS_COMMAND"):
        return [f"cruise: `model` is `{model}`, but CRUISE_HARNESS_COMMAND is the template as given; put the flag "
                "in it yourself"]
    flags = model_flags(harness, model).strip()
    if flags:
        return [f"cruise: the iteration itself runs on `{model}` ({flags}); every stage `.specify/models.json` maps "
                "to `host` runs there too"]
    name = str(harness.get("name", "the harness")) if harness is not None else "the harness"
    return [f"cruise: `model` is `{model}`, but the {name} row records no `modelFlag` (scripts/agents/registry.json, "
            "`headless`), so the harness's own default runs; add the flag to the row once its spelling is verified"]


def index_lines(harness: dict[str, Any] | None) -> list[str]:
    """What a run can expect of the code index, said before the first iteration: nothing where none was adopted; the
    route an iteration reaches it by; or that no iteration can, so its text-search answers are read for what they are."""
    if not CODE_INDEX.is_file():
        return []
    cli = "codegraph" if shutil.which("codegraph") else "npx" if shutil.which("npx") else None
    project = harness.get("projectMcp") if harness is not None else None
    name = str(harness.get("name", "the harness")) if harness is not None else "the harness"
    if cli is None:
        return [f"cruise: the code index ({relative(CODE_INDEX.parent)}) is here, but neither `codegraph` nor `npx` is "
                "on PATH: no iteration can reach it, and each is told to say so and use text search — install the "
                "CLI, or Node, before an unattended run"]
    if isinstance(project, dict):
        file = ROOT / str(project["file"])
        if file.is_file():
            passed = (f", and every iteration is started with it ({str(project['headlessFlags']).replace('{root}', '<root>')})"
                      if project.get("headlessFlags") else f", which {name} reads itself")
            return [f"cruise: the code index is reached over MCP — {relative(file)} names the server{passed}"]
        return [f"cruise: the code index ({relative(CODE_INDEX.parent)}) is here, but {relative(file)} does not name "
                f"its server, so an iteration reaches it only through the `{cli}` CLI; `make agents` writes the file "
                "once the extension is adopted (`./init --extension codegraph`)"]
    return [f"cruise: the code index is reached through the `{cli}` CLI; the registry knows no project MCP file for "
            f"{name}"]


def resolve_harness(sandbox: bool) -> tuple[dict[str, Any] | None, str, str]:
    """The harness row (none under the override where nothing is installed), the shell template, and the sentence
    the run starts with. The override is consulted first so a rehearsal against a fake harness needs no CLI."""
    if os.environ.get("CRUISE_HARNESS_COMMAND"):
        rows = registry()
        installed = [key for key in installed_keys() if key in rows]
        harness = rows[installed[0]] if installed else None
        template, why = harness_command(harness or {}, sandbox)
        return harness, template, why
    harness, chosen = choose_harness()
    template, why = harness_command(harness, sandbox)
    return harness, template, f"{chosen}; {why}"


def prompt_for(harness: dict[str, Any] | None, argument: str | None) -> str:
    """What an iteration is asked. A harness whose headless row says its print mode resolves the project's slash
    commands (`prompt: "slash"`) is asked `/cruise`; every other is asked to read the command file and follow
    it, which needs nothing of a harness beyond reading a file — the same words whatever the harness."""
    headless = headless_row(harness) if harness is not None else None
    if headless is not None and headless.get("prompt") == "slash":
        return f"/cruise {argument}" if argument else "/cruise"
    tail = f", with `{argument}` as its argument" if argument else "; it is given no argument"
    return f"Run the /cruise command: read {relative(COMMAND)} and follow it exactly as written{tail}."


def fingerprint() -> str:
    """What the tree looks like to the ladder: the commit, the working tree's state, and every file under specs/."""
    digest = hashlib.sha256()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    digest.update(head.stdout.encode())
    # Untracked files one per line, so the log and the checkpoint can be left out: a directory reported as
    # untracked the moment the log is first written read as progress, once, in every run.
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True,
                            capture_output=True)
    own = tuple(path.relative_to(ROOT).as_posix()
                for path in (LOG, CHECKPOINT, PID, RUN_LOG, STREAM, WATCH_CURSOR, LAST_RESPONSE, INBOX, TOLD))
    digest.update("\n".join(line for line in status.stdout.splitlines() if not line.endswith(own)).encode())
    specs = ROOT / "specs"
    for path in sorted(specs.rglob("*")) if specs.is_dir() else []:
        if path.is_file() and path not in (LOG, CHECKPOINT):
            digest.update(str(path.relative_to(ROOT)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def entries() -> list[dict[str, Any]]:
    if not LOG.is_file():
        return []
    return [json.loads(line) for line in LOG.read_text().splitlines() if line.strip()]


def record(entry: dict[str, Any]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def child_environment(harness: dict[str, Any] | None) -> dict[str, str]:
    """What the iteration runs under: this environment, plus what the registry's `headless.env` sets for the
    harness — Claude Code's wait ceiling, which otherwise ends a print session while its delegates still run —
    and minus the harness's own session variables, so a session started from inside another never reads its
    parent's id as its own, or refuses to start as a nested copy of it."""
    environment = dict(os.environ)
    for variable in PARENT_SESSION_VARIABLES:
        environment.pop(variable, None)
    for row in registry().values():
        session_variable = (row.get("usage") or {}).get("env")
        if session_variable:
            environment.pop(str(session_variable), None)
    headless = headless_row(harness) if harness is not None else None
    if headless is not None and isinstance(headless.get("env"), dict):
        environment.update({str(key): str(value) for key, value in headless["env"].items()})
    return environment


def control_paths() -> list[Path]:
    """Every gate and control the run is held by, present or not: the fixed ones, and the hook file of every harness
    whose registry row projects one."""
    paths = list(CONTROL_PATHS)
    for row in registry().values():
        projection = (row.get("hooks") or {}).get("projection") if isinstance(row.get("hooks"), dict) else None
        if isinstance(projection, dict) and projection.get("where"):
            paths.append(ROOT / str(projection["where"]))
    return list(dict.fromkeys(paths))


def controls_signature() -> dict[str, str]:
    """Every file under the controls by its content, taken before an iteration and compared after it."""
    signature: dict[str, str] = {}
    for control in control_paths():
        if control.is_file():
            files = [control]
        elif control.is_dir():
            files = []
            for directory, names, filenames in os.walk(control):
                names[:] = sorted(name for name in names if name not in SKIPPED_DIRECTORIES)
                files += [Path(directory) / name for name in sorted(filenames)]
        else:
            continue
        for path in files:
            try:
                if path.is_file():
                    signature[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
    return signature


def controls_changed(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """What an iteration did to the controls, each with its kind — except a file installed under `tools/`."""
    installed = INSTALLED.relative_to(ROOT).as_posix() + "/"
    changes = []
    for path in sorted(set(before) | set(after)):
        if path in before and path in after:
            if before[path] != after[path]:
                changes.append(f"{path} (modified)")
        elif path in before:
            changes.append(f"{path} (deleted)")
        elif not path.startswith(installed):
            changes.append(f"{path} (added)")
    return changes


def guard() -> None:
    """Claude Code's `PreToolUse` hook on the editing tools — Edit, Write, MultiEdit, NotebookEdit: in a session the
    runner started, refuse an edit to a gate or a control before it lands, with the reason on stderr and exit 2,
    which is how that harness reads a refusal (a 2.1.281 print session, probed 2026-09-24: the tool result carries
    the reason, the model reads it, the file is not written). Outside a runner's iteration the hook does nothing, so
    a person's `/drive` session edits what it likes. The shell is not covered here — a command can write anything —
    which is why the runner compares the controls after every iteration too."""
    if not os.environ.get(RUNNER_VARIABLE):
        return
    event = read_event()
    given = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    target = given.get("file_path") or given.get("notebook_path")
    if not target:
        return
    path = Path(str(target))
    if not path.is_absolute():
        path = Path(str(event.get("cwd") or ROOT)) / path
    path = path.resolve()
    for control in control_paths():
        if path == control or control in path.parents:
            try:
                shown = path.relative_to(ROOT).as_posix()
            except ValueError:
                shown = str(path)
            print(GUARD_REASON.format(path=shown), file=sys.stderr)
            raise SystemExit(2)


def stream_of(harness: dict[str, Any] | None) -> str | None:
    """Which event stream the harness's headless command emits, for the feed: `CRUISE_HARNESS_STREAM` where set
    (a rehearsal against a fake harness), else the headless row's `stream`, else none — plain text, echoed."""
    override = os.environ.get("CRUISE_HARNESS_STREAM")
    if override is not None:
        return override or None
    headless = headless_row(harness) if harness is not None else None
    stream = headless.get("stream") if headless is not None else None
    return str(stream) if stream else None


def first_line(text: object, width: int = 140) -> str:
    """The first non-empty line of a text, cut to a width the feed stays readable at."""
    line = next((part.strip() for part in str(text or "").splitlines() if part.strip()), "")
    return line if len(line) <= width else line[: width - 1] + "…"


def duration(seconds: float) -> str:
    whole = int(seconds)
    return f"{whole // 60}m{whole % 60:02d}s" if whole >= 60 else f"{whole}s"


class Feed:
    """The feed: a harness's event stream rendered one line per thing the iteration did — a command, a file, a
    delegate out and back, the words the session ended on — for a person reading the run log, and for the
    session watching it through `watch`. A harness with no stream (`stream` absent from its headless row) is
    echoed as it comes. A line the renderer does not understand is passed through, so a harness's own warning
    is never lost. `last` is the iteration's last line, read from the stream's final message where there is
    one and from the text where there is not."""

    def __init__(self, kind: str | None) -> None:
        self.kind = kind
        # A delegate out: its tool-use id, to the label it was announced with and when, for the line it comes back on.
        self.delegates: dict[str, tuple[str, float]] = {}
        self.last: str | None = None

    def render(self, raw: str) -> list[str]:
        text = raw.rstrip("\n")
        if self.kind is None:
            if LAST_LINE.match(text):
                self.last = text.strip()
            return [text]
        try:
            event = json.loads(text)
        except ValueError:
            # Not an event: a harness's own warning, or a harness that spoke plain text after all — the last
            # line is read from it the way it is read from a harness with no stream, so a rehearsal against a
            # fake harness, and a harness whose stream flag stopped working, still end their iterations.
            if LAST_LINE.match(text):
                self.last = text.strip()
            return [text] if text.strip() else []
        if not isinstance(event, dict):
            return [text]
        if self.kind == "claude":
            return self.claude(event)
        if self.kind == "codex":
            return self.codex(event)
        return [text]

    def ended_on(self, text: object) -> None:
        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        if lines and LAST_LINE.match(lines[-1]):
            self.last = lines[-1]

    def claude(self, event: dict[str, Any]) -> list[str]:
        """Claude Code's `--output-format stream-json --verbose`: `assistant` and `user` messages carrying content
        blocks, `parent_tool_use_id` set on a delegate's own, and one `result` at the end with the final text and
        every permission the session was refused (the stream 2.1.280 wrote, read 2026-09-22)."""
        kind = event.get("type")
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        blocks = message.get("content") if isinstance(message.get("content"), list) else []
        indent = "      " if event.get("parent_tool_use_id") else "  "
        lines: list[str] = []
        if kind == "assistant":
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and first_line(block.get("text")):
                    lines.append(f"{indent}· {first_line(block.get('text'))}")
                elif block.get("type") == "tool_use":
                    lines.append(f"{indent}{self.call(block)}")
        elif kind == "user":
            for block in blocks:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    lines += self.outcome(block, indent)
        elif kind == "result":
            text = event.get("result")
            self.ended_on(text)
            for denial in event.get("permission_denials") or []:
                if isinstance(denial, dict):
                    asked = denial.get("tool_input") if isinstance(denial.get("tool_input"), dict) else {}
                    lines.append(f"  denied  {denial.get('tool_name', '?')}  "
                                 f"{first_line(asked.get('command') or json.dumps(asked), 100)}")
            if event.get("is_error"):
                lines.append(f"  error  {first_line(text) or event.get('subtype', '')}")
        return lines

    def call(self, block: dict[str, Any]) -> str:
        name = str(block.get("name", "?"))
        given = block.get("input") if isinstance(block.get("input"), dict) else {}
        if name == "Bash":
            return f"$ {first_line(given.get('command'))}"
        files = {"Read": "read", "Write": "write", "Edit": "edit", "MultiEdit": "edit", "NotebookEdit": "edit"}
        if name in files:
            return f"{files[name]}  {given.get('file_path') or given.get('notebook_path') or ''}"
        if name in ("Agent", "Task"):
            label = f"agent {given.get('subagent_type') or 'delegate'}"
            self.delegates[str(block.get("id", ""))] = (label, time.monotonic())
            return f"{label}  \"{first_line(given.get('description') or given.get('prompt'), 80)}\"  ▶"
        if name == "SubagentHandback":
            return f"report  · {first_line(given.get('message'), 100)}"
        if name == "Skill":
            return f"skill  {given.get('skill', '')}"
        if name in ("Grep", "Glob"):
            return f"search  {given.get('pattern', '')}"
        if name in ("WebFetch", "WebSearch"):
            return f"fetch  {given.get('url') or given.get('query') or ''}"
        if name.startswith("mcp__"):
            server, _, tool = name.removeprefix("mcp__").partition("__")
            return f"{server}.{tool}  {first_line(given.get('query') or json.dumps(given), 100)}"
        return f"{name}  {first_line(json.dumps(given), 100)}"

    def outcome(self, block: dict[str, Any], indent: str) -> list[str]:
        content = block.get("content")
        text = (content if isinstance(content, str)
                else " ".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
                if isinstance(content, list) else "")
        ident = str(block.get("tool_use_id", ""))
        if ident in self.delegates:
            label, started = self.delegates.pop(ident)
            return [f"{indent}{label}  ■ back  {duration(time.monotonic() - started)}"]
        if block.get("is_error"):
            return [f"{indent}  failed  {first_line(text)}"]
        return []

    def codex(self, event: dict[str, Any]) -> list[str]:
        """Codex's `exec --json`: `thread.started`, `turn.*`, and `item.started|updated|completed` with a typed item
        (codex-rs/exec/src/exec_events.rs on main, read 2026-09-22)."""
        kind = str(event.get("type", ""))
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        what = item.get("type")
        if kind == "item.started":
            if what == "command_execution":
                return [f"  $ {first_line(item.get('command'))}"]
            if what == "mcp_tool_call":
                return [f"  {item.get('server', '')}.{item.get('tool', '')}"]
            if what == "collab_tool_call":
                return [f"  agent {item.get('tool', '')}  \"{first_line(item.get('prompt'), 80)}\"  ▶"]
            if what == "web_search":
                return [f"  fetch  {first_line(item.get('query'))}"]
        elif kind == "item.completed":
            if what == "agent_message":
                self.ended_on(item.get("text"))
                return [f"  · {first_line(item.get('text'))}"] if first_line(item.get("text")) else []
            failed = item.get("status") != "completed" or item.get("exit_code") not in (0, None)
            if what == "command_execution" and failed:
                return [f"    {item.get('status', '')}  exit {item.get('exit_code')}  "
                        f"{first_line(item.get('aggregated_output'))}"]
            if what == "file_change":
                return [f"  {change.get('kind', 'change')}  {change.get('path', '')}"
                        for change in item.get("changes") or [] if isinstance(change, dict)]
            if what == "collab_tool_call":
                return [f"  agent {item.get('tool', '')}  ■ back  {item.get('status', '')}"]
            if what == "mcp_tool_call" and item.get("status") == "failed":
                return [f"    failed  {item.get('server', '')}.{item.get('tool', '')}"]
            if what == "error":
                return [f"  error  {first_line(item.get('message'))}"]
        elif kind == "turn.failed":
            error = event.get("error") if isinstance(event.get("error"), dict) else {}
            return [f"  failed  {first_line(error.get('message'))}"]
        elif kind == "error":
            return [f"  error  {first_line(event.get('message'))}"]
        return []


def iterate(template: str, prompt: str, environment: dict[str, str], iteration: int, stream: str | None) -> str | None:
    """Run one iteration, marked as the runner's, rendering what it does into the feed as it happens — the raw
    stream kept beside it — and return its last line."""
    global CURRENT
    command = template.replace("{prompt}", shlex.quote(prompt))
    environment = {**environment, RUNNER_VARIABLE: "1", ITERATION_VARIABLE: str(iteration)}
    feed = Feed(stream)
    raw = STREAM.open("a") if stream else None
    try:
        if raw is not None:
            raw.write(f"# iteration {iteration} {now()}\n")
        # Its own process group, so ending the iteration ends everything the session started — a dev server, a
        # watcher — and not only the shell that started the session.
        with subprocess.Popen(command, shell=True, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, env=environment, start_new_session=True) as process:
            CURRENT = process
            assert process.stdout is not None
            for line in process.stdout:
                if raw is not None:
                    raw.write(line)
                    raw.flush()
                stamp = time.strftime("%H:%M:%S")
                for text in feed.render(line):
                    sys.stdout.write(f"{stamp}  {text}\n")
                sys.stdout.flush()
    finally:
        CURRENT = None
        if raw is not None:
            raw.close()
    # What the session left running — the app its demo started, which the ladder leaves up for a person who
    # is not coming, a watcher — is ended with the iteration, or the next one finds the port taken. The group
    # outlives its leader while any member does, so a signal that lands is the sign something was left — unless
    # the group was ended for a person's message, in which case whatever is still dying was ended on purpose.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    else:
        if not INTERRUPTED:
            sys.stdout.write(f"{time.strftime('%H:%M:%S')}  cruise: iteration {iteration} left a process running — "
                             "a dev server, a watcher — and it was ended with the iteration\n")
            sys.stdout.flush()
    return feed.last


def resume() -> None:
    """What a harness prints back into a compacted context: nothing unless an iteration is in flight."""
    if not CHECKPOINT.is_file():
        return
    print(RESUME)
    print(CHECKPOINT.read_text().rstrip())
    log = entries()
    if log:
        print(f"cruise: the log's last iteration is {log[-1]['iteration']}, ended {log[-1]['ended']} with "
              f"`{log[-1]['last_line']}`")


def compacting() -> None:
    """Stamp the checkpoint before compaction, so the resumed context can see when it lost its memory."""
    if CHECKPOINT.is_file():
        with CHECKPOINT.open("a") as handle:
            handle.write(f"- **Compacted:** {now()}\n")


def loop() -> None:
    """Say what is reading this session's last line, so an iteration knows what its end means."""
    if os.environ.get(RUNNER_VARIABLE):
        print(f"cruise: the outer loop (scripts/agents/cruise.py run) started this session as iteration "
              f"{os.environ.get(ITERATION_VARIABLE, '?')} and reads its last line")
    else:
        print(f"cruise: {UNREAD}")


def last_assistant_text(transcript: Path) -> str | None:
    """The text of the last assistant message in a Claude Code transcript, or None where there is none."""
    text = None
    for line in transcript.read_text(errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") != "assistant":
            continue
        content = (entry.get("message") or {}).get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            texts = [block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text"]
            if texts:
                text = texts[-1]
    return text


def read_event() -> dict[str, Any]:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}
    return event if isinstance(event, dict) else {}


def responded() -> None:
    """A harness's after-response hook, for one whose stop event does not carry the message the turn ends on:
    keep the last assistant message where `stopping` can read it. Cursor's `afterAgentResponse` hands the text
    as `text`; anything else with a `text` or `last_assistant_message` field is kept the same way."""
    if not os.environ.get(RUNNER_VARIABLE):
        return
    event = read_event()
    text = event.get("text") or event.get("last_assistant_message")
    if isinstance(text, str) and text.strip():
        LAST_RESPONSE.parent.mkdir(parents=True, exist_ok=True)
        LAST_RESPONSE.write_text(text)


def ending_message(event: dict[str, Any]) -> str:
    """The message the turn ends on: the event's own copy first — `last_assistant_message` (Claude Code),
    `lastAssistantMessage` (Grok Build), `prompt_response` (Gemini CLI) — then the harness's transcript, then
    what the after-response hook kept, and the empty string where none of those has it."""
    for field in ("last_assistant_message", "lastAssistantMessage", "prompt_response"):
        text = event.get(field)
        if isinstance(text, str) and text.strip():
            return text
    transcript = Path(str(event.get("transcript_path") or ""))
    if transcript.is_file():
        return last_assistant_text(transcript) or ""
    if LAST_RESPONSE.is_file():
        return LAST_RESPONSE.read_text()
    return ""


def stopping() -> None:
    """A harness's stop hook: hold a runner's iteration while it is in flight and this turn is not its end.

    Prose in a command file is not a control — a session ended an iteration after the upstream stages and,
    later, on a report that said "continuing now" — so the end of a turn is checked here, where a harness
    lets a hook refuse it. Only in a session the runner started: a typed `/cruise` runs no iteration, it
    starts the runner, so there is nothing to hold. The hook reads the event on stdin and holds the turn
    when a checkpoint says an iteration is in flight, no stop file says a person ended it, and the message the
    turn ends on does not end on one of the four last lines. A turn that ends on `done` or `stopped` takes the
    checkpoint with it, the way the runner would. Every hold is stamped on the checkpoint, and the hook lets
    go after HOLD_LIMIT holds with no rewrite in between — below every harness's own cap on consecutive
    holds, so it is this script that decides when to let go, and says so.

    The hold is spelled the way the harness reads it: Claude Code's `Stop` takes `{"decision": "block",
    "reason"}`, Cursor's `stop` takes `{"followup_message"}`, which it submits as the next user message. The
    event says which — Cursor's carries `loop_count`, Claude Code's `hook_event_name: "Stop"`.
    """
    if not os.environ.get(RUNNER_VARIABLE) or not CHECKPOINT.is_file() or STOP.is_file():
        return
    event = read_event()
    text = ending_message(event)
    if not text.strip():
        # Nothing says what the turn ended on — an event with no message, no transcript, no after-response
        # hook — so there is nothing to judge, and a hold on no evidence would be a hold on every turn.
        print("cruise: the stop event carries no last message and no hook kept one; not holding", file=sys.stderr)
        return
    last = text.rstrip().splitlines()[-1].strip()
    ended = LAST_LINE.match(last) is not None
    if ended and last in ("cruise: done", "cruise: stopped: human"):
        CHECKPOINT.unlink(missing_ok=True)
        return
    if ended:
        return
    checkpoint = CHECKPOINT.read_text()
    if checkpoint.count("- **Held:**") >= HOLD_LIMIT:
        print(f"cruise: held {HOLD_LIMIT} times against a checkpoint nothing rewrote; letting the turn end",
              file=sys.stderr)
        return
    next_step = next((line.strip() for line in checkpoint.splitlines() if line.strip().startswith("- **Next:**")),
                     "- **Next:** (the checkpoint names no next step; read it and commands/cruise.md)")
    with CHECKPOINT.open("a") as handle:
        handle.write(f"- **Held:** {now()} — {last or 'no last line'!r}\n")
    reason = ("cruise: an iteration is in flight (specs/cruise-checkpoint.md) and this turn did not end on one of "
              "its four last lines. An iteration ends only on `cruise: continue`, `cruise: done`, `cruise: parked: "
              "<why>` or `cruise: stopped: human`; a message that says what it is about to do next is a stop, "
              f"whatever it says. Continue from the checkpoint: {next_step}. A person ends the run with "
              f"`touch {relative(STOP)}`.")
    if "loop_count" in event or str(event.get("hook_event_name", "")) == "stop":
        print(json.dumps({"followup_message": reason}))
    else:
        print(json.dumps({"decision": "block", "reason": reason}))


def park(reason: str, no_park: bool, poll: float, seen: str) -> None:
    """Wait for a person: the stop file ends the run, a change under specs/ or a message resumes it, `--no-park`
    exits 3. The tree is re-read every poll; the stop file and the inbox every second, because a person who typed
    something into a parked run is waiting for it and `poll_minutes` is sized for a tree nobody is touching."""
    print(f"cruise: parked — {reason}")
    if no_park:
        raise SystemExit(PARKED_EXIT)
    print(f"cruise: waiting; `touch {relative(STOP)}` ends the run, a change under specs/, a commit or a message "
          "(`python3 scripts/agents/cruise.py tell …`) resumes it", flush=True)
    while True:
        slept = 0.0
        while slept < poll:
            step = min(1.0, poll - slept)
            time.sleep(step)
            slept += step
            if STOP.is_file():
                print("cruise: stopped by human")
                raise SystemExit(0)
            if INBOX.is_file():
                print("cruise: a person's message; resuming")
                return
        if fingerprint() != seen:
            print("cruise: something changed; resuming")
            return


def running_pid() -> tuple[int, str] | None:
    """The pid and start time of the runner the pid file names, where that process is still alive."""
    if not PID.is_file():
        return None
    words = PID.read_text().split()
    if not words or not words[0].isdigit():
        return None
    pid = int(words[0])
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        pass
    return pid, words[1] if len(words) > 1 else "?"


def terminated(_signal: int, _frame: object) -> None:
    """A SIGTERM to the runner ends the iteration under way with it, so `stop --now` leaves no orphan session —
    and no benchmark entry left open by the session it ended."""
    if CURRENT is not None and CURRENT.poll() is None:
        try:
            os.killpg(CURRENT.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        CURRENT.wait()
    cut_off_brackets("the iteration was ended by `stop --now`")
    raise SystemExit(128 + signal.SIGTERM)


def interrupted(_signal: int, _frame: object) -> None:
    """A SIGUSR1 to the runner (`tell --now`) ends the iteration under way for a person's message, and nothing
    else: the loop goes on, and the next iteration starts at once with the inbox as its argument. Between
    iterations, or parked, there is nothing to end, and the inbox is read within the second anyway."""
    global INTERRUPTED
    if CURRENT is not None and CURRENT.poll() is None:
        INTERRUPTED = True
        try:
            os.killpg(CURRENT.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def queued() -> list[dict[str, Any]]:
    """What a person has queued and no iteration has taken yet, oldest first."""
    if not INBOX.is_file():
        return []
    return [json.loads(line) for line in INBOX.read_text().splitlines() if line.strip()]


def deliver() -> list[str]:
    """Take everything queued, in order, and keep it for the iteration's log entry. The file is moved before it
    is read, so a `tell` landing at this moment goes to a fresh inbox rather than being lost."""
    if not INBOX.is_file():
        return []
    taken = INBOX.with_suffix(".taking")
    try:
        os.replace(INBOX, taken)
    except FileNotFoundError:
        return []
    lines = [line for line in taken.read_text().splitlines() if line.strip()]
    taken.unlink()
    with TOLD.open("a") as handle:
        handle.write("".join(f"{line}\n" for line in lines))
    return [str(json.loads(line)["text"]) for line in lines]


def delivered() -> list[dict[str, Any]]:
    """Every message an iteration was given, by the runner or by `told`, and the file cleared for the next."""
    if not TOLD.is_file():
        return []
    given = [json.loads(line) for line in TOLD.read_text().splitlines() if line.strip()]
    TOLD.unlink()
    return given


def requeue(given: list[dict[str, Any]]) -> None:
    """Put back, ahead of anything queued since, what an iteration was given and never got to act on — one
    ended for a later message, or a run ended under it. A person's word is not spent by an iteration that died."""
    if not given:
        return
    lines = [json.dumps(entry, ensure_ascii=False) for entry in given] + [
        json.dumps(entry, ensure_ascii=False) for entry in queued()]
    INBOX.parent.mkdir(parents=True, exist_ok=True)
    INBOX.write_text("".join(f"{line}\n" for line in lines))


def told_argument(texts: list[str]) -> str:
    """The messages as an iteration's argument: `told: <one>`, or the several in order, each on its own `told:`."""
    return " ".join(f"{TOLD_WORD} {' '.join(text.split())}" for text in texts)


def tell(arguments: list[str]) -> None:
    """Queue a message for the run: the next iteration carries it as `told: <message>` in its argument. With
    `--now` — the first word, on the command line or in the text — the iteration in flight is ended for it and
    the next starts at once. The message is the words given, or standard input when there are none, so a
    command file can hand it over in a quoted heredoc and no quote inside it reaches the shell."""
    # A bare `tell` at a terminal is a person who forgot the message, not one about to type it into a pipe.
    text = " ".join(arguments).strip() if arguments else ("" if sys.stdin.isatty() else sys.stdin.read().strip())
    now_flag = False
    if text == "--now" or text.startswith("--now "):
        now_flag, text = True, text.removeprefix("--now").strip()
    if not text:
        raise RuntimeError("tell takes the message as its words, or on standard input")
    INBOX.parent.mkdir(parents=True, exist_ok=True)
    with INBOX.open("a") as handle:
        handle.write(json.dumps({"at": now(), "text": text, "now": now_flag}, ensure_ascii=False) + "\n")
    waiting = len(queued())
    count = f"{waiting} message(s) queued" if waiting > 1 else "queued"
    running = running_pid()
    if running is None:
        print(f"cruise: {count}; no runner is running here — the first iteration of the next run carries it "
              "(`/cruise` starts one)")
        return
    # A parked runner says so as the last line of its log; a foreground one prints it instead, so there the log
    # entry is the evidence, and it cannot say whether something resumed the run since.
    tail = RUN_LOG.read_text(errors="replace").rstrip().splitlines()[-1:] if RUN_LOG.is_file() else []
    log = entries()
    if tail and tail[-1].startswith("cruise: waiting;"):
        print(f"cruise: {count}; the run is parked and resumes with it within the second")
        return
    if not tail and log and str(log[-1]["last_line"]).startswith("cruise: parked: "):
        print(f"cruise: {count}; the run parked after iteration {log[-1]['iteration']} and resumes with it within "
              "the second — unless something already resumed it, in which case the next iteration carries it")
        return
    if now_flag:
        os.kill(running[0], signal.SIGUSR1)
        print(f"cruise: {count}, and the runner (pid {running[0]}) was told to end the iteration in flight for it; "
              "the next iteration starts at once with the message, and the ended iteration's increment commits "
              "are on its branch")
        return
    print(f"cruise: {count} for the next iteration; the one in flight ends first — the runner (pid {running[0]}) "
          "reads the inbox before each iteration, and the iteration itself between stages. "
          "`python3 scripts/agents/cruise.py tell --now …` would end the one in flight for it")


def told() -> None:
    """Inside an iteration, between stages: what a person queued since the iteration started, one line each,
    taken — so the next iteration is not given it again — and kept for this iteration's log entry."""
    texts = deliver()
    if not texts:
        return
    print(f"cruise: {len(texts)} message(s) from a person since this iteration started; act on each before the "
          "next stage, and write down what must outlive this iteration")
    for text in texts:
        print(f"cruise: {TOLD_WORD} {text}")


def cut_off_brackets(reason: str) -> None:
    """Close what the iteration's session left open in the benchmark records: nothing will `end` it now, and an
    entry left open reads as a stage still running (`scripts/agents/benchmark.py cut-off`). Its lines go to the
    run log like the feed's; a benchmark script that fails here fails nothing else."""
    script = SCRIPT.with_name("benchmark.py")
    if script.is_file():
        subprocess.run([sys.executable, str(script), "cut-off", reason], cwd=ROOT, check=False)
        sys.stdout.flush()


def run_arguments(arguments: list[str]) -> tuple[str | None, str | None, bool, bool]:
    """What `run` and `start` are given: `--feature <feature>`, which scopes every iteration; the kick-off — every
    other word, what a person typed after `/cruise`, which reaches the first iteration of this run and no other,
    because everything after it derives from disk; and the two flags."""
    feature: str | None = None
    words: list[str] = []
    skip = False
    for index, argument in enumerate(arguments):
        if skip:
            skip = False
            continue
        if argument == "--feature":
            feature = arguments[index + 1] if index + 1 < len(arguments) else None
            skip = True
        elif argument not in ("--no-park", "--sandbox"):
            words.append(argument)
    return feature, " ".join(words).strip() or None, "--no-park" in arguments, "--sandbox" in arguments


def run(arguments: list[str]) -> None:
    table = enabled()
    running = running_pid()
    if running is not None and running[0] != os.getpid():
        raise RuntimeError(f"a runner is already running here (pid {running[0]}, since {running[1]}); "
                           f"`python3 scripts/agents/cruise.py status` says where it is")
    feature, kickoff, no_park, sandbox = run_arguments(arguments)
    harness, template, why = resolve_harness(sandbox)
    environment = child_environment(harness)
    prompt = prompt_for(harness, feature)
    first = prompt_for(harness, " ".join(part for part in (feature, kickoff) if part))
    PID.parent.mkdir(parents=True, exist_ok=True)
    PID.write_text(f"{os.getpid()} {now()}\n")
    # What a run that ended under an iteration — `stop --now`, a killed runner — had given it is not spent.
    requeue(delivered())
    signal.signal(signal.SIGTERM, terminated)
    signal.signal(signal.SIGUSR1, interrupted)
    try:
        drive(table, harness, template, why, environment, prompt, first, feature, kickoff, no_park)
    finally:
        if PID.is_file() and PID.read_text().split()[:1] == [str(os.getpid())]:
            PID.unlink()


def settings_now(table: dict[str, Any]) -> dict[str, Any]:
    """The settings as they are at this iteration, not as they were when the run started: `/cruise-settings`
    promises a change takes effect at the next iteration, and the budgets, the stuck window, the poll and
    `unblock` are the runner's to honour. A file a hand edit broke keeps the last good table, and says so."""
    try:
        return load()
    except (RuntimeError, ValueError, OSError) as error:
        print(f"cruise: {error}; keeping the settings the last iteration ran under", flush=True)
        return table


def drive(table: dict[str, Any], harness: dict[str, Any] | None, template: str, why: str,
          environment: dict[str, str], prompt: str, first: str, feature: str | None, kickoff: str | None,
          no_park: bool) -> None:
    print(f"cruise: {why}")
    if first != prompt:
        print(f"cruise: the first iteration runs `{first}`, the kick-off; every later one runs `{prompt}`")
    print(f"cruise: each iteration runs `{prompt}` in a fresh session; `touch {relative(STOP)}` stops it")
    for line in model_lines(harness, table["model"]) + index_lines(harness):
        print(line)
    sys.stdout.flush()
    stream = stream_of(harness)
    started_run = time.monotonic()
    iterations_this_run = 0
    # An iteration a person ended for a message is not the run failing to move, so it is not in the stuck window.
    fingerprints = [entry["fingerprint"] for entry in entries() if not entry.get("interrupted")]
    # The fingerprint a stuck run was already given its one unblocking iteration at, so it gets exactly one.
    unblocked_at: str | None = None
    ask, attempt = first, "kick-off" if first != prompt else None
    global INTERRUPTED
    while True:
        table = settings_now(table)
        poll = float(os.environ.get("CRUISE_POLL_SECONDS", table["poll_minutes"] * 60))
        if STOP.is_file():
            print("cruise: stopped by human")
            return
        if not table["enabled"]:
            print("cruise: `enabled` is now false (/cruise-settings); the run ends here, and /cruise refuses to "
                  "start until it is true again")
            return
        if table["max_iterations"] is not None and iterations_this_run >= table["max_iterations"]:
            print(f"cruise: budget spent — {table['max_iterations']} iteration(s)")
            return
        if table["max_hours"] is not None and time.monotonic() - started_run >= table["max_hours"] * 3600:
            print(f"cruise: budget spent — {table['max_hours']} hour(s)")
            return
        # A person's message rides on this iteration's argument: after the kick-off on the first, in place of
        # the bosun's `unblock:` — a person's word is the likelier thing to move a stuck run, and the bosun's one
        # iteration is kept for after it — and alone on any other.
        messages = deliver()
        if messages:
            if attempt == "unblock":
                unblocked_at, attempt = None, None
            ask = prompt_for(harness, " ".join(part for part in (
                feature, kickoff if attempt == "kick-off" else None, told_argument(messages)) if part))
            print(f"cruise: iteration {len(entries()) + 1} carries {len(messages)} message(s) from a person", flush=True)
        iteration = len(entries()) + 1
        # The index an iteration starts against is the runner's to make sound, not the iteration's: a corrupt one is
        # moved aside and rebuilt, a stale one synced, and the entry says which — before the clock starts.
        index = code_index.health()
        if index:
            print(f"cruise: code index before iteration {iteration} — {index['state']}: {index['detail']} "
                  f"({index['seconds']}s)", flush=True)
        started = now()
        LAST_RESPONSE.unlink(missing_ok=True)
        INTERRUPTED = False
        print(f"cruise: iteration {iteration} started {started}, running `{ask}`", flush=True)
        began = time.monotonic()
        controls_before = controls_signature()
        # The model flag is read with the settings, so `/cruise-settings model=…` holds from the next iteration.
        last = iterate(template + model_flags(harness, table["model"]), ask, environment, iteration, stream)
        if INTERRUPTED:
            last = "interrupted: a person's message"
            cut_off_brackets("the iteration was ended by `tell --now`")
        else:
            cut_off_brackets(f"iteration {iteration} ended with the entry open")
        iterations_this_run += 1
        seen = fingerprint()
        if not INTERRUPTED:
            fingerprints.append(seen)
        entry: dict[str, Any] = {"iteration": iteration, "started": started, "ended": now(),
                                 "harness": harness["key"] if harness is not None else "override",
                                 "last_line": last or "no last line", "fingerprint": seen}
        if attempt is not None:
            entry["attempt"] = attempt
        if index:
            entry["index"] = index
        use = code_index.delegate_use(STREAM, iteration).get(iteration) if index and stream else None
        if use:
            entry["index_use"] = use
            for line in code_index.use_lines(iteration, use):
                print(line, flush=True)
        changed = controls_changed(controls_before, controls_signature())
        if changed:
            entry["controls_changed"] = changed
        given = delivered()
        if given:
            entry["told"] = [str(each["text"]) for each in given]
        if INTERRUPTED:
            # The entry says what the iteration was given; the next is given it again, ahead of the message that
            # ended this one, since nothing says this one acted on it.
            entry["interrupted"] = True
            requeue(given)
        ask, attempt = prompt, None
        record(entry)
        # The boundary `watch` returns on: the iteration, what it ended on, and how long it took.
        print(f"cruise: iteration {iteration} ended — {last or 'no last line'} ({duration(time.monotonic() - began)})",
              flush=True)
        if changed:
            # A gate made to pass is no pass, whatever the last line says: the run parks on the change itself, and a
            # person reverts it, or keeps it on purpose and resumes with a message.
            park(f"iteration {iteration} changed a gate or a control of the run — {', '.join(changed)} — and a gate "
                 "is satisfied in the tree it measures, never edited; revert the change, or keep it on purpose and "
                 "resume with a message", no_park, poll, seen)
            continue
        if INTERRUPTED:
            # Ended for a message, not by its own last line: the next iteration is where the message goes, and it
            # starts now — there is nothing to park on and nothing to count.
            continue
        if last in ("cruise: done", "cruise: stopped: human"):
            # The iteration is over for good; a checkpoint left behind would read as state to resume.
            CHECKPOINT.unlink(missing_ok=True)
            print("cruise: done — every specification is satisfied" if last == "cruise: done"
                  else "cruise: stopped by human")
            return
        if last is not None and last.startswith("cruise: parked: "):
            park(last.removeprefix("cruise: parked: "), no_park, poll, seen)
            continue
        window = fingerprints[-table["stuck_after"]:]
        if len(window) == table["stuck_after"] and len(set(window)) == 1:
            since = iteration - table["stuck_after"] + 1
            if table["unblock"] == "bosun" and unblocked_at != seen:
                # One iteration for the bosun to move it, said in the prompt so the command goes straight there.
                unblocked_at = seen
                ask = prompt_for(harness, f"{feature + ' ' if feature else ''}unblock: no progress since iteration {since}")
                attempt = "unblock"
                print(f"cruise: no progress since iteration {since}; one iteration to unblock, then park")
                continue
            park(f"no progress since iteration {since}, and the bosun's iteration did not move it"
                 if unblocked_at == seen else f"no progress since iteration {since}", no_park, poll, seen)


def start(arguments: list[str]) -> None:
    """The loop, detached from the session that asked for it: what a typed `/cruise` does instead of running
    the ladder in a context nothing re-invokes. Everything that can refuse — the settings, the stop file, a
    runner already running, no harness to run through — is checked here, before the fork, so the refusal is
    read by whoever typed it; the runner's own output goes to the run log."""
    table = enabled()
    if os.environ.get(RUNNER_VARIABLE):
        raise RuntimeError(f"this session is iteration {os.environ.get(ITERATION_VARIABLE, '?')} of a run already "
                           "under way; the runner that started it re-invokes /cruise, nothing here has to")
    running = running_pid()
    if running is not None:
        print(f"cruise: the runner is already running (pid {running[0]}, since {running[1]}); its log is "
              f"{relative(RUN_LOG)}, and `python3 scripts/agents/cruise.py status` says where it is")
        print(f"cruise: watch it from here with `python3 scripts/agents/cruise.py watch`{WATCH_TAIL}")
        return
    if STOP.is_file():
        raise RuntimeError(f"{relative(STOP)} is present: a person ended the last run, and the runner would end "
                           "again at once; remove the file to start another")
    feature, kickoff, _no_park, sandbox = run_arguments(arguments)
    harness, _template, why = resolve_harness(sandbox)
    prompt = prompt_for(harness, feature)
    first = prompt_for(harness, " ".join(part for part in (feature, kickoff) if part))
    # Said before the fork, so a runner that ends at once has still said what its iterations run on and how they
    # reach the index.
    for line in model_lines(harness, table["model"]) + index_lines(harness) + queued_lines():
        print(line)
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    # The watch seat starts reading here, so the first `watch` shows this run from its first line.
    WATCH_CURSOR.write_text(str(RUN_LOG.stat().st_size if RUN_LOG.is_file() else 0))
    with RUN_LOG.open("ab") as log:
        log.write(f"cruise: runner started {now()} from a session, detached\n".encode())
        process = subprocess.Popen([sys.executable, str(SCRIPT), "run", *arguments], cwd=ROOT,
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True, env=dict(os.environ))
    # The runner writes its pid file as it starts; wait for that, so `status` typed a moment later sees it —
    # and so a runner that refused after all is reported here, with its reason, rather than found in the log.
    for _ in range(100):
        if process.poll() is not None:
            tail = RUN_LOG.read_text().rstrip().splitlines()[-3:] if RUN_LOG.is_file() else []
            if process.returncode == 0:
                # A run with nothing left to do ends inside this wait: done, stopped, or a budget already spent.
                print(f"cruise: the runner started and already ended ({why}); {relative(RUN_LOG)} says: "
                      + " | ".join(tail))
                return
            raise RuntimeError(f"the runner ended at once (exit {process.returncode}); {relative(RUN_LOG)} says: "
                               + " | ".join(tail))
        words = PID.read_text().split() if PID.is_file() else []
        if words[:1] == [str(process.pid)]:
            break
        time.sleep(0.05)
    print(f"cruise: runner started as pid {process.pid}, detached from this session ({why})")
    if first != prompt:
        print(f"cruise: the first iteration runs `{first}`, the kick-off; every later one runs `{prompt}`, and "
              "derives from disk — what the kick-off says that must outlive it, the first iteration writes down")
    print(f"cruise: each iteration runs `{prompt}` in a fresh session; this session runs no stage of it")
    print(f"cruise: it writes to {relative(RUN_LOG)}; `python3 scripts/agents/cruise.py status` says where it is; "
          f"`touch {relative(STOP)}` ends it after the iteration in flight, `python3 scripts/agents/cruise.py stop "
          "--now` ends it now")
    print(f"cruise: watch it from here with `python3 scripts/agents/cruise.py watch`{WATCH_TAIL}")


# What `start` says about the watch seat, and `watch` repeats when the run continues.
WATCH_TAIL = (": it prints what the iteration does as it happens and returns at the iteration's end, a park, the "
              f"run's end, once the feed has been quiet for {WATCH_QUIET_SECONDS:g} seconds, or after "
              f"{WATCH_MINUTES:g} minutes with nothing new — its last line says which, and whether to watch again")


def watch_position() -> int:
    """Where the watch seat reads the run log from: the cursor the last `watch` (or `start`) left, or — with no
    cursor, or a log shorter than it — the start of the last run, so a first watch is not the whole history."""
    size = RUN_LOG.stat().st_size if RUN_LOG.is_file() else 0
    if WATCH_CURSOR.is_file():
        cursor = WATCH_CURSOR.read_text().strip()
        if cursor.isdigit() and int(cursor) <= size:
            return int(cursor)
    data = RUN_LOG.read_bytes() if RUN_LOG.is_file() else b""
    marker = data.rfind(b"cruise: runner started")
    return 0 if marker < 0 else data.rfind(b"\n", 0, marker) + 1


def boundary(line: str) -> tuple[str, str] | None:
    """What a runner's line means to the watch seat: the iteration ended and on what, the run ended, a park —
    or nothing it returns on."""
    ended = re.match(r"^cruise: iteration \d+ ended — (.*) \([0-9ms]+\)$", line)
    if ended:
        last = ended.group(1)
        if last in ("cruise: done", "cruise: stopped: human"):
            return "ended", line
        if last.startswith("cruise: parked: "):
            return "parked", last.removeprefix("cruise: parked: ")
        return "continue", line
    if line.startswith("cruise: parked — "):
        return "parked", line.removeprefix("cruise: parked — ")
    if line.startswith(("cruise: done — ", "cruise: stopped by human", "cruise: budget spent — ")):
        return "ended", line
    return None


def watch(arguments: list[str]) -> None:
    """The watch seat: what the session that typed `/cruise` runs after `start`, and again after each return.

    Prints the feed as the runner writes it, from where the last `watch` left off, and returns at the next
    boundary — the iteration's end, a park, the run's end, no runner running — or, with the iteration still in
    flight, once it has shown something new and the feed has been quiet for `--quiet` seconds, or after
    `--minutes` with nothing new at all. A harness shows a command's output when the command returns, so
    returning on quiet is what puts the feed in front of a person as it happens, and returning on the budget
    is what answers a person who typed into the watching session. The last line says which, and whether to
    watch again. Watching is only ever reading: the runner needs nothing from the session, and ending the
    watch ends nothing else."""
    minutes = float(arguments[arguments.index("--minutes") + 1]) if "--minutes" in arguments else WATCH_MINUTES
    quiet = float(arguments[arguments.index("--quiet") + 1]) if "--quiet" in arguments else WATCH_QUIET_SECONDS
    tick = float(os.environ.get("CRUISE_WATCH_TICK", "0.5"))
    deadline = time.monotonic() + minutes * 60
    position = watch_position()
    verdict: tuple[str, str] | None = None
    shown_at: float | None = None
    while verdict is None:
        chunk = b""
        if RUN_LOG.is_file():
            with RUN_LOG.open("rb") as log:
                log.seek(position)
                chunk = log.read()
        # Whole lines only: a line the runner is still writing waits for the next pass. Past a boundary, the
        # runner's own lines about it are still this watch's — the reason it parked, how the run ended — and
        # the next iteration's first line is the next watch's, so the cursor stops in front of it.
        cut = chunk.rfind(b"\n") + 1
        for raw in chunk[:cut].splitlines(keepends=True):
            line = raw.decode(errors="replace").rstrip("\n")
            if verdict is not None and line.startswith("cruise: iteration ") and " started " in line:
                break
            print(line)
            position += len(raw)
            verdict = boundary(line) or verdict
        if cut:
            WATCH_CURSOR.write_text(str(position))
            sys.stdout.flush()
            shown_at = time.monotonic()
            if verdict is not None:
                break
        if running_pid() is None:
            verdict = ("gone", "")
        elif shown_at is not None and time.monotonic() - shown_at >= quiet:
            verdict = ("quiet", "")
        elif time.monotonic() >= deadline:
            verdict = ("time", "")
        elif not cut and RUN_LOG.is_file():
            # Nothing new and a runner alive: a run parked before this watch began is still parked, and the
            # seat should say so now rather than sit the whole budget out on a log that will not move.
            tail = RUN_LOG.read_text(errors="replace").rstrip().splitlines()[-2:]
            if tail and tail[-1].startswith("cruise: waiting;"):
                parked = next((boundary(line) for line in tail if line.startswith("cruise: parked — ")), None)
                verdict = parked or ("parked", "see the log")
        if verdict is None:
            time.sleep(tick)
    kind, detail = verdict
    if kind == "continue":
        print("cruise: watch: the run continues — watch again with `python3 scripts/agents/cruise.py watch`; the "
              "runner needs nothing from this session")
    elif kind == "parked":
        print(f"cruise: watch: parked — {detail}. The runner waits: a change under specs/ or a commit resumes it, "
              f"`touch {relative(STOP)}` ends it; nothing to watch until then")
    elif kind == "ended":
        print(f"cruise: watch: the run ended — {detail}; nothing to watch")
    elif kind == "gone":
        print("cruise: watch: no runner is running; nothing to watch (`python3 scripts/agents/cruise.py status` "
              "says what the log shows)")
    elif kind == "quiet":
        print("cruise: watch: the iteration is in flight and the feed went quiet — watch again with `python3 "
              "scripts/agents/cruise.py watch` to keep watching")
    else:
        print(f"cruise: watch: an iteration is still in flight with nothing new for {minutes:g} minutes — watch "
              "again with `python3 scripts/agents/cruise.py watch` to keep watching")


def stop(arguments: list[str]) -> None:
    """End the run: the stop file ends it after the iteration in flight, `--now` ends the iteration too."""
    STOP.parent.mkdir(parents=True, exist_ok=True)
    STOP.touch()
    running = running_pid()
    if running is None:
        print(f"cruise: {relative(STOP)} written; no runner is running here, and /cruise refuses to start until "
              "the file is removed")
        return
    if "--now" in arguments:
        os.kill(running[0], signal.SIGTERM)
        # Said once it has ended, not once it was told to. The runner ends the iteration's session before it goes,
        # and a `start` typed the moment this returned found the old runner still alive and declined to start one
        # — after which nobody was running, and the watch seat found nobody to watch.
        for _ in range(int(STOP_WAIT_SECONDS / 0.05)):
            if running_pid() is None:
                break
            time.sleep(0.05)
        else:
            print(f"cruise: {relative(STOP)} written and the runner (pid {running[0]}) told to end; it is still ending "
                  f"the iteration in flight after {STOP_WAIT_SECONDS:g}s — `python3 scripts/agents/cruise.py status` "
                  "says when it has gone")
            return
        print(f"cruise: {relative(STOP)} written and the runner (pid {running[0]}) terminated with the iteration "
              "in flight; its increment commits are on the slice branch, and the next run re-derives from disk")
        return
    print(f"cruise: {relative(STOP)} written; the runner (pid {running[0]}) ends after the iteration in flight, "
          "and /cruise refuses to start until the file is removed")


def refusals() -> dict[tuple[str, str], list[int]]:
    """Every permission an iteration was refused, read from the raw stream: the tool and what it was asked, to the
    iterations it happened in. Claude Code lists them on its `result` event; Codex marks a declined command."""
    found: dict[tuple[str, str], list[int]] = {}
    if not STREAM.is_file():
        return found
    iteration = 0
    for line in STREAM.read_text(errors="replace").splitlines():
        if line.startswith("# iteration "):
            iteration = int(line.split()[2])
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        for denial in event.get("permission_denials") or []:
            if isinstance(denial, dict):
                asked = denial.get("tool_input") if isinstance(denial.get("tool_input"), dict) else {}
                what = first_line(asked.get("command") or asked.get("file_path") or json.dumps(asked), 100)
                found.setdefault((str(denial.get("tool_name", "?")), what), []).append(iteration)
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        if item.get("type") == "command_execution" and item.get("status") == "declined":
            found.setdefault(("command", first_line(item.get("command"), 100)), []).append(iteration)
    return found


def index_queries() -> dict[int, int]:
    """How many times each iteration in the stream asked the code index — an MCP tool of the codegraph server, or a
    query subcommand of the CLI through the shell; never `sync`, `init` or `serve`, which maintain it — so `status`
    can say whether the index was used rather than only kept fresh. Summed over the host and every delegate."""
    return {iteration: sum(agent["queries"] for agent in agents)
            for iteration, agents in code_index.delegate_use(STREAM).items()}


def index_use_lines() -> list[str]:
    """`status`'s account of the index: in how many of the stream's iterations it was asked, and — when never — that
    every answer was a text search, which AGENTS.md's block asks each iteration to say and nothing else checks."""
    if not CODE_INDEX.is_file():
        return []
    asked = index_queries()
    if not asked:
        return []
    used = sum(1 for count in asked.values() if count)
    if used:
        return [f"cruise: the code index was asked in {used} of {len(asked)} iteration(s) the stream holds "
                f"({sum(asked.values())} quer{'y' if sum(asked.values()) == 1 else 'ies'})"]
    return [f"cruise: the code index was never asked in the {len(asked)} iteration(s) the stream holds — every answer "
            "about callers and blast radius was a text search; `python3 scripts/agents/cruise.py denials` says whether "
            "it was refused, and `start` says whether it can be reached at all"]


def delegate_lines(last: int = 5) -> list[str]:
    """`status`'s per-delegate account of the last few iterations the stream holds: each agent's queries, and each
    that searched the source for a symbol before asking the index."""
    if not CODE_INDEX.is_file():
        return []
    used = code_index.delegate_use(STREAM)
    lines: list[str] = []
    for iteration in sorted(used)[-last:]:
        lines += code_index.use_lines(iteration, used[iteration])
    return lines


def denials() -> None:
    """What a run needed that its permissions did not allow — the list to read after a run, before widening
    anything, because the tools a build needs are measured from a build and not guessed at."""
    found = refusals()
    if not STREAM.is_file():
        print("cruise: no stream kept here — a harness with no event stream reports no refusals; the run log may")
        return
    if not found:
        print("cruise: no permission was refused in the iterations the stream holds")
        return
    print(f"cruise: {sum(len(its) for its in found.values())} refusal(s), {len(found)} distinct — each is a tool the "
          "harness's row does not allow, or a settings rule denies; a deny rule that fired is doing its job")
    for (tool, what), its in sorted(found.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        where = sorted(set(its))
        print(f"  {len(its):>3}×  {tool}  {what}  (iteration{'s' if len(where) > 1 else ''} "
              f"{', '.join(str(each) for each in where)})")


def queued_lines() -> list[str]:
    """What `status` and `start` say of the inbox: each message waiting for the next iteration, or nothing."""
    waiting = queued()
    if not waiting:
        return []
    return [f"cruise: {len(waiting)} message(s) queued for the next iteration ({relative(INBOX)}):"] + [
        f"cruise:   {first_line(entry['text'])}" + (" (asked to end the iteration in flight)" if entry.get("now") else "")
        for entry in waiting
    ]


def status() -> None:
    running = running_pid()
    if running is not None:
        print(f"cruise: the runner is running (pid {running[0]}, since {running[1]}); its log is {relative(RUN_LOG)}")
    else:
        print("cruise: no runner is running here")
    for line in queued_lines():
        print(line)
    log = entries()
    if not log:
        print("cruise: no iteration has run here")
        if CHECKPOINT.is_file():
            print(f"cruise: {CHECKPOINT.relative_to(ROOT)} is present — an iteration is in flight in a session "
                  "that has not ended yet")
        return
    last = log[-1]
    print(f"cruise: {len(log)} iteration(s) logged; the last ended {last['ended']} with `{last['last_line']}`")
    if str(last["last_line"]).startswith("cruise: parked: "):
        print(f"cruise: parked — {str(last['last_line']).removeprefix('cruise: parked: ')}")
    if STOP.is_file():
        print(f"cruise: {STOP.relative_to(ROOT)} is present; remove it before the next run")
    if CHECKPOINT.is_file():
        print(f"cruise: {CHECKPOINT.relative_to(ROOT)} is present — an iteration is in flight, or ended without "
              "`done`; the next iteration reads it as a lead")
    found = refusals()
    if found:
        print(f"cruise: {sum(len(its) for its in found.values())} permission refusal(s) in the stream; "
              "`python3 scripts/agents/cruise.py denials` lists them")
    for line in index_use_lines() + delegate_lines():
        print(line)


def checkpoint_fields() -> dict[str, str]:
    """The checkpoint's labelled fields — Feature, Slice, Stage, Written, Delegates out, Open question, Next — as
    the command writes them (`CHECKPOINT_ENTRY`), or nothing where no checkpoint is written."""
    if not CHECKPOINT.is_file():
        return {}
    fields: dict[str, str] = {}
    label: str | None = None
    for line in CHECKPOINT.read_text().splitlines():
        found = re.findall(r"\*\*([A-Za-z ]+):\*\* (.*?)(?= · \*\*|$)", line)
        if found:
            for label, value in found:
                fields[label] = value.strip()
        elif label is not None and line.startswith("  ") and label in ("Delegates out", "Open question", "Next"):
            fields[label] = f"{fields[label]} {line.strip()}"
    return fields


def where() -> None:
    """Where a run stands, for `/where-are-we` and `/whats-next` typed beside it — and nothing at all where no runner
    is running, so that both commands answer exactly as they do without `/cruise`. With a runner alive: the run,
    the iteration in flight or the park it waits in, the checkpoint's slice, stage and next step, and what a
    person can do from here, which is never to run a stage themselves."""
    running = running_pid()
    if running is None:
        return
    log = entries()
    tail = RUN_LOG.read_text(errors="replace").rstrip().splitlines()[-2:] if RUN_LOG.is_file() else []
    parked = next((line.removeprefix("cruise: parked — ") for line in tail if line.startswith("cruise: parked — ")),
                  None) if tail and tail[-1].startswith("cruise: waiting;") else None
    print(f"cruise: a run is going here — runner pid {running[0]} since {running[1]}, {len(log)} iteration(s) logged, "
          + (f"parked after iteration {len(log)}" if parked else f"iteration {len(log) + 1} in flight"))
    fields = checkpoint_fields()
    if fields:
        print(f"cruise: feature {fields.get('Feature', '?')} · slice {fields.get('Slice', '?')} · stage "
              f"{fields.get('Stage', '?')} · checkpoint written {fields.get('Written', '?')}")
        for label in ("Open question", "Delegates out"):
            if fields.get(label) and fields[label].lower() != "none":
                print(f"cruise: {label.lower()} — {fields[label]}")
        print(f"cruise: next — {fields.get('Next', '(the checkpoint names no next step)')}")
    else:
        print("cruise: no checkpoint written yet — the iteration has not reached its first stage boundary")
    if parked:
        print(f"cruise: parked — {parked}")
        print("cruise: nothing to run from here — a person provides what the park names; `/cruise-tell` with it resumes "
              "the run, `/cruise-stop` ends it")
    else:
        print("cruise: nothing to run from here — the runner is on it; `/cruise` watches it, `/cruise-tell` steers it, "
              "`/cruise-stop` ends it")


def main() -> None:
    arguments = sys.argv[1:]
    if arguments[:1] == ["where"]:
        # Before the settings check: a project with no `/cruise` settings has no run, and the commands that ask
        # this read silence as "answer as without /cruise".
        where()
        return
    if not CONFIG.is_file():
        print(ABSENT)
        return
    verbs = {"run": lambda: run(arguments[1:]), "start": lambda: start(arguments[1:]),
             "watch": lambda: watch(arguments[1:]), "stop": lambda: stop(arguments[1:]), "status": status,
             "tell": lambda: tell(arguments[1:]), "told": told,
             "denials": denials, "resume": resume, "compacting": compacting, "loop": loop, "stopping": stopping,
             "responded": responded, "guard": guard}
    if arguments and arguments[0] in verbs:
        verbs[arguments[0]]()
        return
    if "--set" in arguments:
        table = json.loads(CONFIG.read_text())
        assignments = arguments[arguments.index("--set") + 1:]
        if not assignments:
            raise RuntimeError(f"--set takes key=value with a key from {', '.join(DEFAULTS)}")
        changed = [assign(table, assignment) for assignment in assignments]
        findings = check(table)
        if findings:
            raise RuntimeError("not written — the change would leave the file malformed:\n  - " + "\n  - ".join(findings))
        CONFIG.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n")
        for line in changed:
            print(line)
        print(f"{CONFIG.relative_to(ROOT)} written; it takes effect at the next iteration /cruise runs. "
              "Commit it: the choice is versioned with the project.")
        return
    table = load()
    if "--check" in arguments:
        state = "enabled" if table["enabled"] else "not enabled"
        print(f"check-cruise: {CONFIG.relative_to(ROOT)} is well-formed; /cruise is {state}")
        return
    print(describe(table))
    if shutil.which("git") is None:
        print("note: git is not on PATH; `run` needs it for the artifact fingerprint")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"cruise: {error}", file=sys.stderr)
        raise SystemExit(1) from None
