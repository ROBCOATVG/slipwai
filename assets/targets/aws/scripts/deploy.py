#!/usr/bin/env python3
"""The production verbs the Makefile hands off to: push, smoke, deploy, rollback, migrate.

Each `make` target is one line and this is where the lines meet: reading `project.json` for what the
services are, running `tofu` and the `aws` CLI, and keeping the release record that makes a rollback a single
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

`deploy`, `rollback`, `migrate` and `url` need `TOFU_STATE_BUCKET` and `AWS_REGION` in the environment — the
identifiers the bootstrap stack printed — and AWS credentials the way any AWS tool finds them. `promote`
needs neither: it asks the forge to run `.github/workflows/production.yml`, and the runner does the work
with the deploy role, which is why promoting from a laptop is not the same as applying from one.
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
# `infra/service/project.auto.tfvars.json`, which is the same value the load balancer's health check asks
# for: read rather than spelled again here, because two literals for one path is how a probe and the thing
# waiting on it drift apart.
HEALTH_PATH = "/health"
# How long a migrate task may run before it is stopped and the deploy fails. Generous for a real migration
# on the smallest RDS instance; short enough that a task that is serving instead of migrating is caught.
MIGRATION_MINUTES = 15
# How many times a failed task's log stream is read before it is called empty. A task reported STOPPED has
# usually flushed, but not always, and the lines that explain the failure are the last ones written.
LOG_ATTEMPTS = 4


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
    """Run each built image the way a task would and ask it the probe. Proves the image starts, listens on
    PORT, and answers — the three things a broken build breaks."""
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
        # are worth having, so this is the end that gives way. It is one ephemeral high port for the few
        # seconds the container lives, which is what `docker-compose.yml` does for Postgres all day.
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


def setting(name: str) -> str:
    value = os.environ.get(name)
    if not value and name == "AWS_REGION":
        # The region `make bootstrap` wrote down, when the environment does not say. Put into the
        # environment as well, so `tofu` and `aws` read the same answer.
        region_file = ROOT / "infra/region"
        value = region_file.read_text().strip() if region_file.is_file() else ""
        if value:
            os.environ["AWS_REGION"] = value
    if not value:
        raise Failure(f"{name} is not set; the bootstrap stack's outputs say what it should be (infra/README.md)")
    return value


def tofu(*arguments: str, capture: bool = False) -> str:
    return run(["tofu", f"-chdir={INFRA}", *arguments], capture=capture)


def select_workspace(environment: str) -> None:
    which("tofu")
    which("aws")
    tofu(
        "init", "-input=false", "-reconfigure",
        f"-backend-config=bucket={setting('TOFU_STATE_BUCKET')}",
        f"-backend-config=region={setting('AWS_REGION')}",
    )
    tofu("workspace", "select", "-or-create", environment)


def outputs() -> dict:
    return {name: value["value"] for name, value in json.loads(tofu("output", "-json", capture=True)).items()}


def apply(environment: str, images: dict[str, str], *targets: str) -> dict:
    tofu(
        "apply", "-input=false", "-auto-approve",
        f"-var-file={environment}.tfvars",
        f"-var=images={json.dumps(images)}",
        *(f"-target={target}" for target in targets),
    )
    return outputs()


def run_migrations(found: dict) -> None:
    """Each migrate task once, inside the VPC, waited on for at most `MIGRATION_MINUTES` and held to its exit
    code — and on a non-zero one, its log printed before the deploy fails."""
    for name, task in found.get("migrate_tasks", {}).items():
        network = json.dumps({
            "awsvpcConfiguration": {
                "subnets": task["subnets"],
                "securityGroups": task["security_groups"],
                "assignPublicIp": "ENABLED",
            }
        })
        # By family, not by revision: the latest ACTIVE revision is the one the apply just registered, whatever
        # a targeted apply left in the outputs.
        started = json.loads(run([
            "aws", "ecs", "run-task", "--cluster", task["cluster"], "--task-definition", task["family"],
            "--launch-type", "FARGATE", "--network-configuration", network, "--output", "json",
        ], capture=True))
        if started.get("failures"):
            raise Failure(f"{name}: the migrate task was not started: {started['failures']}")
        arn = started["tasks"][0]["taskArn"]
        stopped = wait_until_stopped(name, task["cluster"], arn)
        container = stopped["containers"][0]
        if container.get("exitCode") != 0:
            # The exit code says a migration failed; the log says why, and it is the only place that does —
            # a container's `reason` is ECS's ("Essential container in task exited"), never the
            # application's. Printed here rather than left for the reader to find, because the alternative
            # is a trip to the CloudWatch console in the middle of a failed deploy, every time, in every
            # project this factory generates.
            print(migration_log(task, arn), file=sys.stderr)
            raise Failure(
                f"{name}: migrations exited {container.get('exitCode')} "
                f"({container.get('reason') or stopped.get('stoppedReason')}). "
                "The task's log is above."
            )
        print(f"{name}: migrations applied")


def migration_log(task: dict, arn: str) -> str:
    """What the failed migrate task printed, or a line saying where it would have been.

    The stream name is the `awslogs` configuration the task definition carries — `<prefix>/<container>/<id>`
    — with the id being the last segment of the task ARN; `log_group` and `log_stream` come from
    `migrate_tasks` (rds.tf) so this never has to guess either half. Never raises: a deploy that failed on
    the migration must report the migration's failure, not a second one from trying to read about it.
    """
    group = task.get("log_group")
    if not group:
        # An environment applied before this output existed. Worth saying rather than crashing: the exit
        # code and `stoppedReason` still get reported, and the next apply adds the output.
        return f"  (this environment's outputs name no log group for {task.get('family')}; re-apply to add it)"
    stream = f"{task['log_stream']}/{arn.rsplit('/', 1)[-1]}"
    # Retried, briefly, because a task reported STOPPED is not a promise that its last lines have been
    # ingested — and the interesting lines are always the last ones. An empty stream after this is a
    # container that really never wrote, which is a different failure and says so.
    for attempt in range(LOG_ATTEMPTS):
        try:
            events = json.loads(run([
                "aws", "logs", "get-log-events", "--log-group-name", group, "--log-stream-name", stream,
                "--start-from-head", "--output", "json",
            ], capture=True))["events"]
        except (Failure, KeyError, ValueError) as reading:
            return f"  could not read {group} {stream}: {reading}"
        if events:
            lines = "\n".join(f"  {event['message']}" for event in events)
            return f"\n--- {group} {stream} ---\n{lines}\n--- end of log ---"
        if attempt + 1 < LOG_ATTEMPTS:
            time.sleep(3)
    # A task that failed before its container ran — an image it could not pull, a secret it could not read
    # — writes nothing here, and `stoppedReason` in the failure above is where that case is named.
    return f"  {group} {stream} is empty: the container produced no output before it exited"


def wait_until_stopped(name: str, cluster: str, arn: str) -> dict:
    """The task once it has stopped, or a failure that says why it was still running.

    Polled here rather than left to `aws ecs wait tasks-stopped`, whose ten minutes end in "Max attempts
    exceeded" and a task left running. A migration that has not finished in `MIGRATION_MINUTES` is either a
    very long one or a task that is not migrating at all — the image's entrypoint started the service
    instead and it is sitting there serving, which is exactly what its log stream will show. Either way the
    task is stopped, so a retry does not run beside it, and the failure says where to look.
    """
    deadline = time.monotonic() + MIGRATION_MINUTES * 60
    while True:
        described = json.loads(run([
            "aws", "ecs", "describe-tasks", "--cluster", cluster, "--tasks", arn, "--output", "json",
        ], capture=True))
        found = described["tasks"][0]
        if found["lastStatus"] == "STOPPED":
            return found
        if time.monotonic() >= deadline:
            break
        time.sleep(15)
    run([
        "aws", "ecs", "stop-task", "--cluster", cluster, "--task", arn, "--output", "json",
        "--reason", f"migrations still running after {MIGRATION_MINUTES} minutes",
    ], capture=True)
    raise Failure(
        f"{name}: the migrate task was still running after {MIGRATION_MINUTES} minutes and has been stopped. "
        f"A migration that long is unusual; a task that is serving instead of migrating is an image whose "
        f"entrypoint ignored the command. Read the task's log stream (prefix `migrate/`, in the service's log "
        f"group): a normal service start there is the second case. {arn}"
    )


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


def upload_site(found: dict, sha: str, environment: dict[str, str]) -> None:
    """Build the bundle for this environment and upload it: assets first, immutable; index.html last, as
    the release pointer, with a copy kept for rollback."""
    bucket = found.get("web_bucket")
    web = web_app()
    if not bucket or web is None:
        return
    which("npm")
    run(["npm", "ci"], cwd=ROOT)
    # The shared packages before the app that imports them, and both after `npm ci` — which is what creates
    # the workspace links a `--workspace` build resolves through. Their `dist/` is not committed, so a fresh
    # checkout has none and the app's build ends in a module it cannot resolve; this runs after the applies,
    # so failing here leaves an environment already changed with no release recorded.
    for package in shared_packages():
        run(["npm", "--workspace", package, "run", "build"], cwd=ROOT)
    run(["npm", "--workspace", web["path"], "run", "build"], cwd=ROOT, env={**os.environ, **environment})
    dist = ROOT / web["path"] / "dist"
    run([
        "aws", "s3", "sync", str(dist), f"s3://{bucket}/", "--exclude", "index.html",
        "--cache-control", "public, max-age=31536000, immutable",
    ])
    index = dist / "index.html"
    run(["aws", "s3", "cp", str(index), f"s3://{bucket}/releases/{sha}/index.html", "--cache-control", "no-store"])
    run(["aws", "s3", "cp", str(index), f"s3://{bucket}/index.html", "--cache-control", "no-store"])


def site_environment(found: dict) -> dict[str, str]:
    """What the browser app's bundle is built with in this environment.

    One source: the stack's `web_environment`, which is what an apply decided — the customer pool's issuer
    and client id, when there is one.

    Feature flags are deliberately not here. They were, as `VITE_FLAG_<KEY>` read from this environment's
    parameters and inlined by Vite at build time, and that gave one product flag two clocks: the service's
    moved in a restart, the browser's only when the environment was deployed again. The bundle now asks the
    service instead, over `GET /api/flags`, so a flip reaches both halves at once and nothing about a flag
    is baked into a build. `apps/<web>/src/flags.ts` is that side of it.
    """
    if web_app() is None:
        return {}
    return dict(found.get("web_environment", {}))


def restore_site(found: dict, sha: str) -> None:
    bucket = found.get("web_bucket")
    if bucket and web_app() is not None:
        run([
            "aws", "s3", "cp", f"s3://{bucket}/releases/{sha}/index.html", f"s3://{bucket}/index.html",
            "--cache-control", "no-store",
        ])


def releases_prefix(environment: str) -> str:
    return f"s3://{setting('TOFU_STATE_BUCKET')}/releases/{environment}/"


def record_release(environment: str, sha: str, images: dict[str, str], rollback_of: str | None = None) -> None:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    record = {"sha": sha, "images": images, "at": stamp, **({"rollback_of": rollback_of} if rollback_of else {})}
    path = BUILD / f"release-{environment}.json"
    BUILD.mkdir(exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n")
    run(["aws", "s3", "cp", str(path), f"{releases_prefix(environment)}{stamp}-{sha}.json"])


def releases(environment: str) -> list[dict]:
    """Every release of this environment, newest first."""
    listing = run(["aws", "s3", "ls", releases_prefix(environment)], capture=True)
    keys = sorted((line.split()[-1] for line in listing.splitlines() if line.strip()), reverse=True)
    found = []
    for key in keys:
        body = run(["aws", "s3", "cp", f"{releases_prefix(environment)}{key}", "-"], capture=True)
        found.append(json.loads(body))
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
            "aws", "ecr", "describe-images", "--repository-name", repository,
            "--image-ids", f"imageTag={sha}", "--query", "imageDetails[0].imageDigest", "--output", "text",
        ], capture=True).strip()
        if not digest.startswith("sha256:"):
            raise Failure(f"no image tagged {sha} in {repository}; has `make push` run for this commit?")
        found[name] = f"{registry}{repository}@{digest}"
    return found


def deploy(environment: str) -> None:
    """Expand first: the migrations run before the new revision rolls, so the release still serving keeps the
    schema it knows and the one arriving finds the schema it needs — which is what `make check-migrations`
    holds every migration to. The migrate task definitions alone are applied with the new images (a targeted
    apply, the one place this pipeline uses one), the migrations run, and then the whole stack is applied. A
    fresh environment has nothing running yet, so it is applied whole and migrated after; so is a project
    whose services migrate as they start (Flyway), which has no task to run."""
    sha = current_sha()
    images = images_of(sha)
    select_workspace(environment)
    if outputs().get("migrate_tasks"):
        apply(environment, images, "aws_ecs_task_definition.migrate")
        run_migrations(outputs())
        found = apply(environment, images)
    else:
        found = apply(environment, images)
        run_migrations(found)
    # Under `appconfig` the stack does not own the flag document, so a newly declared flag reaches this
    # environment here rather than in the apply above. A no-op under `ssm`, where the parameters are the
    # stack's, and a no-op once a key is in the document.
    reconcile_flags(found.get("flags") or {})
    upload_site(found, sha, site_environment(found))
    record_release(environment, sha, images)
    print(f"\n{environment}: {found['url']}")
    for name, address in found.get("urls", {}).items():
        print(f"  {name}: {address}")


def rollback(environment: str) -> None:
    select_workspace(environment)
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
    select_workspace(environment)
    found = outputs()
    if not found.get("migrate_tasks"):
        print(f"{environment}: no service here runs its migrations as a task")
        return
    run_migrations(found)


def url(environment: str) -> None:
    select_workspace(environment)
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
    deploy role — the same role and the same `make deploy` the pipeline uses — so `make promote` from a
    laptop is not `tofu apply` from a laptop, which this project never does.

    It says which commit it expects to be promoted when it can read staging's release record, and says it
    could not when it cannot: the answer belongs to the run, which resolves it again for itself, and a
    laptop without credentials for the state bucket can still promote.
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
    select_workspace(environment)
    return outputs()


def flag_history(names: list[str]) -> dict[str, tuple[str, str, str]]:
    """What each parameter is set to now, who set it and when — keyed by parameter name.

    The audit trail a flip has is the parameter store's own: SSM keeps every version of a parameter with
    the identity that wrote it and the moment it did, so `make flags` can answer "who turned this on, and
    when" without this project storing anything to make that true. A flip is not in the release record and
    never will be, so this is the only place that answer lives.

    One call per parameter, which `get-parameters` does not need — but history is per name, and a project
    with a handful of flags is what this is for. A parameter that cannot be read at all is reported as
    such rather than failing the listing: it means somebody removed it out of band, which is worth seeing
    beside the flags that are fine.
    """
    found: dict[str, tuple[str, str, str]] = {}
    for name in names:
        try:
            read = json.loads(run([
                "aws", "ssm", "get-parameter-history", "--name", name, "--output", "json",
            ], capture=True))
        except Failure:
            continue
        versions = read.get("Parameters") or []
        if not versions:
            continue
        # The highest `Version`, not the last row. SSM stamps every version with an increasing number and
        # documents that field; it does not promise the order the history comes back in, and the CLI's own
        # auto-pagination stitches pages together in whatever order it received them. Reading the last row
        # therefore works until the day it does not, and the day it does not `make flags` reports a
        # superseded value as the live one — which is the single question this command exists to answer,
        # asked in the middle of deciding whether a bad flip or a bad release is what broke production.
        current = max(versions, key=lambda version: int(version.get("Version", 0)))
        # The identity is an ARN — an IAM user, or the assumed deploy role with its session name. The
        # account and partition in front of it are the same for every row, so only the tail is printed.
        who = str(current.get("LastModifiedUser", "")).rsplit(":", 1)[-1] or "unknown"
        when = str(current.get("LastModifiedDate", ""))[:19] or "unknown"
        found[name] = (current.get("Value", ""), when, who)
    return found


def flag_values(names: list[str]) -> dict[str, str]:
    """What each named parameter is set to now, keyed by parameter name.

    Ten at a time: `get-parameters` takes no more, and a project with eleven flags should not discover that
    in production. A name the call does not answer for is absent from the result rather than guessed at —
    both callers say what they do about that, and they say different things.
    """
    values: dict[str, str] = {}
    for start in range(0, len(names), 10):
        read = json.loads(run([
            "aws", "ssm", "get-parameters", "--names", *names[start:start + 10], "--output", "json",
        ], capture=True))
        values.update({parameter["Name"]: parameter["Value"] for parameter in read.get("Parameters", [])})
    return values


# ── The AppConfig transport ────────────────────────────────────────────────────────────────────────────
#
# Where `flag_transport = "appconfig"` puts the values. One hosted configuration document per environment,
# not a parameter per flag, which is why the stack owns the profile and this file owns the content: a stack
# owning the document would rewrite every flag on every unattended apply. `flags.tf` has the argument.


def appconfig_of(found: dict) -> dict | None:
    """This environment's AppConfig identifiers, or None where it reads its flags from the parameters."""
    settings = found.get("appconfig")
    return settings if isinstance(settings, dict) else None


