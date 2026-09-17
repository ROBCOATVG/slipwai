"""The Go backend: one module per service, its committed variants, and the workspace above them."""
from __future__ import annotations

from ...assets import LANGUAGE_ROOT, asset_tree
from ...backends import APP
from ...errors import GenerationError
from ...selection import Selection
from ...services import App
from ...tooling import package_name
from ..backing_services import backing_service_service_files
from ..composition import wire_store
from ..flag_route import wire_entry
from ..flags import flag_reader
from ..mutation import GO_GREMLINS, GO_MUTATION_SCRIPT

# The coverage gate `make test` holds a Go service to, and the script that is the gate. The test line writes
# a profile with `-coverpkg=./...`, because without it Go credits a package only with its own tests and the
# domain package — tested through every adapter, holding no `_test.go` of its own — reads 0%; the script
# reads the profile back, leaves entry points and integration-tagged suites out of the count (its docstring
# says why), and fails below the minimum. Spelled as one command and one gate line so the Makefile recipe
# and the verify script below run the same thing.
GO_COVERAGE_SCRIPT = "scripts/go-coverage.py"
GO_TEST_COMMAND = "go test -coverpkg=./... -coverprofile=coverage.out ./..."
GO_TEST = f"cd {APP} && {GO_TEST_COMMAND}"
# The skeleton itself measures 78-83% in this gate's scope on every variant — memory, SQLite and Postgres
# stores, with and without a transport and an identity provider (2026-09-09) — so 70 is below what a fresh
# service starts at by a margin a first slice can spend, not a number the first test has to chase. It is on
# the Makefile line so a project raises it there as the suite earns it.
GO_COVERAGE_MINIMUM = 70
GO_COVERAGE_GATE = f"python3 {GO_COVERAGE_SCRIPT} {APP} {GO_COVERAGE_MINIMUM}"
# The token the mutation script carries where the pinned Gremlins release goes, so the pin is written once.
GO_GREMLINS_TOKEN = "__GO_GREMLINS__"
# What this service calls itself in a trace, carried in `config.go` as a token for the reason the module
# path is: the file is Go, and an exported span has to name the service rather than the template it came
# from. Resolved in `name_service`, where the project's name is known.
SERVICE_NAME = "__SERVICE_NAME__"

# Build `covdata` before anything races to exec it, and run this ahead of every `go test -cover` this
# backend writes — the Makefile's `test` target through `native_commands`, and the verify script below.
#
# Go 1.24 and later stopped shipping the toolchain's own commands prebuilt and build them on demand into
# the build cache instead. `go test -cover` then execs the resulting `covdata` once per package that has no
# test files — several at a time, moments after the same `go` process wrote that file — and on a cold cache
# one of those execs loses the race to the write that created it and dies with `text file busy`. That fails
# the gate while naming a package with no tests in it, and nothing about the project is wrong. Every CI
# runner starts cold, which is where it bites. A separate process that has exited before the parallel run
# begins leaves that run a finished binary and nothing to write.
#
# `percent` over a directory holding no coverage data is the cheapest invocation that exits zero, and it is
# spelled with no `$` so that one line serves a Makefile recipe and a `/bin/sh` script unchanged. `|| true`
# is deliberate: a warm-up must never become the thing that fails a gate, so a later toolchain that spells
# this differently leaves a project where it stands today rather than breaking it.
GO_COVDATA_READY = "go tool covdata percent -i=. >/dev/null 2>&1 || true"

# The third analyser in this backend's lint gate, after `gofmt` and `go vet`. `go vet` is deliberately
# narrow — it reports what is almost certainly a mistake and nothing arguable — which leaves a large class
# of real findings nobody sees: a value assigned and never read, a `defer` inside a loop, an error compared
# with `==` where the chain has to be unwrapped, an `errors.New` built with a format string. staticcheck's
# SA checks are those, and they are the ones a Go reviewer would raise by hand.
#
# `go tool` and not an installed binary: the module's `tool` directive pins it (`modules/base/go.mod`), so
# `go mod download` fetches it with every other dependency and the gate needs no second install step on a
# laptop, in the Compose container or in CI — and the version moves through `make locks` like the rest.
GO_STATICCHECK = "go tool staticcheck ./..."


def service_files(event: bool, selection: Selection, target: str = "none") -> dict[str, str]:
    """What this backend puts in a service's directory, keyed relative to it."""
    files = asset_tree(LANGUAGE_ROOT / "go/app")
    files["go.mod"] = go_module(selection)
    checksums = go_checksums(selection)
    if checksums is not None:
        files["go.sum"] = checksums
    if event and not selection.has("memory"):
        # Only for a backend whose event-store axis is not offered yet: a port with a shape and no
        # adapter behind it. Once the axis is asked, the port and its adapters arrive together.
        files.update(asset_tree(LANGUAGE_ROOT / "go/event-port"))
    files.update(backing_service_service_files(selection, "go"))
    # The flag reader, only where there is somewhere to deploy: a flag is what makes a merge and a release
    # two decisions, and `--target none` has neither the mechanism nor the unsafe push. See `flags.py`.
    files.update(flag_reader(target, "go"))
    # And the entry point's half of it: the source is handed to `BuildApp`, which is what puts
    # `/api/flags` in front of the browser app. `nil`, not an unresolved placeholder, with no reader.
    wire_entry(files, target)
    # And the store's half: which adapter this project opens, and what `/ready` is handed. See
    # `composition.py` — the entry point is the only place that may name the answer.
    wire_store(files, selection, "go")
    return files


