#!/usr/bin/env python3
"""Run a recorded gate over code written before the gate existed, and fail only on what is new.

    python3 scripts/ratchet.py <application> <target> -- <command...>

A repository the delivery method was installed around (brownfield adoption; experimental) has a linter and a
type checker of its own, and on day one they are usually red: the rules arrived after the code did. Turning
them off would lose the rule; leaving them red would teach everyone that red means nothing. So this runs the
recorded command, reads its findings, and holds the code to a **baseline**: the findings that were there when
the baseline was recorded pass, and any finding not in it fails. The baseline only tightens — fixing a finding
never makes anything else fail, and `make ratchet-tighten` re-records the current findings once they shrink.

A finding is a line of the command's output that names a file in this repository *at a position* — `src/a.js:3:7`,
`Foo.cs(3,7)` — which is how every linter and type checker reports one; the position is then dropped, so that
editing above a known finding does not make it look new, and a line that merely mentions a file (`> node
lint.js`) is not a finding. A path is resolved against the directory the build runs in as well as the root —
`project.json` records it, and a wrapped application's commands usually start `cd <its directory> &&` — and
recorded root-relative either way, so a finding compares the same however the tool that printed it spelled it. A test runner names the test rather than a file — `--- FAIL: TestX`, `not ok 3 - adds`,
`FAILED tests/test_a.py::test_b`, Surefire's `[ERROR]   ShopTest.adds:42` — and each of those is a finding too,
`test: <name>`, so that a second failure beside a known one is new and named. Where a red command's output has
neither, this cannot tell new findings from old: the exit code is compared instead, and the report says so. A
command that could not run at all — its tool is not on this machine, which the shell reports as exit 127 (not
found) or 126 (not executable) — has no findings to record: the run fails, names the tool, and writes nothing,
because a baseline of "the build tool was missing" would pass forever on any machine that lacks it.

`test` runs through the same ratchet, with one difference: a suite that is red on the day the method arrives is
not quarantined behind anybody's back. The first run stops, shows the failures, and says what quarantining means;
`make ratchet-tighten`, once somebody has read them, records the state and from then on the run says the suite is
**quarantined** — passing on what was recorded, failing on a new failure the output names — until it is green and
`make ratchet-tighten` clears the entry. Two real adoptions found a red suite passing `verify` on a laptop with
nobody having decided that, and recorded it as the bug it was.

The baseline lives beside this script's Makefile as `baseline.json`, committed. Without an entry for an
application and target, `lint` and `typecheck` are recorded from the current findings and the run passes — locally
only: on CI (the `CI` variable set, as every forge does) a missing entry fails, because a baseline recorded on a
build machine is one nobody looked at and nobody committed. `RATCHET_TIGHTEN=1` re-records an entry unconditionally.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

RATCHETED = ("lint", "typecheck", "test")
# What `sh -c` exits with when the command's tool is not there to run: 127 not found, 126 not executable.
NOT_RUNNABLE = (126, 127)
# A token that names a file, with an optional position after it: `src/a.js:3:7`, `src/a.js(3,7)`, `Foo.cs(3,7)`.
LOCATION = re.compile(
    r"(?P<path>(?:[\w.-]+/)*[\w.-]+\.[A-Za-z0-9]+)(?P<position>(?::\d+(?::\d+)?)|(?:\(\d+(?:,\d+)?\)))?"
)
# A failed test named by its runner, on a line that names no file at a position: go's `--- FAIL: TestX/sub`, TAP's
# `not ok 3 - adds` (node:test, and every TAP reporter), pytest's `FAILED tests/test_a.py::test_b - message`,
# Surefire's summary `[ERROR]   ShopTest.adds:42 expected…` (three spaces: the summary's indent, which the
# `[ERROR] Failed to execute goal` lines do not have), Gradle's `ShopTest > adds FAILED`, `dotnet test`'s
# `Failed Shop.Adds [3 ms]`, Jest's `● Shop › adds`, Vitest's `× Shop > adds 3ms` and node's spec reporter's
# `✖ adds (1.06ms)` — the reporter node picks on a terminal, and from 23 everywhere, where TAP was the default before.
# The finding is the name alone: what stays the same from run to run, and from reporter to reporter, while the
# message and the duration beside it change.
TEST_FAILURES = (
    re.compile(r"^--- FAIL: (\S+)"),
    re.compile(r"^not ok \d+ -? ?(.+?)\s*(?:#.*)?$"),
    re.compile(r"^FAILED (\S+::\S+)"),
    re.compile(r"^\[ERROR\] {3}(\S+?)(?::\d+)?(?:\s|$)"),
    re.compile(r"^(\S+ > \S+) FAILED$"),
    re.compile(r"^\s*Failed (\S+)(?: \[[^\]]*\])?$"),
    re.compile(r"^\s*[●×✕✗✖✘] (.+?)(?:\s+\(?\d+(?:\.\d+)?\s?ms\)?)?$"),
)
# Node's spec reporter points at where a failed test is defined — `test at test/a.test.js:2:1` — under every `✖`. A
# file at a position, so it would read as a finding of its own; it says nothing the `✖` line does not, and TAP, the
# reporter node picks off a terminal, never prints it, so a baseline recorded under one reporter would be red under
# the other for the same one failing test. The same reporter heads its detail with `✖ failing tests:`, which is not
# a test either.
NOT_A_FINDING = re.compile(r"^\s*test at \S+:\d+|^\s*✖ failing tests:$")


def project_root(script: Path) -> Path:
    """The repository root: the nearest directory above this script holding `project.json`."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[1]


