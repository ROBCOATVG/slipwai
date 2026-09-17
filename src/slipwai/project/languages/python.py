"""The Python backend: each service's package, its manifest and committed lock, and the verify script above them."""
from __future__ import annotations

from ...assets import LANGUAGE_ROOT, asset_tree
from ...backends import UV_VERSION
from ...naming import python_package_name
from ...selection import Selection
from ...services import App
from ...tooling import service_qualifier
from ..backing_services import backing_service_service_files
from ..composition import wire_store
from ..flag_route import wire_entry
from ..flags import flag_reader
from ..openapi import published_document


def service_files(event: bool, selection: Selection, target: str = "none") -> dict[str, str]:
    """What this backend puts in a service's directory, keyed relative to it."""
    files = asset_tree(LANGUAGE_ROOT / "python/app")
    if event and not selection.has("memory"):
        # Only for a backend whose event-store axis is not offered yet: a port with a shape and no adapter
        # behind it. Once the axis is asked, the port and its adapters arrive together from the assets, and
        # this placeholder would only be a second definition of the same thing.
        files.update(asset_tree(LANGUAGE_ROOT / "python/event-port"))
    files.update(backing_service_service_files(selection, "python"))
    # The flag reader, only where there is somewhere to deploy: a flag is what makes a merge and a release
    # two decisions, and `--target none` has neither the mechanism nor the unsafe push. See `flags.py`.
    files.update(flag_reader(target, "python"))
    # And the entry point's half of it: the source is handed to `build_app`, which is what puts
    # `/api/flags` in front of the browser app. Removed, not left unresolved, where there is no reader.
    wire_entry(files, target)
    # And the store's half: which adapter this project opens, and what `/ready` is handed. See
    # `composition.py` — the entry point is the only place that may name the answer.
    wire_store(files, selection, "python")
    # The published contract, committed beside the service: which of the two shapes it takes is the same
    # condition that decides whether `/api/flags` is a route at all.
    files.update(published_document(selection, target))
    # Last, because the selection decides which dependencies are in the manifest — and which of the
    # committed locks is the one resolved from exactly that manifest.
    files["pyproject.toml"] = python_pyproject(files["pyproject.toml"], selection)
    files["uv.lock"] = service_lock(selection)
    return files


# The tools every Python service's gate runs, whatever it was given. Pinned exactly, and the same versions
# the factory holds itself to — the factory should not be checked by a stricter tool than the one it hands
# its own output. mypy beside pytest and ruff, because `typecheck` is a type check: `compileall` only
# proves the files parse.
BASE_DEVELOPMENT = ("mypy==2.3.1", "pytest==9.1.1", "ruff==0.16.3")

# What each feature pins, split by where it belongs: `runtime` is what the service imports when it is
# running and is therefore what the production image carries, `development` what only the gate needs. One
# table rather than a branch per feature, and kept in step with `PACKAGE_EDITS` in
# assets/backing-services/prune.py, which drops exactly these distributions again when the feature is
# pruned; the factory's test suite asserts the two agree.
FEATURE_REQUIREMENTS: dict[str, dict[str, tuple[str, ...]]] = {
    # The binary wheel, so an install needs no libpq and no compiler.
    "postgres": {"runtime": ("psycopg[binary]==3.3.4",), "development": ()},
    # The framework, the settings model the composition root checks the environment against, the
    # server — and the telemetry the transport is the only thing that can produce: one span per
    # request, continuing whatever `traceparent` arrived. The API and the SDK are separate
    # distributions by OpenTelemetry's own design — the API is what code calls, the SDK what a
    # process installs — and the OTLP exporter is a third, because `tracing.py` only constructs
    # one when an endpoint was named; the instrumentation's versions run on their own `0.<n>b0`
    # line. Pydantic itself is not pinned here: it arrives with FastAPI, which is what decides which
    # major it works against. `httpx` is development-only — it is what `TestClient` drives the app
    # with, and a running service never imports it.
    "fastapi": {
        "runtime": (
            "fastapi==0.141.1",
            "opentelemetry-api==1.44.0",
            "opentelemetry-exporter-otlp-proto-http==1.44.0",
            "opentelemetry-instrumentation-fastapi==0.65b0",
            "opentelemetry-sdk==1.44.0",
            "pydantic-settings==2.15.0",
            "uvicorn==0.52.4",
        ),
        "development": ("httpx==0.28.1",),
    },
}

