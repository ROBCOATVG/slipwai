#!/usr/bin/env python3
"""The production verbs the Makefile hands off to: push, smoke, deploy, rollback, migrate.

Each `make` target is one line and this is where the lines meet: reading `project.json` for what the
services are, running `tofu` and the `az` CLI, and keeping the release record that makes a rollback a single
automated action rather than an archaeology exercise. Dependency-free on purpose — Python 3 is already what
every gate in this repository runs on — and every external command it runs is printed before it runs, so a
failure reads as the command that failed.

    scripts/deploy.py push <name>=<image> ...         push each built image, record the digests in .build/images.json
    scripts/deploy.py smoke-image <name>=<image> ...  run each built image locally and prove its probe answers
    scripts/deploy.py deploy <env>                    migrate, apply the service stack, upload the site, record the release
    scripts/deploy.py rollback <env>                  re-apply the release before the current one
    scripts/deploy.py promote [<commit>]              ask the forge to deploy production with what staging runs
    scripts/deploy.py promoting <env> [<commit>]      print the commit that would be promoted, and nothing else
    scripts/deploy.py migrate <env>                   run each service's migrations inside the environment
    scripts/deploy.py smoke <url>                     prove a deployed environment answers
    scripts/deploy.py url <env>                       print the environment's address
    scripts/deploy.py flag <env> <service> <k> <v>    set one feature flag, restart what reads it, smoke it
    scripts/deploy.py flags <env>                     print every flag, its value, and who set it when

`deploy`, `rollback`, `migrate` and `url` need the identifiers the bootstrap stack printed —
`TOFU_STATE_RESOURCE_GROUP`, `TOFU_STATE_ACCOUNT`, `TOFU_STATE_CONTAINER`, `AZURE_LOCATION`,
`AZURE_REGISTRY_ID`, `IMAGE_REGISTRY` — and an Azure sign-in the way any Azure tool finds one. `promote`
needs neither: it asks the forge to run `.github/workflows/production.yml`, and the runner does the work
with the deploy identity, which is why promoting from a laptop is not the same as applying from one.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra/service"
TFVARS = INFRA / "project.auto.tfvars.json"
BUILD = ROOT / ".build"
IMAGES = BUILD / "images.json"
# Liveness — the process is up and answering — and the fallback for anything this script cannot find a
# readiness path for. What gates traffic is the *readiness* path each service records in
# `infra/service/project.auto.tfvars.json`, which is the same value the App Service probe asks for: read
# rather than spelled again here, because two literals for one path is how a probe and the thing waiting
# on it drift apart.
HEALTH_PATH = "/health"
# How long a migrate job may run before it is stopped and the deploy fails. Generous for a real migration
# on the smallest Flexible Server; short enough that a job that is serving instead of migrating is caught.
# The job's own `replica_timeout_in_seconds` is the platform's version of this, and is set to match.
MIGRATION_MINUTES = 15
# The Static Web Apps CLI, pinned: it is the one tool this script runs that the repository does not build
# and the toolchain does not already carry, so the version is named here where a project can move it.
SWA_CLI = "@azure/static-web-apps-cli@2.0.10"


class Failure(Exception):
    """Something this script can name, printed without a traceback."""


def run(command: list[str], *, cwd: Path | None = None, capture: bool = False, env: dict | None = None) -> str:
    """A command this script is not reading writes to stderr, not stdout, so that this script's stdout carries
    only what the verb was asked for. `url` prints one line and nothing else because of this: it is read as
    `make smoke URL=$(make -s url ENV=staging)`, and `tofu init`'s chatter in front of that line — which
    begins with a blank one — would leave `URL` empty and smoke asking about no address at all."""
    print("+", " ".join(command), file=sys.stderr, flush=True)
    result = subprocess.run(
        command, cwd=cwd, text=True, env=env, stdout=subprocess.PIPE if capture else sys.stderr, check=False
    )
    if result.returncode != 0:
        raise Failure(f"`{command[0]}` exited {result.returncode}")
    return result.stdout if capture else ""


def which(tool: str) -> None:
    if shutil.which(tool) is None:
        raise Failure(f"{tool} is not on the PATH; infra/README.md lists what a deploy needs")


def manifest() -> dict:
    return json.loads((ROOT / "project.json").read_text())


def services() -> dict[str, dict]:
    return {
        name: record
        for name, record in manifest()["deployables"].items()
        if record.get("kind") == "service"
    }


def probe_paths() -> dict[str, str]:
    """Where each service answers "send me traffic", per service, from the stack's own variables."""
    document = json.loads(TFVARS.read_text()) if TFVARS.is_file() else {}
    return {
        name: record.get("health_path", HEALTH_PATH)
        for name, record in (document.get("services") or {}).items()
    }


def parse_images(arguments: list[str]) -> dict[str, str]:
    """`name=image` pairs, as the Makefile spells them."""
    images = {}
    for argument in arguments:
        name, _, image = argument.partition("=")
        if not name or not image:
            raise Failure(f"expected name=image, got {argument!r}")
        images[name] = image
    if not images:
        raise Failure("no images named")
    return images


# ── Images ─────────────────────────────────────────────────────────────────────────────────────────────


def digest_of(image: str) -> str:
    """The `repository@sha256:…` reference of a pushed image — what the service stack deploys."""
    inspected = run(["docker", "inspect", "--format", "{{json .RepoDigests}}", image], capture=True)
    repository = image.rsplit(":", 1)[0]
    for digest in json.loads(inspected):
        if digest.startswith(f"{repository}@"):
            return digest
    raise Failure(f"{image} has no digest for {repository}; was it pushed?")


