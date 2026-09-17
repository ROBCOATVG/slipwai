"""The `azure` target: what a project going there is given, and that it holds together.

The apply itself ends in somebody's subscription and is unprovable here by construction. What is proved
instead is everything up to it: what a project is given, and a second service or a browser app regenerating
it. What the stacks themselves say, and that they validate against the real providers, is
`test_azure_stack.py`; that every backend's image builds and starts is `test_images.py`, which is
cloud-neutral and covers this target without knowing it exists.

Held against `test_aws_target.py` deliberately. Where this suite asserts something different from its
counterpart there, the difference is a decision recorded in `docs/azure-target.md` and not an accident.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.catalog import CATALOG, axis_default
from slipwai.targets import provisioned_as


class AzureTargetTest(FactoryTestCase):
    def generate_azure(
        self, directory: str, name: str, backend: str = "typescript", frontend: str = "react-vite", **axes
    ):
        return self.generate(
            directory, name, "event-modelling", backend, frontend, target="azure",
            event_store=axes.pop("event_store", "postgres"), http=axis_default("http", backend, "azure"),
            **axes,
        )

    def test_what_this_target_provisions_for_each_answer_and_the_one_it_has_no_answer_for(self) -> None:
        """What an answer becomes under this target is a declaration on the option, and one product this
        cloud sells is deliberately not among them — asserted here so that changing it is a visible change."""
        self.assertEqual(provisioned_as(CATALOG, "event-store", "postgres", "azure"), "flexible-server")
        self.assertEqual(provisioned_as(CATALOG, "auth", "entra", "azure"), "entra")
        self.assertIsNone(provisioned_as(CATALOG, "event-store", "memory", "azure"))
        # The customer-identity answer here is Auth0, not an Entra External ID tenant. `docs/azure-target.md`
        # says why: azurerm has no resource for such a tenant and azuread none for a user flow, so the sign-up
        # this axis promises could not be declared at all — where Auth0's whole tenant is declarable.
        self.assertEqual(
            [name for name, option in CATALOG["axes"]["users"]["options"].items() if "azure" in option["targets"]],
            ["none", "auth0"],
        )
        self.assertEqual(provisioned_as(CATALOG, "users", "auth0", "azure"), "auth0")
        self.assertEqual(provisioned_as(CATALOG, "auth", "auth0", "azure"), "auth0")

    def test_a_project_going_to_azure_carries_its_whole_path_to_production(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_azure(directory, "shipped", auth="entra")
            for relative in (
                "infra/README.md", "infra/bootstrap/main.tf", "infra/bootstrap/variables.tf",
                "infra/bootstrap/outputs.tf", "infra/bootstrap/project.auto.tfvars.json",
                "infra/service/versions.tf", "infra/service/variables.tf", "infra/service/ingress.tf",
                "infra/service/main.tf", "infra/service/postgres.tf", "infra/service/entra_staff.tf",
                "infra/service/frontend.tf", "infra/service/outputs.tf",
                "infra/service/staging.tfvars", "infra/service/production.tfvars",
                "infra/service/project.auto.tfvars.json", "infra/service/flags.tf",
                "infra/service/flags.auto.tfvars", "scripts/deploy.py", "scripts/bootstrap.py",
                "scripts/check-flags.py", ".github/workflows/deploy.yml", ".github/workflows/production.yml",
                ".github/workflows/rollback.yml", "docs/adr/0002-production-target.md", "docs/deployment.md",
            ):
                self.assertTrue((repo / relative).is_file(), relative)
            self.assertFalse((repo / "infra/service/no-frontend.tf").exists())
            # Nothing AWS's: a second cloud that shipped the first one's files would be a half-port, and
            # `assets/targets/<target>/` is read as a tree, so this is the check that it was read correctly.
            for absent in ("infra/service/rds.tf", "infra/service/network.tf", "infra/service/cognito_staff.tf"):
                self.assertFalse((repo / absent).exists(), absent)
            for script in ("scripts/deploy.py", "scripts/bootstrap.py"):
                self.assertTrue(os.access(repo / script, os.X_OK), script)
            # `azure/login` has no client-secret input: it is the GitHub OIDC path only. A forge without
            # OIDC gets a secret from bootstrap, and every workflow must use the Azure CLI's service-principal
            # path instead — including build, whose failed registry login would skip both deploy jobs.
            for name in ("deploy.yml", "production.yml", "rollback.yml"):
                workflow = (repo / ".github/workflows" / name).read_text()
                self.assertIn("if: ${{ secrets.AZURE_CLIENT_SECRET == '' }}", workflow, name)
                self.assertIn("if: ${{ secrets.AZURE_CLIENT_SECRET != '' }}", workflow, name)
                self.assertIn("az login --service-principal", workflow, name)
                self.assertIn("az account set --subscription", workflow, name)
                self.assertNotIn("client-secret:", workflow, name)
            # Expand first: on an environment that is running, the migrate jobs are applied alone and run
            # before the whole stack is, so the release still serving never meets a schema it lacks.
            deploy = (repo / "scripts/deploy.py").read_text()
            self.assertIn('apply(environment, images, "azurerm_container_app_job.migrate")', deploy)
            self.assertLess(
                deploy.index('"azurerm_container_app_job.migrate")'),
                deploy.index("found = apply(environment, images)"),
            )
            # The migrate job is polled and, still running past the limit, stopped and named.
            self.assertIn('"az", "containerapp", "job", "stop"', deploy)
            self.assertIn("entrypoint ignored the command", deploy)
            data = json.loads((repo / "infra/service/project.auto.tfvars.json").read_text())
            self.assertEqual(data["project"], "shipped")
            self.assertEqual(data["web"], {"path": "apps/web", "api": "service"})
            service = data["services"]["service"]
            self.assertEqual((service["store"], service["auth"], service["users"]),
                             ("flexible-server", "entra", None))
            self.assertEqual(service["migrate_command"], ["npm", "--workspace", "apps/service", "run", "migrate"])
            self.assertIsNone(service["migrate_image"])
            self.assertEqual(data, json.loads((repo / "infra/bootstrap/project.auto.tfvars.json").read_text()))
            # The client half of the managed Postgres's TLS policy, keyed by what the store is provisioned
            # as rather than by the cloud — see `images.POSTGRES_SSLMODE`.
            self.assertEqual(service["environment"].get("PGSSLMODE"), "no-verify")
            makefile = (repo / "Makefile").read_text()
            for target in (
                "bootstrap:", "build:", "build-service:", "push:", "smoke-image:", "smoke:", "deploy:",
                "rollback:", "url:", "migrate-remote:", "promote:", "flag:", "flags:",
            ):
                self.assertIn(f"\n{target}", makefile, target)
            self.assertIn("IMAGE = $(IMAGE_REPOSITORY):$(GIT_SHA)", makefile)
            self.assertIn("$(IMAGE_REGISTRY)shipped-service", makefile)
            self.assertIn("admin Azure credentials", makefile)
            self.assertIn("# backing-service:postgres:begin\n.PHONY: migrate-remote", makefile)
            self.assertEqual(json.loads((repo / "project.json").read_text())["target"], "azure")

    def test_the_pages_and_the_rules_a_project_here_is_given_are_this_cloud_s(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_azure(directory, "shipped", auth="entra")
            drawn = (repo / "docs/deployment.md").read_text()
            self.assertEqual(drawn.count("```mermaid"), 2)
            for said in (
                "Static Web Apps: apps/web", "app_service", "PostgreSQL Flexible Server", "Entra ID",
                "migrations as a Container Apps job: service", "rollback.yml",
                "reached through the site", "the release before, until it is deactivated",
            ):
                self.assertIn(said, drawn)
            # Nothing of the other cloud's drawing, which is the check that `target_docs` picked the module
            # rather than that `aws_docs` grew a conditional.
            for absent in ("CloudFront", "ECS cluster", "target group"):
                self.assertNotIn(absent, drawn, absent)
            adr = (repo / "docs/adr/0002-production-target.md").read_text()
            for said in (
                "Production target: Azure", "B_Standard_B1ms", "Entra ID", "Static Web Apps", "OpenTofu",
                "a month", "Image tags are not immutable", "puts an SDK in the image",
                "inherited from the AWS table rather than measured here",
            ):
                self.assertIn(said, adr)
            self.assertIn("never `tofu apply` production by hand", (repo / "AGENTS.md").read_text())
            self.assertIn("No service calls Azure for a flag", (repo / "AGENTS.md").read_text())
            readme = (repo / "README.md").read_text()
            self.assertIn("## Production", readme)
            self.assertIn("This project deploys to Azure", readme)
            self.assertIn("`az account show` names that subscription", readme)
            self.assertIn("draws what runs in Azure", readme)
            self.assertIn("A path to production", (repo / "docs/whats-included.md").read_text())

    def test_init_asks_for_this_cloud_s_tools_and_says_this_cloud_s_name(self) -> None:
        """The generated `./init` checks the same list `preflight` refuses on — `targets.TOOLS` — so a
        project cannot be refused for a tool its own script never looks for."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_azure(directory, "shipped")
            init = (repo / "init").read_text()
            self.assertIn("for tool in tofu az; do", init)
            self.assertIn("This project deploys to Azure, and bootstrapping it needs:", init)
            for said in (
                "Repository to push to", "scripts/bootstrap.py push", "make bootstrap", "--repository",
                "--skip-bootstrap", "infra/bootstrap/terraform.tfstate", "Already bootstrapped",
            ):
                self.assertIn(said, init)
            self.assertLess(init.index("bootstrapping it needs"), init.index("run_specify()"))
            self.assertLess(init.index("-f infra/bootstrap/terraform.tfstate"), init.index("bootstrapping it needs"))
            self.assertEqual(subprocess.run(["sh", "-n", "init"], cwd=repo).returncode, 0)

    def test_bootstrap_reads_the_forge_off_the_remote_and_says_what_it_would_do(self) -> None:
        """`make bootstrap` is the one thing a person runs; `--plan` is how it is held to its decisions
        without a subscription. The forge is read from the remote's host, and what the pipeline becomes
        follows from it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_azure(directory, "planned", frontend="none")
            environment = {**os.environ, "AZURE_LOCATION": "uksouth"}
            for remote, forge, pipeline in (
                ("https://github.com/owner/name.git", "github", "federated credential"),
                ("https://gitea.example.com/owner/name.git", "gitea", "client secret"),
            ):
                planned = subprocess.run(
                    ["python3", "scripts/bootstrap.py", "--plan", "--repository", "owner/name",
                     "--forge", forge],
                    cwd=repo, text=True, capture_output=True, env=environment,
                )
                self.assertEqual(planned.returncode, 0, planned.stderr)
                self.assertIn(f"owner/name on {forge}", planned.stdout)
                self.assertIn(pipeline, planned.stdout, remote)
                self.assertIn("location     uksouth", planned.stdout)
                # Every identifier the pipeline is configured with, named before anything is applied.
                for variable in ("AZURE_CLIENT_ID", "AZURE_TENANT_ID", "TOFU_STATE_ACCOUNT", "IMAGE_REGISTRY"):
                    self.assertIn(variable, planned.stdout)
            # Without a location there is nothing to apply, and Azure has no ambient region to fall back
            # on — where AWS's provider would read one out of the environment, every resource here carries
            # one. Both tools are faked onto the PATH so the refusal proved is that one and not a missing
            # `az`; `configured_location` answering nothing is the machine, which is what the sandbox is.
            tools = Path(directory) / "bin"
            tools.mkdir(exist_ok=True)
            for tool in ("tofu", "az"):
                (tools / tool).write_text("#!/bin/sh\nexit 0\n")
                (tools / tool).chmod(0o755)
            refused = subprocess.run(
                ["python3", "scripts/bootstrap.py", "--repository", "owner/name", "--forge", "none"],
                cwd=repo, text=True, capture_output=True,
                env={
                    **{k: v for k, v in os.environ.items() if k != "AZURE_LOCATION"},
                    "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
                },
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("no location", refused.stderr)

    def test_a_local_only_project_has_none_of_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "local", "event-modelling", "typescript", "react-vite")
            for absent in ("infra", "scripts/deploy.py", "scripts/bootstrap.py",
                           ".github/workflows/deploy.yml", "docs/adr/0002-production-target.md"):
                self.assertFalse((repo / absent).exists(), absent)
