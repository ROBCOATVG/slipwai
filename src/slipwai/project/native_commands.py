"""What each backend runs for the eight targets the Makefile is built from, per service.

One table, keyed by backend, because the answer is pure data: which command installs, lints, tests or
audits a service is the same command whatever else the selection contains — and the same command for every
service, spelled with `APP` where the service's path goes. It sits apart from `makefile.py` for the reason
`service_layouts.py` sits apart from `backing_services.py` — the table is most of the bytes and none of the
assembly, and a module holding both outgrows what anybody wants to read at once. `makefile.py` had grown
past check-structure's module budget saying exactly that.

The keys are the contract: every backend answers all eight, `docs/backend-obligations.md` documents them
row for row, and `tests/test_backend_obligations.py` fails until a new backend answers each one. The
contract is owed *per service*: `native_commands` asks it of every service in the project and merges the
answers into one recipe per target.
"""
from __future__ import annotations

import shlex

from ..backends import APP, MAVEN, MAVEN_READY, VERIFY
from ..services import App, services_of, web_apps, wrapped_of
from ..tooling import for_app, verify_path
from .languages.go import GO_COVDATA_READY, GO_COVERAGE_GATE, GO_STATICCHECK, GO_TEST
from .mutation import GO_MUTATION_SCRIPT, JAVA_QUARKUS_MUTATION_PLACEHOLDER
from .shared_packages import PACKAGES

# How a recipe with several shell lines is spelled: each line after the first on a new line behind a tab,
# which is where Make wants it. Every table below joins with it, and `steps` is the one way to split it.
STEP = "\n\t"


def steps(recipe: str) -> list[str]:
    """The shell lines of one recipe, in order."""
    return recipe.split(STEP)


# The eight targets every service answers, in the order the recipes below spell them.
TARGETS = ("install", "typecheck", "lint", "test", "integration", "adversarial", "audit", "mutation")
# The targets a wrapped application's recorded command runs through the ratchet: red on day one is the
# expected state of a linter that arrived after the code, and the ratchet fails only on what is new. `test` is
# there so that a suite that is red on day one is quarantined and said, rather than a gate that is red on day one.
RATCHETED = ("lint", "typecheck", "test")
RATCHET = "python3 scripts/ratchet.py"


def wrapped_recipes(apps: list[App]) -> list[dict[str, str]]:
    """An existing application's recorded commands as its recipes, one per target.

    What its own build answers each target with, run from the repository root as recorded — with `$`
    doubled, since these lines land in Make. Where it recorded `null`, a line that says so and passes: a
    written no is the ecosystem having no answer, not a gate failing. Lint, typecheck and test run through the
    ratchet (`scripts/ratchet.py`), which holds them to a committed baseline and fails only on what is new; the
    recorded command reaches it as one quoted word, so a `cd apps/shop && npm run lint` for an application in a
    subdirectory is the ratchet's whole command and not a recipe the shell splits at `&&`.
    """
    recipes = []
    for app in wrapped_of(apps):
        commands = app.commands or {}
        recipe = {}
        for target in TARGETS:
            command = commands.get(target)
            if not command:
                recipe[target] = f"@echo '{app.name}: no {target} command recorded in project.json ({app.path})'"
            elif target in RATCHETED:
                recipe[target] = f"{RATCHET} {app.name} {target} -- {shlex.quote(command).replace('$', '$$')}"
            else:
                recipe[target] = command.replace("$", "$$")
        recipes.append(recipe)
    return recipes