def push(arguments: list[str]) -> None:
    """Push every image the Makefile built and write the digests down where `deploy` reads them.

    An image `pack build --publish` already sent to the registry is not in the daemon; it is pulled back by
    tag so its digest can be read the same way as the others'.
    """
    which("docker")
    recorded = {}
    for name, image in parse_images(arguments).items():
        present = subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0
        if present:
            run(["docker", "push", image])
        else:
            run(["docker", "pull", image])
        recorded[name] = digest_of(image)
    BUILD.mkdir(exist_ok=True)
    IMAGES.write_text(json.dumps(recorded, indent=2) + "\n")
    for name, digest in recorded.items():
        print(f"{name}: {digest}")
    print(f"recorded in {IMAGES.relative_to(ROOT)}")


def published_hosts() -> list[str]:
    """Where a port Docker published may answer from here.

    On a laptop, or a runner that is a bare VM, that is loopback. A containerised runner driving the host's
    daemon through a mounted socket — Gitea's act_runner, a job with `container:` — is not the machine the
    port is published on, so its own loopback refuses the connection and the host answers instead, as
    `host.docker.internal` where Docker publishes that name or as this container's default gateway where it
    does not. Tried in that order, so the common case costs nothing.
    """
    hosts = ["127.0.0.1", "host.docker.internal"]
    try:
        for line in Path("/proc/net/route").read_text().splitlines()[1:]:
            fields = line.split()
            if len(fields) > 2 and fields[1] == "00000000" and fields[2] != "00000000":
                gateway = int(fields[2], 16).to_bytes(4, "little")
                hosts.append(".".join(str(byte) for byte in gateway))
    except OSError:
        pass
    return hosts


def wait_for(port: str, path: str, seconds: int = 60) -> tuple[int, str, str]:
    """The probe's status and answer, and the host it answered on, from whichever published address reaches
    it.

    A 503 counts as an answer, and deliberately. This runs one image with nothing else running, so a
    service whose event store is a database nobody started is *correctly* not ready — and what is being
    proved here is the three things a broken build breaks: that the image starts, that it listens on PORT,
    and that it serves the probe. Whether it is ready is a question for an environment that has the
    backing services in it, which is `make smoke` against a deployed URL.
    """
    deadline = time.monotonic() + seconds
    error = "not tried"
    while time.monotonic() < deadline:
        for host in published_hosts():
            url = f"http://{host}:{port}{path}"
            try:
                with urllib.request.urlopen(url, timeout=3) as response:
                    return response.status, response.read().decode(), url
            except urllib.error.HTTPError as answered:
                return answered.code, answered.read().decode(), url
            except (urllib.error.URLError, OSError) as failure:
                error = f"{url}: {failure}"
        time.sleep(1)
    raise Failure(f"the published port {port} did not answer within {seconds}s: {error}")


def smoke_image(arguments: list[str]) -> None:
    """Run each built image the way a replica would and ask it the probe. Proves the image starts, listens
    on PORT, and answers — the three things a broken build breaks."""
    which("docker")
    ports = {name: record["port"] for name, record in services().items()}
    probes = probe_paths()
    for name, image in parse_images(arguments).items():
        if name.endswith("-migrate"):
            continue  # a migrate image runs to completion against a database; it has no probe to ask
        port = ports.get(name, 3000)
        # Published on every interface, not just the daemon host's loopback. `published_hosts` already knows
        # the prober and the daemon are two different machines on a containerised runner — but a port bound
        # to the host's loopback is reachable from nowhere else, so binding it there refuted every address
        # that function offers and the probe could only ever time out. The pair has to agree: the fallbacks
        # are worth having, so this is the end that gives way.
        container = run(
            ["docker", "run", "--detach", "--env", f"PORT={port}", "--publish", f"0:{port}", image],
            capture=True,
        ).strip()
        try:
            published = run(["docker", "port", container, str(port)], capture=True).split("\n")[0]
            probe = probes.get(name, HEALTH_PATH)
            status, body, url = wait_for(published.rsplit(":", 1)[1], probe)
            print(f"{name}: {image} answers {probe}: {status} {body.strip()} ({url})")
        except Failure:
            subprocess.run(["docker", "logs", container], stdout=sys.stderr, check=False)
            raise
        finally:
            subprocess.run(["docker", "rm", "--force", container], capture_output=True, check=False)


# ── The environment ────────────────────────────────────────────────────────────────────────────────────

# What `make bootstrap` wrote down beside the repository's variables, for a laptop whose environment does
# not carry them. One file per setting, so a reader can see what each is without decoding anything.
RECORDED = {
    "AZURE_LOCATION": "infra/location",
    "AZURE_REGISTRY_ID": "infra/registry-id",
    "IMAGE_REGISTRY": "infra/registry",
    "TOFU_STATE_RESOURCE_GROUP": "infra/state-resource-group",
    "TOFU_STATE_ACCOUNT": "infra/state-account",
    "TOFU_STATE_CONTAINER": "infra/state-container",
}


def setting(name: str) -> str:
    value = os.environ.get(name)
    if not value and name in RECORDED:
        # What `make bootstrap` wrote down, when the environment does not say. Put into the environment as
        # well, so `tofu` and `az` read the same answer.
        recorded = ROOT / RECORDED[name]
        value = recorded.read_text().strip() if recorded.is_file() else ""
        if value:
            os.environ[name] = value
    if not value:
        raise Failure(f"{name} is not set; the bootstrap stack's outputs say what it should be (infra/README.md)")
    return value


def registry_name() -> str:
    """The container registry's own name, from the login server the pipeline carries — `acrfoo.azurecr.io/`
    is `acrfoo`. One fact in one repository variable rather than two that could disagree."""
    return setting("IMAGE_REGISTRY").strip("/").split(".", 1)[0]


def tofu(*arguments: str, capture: bool = False) -> str:
    return run(["tofu", f"-chdir={INFRA}", *arguments], capture=capture)


