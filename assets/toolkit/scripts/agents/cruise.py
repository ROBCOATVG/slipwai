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
    python3 scripts/agents/cruise.py run [--feature F] [--no-park] [--sandbox]   # the loop; `make cruise`
    python3 scripts/agents/cruise.py start [--feature F] [--no-park] [--sandbox] # the loop, detached from this session
    python3 scripts/agents/cruise.py stop [--now]  # end the run after the iteration in flight, or now
    python3 scripts/agents/cruise.py status      # whether a runner is running, and what the log says it is doing
    python3 scripts/agents/cruise.py resume      # print the checkpoint into a compacted context; nothing when none
    python3 scripts/agents/cruise.py compacting  # stamp the checkpoint before the harness compacts
    python3 scripts/agents/cruise.py loop        # what is reading this session's last line: the runner, or nobody
    python3 scripts/agents/cruise.py stopping    # a harness's stop hook: refuse to end a runner's iteration early
    python3 scripts/agents/cruise.py responded   # a harness's after-response hook: keep the last message for `stopping`

`run` marks every session it starts with `CRUISE_RUNNER=1` and `CRUISE_ITERATION=<n>`, which is how `loop` and
`stopping` tell a runner's iteration from a `/cruise` a person typed — where nothing reads the last line, so the
command starts the runner instead of running the ladder itself.

Which harness an iteration runs through is the registry's `headless` column (`scripts/agents/registry.json`):
the first installed harness with a verified headless command whose binary is on PATH, else any harness in the
registry whose binary is, so a `/cruise` typed into an editor with no command line of its own still runs
through whichever CLI harness the machine has. `CRUISE_HARNESS_COMMAND` (a shell template with `{prompt}`)
overrides all of that, and `CRUISE_POLL_SECONDS` how long a parked loop waits, so a run can be rehearsed
against a fake harness.

A person stops a run with `touch .specify/cruise.stop` (`stop`), or by interrupting a foreground `run`: the
iteration under way is killed, its increment commits are on the slice branch, and the next iteration re-derives
from disk.
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
# The delivery toolkit this script is part of: `commands/`, `scripts/`, `skills/` beside each other, at the root
# or under the delivery directory of an adopted repository.
DELIVERY = SCRIPT.parents[2]
COMMAND = DELIVERY / "commands/cruise.md"
CONFIG = ROOT / ".specify/cruise.json"
STOP = ROOT / ".specify/cruise.stop"
# The runner's own state: its pid while it runs, and where a detached runner writes what a foreground one prints.
PID = ROOT / ".specify/cruise.pid"
RUN_LOG = ROOT / ".specify/cruise-run.log"
# The last message a harness's after-response hook saw, for a stop hook whose event does not carry it.
LAST_RESPONSE = ROOT / ".specify/cruise-last-response.txt"
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
          "scripts/agents/cruise.py start` — and ends the turn with what that printed; the runner drives the ladder "
          "from here, a fresh session per iteration, and this session runs no stage of it")
