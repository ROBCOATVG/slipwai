"""What the applications run on, and whether it is still supported: the Platform axis of the convergence map.

Brownfield adoption (experimental as `AGENTS.md` defines the word). The first real adoption ran Spring 3.2.8,
JUnit 3.8.1 and a `javax.servlet` 2.4 API under Tomcat 8.5, and nothing the factory wrote said so: the survey read
dependency names without versions, and the strategy recommendation read only the prose in `why`. An agent
asked over that tree what test framework to add proposed JUnit 4. This module reads the versions the tree pins —
the runtime from the application's record, frameworks from its manifest, images from its `Dockerfile` — and dates
each against a shipped table of support cycles (`assets/adoption/support.json`, a snapshot of endoflife.date with
JUnit and the servlet API kept by hand), so that `survey/structure.md` can say *Spring Framework 3.2.8 left support
on 2016-12-31* offline, the map's Platform row can stand where the facts put it, the recommendation can put *the
platform in support* before any strategy, and each expired product comes with the option the essay names for it.

The rule every other fact follows holds here: nothing is inferred. A version the tree does not pin is not read; a
version the table has no cycle for is `unknown`, written as *not in the support table* and never guessed at. The
table is dated, and `/survey` re-dates every product against the day it runs, so a runtime that leaves support
while the work goes on moves the row down by itself — which is how these things stay tracked rather than found
once. The factory never bumps a version: the option is offered as a method slice, and a person decides.
"""
from __future__ import annotations

import dataclasses
import datetime
import json
import re
from pathlib import Path

from .assets import ADOPTION_ROOT
from .ecosystems import read
from .origin import Adoption
from .services import App, wrapped_of

SUPPORT_TABLE = ADOPTION_ROOT / "support.json"
ENDING_SOON = datetime.timedelta(days=180)
STATUSES = ("supported", "ending", "end-of-life", "unknown")
# The Docker images whose tag names a product's version: `tomcat:8.5-jdk8`, `eclipse-temurin:17-jre`,
# `mcr.microsoft.com/dotnet/aspnet:8.0`. The repository at the end of the image name decides the product.
IMAGES: dict[str, str] = {
    "tomcat": "tomcat", "node": "node", "python": "python", "golang": "go", "ruby": "ruby", "php": "php",
    "eclipse-temurin": "java", "openjdk": "java", "amazoncorretto": "java", "zulu-openjdk": "java", "temurin": "java",
    "aspnet": "dotnet", "sdk": "dotnet", "runtime": "dotnet",
}
@dataclasses.dataclass(frozen=True)
class Product:
    """One thing an application runs on, as the tree pins it and the table dates it."""

    app: str
    product: str
    title: str
    version: str
    cycle: str | None
    status: str
    eol: str | None
    evidence: str

    def record(self) -> dict:
        return dataclasses.asdict(self)


def support_table() -> dict:
    return json.loads(SUPPORT_TABLE.read_text())


def numbers(version: str) -> str:
    """The dotted numbers a version string carries — `^4.18.2` → `4.18.2`, `net8.0` → `8.0`, `3.2.8.RELEASE` → `3.2.8`,
    `>= 3.9` → `3.9` — or nothing, where there are none."""
    match = re.search(r"\d+(?:\.\d+)*", version or "")
    return match.group(0) if match else ""


def cycle_of(version: str, cycles: dict) -> str | None:
    """The table's cycle the version belongs to: the longest cycle key the version's numbers start with — `3.2.8` is
    in `3.2`, `5.10.2` in `5`, `1.22.3` in `1.22` — or None where the table has none for it."""
    parts = numbers(version).split(".") if numbers(version) else []
    for length in range(len(parts), 0, -1):
        candidate = ".".join(parts[:length])
        if candidate in cycles:
            return candidate
    return None


def status_of(eol: str | None, today: datetime.date) -> str:
    if eol is None:
        return "supported"
    ends = datetime.date.fromisoformat(eol)
    if ends < today:
        return "end-of-life"
    return "ending" if ends - today <= ENDING_SOON else "supported"


def dated(app: str, product: str, version: str, evidence: str, table: dict, today: datetime.date) -> Product | None:
    """The product dated against the table, or None where the table knows no such product at all — which is not a
    fact about the application and is left unsaid; a product the table knows at a cycle it does not is `unknown`."""
    known = table["products"].get(product)
    if known is None or not numbers(version):
        return None
    cycle = cycle_of(version, known["cycles"])
    eol = known["cycles"][cycle]["eol"] if cycle else None
    status = status_of(eol, today) if cycle else "unknown"
    return Product(app, product, known["title"], numbers(version), cycle, status, eol, evidence)


# --- what each manifest pins -----------------------------------------------------------------------------------------