# The only features that add a Python distribution, and therefore the only ones that change the lock. Read
# combinatorially the way TypeScript's `LOCK_FEATURES` is, so one dependency set has exactly one name.
LOCK_FEATURES = ("fastapi", "postgres")


def requirements(selection: Selection) -> tuple[list[str], list[str]]:
    """This selection's runtime and development distributions, each sorted and pinned."""
    runtime: list[str] = []
    development = list(BASE_DEVELOPMENT)
    for feature, pins in FEATURE_REQUIREMENTS.items():
        if not selection.has(feature):
            continue
        runtime += pins["runtime"]
        development += pins["development"]
    return sorted(runtime), sorted(development)


def dependency_array(pins: list[str]) -> str:
    """A PEP 621 dependency array, one pin per line — the shape `uv add` writes and `uv lock` reads."""
    if not pins:
        return "[]"
    return "[\n" + "".join(f'  "{pin}",\n' for pin in pins) + "]"


def python_pyproject(source: str, selection: Selection) -> str:
    """The service manifest with the dependencies this selection actually needs.

    Written into the template's two empty arrays rather than assembled here, so everything that is *not*
    a dependency — the pytest, mypy, ruff and uv settings, and the prose above each of them — lives in
    `assets/` like every other generated file's body.
    """
    runtime, development = requirements(selection)
    return source.replace("dependencies = []", f"dependencies = {dependency_array(runtime)}", 1).replace(
        "dev = []", f"dev = {dependency_array(development)}", 1
    )


def lock_suffix(selection: Selection) -> str:
    """The committed lock's name for this selection's dependency set: '' for the plain one,
    '-fastapi-postgres' for both. Sorted by `LOCK_FEATURES`, so one dependency set has exactly one name."""
    return "".join(f"-{feature}" for feature in LOCK_FEATURES if selection.has(feature))


def service_lock(selection: Selection) -> str:
    """The committed `uv.lock` resolved from exactly the manifest this selection produces.

    Committed per dependency set rather than resolved at generation time, for the reason the npm and Go
    locks are: `uv sync --locked` refuses a lock that disagrees with its manifest, generation must work
    offline, and two people generating the same answers a week apart must get the same versions. The
    template's name is rewritten into the project's by `name_service`, exactly as the npm locks' is.
    """
    return (LANGUAGE_ROOT / f"python/locks/uv{lock_suffix(selection)}.lock").read_text()