def select_workspace(environment: str) -> None:
    which("tofu")
    which("az")
    tofu(
        "init", "-input=false", "-reconfigure",
        f"-backend-config=resource_group_name={setting('TOFU_STATE_RESOURCE_GROUP')}",
        f"-backend-config=storage_account_name={setting('TOFU_STATE_ACCOUNT')}",
        f"-backend-config=container_name={setting('TOFU_STATE_CONTAINER')}",
    )
    tofu("workspace", "select", "-or-create", environment)


def outputs() -> dict:
    return {name: value["value"] for name, value in json.loads(tofu("output", "-json", capture=True)).items()}


def apply(environment: str, images: dict[str, str], *targets: str) -> dict:
    tofu(
        "apply", "-input=false", "-auto-approve",
        f"-var-file={environment}.tfvars",
        f"-var=images={json.dumps(images)}",
        f"-var=location={setting('AZURE_LOCATION')}",
        f"-var=registry_id={setting('AZURE_REGISTRY_ID')}",
        f"-var=registry_server={setting('IMAGE_REGISTRY').strip('/')}",
        *(f"-target={target}" for target in targets),
    )
    return outputs()


# ── Migrations ─────────────────────────────────────────────────────────────────────────────────────────


def run_migrations(found: dict) -> None:
    """Each migrate job once, in the same environment as the app, waited on for at most
    `MIGRATION_MINUTES` and held to its outcome — and on a failure, its log printed before the deploy
    fails."""
    for name, job in found.get("migrate_jobs", {}).items():
        started = json.loads(run([
            "az", "containerapp", "job", "start",
            "--name", job["name"], "--resource-group", job["resource_group"], "--output", "json",
        ], capture=True) or "{}")
        execution = started.get("name") or started.get("id", "").rsplit("/", 1)[-1]
        if not execution:
            raise Failure(f"{name}: the migrate job was started but named no execution: {started}")
        status = wait_until_finished(name, job, execution)
        if status != "Succeeded":
            # The status says a migration failed; the log says why, and it is the only place that does.
            # Printed here rather than left for the reader to find, because the alternative is a trip to
            # the portal in the middle of a failed deploy, every time, in every project this factory
            # generates.
            print(migration_log(job, execution), file=sys.stderr)
            raise Failure(f"{name}: migrations finished {status}. The job's log is above.")
        print(f"{name}: migrations applied")


def execution_status(job: dict, execution: str) -> str:
    """What the platform says about one execution — `Running`, `Succeeded`, `Failed`, or `Unknown` where it
    will not say."""
    shown = run([
        "az", "containerapp", "job", "execution", "show",
        "--name", job["name"], "--resource-group", job["resource_group"],
        "--job-execution-name", execution, "--output", "json",
    ], capture=True)
    return (json.loads(shown or "{}").get("properties") or {}).get("status") or "Unknown"


def wait_until_finished(name: str, job: dict, execution: str) -> str:
    """The execution's final status, or a failure that says why it was still running.

    Polled here rather than left to the platform's own timeout, whose expiry leaves the execution in a
    state this script would have to interpret anyway. A migration that has not finished in
    `MIGRATION_MINUTES` is either a very long one or a job that is not migrating at all — the image's
    entrypoint started the service instead and it is sitting there serving, which is exactly what its log
    will show. Either way the execution is stopped, so a retry does not run beside it.
    """
    deadline = time.monotonic() + MIGRATION_MINUTES * 60
    while True:
        status = execution_status(job, execution)
        if status not in ("Running", "Processing", "Unknown"):
            return status
        if time.monotonic() >= deadline:
            break
        time.sleep(15)
    subprocess.run(
        ["az", "containerapp", "job", "stop", "--name", job["name"],
         "--resource-group", job["resource_group"], "--job-execution-name", execution, "--output", "json"],
        capture_output=True, check=False,
    )
    raise Failure(
        f"{name}: the migrate job was still running after {MIGRATION_MINUTES} minutes and has been stopped. "
        f"A migration that long is unusual; a job that is serving instead of migrating is an image whose "
        f"entrypoint ignored the command. Read the execution's log: a normal service start there is the "
        f"second case. {execution}"
    )


def migration_log(job: dict, execution: str) -> str:
    """What the failed migrate job printed, or a line saying where it would have been.

    Never raises: a deploy that failed on the migration must report the migration's failure, not a second
    one from trying to read about it. The CLI reads this out of the environment's Log Analytics workspace,
    which takes a minute or two to ingest — so an empty answer here is as likely to be "not yet" as "the
    container wrote nothing", and the line below says so rather than choosing.
    """
    read = subprocess.run(
        ["az", "containerapp", "job", "logs", "show", "--name", job["name"],
         "--resource-group", job["resource_group"], "--container", "migrate",
         "--tail", "200", "--output", "json"],
        text=True, capture_output=True, check=False,
    )
    if read.returncode != 0 or not read.stdout.strip():
        return (
            f"  no log could be read for {job['name']} / {execution}. Logs reach the workspace a minute or "
            f"two after the execution ends; `az containerapp job logs show --name {job['name']} "
            f"--resource-group {job['resource_group']} --container migrate` is this command by hand."
        )
    lines = "\n".join(f"  {line}" for line in read.stdout.strip().splitlines())
    return f"\n--- {job['name']} / {execution} ---\n{lines}\n--- end of log ---"


# ── The browser app ────────────────────────────────────────────────────────────────────────────────────


def web_app() -> dict | None:
    web = [record for record in manifest()["deployables"].values() if record.get("kind") == "web"]
    return web[0] if web else None


