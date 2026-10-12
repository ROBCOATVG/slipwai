"""`MatrixCase`: a package's generated-variant matrix as a `unittest` case, for its own `tests/test_matrix.py`.

A package subclasses it and names where it is, as it does `ConformanceCase`::

    from pathlib import Path
    from slipwai import matrix

    class Matrix(matrix.MatrixCase):
        language_dir = Path(__file__).resolve().parents[2]
        package = "go"

The plan is read once for the class, in a fresh interpreter (`run.plan`). `test_every_native_gate_variant_passes_its_
own_gate` generates each row and runs the project's own `make verify` in it, one subtest per row; `test_every_backends
_image_starts_and_answers_its_probe` builds each backend's production image and starts it, where Docker is here. A row
only one package has is a test of that package's subclass, built on `generate`, `verify` and `require`.

The case **skips unless `SLIPWAI_MATRIX=1`**, saying why: it takes minutes and every toolchain, and a package's tests
are collected wherever they are discovered — the root suite's run of every package's tests among them. The command
line and the root shims set `opted_in` instead. `only` restricts a run to some backends; `gate`, `image_gate` and
`image_tools` are the commands it runs and the tool each image builder needs, which a test of the case replaces.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from . import images, run
from .rows import Row

VARIABLE = "SLIPWAI_MATRIX"
UNSET = "set language_dir and package on the subclass of MatrixCase"
OFF = (f"the matrix generates every native-gate variant of this package's backends and runs each one's own "
       f"`make verify`, which takes minutes and every toolchain: set {VARIABLE}=1 to run it, or run "
       f"`python -m slipwai.matrix <language-dir> <package>`")
NATIVE_TEST = "test_every_native_gate_variant_passes_its_own_gate"
IMAGE_TEST = "test_every_backends_image_starts_and_answers_its_probe"


class Stopped(KeyboardInterrupt):
    """A SIGTERM, raised as an interrupt: `unittest` records any other exception as a row's error and goes on to the
    next row, and lets an interrupt end the run, which is what a stop is."""


class MatrixCase(unittest.TestCase):
    """Every native-gate variant of `package`'s backends in `language_dir`, each held to its own gate."""

    language_dir: ClassVar[Path | str | None] = None
    package: ClassVar[str | None] = None
    opted_in: ClassVar[bool] = False
    only: ClassVar[frozenset[str] | None] = None
    gate: ClassVar[tuple[str, ...]] = ("make", "verify")
    image_gate: ClassVar[tuple[str, ...]] = ("make", "build", "smoke-image")
    image_tools: ClassVar[Mapping[str, str]] = images.NEEDS
    plan: ClassVar[run.Plan]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if cls.language_dir is None or cls.package is None:
            raise unittest.SkipTest(UNSET)
        if not cls.opted_in and os.environ.get(VARIABLE) != "1":
            raise unittest.SkipTest(OFF)
        cls.plan = run.plan(cls.language_dir, cls.package).only(cls.only)

    def run(self, result: unittest.TestResult | None = None) -> unittest.TestResult | None:
        """The test, with its cleanups run when it is interrupted too: `unittest` skips them on an interrupt, and
        they are what removes the projects it generated."""
        try:
            return super().run(result)
        except KeyboardInterrupt:
            self.doCleanups()
            raise

    def require(self, backend: str) -> None:
        """Skip unless `backend` is one this run of the matrix covers."""
        if backend not in self.plan.backends:
            self.skipTest(f"{backend} is not in this run of {self.plan.package}'s matrix")

    def generate(self, name: str, profile: str, backend: str, frontend: str = "none", **answers: str) -> Path:
        """Generate a project the way a project maker would, into a directory removed when the test ends. Answers are
        passed by name — `persistence="postgres"`, `target="<a place>"` — and any axis left unnamed keeps its
        default."""
        return self.generated(Row(name, profile, backend, frontend,
                                  tuple((axis.replace("_", "-"), option) for axis, option in answers.items())))

    def generated(self, row: Row) -> Path:
        parent = Path(tempfile.mkdtemp(prefix="slipwai-matrix-"))
        self.addCleanup(shutil.rmtree, parent, True)
        repo, said = run.generate(self.plan.directory, parent, row)
        if repo is None:
            self.fail(f"{row.name} did not generate: {said}")
        return repo

    def verify(self, repo: Path) -> None:
        """Run `gate` in `repo`, its output on this process's own, and fail naming the project unless it passes."""
        done = subprocess.run(self.gate, cwd=repo)
        self.assertEqual(done.returncode, 0, f"{repo.name}: `{' '.join(self.gate)}` exited {done.returncode}")

    def test_every_native_gate_variant_passes_its_own_gate(self) -> None:
        for row in self.plan.rows:
            with self.subTest(row=row.name):
                repo = self.generated(row)
                self.verify(repo)
                shutil.rmtree(repo.parent, ignore_errors=True)

    def test_every_backends_image_starts_and_answers_its_probe(self) -> None:
        reason = images.unavailable()
        if reason:
            self.skipTest(reason)
        own = images.machine() or ""
        production: list[str] = []  # asked once, at the first `pack` build: it starts a container
        with images.Registry() as registry:
            for image in self.plan.images:
                with self.subTest(backend=image.row.backend):
                    # A tool this table has no row for is a package naming its own image builder, which it
                    # may: `image_builder`'s `tool` is the package's word and `NEEDS` is the keel's list of
                    # what each of the ones it knows is called on a PATH. Said and skipped, never a
                    # `KeyError` out of a matrix run — which is what the language template got, because the
                    # toy's builder is an inert placeholder called `toy`.
                    needed = self.image_tools.get(image.tool)
                    if needed is None:
                        self.skipTest(f"{image.row.backend}'s image builder is `{image.tool}`, and the "
                                      f"matrix has no binary name for it: add one to "
                                      f"`slipwai.matrix.images.NEEDS`, or set `image_tools` on this case")
                    if shutil.which(needed) is None:
                        self.skipTest(f"{needed} is needed for the {image.row.backend} image; the factory's CI "
                                      "installs it")
                    environment = {**os.environ, "GIT_SHA": "test"}
                    built_for = own
                    if image.tool == "pack":
                        production = production or [images.pack_platform(own)]
                        built_for = production[0]
                        environment["IMAGE_REGISTRY"] = registry.address()
                        environment["PACK_FLAGS"] = (f"--network host --timestamps --cache "
                                                     f"'{images.pack_cache(image.row.backend)}' "
                                                     f"{os.environ.get('PACK_FLAGS', '')}").strip()
                    repo = self.generated(image.row)
                    result = subprocess.run([*self.image_gate, f"PLATFORM={built_for}"], cwd=repo, text=True,
                                            capture_output=True, env=environment, timeout=900)
                    self.assertEqual(result.returncode, 0, result.stdout[-12000:] + result.stderr[-3000:])
                    if image.tool == "pack":
                        print(f"\n{image.row.backend} image:\n{images.pack_phases(result.stdout)}")
                    # The readiness path the backend records for the load balancer, so the image is proved
                    # against the probe that decides whether it is sent traffic.
                    self.assertIn(f"answers {image.ready}", result.stdout, result.stdout)
