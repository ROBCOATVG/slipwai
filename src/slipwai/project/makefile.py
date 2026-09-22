"""The `Makefile`: every local and CI entry point a generated project has.

`make verify` is the gate, and it is the same command locally and in CI. The targets a selection adds —
migrations, integration tests, the containers, the ways to run it — are marked regions, so a later
`./init` can cut them back out. Every recipe is built per service and merged, so a project with several
services — in one language or several — has one gate rather than one per service.
"""
from __future__ import annotations

from ..backends import SERVICE_PORT, dev_command
from ..catalog import CATALOG
from ..layout import AT_ROOT, Layout
from ..probes import HEALTH_PATH
from ..services import App, containers_of, services_of, web_apps, wrapped_of
from ..targets import managed
from ..tooling import app_tooling, service_qualifier, verify_path
from .adopted_targets import adoption_targets
from .agent_targets import agent_targets
from .compose import composed
from .flags import flag_gate, flag_gate_dependency
from .integration import integration_targets, integration_variables
from .model_targets import MODEL_GATES, model_targets
from .mutation import mutation_notes
from .native_commands import STEP, format_command, gated, go_modules_variable, native_commands, steps
from .openapi import exporting, openapi_targets
from .production import production_targets
from .shared_packages import npm_dependency, npm_workspace_targets


def dev_targets(project_name: str, services: list[App], apps: list[App]) -> str:
    """One foreground target per service that has a transport, each inside its own transport's marked
    region: `dev` for the first service, `dev-<name>` for the rest.

    In the transport's region because a service with no inbound HTTP has nothing to start — its entry point
    is whatever a slice makes it, and a target that ran nothing would be worse than the absence of one. A
    service's skeleton listens on `SERVICE_PORT` unless `PORT` says otherwise, so a service on any other port
    is told its own as the default — the environment still wins, exactly as it does for the first.
    """
    targets = ""
    for service in services:
        if service.transport is None:
            continue
        what = "the service" if len(services) == 1 else service.name
        command = dev_command(
            service.backend, service_qualifier(project_name, service), service.path,
            verify_path(service.language, apps),
        )
        if service.port != SERVICE_PORT:
            lines = steps(command)
            lines[-1] = f"export PORT=$${{PORT:-{service.port}}}; {lines[-1]}"
            command = STEP.join(lines)
        targets += f"""
# backing-service:{service.transport}:begin
{service.dev_target}: ## Run {what} in the foreground on http://localhost:{service.port} (Ctrl-C stops it)
\t{command}
# backing-service:{service.transport}:end
"""
    return targets


def install_step(service: App, tooling: dict) -> tuple[str, str]:
    """How one service's dependencies are made present before a recipe of its own runs: as a prerequisite
    on the target line, or as the first step of the recipe."""
    if needs := npm_dependency(service):
        return f" {needs}", ""
    return "", f"\t{tooling['install']}\n"


def migrate_targets(services: list[App], apps: list[App]) -> str:
    """`migrate`, named for the role the migrating feature answers rather than for the product — "the
    event-store migrations" stays true of whichever store was chosen, and of the next one.

    One target for one service; with several, one per migrating service inside its own store's marked
    region, and an unmarked aggregate that names them all — `$(MIGRATE_TARGETS)` is built inside the
    regions, so pruning a store empties its share of the aggregate rather than leaving a dangling name.

    The dependencies the migration tool needs come first, and how they are asked for differs by family: an
    npm service takes the npm dependency target as a prerequisite, because that target is where `npm ci` is
    spelled for the whole file, and every other backend's install is a step of the recipe. The prerequisite
    goes on the target line inside the marked region rather than on a line of its own outside it — a
    prerequisite line left behind by a prune would define `migrate` as a target with no recipe, which is a
    `make migrate` that succeeds silently having applied nothing.
    """
    migrating = [(s, f) for s in services if (f := s.selection.migrating_feature) is not None]
    if not migrating:
        return ""
    if len(services) == 1:
        service, feature = migrating[0]
        tooling = app_tooling(service, apps, feature)
        needs, install = install_step(service, tooling)
        return f"""
# backing-service:{feature}:begin
.PHONY: migrate
migrate:{needs} ## Apply the {service.selection.axis_of(feature)} migrations (needs services-up)
{install}\t{tooling['migrate']}
# backing-service:{feature}:end
"""
    text = ""
    for service, feature in migrating:
        tooling = app_tooling(service, apps, feature)
        needs, install = install_step(service, tooling)
        text += f"""
# backing-service:{feature}:begin
MIGRATE_TARGETS += migrate-{service.name}
.PHONY: migrate-{service.name}
migrate-{service.name}:{needs} ## Apply {service.name}'s {service.selection.axis_of(feature)} migrations (needs services-up)
{install}\t{tooling['migrate']}
# backing-service:{feature}:end
"""
    return text + """
.PHONY: migrate
migrate: $(MIGRATE_TARGETS) ## Apply every service's migrations (needs services-up)
"""