def maven_products(text: str) -> list[tuple[str, str]]:
    """(product, version) for what a `pom.xml` pins: the Spring Framework, Spring Boot, JUnit, the servlet API,
    Tomcat — with `${property}` versions resolved from `<properties>`."""
    properties = dict(re.findall(r"<([\w.-]+)>\s*([^<\s][^<]*?)\s*</\1>", "".join(
        re.findall(r"<properties>(.*?)</properties>", text, re.S)
    )))

    def resolve(version: str) -> str:
        for _ in range(3):
            version = re.sub(r"\$\{([\w.-]+)\}", lambda m: properties.get(m.group(1), ""), version)
        return version.strip()

    found: list[tuple[str, str]] = []
    parent = re.search(r"<parent>(.*?)</parent>", text, re.S)
    if parent and "spring-boot-starter-parent" in parent.group(1):
        version = re.search(r"<version>\s*([^<]+?)\s*</version>", parent.group(1))
        if version:
            found.append(("spring-boot", resolve(version.group(1))))
    blocks = re.findall(r"<dependency>(.*?)</dependency>", text, re.S)
    blocks += re.findall(r"<plugin>(.*?)</plugin>", text, re.S)
    for block in blocks:
        group = re.search(r"<groupId>\s*([^<]+?)\s*</groupId>", block)
        artifact = re.search(r"<artifactId>\s*([^<]+?)\s*</artifactId>", block)
        version = re.search(r"<version>\s*([^<]+?)\s*</version>", block)
        if not (group and artifact and version):
            continue
        group_id, artifact_id, pinned = group.group(1), artifact.group(1), resolve(version.group(1))
        if group_id == "org.springframework" and artifact_id.startswith("spring-"):
            found.append(("spring-framework", pinned))
        elif group_id == "org.springframework.boot" and artifact_id.startswith("spring-boot"):
            found.append(("spring-boot", pinned))
        elif (group_id == "junit" and artifact_id == "junit") or group_id.startswith("org.junit"):
            found.append(("junit", pinned))
        elif group_id in ("javax.servlet", "jakarta.servlet") and "servlet" in artifact_id:
            found.append(("servlet", pinned))
        elif group_id.startswith("org.apache.tomcat") or artifact_id.startswith("tomcat"):
            found.append(("tomcat", pinned))
    named = (("spring.version", "spring-framework"), ("spring-framework.version", "spring-framework"),
             ("spring-boot.version", "spring-boot"), ("tomcat.version", "tomcat"), ("junit.version", "junit"))
    for key, product in named:
        if key in properties and product not in {p for p, _ in found}:
            found.append((product, resolve(properties[key])))
    return first_of_each(found)


