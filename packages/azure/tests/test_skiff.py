"""Azure's skiff stays on production and refuses staging before any external operation."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, PACKAGE / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AzureSkiffTest(unittest.TestCase):
    @staticmethod
    def tfvars(path: Path) -> dict[str, str]:
        """An environment file as the keys it sets, so a test says which value it means."""
        settings = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            settings[name.strip()] = value.strip()
        return settings

    def test_production_keeps_resource_sources_while_staging_is_absent(self) -> None:
        from slipwai_target_azure import TARGET

        from slipwai.target_protocol import DEPLOYMENT_SHAPES, SHAPES
        rows = TARGET.answers[DEPLOYMENT_SHAPES]
        skiff, liner = rows["skiff"], rows["liner"]
        self.assertEqual(skiff["environments"], ("production",))
        self.assertEqual(liner["environments"], ("staging", "production"))
        self.assertNotIn("service/staging.tfvars", skiff["stacks"]["service"])
        self.assertEqual(skiff["stacks"]["service"]["service/production.tfvars"],
                         "skiff/production.tfvars")
        for phase, paths in TARGET.answers[SHAPES].items():
            self.assertEqual(liner["stacks"][phase], {p: p for p in paths})
        for source in skiff["stacks"]["service"].values():
            self.assertTrue((PACKAGE / source).is_file(), source)
        self.assertEqual(skiff["stacks"]["service"]["service/postgres.tf"], "service/postgres.tf")

    def test_the_skiffs_own_environment_file_is_what_scales_it_to_zero_and_wakes_it(self) -> None:
        """Read through the skiff's row, not past it.

        Azure's skiff is the liner's HCL given a different environment, so a test that reads
        `service/main.tf` and `service/postgres.tf` and stops there proves the liner and would pass with
        the skiff deleted. What is the skiff's is `skiff/production.tfvars` — reached here the way the
        keel reaches it, through the row — and the claims the row makes about it. So: the floor the skiff
        sets, that it is lower than the liner's, that each name it sets is a variable the app template
        actually reads, and that a floor of zero has something to wake it.
        """
        from slipwai_target_azure import TARGET

        from slipwai.target_protocol import DEPLOYMENT_SHAPES
        rows = TARGET.answers[DEPLOYMENT_SHAPES]
        skiff, liner = rows["skiff"], rows["liner"]
        settings = self.tfvars(PACKAGE / skiff["stacks"]["service"]["service/production.tfvars"])
        self.assertEqual(settings["min_replicas"], "0")
        self.assertEqual(settings["max_replicas"], "1")
        # Nothing kept warm beside the release: a rollback here is a restart, which is the trade a staff
        # tool makes and a product does not.
        self.assertEqual(settings["kept_revisions"], "0")
        liner_settings = self.tfvars(PACKAGE / liner["stacks"]["service"]["service/production.tfvars"])
        self.assertNotEqual(liner_settings["min_replicas"], settings["min_replicas"])
        self.assertNotEqual(liner_settings["kept_revisions"], settings["kept_revisions"])
        # Every name the skiff sets is a variable the stack declares — a tfvars key nothing reads is a
        # setting that silently does nothing — and the two that scale it reach the app's template.
        declared = (PACKAGE / "service/variables.tf").read_text()
        for name in settings:
            self.assertIn(f'variable "{name}"', declared, name)
        stack = (PACKAGE / "service/main.tf").read_text()
        self.assertIn("min_replicas = var.min_replicas", stack)
        self.assertIn("max_replicas = var.max_replicas", stack)
        self.assertIn("max_inactive_revisions       = var.kept_revisions", stack)
        # A floor of zero is only usable because a request can wake it: external HTTP ingress and the one
        # scaler Container Apps has of its own. The row says so in the words an operator reads.
        self.assertIn("http_scale_rule", stack)
        self.assertIn("external_enabled = true", stack)
        self.assertIn("HTTP", skiff["guidance"])
        self.assertIn("cold-start", skiff["guidance"])

    def test_the_rows_database_claim_is_true_of_the_file_the_skiff_actually_ships(self) -> None:
        """The row tells an operator the database keeps its firewall and TLS policy and does not sleep.

        The skiff takes the liner's `service/postgres.tf` unchanged, which is exactly why the claim has to
        be checked against it: the compute scales to zero and the database does not, and an operator who
        read "scale to zero" as the whole project's would plan the bill and the recovery wrong.
        """
        from slipwai_target_azure import TARGET

        from slipwai.target_protocol import DEPLOYMENT_SHAPES
        skiff = TARGET.answers[DEPLOYMENT_SHAPES]["skiff"]
        source = skiff["stacks"]["service"]["service/postgres.tf"]
        self.assertEqual(source, "service/postgres.tf")
        database = (PACKAGE / source).read_text()
        self.assertIn("require_secure_transport", database)
        self.assertIn("azurerm_postgresql_flexible_server_firewall_rule", database)
        self.assertIn("firewall", skiff["database"])
        self.assertIn("TLS", skiff["database"])
        self.assertIn("does not scale to zero", skiff["guidance"])

    def test_staging_and_promotion_are_refused_without_invoking_tools(self) -> None:
        deploy = load("azure_skiff_deploy", "scripts/deploy.py")
        with patch.object(deploy, "manifest", return_value={"shape": "skiff"}), \
                patch.object(deploy, "which") as which, \
                patch.object(deploy, "tofu") as tofu, \
                patch.object(deploy, "origin") as origin:
            with self.assertRaisesRegex(deploy.Failure, "make deploy ENV=production"):
                deploy.select_workspace("staging")
            with self.assertRaisesRegex(deploy.Failure, "make deploy ENV=production"):
                deploy.promote([])
            which.assert_not_called()
            tofu.assert_not_called()
            origin.assert_not_called()

    def test_existing_manifests_still_allow_the_liner_staging_workspace(self) -> None:
        deploy = load("azure_liner_deploy", "scripts/deploy.py")
        with patch.object(deploy, "manifest", return_value={}), \
                patch.object(deploy, "which"), \
                patch.object(deploy, "setting", return_value="configured"), \
                patch.object(deploy, "tofu") as tofu:
            deploy.select_workspace("staging")
            self.assertEqual(tofu.call_args.args, ("workspace", "select", "-or-create", "staging"))
