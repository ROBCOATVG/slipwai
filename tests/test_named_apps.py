"""The first service and the first browser app under names the generation chose.

`service` and `web` were the only names a project could start with, which was fine while a project had one
of each; once `add-service` names every later one, the first being unnameable is the odd one out. The proof
is the same as for a second service: a project named otherwise passes its own `make verify`, grows through
`add-service` and `add-frontend`, and nothing in it still says `apps/service` or `apps/web`.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_add_service import add_frontend, add_service, commit_all

from slipwai.assets import PRUNER, ROOT
from slipwai.manifest import apps_from_manifest
from slipwai.selection import Selection
from slipwai.services import default_apps
from slipwai.tooling import service_qualifier


def leftovers(repo: Path) -> list[str]:
    """Every line under the repository that still spells the default names as paths."""
    result = subprocess.run(
        ["grep", "-rn", "--exclude-dir=.git", "--exclude-dir=node_modules", "--exclude=package-lock.json",
         "-e", "apps/service", "-e", "apps/web", "."],
        cwd=repo, text=True, capture_output=True,
    )
    return result.stdout.splitlines()


class NamedAppsTest(FactoryTestCase):
    def test_a_project_named_otherwise_passes_its_own_gate_and_grows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(
                [str(ROOT / "slipwai"), "generate", "acme", "--profile", "event-modelling", "--backend", "typescript",
                 "--frontend", "react-vite", "--auth", "keycloak", "--service-name", "ledger",
                 "--frontend-name", "portal", "--output", directory],
                check=True,
            )
            repo = Path(directory) / "acme"
            manifest = json.loads((repo / "project.json").read_text())
            self.assertEqual(list(manifest["deployables"]), ["ledger", "portal"])
            self.assertEqual(manifest["deployables"]["ledger"]["path"], "apps/ledger")
            self.assertEqual(manifest["deployables"]["portal"]["api"], "ledger")
            self.assertTrue((repo / "apps/ledger/src/main.ts").is_file())
            self.assertTrue((repo / "apps/portal/vite.config.ts").is_file())
            self.assertFalse((repo / "apps/service").exists())
            # The first of each kind keeps the role, whatever it is called: `make dev`, `PORT`, the project's
            # own package name.
            makefile = (repo / "Makefile").read_text()
            self.assertIn("\ndev: ##", makefile)
            self.assertIn("\ndev-web: ##", makefile)
            self.assertIn("apps/ledger", makefile)
            apps = apps_from_manifest(manifest)
            self.assertTrue(apps[0].first and apps[1].first)
            self.assertEqual(service_qualifier("acme", apps[0]), "acme")
            self.assertEqual(json.loads((repo / "apps/ledger/package.json").read_text())["name"], "acme-ledger")
            # Every copied asset that spoke of `apps/service` and `apps/web` now speaks of these two: the
            # skeleton's own comments, the skills, the Spec Kit templates, the Keycloak notes.
            self.assertEqual(leftovers(repo), [])
            self.assertIn("apps/portal/**", (repo / "skills/event-sourcing/SKILL.md").read_text())
            self.assertIn("apps/ledger", (repo / "docker/keycloak/README.md").read_text())
            self.assertIn("apps/ledger", (repo / "apps/ledger/src/main.ts").read_text())
            for name in ("add-service", "add-frontend"):
                self.assertIn("- `ledger` — typescript, port 3000", (repo / f"commands/{name}.md").read_text())

            result = add_service(repo, "payments", "--language", "python")
            self.assertEqual(result.returncode, 0, result.stderr)
            # A later service's own files speak of that service, not of the first — which was wrong before
            # names could differ too, when a second skeleton's comments still said `apps/service`.
            main = next((repo / "apps/payments/src").glob("*/main.py"))
            self.assertIn("apps/payments", main.read_text())
            self.assertEqual(leftovers(repo), [])
            commit_all(repo, "add payments")
            result = add_frontend(repo, "admin", "--api", "payments")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(PRUNER.project_web_apps(repo), ["apps/portal", "apps/admin"])
            # Each browser app's dev-server proxy is a marked region, and the pruner has to be able to find
            # the second one's too.
            self.assertIn("apps/admin/vite.config.ts", PRUNER.marked_files([], PRUNER.project_web_apps(repo)))
            commit_all(repo, "add admin")

            verify = subprocess.run(["make", "verify"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(verify.returncode, 0, verify.stdout[-4000:] + verify.stderr[-4000:])

    def test_the_names_are_refused_where_they_cannot_be_applications(self) -> None:
        for flags, message in (
            (("--service-name", "Ledger"), "cannot name an application"),
            (("--service-name", "web"), "already has an application named 'web'"),
            (("--frontend", "none", "--frontend-name", "portal"), "--frontend none has none to name"),
        ):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as directory:
                result = subprocess.run(
                    [str(ROOT / "slipwai"), "generate", "refused", *flags, "--output", directory],
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertFalse((Path(directory) / "refused").exists())

    def test_the_defaults_are_the_names_every_project_had(self) -> None:
        apps = default_apps("go", "react-vite", Selection({}))
        self.assertEqual([app.path for app in apps], ["apps/service", "apps/web"])
        self.assertEqual([app.dev_target for app in apps], ["dev", "dev-web"])
        named = default_apps("go", "react-vite", Selection({}), "api", "console")
        self.assertEqual([app.path for app in named], ["apps/api", "apps/console"])
        self.assertEqual([app.dev_target for app in named], ["dev", "dev-web"])
        self.assertEqual(named[1].api, "api")
