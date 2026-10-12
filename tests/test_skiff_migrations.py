"""Exercise the Lightsail migration controller across its real file/process boundary with a fake cloud CLI.

The provider itself is validated separately. These cases prove result receipts and cleanup, without an
account or paid resources; all wrapper/request/log files are real and only subprocess responses are fake.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1] / "packages/aws"
IMAGE = "123456789012.dkr.ecr.eu-west-2.amazonaws.com/tool-service@sha256:" + "a" * 64


def module():
    spec = importlib.util.spec_from_file_location("skiff_migrations_test", PACKAGE / "scripts/skiff_migrations.py")
    assert spec and spec.loader
    found = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(found)
    return found


class CloudCLI:
    def __init__(self, verdict="0", ownership=True, cleanup_fault=False):
        self.verdict = verdict
        self.ownership = ownership
        self.cleanup_fault = cleanup_fault
        self.created: dict[str, Any] = {}
        self.deleted = []
        self.deleted_images = []
        self.document: dict[str, Any] = {
            "Version": "2012-10-17", "Statement": {"Sid": "ExistingAccess", "Effect": "Allow"},
        }
        self.wrapper = ""
        self.payload: dict[str, Any] = {}
        self.commands = []

    def __call__(self, command, **options):
        self.commands.append(command)
        result: Any = {}
        if command[0] == "docker":
            if command[1:3] == ["image", "inspect"]:
                if ":slipwai-migrate-" in command[3]:
                    repository = command[3].split(":slipwai-migrate-", 1)[0]
                    result = [{"RepoDigests": [repository + "@sha256:" + "b" * 64]}]
                else:
                    result = [{"Config": {"Entrypoint": ["/cnb/process/web"], "Cmd": []}}]
            if command[1] == "build":
                self.wrapper = (Path(options["cwd"]) / "wrapper.sh").read_text()
        elif command[1] == "ecr":
            if command[2] == "get-repository-policy":
                result = {"policyText": json.dumps(self.document)}
            elif command[2] == "set-repository-policy":
                request = json.loads(Path(command[command.index("--cli-input-json") + 1][7:]).read_text())
                self.document = json.loads(request["policyText"])
            elif command[2] == "batch-delete-image":
                self.deleted_images.append(command[command.index("--image-ids") + 1])
                if self.cleanup_fault:
                    result = {"failures": [{"failureCode": "ImageNotFound"}]}
        elif command[2] == "create-container-service":
            self.created = json.loads(Path(command[command.index("--cli-input-json") + 1][7:]).read_text())
        elif command[2] == "get-container-services":
            service = {"state": "READY", "tags": self.created["tags"] if self.ownership else [],
                       "privateRegistryAccess": {"ecrImagePullerRole": {"principalArn": "arn:aws:iam::1:role/temp"}}}
            result = {"containerServices": [service]}
        elif command[2] == "create-container-service-deployment":
            self.payload = json.loads(Path(command[command.index("--cli-input-json") + 1][7:]).read_text())
        elif command[2] == "get-container-log":
            token = self.created["tags"][0]["value"]
            result = {"logEvents": [{"message": "postgres://app:very-secret@private:5432/app"},
                                    {"message": "driver password very-secret"},
                                    {"message": f"slipwai-migration:{token}:{self.verdict}"}]}
        elif command[2] == "delete-container-service":
            self.deleted.append(command[command.index("--service-name") + 1])
        return subprocess.CompletedProcess(command, 0, json.dumps(result), "")


class MigrationReceiptTest(unittest.TestCase):
    def exercise(self, cloud, *, deadline=False):
        found = module()
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(found.subprocess, "run", side_effect=cloud), \
                contextlib.redirect_stderr(io.StringIO()) as diagnostics:
            logs = Path(directory)
            environment = {"DATABASE_URL": "postgres://app:very-secret@private:5432/app"}
            clock: Any
            if deadline:
                clock = patch.object(found.time, "monotonic", side_effect=[0, 0, 1000])
            else:
                clock = contextlib.nullcontext()
            with clock:
                try:
                    found.migrate("tool", "service", IMAGE, ["npx", "tsx", "migrate.ts"], environment, logs)
                except found.Failure as fault:
                    failure = str(fault)
                else:
                    failure = ""
            retained = list(logs.glob("*.log"))
            self.assertEqual(len(retained), 1)
            text = retained[0].read_text()
            self.assertNotIn("very-secret", text + diagnostics.getvalue() + failure)
            return failure, text

    def test_exact_success_receipt_preserves_other_policy_and_removes_only_owned_temporary_resources(self):
        cloud = CloudCLI()
        failure, text = self.exercise(cloud)
        self.assertFalse(failure, failure)
        self.assertIn("[redacted]", text)
        self.assertIn("/cnb/lifecycle/launcher npx tsx migrate.ts", cloud.wrapper)
        self.assertNotIn("/cnb/process/web", cloud.wrapper)
        self.assertEqual(cloud.deleted, [cloud.created["serviceName"]])
        self.assertEqual([row["Sid"] for row in cloud.document["Statement"]], ["ExistingAccess"])
        self.assertEqual(len(cloud.deleted_images), 1)
        self.assertTrue(cloud.deleted_images[0].startswith("imageTag=slipwai-migrate-"))
        self.assertEqual(cloud.payload["containers"]["migration"]["environment"]["DATABASE_URL"],
                         "postgres://app:very-secret@private:5432/app")

    def test_nonzero_receipt_refuses_deploy_but_still_cleans_up_and_retains_redacted_diagnostics(self):
        cloud = CloudCLI(verdict="7")
        failure, text = self.exercise(cloud)
        self.assertIn("migration reported exit 7", failure)
        self.assertIn("make migrate-remote ENV=production", failure)
        self.assertIn(":7", text)
        self.assertEqual(cloud.deleted, [cloud.created["serviceName"]])

    def test_ready_or_active_without_a_result_marker_never_means_migration_success(self):
        cloud = CloudCLI()
        failure, _text = self.exercise(cloud, deadline=True)
        self.assertIn("result marker did not arrive", failure)
        self.assertEqual(cloud.deleted, [cloud.created["serviceName"]])

    def test_cleanup_refuses_an_unowned_service_even_after_its_name_was_created(self):
        cloud = CloudCLI(ownership=False)
        failure, _text = self.exercise(cloud)
        self.assertIn("unowned Lightsail service", failure)
        self.assertEqual(cloud.deleted, [])

    def test_cleanup_failure_is_visible_even_after_a_successful_migration_receipt(self):
        cloud = CloudCLI(cleanup_fault=True)
        failure, _text = self.exercise(cloud)
        self.assertIn("temporary image cleanup failed", failure)
        self.assertEqual(cloud.deleted, [cloud.created["serviceName"]])
        self.assertEqual([row["Sid"] for row in cloud.document["Statement"]], ["ExistingAccess"])

    def test_an_old_or_other_run_receipt_is_ignored_until_the_deadline(self):
        found = module()
        with patch.object(found, "aws", return_value={"logEvents": [{"message": "slipwai-migration:old-run:0"}]}), \
                patch.object(found.time, "monotonic", side_effect=[0, 10, 20]), \
                patch.object(found.time, "sleep"), \
                self.assertRaisesRegex(found.Failure, "result marker did not arrive"):
            found.result("service", "current-run", 15, [])

    def test_wrappers_quote_original_argv_without_reinterpreting_shell_metacharacters(self):
        found = module()
        script = found.wrapper(["/app/migrate", "argument;echo wrong", "dollar$()"], "run-id")
        self.assertIn("'/app/migrate'".strip("'"), script)
        self.assertIn("'argument;echo wrong'", script)
        self.assertIn("'dollar$()'", script)
        self.assertIn("/slipwai/busybox sleep", script)


class AdapterBoundaryTest(unittest.TestCase):
    def adapter(self, store=None, command=None):
        import sys
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        scripts = root / "scripts"
        scripts.mkdir()
        for destination, source in (("deploy.py", "skiff_deploy.py"), ("_deploy_common.py", "deploy.py")):
            (scripts / destination).write_text((PACKAGE / "scripts" / source).read_text(), encoding="utf-8")
        stack = root / "infra/service"
        stack.mkdir(parents=True)
        (stack / "project.auto.tfvars.json").write_text(json.dumps({
            "project": "tool", "services": {"service": {"store": store, "migrate_command": command}},
        }), encoding="utf-8")
        spec = importlib.util.spec_from_file_location("skiff_adapter_test", scripts / "deploy.py")
        assert spec and spec.loader
        found = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"skiff_migrations": module()}):
            spec.loader.exec_module(found)
        return found

    def test_staging_is_refused_before_workspace_or_cloud_commands(self):
        found = self.adapter()
        with patch.object(found.common, "select_workspace") as workspace, \
                contextlib.redirect_stderr(io.StringIO()) as message:
            self.assertEqual(found.main(["deploy", "staging"]), 1)
            workspace.assert_not_called()
            self.assertIn("make deploy ENV=production", message.getvalue())

    def test_removing_a_deployed_database_is_refused_before_any_apply(self):
        found = self.adapter()
        with patch.object(found.common, "select_workspace"), \
                patch.object(found.common, "outputs", return_value={"database_name": "protected"}), \
                patch.object(found.common, "apply") as apply, \
                self.assertRaisesRegex(found.common.Failure, "No apply or deletion has run"):
            found.prepared("production", {})
        apply.assert_not_called()

    def test_rollback_cannot_bypass_database_retention_after_a_prune(self):
        found = self.adapter()
        with patch.object(found.common, "select_workspace"), \
                patch.object(found.common, "outputs", return_value={"database_name": "protected"}), \
                patch.object(found.common, "rollback") as rollback, \
                self.assertRaisesRegex(found.common.Failure, "preserve the database/state"):
            found.guarded(rollback, "production")
        rollback.assert_not_called()

    def test_unknown_or_pending_tls_enforcement_refuses_to_start_work(self):
        found = self.adapter()
        parameters = {"parameters": [{"parameterName": "rds.force_ssl", "parameterValue": "0",
                                      "isModifiable": True, "applyType": "static"}]}
        with patch.object(found.skiff_migrations, "aws", return_value=parameters), \
                patch.object(found.skiff_migrations, "payload") as update, \
                self.assertRaisesRegex(found.common.Failure, "rds.force_ssl=1"):
            found.database_tls("protected")
        update.assert_not_called()

    def test_failed_remote_migration_never_applies_application_or_records_a_release(self):
        found = self.adapter(store="rds", command=["npx", "tsx", "migrate.ts"])
        database = {"database_name": "db", "database_url": "secret"}
        failure = found.skiff_migrations.Failure("job failed")
        with patch.object(found.common, "current_sha", return_value="commit"), \
                patch.object(found.common, "images_of", return_value={"service": IMAGE}), \
                patch.object(found.common, "select_workspace"), \
                patch.object(found.common, "outputs", return_value={}), \
                patch.object(found.common, "apply", return_value=database) as apply, \
                patch.object(found, "database_tls"), \
                patch.object(found.skiff_migrations, "migrate", side_effect=failure), \
                patch.object(found.common, "record_release") as release, \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(found.main(["deploy", "production"]), 1)
        self.assertEqual(apply.call_count, 1)
        self.assertIn("aws_lightsail_database.database", apply.call_args.args)
        release.assert_not_called()