def service_commands(backend: str, path: str, verify: str = "scripts/verify") -> dict[str, str]:
    """One service's eight commands, spelled for its own directory (and its family's verify script)."""
    native = {
        "typescript": {
            "install": "npm ci",
            "typecheck": f"npm --workspace {APP} run typecheck",
            "lint": f"npm --workspace {APP} run lint",
            "test": f"npm --workspace {APP} test",
            "integration": f"npm --workspace {APP} exec -- vitest run --passWithNoTests tests/integration",
            "adversarial": f"npm --workspace {APP} exec -- vitest run --passWithNoTests -t adversarial",
            "audit": "npm audit --audit-level=critical",
            "mutation": "@echo 'Configure the repository-selected Stryker mutator, then run its checked-in configuration.'; exit 2",
        },
        # `scripts/verify` loops over the services itself, so most of these are one line for the whole
        # project and `native_commands` below emits them once.
        "python": {
            "install": f"./{VERIFY} --install-only",
            # Byte-compile, then mypy over the same trees — the shape the factory holds itself to.
            # `compileall` alone is not a type check: it proves the files parse and nothing else.
            "typecheck": f"./{VERIFY} --typecheck-only",
            "lint": f"./{VERIFY} --lint-only",
            "test": f"./{VERIFY} --test-only",
            "integration": f"./{VERIFY} --integration-only",
            "adversarial": f"./{VERIFY} --adversarial-only",
            # Against the lock, exported on the spot — every pin this project resolves to, the gate's
            # tools included, and no committed file for the audit to read a stale copy of.
            "audit": (
                "@command -v pip-audit >/dev/null 2>&1 || { echo 'install pip-audit to run dependency "
                "audit' >&2; exit 2; }; pip-audit -r <(uv export --project "
                f"{APP} --frozen --no-emit-project --no-hashes)"
            ),
            "mutation": "@command -v mutmut >/dev/null 2>&1 || { echo 'install and configure mutmut for the selected production packages' >&2; exit 2; }; mutmut run",
        },
        "go": {
            "install": f"cd {APP} && go mod download",
            "typecheck": f"cd {APP} && go test -run '^$$' ./...",
            # Three analysers, widening as they go: the formatter, the compiler's own narrow vet, and
            # staticcheck for what vet deliberately leaves alone (`go.py` says which).
            "lint": (
                f"test -z \"$$(gofmt -l $(GO_MODULES))\"\n\tcd {APP} && go vet ./...\n\tcd {APP} && {GO_STATICCHECK}"
            ),
            # The suite, then the coverage gate over the profile it wrote: `-coverpkg=./...` so a package
            # is credited with every test that reaches it, and the script's minimum on the line (`go.py`).
            "test": f"{GO_COVDATA_READY}\n\t{GO_TEST}\n\t{GO_COVERAGE_GATE}",
            "integration": f"cd {APP} && go test -tags=integration ./...",
            "adversarial": f"cd {APP} && go test -run Adversarial ./...",
            "audit": f"@command -v govulncheck >/dev/null 2>&1 || {{ echo 'install govulncheck to run dependency audit' >&2; exit 2; }}; cd {APP} && govulncheck ./...",
            # Gremlins through the wrapper, which stages the service beside the workspace modules it imports
            # and fails a run Gremlins would pass on nothing. The gate is the service's `.gremlins.yaml`:
            # Gremlins 0.6.0 ignores a threshold given as a flag, so none is given here (see `mutation.py`).
            "mutation": f"python3 {GO_MUTATION_SCRIPT} {APP}",
        },
        "java-quarkus": {
            "install": MAVEN_READY,
            # javac *is* the type checker, so this target is "compile, with the checks that ride along":
            # Error Prone augments javac's own analysis and NullAway adds null-safety to it, both as
            # compiler plugins rather than a separate pass. `test-compile` so the test sources are held to
            # the same standard as the code they exercise.
            "typecheck": f"{MAVEN} -DskipTests test-compile",
            # Three analysers, and the compile they all need: SpotBugs reads bytecode, so `target/classes`
            # has to exist before it runs. Checkstyle is the standard, PMD the source-level rule set, and
            # each has its own committed configuration under the service's `config/` — tune the rules
            # there rather than dropping a gate here.
            "lint": f"{MAVEN} -DskipTests compile checkstyle:check pmd:check spotbugs:check",
            "test": f"{MAVEN} test",
            "integration": f"{MAVEN} test-compile failsafe:integration-test failsafe:verify",
            # A JUnit 5 tag rather than a name pattern, and `failIfNoTests=false` because a project that
            # has not written an adversarial test yet must still have a target that passes.
            "adversarial": f"{MAVEN} test -Dgroups=adversarial -DfailIfNoTests=false",
            "audit": (
                "@command -v osv-scanner >/dev/null 2>&1 || { echo 'install osv-scanner to run "
                f"dependency audit' >&2; exit 2; }}; osv-scanner scan source --recursive {APP}"
            ),
            "mutation": JAVA_QUARKUS_MUTATION_PLACEHOLDER,
        },
        # The same eight targets as its sibling, and only two of them differ. Everything a Maven build
        # does is a goal, so `install`, `typecheck`, `lint`, `test`, `integration`, `adversarial` and
        # `audit` are word for word what the Quarkus backend runs — the configuration those goals read
        # is what differs, and that lives in each pom. What is genuinely different is `mutation`.
        "java-spring": {
            "install": MAVEN_READY,
            "typecheck": f"{MAVEN} -DskipTests test-compile",
            "lint": f"{MAVEN} -DskipTests compile checkstyle:check pmd:check spotbugs:check",
            "test": f"{MAVEN} test",
            "integration": f"{MAVEN} test-compile failsafe:integration-test failsafe:verify",
            "adversarial": f"{MAVEN} test -Dgroups=adversarial -DfailIfNoTests=false",
            "audit": (
                "@command -v osv-scanner >/dev/null 2>&1 || { echo 'install osv-scanner to run "
                f"dependency audit' >&2; exit 2; }}; osv-scanner scan source --recursive {APP}"
            ),
            # A real target, not a placeholder, and this is the one backend in this factory where that is
            # true. PIT is configured in the pom over the domain packages with `*IT` excluded; pitest
            # issue #1287 — the timeouts that make the Quarkus sibling ship a documented gap instead —
            # reports the same setup working under Spring Boot.
            #
            # No `-DskipTests`, and that is not an oversight to tidy up. It reads like the right flag —
            # PIT runs the tests itself, once per mutant, so Surefire running them first buys nothing —
            # and `test-compile` does not run tests anyway, so it buys nothing either. What it *does* do
            # is make pitest skip the entire project: "Skipping project because: Test execution should be
            # skipped (-DskipTests)", exit 0, no report. Combined with a target no gate runs, that is a
            # mutation score nobody has that looks exactly like one everybody passed.
            "mutation": f"{MAVEN} test-compile org.pitest:pitest-maven:mutationCoverage",
        },
    }[backend]
    return {target: for_app(command, path, verify) for target, command in native.items()}


