#!/usr/bin/env python3
"""`make mutation` for a Go service: Gremlins, over a staged copy of the module and the workspace modules
it imports, held to what its own report says.

    python3 scripts/go-mutation.py <service>

Why a stage. Gremlins copies the module it mutates — the nearest `go.mod` upwards, never the workspace — to
a temporary directory and runs the tests there. Nothing above that copy exists: not the root `go.work`, not
the sibling module under `packages/` it names. A service that imports shared code by module path, as
docs/architecture.md says to, cannot build in that copy — and Gremlins scores the build failure as KILLED,
because `go test` exits 1 for a failed build and a failed test alike. Run naked on such a service it reports
every mutant in the importing package killed, 100% efficacy and a green target, with tests that cannot fail.

So this stages the service and each workspace module it imports into one temporary tree, writes into the
staged `go.mod` a `require` and an *absolute* `replace` for each — a relative one breaks in Gremlins' own
copy the same way — and runs Gremlins there with `GOWORK=off`. A service that imports nothing from the
workspace is staged the same way: one path, and it is the tested one.

What it holds the run to, beyond the threshold in the service's `.gremlins.yaml`, for the reason
`failWhenNoMutations` is true in the Spring service's pom — a silent pass on a target no gate runs is worse
than a red one:

- **Nothing mutated is a failure.** Gremlins prints "No results to report." and exits 0 on a module with
  no mutable code; here that is exit 1.
- **A timed-out mutant is a failure.** Gremlins leaves timed-out mutants out of the score, so a suite that
  slowed past `timeout-coefficient` passes on the mutants it managed. The fix is in `.gremlins.yaml`.

Only this module is mutated. A shared module under `packages/` is built here and never mutated: run this
against it as a service of its own if its rules deserve a gate of their own.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

# The pinned release the factory wrote here; `go run` fetches it, so it is never a dependency of the module.
GREMLINS = "__GO_GREMLINS__"
REPORT = "gremlins.json"
TIMED_OUT = "TIMED OUT"


def module_path(go_mod: Path) -> str:
    for line in go_mod.read_text().splitlines():
        if line.startswith("module "):
            return line.split(None, 1)[1].strip()
    sys.exit(f"{go_mod}: no module directive")


def uses(go_work: str) -> list[str]:
    """The directories a go.work file uses, from `use ./x` lines and `use ( ... )` blocks alike."""
    directories, block = [], False
    for raw in go_work.splitlines():
        line = raw.split("//", 1)[0].strip()
        if block:
            if line == ")":
                block = False
            elif line:
                directories.append(line)
        elif line == "use (":
            block = True
        elif line.startswith("use "):
            directories.append(line[4:].strip())
    return directories


def workspace(service: Path) -> tuple[Path, dict[str, Path]]:
    """The directory holding the go.work above the service, and every module it uses, by module path.

    Without a workspace the service's parent stands in for the root and there is nothing to stage beside it.
    """
    for parent in [service, *service.parents]:
        work = parent / "go.work"
        if work.is_file():
            modules = {module_path(parent / d / "go.mod"): (parent / d).resolve() for d in uses(work.read_text())}
            return parent, modules
    return service.parent, {}


def imported(service: Path) -> set[str]:
    """Every module the service's packages and their tests depend on, by path — read with the workspace on,
    which is the only place these imports resolve."""
    listed = subprocess.run(
        ["go", "list", "-deps", "-test", "-f", "{{if .Module}}{{.Module.Path}}{{end}}", "./..."],
        cwd=service, text=True, capture_output=True,
    )
    if listed.returncode != 0:
        sys.stderr.write(listed.stderr)
        sys.exit(listed.returncode)
    return {line.strip() for line in listed.stdout.splitlines() if line.strip()}


def required(go_mod: str, module: str) -> bool:
    """Whether a go.mod already requires the module, on its own line or inside a `require (` block."""
    return re.search(rf"(^|\s){re.escape(module)}\s+v", go_mod) is not None


def stage(service: Path, root: Path, modules: dict[str, Path], into: Path) -> Path:
    """The service and the workspace modules it imports, copied under `into` at their paths below the root,
    the staged go.mod pointing at the staged copies by absolute path."""
    own = module_path(service / "go.mod")
    staged_service = into / service.relative_to(root)
    shutil.copytree(service, staged_service, symlinks=True)
    needed = {path: directory for path, directory in modules.items() if path != own}
    if needed:
        needed = {path: directory for path, directory in needed.items() if path in imported(service)}
    go_mod = staged_service / "go.mod"
    text = go_mod.read_text()
    sums = [service / "go.sum"]
    for path, directory in sorted(needed.items()):
        staged = into / directory.relative_to(root)
        shutil.copytree(directory, staged, symlinks=True)
        if not required(text, path):
            text += f"\nrequire {path} v0.0.0\n"
        text += f"replace {path} => {staged}\n"
        sums.append(staged / "go.sum")
        print(f"mutation: staged {directory.relative_to(root)} for {path}")
    go_mod.write_text(text)
    # A workspace keeps the checksums of a shared module's dependencies in go.work.sum; with GOWORK=off the
    # staged service needs them in its own go.sum. Every line once, whichever file it came from.
    sums.append(root / "go.work.sum")
    lines = dict.fromkeys(line for path in sums if path.is_file() for line in path.read_text().splitlines() if line)
    if lines:
        (staged_service / "go.sum").write_text("".join(f"{line}\n" for line in lines))
    return staged_service


def assess(report: Path) -> int:
    """Exit status from Gremlins' own report, after a run Gremlins itself passed."""
    if not report.is_file():
        sys.stderr.write(
            "mutation: Gremlins found nothing to mutate. A module with no mutable code, or a misconfigured "
            "run — either way a pass on nothing is not a pass.\n"
        )
        return 1
    result = json.loads(report.read_text())
    statuses = Counter(m["status"] for f in result.get("files", []) for m in f.get("mutations", []))
    if not statuses:
        sys.stderr.write("mutation: Gremlins reported no mutants; a pass on nothing is not a pass.\n")
        return 1
    if statuses[TIMED_OUT]:
        sys.stderr.write(
            f"mutation: {statuses[TIMED_OUT]} mutant(s) timed out, and Gremlins leaves a timed-out mutant "
            "out of its score. Raise `timeout-coefficient` in .gremlins.yaml, or make the suite faster, "
            "and rerun.\n"
        )
        return 1
    print(f"mutation: {sum(statuses.values())} mutants, none timed out; Gremlins' threshold held")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("usage: go-mutation.py <service>\n")
        return 2
    service = Path(argv[1]).resolve()
    if not (service / "go.mod").is_file():
        sys.stderr.write(f"{service}: no go.mod; the argument is a Go service's directory\n")
        return 2
    root, modules = workspace(service)
    into = Path(tempfile.mkdtemp(prefix="go-mutation-"))
    try:
        staged = stage(service, root.resolve(), modules, into)
        report = into / REPORT
        run = subprocess.run(
            ["go", "run", GREMLINS, "unleash", "--output", str(report), "."],
            cwd=staged, env={**os.environ, "GOWORK": "off"},
        )
        if run.returncode != 0:
            return run.returncode
        return assess(report)
    finally:
        shutil.rmtree(into, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
