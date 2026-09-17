"""What a build ecosystem's files say about the code they build, and how its own tools answer the Make targets.

The table behind `survey.py` (brownfield adoption; experimental as `AGENTS.md` defines the word). One
row per ecosystem the survey can recognise — by the manifest file that starts its build — with the language
it is written in, how to tell its toolchain's version, and the command its own tools run for each of the
eight Make targets a service owes. A target the ecosystem has no answer for is `None`, which the manifest
records as a written `null` and the Makefile runs as a line that says so; it is never guessed at.

Deliberately not `catalog.json`: the catalog is the contract for what the factory can *generate*, and a C#
row there would be a claim nothing behind it keeps. These rows say only what can be *recognised*, and every
command here is a proposal the person confirms or overrides — `survey.py` records which.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# The eight targets, in the order a service's recipes spell them (`project/native_commands.py`).
TARGETS = ("install", "typecheck", "lint", "test", "integration", "adversarial", "audit", "mutation")
# What a wrapped application may record beside the eight, each with a target of its own and never proposed by the
# survey: `test-full`, a suite too slow for `verify`; `smoke`, the one command that starts the application and proves
# it answers — the fact the day-one gate cannot compose from the eight, and the floor beside the build
# (`programme.py`), because every false green the first adoptions shipped was a change nothing had started.
EXTRA = ("test-full", "smoke")
Commands = dict[str, str | None]


@dataclass(frozen=True)
class Detected:
    """One buildable directory, as its files describe it."""

    ecosystem: str
    language: str
    evidence: str
    commands: Commands
    # `kind` names the runtime a CI job sets up (`node`, `python`, `go`, `java`, `dotnet`, `php`, `ruby`);
    # `version` is the pin the tree carries, or empty where it carries none.
    toolchain: dict[str, str]
    # What the build packages, where that decides which rung of the ladder is next: `war` for a Maven build that
    # makes one.
    packaging: str | None = None


def complete(**given: str | None) -> Commands:
    """Every target, in order; the ones not given are written no's."""
    return {target: given.get(target) for target in TARGETS}


def read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def first_line(path: Path) -> str:
    text = read(path).strip()
    return text.splitlines()[0].strip().lstrip("v") if text else ""


def in_dir(directory: str, command: str) -> str:
    """A command run inside `directory`, from the repository root — as is when the directory is the root."""
    return command if directory == "." else f"cd {directory} && {command}"


def prefixed(directory: str, path: str) -> str:
    return path if directory == "." else f"{directory}/{path}"


def node(root: Path, directory: str) -> Detected | None:
    manifest = root / directory / "package.json"
    if not manifest.is_file():
        return None
    try:
        package = json.loads(read(manifest))
    except ValueError:
        package = {}
    scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
    scripts = scripts if isinstance(scripts, dict) else {}
    here = root / directory
    if (here / "pnpm-lock.yaml").is_file():
        tool, install = "pnpm", "pnpm install --frozen-lockfile"
    elif (here / "yarn.lock").is_file():
        tool, install = "yarn", "yarn install --frozen-lockfile"
    else:
        tool, install = "npm", "npm ci" if (here / "package-lock.json").is_file() else "npm install"

    def run(script: str) -> str:
        return in_dir(directory, f"{tool} run {script}")

    dependencies = {
        **(package.get("dependencies") or {}), **(package.get("devDependencies") or {})
    } if isinstance(package, dict) else {}
    typescript = (here / "tsconfig.json").is_file() or "typescript" in dependencies
    test = scripts.get("test")
    typecheck = next((s for s in ("typecheck", "type-check", "check-types") if s in scripts), None)
    version = first_line(here / ".nvmrc") or first_line(here / ".node-version") or str(
        (package.get("engines") or {}).get("node", "") if isinstance(package, dict) else ""
    )
    return Detected(
        "node", "typescript" if typescript else "javascript", prefixed(directory, "package.json"),
        complete(
            install=in_dir(directory, install),
            typecheck=run(typecheck) if typecheck else (
                in_dir(directory, f"{tool} exec -- tsc --noEmit") if typescript else None
            ),
            lint=run("lint") if "lint" in scripts else None,
            test=run("test") if test and "no test specified" not in test else None,
            integration=run("test:integration") if "test:integration" in scripts else None,
            audit=in_dir(directory, f"{tool} audit --audit-level=critical" if tool != "yarn" else "yarn audit"),
        ),
        {"kind": "node", "version": version.strip()},
    )


