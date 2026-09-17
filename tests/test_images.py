"""Every backend's production image: built the way `make build` builds it, started the way an ECS task
starts it, and asked its readiness probe — `make build smoke-image`, the two targets `make ci` runs in a generated
project.

This is the proof "hello world to production" rests on, and the one a real deploy found missing: an image
can build and push perfectly and still die at start — a launch point the buildpack copied before it was
written, a PYTHONPATH that replaced the buildpack's own. Only starting the container catches that.

The migrate task's proof — that the buildpack launcher runs the `command` the image's own entrypoint
ignores — is `test_launcher.py`, built on the same `ImageProbe` base: it is about the builder, not about any
backend, and runs once where this runs per backend. In CI this suite rides in each backend's `matrix` job,
sliced by `FACTORY_BACKENDS` like the matrix itself, so five images build beside each other on one daemon:
everything a run puts on the daemon carries the backend or the process in its name for that reason.

A backend whose builder is `pack` publishes to a registry: Docker Desktop's containerd image store cannot
take a `pack` export directly (buildpacks/pack#2272), so the test starts a throwaway `registry:2` on the
daemon's own loopback — on the host network, listening on 127.0.0.1 itself rather than behind a published
port — and tells `pack`'s containers to share that network to reach it. The daemon then pulls the result
from the same address for the smoke. No port proxy sits on either path, which is what a published port
would have put there and what intermittently refused the connection (run 216). Those backends are
also built for Fargate's platform, `linux/amd64`, wherever this machine can run such a container — the
platform the pipeline builds, and the one that same image store has reliably exported the builder for; its
own platform otherwise. Every `pack` build in this file is for that one platform, the launcher probe
included: `--pull-policy if-not-present` hands pack whichever variant of the builder the daemon already
holds, and a build for the other platform then fails reading layers the daemon never pulled — `failed to
fetch base layers: open …/blobs/sha256/…: no such file` (run 228, on a Mac runner that had just built for
amd64). `IMAGE_REGISTRY` in the environment names a registry to use instead; `PACK_FLAGS` in the
environment is passed on, for a machine that needs more (a proxy's certificate, a mirrored run image).

Every `pack` build here names its build cache (`pack_cache`). Left to pack, the cache volume is named after
the image, and the image here is named after a registry on a port chosen at random — so on CI no build ever
found the cache the one before it left, and every run downloaded CPython, the Node engine and every Maven
dependency again: the python job spent eight of its ten minutes in this one build (run 140). The name is
per backend, so five builds on one daemon never share a volume, and per ref, because the workflow's
concurrency group already keeps one ref to one run at a time; the buildpacks still decide for themselves
what a restored layer is good for, so a changed requirement is rebuilt. And every build runs with
`--timestamps`, its phase lines printed on success as well as failure, so the log says where a slow one
spent its time instead of showing one `ok` eight minutes after the test's name.
"""
from __future__ import annotations

import os
import platform
import random
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from support import FactoryTestCase, backends_under_test

from slipwai.catalog import axis_default
from slipwai.images import IMAGE_BUILDERS
from slipwai.probes import ready_path

# What each builder needs on the PATH beyond docker: the tool itself, or a JDK for the builds Maven drives.
NEEDS = {"pack": "pack", "ko": "ko", "": "java"}


def can_run(wanted: str) -> bool:
    """Whether this machine's daemon can run a container built for `wanted` — natively or emulated."""
    probe = subprocess.run(
        ["docker", "run", "--rm", "--platform", wanted, "alpine:3.20", "true"], capture_output=True, timeout=300
    )
    return probe.returncode == 0


def docker_run(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "run", "--rm", *arguments], text=True, capture_output=True, timeout=300)


def pack_cache(scope: str) -> str:
    """The `--cache` value naming a `pack` build's cache volume, for `scope` on this ref: stable across runs,
    so the second build on a daemon restores what the first left, and distinct per backend and per ref, so
    no two builds that can run at once on one daemon share one (see the module docstring)."""
    ref = re.sub(r"[^A-Za-z0-9_.-]", "-", os.environ.get("GITHUB_REF_NAME") or "local")
    return f"type=build;format=volume;name=slipwai-pack-{scope}-{ref}.build"


def pack_phases(output: str) -> str:
    """The timestamped phase lines of a `pack --timestamps` build, for the log: where the minutes went."""
    return "\n".join(line for line in output.splitlines() if "===>" in line)


