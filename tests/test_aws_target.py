"""The `aws` target: what a project going there is given, and that it holds together.

The apply itself ends in somebody's account and is unprovable here by construction. What is proved instead is
everything up to it: what a project is given, and a second service or a browser app regenerating it. What
the stack itself says, and that it validates against the real provider, is `test_aws_stack.py`; that every
backend's image builds and starts is `test_images.py`.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase, commit_all

from slipwai.assets import ROOT
from slipwai.catalog import CATALOG, axis_default
from slipwai.images import IMAGE_BUILDERS

# What each backend's `make build` reaches for, and how its migrations run once it is an image — asserted by
# the string a person would grep the Makefile and tfvars for.
BUILDERS = {
    # Compiled before it is packed: Paketo's npm-install copies a workspace package into its layers before
    # any build script runs, so a `.build/` written by one is missing from the image.
    "typescript": (
        "npm --workspace apps/service run build\n\tpack build", "--env BP_NODE_RUN_SCRIPTS= ",
        "BP_LAUNCHPOINT=apps/service/.build/src/main.js",
    ),
    "python": ("pack build", "--path apps/service"),
    "go": ("ko build ./cmd/serve", "ko build ./cmd/migrate"),
    "java-quarkus": ("quarkus.container-image.build=true", "quarkus.jib.platforms"),
    "java-spring": ("spring-boot:build-image", "imagePlatform"),
}


class AwsTargetTest(FactoryTestCase):
    def generate_aws(
        self, directory: str, name: str, backend: str = "typescript", frontend: str = "react-vite", **axes
    ):
        return self.generate(
            directory, name, "event-modelling", backend, frontend, target="aws",
            event_store=axes.pop("event_store", "postgres"), http=axis_default("http", backend, "aws"),
            **axes,
        )

    def test_a_project_going_to_aws_carries_its_whole_path_to_production(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "shipped", auth="cognito", users="cognito")
            for relative in (
                "infra/README.md", "infra/bootstrap/main.tf", "infra/bootstrap/variables.tf",
                "infra/bootstrap/outputs.tf", "infra/bootstrap/project.auto.tfvars.json",
                "infra/service/versions.tf", "infra/service/variables.tf", "infra/service/network.tf",
                "infra/service/main.tf", "infra/service/rds.tf", "infra/service/cognito_staff.tf",
                "infra/service/cognito_customers.tf", "infra/service/frontend.tf", "infra/service/outputs.tf",
                "infra/service/staging.tfvars", "infra/service/production.tfvars",
                "infra/service/project.auto.tfvars.json", "infra/service/flags.tf",
                "infra/service/flags.auto.tfvars", "scripts/deploy.py", "scripts/bootstrap.py",
                ".github/workflows/deploy.yml", ".github/workflows/rollback.yml", "docs/adr/0002-production-target.md",
                "docs/deployment.md",
            ):
                self.assertTrue((repo / relative).is_file(), relative)
            self.assertFalse((repo / "infra/service/no-frontend.tf").exists())
            for script in ("scripts/deploy.py", "scripts/bootstrap.py"):
                self.assertTrue(os.access(repo / script, os.X_OK), script)
            # Expand first: on an environment that is running, the migrate task definitions are applied alone
            # and run before the whole stack is, so the release still serving never meets a schema it lacks.
            deploy = (repo / "scripts/deploy.py").read_text()
            self.assertIn('apply(environment, images, "aws_ecs_task_definition.migrate")', deploy)
            self.assertLess(
                deploy.index('"aws_ecs_task_definition.migrate")'), deploy.index("found = apply(environment, images)")
            )
            # The migrate task is polled and, still running past the limit, stopped and named — not left to
            # `aws ecs wait`, whose "Max attempts exceeded" says nothing and leaves the task running.
            self.assertNotIn('"wait", "tasks-stopped"', deploy)
            self.assertIn('"aws", "ecs", "stop-task"', deploy)
            self.assertIn("entrypoint ignored the command", deploy)
            self.assertIn("family          = task.family", (repo / "infra/service/rds.tf").read_text())
            data = json.loads((repo / "infra/service/project.auto.tfvars.json").read_text())
            self.assertEqual(data["project"], "shipped")
            self.assertEqual(data["web"], {"path": "apps/web", "api": "service"})
            service = data["services"]["service"]
            self.assertEqual((service["store"], service["auth"], service["users"]), ("rds", "cognito", "cognito"))
            self.assertEqual(service["migrate_command"], ["npm", "--workspace", "apps/service", "run", "migrate"])
            self.assertIsNone(service["migrate_image"])
            bootstrap = json.loads((repo / "infra/bootstrap/project.auto.tfvars.json").read_text())
            self.assertEqual(data, bootstrap)
            # `configure-aws-credentials` tags the session, and an IAM user needs that granted on both sides —
            # its own policy and the role's trust — or the key path fails at the first step of every deploy.
            self.assertEqual(
                (repo / "infra/bootstrap/main.tf").read_text().count('["sts:AssumeRole", "sts:TagSession"]'), 2
            )
            makefile = (repo / "Makefile").read_text()
            for target in (
                "bootstrap:", "build:", "build-service:", "push:", "smoke-image:", "smoke:", "deploy:", "rollback:",
                "url:", "migrate-remote:",
            ):
                self.assertIn(f"\n{target}", makefile, target)
            self.assertRegex(makefile, r"\nci: [^\n]*\bbuild smoke-image\b")
            self.assertIn("IMAGE = $(IMAGE_REPOSITORY):$(GIT_SHA)", makefile)
            self.assertIn("$(IMAGE_REGISTRY)shipped-service", makefile)
            # The migrate task is the store's: its target sits in the store's region, and goes with it.
            self.assertIn("# backing-service:postgres:begin\n.PHONY: migrate-remote", makefile)
            self.assertIn("Cache-Control", (repo / "infra/service/frontend.tf").read_text())
            self.assertIn("aws_cloudfront_distribution", (repo / "infra/service/frontend.tf").read_text())
            self.assertIn("make bootstrap", (repo / "README.md").read_text())
            self.assertIn("## Production", (repo / "README.md").read_text())
            # The architecture, drawn from this project's answers: its service, its site, its database and pools.
            drawn = (repo / "docs/deployment.md").read_text()
            self.assertEqual(drawn.count("```mermaid"), 2)
            for said in ("CloudFront: apps/web", "svc_service", "RDS Postgres", "Cognito: staff", "the product's users",
                         "blue/green", "migrations as a one-off task: service", "rollback.yml"):
                self.assertIn(said, drawn)
            self.assertIn("docs/deployment.md", (repo / "README.md").read_text())
            # `./init` is the first-day step, so it asks where to push and bootstraps; a script can answer
            # ahead or decline, and Spec Kit never sees either flag.
            init = (repo / "init").read_text()
            for said in (
                "Repository to push to", "scripts/bootstrap.py push", "make bootstrap", "--repository",
                "--skip-bootstrap", "infra/bootstrap/terraform.tfstate", "Already bootstrapped",
            ):
                self.assertIn(said, init)
            self.assertLess(init.index("bootstrapping it needs"), init.index("run_specify()"))  # said first
            # And the committed state is read before the tools are asked for, so a rerun on a machine
            # without `tofu` is not told about a step it will not take.
            self.assertLess(init.index("-f infra/bootstrap/terraform.tfstate"), init.index("bootstrapping it needs"))
            self.assertEqual(subprocess.run(["sh", "-n", "init"], cwd=repo).returncode, 0)
            self.assertIn("never `tofu apply` production by hand", (repo / "AGENTS.md").read_text())
            self.assertIn("A path to production", (repo / "docs/whats-included.md").read_text())
            self.assertIn("Bash(make build)", (repo / ".claude/settings.json").read_text())
            self.assertNotIn("make deploy", (repo / ".claude/settings.json").read_text())
            self.assertIn(".build/\n", (repo / ".gitignore").read_text())
            adr = (repo / "docs/adr/0002-production-target.md").read_text()
            for said in ("blue/green", "db.t4g.micro", "Cognito", "CloudFront", "OpenTofu", "a month", "#45678"):
                self.assertIn(said, adr)
            self.assertIn("bootstrap stack", (repo / "commands/add-service.md").read_text())
            # Compose stays, and says what it is for.
            self.assertIn("Local development only", (repo / "docker-compose.yml").read_text())
            self.assertEqual(json.loads((repo / "project.json").read_text())["target"], "aws")

    def test_bootstrap_reads_the_forge_off_the_remote_and_says_what_it_would_do(self) -> None:
        """`make bootstrap` is the one thing a person runs; `--plan` is how it is held to its decisions without
        an account: GitHub means an OIDC trust and no stored credential, anything else means a key that may
        only assume the deploy role, and no remote is a refusal that says to push first."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "planned", "go", "none", event_store="memory")
            script = ["python3", "scripts/bootstrap.py", "--plan"]
            env = {**os.environ, "AWS_REGION": "eu-west-2"}
            refused = subprocess.run(script, cwd=repo, text=True, capture_output=True, env=env)
            self.assertEqual(refused.returncode, 1)
            self.assertIn("no `origin` remote yet", refused.stderr)
            subprocess.run(["git", "remote", "add", "origin", "git@github.com:acme/planned.git"], cwd=repo, check=True)
            github = subprocess.run(script, cwd=repo, text=True, capture_output=True, env=env, check=True).stdout
            self.assertIn("acme/planned on github (via the gh CLI)", github)
            self.assertIn("no credential is stored", github)
            self.assertIn("GitHub OIDC trust", github)
            # Any host but GitHub's is a forge without OIDC federation; the host itself is whatever git's
            # `insteadOf` rewrites leave it, so only the shape of the API address is asserted.
            subprocess.run(
                ["git", "remote", "set-url", "origin", "http://localhost:3300/luke-gee/planned.git"],
                cwd=repo, check=True,
            )
            gitea = subprocess.run(script, cwd=repo, text=True, capture_output=True, env=env, check=True).stdout
            self.assertRegex(gitea, r"luke-gee/planned on gitea \(http://[^/]+:3300/api/v1\)")
            self.assertIn("IAM user key, stored as repository secrets", gitea)
            self.assertIn("secrets AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY", gitea)
            self.assertIn("generated now and printed once", gitea)
            # The region: from the environment, else from the file a previous run wrote — asked for only in a
            # terminal, which a test is not, so `--plan` says it is unset rather than hanging on a question.
            without = subprocess.run(
                script, cwd=repo, text=True, capture_output=True, check=True,
                env={k: v for k, v in os.environ.items() if k != "AWS_REGION"},
            ).stdout
            self.assertIn("region       (unset", without)
            (repo / "infra/region").write_text("eu-west-1\n")
            remembered = subprocess.run(
                script, cwd=repo, text=True, capture_output=True, check=True,
                env={k: v for k, v in os.environ.items() if k != "AWS_REGION"},
            ).stdout
            self.assertIn("region       eu-west-1", remembered)

    def test_url_prints_the_address_and_nothing_else_so_smoke_can_be_given_it(self) -> None:
        """`make smoke URL=$(make -s url ENV=staging)` reads this script's stdout, so nothing but the address
        may be on it. `tofu init` opens with a blank line: let that through and the shell splits `URL=` off
        as its own empty word, smoke is asked about no address, and the failure reads as a usage message
        about `smoke` rather than as the address that never arrived."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "shipped")
            tools = Path(directory) / "bin"
            tools.mkdir()
            (tools / "tofu").write_text(
                "#!/bin/sh\n"
                'for argument in "$@"; do\n'
                '  if [ "$argument" = "output" ]; then\n'
                '    echo \'{"url": {"value": "https://d1.cloudfront.net"}}\'\n'
                "    exit 0\n"
                "  fi\n"
                "done\n"
                "printf '\\nInitializing the backend...\\n'\n"  # what every other tofu says, on stdout
            )
            (tools / "aws").write_text("#!/bin/sh\nexit 0\n")
            for tool in ("tofu", "aws"):
                (tools / tool).chmod(0o755)
            printed = subprocess.run(
                ["python3", "scripts/deploy.py", "url", "staging"],
                cwd=repo, text=True, capture_output=True,
                env={
                    **os.environ, "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
                    "TOFU_STATE_BUCKET": "shipped-tofu-state", "AWS_REGION": "us-west-2",
                },
            )
            self.assertEqual(printed.returncode, 0, printed.stderr)
            self.assertEqual(printed.stdout, "https://d1.cloudfront.net\n")
            self.assertIn("Initializing the backend", printed.stderr)  # not lost, just not on stdout

    def test_a_local_only_project_has_none_of_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "local", frontend="react-vite")
            self.assertFalse((repo / "infra").exists())
            self.assertFalse((repo / "scripts/deploy.py").exists())
            self.assertFalse((repo / ".github/workflows/deploy.yml").exists())
            self.assertFalse((repo / "docs/deployment.md").exists())
            self.assertFalse((repo / ".github/workflows/rollback.yml").exists())
            self.assertFalse((repo / ".github/workflows/production.yml").exists())
            self.assertFalse((repo / "docs/adr/0002-production-target.md").exists())
            makefile = (repo / "Makefile").read_text()
            for target in ("build:", "push:", "deploy:", "rollback:", "promote:", "smoke:", "flag:", "flags:"):
                self.assertNotIn(f"\n{target}", makefile, target)
            self.assertNotIn("## Production", (repo / "README.md").read_text())
            self.assertNotIn("bootstrap stack", (repo / "commands/add-service.md").read_text())
            self.assertNotIn(".build/\ninfra", (repo / ".gitignore").read_text())
            self.assertNotIn("bootstrap", (repo / "init").read_text())

    def test_each_backend_builds_its_image_its_own_way_and_migrates_in_its_own_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for backend in CATALOG["backends"]:
                with self.subTest(backend=backend):
                    repo = self.generate_aws(directory, f"image-{backend}", backend, "none")
                    makefile = (repo / "Makefile").read_text()
                    for said in BUILDERS[backend]:
                        self.assertIn(said, makefile, backend)
                    # Only the workspace that is packed whole keeps its machine's node_modules out of the upload.
                    self.assertEqual((repo / "project.toml").is_file(), backend == "typescript", backend)
                    tfvars = json.loads((repo / "infra/service/project.auto.tfvars.json").read_text())
                    service = tfvars["services"]["service"]
                    workflow = (repo / ".github/workflows/deploy.yml").read_text()
                    tool = IMAGE_BUILDERS[backend]["tool"]
                    for installed in ("pack", "ko"):
                        self.assertEqual(f"setup-{installed}" in workflow, installed == tool, f"{backend}: {installed}")
                    if backend == "go":
                        # ko builds one binary per image, so the migrations get an image of their own.
                        self.assertEqual(service["migrate_image"], "service-migrate")
                        self.assertIsNone(service["migrate_command"])
                        self.assertIn("IMAGE_MIGRATE = $(IMAGE_REPOSITORY_MIGRATE):$(GIT_SHA)", makefile)
                        self.assertIn("service-migrate=$(IMAGE_MIGRATE)", makefile)
                    elif backend.startswith("java"):
                        # The framework migrates as the service starts, switched on in production only.
                        self.assertIsNone(service["migrate_command"])
                        self.assertTrue(service["environment"], backend)
                        self.assertNotIn("migrate-remote", makefile)
                    else:
                        self.assertIsNotNone(service["migrate_command"])
                        self.assertIn("migrate-remote:", makefile)
                        # The migrate task runs a command through the buildpack launcher, `/cnb/lifecycle/launcher`
                        # (rds.tf), so a command is only the right shape inside an image a buildpack built. A
                        # backend built another way migrates by image or as it starts — or teaches rds.tf its
                        # entrypoint first.
                        self.assertEqual(tool, "pack", f"{backend} migrates by command but is not built by pack")
                    procfile = repo / "apps/service/Procfile"
                    self.assertEqual(procfile.is_file(), backend == "python")
                    if backend == "python":
                        self.assertIn("python -m image_python.main", procfile.read_text())
                    # No store to migrate: no task, no switch, no second image.
                    bare = self.generate_aws(
                        directory, f"bare-{backend}", backend, "none", event_store="memory"
                    )
                    plain = json.loads(
                        (bare / "infra/service/project.auto.tfvars.json").read_text()
                    )["services"]["service"]
                    self.assertEqual(
                        (plain["store"], plain["migrate_command"], plain["migrate_image"], plain["environment"]),
                        (None, None, None, {}),
                    )
                    self.assertNotIn("migrate-remote", (bare / "Makefile").read_text())

    def test_add_service_and_add_frontend_regenerate_the_path_to_production(self) -> None:
        """A second service is one more image, one more ECS service and one more repository; a browser
        app puts the site in front. Both come from the same regeneration everything else does."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "grown", "go", "none")
            frontend = (repo / "infra/service/frontend.tf").read_text()
            self.assertIn("public_url = local.service_urls", frontend)
            report = subprocess.run(
                [
                    str(ROOT / "slipwai"), "add-service", "payments", "--language", "python",
                    "--purpose", "Takes payment.",
                ],
                cwd=repo, check=True, text=True, capture_output=True,
            ).stdout
            self.assertIn("`make bootstrap` needs running once more", report)
            data = json.loads((repo / "infra/service/project.auto.tfvars.json").read_text())
            self.assertEqual(list(data["services"]), ["service", "payments"])
            self.assertEqual(data["services"]["payments"]["port"], 3001)
            self.assertEqual(data["services"]["payments"]["migrate_command"], ["python", "migrations/apply.py"])
            self.assertEqual(data, json.loads((repo / "infra/bootstrap/project.auto.tfvars.json").read_text()))
            makefile = (repo / "Makefile").read_text()
            self.assertIn("\nbuild-payments:", makefile)
            self.assertIn("IMAGE_PAYMENTS = $(IMAGE_REPOSITORY_PAYMENTS):$(GIT_SHA)", makefile)
            self.assertIn("payments=$(IMAGE_PAYMENTS)", makefile)
            self.assertTrue((repo / "apps/payments/Procfile").is_file())
            workflow = (repo / ".github/workflows/deploy.yml").read_text()
            for said in ("setup-ko", "setup-pack", "setup-python", "setup-go"):
                self.assertIn(said, workflow)
            commit_all(repo, "payments")
            subprocess.run(
                [str(ROOT / "slipwai"), "add-frontend", "web"], cwd=repo, check=True, capture_output=True
            )
            frontend = (repo / "infra/service/frontend.tf").read_text()
            self.assertIn("aws_cloudfront_distribution", frontend)
            self.assertNotIn("public_url = local.service_urls", frontend)
            # One definition of the address, in one file: the regeneration rewrote rather than added.
            stack = repo / "infra/service"
            definitions = sum(p.read_text().count("public_url =") for p in stack.glob("*.tf"))
            self.assertEqual(definitions, 1)
            self.assertEqual(
                json.loads((stack / "project.auto.tfvars.json").read_text())["web"],
                {"path": "apps/web", "api": "service"},
            )
            self.assertIn("setup-node", (repo / ".github/workflows/deploy.yml").read_text())
            self.assertIn("CloudFront", (repo / "commands/add-frontend.md").read_text())
            # The drawing followed both: the second service is in it, and so is the site in front.
            drawn = (repo / "docs/deployment.md").read_text()
            for said in ("svc_payments", "svc_service", "CloudFront: apps/web", "| `payments` | python |"):
                self.assertIn(said, drawn)
            # And what the target refuses at generation, it refuses when a service is added.
            for flags, said in (
                (["--event-store", "sqlite"], "offered under the none/existing target only"),
                (["--http", "none"], "cannot be taken to the aws target"),
            ):
                result = subprocess.run(
                    [str(ROOT / "slipwai"), "add-service", "audit", *flags],
                    cwd=repo, text=True, capture_output=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(said, result.stderr)