def merged(recipes: list[dict[str, str]]) -> dict[str, str]:
    """Several services' recipes as one per target, each distinct line once, in order.

    A line that names a service's path differs per service and is kept for each; a line that does not —
    `npm ci`, `./scripts/verify --lint-only`, the install guard — is a repository-level step, and running
    it once per service would install and audit the same workspace several ways.
    """
    result: dict[str, str] = {}
    if not recipes:
        return dict.fromkeys(TARGETS, "@true")
    for target in recipes[0]:
        lines: list[str] = []
        for recipe in recipes:
            for line in steps(recipe[target]):
                if line not in lines:
                    lines.append(line)
        result[target] = STEP.join(lines)
    return result


def gated(apps: list[App]) -> tuple[list[App], list[dict[str, str]]]:
    """Every application the gate's integration suites belong to, with each one's recipes: the generated
    services' own, and after them what each application that existed before the method did recorded."""
    services = services_of(apps)
    return [*services, *wrapped_of(apps)], [*commands_of(services, apps), *wrapped_recipes(apps)]


def commands_of(services: list[App], apps: list[App]) -> list[dict[str, str]]:
    """Each service's eight commands, in service order."""
    return [
        service_commands(service.backend, service.path, verify_path(service.language, apps))
        for service in services
    ]