# How many times the Stop hook holds a turn against one checkpoint before it lets go: the command rewrites the
# checkpoint at every stage boundary, so a checkpoint held this often without a rewrite is a session that is
# not moving, and a hook that never let go would spend tokens forever on it.
HOLD_LIMIT = 3
REGISTRY = SCRIPT.with_name("registry.json")
INTEGRATION = ROOT / ".specify/integration.json"
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
DEFAULTS: dict[str, Any] = {
    "enabled": False, "decide": "recommended-first", "release": "flagged", "constitution": "ratify",
    "hand": "browser", "unblock": "bosun", "stuck_after": 3, "max_iterations": None, "max_hours": None,
    "poll_minutes": 10,
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

    The first installed harness with a verified headless command whose binary is on PATH. Failing that, any
    harness in the registry whose binary is on PATH — a `/cruise` typed into an editor that has no command
    line, or into a CLI nobody has verified a print mode for, still runs through whichever CLI harness this
    machine has, and the sentence says so. Failing that, a refusal that names what is installed, which
    harnesses would do, and the override.
    """
    rows = registry()
    installed = [key for key in installed_keys() if key in rows]
    for key in installed:
        harness = rows[key]
        if headless_row(harness) is not None and shutil.which(binary_of(harness)):
            return harness, f"harness: {harness['name']}"
    for harness in rows.values():
        if headless_row(harness) is not None and shutil.which(binary_of(harness)):
            if installed:
                why = (f"{rows[installed[0]]['name']} is the installed harness, and "
                       + ("the registry records no way to run it headless"
                          if headless_row(rows[installed[0]]) is None
                          else f"`{binary_of(rows[installed[0]])}` is not on PATH"))
            else:
                why = "no harness is initialised here (`./init --integration <agent>` records one)"
            return harness, f"harness: {harness['name']}, found on PATH — {why}"
    able = ", ".join(f"{harness['name']} (`{binary_of(harness)}`)" for harness in rows.values()
                     if headless_row(harness) is not None)
    named = ", ".join(rows[key]["name"] for key in installed) or "no harness is initialised here"
    raise RuntimeError(f"no harness this loop can run an iteration through is on PATH: {named}"
                       f"{' is installed' if len(installed) == 1 else ' are installed' if installed else ''}, "
                       "and none of the harnesses the registry records a headless command for is on PATH — "
                       f"{able} (scripts/agents/registry.json, `headless`). Install one of those, or set "
                       "CRUISE_HARNESS_COMMAND to a shell template with {prompt}")


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
    return str(headless["command"]).replace("{permissions}", permissions), why


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
    own = tuple(path.relative_to(ROOT).as_posix() for path in (LOG, CHECKPOINT, PID, RUN_LOG, LAST_RESPONSE))
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


def iterate(template: str, prompt: str, environment: dict[str, str], iteration: int) -> str | None:
    """Run one iteration, marked as the runner's, echoing its output, and return its last line."""
    global CURRENT
    command = template.replace("{prompt}", shlex.quote(prompt))
    environment = {**environment, RUNNER_VARIABLE: "1", ITERATION_VARIABLE: str(iteration)}
    last = None
    with subprocess.Popen(command, shell=True, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env=environment) as process:
        CURRENT = process
        assert process.stdout is not None
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            if LAST_LINE.match(line):
                last = line.strip()
    CURRENT = None
    return last


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
    """Wait for a person: the stop file ends the run, a change under specs/ resumes it, `--no-park` exits 3."""
    print(f"cruise: parked — {reason}")
    if no_park:
        raise SystemExit(PARKED_EXIT)
    print(f"cruise: waiting; `touch {relative(STOP)}` ends the run, a change under specs/ or a commit "
          "resumes it", flush=True)
    while True:
        time.sleep(poll)
        if STOP.is_file():
            print("cruise: stopped by human")
            raise SystemExit(0)
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
    """A SIGTERM to the runner ends the iteration under way with it, so `stop --now` leaves no orphan session."""
    if CURRENT is not None and CURRENT.poll() is None:
        CURRENT.terminate()
    raise SystemExit(128 + signal.SIGTERM)


def run(arguments: list[str]) -> None:
    table = enabled()
    running = running_pid()
    if running is not None and running[0] != os.getpid():
        raise RuntimeError(f"a runner is already running here (pid {running[0]}, since {running[1]}); "
                           f"`python3 scripts/agents/cruise.py status` says where it is")
    feature = arguments[arguments.index("--feature") + 1] if "--feature" in arguments else None
    no_park, sandbox = "--no-park" in arguments, "--sandbox" in arguments
    harness, template, why = resolve_harness(sandbox)
    environment = child_environment(harness)
    prompt = prompt_for(harness, feature)
    poll = float(os.environ.get("CRUISE_POLL_SECONDS", table["poll_minutes"] * 60))
    PID.parent.mkdir(parents=True, exist_ok=True)
    PID.write_text(f"{os.getpid()} {now()}\n")
    signal.signal(signal.SIGTERM, terminated)
    try:
        drive(table, harness, template, why, environment, prompt, feature, no_park, poll)
    finally:
        if PID.is_file() and PID.read_text().split()[:1] == [str(os.getpid())]:
            PID.unlink()


def drive(table: dict[str, Any], harness: dict[str, Any] | None, template: str, why: str,
          environment: dict[str, str], prompt: str, feature: str | None, no_park: bool, poll: float) -> None:
    print(f"cruise: {why}")
    print(f"cruise: each iteration runs `{prompt}` in a fresh session; `touch {relative(STOP)}` stops it",
          flush=True)
    started_run = time.monotonic()
    iterations_this_run = 0
    fingerprints = [entry["fingerprint"] for entry in entries()]
    # The fingerprint a stuck run was already given its one unblocking iteration at, so it gets exactly one.
    unblocked_at: str | None = None
    ask = prompt
    while True:
        if STOP.is_file():
            print("cruise: stopped by human")
            return
        if table["max_iterations"] is not None and iterations_this_run >= table["max_iterations"]:
            print(f"cruise: budget spent — {table['max_iterations']} iteration(s)")
            return
        if table["max_hours"] is not None and time.monotonic() - started_run >= table["max_hours"] * 3600:
            print(f"cruise: budget spent — {table['max_hours']} hour(s)")
            return
        iteration = len(entries()) + 1
        started = now()
        LAST_RESPONSE.unlink(missing_ok=True)
        last = iterate(template, ask, environment, iteration)
        iterations_this_run += 1
        seen = fingerprint()
        fingerprints.append(seen)
        entry: dict[str, Any] = {"iteration": iteration, "started": started, "ended": now(),
                                 "harness": harness["key"] if harness is not None else "override",
                                 "last_line": last or "no last line", "fingerprint": seen}
        if ask != prompt:
            entry["attempt"] = "unblock"
        ask = prompt
        record(entry)
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
                print(f"cruise: no progress since iteration {since}; one iteration to unblock, then park")
                continue
            park(f"no progress since iteration {since}, and the bosun's iteration did not move it"
                 if unblocked_at == seen else f"no progress since iteration {since}", no_park, poll, seen)


def start(arguments: list[str]) -> None:
    """The loop, detached from the session that asked for it: what a typed `/cruise` does instead of running
    the ladder in a context nothing re-invokes. Everything that can refuse — the settings, the stop file, a
    runner already running, no harness to run through — is checked here, before the fork, so the refusal is
    read by whoever typed it; the runner's own output goes to the run log."""
    enabled()
    if os.environ.get(RUNNER_VARIABLE):
        raise RuntimeError(f"this session is iteration {os.environ.get(ITERATION_VARIABLE, '?')} of a run already "
                           "under way; the runner that started it re-invokes /cruise, nothing here has to")
    running = running_pid()
    if running is not None:
        print(f"cruise: the runner is already running (pid {running[0]}, since {running[1]}); its log is "
              f"{relative(RUN_LOG)}, and `python3 scripts/agents/cruise.py status` says where it is")
        return
    if STOP.is_file():
        raise RuntimeError(f"{relative(STOP)} is present: a person ended the last run, and the runner would end "
                           "again at once; remove the file to start another")
    feature = arguments[arguments.index("--feature") + 1] if "--feature" in arguments else None
    harness, _template, why = resolve_harness("--sandbox" in arguments)
    prompt = prompt_for(harness, feature)
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
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
    print(f"cruise: each iteration runs `{prompt}` in a fresh session; this session runs no stage of it")
    print(f"cruise: it writes to {relative(RUN_LOG)}; `python3 scripts/agents/cruise.py status` says where it is; "
          f"`touch {relative(STOP)}` ends it after the iteration in flight, `python3 scripts/agents/cruise.py stop "
          "--now` ends it now")


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
        print(f"cruise: {relative(STOP)} written and the runner (pid {running[0]}) terminated with the iteration "
              "in flight; its increment commits are on the slice branch, and the next run re-derives from disk")
        return
    print(f"cruise: {relative(STOP)} written; the runner (pid {running[0]}) ends after the iteration in flight, "
          "and /cruise refuses to start until the file is removed")


def status() -> None:
    running = running_pid()
    if running is not None:
        print(f"cruise: the runner is running (pid {running[0]}, since {running[1]}); its log is {relative(RUN_LOG)}")
    else:
        print("cruise: no runner is running here")
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


def main() -> None:
    arguments = sys.argv[1:]
    if not CONFIG.is_file():
        print(ABSENT)
        return
    verbs = {"run": lambda: run(arguments[1:]), "start": lambda: start(arguments[1:]),
             "stop": lambda: stop(arguments[1:]), "status": status, "resume": resume, "compacting": compacting,
             "loop": loop, "stopping": stopping, "responded": responded}
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