def web_targets(web: list[App], apps: list[App]) -> str:
    """One foreground target per browser app: `dev-web` for the first, `dev-<name>` after.

    `WEB_HOST` sits outside any transport's markers because it describes the dev servers rather than a
    service — `./init --http none` keeps `dev-web`, and a default pruned away underneath it would leave the
    target reading a variable nothing defines. `?=` so the environment and command line win over it, and
    `export` because Vite reads the environment, not anything Make would pass a recipe."""
    if not web:
        return ""
    targets = """
# Where the dev servers listen. Vite binds loopback by default, and on a laptop that is right: the browser
# is on this machine, and a dev server does not belong on the LAN. Anywhere the browser is somewhere else —
# a VM, a container, a remote sandbox — loopback is a boundary it sits on the far side of, and the symptom
# is a forwarded port that connects to nothing while the startup banner below looks perfectly healthy.
# `make dev-web WEB_HOST=0.0.0.0` opens it. Exported because Vite reads the environment, not Make, and the
# service needs no equivalent: it already defaults HOST to 0.0.0.0.
WEB_HOST ?= localhost
export WEB_HOST
"""
    for app in web:
        api = app.api_service(apps)
        to = "the service" if len(services_of(apps)) == 1 else (api.name if api else "")
        proxy = f", proxying /api to {to}" if api is not None else ""
        what = "the browser app" if len(web) == 1 else app.name
        targets += f"""
{app.dev_target}: ## Run {what} in the foreground on http://localhost:{app.port}{proxy}
\tnpm --workspace {app.path} run dev
"""
    return targets


