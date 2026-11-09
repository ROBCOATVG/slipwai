#!/usr/bin/env python3
"""The fence: what a generated project runs on macOS and Linux, held to the bytes it had, or to a reason.

Phase 24 lets Windows run a project's own files under Git Bash, and the owner's rule for it is that bytes
may change on macOS and Linux and behaviour may not (docs/windows-plan.md, D2). A test cannot prove a
behaviour unchanged across every machine, but it can make every change to those files a sentence somebody
wrote. So this generates a project per profile and service shape, takes the SHA-256 of every file that
machine runs — the Makefiles, `init`, everything under `scripts/`, the hook, the harness settings — and
compares them with `tests/fixtures/run-files.sha256`.

A digest moves only through `--why`: the record is rewritten and the reason appended to it with a digest
over the whole record, so a record edited by hand, or moved without a reason, no longer matches its last
reason. `tests/test_fence.py` runs `--check`.

    python3 scripts/fence.py --check
    python3 scripts/fence.py --why "verify joins PYTHONPATH with os.pathsep; ':' on macOS and Linux as before"
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "tests/fixtures/run-files.sha256"
BACKEND = "toy-plain"
#: Each project the fence generates: its profile and what its service keeps and serves. The toy backend
#: declares no target, so every one goes nowhere; what a target adds is a language package's to fence.
MATRIX = tuple((profile, keeps, serves)
               for profile in ("standard", "event-modelling")
               for keeps, serves in (("memory", "none"), ("postgres", "toy-serve")))
WHY = "# why: "


def runs(path: Path) -> bool:
    """Whether a file in a generated project is one macOS or Linux runs, by where it sits."""
    parts = path.parts
    return (path.name in ("Makefile", "init") or path.suffix in (".sh", ".mk")
            or "scripts" in parts[:-1] or parts[0] in (".githooks", ".claude"))


def generated(profile: str, keeps: str, serves: str, into: Path) -> Path:
    """One project, generated with the toy backend into `into`."""
    done = subprocess.run(
        [sys.executable, "-m", "slipwai", "generate", "demo", "--backend", BACKEND, "--frontend", "none",
         "--profile", profile, "--persistence", keeps, "--http", serves, "--no-init", "--output", str(into)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "SLIPWAI_LANGUAGES": str(ROOT / "packages")},
    )
    if done.returncode != 0:
        raise SystemExit(f"fence: generating {profile}/{keeps}/{serves} failed:\n{done.stdout}{done.stderr}")
    return into / "demo"


def digests() -> list[str]:
    """`<sha256>  <profile>-<persistence>-<http>  <path>` for every file each project runs, sorted."""
    lines = []
    for profile, keeps, serves in MATRIX:
        with tempfile.TemporaryDirectory() as scratch:
            project = generated(profile, keeps, serves, Path(scratch))
            for file in project.rglob("*"):
                relative = file.relative_to(project)
                if file.is_file() and relative.parts[0] != ".git" and runs(relative):
                    digest = hashlib.sha256(file.read_bytes()).hexdigest()
                    lines.append(f"{digest}  {profile}-{keeps}-{serves}  {relative.as_posix()}")
    return sorted(lines)


def whole(lines: list[str]) -> str:
    """The digest over a record's digests: what a reason vouches for."""
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]


def read() -> tuple[list[str], list[str], list[str]]:
    """The record's header, its reasons and its digests."""
    header, reasons, lines = [], [], []
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        if line.startswith(WHY):
            reasons.append(line)
        elif line.startswith("#") or not line:
            header.append(line)
        else:
            lines.append(line)
    return header, reasons, lines


def problems(now: list[str]) -> list[str]:
    """What stands between the record and the tree, as lines to print; none when they agree."""
    if not RECORD.exists():
        return [f"{RECORD.relative_to(ROOT)} is missing: python3 scripts/fence.py --why '...'"]
    _, reasons, recorded = read()
    found = []
    if not reasons or reasons[-1].split()[3] != whole(recorded):
        found.append("the record's digests are not the ones its last reason vouches for: they were edited "
                     "by hand. Put them back and move them with --why.")
    gone, came = set(recorded) - set(now), set(now) - set(recorded)
    for line in sorted(gone | came, key=lambda one: one.split("  ", 1)[1]):
        found.append(("now   " if line in came else "was   ") + line)
    if gone or came:
        found.append("A file macOS or Linux runs changed. If what it does there is unchanged, say why: "
                     "python3 scripts/fence.py --why '<what changed, and why behaviour is the same>'")
    return found


HEADER = """\
# What a generated project runs on macOS and Linux, as SHA-256 over each file's bytes, written by
# scripts/fence.py. A line changes only with a reason appended below it, saying why what the file does on
# macOS and Linux is unchanged (docs/windows-plan.md, D2). Each reason carries the digest of the record it
# vouches for; editing a line by hand breaks that.
#"""


def write(now: list[str], why: str) -> None:
    reasons = read()[1] if RECORD.exists() else []
    reasons.append(f"{WHY}{datetime.date.today().isoformat()} {whole(now)} {why}")
    RECORD.write_text("\n".join([HEADER, *reasons, "", *now]) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="fail where the tree and the record differ")
    group.add_argument("--why", help="rewrite the record, with this reason for what moved")
    arguments = parser.parse_args(argv)
    now = digests()
    if arguments.why is not None:
        if not arguments.why.strip():
            parser.error("--why needs the reason itself")
        if not problems(now):
            print("fence: nothing moved; the record stands")
            return 0
        write(now, arguments.why.strip())
        print(f"fence: {len(now)} digests written, with the reason")
        return 0
    found = problems(now)
    for line in found:
        print(line)
    if not found:
        print(f"fence: {len(now)} files across {len(MATRIX)} projects are as recorded")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
