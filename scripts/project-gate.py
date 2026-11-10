#!/usr/bin/env python3
"""A generated project, gated the way the board would gate it on this machine (docs/windows-plan.md, 24.11).

Nothing here is a twin of a project script: it is the board's own code, driven in order. Make is the
machine's, or on Windows installed through `tool_install` against its pinned checksum; the `python3` shim
is written as the board writes it when it starts; and every command runs with the `PATH` the board gives
its children — on Windows Git's `usr/bin` first and the board's tools on it, started through
`init_run.windows_argv` — as the board starts them.
Then:

1. a two-target Makefile with `SHELL := /bin/bash`, which is what every project's Makefile says;
2. a project generated per profile with the toy backend, its `init` checked out at LF;
3. PyYAML for the `python3` the project's scripts run on, the way `./init` gets it — pip `--user`, or where
   that `python3` refuses pip (PEP 668: Homebrew's, a recent Debian's) a venv put first on the `PATH`, which
   is what `./init` tells a person to do (`--no-init` is what keeps Spec Kit and the network out of this);
4. `make verify` in each, which must pass.

On macOS and Linux it runs the same steps with the machine's own Make: the project a person on a Mac makes
from the app, gated. `verify.yml`'s `project` job runs it on all three.
"""
from __future__ import annotations

import os
import shutil
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
ifeq ($(OS),Windows_NT)
.SHELLFLAGS := -hc
endif
.PHONY: one two
one:
\t@echo "one: $$BASH_VERSION" | grep -q 'one: [0-9]'
two: one
\t@[[ "$$(printf 'a\\n' | sed 's/a/b/')" == b ]] && echo "bash, sed and [[ ]] from Make"
\t./plain-script
"""
#: A line with no shell characters, naming a `#!` script: what the event model's `tsx` line is. Native Make
#: starts such a line itself unless `.SHELLFLAGS` sends it to bash, which is what the project's Makefile does.
PLAIN_SCRIPT = "#!/bin/sh\necho 'a #! script, from a plain line'\n"


def step(title: str) -> None:
    print(f"\n== {title}", flush=True)


def run(argv: list[str], where: Path, env: dict[str, str]) -> None:
    started = init_run.windows_argv(argv, env["PATH"]) if sys.platform == "win32" else argv
    print("$ " + " ".join(argv), flush=True)
    done = subprocess.run(started, cwd=where, env=env, check=False)
    if done.returncode != 0:
        raise SystemExit(f"project-gate: `{' '.join(argv)}` exited {done.returncode} in {where}")


def install_make() -> None:
    have = found(BY_KEY["make"])
    if have.state == "found":
        print(f"Make {have.version} is on this machine at {have.where}; the board would install none")
        return
    if sys.platform != "win32":
        raise SystemExit("project-gate: no Make here, and the board installs one only on Windows and macOS")
    installing = tool_install.Installing("make")
    installing.run()
    lines = installing.state()["lines"]
    print("\n".join(lines))
    if not lines or lines[-1].startswith("!"):
        raise SystemExit("project-gate: the board could not install Make")


def environment() -> dict[str, str]:
    env = {**login_environment(), "PYTHONUTF8": "1"}
    print("PATH, as the board's children get it:\n  " + "\n  ".join(env["PATH"].split(os.pathsep)[:8]) + "\n  …")
    return env


def with_yaml(project: Path, env: dict[str, str]) -> dict[str, str]:
    """`env` with a `python3` that imports yaml: as it was where it does, after `./init`'s own two tries."""
    def imports(python: str) -> bool:
        return subprocess.run([python, "-c", "import yaml"], env=env, capture_output=True).returncode == 0

    python = shutil.which("python3", path=env["PATH"]) or "python3"
    if sys.platform == "win32" or imports(python):
        return env
    quiet = ["-m", "pip", "install", "--disable-pip-version-check", "--quiet"]
    if subprocess.run([python, *quiet, "--user", "PyYAML"], env=env, capture_output=True).returncode == 0 \
            and imports(python):
        print("PyYAML installed for python3 with pip --user")
        return env
    venv = project / ".delivery-tools/venv"
    subprocess.run([python, "-m", "venv", "--system-site-packages", str(venv)], env=env, check=True)
    subprocess.run([str(venv / "bin/python"), *quiet, "PyYAML"], env=env, check=True)
    print(f"python3 refuses pip (PEP 668), so PyYAML is in {venv}, first on the PATH, as ./init says to do")
    return {**env, "PATH": f"{venv / 'bin'}{os.pathsep}{env['PATH']}"}


def generated(profile: str, parent: Path, env: dict[str, str]) -> Path:
    name = f"demo-{profile}"
    run([sys.executable, "-m", "slipwai", "generate", name, "--backend", "toy-plain", "--frontend", "none",
         "--profile", profile, "--no-init", "--skip-checks", "--output", str(parent)], ROOT,
        {**env, "PYTHONPATH": str(ROOT / "src"), "SLIPWAI_LANGUAGES": str(ROOT / "packages")})
    project = parent / name
    if b"\r" in (project / "init").read_bytes():
        raise SystemExit(f"project-gate: {project / 'init'} has CRLF line endings")
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
        (area / "plain-script").write_text(PLAIN_SCRIPT, encoding="utf-8", newline="\n")
        (area / "plain-script").chmod(0o755)
        run(["make", "two"], area, env)
        for profile in PROFILES:
            step(f"A {profile} project: generated, then its gate")
            project = generated(profile, area, env)
            run(["make", "verify"], project, with_yaml(project, env))
    print("\nproject-gate: green", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
