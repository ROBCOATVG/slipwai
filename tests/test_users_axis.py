"""The `users` axis: who authenticates the product's own users, asked beside the staff question.

Keycloak answers both questions from one local container, a realm each, which is the first time two features
have shared anything a prune could take away — so most of what is asserted here is that boundary: what one
answer owns, what both share, and what happens to the shared part when one of them goes.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import PRUNER
from slipwai.axes import validate_axes
from slipwai.catalog import CATALOG
from slipwai.errors import GenerationError
from slipwai.project.languages.typescript import WEB_PACKAGE_ADDITIONS
from slipwai.selection import resolve_selection


def both_realms(test: FactoryTestCase, directory: str, name: str) -> Path:
    return test.generate(
        directory,
        name,
        "event-modelling",
        "typescript",
        "react-vite",
        event_store="sqlite",
        http="fastify",
        auth="keycloak",
        users="keycloak",
    )


class UsersAxisTest(FactoryTestCase):
    def test_keycloak_answers_both_identity_questions_from_one_container(self) -> None:
        """One `keycloak` service, two realm files, and each answer's own adapter, keys and prose."""
        with tempfile.TemporaryDirectory() as directory:
            repo = both_realms(self, directory, "two-realms")
            compose = (repo / "docker-compose.yml").read_text()
            self.assertEqual(compose.count("\n  keycloak:\n"), 1)
            self.assertIn("backing-service:keycloak|users-keycloak:begin", compose)
            self.assertIn("./docker/keycloak/realms:/opt/keycloak/data/import:ro", compose)
            self.assertIn("quay.io/keycloak/keycloak:26.7", compose)
            self.assertEqual(
                json.loads((repo / "docker/keycloak/realms/app.json").read_text())["realm"], "app"
            )
            customers = json.loads((repo / "docker/keycloak/realms/customers.json").read_text())
            self.assertEqual(customers["realm"], "customers")
            self.assertTrue(customers["registrationAllowed"])
            web_client = next(c for c in customers["clients"] if c["clientId"] == "web")
            self.assertTrue(web_client["publicClient"])
            self.assertEqual(web_client["attributes"]["pkce.code.challenge.method"], "S256")
            readme = (repo / "docker/keycloak/README.md").read_text()
            self.assertIn("realms/app.json", readme)
            self.assertIn("realms/customers.json", readme)

            environment = (repo / ".env.example").read_text()
            self.assertEqual(environment.count("KEYCLOAK_PORT=8081"), 1)
            self.assertIn("OIDC_ISSUER=http://localhost:8081/realms/app", environment)
            self.assertIn("USERS_OIDC_ISSUER=http://localhost:8081/realms/customers", environment)
            self.assertIn("VITE_USERS_CLIENT_ID=web", environment)

            for relative in (
                "apps/service/src/adapters/driving/http/auth/oidc-keycloak.ts",
                "apps/service/src/adapters/driving/http/users/oidc-keycloak.ts",
                "apps/service/tests/users/oidc-keycloak.test.ts",
                "apps/web/src/auth/users.tsx",
                "apps/web/src/auth/Account.tsx",
                "apps/web/tests/auth/Account.test.tsx",
            ):
                self.assertTrue((repo / relative).is_file(), relative)
            # The browser app owns the login: its entry point wraps the app, its manifest carries the client,
            # and the committed lock resolves it, so `npm ci` has nothing to complain about.
            self.assertIn("<UsersProvider>", (repo / "apps/web/src/main.tsx").read_text())
            package = json.loads((repo / "apps/web/package.json").read_text())
            self.assertEqual(package["dependencies"]["react-oidc-context"], "3.3.1")
            lock = json.loads((repo / "package-lock.json").read_text())
            self.assertIn("node_modules/oidc-client-ts", lock["packages"])

            metadata = json.loads((repo / "project.json").read_text())
            self.assertEqual(metadata["deployables"]["service"]["selection"]["users"], "keycloak")
            self.assertIn("users-keycloak", metadata["deployables"]["service"]["capabilities"])
            self.assertIn("the product's users", (repo / "README.md").read_text())
            self.assertIn("refuses any other issuer", (repo / "AGENTS.md").read_text())

    def test_dropping_one_realm_keeps_the_container_for_the_other(self) -> None:
        """A shared region names the features holding it; dropping one rewrites the marker rather than the
        region, and the container goes with the last realm."""
        with tempfile.TemporaryDirectory() as directory:
            repo = both_realms(self, directory, "one-realm")
            script = ["python3", "scripts/backing-services.py"]
            subprocess.run([*script, "--auth", "none"], cwd=repo, check=True, capture_output=True, text=True)

            compose = (repo / "docker-compose.yml").read_text()
            self.assertIn("\n  keycloak:\n", compose)
            self.assertIn("backing-service:users-keycloak:begin", compose)
            self.assertNotIn("keycloak|users-keycloak", compose)
            self.assertFalse((repo / "docker/keycloak/realms/app.json").exists())
            self.assertTrue((repo / "docker/keycloak/realms/customers.json").is_file())
            readme = (repo / "docker/keycloak/README.md").read_text()
            self.assertNotIn("realms/app.json", readme)
            self.assertIn("realms/customers.json", readme)
            environment = (repo / ".env.example").read_text()
            self.assertIn("KEYCLOAK_PORT=8081", environment)
            self.assertNotIn("OIDC_ISSUER=", environment.replace("USERS_OIDC_ISSUER=", ""))
            self.assertIn("USERS_OIDC_ISSUER=", environment)
            self.assertFalse((repo / "apps/service/src/adapters/driving/http/auth").exists())
            self.assertTrue((repo / "apps/service/src/adapters/driving/http/users").is_dir())
            # The staff question is settled and no longer offered; the customer one still is.
            listing = subprocess.run(
                [*script, "--list"], cwd=repo, check=True, capture_output=True, text=True
            ).stdout
            self.assertNotIn("--auth", listing)
            self.assertIn("--users", listing)

            subprocess.run([*script, "--users", "none"], cwd=repo, check=True, capture_output=True, text=True)
            compose = (repo / "docker-compose.yml").read_text()
            self.assertNotIn("keycloak", compose)
            self.assertFalse((repo / "docker").exists())
            self.assertFalse((repo / "apps/web/src/auth").exists())
            self.assertFalse((repo / "apps/web/tests/auth").exists())
            self.assertNotIn("UsersProvider", (repo / "apps/web/src/main.tsx").read_text())
            # The root `.env` stays the app's, because it never was this feature's: every `VITE_*` value
            # comes from there — a feature flag as much as a login — and an app that lost `envDir` with
            # `--users none` would read nothing at all.
            self.assertIn("envDir:", (repo / "apps/web/vite.config.ts").read_text())
            self.assertNotIn("users-keycloak", (repo / ".env.example").read_text())
            package = json.loads((repo / "apps/web/package.json").read_text())
            self.assertNotIn("react-oidc-context", package.get("dependencies", {}))

    def test_a_customer_login_needs_a_transport_to_present_the_token_to(self) -> None:
        with self.assertRaisesRegex(GenerationError, "nothing to validate"):
            resolve_selection(
                {"event-store": "memory", "http": "none", "auth": "none", "users": "keycloak"},
                "event-modelling",
                "typescript",
                "none",
            )
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory,
                "no-transport",
                "event-modelling",
                "typescript",
                "none",
                event_store="memory",
                http="fastify",
                users="keycloak",
            )
            refused = subprocess.run(
                ["python3", "scripts/backing-services.py", "--http", "none"],
                cwd=repo,
                capture_output=True,
                text=True,
            )
            self.assertEqual(refused.returncode, 2)
            self.assertIn("nothing to validate", refused.stderr)
            self.assertTrue((repo / "apps/service/src/adapters/driving/http/users").is_dir())

    def test_a_feature_belongs_to_one_axis_and_is_named_for_it(self) -> None:
        """`keycloak` is the staff axis's feature, so the customer option's is `users-keycloak` — the axis
        and the option — and nothing else would do."""
        shared = json.loads(json.dumps(CATALOG))
        shared["axes"]["users"]["options"]["keycloak"]["features"] = ["keycloak"]
        with self.assertRaisesRegex(ValueError, "owned by both the auth and users axes"):
            validate_axes(shared)
        misnamed = json.loads(json.dumps(CATALOG))
        misnamed["axes"]["users"]["options"]["keycloak"]["features"] = ["customers"]
        with self.assertRaisesRegex(ValueError, "named neither for an option of its own axis nor users-<option>"):
            validate_axes(misnamed)

    def test_the_browser_app_s_dependencies_are_removed_the_way_they_were_added(self) -> None:
        self.assertEqual(set(WEB_PACKAGE_ADDITIONS), set(PRUNER.WEB_PACKAGE_EDITS))
        for feature, additions in WEB_PACKAGE_ADDITIONS.items():
            self.assertEqual(set(additions), set(PRUNER.WEB_PACKAGE_EDITS[feature]), feature)
        # A feature that puts a dependency in a browser app puts files there too — the dependency is
        # what those files import. The reverse does not hold: the transport owns the route that calls
        # this project's API without the browser app taking a package for it.
        self.assertLessEqual(set(WEB_PACKAGE_ADDITIONS), set(PRUNER.OWNED_FILES_PER_WEB_APP))

    def test_a_shared_marker_names_only_the_features_still_holding_it(self) -> None:
        text = (
            "# backing-service:keycloak|users-keycloak:begin\nshared\n"
            "# backing-service:keycloak|users-keycloak:end\n"
            "# backing-service:keycloak:begin\nstaff\n# backing-service:keycloak:end\n"
        )
        one = PRUNER.strip_markers(text, {"users-keycloak"}, set())
        self.assertEqual(
            one, "# backing-service:users-keycloak:begin\nshared\n# backing-service:users-keycloak:end\n"
        )
        self.assertEqual(PRUNER.strip_markers(text, set(), set()), "")
        # Settling one feature drops its name from the marker; the region stays for the other.
        settled = PRUNER.strip_markers(text, {"keycloak", "users-keycloak"}, {"keycloak"})
        self.assertEqual(
            settled,
            "# backing-service:users-keycloak:begin\nshared\n# backing-service:users-keycloak:end\nstaff\n",
        )

    def test_a_browser_app_with_nothing_to_proxy_to_keeps_no_proxy(self) -> None:
        """A web app beside a service with no transport has no `/api` to forward, so the proxy — and the
        placeholder that named the transport — must both be gone."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "no-proxy", "event-modelling", "typescript", "react-vite", event_store="memory", http="none"
            )
            config = (repo / "apps/web/vite.config.ts").read_text()
            self.assertNotIn("__TRANSPORT__", config)
            self.assertNotIn("proxy:", config)
            self.assertNotIn("backing-service:", config)
