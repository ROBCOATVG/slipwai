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
    python3 scripts/agents/cruise.py status                # what the log says the run is doing

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
}
# Whole numbers: the least value allowed, and whether `null` is one of the answers.
NUMBERS: dict[str, tuple[int, bool]] = {
    "stuck_after": (1, False), "max_iterations": (1, True), "max_hours": (1, True), "poll_minutes": (1, False),
}
DEFAULTS: dict[str, Any] = {
    "enabled": False, "decide": "recommended-first", "release": "flagged", "constitution": "ratify",
    "hand": "browser", "stuck_after": 3, "max_iterations": None, "max_hours": None, "poll_minutes": 10,
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
    for arguments in (("rev-parse", "HEAD"), ("status", "--porcelain")):
        result = subprocess.run(["git", *arguments], cwd=ROOT, text=True, capture_output=True)
        digest.update(result.stdout.encode())
    specs = ROOT / "specs"
    for path in sorted(specs.rglob("*")) if specs.is_dir() else []:
        if path.is_file() and path != LOG:
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


def iterate(template: str, prompt: str, environment: dict[str, str]) -> str | None:
    """Run one iteration, echoing its output, and return its last line."""
    command = template.replace("{prompt}", shlex.quote(prompt))
    last = None
    with subprocess.Popen(command, shell=True, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env=environment) as process:
        assert process.stdout is not None
        for line in process.stdout:
            sys.stdout.write(line)
            if LAST_LINE.match(line):
                last = line.strip()
    return last


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
        last = iterate(template, prompt, environment)
        iterations_this_run += 1
        seen = fingerprint()
        fingerprints.append(seen)
        record({"iteration": iteration, "started": started, "ended": now(), "harness": harness["key"],
                "last_line": last or "no last line", "fingerprint": seen})
        if last == "cruise: done":
            print("cruise: done — every specification is satisfied")
            return
        if last == "cruise: stopped: human":
            print("cruise: stopped by human")
            return
        if last is not None and last.startswith("cruise: parked: "):
            park(last.removeprefix("cruise: parked: "), no_park, poll, seen)
            continue
        window = fingerprints[-table["stuck_after"]:]
        if len(window) == table["stuck_after"] and len(set(window)) == 1:
            park(f"no progress since iteration {iteration - table['stuck_after'] + 1}", no_park, poll, seen)


def status() -> None:
    log = entries()
    if not log:
        print("cruise: no iteration has run here")
        return
    last = log[-1]
    print(f"cruise: {len(log)} iteration(s) logged; the last ended {last['ended']} with `{last['last_line']}`")
    if str(last["last_line"]).startswith("cruise: parked: "):
        print(f"cruise: parked — {str(last['last_line']).removeprefix('cruise: parked: ')}")
    if STOP.is_file():
        print(f"cruise: {STOP.relative_to(ROOT)} is present; remove it before the next run")


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
