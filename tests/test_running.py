"""A green gate is not a demonstration: every project can be run, or says why it cannot be."""
from __future__ import annotations

import json
import subprocess
import tempfile

from support import FactoryTestCase

from slipwai.backends import (
    BACKEND_TOOLING,
)


class RunningTest(FactoryTestCase):
    def test_every_backend_can_be_run_and_demonstrated_rather_than_only_verified(self) -> None:
        """A starter whose only verb is `make verify` teaches that working means passing, and leaves the
        demo every slice ends with to be invented by whoever gets there first. So each transport ships the
        one file that binds a port, `make dev` runs it, `make demo` runs the whole thing in containers, and
        Compose runs that *same* `make dev` — two paths that cannot drift because there is only one
        command."""
        entry_points = {
            "typescript": ("fastify", "apps/service/src/main.ts", "npm --workspace apps/service run dev"),
            "python": (
                "fastapi", "apps/service/src/runnable/main.py",
                "uv run --project apps/service --no-sync python -m runnable.main",
            ),
            "go": ("net-http", "apps/service/cmd/serve/main.go", "go run ./cmd/serve"),
        }
        for language, (transport, entry, command) in entry_points.items():
            with tempfile.TemporaryDirectory() as directory:
                repo = self.generate(
                    directory, "runnable", "event-modelling", language, "react-vite", http=transport
                )
                self.assertTrue((repo / entry).is_file(), f"{language} has nothing that listens")

                makefile = (repo / "Makefile").read_text()
                self.assertIn(command, makefile)
                for target in ("dev:", "dev-web:", "demo:", "demo-down:"):
                    self.assertIn(f"\n{target}", makefile, f"{language} is missing {target}")
                # Pruning the transport has to take the way to run it too, so the target lives inside the
                # transport's region rather than beside it.
                dev = makefile.split(f"# backing-service:{transport}:begin")
                self.assertTrue(
                    any("dev:" in block.split(f"# backing-service:{transport}:end")[0] for block in dev[1:]),
                    f"{language}: the dev target is outside the transport's marked region",
                )

                compose = self.settings((repo / "docker-compose.yml").read_text())
                # The same `make dev` a laptop runs, behind whatever this image is missing first — a
                # Python container has no uv, and installs the pinned one before Make starts.
                setup = BACKEND_TOOLING[language]["container_setup"]
                self.assertIn(
                    f"command: ['sh', '-c', '{setup} && make dev']" if setup else "command: ['make', 'dev']",
                    compose,
                )
                self.assertIn("command: ['make', 'dev-web']", compose)
                # Behind a profile, or `make services-up` would start the app as well as the database it
                # was asked for.
                self.assertEqual(compose.count("profiles: ['app']"), 2)
                self.assertIn("- '${PORT:-3000}:3000'", compose)
                self.assertIn("- '${WEB_PORT:-5173}:5173'", compose)
                # The image is the one CI runs the gate in: a demo and a pipeline disagreeing about a
                # toolchain version is a bug that only ever reproduces for one of them.
                self.assertIn(f"image: {BACKEND_TOOLING[language]['ci_image']}", compose)

                # An empty node_modules is the normal state of a container that mounts a volume over it, so
                # the install guard cannot be the directory's existence.
                self.assertNotIn("[ -d node_modules ]", makefile)

                vite = (repo / "apps/web/vite.config.ts").read_text()
                self.assertIn(f"backing-service:{transport}:begin", vite)
                self.assertIn("process.env.API_ORIGIN", vite)
                self.assertIn("'/api': { target: apiOrigin, changeOrigin: true }", vite)

                skill = (repo / "skills/run-the-app/SKILL.md").read_text()
                self.assertIn("http://localhost:3000", skill)
                self.assertIn("http://localhost:5173", skill)
                self.assertIn("make demo", skill)

    def test_the_generated_compose_file_is_one_docker_compose_agrees_to_read(self) -> None:
        """The app's services are written into a marked YAML file by substitution, which is the one kind of
        change that can produce a file no gate reads and Compose refuses. `config` parses it and resolves
        every interpolation without pulling an image or starting anything."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory,
                "composable",
                "event-modelling",
                "typescript",
                "react-vite",
                event_store="postgres",
                http="fastify",
                auth="keycloak",
            )
            result = subprocess.run(
                ["docker", "compose", "config", "--quiet"],
                cwd=repo,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_dropping_the_transport_takes_the_way_to_run_it_along_with_it(self) -> None:
        """The pruner's rule is that nothing it leaves behind may reference what it removed. An entry point
        with no adapter, a `make dev` that starts a deleted file, or a dev-server proxy pointing at a
        service that is gone would each pass every gate here and fail the first time somebody ran it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory,
                "was-served",
                "event-modelling",
                "typescript",
                "react-vite",
                event_store="postgres",
                http="fastify",
            )
            self.assertTrue((repo / "apps/service/src/main.ts").is_file())
            subprocess.run(
                ["python3", "scripts/backing-services.py", "--http", "none"],
                cwd=repo,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            self.assertFalse((repo / "apps/service/src/main.ts").exists())
            self.assertNotIn("dev:", (repo / "Makefile").read_text())
            self.assertNotIn("dev", json.loads((repo / "apps/service/package.json").read_text())["scripts"])

            vite = (repo / "apps/web/vite.config.ts").read_text()
            self.assertNotIn("apiOrigin", vite)
            self.assertNotIn("backing-service", vite)
            # The browser app is still runnable, and still worth composing: only what it talked to is gone.
            compose = self.settings((repo / "docker-compose.yml").read_text())
            self.assertNotIn("command: ['make', 'dev']", compose)
            self.assertIn("command: ['make', 'dev-web']", compose)
            self.assertIn("postgres:", compose)
            pruned = (repo / "Makefile").read_text()
            self.assertIn("dev-web:", pruned)
            # And the variable that target reads survives with it: `WEB_HOST` describes the dev server, not
            # the transport, so pruning the one must not take the other's default away.
            self.assertIn("WEB_HOST ?= localhost", pruned)

    def test_the_dev_server_can_be_told_to_listen_where_the_browser_is_not(self) -> None:
        """Vite binds loopback, which is the right default on a laptop and the wrong one everywhere the
        browser is not on the machine running it — a container, a VM, a remote sandbox. The failure is
        expensive because the symptom points away from the cause: the startup banner is clean, the port is
        forwarded, and nothing connects, so the search goes to the proxy and the firewall rather than to the
        address that was bound. Compose already sets WEB_HOST for the demo's `web` container, so `make dev`
        and `make demo` were both reachable from elsewhere and `make dev-web` alone was not.

        Outside the transport's marked region, because the dev server belongs to the frontend: `./init
        --http none` keeps `dev-web`, and a default pruned out from under it would leave the target
        depending on a variable no longer defined."""
        for transport, expected in (("fastify", "proxying /api to the service"), ("none", "5173")):
            with tempfile.TemporaryDirectory() as directory:
                repo = self.generate(
                    directory, "reachable", "event-modelling", "typescript", "react-vite", http=transport
                )
                makefile = (repo / "Makefile").read_text()
                self.assertIn("\nWEB_HOST ?= localhost", makefile)
                # Vite reads the environment, not Make's variables, so without this the override is inert
                # in the one spelling most people reach for first.
                self.assertIn("\nexport WEB_HOST", makefile)
                self.assertIn(expected, makefile)

                skill = (repo / "skills/run-the-app/SKILL.md").read_text()
                self.assertIn("WEB_HOST=0.0.0.0", skill)

                # An agent is the reader most likely to need this, and it is stopped by a permission
                # prompt rather than by the binding — so the override is pre-approved beside the target it
                # modifies, or the fix reaches everyone except the case it was written for.
                allowed = json.loads((repo / ".claude/settings.json").read_text())
                self.assertIn("Bash(make dev-web WEB_HOST=*)", allowed["permissions"]["allow"])

    def test_a_project_with_no_browser_app_is_not_given_a_dev_server_to_configure(self) -> None:
        """A `WEB_HOST` in a project with no `apps/web` is a setting for a server that does not exist, and
        the reader who finds it has to prove that themselves before they can ignore it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "no-browser", "event-modelling", "go", "none", http="net-http"
            )
            self.assertNotIn("WEB_HOST", (repo / "Makefile").read_text())
            self.assertNotIn("WEB_HOST", (repo / "skills/run-the-app/SKILL.md").read_text())

    def test_a_project_with_nothing_to_run_says_so_instead_of_offering_a_target(self) -> None:
        """`make demo` on a project with no transport and no browser app would start an empty network, and
        a run skill listing commands that do nothing is worse than no skill: the demo it promises has to be
        invented anyway, after the reader has trusted it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory,
                "nothing-to-run",
                "standard",
                "go",
                "none",
                http="none",
            )
            makefile = (repo / "Makefile").read_text()
            for target in ("dev:", "dev-web:", "demo:"):
                self.assertNotIn(f"\n{target}", makefile)
            self.assertFalse((repo / "docker-compose.yml").exists())
            skill = (repo / "skills/run-the-app/SKILL.md").read_text()
            self.assertIn("nothing to", skill)
            self.assertIn("acceptance tests", skill)
