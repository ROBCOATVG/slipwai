"""The migrate task's entrypoint, proved through the smallest image the pinned builder makes.

A buildpack image's entrypoint is its web process, and it starts that whatever `command` the task hands it —
which is how a deploy once hung: the migrate task, given only a `command`, started the web server instead,
never exited, and `scripts/deploy.py` waited on it until the waiter gave up. So
`aws_ecs_task_definition.migrate` points the entrypoint at the buildpack launcher instead, and this proves
both halves on one image: two scripts, one per process, built by the same builder every `pack` backend uses.
The entrypoint it runs is read off the stack itself, so the two cannot drift apart.

Its own module because it is about the builder and not about any backend: `test_images.py` runs once per
backend in CI, in that backend's `matrix` job, and this runs once, in `aws`. Built on the same `ImageProbe`.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from test_images import ImageProbe, docker_run, pack_cache, pack_phases

from slipwai.assets import ROOT
from slipwai.images import NODE_VERSION, PAKETO_BUILDER

MIGRATE_TASK = ROOT / "assets/targets/aws/service/rds.tf"


class LauncherTest(ImageProbe):
    def test_the_launcher_runs_the_migrate_command_the_images_own_entrypoint_ignores(self) -> None:
        if shutil.which("pack") is None:
            self.skipTest("pack is needed to build the image; the factory's CI installs it")
        named = re.search(r'entryPoint = \["([^"]+)"\]', MIGRATE_TASK.read_text())
        self.assertIsNotNone(named, "the migrate task no longer points its entrypoint at the launcher")
        launcher = named.group(1)  # type: ignore[union-attr]
        built_for = self.pack_platform()
        with self.registry() as registry, tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            (app / "package.json").write_text(json.dumps({
                "name": "probe", "version": "0.0.0",
                "scripts": {"start": "node web.js", "migrate": "node migrate.js"},
            }))
            (app / "web.js").write_text('console.log("the web process started");\n')
            (app / "migrate.js").write_text('console.log("the migration ran");\n')
            image = f"{registry()}launcher-probe:test"
            built = subprocess.run(
                [
                    "pack", "build", image, "--publish", "--builder", PAKETO_BUILDER, "--platform", built_for,
                    "--pull-policy", "if-not-present", "--path", ".", "--env", f"BP_NODE_VERSION={NODE_VERSION}",
                    "--network", "host", "--timestamps", "--cache", pack_cache("launcher"),
                    *shlex.split(os.environ.get("PACK_FLAGS", "")),
                ],
                cwd=app, text=True, capture_output=True, timeout=900,
            )
            self.assertEqual(built.returncode, 0, built.stdout[-8000:] + built.stderr[-3000:])
            print(f"\nlauncher probe:\n{pack_phases(built.stdout)}")
            pulled = subprocess.run(["docker", "pull", image], text=True, capture_output=True, timeout=300)
            self.assertEqual(pulled.returncode, 0, pulled.stderr)
            try:
                # What `command` alone does: the image's own entrypoint starts the web process regardless.
                as_built = docker_run("--platform", built_for, image, "npm", "run", "migrate")
                self.assertEqual(as_built.returncode, 0, as_built.stderr)
                self.assertIn("the web process started", as_built.stdout)
                self.assertNotIn("the migration ran", as_built.stdout)
                # What the task does: the same command, through the launcher the stack names.
                through_launcher = docker_run(
                    "--platform", built_for, "--entrypoint", launcher, image, "npm", "run", "migrate"
                )
                self.assertEqual(through_launcher.returncode, 0, through_launcher.stderr)
                self.assertIn("the migration ran", through_launcher.stdout)
                self.assertNotIn("the web process started", through_launcher.stdout)
            finally:
                subprocess.run(["docker", "rmi", "--force", image], capture_output=True)
