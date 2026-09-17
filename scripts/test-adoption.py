#!/usr/bin/env python3
"""Prove brownfield adoption end to end, on repositories shaped like the ones it will meet.

`docs/adopting.md` says `slipwai adopt` installs the delivery method around a repository the factory did not
make, that the gate it installs is green on day one, that adopting again changes nothing, and that a newer
factory later merges over the adopted repository as cleanly as over a generated one. Said and not gated, that
rots the way any asserted-only path does — so this takes each fixture under `tests/fixtures/adopt/` (one per
ecosystem the survey recognises, two in languages the factory cannot generate, one whose CI is GitLab's), makes
it a repository with history of its own, and holds the whole path to those claims: adopt commits once as the
factory and leaves the tree clean; `adopt --refresh` straight afterwards changes nothing;
`make -f delivery/Makefile verify` passes, red linter and all — a red suite stops the first run and is
quarantined only on request — where the fixture's toolchain is on
this machine (and says so where it is not); a GitLab repository gets a GitLab job and no GitHub workflow; a
newer factory's `migrate` is one clean merge that carries its change in and leaves the repository's own files
as they were; and the gate passes again afterwards. `make test-adoption` runs it; CI runs it as a job of its own.

Experimental, with the rest of adoption (`AGENTS.md` says what the word means here): a fixture that
fails here is the feedback loop working.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FACTORY = Path(__file__).resolve().parents[1]
FIXTURES = FACTORY / "tests/fixtures/adopt"
NEWER = "99.0.0"
CHANGED_SKILL = "skills/tdd/SKILL.md"
CHANGE = "\n\nA sentence a newer factory added.\n"
IDENTITY = (
    "-c", "user.name=product", "-c", "user.email=product@local", "-c", "maintenance.auto=false", "-c", "gc.auto=0",
)
# Per fixture: the flags `adopt --yes` is given, and the tool its own build needs on this machine for `verify`.
ADOPTIONS: dict[str, tuple[list[str], str]] = {
    # A language the factory cannot generate, with a linter that is red on day one on purpose.
    "javascript-service": (
        ["--why", "the runtime is end of life", "--purpose", "javascript-service=Sells things."], "node",
    ),
    # The survey proposes pytest for a `tests/` directory; the repository runs unittest, and the flag says so.
    "python-worker": (["--command", "python-worker:test=python3 -m unittest discover -s tests -v"], "python3"),
    # A language the factory generates, so `add-service --language go` could put a generated service beside it.
    "go-module": ([], "go"),
    # A language the factory cannot generate, whose toolchain the gate's machine may not have.
    "dotnet-api": ([], "dotnet"),
    # CI on GitLab, a deploy job, a start script, and a test suite that is red on day one: the gate is a GitLab
    # job and not a GitHub workflow, the release path and the kind are read off the tree, and the red suite stops
    # the first `verify` and says so — quarantined only when `ratchet-tighten` is asked for by name.
    "javascript-gitlab": (["--purpose", "javascript-gitlab=Takes orders."], "node"),
    # An Ant build from a NetBeans layout, its jars committed: below the floor the method holds a repository to, so
    # the programme opens with the move to Maven or Gradle, and the survey neither refuses it nor crashes on it.
    "ant-desktop": ([], "ant"),
}
# A fixture whose test suite is red on day one: the first `verify` stops and says so — a red suite is never
# quarantined behind anybody's back — and `ratchet-tighten` is the person's decision to quarantine it, after which the
# gate is green.
RED_SUITES = {"javascript-gitlab"}
# The programme's first step where the build is below the floor: said on docs/change-strategy.md whatever the strategy.
FLOOR = {"ant-desktop": "the build is Ant with its jars committed — move it to Maven or Gradle"}
# What the tree itself says is out of support, per fixture, as the support table dates it: the recommendation and
# the architecture view have to say so even with no `why` recorded.
EXPIRED = {"go-module": "Go 1.22 left support on 2025-02-11"}


def run(*command: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, env=env, check=False)


def must(result: subprocess.CompletedProcess, what: str) -> str:
    if result.returncode != 0:
        raise SystemExit(f"test-adoption: {what} failed (exit {result.returncode})\n{result.stdout}{result.stderr}")
    return result.stdout


def clean(repo: Path) -> bool:
    return must(run("git", "status", "--porcelain", cwd=repo), "git status").strip() == ""


def own_files(fixture: Path) -> dict[str, bytes]:
    return {path.relative_to(fixture).as_posix(): path.read_bytes() for path in fixture.rglob("*") if path.is_file()}


def newer_factory(into: Path) -> Path:
    """This checkout, copied, with one toolkit skill changed and its version raised: what a newer factory is."""
    factory = into / "factory"
    factory.mkdir()
    for name in ("src", "assets"):
        shutil.copytree(FACTORY / name, factory / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("catalog.json", "slipwai", "CHANGELOG.md"):
        shutil.copy2(FACTORY / name, factory / name)
    (factory / "VERSION").write_text(f"{NEWER}\n")
    skill = factory / "assets/toolkit" / CHANGED_SKILL
    skill.write_text(skill.read_text() + CHANGE)
    return factory


def verify(repo: Path, tool: str, when: str, makefile: str = "delivery/Makefile") -> None:
    if shutil.which(tool) is None:
        print(f"  verify {when}: skipped — `{tool}` is not on this machine, so the fixture's own build cannot run")
        return
    env = {key: value for key, value in os.environ.items() if key not in ("CI", "RATCHET_TIGHTEN")}
    result = run("make", "-f", makefile, "verify", cwd=repo, env=env)
    if result.returncode != 0:
        raise SystemExit(
            f"test-adoption: `make -f {makefile} verify` failed {when}\n"
            f"{result.stdout[-4000:]}{result.stderr[-4000:]}"
        )
    ratchet = [line for line in result.stdout.splitlines() if line.startswith("ratchet:")]
    print(f"  verify {when}: green" + "".join(f"; {line}" for line in ratchet[:2]))


def quarantine(repo: Path, tool: str) -> None:
    """A red suite on day one: `verify` stops with the failures and the word, records nothing, and `ratchet-tighten`
    quarantines it by name — the state the next `verify` passes on and says so."""
    if shutil.which(tool) is None:
        return
    env = {key: value for key, value in os.environ.items() if key not in ("CI", "RATCHET_TIGHTEN")}
    stopped = run("make", "-f", "delivery/Makefile", "verify", cwd=repo, env=env)
    if stopped.returncode == 0 or "is not quarantined behind your back" not in stopped.stderr:
        raise SystemExit(
            f"test-adoption: a red suite should stop the first verify and say so\n"
            f"{stopped.stdout[-3000:]}{stopped.stderr[-3000:]}"
        )
    baseline = repo / "delivery/baseline.json"
    if baseline.is_file() and '"test"' in baseline.read_text():
        raise SystemExit("test-adoption: the red suite was quarantined without anybody asking for it")
    tightened = run("make", "-f", "delivery/Makefile", "ratchet-tighten", cwd=repo, env=env)
    if tightened.returncode != 0 or "QUARANTINED" not in tightened.stdout:
        raise SystemExit(
            f"test-adoption: ratchet-tighten should quarantine the red suite\n"
            f"{tightened.stdout[-3000:]}{tightened.stderr[-3000:]}"
        )
    print("  day one: the red suite stopped verify and said so; ratchet-tighten quarantined it on request")


def adopt_fixture(name: str, flags: list[str], tool: str, work: Path, factory: Path) -> None:
    fixture = FIXTURES / name
    original = own_files(fixture)
    repo = work / name
    shutil.copytree(fixture, repo)
    must(run("git", "init", "-q", "-b", "main", cwd=repo), "git init")
    must(run("git", "add", "-A", cwd=repo), "git add")
    must(run("git", *IDENTITY, "commit", "-q", "-m", "theirs", cwd=repo), "git commit")
    before = must(run("git", "rev-parse", "HEAD", cwd=repo), "rev-parse").strip()
    print(f"test-adoption: {name}")

    adopted = must(run(str(FACTORY / "slipwai"), "adopt", "--yes", *flags, cwd=repo), "adopt")
    first = adopted.splitlines()[0]
    if not first.startswith("adopted ") or "experimental" not in first:
        raise SystemExit(
            f"test-adoption: the report's first line does not say what it adopted, or that it is experimental:\n{first}"
        )
    author = must(run("git", "log", "--format=%ae", "-1", cwd=repo), "git log").strip()
    if author != "factory@local" or must(run("git", "rev-parse", "HEAD^", cwd=repo), "rev-parse").strip() != before:
        raise SystemExit(f"test-adoption: {name}: adoption is not one commit by the factory on top of theirs")
    if not clean(repo):
        raise SystemExit(f"test-adoption: {name}: adoption left the tree unclean")
    for path, content in original.items():
        if path in ("AGENTS.md", ".gitignore"):
            if not (repo / path).read_bytes().startswith(content):
                raise SystemExit(f"test-adoption: {name}: {path} no longer starts with the repository's own text")
        elif (repo / path).read_bytes() != content:
            raise SystemExit(f"test-adoption: {name}: adoption wrote over {path}")
    if (repo / ".gitlab-ci.yml").is_file():
        if (repo / ".github/workflows/verify-delivery.yml").exists():
            raise SystemExit(f"test-adoption: {name}: a GitHub workflow was written into a GitLab repository")
        if not (repo / "delivery/ci/verify-delivery.gitlab-ci.yml").is_file():
            raise SystemExit(f"test-adoption: {name}: no GitLab job was written for a repository whose CI is GitLab's")
    drive = (repo / "delivery/commands/drive.md").read_text()
    for stage in ("**Ground**", "**Principles**", "**Pin**", "**Implementation**", "**Convergence**"):
        if stage not in drive:
            raise SystemExit(f"test-adoption: {name}: /drive has no {stage} stage")
    order = [drive.index(stage) for stage in ("**Ground**", "**Principles**", "**Pin**", "**Implementation**")]
    if order != sorted(order):
        raise SystemExit(f"test-adoption: {name}: /drive's adoption stages are out of order")
    view = (repo / "delivery/survey/structure.md").read_text()
    headings = ("### Where anything starts", "### What the graph says", "## What this means for the map",
                "## Where to cut")
    for heading in headings:
        if heading not in view:
            raise SystemExit(f"test-adoption: {name}: the architecture view lacks {heading!r}")
    # The essay opens with the strategy the trigger recommends: changing in place for an end-of-life runtime —
    # said in `why`, or read off the tree, as the Go module's `go 1.22` is — and leaving it where neither says.
    essay = (repo / "delivery/docs/change-strategy.md").read_text()
    expired = EXPIRED.get(name)
    strategy = "in-place" if "--why" in flags or expired else "leave-it"
    if "## Recommended for this repository" not in essay or f"**`{strategy}`**" not in essay:
        raise SystemExit(f"test-adoption: {name}: docs/change-strategy.md does not open by recommending `{strategy}`")
    if expired and (expired not in essay or expired not in view or "### What it runs on" not in view):
        raise SystemExit(f"test-adoption: {name}: the platform the tree names as out of support ({expired}) is not "
                         "on docs/change-strategy.md and survey/structure.md")
    floor = FLOOR.get(name)
    if floor and (floor not in essay or essay.index(floor) < essay.index("### The programme")):
        raise SystemExit(f"test-adoption: {name}: docs/change-strategy.md's programme does not open with the build "
                         f"({floor})")
    ground = (repo / "delivery/commands/ground.md").read_text()
    if "## The rows, as they stand" not in ground or "### Integration" not in ground or "/ground" not in drive:
        raise SystemExit(f"test-adoption: {name}: /ground lacks its rows or questions, or /drive does not name it")
    running = (repo / "delivery/survey/running.md").read_text()
    skill = (repo / "delivery/skills/run-the-app/SKILL.md").read_text()
    if "Not yet proven" not in running or "`delivery/survey/running.md`" not in skill or "never here" not in skill:
        raise SystemExit(f"test-adoption: {name}: the run path's home is not the repository's own survey/running.md")
    pin = (repo / "delivery/commands/characterise.md").read_text()
    if ("not a framework you add" not in pin or "Mockito" not in pin or "never a mocking framework" not in drive
            or "never a mocking framework added for the purpose" not in drive.split("**Implementation**")[1]):
        raise SystemExit(f"test-adoption: {name}: /characterise or /drive's Pin stage allows a mocking framework")
    hooks = (repo / ".specify/extensions.yml").read_text()
    if "before_specify:" not in hooks or "before_plan:" not in hooks or hooks.count("convergence-map") < 2:
        raise SystemExit(f"test-adoption: {name}: .specify/extensions.yml lacks the adoption's hooks")
    print("  adopted: one commit by the factory; nothing of theirs written over; /drive grounds, pins, holds the map")

    refreshed = must(run(str(FACTORY / "slipwai"), "adopt", "--refresh", cwd=repo), "adopt --refresh")
    if not clean(repo) or "refreshed: nothing" not in refreshed:
        raise SystemExit(f"test-adoption: {name}: re-surveying straight after adopting was not a no-op\n{refreshed}")
    print("  re-survey: a no-op")

    if name in RED_SUITES:
        quarantine(repo, tool)
    verify(repo, tool, "on day one")
    must(run("git", "add", "-A", cwd=repo), "git add")
    if not clean(repo):
        must(
            run("git", *IDENTITY, "commit", "-q", "-m", "day one: the baseline and what the build wrote", cwd=repo),
            "commit",
        )

    env = os.environ | {
        "GIT_AUTHOR_NAME": "product", "GIT_AUTHOR_EMAIL": "product@local",
        "GIT_COMMITTER_NAME": "product", "GIT_COMMITTER_EMAIL": "product@local",
        "SLIPWAI_INDEX": "http://127.0.0.1:9/none",
    }
    migrated = run(str(factory / "slipwai"), "migrate", cwd=repo, env=env)
    conflicts = must(run("git", "diff", "--name-only", "--diff-filter=U", cwd=repo), "git diff").split()
    if migrated.returncode != 0 or conflicts:
        raise SystemExit(
            f"test-adoption: {name}: a newer factory did not merge cleanly "
            f"(conflicts: {', '.join(conflicts) or 'none'})\n"
            f"{migrated.stdout}{migrated.stderr}"
        )
    if not clean(repo):
        raise SystemExit(f"test-adoption: {name}: the migration left the tree unclean")
    if CHANGE.strip() not in (repo / "delivery" / CHANGED_SKILL).read_text():
        raise SystemExit(f"test-adoption: {name}: the newer factory's change did not arrive")
    for path, content in original.items():
        if path not in ("AGENTS.md", ".gitignore") and (repo / path).read_bytes() != content:
            raise SystemExit(f"test-adoption: {name}: the migration changed {path}, which is the repository's own")
    print(f"  migrated to {NEWER}: one clean merge; the repository's own files untouched")
    verify(repo, tool, "after the migration")


JOURNEY = "converging"
ADR = """# 0002. Leave the architecture where it is