# How each language family rewrites its own code into the shape its gate checks for. A ninth answer beside
# the eight above rather than a ninth member of `TARGETS`, because this one is not owed: `make verify`
# *checks* the formatting, and a family whose gate has no formatter contributes no line and needs no
# placeholder. A family that has one contributes exactly one recipe however many services it has — which
# is why this is keyed by family and not stamped per service, except Go, whose tool takes paths.
#
# Biome's configuration names `apps/**` and `packages/**`, and `biome format --write .` honours that glob
# from the root. `packages/` is also where a Go module lives (`SHARED_CODE` in `rules.py`), and Biome
# formats JSON: a digest over raw bytes then changes because a formatter ran, while `make lint` never
# saw the files — it is `biome check` inside each npm workspace. The loop is the same test
# `build-packages` already uses: a directory with a `package.json` is an npm package, and nothing else
# is. `biome.jsonc` stays as the one set of rules; this recipe is what stops it walking a tree it does
# not own. No install of its own: `format` takes the npm dependency target as a prerequisite
# (`project/shared_packages.consumers`).
BIOME_FORMAT = (
    f"@for dir in apps/*/ {PACKAGES}/*/; do \\\n"
    '\t\t[ -f "$$dir/package.json" ] || continue; \\\n'
    '\t\tnpm exec -- biome format --write "$${dir%/}"; \\\n'
    "\tdone"
)
FORMATTERS: dict[str, str] = {
    "typescript": BIOME_FORMAT,
    "python": f"./{VERIFY} --format",
    # Over `$(GO_MODULES)`, the one list `lint` reads too (`makefile.py`), so the two can never cover different
    # paths: a project whose gate checked two directories while its formatter rewrote one had a `make format`
    # that exited 0 and left the files `make lint` was about to fail.
    "go": "gofmt -w $(GO_MODULES)",
}


# Every Go module `gofmt` covers, named once and read by `lint` and `format` alike, so the two cannot drift. A
# project whose gate checked two directories while its formatter rewrote one had a `make format` that exited 0
# and left the files `make lint` was about to fail — twice, and diagnosed as delegate negligence both times,
# because formatting drift only ever surfaces downstream of the delegate that caused it.
GO_MODULES = """
# The Go modules `gofmt` formats and `make lint` checks, once, so the two never cover different paths. A Go
# module added under packages/ belongs on this line; both targets follow.
GO_MODULES := {paths}
"""


def go_modules_variable(services: list[App]) -> str:
    """The `GO_MODULES` definition for the Makefile, or nothing where no service is Go."""
    paths = [service.path for service in services if service.language == "go"]
    return GO_MODULES.format(paths=" ".join(paths)) if paths else ""


def format_command(apps: list[App]) -> str:
    """The `format` recipe for this project, or an empty string where nothing in it has a formatter.

    Every family is one recipe whatever the project holds: `gofmt` takes paths rather than reading a
    configuration, and its paths are the Makefile's `GO_MODULES`, named once for `lint` and `format` alike.
    """
    services = services_of(apps)
    lines: list[str] = []
    for family in dict.fromkeys(service.language for service in services):
        if family not in FORMATTERS:
            continue
        for service in (s for s in services if s.language == family):
            line = for_app(FORMATTERS[family], service.path, verify_path(family, apps))
            if line not in lines:
                lines.append(line)
    if web_apps(apps) and FORMATTERS["typescript"] not in lines:
        lines.append(FORMATTERS["typescript"])
    return STEP.join(lines)


def native_commands(apps: list[App]) -> dict[str, str]:
    """Every service's commands, merged, with each browser app's own checks appended after them — and after
    the generated services', the recorded commands of every application that existed before the method did."""
    services = services_of(apps)
    native = merged([*commands_of(services, apps), *wrapped_recipes(apps)])
    web = web_apps(apps)
    if web:
        # Of the family throughout this block: `npm ci` and `npm audit` are already in a TypeScript
        # backend's own recipes whatever framework owns its startup, and appending them twice
        # would be a gate that installs and audits the same workspace two ways.
        node_backend = any(service.language == "typescript" for service in services)
        if not node_backend:
            native["install"] += "\n\tnpm ci"
        # No install step here either: these targets take the npm dependency target as a prerequisite
        # (`shared_packages`), which is emitted for exactly the projects these lines are appended to.
        native["typecheck"] += "".join(f"\n\tnpm --workspace {w.path} run typecheck" for w in web)
        native["lint"] += "".join(f"\n\tnpm --workspace {w.path} run lint" for w in web)
        native["test"] += "".join(f"\n\tnpm --workspace {w.path} test" for w in web)
        native["adversarial"] += "".join(
            f"\n\tnpm --workspace {w.path} exec -- vitest run --passWithNoTests -t adversarial" for w in web
        )
        if not node_backend:
            native["audit"] += "\n\tnpm audit --audit-level=critical"
    return native
