"""Big issues that are quick wins: what the survey can see in a tree that is cheap to fix and expensive to leave.

Brownfield adoption (experimental as `AGENTS.md` defines the word). The second real adoption carried a
third-party API key as a string literal in a Java source file, an in-memory `admin` password in a Spring Security
XML, and an IDE's whole `.idea/` directory under version control, and the method said nothing about any of it
while it talked about ladders. This module reads for the handful of things that are both — a secret in the tree,
IDE and build output tracked, a dependency repository fetched over plain HTTP, a lockfile the package manager
would have written but nobody committed, a binary archive tracked — and says each with the file that shows it and
the fix, never the value: a secret's value is not written anywhere by this factory, and the fix for one begins
with rotating it, because a key in history is public.

Each finding is a proposal and nothing is changed: the adoption's report lists them, `survey/survey.md` carries
them under *Big issues that are quick wins*, and `/drive`'s Convergence stage offers them ahead of the map's rows
while any remain. `/survey` reads the tree again, so a finding disappears when the tree stops showing it — that is
how they are tracked, without a ledger to tick.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .ecosystems import read

KINDS = ("secret-in-tree", "ide-or-build-output-tracked", "insecure-dependency-source", "no-lockfile",
         "archive-tracked")
CONFIG_SUFFIXES = {".xml", ".properties", ".yml", ".yaml", ".json", ".env", ".ini", ".cfg", ".conf", ".toml"}
SOURCE_SUFFIXES = {".java", ".py", ".js", ".ts", ".go", ".cs", ".rb", ".php", ".kt", ".scala", ".sh"}
# `password=...`, `api_key: "..."`, `secret = '...'`, `<... password="...">` — the key names a credential, and the
# value is a literal rather than a placeholder or a read from the environment.
KEYED = re.compile(r"""(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?key|auth[_-]?token|token)\b\s*[:=]\s*
                       (?:["']([^"'\s]{4,})["']|([^\s"'<>;,]{4,}))""", re.X)
# Spring's bean XML names the key in one attribute and the value in the next — `<property name="password"
# value="…"/>`, or a `<value>` child — so `KEYED`, which wants `key = value`, walked past it and gave a false
# all-clear on the one file the second real adoption most needed read.
PROPERTY = re.compile(r"""(?i)<property\s+name=["']
                          (password|passwd|pwd|secret|api[_-]?key|access[_-]?key|auth[_-]?token|token)["']
                          \s*(?:value=["']([^"']{4,})["']|>\s*<value>\s*([^<\s]{4,})\s*</value>)""", re.X)
PLACEHOLDER = re.compile(r"^(\$\{|\{\{|%\(|<|\$[A-Z_]|\*+$|x+$|change|your|example|dummy|placeholder|none$|null$|"
                         r"true$|false$|env|os\.|process\.|System\.|getenv|config\.|settings\.|\w+\.\w+\()", re.I)
# Shapes a real secret has whatever it is called.
SHAPES = (
    ("SendGrid key", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Stripe live key", re.compile(r"\bsk_live_[0-9a-zA-Z]{16,}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY")),
    ("connection string with a password", re.compile(r"(?i)\b\w+://[^\s/:@]+:[^\s/@]{4,}@[^\s/]+")),
)
TRACKED_NOISE = (
    (".idea/", "IntelliJ's `.idea/`"), (".iml", "an IntelliJ `.iml`"), (".DS_Store", "`.DS_Store`"),
    ("Thumbs.db", "`Thumbs.db`"), ("node_modules/", "`node_modules/`"), ("target/", "Maven's `target/`"),
    ("__pycache__/", "`__pycache__/`"), (".class", "compiled `.class` files"), (".pyc", "compiled `.pyc` files"),
)
ARCHIVES = {".jar", ".war", ".ear", ".zip", ".tar", ".gz", ".tgz", ".7z", ".dll", ".exe", ".so", ".dylib"}
LOCKFILES = {
    "package.json": ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock"),
    "Gemfile": ("Gemfile.lock",), "composer.json": ("composer.lock",), "Cargo.toml": ("Cargo.lock",),
}
MAX_TEXT = 512 * 1024


@dataclass(frozen=True)
class Finding:
    kind: str
    where: str
    what: str
    fix: str

    def record(self) -> dict:
        return asdict(self)


def tracked(root: Path) -> list[str]:
    """What Git tracks, relative and posix — the tree as it will be cloned, ignored files left out."""
    if not (root / ".git").exists():
        return []
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=False)
    return [p.decode("utf-8", "replace") for p in result.stdout.split(b"\0") if p] if result.returncode == 0 else []


def literal(value: str | None, key: str = "", in_config: bool = False) -> bool:
    """Whether the value is a credential written down rather than a placeholder or a reference: in a configuration
    file any word that is not the key's own name (`password="pass"`), in source only what is not an identifier."""
    if not value or PLACEHOLDER.search(value):
        return False
    return value.lower() != key.lower() if in_config else not value.isidentifier()


def secrets_in(root: Path, paths: list[str], written: set[str]) -> list[Finding]:
    """A credential written down: a keyed literal in a configuration file, a keyed quoted literal with a digit in a
    source file, or a value shaped like a known kind of key anywhere. The value is never repeated."""
    found = []
    for relative in paths:
        path = root / relative
        suffix = path.suffix.lower()
        name = path.name.lower()
        is_config = suffix in CONFIG_SUFFIXES or name.startswith(".env")
        if relative in written or not (is_config or suffix in SOURCE_SUFFIXES) or path.stat().st_size > MAX_TEXT:
            continue
        if relative.endswith((".lock", "-lock.json")) or name in ("mvnw", "gradlew", "package-lock.json"):
            continue
        for number, line in enumerate(read(path).splitlines(), start=1):
            shaped = next((label for label, pattern in SHAPES if pattern.search(line)), None)
            if shaped:
                found.append(Finding(
                    "secret-in-tree", f"{relative}:{number}", f"a {shaped} is written in the file",
                    "rotate it now — a key in Git history is public — then read it from the environment or a secret "
                    "store and purge the history (`git filter-repo`)",
                ))
                break
            match = KEYED.search(line) or (PROPERTY.search(line) if is_config else None)
            if not match:
                continue
            quoted, bare = match.group(2), match.group(3)
            if match.re is PROPERTY:
                # Either form of the property is a written value in a configuration file: a quoted literal.
                quoted, bare = match.group(2) or match.group(3), None
            value = quoted or bare
            if (is_config and literal(value, match.group(1), True)) or (
                quoted and literal(quoted) and len(quoted) >= 8 and any(c.isdigit() for c in quoted)
            ):
                found.append(Finding(
                    "secret-in-tree", f"{relative}:{number}", f"`{match.group(1)}` has a literal value in the file",
                    "rotate it, read it from the environment or a secret store, and purge the history "
                    "(`git filter-repo`); an in-memory user in a security config is a credential too",
                ))
                break
    return found


def noise_tracked(paths: list[str]) -> list[Finding]:
    found = []
    for needle, what in TRACKED_NOISE:
        hits = [p for p in paths if (f"/{needle}" in f"/{p}" if needle.endswith("/") else p.endswith(needle))]
        if hits:
            found.append(Finding(
                "ide-or-build-output-tracked", hits[0] + (f" (+{len(hits) - 1} more)" if len(hits) > 1 else ""),
                f"{what} is under version control", "add it to `.gitignore` and `git rm -r --cached` it; every "
                "clone and every diff carries it otherwise",
            ))
    return found


def insecure_sources(root: Path, paths: list[str]) -> list[Finding]:
    found = []
    for relative in paths:
        name = Path(relative).name
        sources = ("pom.xml", ".npmrc", "build.gradle", "build.gradle.kts", "settings.xml", "requirements.txt",
                   "pip.conf", "Gemfile")
        text = read(root / relative) if name in sources else ""
        if not text:
            continue
        hit = None
        if name in ("pom.xml", "settings.xml"):
            blocks = re.findall(r"<(?:plugin)?[rR]epository>(.*?)</(?:plugin)?[rR]epository>", text, re.S)
            hit = next((b for b in blocks if re.search(r"<url>\s*http://", b)), None)
        elif re.search(r"(?m)^\s*(registry\s*=\s*|--index-url\s+|--extra-index-url\s+|index-url\s*=\s*|source\s+['\"])http://"
                       r"|maven\s*\{[^}]*url\s*[=(]?\s*['\"]http://", text):
            hit = "yes"
        if hit:
            found.append(Finding(
                "insecure-dependency-source", relative, "a dependency repository is fetched over plain HTTP",
                "change the URL to `https://`; an HTTP source lets anyone on the path hand the build a different "
                "artifact",
            ))
    return found


def missing_lockfiles(root: Path, paths: list[str]) -> list[Finding]:
    found = []
    for relative in paths:
        path = Path(relative)
        locks = LOCKFILES.get(path.name)
        if not locks or any(str(path.with_name(lock)) in paths for lock in locks):
            continue
        found.append(Finding(
            "no-lockfile", relative, f"no lockfile beside `{path.name}` ({' / '.join(locks[:2])})",
            "install once and commit the lockfile the package manager writes; without it every build resolves "
            "versions afresh and no two are the same",
        ))
    return found


def archives_tracked(paths: list[str]) -> list[Finding]:
    # A jar at or under an Ant build is that build's classpath — the only way Ant declares a dependency — and not
    # an archive tracked by mistake: the programme's build step (Maven or Gradle) is where those go, all at once.
    ant_roots = [p[: -len("build.xml")] for p in paths if p == "build.xml" or p.endswith("/build.xml")]
    hits = [p for p in paths if Path(p).suffix.lower() in ARCHIVES and not p.endswith("gradle-wrapper.jar")
            and not (p.endswith(".jar") and any(p.startswith(prefix) for prefix in ant_roots))]
    if not hits:
        return []
    return [Finding(
        "archive-tracked", hits[0] + (f" (+{len(hits) - 1} more)" if len(hits) > 1 else ""),
        f"{len(hits)} binary archive(s) under version control",
        "declare them as dependencies the build fetches, or keep them in Git LFS; a binary in history is there "
        "for good and cannot be reviewed",
    )]


def quick_wins(root: Path, paths: list[str], written: set[str], delivery: str = ".") -> list[Finding]:
    """Everything above, over what Git tracks — or over `paths`, the survey's own listing, where there is no Git —
    leaving out what the factory wrote (`written`) and the delivery directory, which are not theirs."""
    listed = tracked(root) or paths
    theirs = [p for p in listed if p not in written and not (delivery != "." and p.startswith(f"{delivery}/"))
              and not p.startswith((".specify/", "specs/"))]
    return [
        *secrets_in(root, theirs, written), *noise_tracked(theirs), *insecure_sources(root, theirs),
        *missing_lockfiles(root, theirs), *archives_tracked(theirs),
    ]