Date: 2026-09-07

## Status

Accepted

## Context

The trigger was the runtime, and the runtime is upgraded.

## Decision

Strategy: leave-it

## Consequences

The retirement ledger stays empty on purpose.
"""


def commit(repo: Path, message: str) -> None:
    must(run("git", "add", "-A", cwd=repo), "git add")
    if not clean(repo):
        must(run("git", *IDENTITY, "commit", "-q", "-m", message, cwd=repo), "git commit")


def rows_of(repo: Path) -> dict[str, dict]:
    document = json.loads((repo / "project.json").read_text())
    return {row["axis"]: row for row in document["convergence"]}


def journey(work: Path, factory: Path) -> None:
    """The whole arc on the smallest fixture that can reach every target: adopt, the map, one method slice that
    flips a row with the gate agreeing, every other rung established as a person would establish it, converge,
    and then the generated project's own gate at the root — and a newer factory's migrate over that."""
    repo = work / JOURNEY
    shutil.copytree(FIXTURES / JOURNEY, repo)
    must(run("git", "init", "-q", "-b", "main", cwd=repo), "git init")
    commit(repo, "theirs")
    print(f"test-adoption: {JOURNEY} — the journey")
    if shutil.which("node") is None:
        print("  skipped — `node` is not on this machine")
        return
    must(run(str(FACTORY / "slipwai"), "adopt", "--yes", "--why", "the runtime is end of life",
             "--purpose", "shop=Sells things.", cwd=repo), "adopt")
    verify(repo, "node", "on day one")
    commit(repo, "day one: the baseline")
    rows = rows_of(repo)
    if (rows["safety-net"]["rung"], rows["path-to-production"]["rung"], rows["structure"]["rung"]) != (
        "tests-exist", "pipeline", "laid-out",
    ):
        raise SystemExit(f"test-adoption: {JOURNEY}: the map did not read the tree as expected: {rows}")
    print("  adopted: the map reads tests-exist, pipeline, laid-out off the tree")

    # One method slice: the suite is green in the gate and nothing is quarantined, so the safety-net row may
    # truthfully move one rung. A person moves it; the refresh redraws the page; the gate agrees.
    document = json.loads((repo / "project.json").read_text())
    for row in document["convergence"]:
        if row["axis"] == "safety-net":
            row.update(rung="tests-pass", provenance="confirmed", planned=None)
    (repo / "project.json").write_text(json.dumps(document, indent=2) + "\n")
    commit(repo, "method slice: the suite is green in the gate")
    must(run(str(FACTORY / "slipwai"), "adopt", "--refresh", cwd=repo), "adopt --refresh")
    commit(repo, "the map redrawn")
    verify(repo, "node", "after the method slice")
    if rows_of(repo)["safety-net"]["rung"] != "tests-pass":
        raise SystemExit(f"test-adoption: {JOURNEY}: the refresh moved the row a person placed")
    print("  method slice: safety-net tests-exist -> tests-pass; the gate agrees and the page follows")

    # The rest of the journey, as a person establishes each rung: every row at its target, the layout declared,
    # the infrastructure answered, the constitution ratified in full, the strategy decided by an ADR.
    document = json.loads((repo / "project.json").read_text())
    for row in document["convergence"]:
        row.update(rung=row["target"], provenance="confirmed", planned=None)
    document["deployables"]["shop"]["layout"] = "hexagonal"
    document["infrastructure"].update(home="none", provenance="confirmed")
    (repo / "project.json").write_text(json.dumps(document, indent=2) + "\n")
    requirements = must(run("python3", "delivery/scripts/check-constitution.py", "--requirements", cwd=repo),
                        "constitution requirements")
    (repo / ".specify/memory").mkdir(parents=True, exist_ok=True)
    (repo / ".specify/memory/constitution.md").write_text("# Ratified\n\n" + requirements)
    (repo / "delivery/docs/adr").mkdir(parents=True, exist_ok=True)
    (repo / "delivery/docs/adr/0002-leave-it.md").write_text(ADR)
    commit(repo, "every rung established")
    must(run(str(FACTORY / "slipwai"), "adopt", "--refresh", cwd=repo), "adopt --refresh")
    commit(repo, "the map redrawn at every target")
    verify(repo, "node", "with every row at its target")

    ready = run(str(FACTORY / "slipwai"), "converge", "--check", cwd=repo)
    if ready.returncode != 0 or "ready" not in ready.stdout:
        raise SystemExit(f"test-adoption: {JOURNEY}: converge --check is not ready:\n{ready.stdout}{ready.stderr}")
    must(run(str(FACTORY / "slipwai"), "converge", cwd=repo), "converge")
    if (repo / "delivery").exists() or not clean(repo):
        raise SystemExit(f"test-adoption: {JOURNEY}: converge left delivery/ behind or the tree unclean")
    document = json.loads((repo / "project.json").read_text())
    if document.get("origin") != "adopted" or document["layout"]["delivery"] != "." or "converged" not in document:
        raise SystemExit(f"test-adoption: {JOURNEY}: the record after converge is wrong: {document.get('layout')}")
    print("  converged: the material is at the root; origin adopted kept as history")
    # The generated project's own gate, at the root, over what was adopted.
    verify(repo, "node", "at the root, as a generated project", makefile="Makefile")

    # The merge commit is the repository's own, so the person's identity goes with it, as for every fixture above.
    env = os.environ | {
        "GIT_AUTHOR_NAME": "product", "GIT_AUTHOR_EMAIL": "product@local",
        "GIT_COMMITTER_NAME": "product", "GIT_COMMITTER_EMAIL": "product@local",
        "SLIPWAI_INDEX": "http://127.0.0.1:9/none",
    }
    migrated = run(str(factory / "slipwai"), "migrate", cwd=repo, env=env)
    conflicts = must(run("git", "diff", "--name-only", "--diff-filter=U", cwd=repo), "git diff").split()
    if migrated.returncode != 0 or conflicts or not clean(repo):
        raise SystemExit(f"test-adoption: {JOURNEY}: a newer factory did not merge cleanly after converge\n"
                         f"{migrated.stdout}{migrated.stderr}")
    if CHANGE.strip() not in (repo / CHANGED_SKILL).read_text():
        raise SystemExit(f"test-adoption: {JOURNEY}: the newer factory's change did not arrive at the root")
    verify(repo, "node", "after a newer factory's migrate", makefile="Makefile")
    print(f"  migrated to {NEWER} at the root: one clean merge, the gate green")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--keep", type=Path, default=None, metavar="DIR", help="leave the adopted repositories under DIR"
    )
    parser.add_argument("--only", action="append", default=[], metavar="FIXTURE", help="run one fixture; repeatable")
    args = parser.parse_args()
    names = [name for name in ADOPTIONS if not args.only or name in args.only]
    run_journey = not args.only or JOURNEY in args.only
    missing = [name for name in names if not (FIXTURES / name).is_dir()]
    if missing:
        raise SystemExit(f"test-adoption: no fixture under {FIXTURES}: {', '.join(missing)}")
    with tempfile.TemporaryDirectory(prefix="adoption-") as scratch:
        work = Path(scratch)
        factory = newer_factory(work)
        for name in names:
            flags, tool = ADOPTIONS[name]
            adopt_fixture(name, flags, tool, work, factory)
        if run_journey:
            journey(work, factory)
        if args.keep is not None:
            args.keep.mkdir(parents=True, exist_ok=True)
            for name in names:
                shutil.copytree(work / name, args.keep / name, dirs_exist_ok=True)
            print(f"test-adoption: kept under {args.keep}")
    print(f"test-adoption: {len(names)} fixture(s) adopted, re-surveyed, verified and migrated"
          + ("; the journey converged" if run_journey else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
