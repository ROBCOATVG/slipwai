#!/usr/bin/env python3
"""A generated project, gated on Windows the way the board would gate it there (docs/windows-plan.md, 24.11).

Nothing here is a Windows twin of a project script: it is the board's own code, driven in order. Make is
installed through `tool_install` against its pinned checksum, the `python3` shim is written as the board
writes it when it starts, and every command runs with the `PATH` the board gives its children — Git's
`usr/bin` first, the board's tools on it — through `init_run.windows_argv`, as the board starts them.
Then:

1. a two-target Makefile with `SHELL := /bin/bash`, which is what every project's Makefile says;
2. a project generated per profile with the toy backend, its `init` checked out at LF;
3. `make verify` in each, which must pass.

On macOS and Linux it runs the same steps with the machine's own Make and skips the install, so it can be
tried anywhere; it proves something only on Windows. `verify.yml`'s `windows-project` job runs it.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slipwai import init_run, tool_install  # noqa: E402
from slipwai.prerequisites import BY_KEY, found  # noqa: E402
from slipwai.shell_environment import login_environment  # noqa: E402

PROFILES = ("standard", "event-modelling")
SHELL_CHECK = """SHELL := /bin/bash
.PHONY: one two
one:
\t@echo "one: $$BASH_VERSION" | grep -q 'one: [0-9]'
two: one
\t@[[ "$$(printf 'a\\n' | sed 's/a/b/')" == b ]] && echo "bash, sed and [[ ]] from Make"
"""


def step(title: str) -> None:
    print(f"\n== {title}", flush=True)


def run(argv: list[str], where: Path, env: dict[str, str]) -> None:
    started = init_run.windows_argv(argv, env["PATH"]) if sys.platform == "win32" else argv
    print("$ " + " ".join(argv), flush=True)
    done = subprocess.run(started, cwd=where, env=env, check=False)
    if done.returncode != 0:
        raise SystemExit(f"windows-gate: `{' '.join(argv)}` exited {done.returncode} in {where}")


def install_make() -> None:
    have = found(BY_KEY["make"])
    if have.state == "found":
        print(f"Make {have.version} is on this machine at {have.where}; the board would install none")
        return
    if sys.platform != "win32":
        raise SystemExit("windows-gate: no Make here, and the board installs one only on Windows and macOS")
    installing = tool_install.Installing("make")
    installing.run()
    lines = installing.state()["lines"]
    print("\n".join(lines))
    if not lines or lines[-1].startswith("!"):
        raise SystemExit("windows-gate: the board could not install Make")


def environment() -> dict[str, str]:
    env = {**login_environment(), "PYTHONUTF8": "1"}
    print("PATH, as the board's children get it:\n  " + "\n  ".join(env["PATH"].split(os.pathsep)[:8]) + "\n  …")
    return env


def generated(profile: str, parent: Path, env: dict[str, str]) -> Path:
    name = f"demo-{profile}"
    run([sys.executable, "-m", "slipwai", "generate", name, "--backend", "toy-plain", "--frontend", "none",
         "--profile", profile, "--no-init", "--skip-checks", "--output", str(parent)], ROOT,
        {**env, "PYTHONPATH": str(ROOT / "src"), "SLIPWAI_LANGUAGES": str(ROOT / "packages")})
    project = parent / name
    if b"\r" in (project / "init").read_bytes():
        raise SystemExit(f"windows-gate: {project / 'init'} has CRLF line endings")
    return project


def main() -> int:
    step("Make, from the board")
    install_make()
    step("python3 for bash, as the board writes it when it starts")
    print(tool_install.windows_shims() or "nothing to write here")
    env = environment()
    with tempfile.TemporaryDirectory() as scratch:
        area = Path(scratch)
        step("SHELL := /bin/bash, under this Make")
        (area / "Makefile").write_text(SHELL_CHECK, encoding="utf-8", newline="\n")
        run(["make", "two"], area, env)
        for profile in PROFILES:
            step(f"A {profile} project: generated, then its gate")
            project = generated(profile, area, env)
            run(["make", "verify"], project, env)
    print("\nwindows-gate: green", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