def hosted_version(settings: dict) -> tuple[int, dict[str, str]]:
    """The latest hosted configuration version's number and content — `(0, {})` before the first one.

    The number is what makes a flip safe to run twice at once: it is handed back to
    `create-hosted-configuration-version` as `--latest-version-number`, which refuses the write if anything
    landed in between. Two people flipping two flags at the same moment is otherwise a lost update, because
    a document is read, changed and written whole where a parameter was not.
    """
    listed = json.loads(run([
        "aws", "appconfig", "list-hosted-configuration-versions",
        "--application-id", settings["application"],
        "--configuration-profile-id", settings["profile"],
        "--max-items", "1", "--output", "json",
    ], capture=True))
    items = listed.get("Items") or []
    if not items:
        return 0, {}
    number = int(items[0]["VersionNumber"])
    with tempfile.NamedTemporaryFile(suffix=".json") as handle:
        run([
            "aws", "appconfig", "get-hosted-configuration-version",
            "--application-id", settings["application"],
            "--configuration-profile-id", settings["profile"],
            "--version-number", str(number), "--output", "json", handle.name,
        ], capture=True)
        content = json.loads(Path(handle.name).read_text() or "{}")
    return number, {key: str(value) for key, value in content.items()}


def deploy_flags(settings: dict, flags: dict[str, str], latest: int) -> None:
    """Write the document and deploy it, which is the whole of a flip under this transport.

    No restart: the agent beside each task polls AppConfig and the running process re-reads it. One
    deployment may be in flight per environment — a second is refused rather than queued — so a collision
    here is loud, which with one shared document is what you want.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
        handle.write(json.dumps(flags, indent=2, sort_keys=True))
        handle.flush()
        created = json.loads(run([
            "aws", "appconfig", "create-hosted-configuration-version",
            "--application-id", settings["application"],
            "--configuration-profile-id", settings["profile"],
            "--content", f"fileb://{handle.name}",
            "--content-type", "application/json",
            "--latest-version-number", str(latest),
            "--output", "json", "/dev/stdout",
        ], capture=True) or "{}")
    version = created.get("VersionNumber", latest + 1)
    run([
        "aws", "appconfig", "start-deployment",
        "--application-id", settings["application"],
        "--environment-id", settings["environment"],
        "--deployment-strategy-id", settings["strategy"],
        "--configuration-profile-id", settings["profile"],
        "--configuration-version", str(version), "--output", "json",
    ], capture=True)


def reconcile_flags(found: dict) -> None:
    """Give a new environment the flags `flags.auto.tfvars` declares, at their seeds.

    The stack creates the parameters under `ssm`; under `appconfig` there is nothing for it to create,
    because it does not own the document. So a declared key that the document has never carried is added
    here, at its seed, on the deploy that follows the declaration — and a key already in the document is
    left exactly as it is, which is the same promise `ignore_changes = [value]` makes on the other side.
    """
    settings = appconfig_of(found)
    declared = found.get("declared") or {}
    if settings is None or not declared:
        return
    latest, flags = hosted_version(settings)
    missing = {key: seed for key, seed in declared.items() if key not in flags}
    if not missing:
        return
    stated = ", ".join(f"{key}={seed}" for key, seed in sorted(missing.items()))
    print(f"seeding {len(missing)} flag(s) this environment has never carried: {stated}", file=sys.stderr)
    deploy_flags(settings, {**flags, **missing}, latest)


def flag(arguments: list[str]) -> None:
    """Set one flag, restart the service that reads it, wait for it, and prove the environment answers.

    The first two steps are what the shape buys everywhere else: the value reaches the container as an
    environment variable ECS resolves when a task *starts*, so tasks already running are holding the old
    one. `--force-new-deployment` is a blue/green deploy of the revision already deployed — new tasks come
    up beside the old, pass their health checks, take the traffic, and the old ones drain — so a flip costs
    no build, no apply and no merge to `main`, but it does cost the couple of minutes that takes.

    The last two steps are that couple of minutes spent rather than guessed at. A flip is a production
    change made with no `verify`, no review and no pipeline behind it, so the one cheap thing available is
    to wait for the deployment it already forces and then ask the environment the same question a deploy
    asks: `services-stable`, then `smoke`. It smokes the environment's public address — the site where
    there is one — which is what a deploy smokes; it is not a test of the feature the flag just revealed,
    and the person who flipped it still has to look.

    Nothing about this reaches the release record `deploy` keeps: a release names a commit and its images,
    and a flag flipped afterwards is not in it. `flags` below is where an environment's current answer
    lives, and it is the only place it lives.
    """
    if len(arguments) != 4:
        raise Failure("expected: flag <environment> <service> <key> <value>")
    environment, service, key, value = arguments
    state = flag_state(environment)
    found = state.get("flags") or {}
    parameters = found.get("parameters", {})
    identifier = f"{service}/{key}"
    # What the stack was told is declared, which is the same under either transport — `parameters` is empty
    # under `appconfig`, because there is nothing for the stack to have created.
    known = found.get("declared") or parameters
    if identifier not in known:
        declared = ", ".join(sorted(known)) or "none"
        raise Failure(
            f"{environment} has no flag {identifier} (declared: {declared}). "
            "A flag is declared in infra/service/flags.auto.tfvars and reaches an environment on the next deploy."
        )
    settings = appconfig_of(found)
    if settings is not None:
        # No restart at all: the agent polls, and the tasks already running pick the value up.
        latest, flags = hosted_version(settings)
        deploy_flags(settings, {**flags, identifier: value}, latest)
        print(f"{environment}: {identifier} = {value}, live — no restart. `make flags ENV={environment}`.")
        smoke(state["url"])
        return
    run([
        "aws", "ssm", "put-parameter", "--name", parameters[identifier], "--type", "String",
        "--value", value, "--overwrite", "--output", "json",
    ], capture=True)
    name = found.get("services", {}).get(service)
    if not name:
        raise Failure(f"{environment} has no service {service}; the parameter is set but nothing was restarted")
    run([
        "aws", "ecs", "update-service", "--cluster", found["cluster"], "--service", name,
        "--force-new-deployment", "--output", "json",
    ], capture=True)
    print(f"{environment}: {identifier} = {value}. {name} is restarting to read it; `make flags ENV={environment}` shows the environment.")
    web = web_app()
    if web is not None and web.get("api") == service:
        # Both halves move on this one restart now. Worth saying at the moment of the flip, because the
        # browser used to need a deploy of its own and anybody who has flipped a flag here before will
        # expect to owe one.
        print(
            f"  {web['path']} reads this flag too, and asks {service} for it: the restart above moves "
            f"both halves, and a browser already open picks it up on its next load. No deploy is owed."
        )
    run([
        "aws", "ecs", "wait", "services-stable", "--cluster", found["cluster"], "--services", name,
    ], capture=True)
    smoke(state["url"])


def flags(environment: str) -> None:
    """Every flag this environment declares, what it is set to *now*, and who set it when.

    What it is set to is what `flags.auto.tfvars` says only until somebody flips one, since the stack stops
    managing a value the moment it has seeded it — so this is the answer, and the columns beside it are the
    parameter store's own version history rather than anything this project keeps.
    """
    found = (flag_state(environment).get("flags") or {})
    parameters = found.get("parameters", {})
    settings = appconfig_of(found)
    if settings is not None:
        declared = found.get("declared") or {}
        if not declared:
            print(f"{environment} declares no feature flags (infra/service/flags.auto.tfvars is where they go)")
            return
        _latest, flags = hosted_version(settings)
        width = max(len(identifier) for identifier in declared)
        for identifier in sorted(declared):
            # A declared key the document has never carried reads as off, which is what the agent answers
            # for it too; the next `make deploy` seeds it.
            value = flags.get(identifier, "(not yet deployed)")
            print(f"{identifier:<{width}}  {value}")
        return
    if not parameters:
        print(f"{environment} declares no feature flags (infra/service/flags.auto.tfvars is where they go)")
        return
    history = flag_history([parameters[identifier] for identifier in sorted(parameters)])
    width = max(len(identifier) for identifier in parameters)
    for identifier in sorted(parameters):
        value, when, who = history.get(parameters[identifier], ("(cannot be read)", "", ""))
        print(f"{identifier:<{width}}  {value:<4}  {when}  {who}".rstrip())


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

    The probe asked is the *readiness* one, the same path the load balancer gates traffic on, so a release
    whose event store it cannot reach fails here rather than passing a smoke test and then failing every
    request."""
    address = address.rstrip("/")
    probe = next(iter(probe_paths().values()), HEALTH_PATH)
    if web_app() is None:
        status, _headers, body = fetch(f"{address}{probe}")
        if status != 200 or "status" not in body:
            raise Failure(f"{address}{probe} answered {status}: {body[:200]}")
        print(f"{address}{probe}: {status} {body.strip()}")
        return
    # Behind CloudFront `/health` is the site's route (the probe sits outside `/api`, so the bucket answers it
    # with index.html); the service is reached through the proxy's own 404 shape instead.
    status, headers, body = fetch(f"{address}/")
    if status != 200 or "text/html" not in headers.get("content-type", ""):
        raise Failure(f"{address}/ answered {status} {headers.get('content-type')}")
    if "no-store" not in headers.get("cache-control", ""):
        raise Failure(f"{address}/ is cacheable ({headers.get('cache-control')!r}); index.html must be no-store")
    print(f"{address}/: {status}, {headers.get('cache-control')}")
    status, headers, body = fetch(f"{address}/api{HEALTH_PATH}")
    if status != 404 or "notFound" not in body:
        raise Failure(f"{address}/api{HEALTH_PATH} answered {status}: {body[:200]} — /api is not reaching the service")
    print(f"{address}/api{HEALTH_PATH}: {status} {body.strip()} (the service, through the proxy)")


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
