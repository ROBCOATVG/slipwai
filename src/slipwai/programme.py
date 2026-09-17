"""The programme for an adopted repository: every improvement the record shows, in order, paced by the strategy.

Brownfield adoption (experimental as `AGENTS.md` defines the word). Three kinds of thing the survey and the
platform turn up wanted tracking without three ledgers: the big issues that are quick wins (`quick_wins.py`), the
runtimes and frameworks past their end of life (`platform.py`), and the longer moves the ladder in
`docs/change-strategy.md` names — packaging, runtime, host, data, the tooling an ecosystem has and the record says
is missing. Under the ladder sits its floor: a build that declares its dependencies and fetches them. An Ant build
with its jars committed is below it, and moving that to Maven or Gradle is the one step no strategy paces
differently — first, because nothing above it can be fetched, dated or audited until it is done. Beside the build
sits the other half of the floor: the application proven to start, its run path written in `survey/running.md` and
the command that starts it and proves it answers recorded as `commands.smoke` — before any slice changes code that
was here, because the first adoptions each merged a slice that had stopped the application starting, and no suite
saw it. This module reads them all off the record as one ordered list, each step with its kind and its
*pacing*: a quick win is now whatever the strategy; the platform and the rungs are a big bang per rung under
in-place or a modular monolith, over time — the new home current from day one, the old home only if it
stays — under a strangler fig, recorded but not scheduled under *leave it*, and, while nothing is decided,
"decide the strategy first". Written into `strategy.programme` by `with_recommendation`, rendered on
`docs/change-strategy.md` as *The programme*, and offered by `/drive`'s Convergence stage from the top. Nothing is
ticked off by hand: `/survey` derives it again, and a step the tree shows done is not there any more.
"""
from __future__ import annotations

import datetime

from .ecosystems import prefixed
from .origin import Adoption
from .services import App, wrapped_of

STALE_AFTER = datetime.timedelta(days=180)
# What the essay (`docs/change-strategy.md`, *Separate the layers*) says the way up is for each product — an option
# offered, never a version the factory bumps. Rung 1 is the language, rung 2 the framework; the packaging rung is
# where a container stops mattering.
UPGRADE_PATHS: dict[str, str] = {
    "java": "the current LTS (21, or 25) through OpenRewrite's `UpgradeToJava21` recipe; the `-source`/`-target` the "
            "build pins move with it, and the framework rung comes first where Spring is older than 5.3 — Spring 3 and "
            "4 cannot load bytecode above Java 8",
    "node": "the current LTS line (even-numbered); `engines.node` or `.nvmrc` pins it, and the gate's CI installs what "
            "is pinned",
    "python": "the current 3.x; `pyupgrade --py3XX-plus` rewrites the syntax, and `futurize` bridges from 2",
    "go": "the newest minor — Go supports two at a time — by bumping the `go` directive and running `go fix`",
    "dotnet": "the current LTS through the .NET Upgrade Assistant; a .NET Framework site becomes a self-hosted process "
              "on the way",
    "php": "the current 8.x; Rector rewrites the mechanical part",
    "ruby": "the current 3.x, with the release notes' deprecations cleared first",
    "spring-framework": "Spring Framework 6 — or Spring Boot 3, which brings it — through OpenRewrite's "
                        "`UpgradeSpringFramework_6_0` and `UpgradeSpringBoot_3_x` recipes, in steps through 4.3 and "
                        "5.3, each a release; it needs Java 17 and the `jakarta.*` namespace, so the servlet API and "
                        "the container move in the same step",
    "spring-boot": "the current Boot line through OpenRewrite's `UpgradeSpringBoot_3_x`, one minor at a time with the "
                   "migration guide for each",
    "tomcat": "Tomcat 10.1 or 11 — `jakarta.servlet`, so it goes with the Spring 6 step — or, once the packaging rung "
              "moves off the WAR, no standalone container at all: an executable jar with the server embedded",
    "servlet": "`jakarta.servlet` 6 (Jakarta EE 10), which Tomcat 10.1+ and Spring 6 require; Tomcat's migration tool "
               "for Jakarta EE rewrites the `javax.*` imports mechanically",
    "junit": "JUnit 5 (Jupiter) for new tests, with the vintage engine running the JUnit 3 and 4 tests that exist "
             "until they are moved — and no mocking framework beside it (`AGENTS.md`, *Delivery method*)",
    "django": "the current LTS, one LTS at a time through the release notes' deprecation warnings",
    "rails": "one minor at a time with `rails app:update` and the upgrade guide for each step",
    "angular": "one major at a time with `ng update`; update.angular.io lists the steps",
    "laravel": "one major at a time with the upgrade guide; Laravel Shift automates most of it",
}



