"""The stacks an `azure` project is given, read as HCL and held to the real providers.

The apply itself ends in somebody's subscription and is unprovable here. What is proved instead: what the
stacks say about how a release reaches production and how it is undone, the apply-time decisions
`tofu validate` cannot see, and that every variant this factory writes — maximal, minimal, and maximal
pruned to minimal — validates against the pinned azurerm, azapi and azuread providers.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.catalog import axis_default


def tofu(*arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["tofu", *arguments], cwd=cwd, text=True, capture_output=True)


class AzureStackTest(FactoryTestCase):
    def generate_azure(
        self, directory: str, name: str, backend: str = "typescript", frontend: str = "react-vite", **axes
    ):
        return self.generate(
            directory, name, "event-modelling", backend, frontend, target="azure",
            event_store=axes.pop("event_store", "postgres"), http=axis_default("http", backend, "azure"),
            **axes,
        )

    def validate(self, stack: Path) -> None:
        init = tofu("init", "-backend=false", "-input=false", cwd=stack)
        self.assertEqual(init.returncode, 0, init.stderr)
        formatted = tofu("fmt", "-check", "-recursive", ".", cwd=stack)
        self.assertEqual(formatted.returncode, 0, f"not formatted: {formatted.stdout}")
        valid = tofu("validate", cwd=stack)
        self.assertEqual(valid.returncode, 0, valid.stderr)

    def test_the_stack_deploys_by_revision_and_decides_its_counts_from_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_azure(directory, "shipped", auth="entra")
            stack = (repo / "infra/service/main.tf").read_text()
            # Multiple revisions, and all of the traffic to whatever this apply produced. `latest_revision`
            # rather than a suffix named after the commit: a suffix must be unique for the lifetime of the
            # app and `make rollback` re-runs a commit that has already had one, so naming revisions after
            # commits makes the second rollback a name collision — an apply-time failure nothing here could
            # see, and one nobody would hit until the day it mattered.
            self.assertIn('revision_mode                = "Multiple"', stack)
            self.assertIn("latest_revision = true", stack)
            self.assertNotIn("revision_suffix", stack)
            self.assertIn("max_inactive_revisions       = var.kept_revisions", stack)
            # What gates the switch: a revision takes no traffic until this passes.
            self.assertIn("readiness_probe {", stack)
            # The pull is an identity's, not a password's: no registry credential exists to be stored.
            self.assertIn("identity = azurerm_user_assigned_identity.app.id", stack)
            self.assertNotIn("password_secret_name", stack)
            # A role assignment is not effective the instant it is created, and the very next thing a first
            # apply does is write a secret into the vault it has just granted itself access to. Without the
            # wait the first apply fails with a 403 a second, identical apply would not — which is the worst
            # kind of failure to hand somebody on their first deploy, and one `tofu validate` cannot see.
            self.assertIn('resource "time_sleep" "rbac"', stack)
            self.assertIn("depends_on = [azurerm_role_assignment.pull, time_sleep.rbac]", stack)
            # The environment's own ingress, and no per-service load balancer to create: the file that
            # would have held one is a `locals` block.
            ingress = (repo / "infra/service/ingress.tf").read_text()
            self.assertNotIn("resource ", ingress)
            self.assertIn("app.ingress[0].fqdn", ingress)
            # A buildpack image's entrypoint starts the web process whatever `command` it is given, so the
            # migrate job points the command at the buildpack launcher wherever it gives one — a run-time
            # failure, not an apply-time one: the job serves instead of migrating and never exits.
            migrate = (repo / "infra/service/postgres.tf").read_text()
            self.assertIn('command = each.value.migrate_command != null ? ["/cnb/lifecycle/launcher"] : []', migrate)
            # The same environment the long-running app gets, not a subset: a migration and the service it
            # migrates for reach the same database, so `PGSSLMODE` has to reach both.
            self.assertIn("for_each = local.service_environment[each.key]", migrate)
            # The server half of the TLS policy, stated rather than inherited, in both directions.
            self.assertIn('name      = "require_secure_transport"', migrate)
            self.assertIn('value     = "ON"', migrate)

    def test_the_site_is_the_product_s_own_and_the_service_behind_it_is_not_published(self) -> None:
        """Static Web Apps serves its own content and proxies `/api` by its own rule, so there is no second
        origin for this stack to keep private and no routing rule for it to write. The cost is that the
        linked service answers only through the site — which `urls` has to reflect, or `make smoke` would be
        handed an address that answers 403."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_azure(directory, "shipped")
            frontend = (repo / "infra/service/frontend.tf").read_text()
            self.assertIn('sku_tier = "Standard"', frontend)  # Free cannot link a backend
            self.assertIn("Microsoft.Web/staticSites/linkedBackends@2024-04-01", frontend)
            self.assertIn("backendResourceId = azurerm_container_app.service[var.web.api].id", frontend)
            self.assertIn("if name != var.web.api", frontend)
            # No bucket, no CDN, no cache behaviour and no rewrite function: all four are the AWS shape.
            for absent in ("storage", "cdn", "cache_behavior", "rewrite"):
                self.assertNotIn(absent, frontend.lower(), absent)
            outputs = (repo / "infra/service/outputs.tf").read_text()
            self.assertIn("is deliberately absent", outputs)
            # Without a browser app every service keeps its own address, exactly as it would on AWS.
            bare = self.generate_azure(directory, "bare", frontend="none")
            self.assertIn("service_urls = local.all_service_urls", (bare / "infra/service/frontend.tf").read_text())

    def test_the_bootstrap_asks_for_the_directory_permission_only_where_an_answer_needs_it(self) -> None:
        """An app registration is a directory object, outside the subscription's RBAC, so the pipeline
        cannot create one on Owner alone. The grant that lets it is inside the `keycloak` marker, so a
        project that answered `--auth none` asks for no directory permission at all — which is what keeps
        the prerequisite a property of the answer rather than of the target."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_azure(directory, "identified", auth="entra")
            granted = (repo / "infra/bootstrap/main.tf").read_text()
            self.assertIn('azuread_service_principal.msgraph.app_role_ids["Application.ReadWrite.OwnedBy"]', granted)
            # And the staff identity is app roles rather than directory groups, so the claim carries the
            # same plain strings the local Keycloak realm does and nothing needs `Group.ReadWrite.All`.
            staff = (repo / "infra/service/entra_staff.tf").read_text()
            self.assertIn('OIDC_GROUPS_CLAIM   = "roles"', staff)
            self.assertIn('OIDC_GROUP_ADMIN    = "app-admin"', staff)
            self.assertNotIn("azuread_group", staff)
            # And `./init --auth none` takes the permission away with the answer. The region is in the
            # bootstrap stack rather than the service stack, which is the one place this target has a
            # marked region outside `infra/service/` — so the pruner has to know about that file too.
            subprocess.run(
                ["python3", "scripts/backing-services.py", "--auth", "none"],
                cwd=repo, check=True, capture_output=True,
            )
            self.assertNotIn("Application.ReadWrite", (repo / "infra/bootstrap/main.tf").read_text())
            self.assertEqual((repo / "infra/service/entra_staff.tf").read_text(), "")

    def test_every_stack_validates_against_the_real_providers_before_and_after_a_prune(self) -> None:
        if shutil.which("tofu") is None:
            self.skipTest("tofu is not installed; the factory's CI installs it")
        with tempfile.TemporaryDirectory() as directory:
            maximal = self.generate_azure(directory, "maximal", auth="entra")
            minimal = self.generate_azure(directory, "minimal", "go", "none", event_store="memory")
            for repo in (maximal, minimal):
                for stack in ("bootstrap", "service"):
                    with self.subTest(project=repo.name, stack=stack):
                        self.validate(repo / "infra" / stack)
            # `./init --event-store memory --auth none`, then the stack is still one stack.
            subprocess.run(
                ["python3", "scripts/backing-services.py", "--event-store", "memory", "--auth", "none"],
                cwd=maximal, check=True, capture_output=True,
            )
            self.assertEqual((maximal / "infra/service/postgres.tf").read_text(), "")
            self.assertEqual((maximal / "infra/service/entra_staff.tf").read_text(), "")
            self.assertNotIn("backing-service:postgres", (maximal / "infra/service/main.tf").read_text())
            self.validate(maximal / "infra/service")
            self.validate(maximal / "infra/bootstrap")
