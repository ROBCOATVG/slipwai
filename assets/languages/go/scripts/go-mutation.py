#!/usr/bin/env python3
"""`make mutation` for a Go service: Gremlins, over a staged copy of the module and the workspace modules
it imports, held to what its own report says.

    python3 scripts/go-mutation.py <service> [--since <branch-or-commit>]

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

`--since <branch-or-commit>` scopes the run to the production files that differ from that ref, which is the
difference between a stage priced per repository and one priced per change: every mutant of every file the
change did not touch re-proves work that shipped weeks ago, at the price of a full suite run each, and a
stage that expensive gets routed around rather than read. Without it the whole module is mutated, which is
what a scheduled sweep wants.

It is done here rather than with Gremlins' own `--diff`, which does not survive this layout. `--diff`
resolves changed paths against the repository root and matches them against paths within the module, so from
a module in a subdirectory — `apps/<service>`, every service this factory writes — every mutant comes back
SKIPPED and the run reports success having mutated nothing. Verified against 0.6.0 from both the module
directory and the repository root. The staged tree has no `.git` of its own either, and there `--diff` exits
1 without running. So the scope is computed here, from git, before anything is staged.

Gremlins has no include list: it selects by exclusion, so a scope is a complement, and this generates the
complement per run rather than writing one down — a written one is correct until the next file is added,
and says nothing when it stops being. The complement is passed as `--exclude-files`, which *replaces* the
`.gremlins.yaml` list rather than adding to it, so this reads that list and passes it back; a scoped run
that did not would quietly mutate the two trees the project excluded on purpose.
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
CONFIG = ".gremlins.yaml"
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


def scalar(text: str) -> str:
    """A YAML scalar as these files write one: bare, single-quoted or double-quoted.

    Quoted forms are taken whole, so a `#` inside a pattern stays in it; only a bare scalar has a trailing
    comment stripped, which is the one place a `#` cannot be part of the value.
    """
    text = text.strip()
    for quote in ("'", '"'):
        if len(text) >= 2 and text.startswith(quote) and text.endswith(quote):
            body = text[1:-1]
            return body.replace("\\\\", "\\").replace('\\"', '"') if quote == '"' else body.replace("''", "'")
    return text.split(" #", 1)[0].strip()


def excluded(config: Path) -> list[str]:
    """The `exclude-files` patterns under `unleash:` in a service's `.gremlins.yaml`.

    Read here because a scoped run has to carry them forward itself: `--exclude-files` replaces the file's
    list rather than adding to it, verified against 0.6.0, so a scoped run passing only its own complement
    would mutate `cmd/` and the store contract — the two trees this project excludes on purpose — and report
    survivors nobody should act on.

    Two nested keys in block style, and a loud failure on anything it cannot read rather than a silent empty
    list, because an unread exclusion list and an empty one look identical from here and only one of them is
    true. An absent file is not a failure: there is then nothing to carry forward.
    """
    if not config.is_file():
        return []
    lines = [line for line in config.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if any("\t" in line[: len(line) - len(line.lstrip())] for line in lines):
        sys.exit(f"{config}: a tab in the indentation. YAML does not allow one, so Gremlins is not reading "
                 "this file the way it looks like it reads.")
    patterns: list[str] = []
    section, listing = "", False
    for line in lines:
        body = line.strip()
        if line[0] not in " \t":
            section, listing = body.split(":", 1)[0], False
            continue
        if section != "unleash":
            continue
        if listing and body.startswith("- "):
            patterns.append(scalar(body[2:]))
            continue
        listing = False
        if body.startswith("exclude-files:"):
            rest = body[len("exclude-files:"):].strip()
            if rest and rest != "[]":
                sys.exit(f"{config}: `exclude-files` is written inline. Write it as a block list, one "
                         "`- pattern` per line, so a scoped run can read it and pass it back.")
            listing = True
    return patterns


def sources(module: Path) -> set[str]:
    """Every file in the module Gremlins could mutate, by path within it: Go production files, never tests."""
    return {str(path.relative_to(module)) for path in module.rglob("*.go") if not path.name.endswith("_test.go")}


def changed(service: Path, since: str) -> set[str]:
    """The module's production files that differ from `since`, as paths within it.

    `git diff <ref>` is the working tree against the ref, so work not yet committed counts; untracked files
    are asked for separately, because a file git has never seen is the likeliest thing a change in progress
    just wrote. Test files are dropped: Gremlins mutates production code, so a change that touched only its
    tests has no mutant of its own to answer for.
    """
    def git(*arguments: str) -> list[str]:
        done = subprocess.run(["git", "-C", str(service), *arguments], text=True, capture_output=True)
        if done.returncode != 0:
            sys.stderr.write(done.stderr)
            sys.exit("mutation: --since takes a branch or commit this repository has, and git could not "
                     f"resolve {since!r}.")
        return [line.strip() for line in done.stdout.splitlines() if line.strip()]

    paths = git("diff", "--name-only", "--relative", since, "--", ".")
    paths += git("ls-files", "--others", "--exclude-standard", "--", ".")
    return {path for path in paths if path.endswith(".go") and not path.endswith("_test.go")}


def mutable(keep: set[str], own: list[str]) -> set[str]:
    """Of the changed files, the ones this project has not already excluded from mutation.

    Gremlins matches an `exclude-files` pattern anywhere in the path within the module, so the same search
    is used here. Without this step a change confined to `cmd/` — wiring, excluded on purpose — would scope
    a run down to nothing, and a run that found nothing to mutate is this script's red. That red would be
    true of the run and false about the change.
    """
    return {path for path in keep if not any(re.search(pattern, path) for pattern in own)}


def scope(module: Path, keep: set[str], own: list[str]) -> list[str]:
    """Gremlins' arguments for a run scoped to `keep`: the module's own exclusions, then one per file out of
    scope.

    Anchored, and over the path within the module — `cmd/serve/main.go`, no leading `./`, which is the form
    0.6.0 matches — so that `events.go` cannot take `domain/events.go` with it.
    """
    out_of_scope = (f"^{re.escape(path)}$" for path in sorted(sources(module) - keep))
    return [argument for pattern in (*own, *out_of_scope) for argument in ("--exclude-files", pattern)]


def keep_report(report: Path, service: Path) -> Path | None:
    """The run's own report, copied beside the service before the staging tree it was written into is
    deleted.

    Without this the target leaves a log line and no evidence: Gremlins writes the report inside the tree
    this script makes and this script removes. Copied whatever the exit status, because a red run's report
    is the one most worth reading.
    """
    if not report.is_file():
        return None
    kept = service / REPORT
    shutil.copyfile(report, kept)
    print(f"mutation: report written to {os.path.relpath(kept)}")
    return kept


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


USAGE = "usage: go-mutation.py <service> [--since <branch-or-commit>]\n"


def arguments(argv: list[str]) -> tuple[Path, str | None] | None:
    """The service directory and the ref to scope against, or None when the line is not one of those."""
    rest, since = argv[1:], None
    if "--since" in rest:
        at = rest.index("--since")
        if at + 1 == len(rest):
            return None
        since, rest = rest[at + 1], rest[:at] + rest[at + 2:]
    return (Path(rest[0]), since) if len(rest) == 1 else None


def main(argv: list[str]) -> int:
    parsed = arguments(argv)
    if parsed is None:
        sys.stderr.write(USAGE)
        return 2
    given, since = parsed
    service = given.resolve()
    if not (service / "go.mod").is_file():
        sys.stderr.write(f"{service}: no go.mod; the argument is a Go service's directory\n")
        return 2
    scoped: list[str] = []
    if since is not None:
        own = excluded(service / CONFIG)
        keep = mutable(changed(service, since), own)
        if not keep:
            # Not the "nothing mutated" failure below, and the difference is worth keeping: that one is a run
            # that found no mutable code, which can only mean a misconfigured scope. This is a change with no
            # mutant of its own to answer for — it touched no production Go file, or only files this project
            # excludes — said out loud, because an unexplained green is what this script exists to refuse.
            print(f"mutation: nothing under {given} that differs from {since} is a file Gremlins would "
                  "mutate; no mutant to run")
            return 0
        scoped = scope(service, keep, own)
        print(f"mutation: scoped to {len(keep)} changed file(s) since {since}: {', '.join(sorted(keep))}")
    root, modules = workspace(service)
    into = Path(tempfile.mkdtemp(prefix="go-mutation-"))
    try:
        staged = stage(service, root.resolve(), modules, into)
        report = into / REPORT
        run = subprocess.run(
            ["go", "run", GREMLINS, "unleash", "--output", str(report), *scoped, "."],
            cwd=staged, env={**os.environ, "GOWORK": "off"},
        )
        keep_report(report, service)
        if run.returncode != 0:
            return run.returncode
        return assess(report)
    finally:
        shutil.rmtree(into, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
