"""The architecture view of a repository the method was installed around: where anything starts, what the code is
made of, what it declares it depends on, where change happens, and — where CodeGraph has indexed it — what
depends on what.

Brownfield adoption (experimental as `AGENTS.md` defines the word). `survey.py` reads what a repository is
delivered with; this reads what it is shaped like, for the two decisions that need the shape: which rung of the
Structure axis the map can claim next, and where `/strangle` cuts. Everything is read, nothing inferred: a file is
an entry point because a manifest or its own name says so, a hotspot because commits touched it, an edge because
CodeGraph's index holds it. The graph is read from `.codegraph/codegraph.db` — the SQLite database `codegraph
init` writes, whose `nodes`, `edges` and `files` tables are its `--json` output — and a tree with no index says so.
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .ecosystems import read
from .services import App, wrapped_of
from .survey import SKIPPED

HISTORY = 2000
TOP = 8
GRAPH_DB = ".codegraph/codegraph.db"
# The edge kinds that make one file depend on another; `contains` is a file's own outline.
DEPENDS = ("calls", "imports", "references", "instantiates")
LANGUAGES = {
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".py": "python", ".go": "go", ".java": "java", ".kt": "kotlin", ".cs": "c#", ".php": "php",
    ".rb": "ruby", ".sql": "sql", ".html": "html", ".css": "css", ".scss": "css", ".yml": "yaml", ".yaml": "yaml",
    ".json": "json", ".md": "markdown", ".xml": "xml", ".sh": "shell",
}
RUNS_AT_IMPORT = ("manage.py", "app.py", "main.py", "__main__.py", "wsgi.py", "asgi.py", "server.py")


@dataclass(frozen=True)
class EntryPoint:
    """Where something starts: what the file says it is, the file, and what it runs where the file spells that out."""

    what: str
    path: str
    runs: str = ""


@dataclass(frozen=True)
class Module:
    path: str
    files: int
    languages: str


@dataclass(frozen=True)
class Graph:
    """What CodeGraph's index holds, or why nothing was read from it."""

    present: bool
    note: str
    files: int = 0
    nodes: int = 0
    edges: int = 0
    version: str = ""
    # Per file: how many other files call, import or reference it; how many other files it does that to.
    dependants: dict[str, int] | None = None
    dependencies: dict[str, int] | None = None


@dataclass(frozen=True)
class AppStructure:
    name: str
    path: str
    entry_points: tuple[EntryPoint, ...]
    modules: tuple[Module, ...]
    dependencies: tuple[str, ...]
    manifest: str
    commits: int
    hotspots: tuple[tuple[str, int], ...]
    depended_on: tuple[tuple[str, int], ...]
    depending: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class Structure:
    apps: tuple[AppStructure, ...]
    commits: int
    authors: int
    since: str
    graph: Graph


def under(path: str, directory: str) -> bool:
    return directory == "." or path == directory or path.startswith(f"{directory}/")


def prefixed(directory: str, path: str) -> str:
    return path if directory == "." else f"{directory}/{path}"