def python(root: Path, directory: str) -> Detected | None:
    here = root / directory
    evidence = next((f for f in ("pyproject.toml", "requirements.txt", "setup.py") if (here / f).is_file()), None)
    if evidence is None:
        return None
    pyproject = read(here / "pyproject.toml")
    requirements = (here / "requirements.txt").is_file()
    configured = {
        "ruff": "[tool.ruff" in pyproject or (here / "ruff.toml").is_file(),
        "flake8": (here / ".flake8").is_file() or "[flake8]" in read(here / "setup.cfg") + read(here / "tox.ini"),
        "mypy": "[tool.mypy" in pyproject or (here / "mypy.ini").is_file(),
        "pyright": "[tool.pyright" in pyproject or (here / "pyrightconfig.json").is_file(),
        "pytest": "[tool.pytest" in pyproject or (here / "pytest.ini").is_file() or (here / "tests").is_dir(),
    }
    lint = "python3 -m ruff check ." if configured["ruff"] else "python3 -m flake8 ." if configured["flake8"] else None
    typecheck = "python3 -m mypy ." if configured["mypy"] else "pyright ." if configured["pyright"] else None
    match = re.search(r'requires-python\s*=\s*"[^\d]*([\d.]+)', pyproject)
    version = first_line(here / ".python-version") or (match.group(1) if match else "")
    return Detected(
        "python", "python", prefixed(directory, evidence),
        complete(
            install=in_dir(
                directory,
                "python3 -m pip install -r requirements.txt" if requirements else "python3 -m pip install -e .",
            ),
            typecheck=in_dir(directory, typecheck) if typecheck else None,
            lint=in_dir(directory, lint) if lint else None,
            test=in_dir(directory, "python3 -m pytest") if configured["pytest"] else None,
            audit=in_dir(directory, "pip-audit -r requirements.txt") if requirements else None,
        ),
        {"kind": "python", "version": version},
    )


def go(root: Path, directory: str) -> Detected | None:
    module = root / directory / "go.mod"
    if not module.is_file():
        return None
    match = re.search(r"^go\s+([\d.]+)", read(module), re.M)
    return Detected(
        "go", "go", prefixed(directory, "go.mod"),
        complete(
            install=in_dir(directory, "go mod download"),
            typecheck=in_dir(directory, "go build ./..."),
            lint=in_dir(directory, "go vet ./..."),
            test=in_dir(directory, "go test ./..."),
        ),
        {"kind": "go", "version": match.group(1) if match else ""},
    )


def java_version(here: Path, build: str) -> str:
    for pattern in (
        r"<maven\.compiler\.release>\s*(\d+)", r"<maven\.compiler\.source>\s*(?:1\.)?(\d+)",
        r"<java\.version>\s*(?:1\.)?(\d+)", r"<release>\s*(\d+)\s*</release>",
        r"JavaLanguageVersion\.of\((\d+)\)", r"sourceCompatibility\s*=\s*['\"]?(?:1\.)?(\d+)",
        r"(?m)^javac\.source\s*=\s*(?:1\.)?(\d+)", r"<javac\b[^>]*\bsource=\"(?:1\.)?(\d+)\"",
    ):
        match = re.search(pattern, build)
        if match:
            return match.group(1)
    return first_line(here / ".java-version").removeprefix("1.").split(".")[0]