SCRIPT = Path(__file__).resolve()
ROOT = project_root(SCRIPT)
BASELINE = SCRIPT.parents[1] / "baseline.json"


def application_directory(application: str) -> Path:
    """Where this application's build runs, as `project.json` records it — the repository root for one at `.`.

    A tool prints the paths it found relative to the directory it ran in, and a wrapped application's build
    usually runs in its own: `cd admin-dev/themes/new-theme && npm exec -- tsc`. Resolving those against the
    repository root alone found nothing, so every finding in every application not at the root was invisible
    and the run fell back to comparing the exit code — which passes a second error tomorrow exactly as it
    passed the first. That is the ratchet not doing the one thing it exists for, silently, on precisely the
    repositories it was written for.
    """
    manifest = ROOT / "project.json"
    if not manifest.is_file():
        return ROOT
    try:
        recorded = json.loads(manifest.read_text()).get("deployables", {}).get(application, {}).get("path")
    except (OSError, json.JSONDecodeError, AttributeError):
        return ROOT
    if not isinstance(recorded, str) or recorded in ("", "."):
        return ROOT
    directory = (ROOT / recorded).resolve()
    return directory if directory.is_dir() else ROOT


def findings_in(output: str, root: Path, where: Path | None = None) -> list[str]:
    """Every line of `output` that names a file in the repository at a position, positions dropped, and every failed
    test a runner names (`test: <name>`), once each.

    `where` is the directory the command ran in, where that is not the root. A path is looked for under the
    root first and under `where` second, and either way the key is written root-relative, so a finding reads
    and compares the same however the tool that reported it spelled it.
    """
    found: list[str] = []
    for line in output.splitlines():
        if NOT_A_FINDING.match(line):
            continue
        names_a_file = False

        def replace(match: re.Match[str]) -> str:
            nonlocal names_a_file
            path = match.group("path")
            if not match.group("position"):
                return match.group(0)
            if (root / path).is_file():
                names_a_file = True
                return path
            if where is not None and (where / path).is_file():
                try:
                    spelled = (where / path).resolve().relative_to(root).as_posix()
                except ValueError:  # the command reached outside the repository; not ours to hold
                    return match.group(0)
                names_a_file = True
                return spelled
            return match.group(0)

        key = " ".join(LOCATION.sub(replace, line).split())
        if names_a_file:
            if key not in found:
                found.append(key)
            continue
        for pattern in TEST_FAILURES:
            match = pattern.match(line.rstrip())
            if match:
                name = f"test: {match.group(1).strip()}"
                if name not in found:
                    found.append(name)
                break
    return found


def read_baseline() -> dict:
    if not BASELINE.is_file():
        return {}
    try:
        loaded = json.loads(BASELINE.read_text())
    except ValueError as error:
        raise SystemExit(f"ratchet: {BASELINE.relative_to(ROOT)} is not valid JSON: {error}") from error
    return loaded if isinstance(loaded, dict) else {}