def makefile(project_name: str, profile: str, apps: list[App], target: str = "none", layout: Layout = AT_ROOT) -> str:
    event = profile == "event-modelling"
    services = services_of(apps)
    web = web_apps(apps)
    suites, per_suite = gated(apps)
    native = native_commands(apps)
    # `lint` fails on formatting this project has not applied; `format` is what applies it. Written only
    # where a family in this project has a formatter at all, so no project carries a target that does
    # nothing — and never a prerequisite of `verify`, because a gate that rewrites the tree it is judging
    # is a gate that always passes.
    formatting = format_command(apps)
    if formatting:
        formatting = f"format: ## Rewrite this project's own code the way `make lint` expects to find it\n\t{formatting}\n"
    verify_dependencies = (
        "lint typecheck check-imports check-migrations check-slice-scope check-extensions check-agents check-speckit "
        "check-codegraph check-ux-gates check-constitution check-benchmark check-decisions test"
    )
    style_target = ""
    if web:
        verify_dependencies += " check-styles"
        style_target = """check-styles: ## Fail when imported stylesheets compete for a :root custom property
\tpython3 scripts/check-styles.py
"""
    if event:
        verify_dependencies += MODEL_GATES
    # Not appended to the line above but added as a rule of its own below, inside the transport's marked
    # region: a prerequisite that survived the transport it checks would be a `verify` that cannot run.
    api_document = openapi_targets(project_name, apps)
    verify_dependencies += flag_gate_dependency(target)
    if wrapped_of(apps):
        verify_dependencies += " check-convergence"
    # Which of each service's answers brings a suite the Docker-free gate cannot run, and which one has
    # migrations to apply, are traits the options declare in `catalog.json` and are read per service.
    integrating = any(s.selection.integration_feature is not None for s in services)
    migrating = any(s.selection.migrating_feature is not None for s in services)
    service_variables = integration_variables(suites, apps, per_suite) + go_modules_variable(services)
    if migrating:
        # Under a marked region per migrating store, so pruning the last one prunes the CI step with it.
        service_variables += "".join(
            f"# backing-service:{feature}:begin\nCI_DATABASE := migrate\n# backing-service:{feature}:end\n"
            for feature in dict.fromkeys(
                s.selection.migrating_feature for s in services if s.selection.migrating_feature
            )
        )

    # One pair of targets for every container, rather than a Postgres-shaped pair: a project given only
    # Keycloak still has something to start, and `docker compose up -d --wait` blocks on the healthchecks
    # each service declares for itself. Nothing here needs to know which containers those are. Guarded on
    # the Compose file rather than wrapped in a marker, because a marker is per-feature and the condition
    # here is "any container at all", which no single feature's region can express. The pruner already
    # deletes docker-compose.yml once nothing needs a container, so testing for it is testing the truth
    # directly, and these targets stay correct after a prune instead of failing with no file to read.
    compose_targets = """
.PHONY: services-up services-down
services-up: ## Start the local backing services and wait for them to report healthy
\t@if [ -f docker-compose.yml ]; then docker compose up -d --wait; else echo 'no local backing services in this project'; fi
services-down: ## Stop the local backing services, keeping any volume
\t@if [ -f docker-compose.yml ]; then docker compose down; else echo 'no local backing services in this project'; fi
""" if containers_of(apps) else ""

    dev_target = dev_targets(project_name, services, apps)
    dev_web_target = web_targets(web, apps)
    # The addresses are read back from Compose rather than printed from these constants, because `.env` can
    # move a published port and a demo that names the wrong URL wastes the feedback it was asking for.
    # `up --wait` has already failed the target if anything is unhealthy, so these lines only ever run on a
    # stack that is answering. `API` while there is one service, because that is what it is; each service's
    # own name once there are several, because that is the only way to tell the addresses apart.
    address = "sed -e 's/0\\.0\\.0\\.0/localhost/' -e 's/\\[::\\]/localhost/'"
    demo_lines = ""
    for service in services:
        if service.transport is None:
            continue
        label = "API  " if len(services) == 1 else service.name
        demo_lines += (
            f"# backing-service:{service.transport}:begin\n"
            f"\t@printf '  {label} http://%s{HEALTH_PATH}\\n' "
            f"\"$$(docker compose port {service.name} {service.port} | {address})\"\n"
            f"# backing-service:{service.transport}:end\n"
        )
    for app in web:
        label = "App  " if len(web) == 1 else app.name
        demo_lines += (
            f"\t@printf '  {label} http://%s\\n' \"$$(docker compose port {app.name} {app.port} | {address})\"\n"
        )
    demo_targets = f"""
demo: ## Start the whole app in containers and print where to open it
\tdocker compose --profile app up -d --wait
\t@echo
{demo_lines}\t@echo
\t@echo '  make demo-down stops it; make demo again after an edit only if a dependency changed'
demo-down: ## Stop the demo, keeping any volume
\tdocker compose --profile app down
""" if composed(apps) else ""
    run_targets = ""
    if dev_target or dev_web_target or demo_targets:
        phony = " ".join(
            name
            for name, present in (
                (" ".join(s.dev_target for s in services if s.transport is not None), dev_target),
                (" ".join(app.dev_target for app in web), dev_web_target),
                ("demo demo-down", demo_targets),
            )
            if present
        )
        run_targets = f"\n.PHONY: {phony}{dev_target}{dev_web_target}{demo_targets}"
    service_targets = compose_targets + migrate_targets(services, apps) + run_targets
    mutation_note = mutation_notes(apps)
    # `$(CI_DATABASE)` expands to nothing once its definition is pruned, which is exactly the difference
    # between the two CI gates. Under a production target the extended gate also builds every image and
    # proves each answers its probe — the half of a deploy that can be proved without an account.
    production = " build smoke-image" if managed(CATALOG, target) else ""
    # An adopted repository's `smoke` — each wrapped application started by the command it recorded and proved to
    # answer — is the extended gate's too, and never `verify`'s: it needs what the application needs.
    adoption = " smoke" if wrapped_of(apps) else ""
    ci_targets = (
        f"ci: verify audit $(CI_DATABASE) test-integration{production}{adoption} ## Local equivalent of the extended CI gate\n"
        if integrating
        else f"ci: verify audit test-integration{production}{adoption} ## Local equivalent of the extended CI gate\n"
    )
    production_section = production_targets(project_name, apps, target) if managed(CATALOG, target) else ""
    # The published document's gate, as a prerequisite line per transport rather than a word on `verify`'s
    # own: a project that drops its transport drops the check with it and keeps a gate that runs.
    document_gate = "".join(
        f"# backing-service:{transport}:begin\nverify: check-openapi\n# backing-service:{transport}:end\n"
        for transport in dict.fromkeys(s.transport for s in exporting(project_name, apps))
    )
    phony_integration = " ".join(f"test-integration-{s.name}" for s in suites) if len(suites) > 1 else ""
    return f"""# Local and CI entry points. Compatible with GNU Make 3.81 (the macOS default).
SHELL := /bin/bash
.DEFAULT_GOAL := help
{service_variables}
.PHONY: help
help: ## Show the available targets
\t@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{{ printf "  %-22s %s\\n", $$1, $$2 }}'

.PHONY: install
install: ## Install native dependencies; refresh agent projections after init
\t{native['install']}
\t@if [ -f .specify/integration.json ]; then $(MAKE){layout.make_flag} --no-print-directory agents; else echo 'Spec Kit not initialized; run ./init when ready.'; fi
{npm_workspace_targets(apps, target)}
{agent_targets()}
.PHONY: typecheck lint {'format ' if formatting else ''}check-imports check-migrations check-slice-scope {'check-styles ' if web else ''}{'check-flags ' if target != 'none' else ''}check-speckit check-codegraph check-ux-gates check-constitution constitution-requirements
typecheck: ## Run the native compiler or static type check
\t{native['typecheck']}
lint: ## Run the native formatting and static-analysis gate
\t{native['lint']}
{formatting}
check-imports: ## Fail when domain code imports an outer architecture layer
\tpython3 scripts/check-imports.py
check-migrations: ## Fail when a migration contracts the schema without naming the earlier expand it completes
\tpython3 scripts/check-migrations.py
check-slice-scope: ## Fail when a slice/<id> branch touches what a sibling slice may also be writing
\tpython3 scripts/check-slice-scope.py
{style_target}{flag_gate(target)}check-speckit: ## Fail when an initialized Spec Kit-managed file differs from its manifest
\tpython3 scripts/check-speckit.py
check-codegraph: ## Fail when the adopted code index no longer describes the tracked source
\tpython3 scripts/check-codegraph.py
check-ux-gates: ## Fail when a browser app breaks the adopted UX gates: literal values outside the tokens, and the render gates over screens/
\tpython3 scripts/check-ux-gates.py
check-constitution: ## Fail when a ratified constitution drops a principle this project depends on
\tpython3 scripts/check-constitution.py
constitution-requirements: ## Print the normative text the constitution must cover in this profile
\t@python3 scripts/check-constitution.py --requirements
{model_targets(event)}{api_document}
{service_targets}
.PHONY: test test-integration {phony_integration + ' ' if phony_integration else ''}adversarial mutation audit
test: ## Run the complete native test suite
\t{native['test']}
{integration_targets(suites, per_suite)}adversarial: ## Re-run tests named or tagged adversarial
\t{native['adversarial']}
{mutation_note}mutation: ## Run native mutation testing, or explain the missing project decision
\t{native['mutation']}
audit: ## Run the ecosystem-native dependency vulnerability audit
\t{native['audit']}

.PHONY: verify ci
verify: {verify_dependencies} ## Full deterministic pre-commit gate
\t@echo
\t@echo 'verify: all gates passed'
{document_gate}{ci_targets}{production_section}{adoption_targets(apps, layout)}"""