# The only features that add a Go module requirement, and therefore the only ones that change go.mod and
# go.sum. Read combinatorially below, the way TypeScript's `LOCK_FEATURES` is, so one dependency set has
# exactly one name.
MODULE_FEATURES = ("postgres", "sqlite")


def go_module_variant(selection: Selection) -> str:
    """Which committed module files match this selection's dependency set.

    Go has no SQL driver in its standard library, so a real event store means a module
    requirement — and a requirement means a `go.sum`, which only `go mod tidy` can write. The two
    are committed per variant for the same reason the npm lockfiles are: a manifest and its
    checksums have to move together, and `go build` refuses a go.sum that disagrees with go.mod.

    Combinatorial rather than a priority chain, which is what this was: a chain returns the first
    feature it matches and silently ignores the rest, so it was correct only while no two
    dependency-adding options could be selected together — `net-http` and `keycloak` add no packages.
    The day one axis's answer adds a requirement beside another's, a chain names a variant that is
    missing half the dependency set and `go build` fails somewhere unrelated. Joined in the order
    above, so one set has exactly one name, and `base` for a selection that requires nothing at all.
    """
    chosen = [feature for feature in MODULE_FEATURES if selection.has(feature)]
    return "-".join(chosen) or "base"


def go_module(selection: Selection) -> str:
    return (LANGUAGE_ROOT / f"go/modules/{go_module_variant(selection)}/go.mod").read_text()


def go_checksums(selection: Selection) -> str | None:
    """The committed `go.sum`, or None for a variant that requires nothing."""
    path = LANGUAGE_ROOT / f"go/modules/{go_module_variant(selection)}/go.sum"
    return path.read_text() if path.is_file() else None


def go_language_version(module: str) -> str:
    """The `go` directive of a module file, so go.work cannot pin an older language than go.mod.

    A dependency may require a newer language version than the base module asks for, and
    `go mod tidy` raises the directive when it does. A workspace pinned lower than its only module
    is a workspace that refuses to build.
    """
    for line in module.splitlines():
        if line.startswith("go "):
            return line.split(None, 1)[1].strip()
    raise GenerationError("the committed go.mod has no `go` directive")

def name_service(project_name: str, service: App, files: dict[str, str]) -> dict[str, str]:
    """One service's files under this project's own module path: `example.com/<project>/<service>`."""
    # Every import of the service's own packages names the module path, so renaming the module
    # in go.mod alone would leave a project that does not compile.
    module = f"example.com/{project_name}/{service.name}"
    for path in list(files):
        if path.startswith(f"{service.path}/") and path.endswith((".go", "go.mod")):
            content = files[path].replace("example.com/delivery-starter", module)
            # What this service calls itself in a trace, for the same reason the module path is
            # rewritten: a name the exporter carries has to be the project's and not the template's.
            files[path] = content.replace(SERVICE_NAME, package_name(project_name, service))
    return files


def repository_files(
    project_name: str, files: dict[str, str], services: list[App], verify: str
) -> dict[str, str]:
    """The workspace above the services, the two gate scripts, and the verify script.

    One module per service and one `go.work` naming them all, which is what Go itself asks of a repository
    with more than one module: each service keeps its own `go.mod` and `go.sum` — the committed variants —
    so a second service is a second `use` line and not a second dependency set to lock. A shared module
    under `packages/` is one more `use` line, and every service imports it by path with no `replace`.

    The gate scripts are written once for the family, however many Go services there are: `make test`'s
    coverage gate and `make mutation`'s Gremlins wrapper, which stages a service beside the workspace modules
    it imports because Gremlins copies only the module it mutates (`project/mutation.py` has the account).
    The wrapper carries the pinned release, substituted here so the pin is written in one place. The verify
    script names the coverage gate beside itself rather than from the root, because a delivery layout moves
    `scripts/` and re-points every root-relative path but the ones inside code (`layout.py`).
    """
    uses = "".join(f"use ./{service.path}\n" for service in services)
    files["go.work"] = f"go {go_language_version(files[f'{services[0].path}/go.mod'])}\n\n{uses}"
    for script in (GO_COVERAGE_SCRIPT, GO_MUTATION_SCRIPT):
        files[script] = (LANGUAGE_ROOT / f"go/{script}").read_text().replace(GO_GREMLINS_TOKEN, GO_GREMLINS)
    apps = " ".join(service.path for service in services)
    files[verify] = f"""#!/bin/sh
set -eu
{GO_COVDATA_READY}
for app in {apps}; do
  test -z "$(gofmt -l "$app")"
  (cd "$app" && go vet ./... && {GO_STATICCHECK} && {GO_TEST_COMMAND})
  python3 "$(dirname "$0")/{GO_COVERAGE_SCRIPT.split('/')[-1]}" "$app" {GO_COVERAGE_MINIMUM}
done
"""
    return files
