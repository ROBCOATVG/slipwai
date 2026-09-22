#!/usr/bin/env python3
"""`/cruise`'s settings, and the outer loop that re-invokes it with a fresh context until the specs are satisfied.

`.specify/cruise.json` holds how `/cruise` runs `commands/drive.md` with nobody at the wheel — who decides a
product question, how a slice is released, what a demo is driven with, when a run parks. This reads the file
and says what each setting is and controls, checks a hand edit, and changes them through `--set`, refusing
anything the command could not act on. `run` is the loop: one headless harness session per iteration, each a
fresh context, until the last line of an iteration says `done`, a person stops it, or nothing can move.

    python3 scripts/agents/cruise.py                       # every setting and what it controls
    python3 scripts/agents/cruise.py --check               # well-formed; `make check-agents` runs this
    python3 scripts/agents/cruise.py --set enabled=true    # change settings, checked, any time
    python3 scripts/agents/cruise.py run [--feature F] [--no-park] [--sandbox]   # the loop; `make cruise`
    python3 scripts/agents/cruise.py status      # what the log says the run is doing
    python3 scripts/agents/cruise.py resume      # print the checkpoint into a compacted context; nothing when none
    python3 scripts/agents/cruise.py compacting  # stamp the checkpoint before the harness compacts
    python3 scripts/agents/cruise.py loop        # what is reading this session's last line: the runner, or nobody
    python3 scripts/agents/cruise.py stopping    # Claude Code's Stop hook: refuse to end a turn mid-iteration

`run` marks every session it starts with `CRUISE_RUNNER=1` and `CRUISE_ITERATION=<n>`, which is how `loop` and
`stopping` tell a runner's iteration from a `/cruise` a person typed — where nothing reads the last line, so
`continue` is not an end the ladder has, and the session goes on to the next unit instead.

A person stops a run with `touch .specify/cruise.stop`, or by interrupting this script: the iteration under
way is killed, its increment commits are on the slice branch, and the next iteration re-derives from disk.
`CRUISE_HARNESS_COMMAND` (a shell template with `{prompt}`) overrides how the harness is run and
`CRUISE_POLL_SECONDS` how long a parked loop waits, so a run can be rehearsed against a fake harness.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
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


ROOT = project_root(Path(__file__).resolve(), 2)
CONFIG = ROOT / ".specify/cruise.json"
STOP = ROOT / ".specify/cruise.stop"
LOG = ROOT / "specs/cruise-log.jsonl"
# The iteration in flight, rewritten by `/cruise` at every stage boundary so a compacted context can resume.
CHECKPOINT = ROOT / "specs/cruise-checkpoint.md"
RESUME = ("cruise: this session is a /cruise iteration whose context was compacted. The checkpoint below is what "
          "the summary lost; read it before acting, then commands/cruise.md for the rules it names — run "
          "commands/drive.md as written, decide at its stops by the stop table, end with one of the four last lines.")
# The two variables `run` sets in every session it starts: what tells a runner's iteration from a typed one.
RUNNER_VARIABLE, ITERATION_VARIABLE = "CRUISE_RUNNER", "CRUISE_ITERATION"
# What a session is told when nothing reads its last line — the same words `commands/cruise.md` carries.
UNREAD = ("no outer loop is reading this: `cruise: continue` is not an end here, so the ladder goes on to the next "
          "unit in this session and ends only with `done`, `parked` or `stopped`; `make cruise` runs it unattended")
# How many times the Stop hook holds a turn against one checkpoint before it lets go: the command rewrites the
# checkpoint at every stage boundary, so a checkpoint held this often without a rewrite is a session that is
# not moving, and a hook that never let go would spend tokens forever on it.
HOLD_LIMIT = 3
REGISTRY = Path(__file__).with_name("registry.json")
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


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def installed_harness() -> dict[str, Any]:
    """The registry row of the first harness Spec Kit recorded as installed."""
    if not INTEGRATION.is_file():
        raise RuntimeError("no harness is initialised here (`./init --integration <agent>` records one)")
    state = json.loads(INTEGRATION.read_text())
    keys = state.get("installed_integrations") or [state.get("default_integration")]
    rows = {row["key"]: row for row in json.loads(REGISTRY.read_text())["harnesses"]}
    for key in keys:
        if key in rows:
            return rows[key]
    raise RuntimeError("the installed harness is not one the registry knows")


def harness_command(harness: dict[str, Any], sandbox: bool) -> tuple[str, str]:
    """The shell template one iteration runs, and the sentence saying which permissions it runs under."""
    override = os.environ.get("CRUISE_HARNESS_COMMAND")
    if override:
        return override, "harness: CRUISE_HARNESS_COMMAND, as given"
    headless = harness.get("headless")
    if not isinstance(headless, dict):
        raise RuntimeError(f"the registry records no way to run {harness['name']} headless "
                           "(scripts/agents/registry.json, `headless`): use the harness's own loop over /cruise "
                           "in a session, or set CRUISE_HARNESS_COMMAND to a shell template with {prompt}")
    permissions = headless.get("sandboxPermissions" if sandbox else "permissions", "")
    why = ("--sandbox: every permission check is bypassed, which is only for a container with nothing to lose"
           if sandbox else
           "edits are accepted and every other permission is the harness's own to grant or refuse; pass "
           "--sandbox inside a disposable container to bypass them all")
    return str(headless["command"]).replace("{permissions}", permissions), f"harness: {harness['name']}; {why}"


def fingerprint() -> str:
    """What the tree looks like to the ladder: the commit, the working tree's state, and every file under specs/."""
    digest = hashlib.sha256()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    digest.update(head.stdout.encode())
    # Untracked files one per line, so the log and the checkpoint can be left out: a directory reported as
    # untracked the moment the log is first written read as progress, once, in every run.
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True,
                            capture_output=True)
    own = tuple(path.relative_to(ROOT).as_posix() for path in (LOG, CHECKPOINT))
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