# The tool an ecosystem has for a target the record says nothing runs — proposed, never added (`adopt` introduces
# no step; `docs/adopting.md`, *What it refuses*). `typecheck` only where the language has none built in.
TOOLING: dict[str, dict[str, str]] = {
    "maven": {"lint": "Checkstyle (`maven-checkstyle-plugin`)", "audit": "OWASP `dependency-check-maven`"},
    "gradle": {"lint": "Checkstyle", "audit": "OWASP `dependency-check-gradle`"},
    "node": {"lint": "ESLint", "typecheck": "TypeScript's `tsc --noEmit` (or JSDoc under `checkJs`)"},
    "python": {"lint": "Ruff", "typecheck": "mypy", "audit": "pip-audit"},
    "go": {"audit": "`govulncheck`"},
    "php": {"lint": "PHPStan"},
    "ruby": {"lint": "RuboCop", "audit": "`bundler-audit`"},
}
PACING: dict[str, dict[str | None, str]] = {
    "quick-win": {None: "now — a slice of its own whatever the strategy; a secret in the tree today"},
    "build": {None: "first, whatever the strategy — before the platform and every rung: nothing above it can be "
                    "fetched, dated or audited until the build declares its dependencies, and a build that does is "
                    "the least the method holds any repository to"},
    "run": {None: "next, after the build and before any slice changes code that was here, whatever the strategy: a "
                  "change to an application nothing has started is a change nobody has seen run, and a suite that "
                  "never builds the context cannot tell a constructor the container can call from one it cannot"},
    "platform": {
        None: "depends on the strategy — decide it first (`/ground`); the platform comes before any strategy",
        "in-place": "big bang per rung: one slice per product across the whole application, the gate green "
                    "between, rungs 1 and 2 of the ladder first",
        "modular-monolith": "big bang per rung, before the restructuring: one slice per product, the gate green "
                            "between",
        "strangler-fig": "over time, or first: the new home starts on the current platform; the old home is upgraded "
                         "first only where it must keep shipping for long — the ADR says which",
        "leave-it": "only what security requires; recorded so it is not forgotten, not scheduled",
        "rewrite": "not in place: the new system starts current; recorded for the cut-over plan",
    },
    "rung": {
        None: "depends on the strategy — decide it first (`/ground`)",
        "in-place": "big bang per rung, in ladder order, after the platform",
        "modular-monolith": "big bang per rung, in ladder order, before the restructuring",
        "strangler-fig": "over time: the new home has it from day one; the old home only if it stays",
        "leave-it": "not scheduled; recorded so it is not forgotten",
        "rewrite": "the new system has it from day one; recorded for the cut-over plan",
    },
    "tooling": {None: "over time, whatever the strategy: one tool, one slice, green through the ratchet before it is "
                      "recorded as a command — the method never adds one uninvited"},
    "home": {None: "first under a strangler fig, before the first product slice: the new home is where every product "
                   "slice lands, and a strangler whose slices land in the old home is the old home with a new label"},
}


def pacing(kind: str, strategy: str | None) -> str:
    table = PACING[kind]
    return table.get(strategy, table[None])


def step(kind: str, what: str, evidence: str, strategy: str | None) -> dict:
    return {"kind": kind, "step": what, "pacing": pacing(kind, strategy), "evidence": evidence}