def maven(root: Path, directory: str) -> Detected | None:
    here = root / directory
    pom = here / "pom.xml"
    if not pom.is_file():
        return None
    text = read(pom)
    # Through the wrapper whether or not it is there yet: `adopt` writes it where it is missing (`wrappers.py`),
    # so the recorded commands need a JDK and nothing else on the machine that runs them.
    mvn = in_dir(directory, "./mvnw -B -q")
    packaging = re.search(r"<packaging>\s*(\w+)\s*</packaging>", text)
    return Detected(
        "maven", "java", prefixed(directory, "pom.xml"),
        complete(
            install=f"{mvn} -DskipTests dependency:resolve",
            typecheck=f"{mvn} -DskipTests test-compile",
            lint=f"{mvn} -DskipTests checkstyle:check" if "maven-checkstyle-plugin" in text else None,
            test=f"{mvn} test",
            integration=f"{mvn} failsafe:integration-test failsafe:verify" if "maven-failsafe-plugin" in text else None,
            # The recipe every generated Java service runs, proposed only where the pom declares JUnit 5: Surefire's
            # `groups` is a Jupiter tag there, and a JUnit 4 provider would read it as a Category class and fail on
            # the name. Three wrapped Maven builds recorded `null` here while the factory knew the recipe all along.
            adversarial=(f"{mvn} test -Dgroups=adversarial -DfailIfNoTests=false"
                         if "junit-jupiter" in text or "junit-bom" in text else None),
            audit=f"{mvn} dependency-check:check" if "dependency-check-maven" in text else None,
        ),
        {"kind": "java", "version": java_version(here, text)},
        packaging.group(1) if packaging and packaging.group(1) != "jar" else None,
    )


def gradle(root: Path, directory: str) -> Detected | None:
    here = root / directory
    build = next((f for f in ("build.gradle.kts", "build.gradle") if (here / f).is_file()), None)
    if build is None:
        return None
    text = read(here / build)
    tool = in_dir(directory, "./gradlew -q")  # through the wrapper, for the reason `maven` gives
    kotlin = "kotlin(" in text or 'id("org.jetbrains.kotlin' in text or (here / "src/main/kotlin").is_dir()
    return Detected(
        "gradle", "kotlin" if kotlin else "java", prefixed(directory, build),
        complete(
            install=f"{tool} dependencies",
            typecheck=f"{tool} testClasses",
            lint=f"{tool} checkstyleMain" if "checkstyle" in text else None,
            test=f"{tool} test",
        ),
        {"kind": "java", "version": java_version(here, text)},
    )


def ant(root: Path, directory: str) -> Detected | None:
    """An Ant build — NetBeans' `build.xml` importing `nbproject/build-impl.xml`, or a hand-written one. Recognised
    so the tree is read and not refused, and recorded as what it is: `ant <target>` for the targets it defines, no
    `install` because the jars are committed, and `packaging: war` for a NetBeans web project. It has no wrapper,
    so the machine that runs the gate needs Ant; the programme's first step (`programme.py`) is to move the build
    to Maven or Gradle, which is the least the method holds a repository to."""
    here = root / directory
    build = here / "build.xml"
    if not build.is_file():
        return None
    text = read(build)
    imported = "".join(read(here / f) for f in re.findall(r'<import\s+file="([^"$]+)"', text))
    properties = read(here / "nbproject/project.properties")
    targets = {name for name in re.findall(r'<target\s[^>]*?\bname="([^"]+)"', text + imported)
               if not name.startswith("-")}
    test_dir = re.search(r"^test\.src\.dir\s*=\s*(.+)$", properties, re.M)
    tests = (here / (test_dir.group(1).strip() if test_dir else "test")).is_dir()
    project = read(here / "nbproject/project.xml")
    run = in_dir(directory, "ant -q")
    return Detected(
        "ant", "java", prefixed(directory, "build.xml"),
        complete(
            install=f"{run} resolve" if "resolve" in targets and (here / "ivy.xml").is_file() else None,
            typecheck=f"{run} compile" if "compile" in targets else None,
            lint=f"{run} checkstyle" if "checkstyle" in targets else None,
            test=f"{run} test" if "test" in targets and tests else None,
            audit=f"{run} dependency-check" if "dependency-check" in targets else None,
        ),
        {"kind": "java", "version": java_version(here, properties + text + imported)},
        "war" if "web.project" in project or re.search(r"<war\b", text + imported) else None,
    )