def child_environment(harness: dict[str, Any]) -> dict[str, str]:
    """What the iteration runs under: this environment, plus what the registry's `headless.env` sets for the
    harness — Claude Code's wait ceiling, which otherwise ends a print session while its delegates still run —
    and minus the harness's own session variable, so a session started from inside another never reads its
    parent's id as its own."""
    environment = dict(os.environ)
    headless = harness.get("headless")
    if isinstance(headless, dict) and isinstance(headless.get("env"), dict):
        environment.update({str(key): str(value) for key, value in headless["env"].items()})
    session_variable = (harness.get("usage") or {}).get("env")
    if session_variable:
        environment.pop(str(session_variable), None)
    return environment


def iterate(template: str, prompt: str, environment: dict[str, str], iteration: int) -> str | None:
    """Run one iteration, marked as the runner's, echoing its output, and return its last line."""
    command = template.replace("{prompt}", shlex.quote(prompt))
    environment = {**environment, RUNNER_VARIABLE: "1", ITERATION_VARIABLE: str(iteration)}
    last = None
    with subprocess.Popen(command, shell=True, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env=environment) as process:
        assert process.stdout is not None
        for line in process.stdout:
            sys.stdout.write(line)
            if LAST_LINE.match(line):
                last = line.strip()
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


def stopping() -> None:
    """Claude Code's Stop hook: hold the turn while an iteration is in flight and this is not its end.

    Prose in a command file is not a control — the same session ended an iteration after the upstream stages
    and, later, on a report that said "continuing now" — so the end of a turn is checked here, where the harness
    lets a hook refuse it. The hook reads the event Claude Code hands it on stdin, and holds the turn (a
    `block` decision, with the reason the model reads next) when a checkpoint says an iteration is in flight,
    no stop file says a person ended it, and the last assistant message does not end on one of the four last
    lines — or ends on `continue` in a session no runner started, where that line reaches nobody. A turn that
    ends on `done` or `stopped` takes the checkpoint with it, the way the runner would. Every hold is stamped
    on the checkpoint, and the hook lets go after HOLD_LIMIT holds with no rewrite in between — below the
    harness's own cap on consecutive blocks, so it is this script that decides when to let go, and says so.
    """
    if not CHECKPOINT.is_file() or STOP.is_file():
        return
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        event = {}
    # The message the turn ends on, as the event carries it; the transcript otherwise, which can lag the event.
    text = event.get("last_assistant_message")
    if not isinstance(text, str) or not text.strip():
        transcript = Path(str(event.get("transcript_path") or ""))
        if not transcript.is_file():
            return
        text = last_assistant_text(transcript)
    last = (text or "").rstrip().splitlines()[-1].strip() if (text or "").strip() else ""
    ended = LAST_LINE.match(last) is not None
    if ended and last in ("cruise: done", "cruise: stopped: human"):
        CHECKPOINT.unlink(missing_ok=True)
        return
    if ended and (last != "cruise: continue" or os.environ.get(RUNNER_VARIABLE)):
        return
    checkpoint = CHECKPOINT.read_text()
    if checkpoint.count("- **Held:**") >= HOLD_LIMIT:
        print(f"cruise: held {HOLD_LIMIT} times against a checkpoint nothing rewrote; letting the turn end",
              file=sys.stderr)
        return
    next_step = next((line.strip() for line in checkpoint.splitlines() if line.strip().startswith("- **Next:**")),
                     "- **Next:** (the checkpoint names no next step; read it and commands/cruise.md)")
    if last == "cruise: continue":
        why = (f"`cruise: continue` reaches nobody: no runner started this session ({RUNNER_VARIABLE} is unset), "
               "so the ladder continues here and the iteration ends only with `cruise: done`, "
               "`cruise: parked: <why>` or `cruise: stopped: human`.")
    else:
        why = ("an iteration is in flight (specs/cruise-checkpoint.md) and this turn did not end on one of its "
               "four last lines. An iteration ends only on `cruise: continue`, `cruise: done`, "
               "`cruise: parked: <why>` or `cruise: stopped: human`; a message that says what it is about to do "
               "next is a stop, whatever it says.")
    with CHECKPOINT.open("a") as handle:
        handle.write(f"- **Held:** {now()} — {last or 'no last line'!r}\n")
    reason = (f"cruise: {why} Continue from the checkpoint: {next_step}. A person ends the run with "
              f"`touch {STOP.relative_to(ROOT)}`.")
    print(json.dumps({"decision": "block", "reason": reason}))