def shared_packages() -> list[str]:
    """The shared workspace packages that have something to build, in path order.

    Discovered rather than listed: `project.json`'s `layout.packages` says where shared code lives, and a
    directory under it whose `package.json` declares a `build` script is a package that emits something —
    typically the declarations an app imports, whose `dist/` is not committed. A list of names here would
    drift the first time somebody adds a package and does not think to come back; a project with no such
    directory, or none that builds, asks for nothing.
    """
    directory = ROOT / manifest().get("layout", {}).get("packages", "packages")
    found = []
    for descriptor in sorted(directory.glob("*/package.json")):
        try:
            scripts = json.loads(descriptor.read_text()).get("scripts") or {}
        except ValueError as unreadable:
            raise Failure(f"{descriptor.relative_to(ROOT)} is not readable JSON: {unreadable}") from unreadable
        if scripts.get("build"):
            found.append(descriptor.parent.relative_to(ROOT).as_posix())
    return found


def build_site(environment: dict[str, str]) -> Path | None:
    """The built bundle for this environment, or None where there is no browser app."""
    web = web_app()
    if web is None:
        return None
    which("npm")
    run(["npm", "ci"], cwd=ROOT)
    # The shared packages before the app that imports them, and both after `npm ci` — which is what creates
    # the workspace links a `--workspace` build resolves through. Their `dist/` is not committed, so a fresh
    # checkout has none and the app's build ends in a module it cannot resolve.
    for package in shared_packages():
        run(["npm", "--workspace", package, "run", "build"], cwd=ROOT)
    run(["npm", "--workspace", web["path"], "run", "build"], cwd=ROOT, env={**os.environ, **environment})
    return ROOT / web["path"] / "dist"


def upload_site(found: dict, sha: str, environment: dict[str, str]) -> None:
    """Build the bundle for this environment and upload it, and keep a copy of the release for rollback.

    Unlike the AWS target, the site is not a bucket this stack writes objects into one at a time: Static
    Web Apps owns its own content and takes a whole bundle at once, through its CLI and a deployment token.
    So the cache headers are the app's own `staticwebapp.config.json` rather than per-object metadata set
    here, and the copy a rollback restores is kept beside the release records in the state container rather
    than under the site.
    """
    site = found.get("web_site")
    token = found.get("web_deployment_token")
    dist = build_site(environment)
    if not site or not token or dist is None:
        return
    which("npx")
    run([
        "npx", "--yes", SWA_CLI, "deploy", str(dist),
        "--deployment-token", token, "--env", "production", "--no-use-keychain",
    ], cwd=ROOT)
    keep_bundle(sha, dist)


def site_environment(found: dict) -> dict[str, str]:
    """What the browser app's bundle is built with in this environment.

    One source: the stack's `web_environment`, which is what an apply decided.

    Feature flags are deliberately not here. They were, read from this environment's values and inlined by
    Vite at build time, and that gave one product flag two clocks: the service's moved in a restart, the
    browser's only when the environment was deployed again. The bundle now asks the service instead, over
    `GET /api/flags`, so a flip reaches both halves at once and nothing about a flag is baked into a build.
    `apps/<web>/src/flags.ts` is that side of it.
    """
    if web_app() is None:
        return {}
    return dict(found.get("web_environment", {}))


def bundles_prefix(environment: str) -> str:
    return f"bundles/{environment}/"


def keep_bundle(sha: str, dist: Path) -> None:
    """A copy of this release's bundle, so a rollback has one to put back.

    The whole bundle rather than `index.html` alone, which is where this differs from the AWS target and
    has to: there the assets live in the bucket for ever under hashed names and `index.html` is the pointer
    at them, so restoring the pointer restores the release. Static Web Apps replaces its content wholesale
    on every deployment, so the previous release's assets are gone the moment the next one lands and only a
    copy of the whole bundle can bring it back.
    """
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / "bundle.tar.gz"
        run(["tar", "-C", str(dist), "-czf", str(archive), "."])
        blob_upload(archive, f"{bundles_prefix(current_environment())}{sha}.tar.gz")


def restore_site(found: dict, sha: str) -> None:
    site = found.get("web_site")
    token = found.get("web_deployment_token")
    if not site or not token or web_app() is None:
        return
    which("npx")
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / "bundle.tar.gz"
        dist = Path(directory) / "dist"
        dist.mkdir()
        blob_download(f"{bundles_prefix(current_environment())}{sha}.tar.gz", archive)
        run(["tar", "-C", str(dist), "-xzf", str(archive)])
        run([
            "npx", "--yes", SWA_CLI, "deploy", str(dist),
            "--deployment-token", token, "--env", "production", "--no-use-keychain",
        ], cwd=ROOT)


# ── The release record ─────────────────────────────────────────────────────────────────────────────────

# Which environment the verb in flight is acting on. Set once by every verb that selects a workspace, so
# that the blob helpers below — which are about *where* a thing is kept, not about which environment it
# belongs to — do not each have to be handed it.
_ENVIRONMENT = "staging"


def current_environment() -> str:
    return _ENVIRONMENT


def blob(*arguments: str, capture: bool = False) -> str:
    """One `az storage blob` call against the state container, as ourselves.

    `--auth-mode login` throughout: the state account has no shared key — `shared_access_key_enabled` is
    false in the bootstrap stack — so there is no key to fall back on and the deploy identity's
    `Storage Blob Data Contributor` assignment is the whole of how this reaches it.
    """
    return run([
        "az", "storage", "blob", *arguments,
        "--account-name", setting("TOFU_STATE_ACCOUNT"),
        "--container-name", setting("TOFU_STATE_CONTAINER"),
        "--auth-mode", "login", "--output", "json",
    ], capture=capture)


def blob_upload(path: Path, name: str) -> None:
    blob("upload", "--file", str(path), "--name", name, "--overwrite", capture=True)


def blob_download(name: str, path: Path) -> None:
    blob("download", "--name", name, "--file", str(path), capture=True)


def blob_names(prefix: str) -> list[str]:
    listed = json.loads(blob("list", "--prefix", prefix, capture=True) or "[]")
    return [item["name"] for item in listed]