def python_verify(services: list[App]) -> str:
    """The verify script, run once for the whole repository and looping over the services itself.

    `--ignore` for the integration directory is unconditional, and that is deliberate: it is correct whether
    or not the directory exists, so pruning Postgres cannot leave behind a command that needs it. A marked
    region could not do this — a prune only subtracts, and there would be no un-ignored variant left to
    restore.

    Every tool runs through `uv run --no-sync`, out of the environment `uv sync --locked` built from that
    service's committed lock. One environment per service, beside its own manifest, because a service's
    dependencies are its own; `uv sync` is idempotent and near-instant once the environment is there, so
    every mode can simply ask for it rather than guessing from a directory's existence.
    """
    apps = " ".join(service.path for service in services)
    return f"""#!/bin/sh
set -eu
# One directory per service, from project.json; every mode below runs for each of them in turn.
apps="{apps}"
mode="${{1:-all}}"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is this backend's toolchain and is not on the PATH." >&2
  echo "Install it from https://docs.astral.sh/uv/, or: python3 -m pip install uv=={UV_VERSION}" >&2
  exit 2
fi
for app in $apps; do
  # From the committed lock and nothing else. `--locked` is the `npm ci` of this ecosystem: it installs
  # exactly what uv.lock names and refuses, rather than re-resolving, when pyproject.toml has gained or
  # lost a dependency the lock does not carry. (`--frozen`, its quieter sibling, installs the stale lock
  # and says nothing, which is the failure this gate exists to catch.) No network where the two agree.
  uv sync --project "$app" --locked --quiet
done
[ "$mode" = --install-only ] && exit 0
for app in $apps; do
  # The db-backed suite lives in tests/integration/ and runs only from `make test-integration`, so the
  # default gate stays runnable with no Docker. Ignoring a directory that does not exist is harmless.
  default_suite="$app/tests --ignore=$app/tests/integration"
  # mypy runs from the repository root over one service at a time, so it is told where that service's
  # modules live rather than reading a relative `mypy_path`: the package under `src/`, the shared contract
  # suites under `tests/`, and `tests/integration/`, whose modules import each other by bare name because
  # that is how pytest puts them on the path. A directory that is not there is ignored. The settings —
  # `check_untyped_defs` above all — are in the service's `pyproject.toml`, so a bare `mypy src tests`
  # from the service directory is the same check.
  mypy_path="$app/src:$app/tests:$app/tests/integration"
  # The environment above, without asking uv to check it again for every tool in turn.
  run="uv run --project $app --no-sync"
  case "$mode" in
    --lint-only)
      $run ruff check "$app/src" "$app/tests"
      $run ruff format --check "$app/src" "$app/tests" ;;
    # The half of lint that writes. `make format` is what runs it; no gate does, because a gate that
    # rewrites the tree it is judging is a gate that always passes.
    --format) $run ruff format "$app/src" "$app/tests" ;;
    --typecheck-only)
      python3 -m compileall -q "$app/src" "$app/tests"
      MYPYPATH="$mypy_path" $run mypy --config-file "$app/pyproject.toml" "$app/src" "$app/tests" ;;
    --test-only) PYTHONPATH="$app/src" $run pytest $default_suite ;;
    --migrate)
      if [ -f "$app/migrations/apply.py" ]; then
        $run python "$app/migrations/apply.py"
      else
        echo "migrate: $app has no migrations"
      fi ;;
    --integration-only)
      if [ -d "$app/tests/integration" ]; then
        PYTHONPATH="$app/src" $run pytest "$app/tests/integration"
      else
        echo "test-integration: $app has no integration tests yet"
      fi ;;
    --adversarial-only)
      status=0
      PYTHONPATH="$app/src" $run pytest $default_suite -k adversarial || status=$?
      [ "$status" -eq 0 ] || [ "$status" -eq 5 ] ;;
    all)
      $run ruff check "$app/src" "$app/tests"
      $run ruff format --check "$app/src" "$app/tests"
      PYTHONPATH="$app/src" $run pytest $default_suite
      python3 -m compileall -q "$app/src" "$app/tests"
      MYPYPATH="$mypy_path" $run mypy --config-file "$app/pyproject.toml" "$app/src" "$app/tests" ;;
    *) echo "unknown verify mode: $mode" >&2; exit 2 ;;
  esac
done
"""


def name_service(project_name: str, service: App, files: dict[str, str]) -> dict[str, str]:
    """One service's files under its own package name.

    Both the paths and the imports inside them are rewritten: a Python service's importable package is
    named after the project (and, after the first, the service), and renaming the directory alone leaves a
    project that cannot import itself. The lock is renamed with the manifest, because `uv sync --locked`
    refuses a lock whose project is not the one in the manifest beside it.
    """
    python_package = python_package_name(service_qualifier(project_name, service))
    distribution = f"{project_name}-{service.name}"
    pyproject = f"{service.path}/pyproject.toml"
    files[pyproject] = (
        files[pyproject]
        .replace('name = "delivery-starter"', f'name = "{distribution}"')
        .replace("delivery_starter", python_package)
    )
    lock = f"{service.path}/uv.lock"
    files[lock] = files[lock].replace('name = "delivery-starter"', f'name = "{distribution}"')
    old_package_path = f"{service.path}/src/delivery_starter/"
    for path in list(files):
        if not path.startswith(f"{service.path}/"):
            continue
        new_path = path
        if path.startswith(old_package_path):
            new_path = f"{service.path}/src/{python_package}/" + path.removeprefix(old_package_path)
        if new_path != path:
            files[new_path] = files.pop(path).replace("delivery_starter", python_package)
        elif path.startswith(f"{service.path}/tests/"):
            files[path] = files[path].replace("delivery_starter", python_package)
    # The published document names the service the way FastAPI does — after this package — so the token
    # is resolved here rather than by a second rule about what a document may call a service.
    document = f"{service.path}/openapi.json"
    if document in files:
        files[document] = files[document].replace("__SERVICE_NAME__", python_package)
    return files


def repository_files(
    project_name: str, files: dict[str, str], services: list[App], verify: str
) -> dict[str, str]:
    """The verify script above the services; nothing else sits at the root for this backend."""
    files[verify] = python_verify(services)
    return files
