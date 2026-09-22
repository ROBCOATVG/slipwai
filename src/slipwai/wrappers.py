"""The build wrapper a wrapped Java application runs through, written where the repository has none.

A Maven or Gradle repository that builds from the IDE often has no `mvnw` or `gradlew`, and commands recorded
as `mvn …` or `gradle …` then need a Maven or Gradle on every machine that runs the gate — the laptop that
adopts it, the CI runner — where `command not found` is the first thing `verify` says. The wrapper is the
ecosystem's own answer: a committed script that fetches its pinned build tool on first use, so the machine
needs a JDK and nothing else. So the survey (`ecosystems.py`) proposes the wrapper form — `./mvnw`,
`./gradlew` — for every Maven and Gradle build, whether or not the wrapper is there yet, and `adopt` and
`adopt --refresh` write it beside the build file where it is missing and the recorded commands run it: the
same Maven Wrapper every generated Java project carries (`assets/languages/java/build/`), and the Gradle
Wrapper vendored under `assets/adoption/wrappers/gradle/` (its jar base64-encoded, since every asset must be
text; `source-notes.md` there says where it came from). A command a person overrode to plain `mvn` or `gradle`
opts out: no wrapper is written for commands that do not run one — and `missing_tools` says, in the report,
which tools the recorded commands start with that this machine lacks, so the first `verify` is not the first
to find out.

The files are the repository's own from then on: committed with the adoption, not listed in `.written`, never
replaced by a newer factory; bumping the pinned tool is an edit to the properties file. Experimental, with the
rest of adoption (experimental).
"""
from __future__ import annotations

import base64
import re
import shutil
from pathlib import Path

from .assets import ADOPTION_ROOT, LANGUAGE_ROOT
from .ecosystems import prefixed
from .layout import Layout
from .services import App

# Where the shell ends one command and begins the next, and what a segment can start with that is not a
# program: an assignment, or one of the shell's own words. `cd` leads the list because a wrapped build that
# is not at the repository root is recorded as `cd <dir> && <build>`, which is most of them.
SEPARATORS = re.compile(r"&&|\|\||\||;")
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.DOTALL)
BUILTINS = frozenset((
    "cd", "export", "unset", "set", "echo", "printf", "true", "false", "source", ".", "test", "[", "exec",
    "eval", "exit", "return", "shift", "read", "trap", "umask", "ulimit", "wait", "pushd", "popd", "local",
))
MAVEN_SOURCE = LANGUAGE_ROOT / "java/build"
GRADLE_SOURCE = ADOPTION_ROOT / "wrappers/gradle"
# Per ecosystem: the tool's name, the script whose presence *is* the wrapper, and the files that make it up as
# (path beside the build file, asset it is copied from, executable). A `.base64` asset is decoded on the way out.
WRAPPERS: dict[str, tuple[str, str, tuple[tuple[str, Path, bool], ...]]] = {
    "maven": ("Maven", "mvnw", (
        ("mvnw", MAVEN_SOURCE / "mvnw", True),
        ("mvnw.cmd", MAVEN_SOURCE / "mvnw.cmd", False),
        (".mvn/wrapper/maven-wrapper.properties", MAVEN_SOURCE / ".mvn/wrapper/maven-wrapper.properties", False),
    )),
    "gradle": ("Gradle", "gradlew", (
        ("gradlew", GRADLE_SOURCE / "gradlew", True),
        ("gradlew.bat", GRADLE_SOURCE / "gradlew.bat", False),
        ("gradle/wrapper/gradle-wrapper.jar", GRADLE_SOURCE / "gradle-wrapper.jar.base64", False),
        ("gradle/wrapper/gradle-wrapper.properties", GRADLE_SOURCE / "gradle-wrapper.properties", False),
    )),
}


def missing_wrapper(root: Path, app: App) -> str | None:
    """The ecosystem whose wrapper `app`'s recorded commands run and its directory lacks — or None."""
    ecosystem = (app.toolchain or {}).get("ecosystem")
    if app.generated or ecosystem not in WRAPPERS:
        return None
    _, script, _ = WRAPPERS[ecosystem]
    runs_it = any(f"./{script}" in (command or "") for command in (app.commands or {}).values())
    return ecosystem if runs_it and not (root / app.path / script).is_file() else None


def pinned_version(ecosystem: str) -> str:
    """The build tool version the wrapper fetches, read from the properties it is written with."""
    properties = next(source for _, source, _ in WRAPPERS[ecosystem][2] if source.name.endswith(".properties"))
    match = re.search(r"-(\d+\.\d+(?:\.\d+)?)-bin\.zip", properties.read_text())
    return match.group(1) if match else "its pinned version"


def write_wrappers(root: Path, apps: list[App]) -> dict[str, list[str]]:
    """Write each missing wrapper beside its build file: application name to the paths written, from the root."""
    written: dict[str, list[str]] = {}
    for app in apps:
        ecosystem = missing_wrapper(root, app)
        if ecosystem is None:
            continue
        paths = []
        for relative, source, executable in WRAPPERS[ecosystem][2]:
            data = source.read_bytes()
            if source.suffix == ".base64":
                data = base64.b64decode(data)
            path = root / app.path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(0o755 if executable else 0o644)
            paths.append(prefixed(app.path, relative))
        written[app.name] = paths
    return written


def wrapper_lines(written: dict[str, list[str]], apps: list[App]) -> list[str]:
    """One report line per wrapper written: what, for whom, and that nothing needs installing beyond a JDK."""
    by_name = {app.name: app for app in apps}
    lines = []
    for name, paths in written.items():
        ecosystem = (by_name[name].toolchain or {}).get("ecosystem", "")
        tool = WRAPPERS[ecosystem][0]
        lines.append(
            f"Wrote the {tool} Wrapper for {name} ({', '.join(paths)}), since it had none: its commands run "
            f"./{WRAPPERS[ecosystem][1]}, which fetches {tool} {pinned_version(ecosystem)} itself, so a JDK is all "
            "this machine needs."
        )
    return lines


def tools_in(command: str) -> list[str]:
    """Every program a recorded command runs, in the order it runs them.

    A recorded command is a shell line, not a program and its arguments: a build that lives in a subdirectory
    is recorded as `cd tests/UI && npm ci`, and the program it needs is `npm`. Reading the first word off the
    whole line and asking the PATH for it reported `cd` — a shell builtin, on no PATH anywhere — as a missing
    tool for every target of every application whose build is not at the root, which buried the one tool that
    really was missing. So the line is split where the shell would split it, each segment's leading
    `VAR=value` assignments are stepped over, and the builtins are not programs to install.
    """
    found = []
    for segment in SEPARATORS.split(command):
        words = segment.strip().lstrip("(").split()
        while words and ASSIGNMENT.fullmatch(words[0]):
            words = words[1:]
        if words and words[0] not in BUILTINS:
            found.append(words[0])
    return list(dict.fromkeys(found))


def missing_tools(apps: list[App], layout: Layout) -> list[str]:
    """One line per tool a recorded command runs that is not on this machine's PATH: the gate will stop
    there, and saying so now beats a `command not found` in the middle of the first `verify`."""
    runs: dict[str, list[str]] = {}
    for app in apps:
        for target, command in (app.commands or {}).items():
            for tool in tools_in(command or ""):
                if "/" not in tool and shutil.which(tool) is None:
                    runs.setdefault(tool, []).append(f"{app.name}'s {target}")
    return [
        f"  `{tool}` is not on PATH here, and {', '.join(targets)} run it: {layout.make} verify stops there until it "
        "is installed, or project.json records what this machine does run."
        for tool, targets in runs.items()
    ]