def releases_prefix(environment: str) -> str:
    return f"releases/{environment}/"


def record_release(environment: str, sha: str, images: dict[str, str], rollback_of: str | None = None) -> None:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    record = {"sha": sha, "images": images, "at": stamp, **({"rollback_of": rollback_of} if rollback_of else {})}
    path = BUILD / f"release-{environment}.json"
    BUILD.mkdir(exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n")
    blob_upload(path, f"{releases_prefix(environment)}{stamp}-{sha}.json")


def releases(environment: str) -> list[dict]:
    """Every release of this environment, newest first."""
    names = sorted(blob_names(releases_prefix(environment)), reverse=True)
    found = []
    with tempfile.TemporaryDirectory() as directory:
        for name in names:
            path = Path(directory) / "release.json"
            blob_download(name, path)
            found.append(json.loads(path.read_text()))
            path.unlink()
    return found


def uncreated(environment: str) -> str:
    """What to say about an environment nothing has deployed yet, which for production is a state a project
    can be in on purpose — `AUTO_PROMOTE=false` leaves it uncreated until the first promotion."""
    if environment == "production":
        return (
            "production has not been deployed yet, so there is nothing there to address. `make promote` "
            "creates it with the commit staging is running."
        )
    return f"{environment} has not been deployed yet; `make deploy ENV={environment}` is what creates it."


def current_sha() -> str:
    return os.environ.get("GIT_SHA") or run(["git", "rev-parse", "HEAD"], capture=True, cwd=ROOT).strip()


def image_names() -> list[str]:
    """Every image the project builds: each service's, and the migrate image a backend builds beside it."""
    data = json.loads(TFVARS.read_text())
    names = []
    for name, service in data["services"].items():
        names.append(name)
        if service.get("migrate_image"):
            names.append(service["migrate_image"])
    return names


def images_of(sha: str) -> dict[str, str]:
    """This commit's images by digest — from `make push`'s record when it is here, else looked up in the
    registry by the commit's tag, which is what lets a deploy job run on a fresh checkout with nothing
    handed to it but the commit."""
    if IMAGES.is_file():
        return json.loads(IMAGES.read_text())
    registry = setting("IMAGE_REGISTRY")
    project = json.loads(TFVARS.read_text())["project"]
    found = {}
    for name in image_names():
        repository = f"{project}-{name}"
        digest = run([
            "az", "acr", "repository", "show", "--name", registry_name(),
            "--image", f"{repository}:{sha}", "--query", "digest", "--output", "tsv",
        ], capture=True).strip()
        if not digest.startswith("sha256:"):
            raise Failure(f"no image tagged {sha} in {repository}; has `make push` run for this commit?")
        found[name] = f"{registry}{repository}@{digest}"
    return found


def select(environment: str) -> None:
    global _ENVIRONMENT
    _ENVIRONMENT = environment
    select_workspace(environment)


def deploy(environment: str) -> None:
    """Expand first: the migrations run before the new revision rolls, so the release still serving keeps the
    schema it knows and the one arriving finds the schema it needs — which is what `make check-migrations`
    holds every migration to. The migrate jobs alone are applied with the new images (a targeted apply, the
    one place this pipeline uses one), the migrations run, and then the whole stack is applied. A fresh
    environment has nothing running yet, so it is applied whole and migrated after; so is a project whose
    services migrate as they start (Flyway), which has no job to run."""
    select(environment)
    sha = current_sha()
    images = images_of(sha)
    if outputs().get("migrate_jobs"):
        apply(environment, images, "azurerm_container_app_job.migrate")
        run_migrations(outputs())
        found = apply(environment, images)
    else:
        found = apply(environment, images)
        run_migrations(found)
    upload_site(found, sha, site_environment(found))
    record_release(environment, sha, images)
    print(f"\n{environment}: {found['url']}")
    for name, address in found.get("urls", {}).items():
        print(f"  {name}: {address}")
    linked = found.get("web_api_service")
    if linked:
        print(f"  {linked}: through the site only — it is the linked API backend and has no address of its own")


def rollback(environment: str) -> None:
    select(environment)
    history = releases(environment)
    if not history:
        raise Failure(uncreated(environment))
    if len(history) < 2:
        raise Failure(f"{environment} has {len(history)} release(s) recorded; there is nothing earlier to return to")
    current, previous = history[0], history[1]
    print(f"rolling {environment} back from {current['sha']} to {previous['sha']}", file=sys.stderr)
    found = apply(environment, previous["images"])
    restore_site(found, previous["sha"])
    record_release(environment, previous["sha"], previous["images"], rollback_of=current["sha"])
    print(f"\n{environment}: {found['url']} is running {previous['sha']} again")


def migrate(environment: str) -> None:
    select(environment)
    found = outputs()
    if not found.get("migrate_jobs"):
        print(f"{environment}: no service here runs its migrations as a job")
        return
    run_migrations(found)


def url(environment: str) -> None:
    select(environment)
    found = outputs()
    if "url" not in found:
        # An empty workspace, which is what a project deploying production by hand has until the first
        # promotion. `tofu` makes the workspace on selection, so there is nothing to distinguish this from
        # a fresh environment by, and "KeyError: url" is the wrong way to say it.
        raise Failure(uncreated(environment))
    print(found["url"])


# ── Promotion ──────────────────────────────────────────────────────────────────────────────────────────

# The workflow that deploys production, by the name the forge knows it by. Started from the Actions tab, or
# by `promote` below.
PROMOTION_WORKFLOW = "production.yml"
# The shortest prefix `promoting` will match a commit by, so a typo cannot silently name the wrong release.
SHORTEST_SHA = 7


def promoting(arguments: list[str]) -> None:
    """The commit production would be given: the one asked for, or the one `environment` is running now.

    Prints that one line and nothing else — `production.yml` reads it as a step output, the way `make smoke`
    reads `url`. A commit asked for explicitly is refused unless that environment has a release record for
    it, which is what keeps "production only ever runs what staging has run" true even when a person types
    the commit themselves.
    """
    if not arguments or len(arguments) > 2:
        raise Failure("expected: promoting <environment> [<commit>]")
    environment = arguments[0]
    # Empty rather than absent is what the workflow passes when its input was left blank.
    wanted = (arguments[1] if len(arguments) > 1 else "").strip()
    history = releases(environment)
    if not history:
        raise Failure(
            f"{environment} has no release recorded, so there is nothing to promote from it. "
            f"Push to main and let the pipeline deploy {environment} first."
        )
    if not wanted:
        print(history[0]["sha"])
        return
    if len(wanted) < SHORTEST_SHA:
        raise Failure(f"{wanted!r} is too short to name a commit; give at least {SHORTEST_SHA} characters")
    matched = [record["sha"] for record in history if record["sha"].startswith(wanted)]
    if not matched:
        recent = ", ".join(f"{record['sha'][:12]} ({record['at']})" for record in history[:5])
        raise Failure(
            f"{environment} has no release of {wanted}; production is only ever given a commit "
            f"{environment} has run. Recent releases there: {recent}"
        )
    if len({sha for sha in matched}) > 1:
        raise Failure(f"{wanted!r} names more than one release of {environment}: {', '.join(sorted(set(matched)))}")
    print(matched[0])


def origin() -> tuple[str, str, str]:
    """The forge this repository is on, as (kind, api, owner/name), from the `origin` remote.

    The same reading `scripts/bootstrap.py` makes of the same remote, deliberately: two scripts in this
    directory that disagreed about which forge a repository is on would be worse than either being wrong.
    So the host is taken as it stands and never rewritten — a forge whose ssh host differs from its web host
    (`git-ssh.example.com` against `git.example.com`) is not something a remote says, and guessing at it
    would send a token somewhere nobody named. The API is HTTP whatever the remote's scheme is, so an
    `ssh://` remote is read over https; if that address is not the forge, the refusal below names it.
    """
    url = run(["git", "remote", "get-url", "origin"], capture=True, cwd=ROOT).strip()
    # Both spellings a remote comes in: scp-like (`git@host:owner/name.git`) and a URL.
    if "://" in url:
        scheme, _, rest = url.partition("://")
        host, _, path = rest.partition("/")
    else:
        scheme, host, path = "https", *url.partition(":")[::2]
    host = host.rpartition("@")[2]
    repository = path.removesuffix(".git").strip("/")
    if repository.count("/") != 1:
        raise Failure(f"the origin remote {url!r} does not end in owner/name")
    kind = "github" if host.endswith("github.com") else "gitea"
    return kind, f"{scheme if scheme in ('http', 'https') else 'https'}://{host}/api/v1", repository


def promote(arguments: list[str]) -> None:
    """Ask the forge to deploy production with the commit staging is running.

    This does not apply anything. It dispatches `production.yml`, and the runner does the work with the
    deploy identity — the same identity and the same `make deploy` the pipeline uses — so `make promote`
    from a laptop is not `tofu apply` from a laptop, which this project never does.

    It says which commit it expects to be promoted when it can read staging's release record, and says it
    could not when it cannot: the answer belongs to the run, which resolves it again for itself, and a
    laptop without access to the state account can still promote.
    """
    if len(arguments) > 1:
        raise Failure("expected: promote [<commit>]")
    wanted = (arguments[0] if arguments else "").strip()
    kind, api, repository = origin()
    try:
        history = releases("staging")
        expected = history[0] if history else None
    except Failure as unreadable:
        history, expected = None, None
        print(f"(cannot read staging's releases from here: {unreadable})", file=sys.stderr)
    if history is not None and not history:
        raise Failure(
            "staging has no release recorded, so there is nothing to promote. Push to main and let the "
            "pipeline deploy staging first."
        )
    if kind == "github":
        which("gh")
        command = ["gh", "workflow", "run", PROMOTION_WORKFLOW, "--repo", repository]
        if wanted:
            command += ["-f", f"commit={wanted}"]
        run(command)
    else:
        token = os.environ.get("GITEA_TOKEN")
        if not token:
            raise Failure(
                f"a token is needed to start {PROMOTION_WORKFLOW} on {api}: set GITEA_TOKEN (a token with "
                f"write access to {repository}), or start it from the Actions tab"
            )
        dispatch(api, repository, token, {"commit": wanted} if wanted else {})
    if expected is not None and not wanted:
        print(f"promoting {expected['sha']}, which staging has been running since {expected['at']}")
    elif wanted:
        print(f"promoting {wanted}, if staging has run it — the run refuses it if not")
    print(f"started {PROMOTION_WORKFLOW} on {repository}; watch it in the forge's Actions tab.")


def dispatch(api: str, repository: str, token: str, inputs: dict[str, str]) -> None:
    """Start `production.yml` on a Gitea-shaped forge. `main` is the ref the workflow is read from; what it
    deploys is decided inside the run, not by this."""
    address = f"{api}/repos/{repository}/actions/workflows/{PROMOTION_WORKFLOW}/dispatches"
    body = json.dumps({"ref": "main", "inputs": inputs}).encode()
    request = urllib.request.Request(
        address, data=body, method="POST",
        headers={
            "Authorization": f"token {token}", "Content-Type": "application/json",
            # The default `Python-urllib/3.x` is a banned signature on proxies that front a self-hosted
            # forge, and that refusal reads exactly like a bad token until the body is read.
            "User-Agent": "slipwai-deploy",
        },
    )
    print("+ POST", address, file=sys.stderr)
    try:
        with urllib.request.urlopen(request) as response:
            response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode()[:300]
        hint = ""
        if error.code == 404:
            hint = (
                f" — {PROMOTION_WORKFLOW} has to be on the default branch for the forge to know it, and the "
                "token needs write access"
            )
        raise Failure(f"the forge answered {error.code} starting {PROMOTION_WORKFLOW}{hint}: {detail}") from error
    except urllib.error.URLError as unreachable:
        # The address was read off the `origin` remote, so an unreachable one is most often a forge whose
        # ssh host is not its web host. Name it, rather than reporting a bare connection error.
        raise Failure(
            f"{address} could not be reached ({unreachable.reason}). That address is this repository's "
            "`origin` remote; if the forge answers on another, start production.yml from its Actions tab."
        ) from unreachable


# ── Feature flags ──────────────────────────────────────────────────────────────────────────────────────


def flag_state(environment: str) -> dict:
    """This environment's outputs, selected and read once.

    The whole of them rather than the `flags` output alone, because flipping a flag also has to smoke the
    environment afterwards and the address it asks is `url` — the same output a deploy smokes.
    """
    select(environment)
    return outputs()


def vault_value(vault: str, secret: str) -> str:
    """What a Key Vault secret is set to now, or a marker where it cannot be read."""
    try:
        return json.loads(run([
            "az", "keyvault", "secret", "show", "--vault-name", vault, "--name", secret, "--output", "json",
        ], capture=True) or "{}").get("value", "")
    except Failure:
        return "(cannot be read)"


def vault_history(vault: str, secret: str) -> tuple[str, str]:
    """When the live version of a secret was written, and by nothing more than that.

    The audit trail a flip has here is thinner than the AWS target's, and this is where that shows.
    A parameter store keeps the identity that wrote each version beside it; Key Vault keeps the version's
    timestamps and not its author — who wrote it is in the vault's *diagnostic* logs, which are a
    subscription-level setting this stack does not turn on. So `make flags` answers "what is it, and when
    did it last move", and for "who" the answer is the vault's audit log if one is enabled. Said plainly
    rather than left as a blank column.
    """
    try:
        versions = json.loads(run([
            "az", "keyvault", "secret", "list-versions", "--vault-name", vault, "--name", secret,
            "--output", "json",
        ], capture=True) or "[]")
    except Failure:
        return "", ""
    live = [version for version in versions if (version.get("attributes") or {}).get("enabled")]
    if not live:
        return "", ""
    newest = max(live, key=lambda version: str((version.get("attributes") or {}).get("created", "")))
    created = str((newest.get("attributes") or {}).get("created", ""))[:19]
    return created, str(len(versions))


def appconfig_of(found: dict) -> dict | None:
    """This environment's App Configuration identifiers, or None where it reads its flags from Key Vault."""
    settings = found.get("appconfig")
    return settings if isinstance(settings, dict) else None


def appconfig_set(settings: dict, key: str, value: str) -> None:
    run([
        "az", "appconfig", "kv", "set", "--endpoint", settings["endpoint"], "--auth-mode", "login",
        "--key", key, "--label", settings["label"], "--value", value, "--yes", "--output", "json",
    ], capture=True)


def appconfig_values(settings: dict) -> dict[str, str]:
    listed = json.loads(run([
        "az", "appconfig", "kv", "list", "--endpoint", settings["endpoint"], "--auth-mode", "login",
        "--label", settings["label"], "--output", "json",
    ], capture=True) or "[]")
    return {item["key"]: item.get("value", "") for item in listed}


def flag_key(identifier: str) -> str:
    """`api/checkout-v2` as App Configuration and the environment both spell it: `FLAG_CHECKOUT_V2`."""
    return "FLAG_" + identifier.partition("/")[2].replace("-", "_").upper()


def flag(arguments: list[str]) -> None:
    """Set one flag, restart what reads it, and prove the environment answers.

    The first two steps are what the shape buys everywhere else: the value reaches the container as an
    environment variable Container Apps resolves when a replica *starts*, so replicas already running are
    holding the old one. Restarting the revision brings new replicas up with the new value. Left alone the
    platform would find the new version of a versionless reference within half an hour; this does not wait,
    and a flip costs no build, no apply and no merge to `main` — it costs the couple of minutes a restart
    takes.

    The last step is that couple of minutes spent rather than guessed at. A flip is a production change
    made with no `verify`, no review and no pipeline behind it, so the one cheap thing available is to ask
    the environment the same question a deploy asks. It smokes the environment's public address — the site
    where there is one — which is what a deploy smokes; it is not a test of the feature the flag just
    revealed, and the person who flipped it still has to look.

    Nothing about this reaches the release record `deploy` keeps: a release names a commit and its images,
    and a flag flipped afterwards is not in it. `flags` below is where an environment's current answer
    lives, and it is the only place it lives.
    """
    if len(arguments) != 4:
        raise Failure("expected: flag <environment> <service> <key> <value>")
    environment, service, key, value = arguments
    state = flag_state(environment)
    found = state.get("flags") or {}
    secrets = found.get("secrets", {})
    identifier = f"{service}/{key}"
    # What the stack was told is declared, which is the same under either transport — `secrets` is empty
    # under `appconfig`, because there is no vault secret for the stack to have created.
    known = found.get("declared") or secrets
    if identifier not in known:
        declared = ", ".join(sorted(known)) or "none"
        raise Failure(
            f"{environment} has no flag {identifier} (declared: {declared}). "
            "A flag is declared in infra/service/flags.auto.tfvars and reaches an environment on the next deploy."
        )
    settings = appconfig_of(found)
    if settings is not None:
        # No restart at all: the application re-reads the store.
        appconfig_set(settings, flag_key(identifier), value)
        print(f"{environment}: {identifier} = {value}, live — no restart. `make flags ENV={environment}`.")
        smoke(state["url"])
        return
    run([
        "az", "keyvault", "secret", "set", "--vault-name", found["vault"],
        "--name", secrets[identifier], "--value", value, "--output", "json",
    ], capture=True)
    app = found.get("apps", {}).get(service)
    if not app:
        raise Failure(f"{environment} has no service {service}; the secret is set but nothing was restarted")
    revision = json.loads(run([
        "az", "containerapp", "revision", "list", "--name", app,
        "--resource-group", found["resource_group"], "--query", "[?properties.active].name",
        "--output", "json",
    ], capture=True) or "[]")
    for name in revision:
        run([
            "az", "containerapp", "revision", "restart", "--name", app,
            "--resource-group", found["resource_group"], "--revision", name, "--output", "json",
        ], capture=True)
    print(f"{environment}: {identifier} = {value}. {app} is restarting to read it; `make flags ENV={environment}` shows the environment.")
    web = web_app()
    if web is not None and web.get("api") == service:
        # Both halves move on this one restart. Worth saying at the moment of the flip, because the browser
        # used to need a deploy of its own and anybody who has flipped a flag here before will expect to
        # owe one.
        print(
            f"  {web['path']} reads this flag too, and asks {service} for it: the restart above moves "
            f"both halves, and a browser already open picks it up on its next load. No deploy is owed."
        )
    smoke(state["url"])


def flags(environment: str) -> None:
    """Every flag this environment declares, what it is set to *now*, and when it last moved.

    What it is set to is what `flags.auto.tfvars` says only until somebody flips one, since the stack stops
    managing a value the moment it has seeded it — so this is the answer, and the column beside it is the
    vault's own version history rather than anything this project keeps.
    """
    found = (flag_state(environment).get("flags") or {})
    secrets = found.get("secrets", {})
    settings = appconfig_of(found)
    declared = found.get("declared") or {}
    if settings is not None:
        if not declared:
            print(f"{environment} declares no feature flags (infra/service/flags.auto.tfvars is where they go)")
            return
        values = appconfig_values(settings)
        width = max(len(identifier) for identifier in declared)
        for identifier in sorted(declared):
            value = values.get(flag_key(identifier), "(not yet deployed)")
            print(f"{identifier:<{width}}  {value}")
        return
    if not secrets:
        print(f"{environment} declares no feature flags (infra/service/flags.auto.tfvars is where they go)")
        return
    vault = found["vault"]
    width = max(len(identifier) for identifier in secrets)
    for identifier in sorted(secrets):
        value = vault_value(vault, secrets[identifier])
        when, versions = vault_history(vault, secrets[identifier])
        print(f"{identifier:<{width}}  {value:<4}  {when}  {versions and f'v{versions}' or ''}".rstrip())
    print(
        "\nWho set a value is not here: Key Vault keeps a version's timestamps and not its author. "
        "Turn on the vault's diagnostic logging if that answer is needed.",
        file=sys.stderr,
    )


def fetch(address: str) -> tuple[int, dict[str, str], str]:
    request = urllib.request.Request(address, headers={"User-Agent": "slipwai-smoke"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read().decode()


def smoke(address: str) -> None:
    """What proves a deploy: the probe answers, and — with a site in front — the site is served uncached
    and `/api` reaches the service. Each assertion names the URL it asked.

    Identical to the AWS target's, and that is the point rather than a coincidence. With a site in front,
    `/health` is the site's route (the probe sits outside `/api`, so the site answers it with its fallback
    document) and the service is reached through its own 404 shape instead. Static Web Apps proxies `/api`
    to the *same path* on the linked container app, so `/api/health` is a path the service does not have
    and answers `404 {"error":"notFound"}` for — which is exactly what it does behind CloudFront.
    """
    address = address.rstrip("/")
    # The *readiness* path, the same one the App Service probe gates traffic on, so a release whose event
    # store it cannot reach fails here rather than passing a smoke test and then failing every request.
    probe = next(iter(probe_paths().values()), HEALTH_PATH)
    if web_app() is None:
        status, _headers, body = fetch(f"{address}{probe}")
        if status != 200 or "status" not in body:
            raise Failure(f"{address}{probe} answered {status}: {body[:200]}")
        print(f"{address}{probe}: {status} {body.strip()}")
        return
    status, headers, body = fetch(f"{address}/")
    if status != 200 or "text/html" not in headers.get("content-type", ""):
        raise Failure(f"{address}/ answered {status} {headers.get('content-type')}")
    if "no-store" not in headers.get("cache-control", ""):
        raise Failure(f"{address}/ is cacheable ({headers.get('cache-control')!r}); index.html must be no-store")
    print(f"{address}/: {status}, {headers.get('cache-control')}")
    status, headers, body = fetch(f"{address}/api{HEALTH_PATH}")
    if status != 404 or "notFound" not in body:
        raise Failure(f"{address}/api{HEALTH_PATH} answered {status}: {body[:200]} — /api is not reaching the service")
    print(f"{address}/api{HEALTH_PATH}: {status} {body.strip()} (the service, through the site)")


VERBS = {
    "push": push,
    "smoke-image": smoke_image,
    "deploy": lambda arguments: deploy(*arguments),
    "rollback": lambda arguments: rollback(*arguments),
    "promote": promote,
    "promoting": promoting,
    "migrate": lambda arguments: migrate(*arguments),
    "smoke": lambda arguments: smoke(*arguments),
    "url": lambda arguments: url(*arguments),
    "flag": flag,
    "flags": lambda arguments: flags(*arguments),
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in VERBS:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        VERBS[argv[0]](argv[1:])
    except Failure as failure:
        print(f"deploy: {failure}", file=sys.stderr)
        return 1
    except TypeError:
        # The verb is real but its arguments are not: `make smoke URL=` with an unset URL reaches here as
        # `smoke` with nothing after it, and the usage alone does not say which of the two is missing.
        print(f"deploy: `{argv[0]}` was not given the arguments it needs\n", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
