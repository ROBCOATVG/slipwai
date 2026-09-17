"""Auth0 on both identity axes, under both managed clouds.

The one answer in this factory whose infrastructure is not created by the cloud credential: an Auth0 tenant
is a third party, and `infra/service/auth0.tf` is applied with a machine-to-machine application's own
credentials. That single fact is what most of this suite is about — the provider must reach a project that
chose Auth0 and must not reach one that did not, because the provider refuses to configure itself without a
tenant credential and would fail every plan in a project that has none.

The apply itself ends in somebody's tenant and is unprovable here, exactly as it is for `aws` and `azure`.
What is proved is everything up to it.
"""
from __future__ import annotations

import json
import subprocess
import tempfile

from support import FactoryTestCase

from slipwai.catalog import CATALOG, axis_default, axis_options
from slipwai.targets import provisioned_as

CLOUDS = ("aws", "azure")
# A stem neither cloud's reserved words refuse, and every suffix below is held to the same rule: `aws`,
# `amazon` and `cognito` are refused anywhere inside a name, `azure` and about forty more as whole words.
NAME = "identity-demo"


class Auth0IdentityTest(FactoryTestCase):
    def generate_cloud(self, directory: str, target: str, name: str, **axes):
        backend = "typescript"
        return self.generate(
            directory, f"{NAME}-{name}", "event-modelling", backend, "react-vite", target=target,
            event_store="postgres", http=axis_default("http", backend, target), **axes,
        )

    # ── The catalog ───────────────────────────────────────────────────────────────────────────────────

    def test_auth0_answers_both_identity_axes_under_both_clouds_and_nowhere_else(self) -> None:
        """A third-party issuer is not a property of a cloud, so it is offered under both and under neither
        local target — there is no stack there to create anything with."""
        for axis in ("auth", "users"):
            option = CATALOG["axes"][axis]["options"]["auth0"]
            self.assertEqual(sorted(option["targets"]), ["aws", "azure"])
            for target in CLOUDS:
                self.assertIn("auth0", axis_options(axis, "typescript", target))
                self.assertEqual(provisioned_as(CATALOG, axis, "auth0", target), "auth0")
            for target in ("none", "existing"):
                self.assertNotIn("auth0", axis_options(axis, "typescript", target))

    def test_auth0_reuses_the_keycloak_features_so_the_adapters_cannot_tell_the_providers_apart(self) -> None:
        """The same files Keycloak and Cognito use. Every answer on these axes is an OIDC issuer, so what
        differs between them is configuration — which is the property the axes are named for."""
        self.assertEqual(CATALOG["axes"]["auth"]["options"]["auth0"]["features"], ["keycloak"])
        self.assertEqual(CATALOG["axes"]["users"]["options"]["auth0"]["features"], ["users-keycloak"])
        self.assertEqual(CATALOG["axes"]["auth"]["options"]["auth0"]["containers"], ["keycloak"])

    # ── The file pair ─────────────────────────────────────────────────────────────────────────────────

    def test_only_a_project_that_chose_auth0_carries_the_provider(self) -> None:
        """The whole reason `auth0.tf` and `no-auth0.tf` are chosen between at generation time rather than
        pruned later: `keycloak` is the feature behind Cognito, Entra *and* Auth0, so no marker can tell
        them apart — and a `provider "auth0"` block in a project with no tenant credential fails every plan.
        """
        with tempfile.TemporaryDirectory() as directory:
            for index, (target, native) in enumerate((("aws", "cognito"), ("azure", "entra"))):
                chose = self.generate_cloud(directory, target, f"chose-{index}", auth="auth0", users="auth0")
                stack = (chose / "infra/service/auth0.tf").read_text()
                self.assertIn('provider "auth0"', stack)
                self.assertIn("auth0_client", stack)
                self.assertFalse((chose / "infra/service/no-auth0.tf").exists())

                did_not = self.generate_cloud(directory, target, f"without-{index}", auth=native, users="none")
                empty = (did_not / "infra/service/auth0.tf").read_text()
                self.assertNotIn('provider "auth0"', empty)
                self.assertNotIn("auth0_client", empty)
                self.assertIn("auth0_staff_environment     = {}", empty)

    def test_the_pin_is_declared_for_every_project_because_a_module_may_have_only_one(self) -> None:
        """A module may have one `required_providers` block, so the pin cannot travel with the answer the
        way the resources do. Declaring a provider is not configuring one — nothing asks it for a credential
        until a resource refers to it, which is what makes this safe."""
        with tempfile.TemporaryDirectory() as directory:
            for index, (target, native) in enumerate((("aws", "cognito"), ("azure", "entra"))):
                project = self.generate_cloud(directory, target, f"pinned-{index}", auth=native, users="none")
                versions = (project / "infra/service/versions.tf").read_text()
                self.assertIn('auth0 = {', versions)
                self.assertIn('source  = "auth0/auth0"', versions)

    # ── What the stack hands a service ────────────────────────────────────────────────────────────────

    def test_the_staff_environment_carries_the_same_keys_the_local_stand_in_does(self) -> None:
        """Keycloak stays the local stand-in for this answer as for the other two, so a service reads the
        same six names whichever provider is in front of it."""
        with tempfile.TemporaryDirectory() as directory:
            project = self.generate_cloud(directory, "aws", "chosen", auth="auth0", users="auth0")
            stack = (project / "infra/service/auth0.tf").read_text()
            for key in (
                "OIDC_ISSUER", "OIDC_CLIENT_ID", "OIDC_GROUPS_CLAIM",
                "OIDC_GROUP_ADMIN", "OIDC_GROUP_OPERATOR", "OIDC_GROUP_VIEWER",
            ):
                self.assertIn(key, stack)
            # The customer half, and the audience that is the whole of what separates the two populations.
            self.assertIn("USERS_OIDC_ISSUER", stack)
            self.assertIn("USERS_OIDC_AUDIENCE", stack)

    def test_staff_and_customers_are_two_connections_and_two_clients_never_one_with_a_flag(self) -> None:
        """The same separation the local Keycloak makes with two realms and Cognito with two pools. Sign-up
        is off for staff, who are accounts an administrator creates, and on for customers."""
        with tempfile.TemporaryDirectory() as directory:
            project = self.generate_cloud(directory, "azure", "chosen", auth="auth0", users="auth0")
            stack = (project / "infra/service/auth0.tf").read_text()
            self.assertIn('resource "auth0_connection" "staff"', stack)
            self.assertIn('resource "auth0_connection" "customers"', stack)
            self.assertIn('resource "auth0_client" "staff"', stack)
            self.assertIn('resource "auth0_client" "customers"', stack)
            staff, customers = stack.split('resource "auth0_connection" "customers"')
            self.assertIn("disable_signup          = true", staff)
            self.assertIn("disable_signup         = false", customers)

    def test_the_one_issuer_both_populations_share_is_written_down_where_a_reader_will_meet_it(self) -> None:
        """The divergence from every other answer on these axes, and the one with a security consequence:
        under Keycloak and Cognito an issuer check separates staff from customers, and here it cannot. It is
        recorded in the stack and in the ADR rather than left for somebody to discover from a token."""
        with tempfile.TemporaryDirectory() as directory:
            project = self.generate_cloud(directory, "aws", "chosen", auth="auth0", users="auth0")
            stack = (project / "infra/service/auth0.tf").read_text()
            self.assertIn("what separates them is the audience", stack)
            adr = (project / "docs/adr/0002-production-target.md").read_text()
            self.assertIn("Staff and customers share one issuer here", adr)

    # ── The pipeline ──────────────────────────────────────────────────────────────────────────────────

    def test_only_an_auth0_project_carries_the_tenant_credential_in_its_workflows(self) -> None:
        """An empty `AUTH0_DOMAIN` in a Cognito project's workflow would read as configuration and do
        nothing, which is the one thing a generated file here may never be."""
        with tempfile.TemporaryDirectory() as directory:
            chose = self.generate_cloud(directory, "aws", "chose", auth="auth0", users="auth0")
            for workflow in ("deploy.yml", "production.yml", "rollback.yml"):
                text = (chose / ".github/workflows" / workflow).read_text()
                self.assertIn("AUTH0_DOMAIN: ${{ vars.AUTH0_DOMAIN }}", text)
                self.assertIn("AUTH0_CLIENT_SECRET: ${{ secrets.AUTH0_CLIENT_SECRET }}", text)
            did_not = self.generate_cloud(directory, "aws", "not", auth="cognito", users="cognito")
            for workflow in ("deploy.yml", "production.yml", "rollback.yml"):
                self.assertNotIn("AUTH0", (did_not / ".github/workflows" / workflow).read_text())

    def test_the_bootstrap_asks_for_the_credential_the_cloud_cannot_issue(self) -> None:
        """Two identifiers and one secret, asked for rather than produced: nothing in this repository can
        create an Auth0 tenant, so the bootstrap's job is to carry the answer to the forge and no more."""
        with tempfile.TemporaryDirectory() as directory:
            project = self.generate_cloud(directory, "azure", "chosen", auth="auth0", users="auth0")
            bootstrap = (project / "scripts/bootstrap.py").read_text()
            self.assertIn('AUTH0_VARIABLES = ("AUTH0_DOMAIN", "AUTH0_CLIENT_ID")', bootstrap)
            self.assertIn('AUTH0_SECRETS = ("AUTH0_CLIENT_SECRET",)', bootstrap)
            # It decides from the same file the stack reads, not from a flag somebody has to remember.
            self.assertIn("def uses_auth0()", bootstrap)
            services = json.loads((project / "infra/service/project.auto.tfvars.json").read_text())["services"]
            self.assertEqual({s["auth"] for s in services.values()}, {"auth0"})
            self.assertEqual({s["users"] for s in services.values()}, {"auth0"})

    # ── Pruning ───────────────────────────────────────────────────────────────────────────────────────

    def test_dropping_both_identity_answers_leaves_nothing_that_asks_for_a_tenant_credential(self) -> None:
        """`./init` can still take an answer away, and when it takes both the provider must go with them —
        a `provider "auth0"` block left behind would fail every plan in a project that no longer has a
        credential for it."""
        with tempfile.TemporaryDirectory() as directory:
            project = self.generate_cloud(directory, "aws", "chosen", auth="auth0", users="auth0")
            subprocess.run(
                ["python3", "scripts/backing-services.py", "--auth", "none", "--users", "none"],
                cwd=project, check=True, capture_output=True, text=True,
            )
            stack = (project / "infra/service/auth0.tf").read_text()
            self.assertNotIn("auth0", stack.replace("auth0.tf", ""))
            self.assertNotIn("provider", stack)