def programme(adoption: Adoption, apps: list[App], strategy: str | None) -> list[dict]:
    """Every improvement the record shows, in the order to take them: quick wins, a build below the floor, an
    application nobody has proved starts, the platform, the ladder's rungs the tree says are behind, then the tooling
    the ecosystem has and nothing here runs."""
    wins: list[dict] = list((adoption.survey or {}).get("quickWins") or [])
    steps = [step("quick-win", f"{w.get('what')} — {w.get('fix')}", str(w.get("where")), strategy) for w in wins]
    wrapped = wrapped_of(apps)
    for app in wrapped:
        if (app.toolchain or {}).get("ecosystem") == "ant":
            what = (f"`{app.name}`: the build is Ant with its jars committed — move it to Maven or Gradle through the "
                    "wrapper: a `pom.xml` (or `build.gradle`) that declares each committed jar as a dependency by its "
                    "coordinates, sources under `src/main/java`, the same artifact out of `./mvnw -q package`; then "
                    "`/survey` reads the tree as Maven, the recorded commands follow, and the jars leave the tree")
            steps.append(step("build", what, f"toolchain.ecosystem: ant ({prefixed(app.path, 'build.xml')})", strategy))
    for app in wrapped:
        # A `smoke` recorded as `null` is a written no — an application nobody can start outside production, with the
        # reason in `survey/running.md` — and is not a step; a key nobody has written is.
        if "smoke" not in (app.commands or {}):
            what = (f"`{app.name}`: how it starts is not proven — run it once the way the README, container file or CI "
                    "config says, write what was proven (the command, the port, the seed, the runtime it needs and the "
                    "ones it cannot run on) in `survey/running.md`, and record the one command that starts it and "
                    "proves it answers as `commands.smoke` in `project.json` (`null` is a written no, with the reason "
                    "there); "
                    "`make smoke` and the gate's smoke job run it from then on")
            steps.append(step("run", what, f"commands.smoke: unrecorded for {app.path}", strategy))
    if strategy == "strangler-fig" and wrapped and all(not app.generated for app in apps):
        # The strategy decided and nowhere for a capability to move to: the first strangler adoption built five
        # product slices in the WAR because no new home existed and nothing said one had to.
        steps.append(step("home", "`strangler-fig` is decided and no new home exists — every deployable is one that "
                                  "was here. `add-service` puts a generated service beside them, current from day "
                                  "one; product slices land there, and the first capability moves through `/strangle`",
                          "deployables: none generated", strategy))
    steps += [step("platform", f"{phrase(p)}; the way up is {option(p)}", str(p.get("evidence")), strategy)
              for p in expired(adoption.platform)]
    wars = [app.name for app in wrapped if (app.toolchain or {}).get("packaging") == "war"]
    if wars:
        steps.append(step("rung", "Packaging (rung 3): a WAR on an application server becomes an executable jar with "
                                  "the server embedded, and the container stops mattering",
                          f"packaging: war ({', '.join(wars)})", strategy))
    if wrapped and not (adoption.survey or {}).get("containers"):
        steps.append(step("rung", "Runtime (rung 4): no container image is built here — a first `Dockerfile`, and "
                                  "`make verify` grows a step that builds it",
                          "survey: no Dockerfile or Compose file", strategy))
    if (adoption.infrastructure or {}).get("home") == "unmanaged":
        steps.append(step("rung", "Host (rung 5): the infrastructure is described nowhere anyone can read — describe "
                                  "it here or in a named repository (`docs/deployment.md`)",
                          "infrastructure.home: unmanaged", strategy))
    if (adoption.database or {}).get("schema") == "unmanaged":
        steps.append(step("rung", "Data: the schema is versioned nowhere — the ecosystem's own migration tool, with a "
                                  "baseline migration that matches the database as it is (`docs/change-strategy.md`, "
                                  "*Data*)", "database.schema: unmanaged", strategy))
    for app in wrapped:
        tools = TOOLING.get((app.toolchain or {}).get("ecosystem", ""), {})
        for target, tool in tools.items():
            if (app.commands or {}).get(target) is None and target in (app.commands or {}):
                steps.append(step("tooling",
                                  f"`{app.name}`: no `{target}` command is recorded; the ecosystem has {tool}",
                                  f"commands.{target}: null", strategy))
    return steps


def programme_table(steps: list[dict]) -> str:
    if not steps:
        return ("Nothing the record shows: no quick win, a build that declares its dependencies, no product out of "
                "support, every rung the tree can show reached.")
    rows = "\n".join(f"| {i} | {s['step']} | `{s['kind']}` | {s['pacing']} | `{s['evidence']}` |"
                      for i, s in enumerate(steps, start=1))
    return f"| # | Step | Kind | Pacing | Evidence |\n|---|---|---|---|---|\n{rows}"


def expired(record: dict) -> list[dict]:
    return [p for p in (record or {}).get("products") or [] if p.get("status") == "end-of-life"]


def unplaced(record: dict) -> list[dict]:
    return [p for p in (record or {}).get("products") or [] if p.get("status") == "unknown"]


def phrase(product: dict) -> str:
    """`Spring Framework 3.2.8 left support on 2016-12-31`, or `JUnit 5.10 is not in the support table`."""
    if product.get("status") == "end-of-life":
        return f"{product['title']} {product['version']} left support on {product['eol']}"
    if product.get("status") == "unknown":
        return f"{product['title']} {product['version']} is not in the support table"
    if product.get("status") == "ending":
        return f"{product['title']} {product['version']} leaves support on {product['eol']}"
    until = f" until {product['eol']}" if product.get("eol") else ""
    return f"{product['title']} {product['version']} is in support{until}"


def option(product: dict) -> str:
    """The way up the essay names for this product — an option, never a bump."""
    return UPGRADE_PATHS.get(product.get("product", ""), "the ecosystem's current release, one step at a time")


def staleness(record: dict, today: datetime.date | None = None) -> str:
    """A line about the table's age where it matters: past `STALE_AFTER`, the dating is a reason to refresh."""
    snapshot = (record or {}).get("snapshot")
    if not snapshot:
        return ""
    age = (today or datetime.date.today()) - datetime.date.fromisoformat(snapshot)
    if age <= STALE_AFTER:
        return ""
    # Past the threshold, not the exact age: a number of days that changed every day made `/survey` rewrite the page
    # every day, with no fact behind the change.
    return (f" The table is more than {STALE_AFTER.days} days old; a newer factory carries a newer one "
            "(`scripts/refresh-support.py` in the factory), and `slipwai migrate` then `/survey` re-dates this.")
