"""What building and starting a production image on this machine's daemon needs: the platform, and a registry for
`pack`. Moved from the root suite's `tests/test_images.py`, so a package's matrix carries its image probe.

A backend whose builder is `pack` publishes to a registry: Docker Desktop's containerd image store cannot take a
`pack` export directly (buildpacks/pack#2272), so a throwaway `registry:2` is started on the daemon's own loopback — on
the host network, listening on 127.0.0.1 itself rather than behind a published port, the proxy of which
intermittently refused the connection (run 216) — and `pack`'s containers share that network to reach it. Those
backends are built for `linux/amd64`, which is what a managed target runs, wherever this machine can run such
a container, and for its
own otherwise: one platform for every `pack` build on a daemon, because `--pull-policy if-not-present` hands pack
whichever variant of the builder the daemon already holds (run 228). `IMAGE_REGISTRY` in the environment names a
registry to use instead; `PACK_FLAGS` is passed on, for a machine that needs more.

Every `pack` build names its build cache (`pack_cache`), per backend and per ref: left to pack, the volume is named
after an image on a random port, so no build ever found the cache the one before it left (run 140). Every build runs
with `--timestamps`, its phase lines printed on success too, so the log says where a slow one spent its time.
"""
from __future__ import annotations

import os
import platform
import random
import re
import shutil
import subprocess
import time
import uuid

# What each builder needs on the PATH beyond docker: the tool itself, or a JDK (javac) for the builds Maven drives.
NEEDS = {"pack": "pack", "ko": "ko", "": "javac"}
PLATFORMS = {"aarch64": "linux/arm64", "arm64": "linux/arm64", "x86_64": "linux/amd64"}


def unavailable() -> str | None:
    """Why no image can be built and started here, or `None` where one can."""
    if shutil.which("docker") is None:
        return "docker is needed to start the images"
    if machine() is None:
        return f"no production-shaped platform for {platform.machine()}"
    return None


def machine() -> str | None:
    """This machine's own container platform, where it is one a managed target runs."""
    return PLATFORMS.get(platform.machine())


def can_run(wanted: str) -> bool:
    """Whether this machine's daemon can run a container built for `wanted` — natively or emulated."""
    probe = subprocess.run(
        ["docker", "run", "--rm", "--platform", wanted, "alpine:3.20", "true"], capture_output=True, timeout=300
    )
    return probe.returncode == 0


def pack_platform(own: str) -> str:
    """The one platform every `pack` build is for: production's where this daemon can run it, `own`
    otherwise."""
    return "linux/amd64" if can_run("linux/amd64") else own


def docker_run(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "run", "--rm", *arguments], text=True, capture_output=True, timeout=300)


def pack_cache(scope: str) -> str:
    """The `--cache` value naming a `pack` build's cache volume, for `scope` on this ref: stable across runs, and
    distinct per backend and per ref, so no two builds that can run at once on one daemon share one."""
    ref = re.sub(r"[^A-Za-z0-9_.-]", "-", os.environ.get("GITHUB_REF_NAME") or "local")
    return f"type=build;format=volume;name=slipwai-pack-{scope}-{ref}.build"


def pack_phases(output: str) -> str:
    """The timestamped phase lines of a `pack --timestamps` build, for the log: where the minutes went."""
    return "\n".join(line for line in output.splitlines() if "===>" in line)


class Registry:
    """`IMAGE_REGISTRY` for a pack build, on first `address()`: the one the environment names, or a throwaway one
    started then and removed on `close` — a run that never packs never starts one. Named uniquely rather than per
    process: CI runs several of these beside each other on one daemon, each in its own container."""

    def __init__(self) -> None:
        self.name = f"factory-images-registry-{uuid.uuid4().hex[:12]}"
        self.started: str | None = None

    def __enter__(self) -> Registry:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def address(self) -> str:
        named = os.environ.get("IMAGE_REGISTRY")
        if named:
            return named
        self.started = self.started or self.start()
        return self.started

    def close(self) -> None:
        if self.started:
            subprocess.run(["docker", "rm", "--force", self.name], capture_output=True)

    def start(self) -> str:
        """A registry on the daemon's loopback, as `localhost:<port>/`, the one address Docker and pack both trust
        without a certificate. The port is picked at random and the registry asked for `/v2/` from inside its own
        namespace until it answers; a port already taken shows as the registry exiting, and the next is tried. A start
        that fails or is interrupted removes its container: `close` removes only one that started."""
        try:
            return self.attempt()
        except BaseException:
            subprocess.run(["docker", "rm", "--force", self.name], capture_output=True)
            raise

    def attempt(self) -> str:
        subprocess.run(["docker", "rm", "--force", self.name], capture_output=True)
        attempts: list[str] = []
        for _ in range(5):
            port = random.randrange(20000, 60000)
            subprocess.run(["docker", "run", "--detach", "--name", self.name, "--network", "host",
                            "--env", f"REGISTRY_HTTP_ADDR=127.0.0.1:{port}", "registry:2"],
                           check=True, capture_output=True)
            state = ""
            for _ in range(30):
                probe = subprocess.run(["docker", "exec", self.name, "wget", "-q", "-O", "-", "-T", "2",
                                        f"http://127.0.0.1:{port}/v2/"], capture_output=True, text=True)
                if probe.returncode == 0:
                    return f"localhost:{port}/"
                state = subprocess.run(["docker", "inspect", "--format", "{{.State.Status}}", self.name],
                                       capture_output=True, text=True).stdout.strip()
                if state != "running":
                    break
                time.sleep(1)
            logs = subprocess.run(["docker", "logs", self.name], capture_output=True, text=True)
            attempts.append(f"port {port}: {state or 'unknown'}\n{logs.stdout}{logs.stderr}".rstrip())
            subprocess.run(["docker", "rm", "--force", self.name], capture_output=True)
        raise RuntimeError("no registry came up on the daemon's loopback:\n" + "\n".join(attempts))