class ImageProbe(FactoryTestCase):
    """What building and starting an image on this machine's daemon needs: the platform, and a registry for
    `pack`. No tests of its own — `ImagesTest` here and `LauncherTest` in `test_launcher.py` are the tests."""

    def setUp(self) -> None:
        if shutil.which("docker") is None:
            self.skipTest("docker is needed to start the images")
        machine = {"aarch64": "linux/arm64", "arm64": "linux/arm64", "x86_64": "linux/amd64"}.get(platform.machine())
        if machine is None:
            self.skipTest(f"no Fargate-shaped platform for {platform.machine()}")
        self.machine: str = machine
        # Named uniquely rather than per process: CI runs five of these suites beside each other on one
        # daemon, each in its own container, where a pid is no longer unique.
        self.registry_name = f"factory-images-registry-{uuid.uuid4().hex[:12]}"

    def pack_platform(self) -> str:
        """The one platform every `pack` build here is for: Fargate's where this daemon can run it, its own
        otherwise. One answer per daemon, because `if-not-present` gives every build the builder the first one
        pulled (see the module docstring)."""
        return "linux/amd64" if can_run("linux/amd64") else self.machine

    @contextmanager
    def registry(self) -> Iterator[Callable[[], str]]:
        """`IMAGE_REGISTRY` for a pack build, on first call: the one the environment names, or a throwaway
        one started then and removed on the way out — a test that never packs never starts one."""
        started: str | None = None

        def address() -> str:
            nonlocal started
            named = os.environ.get("IMAGE_REGISTRY")
            if named:
                return named
            started = started or self.start_registry()
            return started

        try:
            yield address
        finally:
            if started:
                subprocess.run(["docker", "rm", "--force", self.registry_name], capture_output=True)

    def start_registry(self) -> str:
        """A registry on the daemon's loopback, as `IMAGE_REGISTRY` — `localhost:<port>/`, the one address
        Docker and pack both trust without a certificate.

        The container joins the host network and the registry binds 127.0.0.1 itself, so `pack`'s lifecycle
        (`--network host`) and the daemon's pull reach it in the network namespace it listens in. A published
        port would put Docker Desktop's proxy between them, and that proxy is what refused `pack` in run 216
        while `docker port` reported the mapping. The port is picked at random and the registry is asked for
        `/v2/` from inside its own namespace until it answers; a port already taken shows as the registry
        exiting, and the next port is tried."""
        subprocess.run(["docker", "rm", "--force", self.registry_name], capture_output=True)
        attempts: list[str] = []
        for _ in range(5):
            port = random.randrange(20000, 60000)
            subprocess.run(
                [
                    "docker", "run", "--detach", "--name", self.registry_name, "--network", "host",
                    "--env", f"REGISTRY_HTTP_ADDR=127.0.0.1:{port}", "registry:2",
                ],
                check=True, capture_output=True,
            )
            for _ in range(30):
                probe = subprocess.run(
                    ["docker", "exec", self.registry_name, "wget", "-q", "-O", "-", "-T", "2",
                     f"http://127.0.0.1:{port}/v2/"],
                    capture_output=True, text=True,
                )
                if probe.returncode == 0:
                    return f"localhost:{port}/"
                state = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Status}}", self.registry_name],
                    capture_output=True, text=True,
                ).stdout.strip()
                if state != "running":
                    break
                time.sleep(1)
            logs = subprocess.run(["docker", "logs", self.registry_name], capture_output=True, text=True)
            attempts.append(f"port {port}: {state or 'unknown'}\n{logs.stdout}{logs.stderr}".rstrip())
            subprocess.run(["docker", "rm", "--force", self.registry_name], capture_output=True)
        self.fail("no registry came up on the daemon's loopback:\n" + "\n".join(attempts))


class ImagesTest(ImageProbe):
    def test_every_backends_image_starts_and_answers_its_probe(self) -> None:
        fargate = self.pack_platform()
        with self.registry() as registry:
            for backend in backends_under_test():
                tool = IMAGE_BUILDERS[backend]["tool"]
                with self.subTest(backend=backend):
                    if shutil.which(NEEDS[tool]) is None:
                        self.skipTest(f"{NEEDS[tool]} is needed for the {backend} image; the factory's CI installs it")
                    environment = {**os.environ, "GIT_SHA": "test"}
                    if tool == "pack":
                        environment["IMAGE_REGISTRY"] = registry()
                        environment["PACK_FLAGS"] = (
                            f"--network host --timestamps --cache '{pack_cache(backend)}' "
                            f"{os.environ.get('PACK_FLAGS', '')}"
                        ).strip()
                    platform_built = fargate if tool == "pack" else self.machine
                    with tempfile.TemporaryDirectory() as directory:
                        # Named per backend: Jib and `build-image` land in the daemon under the project's
                        # name, and two matrix jobs building `built-service:test` at once would smoke each
                        # other's image.
                        repo = self.generate(
                            directory, f"built-{backend}", "event-modelling", backend, "none", target="aws",
                            event_store="memory", http=axis_default("http", backend, "aws"),
                        )
                        result = subprocess.run(
                            ["make", "build", "smoke-image", f"PLATFORM={platform_built}"], cwd=repo, text=True,
                            capture_output=True, env=environment, timeout=900,
                        )
                        self.assertEqual(result.returncode, 0, result.stdout[-12000:] + result.stderr[-3000:])
                        if tool == "pack":
                            print(f"\n{backend} image:\n{pack_phases(result.stdout)}")
                        # The readiness path this backend records in its own stack variables, which is
                        # what the load balancer waits on — so the image is proved against the probe that
                        # decides whether it is sent traffic, not against the one that says it is alive.
                        self.assertIn(f"answers {ready_path(backend)}", result.stdout, result.stdout)