def code_files(here: Path, depth: int = 4) -> list[Path]:
    """Every file under `here` to `depth`, skipping what a build writes and a package manager fetches."""
    found: list[Path] = []
    frontier = [(here, 0)]
    while frontier:
        directory, level = frontier.pop()
        try:
            children = sorted(directory.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_file():
                found.append(child)
            elif level < depth and child.name not in SKIPPED and not child.name.startswith("."):
                frontier.append((child, level + 1))
    return found


def entry_points(root: Path, directory: str, ecosystem: str) -> tuple[EntryPoint, ...]:
    """Every place a file says something starts, by ecosystem, plus what a container or Procfile runs."""
    here = root if directory == "." else root / directory
    found: list[EntryPoint] = []
    if ecosystem == "node":
        try:
            package = json.loads(read(here / "package.json"))
        except ValueError:
            package = {}
        package = package if isinstance(package, dict) else {}
        start = (package.get("scripts") or {}).get("start")
        if start:
            found.append(EntryPoint("`npm start`", prefixed(directory, "package.json"), start))
        bins = package.get("bin") or {}
        for name, path in (bins.items() if isinstance(bins, dict) else [(package.get("name", "bin"), bins)]):
            found.append(EntryPoint(f"command `{name}`", prefixed(directory, str(path))))
        if package.get("main") and not start and not bins:
            found.append(EntryPoint("module entry (`main`)", prefixed(directory, str(package["main"]))))
    if ecosystem == "python":
        scripts = re.search(r"\[project\.scripts\]\n((?:[^\[\n][^\n]*\n?)*)", read(here / "pyproject.toml"))
        for line in (scripts.group(1).splitlines() if scripts else []):
            if "=" in line:
                name, target = (part.strip().strip('"') for part in line.split("=", 1))
                found.append(EntryPoint(f"console script `{name}`", prefixed(directory, "pyproject.toml"), target))
        for path in code_files(here, 2):
            if path.name in RUNS_AT_IMPORT:
                found.append(EntryPoint("runs when executed", path.relative_to(root).as_posix()))
    if ecosystem == "go":
        for path in [here / "main.go", *sorted(here.glob("cmd/*/main.go"))]:
            if path.is_file():
                found.append(EntryPoint("main package", path.relative_to(root).as_posix()))
    if ecosystem == "dotnet":
        for path in code_files(here, 2):
            if path.name == "Program.cs":
                found.append(EntryPoint("program", path.relative_to(root).as_posix()))
            elif path.suffix in (".csproj", ".fsproj") and "Microsoft.NET.Sdk.Web" in read(path):
                found.append(EntryPoint("web application", path.relative_to(root).as_posix()))
    if ecosystem in ("maven", "gradle"):
        for path in code_files(here / "src/main", 6):
            if re.search(r"(Application|Main)\.(java|kt)$", path.name) or path.name == "web.xml":
                found.append(EntryPoint("application class" if path.suffix != ".xml" else "servlet descriptor",
                                        path.relative_to(root).as_posix()))
    if ecosystem in ("php", "ruby"):
        for name in ("public/index.php", "index.php", "artisan", "config.ru", "bin/rails"):
            if (here / name).is_file():
                found.append(EntryPoint("runs when executed", prefixed(directory, name)))
    for name in ("Dockerfile", "Containerfile"):
        for line in read(here / name).splitlines():
            if re.match(r"\s*(ENTRYPOINT|CMD)\b", line):
                found.append(EntryPoint("container runs", prefixed(directory, name), line.strip()))
    for line in read(here / "Procfile").splitlines():
        if ":" in line:
            process, command = line.split(":", 1)
            found.append(EntryPoint(f"process `{process.strip()}`", prefixed(directory, "Procfile"), command.strip()))
    return tuple(found)


def modules(root: Path, directory: str) -> tuple[Module, ...]:
    """The top-level directories of an application, with how many files each holds and in what."""
    here = root if directory == "." else root / directory
    found = []
    try:
        children = sorted(child for child in here.iterdir() if child.is_dir())
    except OSError:
        children = []
    for child in children:
        if child.name in SKIPPED or child.name.startswith("."):
            continue
        files = code_files(child)
        if not files:
            continue
        counted = Counter(LANGUAGES.get(path.suffix, "") for path in files)
        counted.pop("", None)
        languages = ", ".join(language for language, _ in counted.most_common(2)) or "other"
        found.append(Module(prefixed(directory, child.name) + "/", len(files), languages))
    return tuple(found)


def dependencies(root: Path, directory: str, ecosystem: str) -> tuple[tuple[str, ...], str]:
    """What the application's manifest declares it depends on, and the manifest."""
    here = root if directory == "." else root / directory
    if ecosystem == "node":
        try:
            package = json.loads(read(here / "package.json"))
        except ValueError:
            package = {}
        deps = package.get("dependencies") if isinstance(package, dict) else None
        return tuple(sorted(deps or {})), "package.json"
    if ecosystem == "python":
        text = read(here / "pyproject.toml")
        block = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.S | re.M)
        if block:
            names = re.findall(r'"\s*([A-Za-z0-9_.-]+)', block.group(1))
            return tuple(dict.fromkeys(n.lower() for n in names)), "pyproject.toml"
        lines = [line.strip() for line in read(here / "requirements.txt").splitlines()]
        pinned = [re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0] for line in lines if line and line[0] not in "#-"]
        return tuple(dict.fromkeys(n.lower() for n in pinned if n)), "requirements.txt"
    if ecosystem == "go":
        text = read(here / "go.mod")
        requires = "\n".join(re.findall(r"require\s*\((.*?)\)", text, re.S)) + "\n" + text
        modules_ = re.findall(r"^\s*(?:require\s+)?([\w.-]+\.[\w./-]+)\s+v[\w.+-]+(.*)$", requires, re.M)
        return tuple(dict.fromkeys(m for m, rest in modules_ if "indirect" not in rest)), "go.mod"
    if ecosystem == "dotnet":
        projects = sorted(here.glob("*.*proj"))
        packages = [n for path in projects for n in re.findall(r'<PackageReference\s+Include="([^"]+)"', read(path))]
        return tuple(dict.fromkeys(packages)), projects[0].name if projects else ""
    if ecosystem == "maven":
        text = read(here / "pom.xml")
        artifacts = re.findall(r"<dependency>.*?<artifactId>\s*([^<\s]+)\s*</artifactId>", text, re.S)
        return tuple(dict.fromkeys(artifacts)), "pom.xml"
    if ecosystem == "gradle":
        build = "build.gradle.kts" if (here / "build.gradle.kts").is_file() else "build.gradle"
        coordinates = re.findall(r"""(?:implementation|api|compileOnly|runtimeOnly)\s*\(?\s*['"]([^'":]+:[^'":]+)""",
                                 read(here / build))
        return tuple(dict.fromkeys(coordinates)), build
    if ecosystem == "php":
        try:
            composer = json.loads(read(here / "composer.json"))
        except ValueError:
            composer = {}
        required = [n for n in (composer.get("require") or {}) if n != "php" and not n.startswith("ext-")]
        return tuple(sorted(required)), "composer.json"
    if ecosystem == "ruby":
        return tuple(dict.fromkeys(re.findall(r"""^\s*gem\s+['"]([^'"]+)""", read(here / "Gemfile"), re.M))), "Gemfile"
    return (), ""


