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

    def test_zero_replica_configuration_has_http_wake_and_truthful_database_policy(self) -> None:
        from slipwai_target_azure import TARGET

        from slipwai.target_protocol import DEPLOYMENT_SHAPES
        variables = (PACKAGE / "skiff/production.tfvars").read_text()
        self.assertRegex(variables, r"min_replicas\s*=\s*0")
        stack = (PACKAGE / "service/main.tf").read_text()
        self.assertIn("http_scale_rule", stack)
        self.assertIn("external_enabled", stack)
        self.assertIn("HTTP", TARGET.answers[DEPLOYMENT_SHAPES]["skiff"]["guidance"])
        database = (PACKAGE / "service/postgres.tf").read_text()
        self.assertIn("require_secure_transport", database)
        self.assertIn("firewall", TARGET.answers[DEPLOYMENT_SHAPES]["skiff"]["database"])

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