def write_baseline(baseline: dict) -> None:
    BASELINE.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main(argv: list[str]) -> int:
    if len(argv) < 4 or argv[2] != "--":
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    application, target, command = argv[0], argv[1], argv[3:]
    # The recipe passes the recorded command as one quoted word, which is the shell line to run as it stands —
    # `cd apps/shop && npm run lint` included. Several words are an older recipe's, and are re-quoted rather than
    # joined with spaces so that a recorded `sh -c 'test -n "$HOME"'` reaches the second shell as three words.
    shell = command[0] if len(command) == 1 else shlex.join(command)
    tool = next((word for word in shlex.split(shell) if word not in ("cd", "&&", ";", "env") and "/" not in word
                 and "=" not in word), shell) if shell.startswith("cd ") else shlex.split(shell)[0]
    run = subprocess.run(["sh", "-c", shell], cwd=ROOT, text=True, capture_output=True)
    output = run.stdout + run.stderr
    sys.stdout.write(output)
    sys.stdout.flush()
    name = f"{application} {target}"
    if run.returncode in NOT_RUNNABLE:
        print(
            f"ratchet: {name} could not run — `{tool}` is not on this machine (exit {run.returncode}), so there "
            "are no findings to hold the code to, and nothing is recorded. Install it, or change what project.json "
            f"records for {name} to what this repository does run (null is a written no).",
            file=sys.stderr,
        )
        return 1
    if run.returncode == 0:
        baseline = read_baseline()
        entry = baseline.get(application, {}).get(target)
        if entry and (entry.get("findings") or entry.get("exit")):
            print(f"ratchet: {name} is clean; its baseline can go — make ratchet-tighten re-records it")
        if os.environ.get("RATCHET_TIGHTEN") and entry:
            baseline[application][target] = {"exit": 0, "findings": []}
            write_baseline(baseline)
        return 0

    findings = findings_in(output, ROOT, application_directory(application))
    baseline = read_baseline()
    entry = baseline.get(application, {}).get(target)
    if entry is None or os.environ.get("RATCHET_TIGHTEN"):
        if os.environ.get("CI") and not os.environ.get("RATCHET_TIGHTEN"):
            print(
                f"ratchet: {name} failed (exit {run.returncode}) and {relative(BASELINE)} has no baseline for it. A "
                "baseline is recorded where somebody can read it: run the gate locally, look at what it "
                f"recorded, and commit {relative(BASELINE)}.",
                file=sys.stderr,
            )
            return 1
        told = f"{len(findings)} finding(s)" if findings else f"exit {run.returncode}, no finding names a file or a test"
        if target == "test" and not os.environ.get("RATCHET_TIGHTEN"):
            # A red linter is the rule arriving after the code, and recording it is mechanical. A red suite is a fact
            # about the software, and whether to ship on it is a person's answer (`/ground`, Safety net): the run
            # stops here, and the quarantine is recorded only when somebody asks for it by name.
            print(
                f"ratchet: {name} is red (exit {run.returncode}; {told}) and {relative(BASELINE)} has no baseline for "
                "it. A red suite is not quarantined behind your back: read the failures above, decide whether you would "
                "ship on them, then `make ratchet-tighten` records them as the quarantine — the gate passes on that "
                "state and says so on every run, and fails on a new failure — until the suite is green. Or fix the suite.",
                file=sys.stderr,
            )
            return 1
        baseline.setdefault(application, {})[target] = {"exit": run.returncode, "findings": findings}
        write_baseline(baseline)
        if target == "test":
            print(
                f"ratchet: {name} is red and is now QUARANTINED — {told} recorded. The gate passes on this state and "
                f"fails on a new failure; make it green, then make ratchet-tighten clears the quarantine. Commit "
                f"{relative(BASELINE)}."
            )
        else:
            print(
                f"ratchet: baseline {'re-' if entry else ''}recorded for {name} — {told}. These pass from now on and "
                f"nothing new does; commit {relative(BASELINE)}."
            )
        return 0

    known = set(entry.get("findings", []))
    quarantined = " — the suite is still QUARANTINED; make it green, then make ratchet-tighten" if target == "test" else ""
    if not findings:
        if run.returncode == entry.get("exit"):
            print(
                f"ratchet: {name} failed as it did when the baseline was recorded (exit {run.returncode}), and its "
                f"output names no file and no test, so new findings cannot be told from old: passing on the exit code "
                f"alone{quarantined}."
            )
            return 0
        print(
            f"ratchet: {name} failed with exit {run.returncode} where the baseline recorded {entry.get('exit')}, and "
            "its output names no file and no test to compare — treat this as new.",
            file=sys.stderr,
        )
        return 1
    new = [finding for finding in findings if finding not in known]
    if new:
        print(
            f"ratchet: {len(new)} new finding(s) in {name} since the baseline ({len(known)} known):\n  - "
            + "\n  - ".join(new)
            + "\nFix them, or — if the baseline is what is wrong — make ratchet-tighten after looking.",
            file=sys.stderr,
        )
        return 1
    gone = len(known - set(findings))
    print(
        f"ratchet: {name} — {len(findings)} known finding(s), none new"
        + (f"; {gone} fixed since the baseline, which make ratchet-tighten records" if gone else "")
        + quarantined
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