def before_the_method(root: Path, factory: str) -> str:
    """Where the repository's history ends: the parent of the factory's first commit, or `HEAD` before one exists —
    so the view is the same on every `/survey`, where the last N from `HEAD` moved with every commit anybody made."""
    def git(*arguments: str) -> str:
        run = subprocess.run(["git", *arguments], cwd=root, text=True, capture_output=True, check=False)
        return run.stdout.strip() if run.returncode == 0 else ""

    oldest = git("rev-list", "--reverse", f"--author={factory}", "HEAD").split()[:1] if factory else []
    return (git("rev-parse", "--verify", "-q", f"{oldest[0]}^") if oldest else "") or "HEAD"


def history(root: Path, ignoring: str = "") -> tuple[list[list[str]], set[str], str]:
    """The commits before the method arrived — files, authors, oldest date — or nothing where there is no history."""
    until = before_the_method(root, ignoring)
    result = subprocess.run(
        ["git", "log", f"-n{HISTORY}", "--format=%x1e%an%x1f%ae%x1f%as", "--name-only", until],
        cwd=root, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        return [], set(), ""
    commits, authors, since = [], set(), ""
    for record in result.stdout.split("\x1e")[1:]:
        head, _, body = record.partition("\n")
        author, email, date = (head.split("\x1f") + ["", ""])[:3]
        if ignoring and email == ignoring:
            continue
        authors.add(author)
        since = date or since
        commits.append([line for line in body.splitlines() if line])
    return commits, authors, since


def graph(root: Path) -> Graph:
    """What CodeGraph's index says, read straight from its database, file by file."""
    database = root / GRAPH_DB
    if not database.is_file():
        return Graph(False, "not indexed: `./init --extension codegraph` builds the index, then `/survey` reads it")
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            files, nodes, edges = (connection.execute(f"select count(*) from {t}").fetchone()[0]
                                   for t in ("files", "nodes", "edges"))
            version = connection.execute(
                "select value from project_metadata where key = 'indexed_with_version'"
            ).fetchone()
            placeholders = ", ".join("?" for _ in DEPENDS)
            pairs = connection.execute(
                f"select distinct s.file_path, t.file_path from edges e join nodes s on s.id = e.source "
                f"join nodes t on t.id = e.target where e.kind in ({placeholders}) and s.file_path != t.file_path",
                DEPENDS,
            ).fetchall()
        finally:
            connection.close()
    except sqlite3.Error as error:
        return Graph(False, f"`{GRAPH_DB}` could not be read as CodeGraph's schema ({error}); `codegraph index --force`"
                     " rebuilds it")
    dependants: Counter[str] = Counter(target for _, target in pairs)
    depending: Counter[str] = Counter(source for source, _ in pairs)
    return Graph(True, f"CodeGraph {version[0] if version else 'index'}, `{GRAPH_DB}`", files, nodes, edges,
                 version[0] if version else "", dict(dependants), dict(depending))


# The method's own bookkeeping, which the loop touches on every slice: the record, the agent guidance and Spec Kit's
# specifications. Counted, they were the first real adoption's top hotspots, ahead of any of its code.
METHOD_FILES = frozenset({"project.json", "AGENTS.md", "CLAUDE.md"})
METHOD_DIRECTORIES = frozenset({"specs"})


def owned(path: str, directory: str, skipped: tuple[str, ...]) -> bool:
    """Whether a file is this application's: under its directory and not under a skipped one, not what a build
    writes, not a dot-directory's, and not the method's own bookkeeping."""
    return (under(path, directory) and not any(under(path, skip) for skip in skipped)
            and path.split("/", 1)[0] not in SKIPPED | METHOD_DIRECTORIES and not path.startswith(".")
            and path not in METHOD_FILES)


def top(counts: dict[str, int] | None, directory: str, skipped: tuple[str, ...]) -> tuple[tuple[str, int], ...]:
    """The most-counted paths this application owns."""
    kept = {path: count for path, count in (counts or {}).items() if owned(path, directory, skipped)}
    return tuple(sorted(kept.items(), key=lambda item: (-item[1], item[0]))[:TOP])


def structure(root: Path, apps: list[App], delivery: str = ".", ignoring: str = "") -> Structure:
    """The architecture view of every application that existed before the method did; `ignoring` is the author
    whose commits are the factory's rather than the repository's."""
    commits, authors, since = history(root, ignoring)
    found = graph(root)
    wrapped = wrapped_of(apps)
    views = []
    for app in wrapped:
        ecosystem = (app.toolchain or {}).get("ecosystem", "")
        # An application at the root is everything the other wrapped applications are not; the factory's own
        # directory is nobody's.
        skipped = tuple(other.path for other in wrapped if other.path not in (".", app.path))
        skipped += (delivery,) if delivery != "." else ()
        touched = Counter(path for files in commits for path in files if owned(path, app.path, skipped))
        theirs = [files for files in commits if any(owned(path, app.path, skipped) for path in files)]
        declared, manifest = dependencies(root, app.path, ecosystem)
        views.append(AppStructure(
            app.name, app.path, entry_points(root, app.path, ecosystem), modules(root, app.path), declared, manifest,
            len(theirs), top(dict(touched), app.path, skipped), top(found.dependants, app.path, skipped),
            top(found.dependencies, app.path, skipped),
        ))
    return Structure(tuple(views), len(commits), len(authors), since, found)