def dotnet(root: Path, directory: str) -> Detected | None:
    here = root / directory
    projects = sorted(here.glob("*.sln")) or sorted(here.glob("*.csproj")) or sorted(here.glob("*.fsproj"))
    if not projects:
        return None
    project = prefixed(directory, projects[0].name)
    sdk = re.search(r'"version"\s*:\s*"([\d.]+)"', read(here / "global.json"))
    project_file = read(projects[0]) if projects[0].suffix != ".sln" else ""
    framework = re.search(r"<TargetFrameworks?>\s*net([\d.]+)", project_file)
    return Detected(
        "dotnet", "fsharp" if projects[0].suffix == ".fsproj" else "csharp", project,
        complete(
            install=f"dotnet restore {project}",
            typecheck=f"dotnet build {project} --no-restore",
            lint=f"dotnet format {project} --verify-no-changes",
            test=f"dotnet test {project} --no-build",
            audit=f"dotnet list {project} package --vulnerable",
        ),
        {"kind": "dotnet", "version": sdk.group(1) if sdk else framework.group(1) if framework else ""},
    )


def php(root: Path, directory: str) -> Detected | None:
    here = root / directory
    composer = here / "composer.json"
    if not composer.is_file():
        return None
    text = read(composer)
    match = re.search(r'"php"\s*:\s*"[^\d]*([\d.]+)', text)
    phpunit = any((here / f).is_file() for f in ("phpunit.xml", "phpunit.xml.dist"))
    working = "" if directory == "." else f" --working-dir={directory}"
    return Detected(
        "php", "php", prefixed(directory, "composer.json"),
        complete(
            install=f"composer install --no-interaction{working}",
            lint=in_dir(directory, "vendor/bin/phpstan analyse") if (here / "phpstan.neon").is_file() else None,
            test=in_dir(directory, "vendor/bin/phpunit") if phpunit else None,
            audit=f"composer audit{working}",
        ),
        {"kind": "php", "version": match.group(1) if match else ""},
    )


def ruby(root: Path, directory: str) -> Detected | None:
    here = root / directory
    if not (here / "Gemfile").is_file():
        return None
    test = (
        "bundle exec rspec" if (here / "spec").is_dir()
        else "bundle exec rake test" if (here / "Rakefile").is_file() and (here / "test").is_dir()
        else None
    )
    return Detected(
        "ruby", "ruby", prefixed(directory, "Gemfile"),
        complete(
            install=in_dir(directory, "bundle install"),
            lint=in_dir(directory, "bundle exec rubocop") if (here / ".rubocop.yml").is_file() else None,
            test=in_dir(directory, test) if test else None,
        ),
        {"kind": "ruby", "version": first_line(here / ".ruby-version")},
    )


# In the order tried, so a directory with a `package.json` beside a `pyproject.toml` is reported once, as Node,
# and a `pom.xml` beside a leftover `build.xml` as Maven; the survey says which file decided it.
ECOSYSTEMS: tuple[Callable[[Path, str], Detected | None], ...] = (
    node, python, go, maven, gradle, ant, dotnet, php, ruby,
)


def aggregates(root: Path, found: Detected) -> bool:
    """Whether this build owns the builds below it — npm workspaces, Maven modules, a Gradle settings file,
    a .NET solution — so that a manifest under it is a module of it and not a root of its own."""
    here = root / found.evidence
    directory = here.parent
    if found.ecosystem == "node":
        return '"workspaces"' in read(here)
    if found.ecosystem == "maven":
        return "<modules>" in read(here)
    if found.ecosystem == "gradle":
        return any((directory / f).is_file() for f in ("settings.gradle", "settings.gradle.kts"))
    return found.ecosystem == "dotnet" and here.suffix == ".sln"