def park(reason: str, no_park: bool, poll: float, seen: str) -> None:
    """Wait for a person: the stop file ends the run, a change under specs/ resumes it, `--no-park` exits 3."""
    print(f"cruise: parked — {reason}")
    if no_park:
        raise SystemExit(PARKED_EXIT)
    print(f"cruise: waiting; `touch {STOP.relative_to(ROOT)}` ends the run, a change under specs/ or a commit "
          "resumes it")
    while True:
        time.sleep(poll)
        if STOP.is_file():
            print("cruise: stopped by human")
            raise SystemExit(0)
        if fingerprint() != seen:
            print("cruise: something changed; resuming")
            return


def run(arguments: list[str]) -> None:
    table = load()
    if not table["enabled"]:
        raise RuntimeError("not enabled: `python3 scripts/agents/cruise.py --set enabled=true`, checked, turns it on")
    feature = arguments[arguments.index("--feature") + 1] if "--feature" in arguments else None
    no_park, sandbox = "--no-park" in arguments, "--sandbox" in arguments
    harness = installed_harness()
    template, why = harness_command(harness, sandbox)
    environment = child_environment(harness)
    prompt = f"/cruise {feature}" if feature else "/cruise"
    poll = float(os.environ.get("CRUISE_POLL_SECONDS", table["poll_minutes"] * 60))
    print(f"cruise: {why}")
    print(f"cruise: each iteration runs `{prompt}` in a fresh session; `touch {STOP.relative_to(ROOT)}` stops it")
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
        last = iterate(template, ask, environment, iteration)
        iterations_this_run += 1
        seen = fingerprint()
        fingerprints.append(seen)
        entry: dict[str, Any] = {"iteration": iteration, "started": started, "ended": now(),
                                 "harness": harness["key"], "last_line": last or "no last line", "fingerprint": seen}
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
                ask = f"{prompt} unblock: no progress since iteration {since}"
                print(f"cruise: no progress since iteration {since}; one iteration to unblock, then park")
                continue
            park(f"no progress since iteration {since}, and the bosun's iteration did not move it"
                 if unblocked_at == seen else f"no progress since iteration {since}", no_park, poll, seen)


def status() -> None:
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
    if arguments[:1] == ["run"]:
        run(arguments[1:])
        return
    if arguments[:1] == ["status"]:
        status()
        return
    if arguments[:1] == ["resume"]:
        resume()
        return
    if arguments[:1] == ["compacting"]:
        compacting()
        return
    if arguments[:1] == ["loop"]:
        loop()
        return
    if arguments[:1] == ["stopping"]:
        stopping()
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
