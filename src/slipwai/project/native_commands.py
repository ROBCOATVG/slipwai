"""What each service runs for the eight targets the Makefile is built from, merged into one recipe per target.

Which command installs, lints, tests or audits a service is its backend's `native_commands` answer, declared
in its language's `project/languages/<language>_toolchain.py` and read through the registry: pure data, the
same command whatever else the selection contains, and the same for every service, spelled for the service's
own path. This module assembles the answers. It sits apart from `makefile.py` for the reason
the service layouts sat apart from `backing_services.py`, and `makefile.py` had grown past check-structure's
module budget saying exactly that.

`TARGETS` is the contract: every backend answers exactly these eight, `docs/backend-obligations.md` documents
them row for row, and `tests/test_backend_obligations.py` fails, naming the backend and the target, until a
new backend answers each one. The contract is owed *per service*: `native_commands` asks it of every service
in the project and merges the answers into one recipe per target.
"""
from __future__ import annotations

import shlex

from ..npm_workspace import npm
from ..registry import FORMATTER, MAKEFILE_VARIABLES, NATIVE_COMMANDS, registry
from ..services import App, services_of, web_apps, wrapped_of
from ..tooling import for_app, verify_path

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
    """One service's eight commands, spelled for its own directory (and its family's verify script): the
    backend's `native_commands` answer, which `tests/test_backend_obligations.py` holds to exactly `TARGETS`."""
    return registry().answer(backend, NATIVE_COMMANDS)(path, verify)


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


def family_variables(services: list[App]) -> str:
    """The Make variables each family's recipes read (its `makefile_variables` answer), given that family's service
    paths in service order — or nothing, where no family present has any."""
    answer = registry().answer
    variables = ""
    for family in dict.fromkeys(service.language for service in services):
        own = [service for service in services if service.language == family]
        write = answer(own[0].backend, MAKEFILE_VARIABLES)
        variables += write([service.path for service in own]) if write is not None else ""
    return variables


def format_command(apps: list[App]) -> str:
    """The `format` recipe for this project, or an empty string where nothing in it has a formatter.

    How each language family rewrites its own code into the shape its gate checks for: the family's
    `formatter` answer. A ninth answer beside the eight rather than a ninth member of `TARGETS`, because this
    one is not owed: `make verify` *checks* the formatting, and a family whose gate has no formatter answers
    `None`, contributes no line and needs no placeholder. A family that has one contributes exactly one recipe
    however many services it has; a family whose tool takes paths names them through its `makefile_variables`
    answer (Go's `GO_MODULES`), once for `lint` and `format` alike. A browser app is formatted by its own family's
    formatter whatever its services are written in — the family that ships its frontend — and by none where that
    family answers `None`.
    """
    services = services_of(apps)
    answer = registry().answer
    lines: list[str] = []
    for family in dict.fromkeys(service.language for service in services):
        for service in (s for s in services if s.language == family):
            formatter = answer(service.backend, FORMATTER)
            if formatter is None:
                continue
            line = for_app(formatter, service.path, verify_path(family, apps))
            if line not in lines:
                lines.append(line)
    browser = web_apps(apps)
    if browser and (web := registry().family_answer(browser[0].language, FORMATTER)) is not None and web not in lines:
        lines.append(web)
    return STEP.join(lines)


#: What `make unit` runs where no backend says otherwise: the native test suite alone. Integration, mutation,
#: the image build and the audit are the full gate's, before the merge.
DEFAULT_FAST = ("test",)


def fast_targets(apps: list[App]) -> tuple[str, ...]:
    """Which targets are fast enough to run on every increment, as the services' backends answer it.

    The intersection rather than the union: `make unit` is one target over every service, so a target is
    only fast here where it is fast everywhere. One slow service would otherwise make the inner loop slow
    for all of them, which is the habit theme B exists to drop.
    """
    from ..registry import FAST_TARGETS, registry

    answers = []
    for service in services_of(apps):
        answered = registry().answer_or(service.backend, FAST_TARGETS, DEFAULT_FAST)
        named = tuple(str(target) for target in answered) if answered else DEFAULT_FAST
        answers.append({target for target in named if target in TARGETS})
    settled = set.intersection(*answers) if answers else set(DEFAULT_FAST)
    return tuple(target for target in TARGETS if target in settled)


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
        node_backend = any(npm(service.language) for service in services)
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
