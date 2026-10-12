"""Install version 1 itself to reconstruct a crossing's base; never carry its generator in the keel.

A snapshot falls to the newest published stable release below it, and that difference is reported. An
explicit installed interpreter supports offline/private installations, but its version is checked before
it can supply a base. Its process never sees this keel's PYTHONPATH or installed language packages.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
import venv
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .errors import GenerationError
from .versions import is_release, is_snapshot, key, parse

VARIABLE = "SLIPWAI_LEGACY_PYTHON"
INDEX = "https://pypi.org/pypi/slipwai/json"


def selected(recorded: str, available: Sequence[str]) -> str:
    """The exact release, or the nearest stable release below a recorded snapshot."""
    match = parse(recorded)
    if match is None or match.group(1) != "1" or not (is_release(recorded) or is_snapshot(recorded)):
        raise GenerationError(f"{recorded!r} is not a recorded version 1 factory; "
                              "correct generator.generatedWith before `slipwai migrate`")
    if is_release(recorded):
        return recorded
    earlier = [version for version in available if is_release(version) and version.startswith("1.")
               and key(version) < key(recorded)]
    if not earlier:
        raise GenerationError(f"no published release precedes {recorded}; "
                              f"set {VARIABLE} to its installed release interpreter before `slipwai migrate`")
    return max(earlier, key=key)


def published() -> list[str]:
    try:
        with urllib.request.urlopen(INDEX, timeout=30) as response:
            document = json.load(response)
        releases = document.get("releases")
        if not isinstance(releases, dict):
            raise ValueError("no releases map")
        return list(releases)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise GenerationError(f"the published version 1 releases could not be read ({error}); "
                              f"set {VARIABLE} to an installed version 1 interpreter "
                              "and retry `slipwai migrate`") from error


@dataclass(frozen=True)
class Runtime:
    python: Path
    recorded: str
    used: str

    def run(self, arguments: list[str], cwd: Path, data: str | None = None) -> str:
        environment = {**os.environ, "PYTHONPATH": "", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
                       "SLIPWAI_LANGUAGES": str(self.python.parent / ".no-language-packages")}
        for name in ("GITHUB_HEAD_REF", "CI_COMMIT_REF_NAME"):
            environment.pop(name, None)
        try:
            done = subprocess.run([str(self.python), "-I", *arguments], cwd=cwd, env=environment, input=data,
                                  capture_output=True, text=True, encoding="utf-8", timeout=300)
        except subprocess.TimeoutExpired as hung:
            raise GenerationError(f"the installed {self.used} factory did not answer within 300s "
                                  f"({' '.join(arguments[:2])}); set {VARIABLE} to an installed version 1 "
                                  "interpreter and rerun `slipwai migrate --check`") from hung
        if done.returncode:
            raise GenerationError(f"the installed {self.used} factory could not supply its base: "
                                  f"{done.stderr.strip() or done.stdout.strip()}. "
                                  f"Check {VARIABLE} and rerun `slipwai migrate --check`")
        return done.stdout

    def replay(self, project: Path, destination: Path) -> None:
        self.run(["-m", "slipwai", "replay", "--into", str(destination)], project)

    def yaml(self, source: Path) -> object:
        program = "import json,sys,yaml; print(json.dumps(yaml.safe_load(sys.stdin.read())))"
        return json.loads(self.run(["-c", program], source.parent, source.read_text(encoding="utf-8")))


def actual(python: Path, cwd: Path) -> str:
    result = Runtime(python, "", "1.x").run(["-m", "slipwai", "--version"], cwd).strip()
    prefix = "slipwai "
    if not result.startswith(prefix):
        raise GenerationError(f"{python} is not an installed slipwai factory; correct {VARIABLE} and retry")
    return result[len(prefix):]


@contextmanager
def runtime(recorded: str, existing: Path | None = None) -> Iterator[Runtime]:
    """One throwaway installation, or a verified interpreter explicitly supplied by the person."""
    match = parse(recorded)
    if match is None or match.group(1) != "1":
        selected(recorded, [])  # the actionable grammar refusal, before any environment is made
    given = existing or (Path(os.environ[VARIABLE]) if os.environ.get(VARIABLE) else None)
    if given is not None:
        used = actual(given, Path.cwd())
        expected = selected(recorded, published() if is_snapshot(recorded) else [used])
        if used != expected:
            raise GenerationError(f"{given} supplies {used}, but this crossing needs {expected}; "
                                  f"correct {VARIABLE} and rerun `slipwai migrate --check`")
        yield Runtime(given, recorded, used)
        return
    used = selected(recorded, published() if is_snapshot(recorded) else [])
    with tempfile.TemporaryDirectory(prefix="slipwai-legacy-") as scratch:
        environment = Path(scratch)
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        try:
            installed = subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
                                        f"slipwai=={used}", "PyYAML==6.0.3"],
                                       capture_output=True, text=True, encoding="utf-8", timeout=300)
        except subprocess.TimeoutExpired as hung:
            raise GenerationError(f"installing slipwai {used} to reconstruct its base did not finish within "
                                  f"300s. Install it separately, set {VARIABLE}, then retry "
                                  "`slipwai migrate --check`") from hung
        if installed.returncode:
            raise GenerationError(f"slipwai {used} could not be installed to reconstruct its base: "
                                  f"{installed.stderr.strip()}. Install it separately, set {VARIABLE}, "
                                  "then retry `slipwai migrate --check`")
        verified = actual(python, environment)
        if verified != used:
            raise GenerationError(f"the installed factory is {verified}, not {used}; "
                                  f"install {used} separately and set {VARIABLE} before retrying")
        yield Runtime(python, recorded, used)