def gradle_products(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    boot = re.search(r"""id\s*\(?\s*['"]org\.springframework\.boot['"]\s*\)?\s*version\s*\(?\s*['"]([^'"]+)""", text)
    if boot:
        found.append(("spring-boot", boot.group(1)))
    for group, _artifact, version in re.findall(r"""['"]([\w.-]+):([\w.-]+):([^'":]+)['"]""", text):
        if group == "org.springframework":
            found.append(("spring-framework", version))
        elif group == "org.springframework.boot":
            found.append(("spring-boot", version))
        elif group in ("junit",) or group.startswith("org.junit"):
            found.append(("junit", version))
        elif group in ("javax.servlet", "jakarta.servlet"):
            found.append(("servlet", version))
        elif group.startswith("org.apache.tomcat"):
            found.append(("tomcat", version))
    return first_of_each(found)


def node_products(text: str) -> list[tuple[str, str]]:
    try:
        package = json.loads(text)
    except ValueError:
        return []
    if not isinstance(package, dict):
        return []
    dependencies = {**(package.get("dependencies") or {}), **(package.get("devDependencies") or {})}
    version = dependencies.get("@angular/core")
    return [("angular", str(version))] if version else []


def python_products(pyproject: str, requirements: str) -> list[tuple[str, str]]:
    found = []
    for line in re.findall(r'"([^"]+)"', "".join(re.findall(r"^dependencies\s*=\s*\[(.*?)\]", pyproject, re.S | re.M))
                           ) + requirements.splitlines():
        match = re.match(r"\s*(django)\s*([<>=~!]=?\s*[\d.]+)?", line, re.I)
        if match and match.group(2):
            found.append(("django", match.group(2)))
    return first_of_each(found)


def ruby_products(gemfile: str) -> list[tuple[str, str]]:
    match = re.search(r"""gem\s+['"]rails['"]\s*,\s*['"]([^'"]+)['"]""", gemfile)
    return [("rails", match.group(1))] if match else []


def php_products(composer: str) -> list[tuple[str, str]]:
    match = re.search(r'"laravel/framework"\s*:\s*"([^"]+)"', composer)
    return [("laravel", match.group(1))] if match else []


def image_products(dockerfile: str) -> list[tuple[str, str]]:
    """(product, version) for every `FROM` whose image the table knows: `tomcat:8.5-jdk8` → tomcat 8.5,
    `node:20-alpine` → node 20, `mcr.microsoft.com/dotnet/aspnet:8.0` → dotnet 8.0. A `FROM` with no tag, or a stage
    name, says nothing."""
    found = []
    for image in re.findall(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)", dockerfile, re.M | re.I):
        name, _, tag = image.partition(":")
        if not tag or "/" in tag:
            continue
        product = IMAGES.get(name.rsplit("/", 1)[-1])
        if product and numbers(tag) and tag[0].isdigit():
            found.append((product, tag))
    return found


def first_of_each(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for product, version in pairs:
        seen.setdefault(product, version)
    return list(seen.items())


JAR = re.compile(r"^(?P<name>[A-Za-z][\w.-]*?)-(?P<version>\d+(?:\.\d+)+(?:[.-][A-Za-z]\w*)?)(?:-bin)?\.jar$")


def jar_products(root: Path, here: Path) -> list[tuple[str, str, str]]:
    """(product, version, jar path) for the jars an Ant build commits, by their names — `spring-core-3.2.8.RELEASE.jar`,
    `junit-4.12.jar`, `servlet-api-2.5.jar` — at most two directories down and never under the build's output."""
    found: list[tuple[str, str, str]] = []
    for jar in sorted(here.rglob("*.jar")):
        relative = jar.relative_to(here)
        if len(relative.parts) > 3 or any(part in ("build", "dist", "target", ".git") for part in relative.parts):
            continue
        match = JAR.match(jar.name)
        if not match:
            continue
        name = match.group("name").lower()
        product = ("spring-boot" if name.startswith("spring-boot") else "spring-framework" if name.startswith("spring-")
                   else "junit" if name.startswith("junit") else "servlet" if "servlet-api" in name
                   else "tomcat" if name.startswith("tomcat") else None)
        if product and product not in {p for p, _, _ in found}:
            found.append((product, match.group("version"), jar.relative_to(root).as_posix()))
    return found


def manifest_products(root: Path, app: App) -> list[tuple[str, str, str]]:
    """(product, version, the file that pins it) for one application: its manifest first — or, for an Ant build, the
    jars it commits — then any Dockerfile of its own, not one under another wrapped application's directory."""
    here = root if app.path == "." else root / app.path
    ecosystem = (app.toolchain or {}).get("ecosystem", "")
    pins: list[tuple[str, str, str]] = []
    if ecosystem == "ant":
        return jar_products(root, here)
    readers = {
        "maven": ("pom.xml", lambda: maven_products(read(here / "pom.xml"))),
        "gradle": (next((f for f in ("build.gradle.kts", "build.gradle") if (here / f).is_file()), "build.gradle"),
                   lambda: gradle_products(read(here / "build.gradle.kts") + read(here / "build.gradle"))),
        "node": ("package.json", lambda: node_products(read(here / "package.json"))),
        "python": ("pyproject.toml" if (here / "pyproject.toml").is_file() else "requirements.txt",
                   lambda: python_products(read(here / "pyproject.toml"), read(here / "requirements.txt"))),
        "ruby": ("Gemfile", lambda: ruby_products(read(here / "Gemfile"))),
        "php": ("composer.json", lambda: php_products(read(here / "composer.json"))),
    }
    if ecosystem in readers:
        manifest, reader = readers[ecosystem]
        pins += [(product, version, manifest if app.path == "." else f"{app.path}/{manifest}")
                 for product, version in reader()]
    return pins


def dockerfiles(root: Path, app: App, others: list[str]) -> list[Path]:
    here = root if app.path == "." else root / app.path
    found = []
    for path in sorted(here.rglob("*Dockerfile*")):
        relative = path.relative_to(root).as_posix()
        if not path.is_file() or any(part in ("node_modules", ".git", "target", "vendor") for part in path.parts):
            continue
        if any(relative.startswith(f"{other}/") for other in others):
            continue
        if len(path.relative_to(here).parts) <= 3:
            found.append(path)
    return found


def inventory(root: Path, apps: list[App], today: datetime.date | None = None) -> dict:
    """The `platform` record: every product read from the tree for each wrapped application, dated against the table
    on `today` — the runtime from `toolchain.version` with its provenance, the frameworks from the manifest, the
    images from the Dockerfiles — with the table's snapshot date, so a reader can tell how old the dating is."""
    today = today or datetime.date.today()
    table = support_table()
    wrapped = wrapped_of(apps)
    paths = [app.path for app in wrapped if app.path != "."]
    products: list[Product] = []
    for app in wrapped:
        toolchain = app.toolchain or {}
        if toolchain.get("version"):
            found = dated(app.name, toolchain.get("kind", ""), toolchain["version"],
                          f"`toolchain.version` ({app.provenance.get('toolchain', 'detected')})", table, today)
            if found:
                products.append(found)
        for product, version, evidence in manifest_products(root, app):
            found = dated(app.name, product, version, f"`{evidence}`", table, today)
            if found:
                products.append(found)
        for dockerfile in dockerfiles(root, app, [p for p in paths if p != app.path]):
            for product, version in image_products(read(dockerfile)):
                evidence = f"`{dockerfile.relative_to(root).as_posix()}` FROM"
                found = dated(app.name, product, version, evidence, table, today)
                if found and not any(p.app == app.name and p.product == product for p in products):
                    products.append(found)
    return {
        "snapshot": table["snapshot"],
        "dated": today.isoformat(),
        "products": [product.record() for product in products],
        "provenance": "detected",
    }


def with_platform(root: Path, adoption: Adoption, apps: list[App], today: datetime.date | None = None) -> Adoption:
    return dataclasses.replace(adoption, platform=inventory(root, apps, today))
