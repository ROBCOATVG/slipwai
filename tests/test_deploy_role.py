"""The two stacks that meet at the deploy role, held to each other before production is where they meet.

`infra/bootstrap/` grants the deploy role what it may do, once, by a person with admin credentials;
`infra/service/` is applied by that role on every push to `main`. A generated project reported the gap
between them the expensive way: a slice added an `aws_iam_user`, the role could only touch roles, and the
production apply failed part-way on `iam:CreateUser` — with nothing in the failure saying the fix was a
statement in `infra/bootstrap/main.tf` and a `make bootstrap`. So `check-deploy-role` makes it a red
`verify`, and `deploy.py` names the fix when an apply is refused anyway.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from support import FactoryTestCase

USER = 'resource "aws_iam_user" "reporter" {\n  name = "${var.project}-reporter" # "a quote" and a {brace}\n}\n'
USER_GRANT = """
data "aws_iam_policy_document" "deploy_iam_users" {
  statement {
    actions   = ["iam:CreateUser", "iam:DeleteUser", "iam:GetUser", "iam:TagUser"]
    resources = ["arn:aws:iam::${local.account}:user/${var.project}-*"]
  }
}

resource "aws_iam_role_policy" "deploy_iam_users" {
  name   = "iam-users-for-this-project"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy_iam_users.json
}
"""
# `tofu apply` refused on the deploy role's own grants, the way AWS words it.
FAKE_TOFU = """#!/bin/sh
echo "aws_iam_user.reporter: Creating..." 
echo "│ Error: creating IAM User (shop-staging-reporter): operation error IAM: CreateUser, StatusCode: 403, \
api error AccessDenied: User: arn:aws:sts::123456789012:assumed-role/shop-deploy/ci is not authorized to \
perform: iam:CreateUser on resource: arn:aws:iam::123456789012:user/shop-staging-reporter" >&2
exit 1
"""


class DeployRoleTest(FactoryTestCase):
    def gate(self, repo: Path) -> subprocess.CompletedProcess:
        return subprocess.run(["make", "-s", "check-deploy-role"], cwd=repo, text=True, capture_output=True)

    def test_verify_fails_when_the_service_stack_declares_iam_the_deploy_role_cannot_create(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "shop", profile="standard", target="aws")
            makefile = (repo / "Makefile").read_text()
            self.assertRegex(makefile, r"\nverify: [^\n]* check-deploy-role ")
            self.assertTrue(os.access(repo / "scripts/check-deploy-role.py", os.X_OK))

            clean = self.gate(repo)
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
            self.assertRegex(clean.stdout, r"check-deploy-role: \d+ IAM resource\(s\) in infra/service/, each within")

            (repo / "infra/service/reporter.tf").write_text(USER)
            refused = self.gate(repo)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("infra/service/reporter.tf: aws_iam_user.reporter needs iam:CreateUser on user/…",
                          refused.stdout)
            self.assertIn("aws_iam_user.reporter needs iam:DeleteUser", refused.stdout)
            self.assertIn("infra/bootstrap/main.tf", refused.stdout)
            self.assertIn("run `make bootstrap`", refused.stdout)

            # Granted on roles is not granted on users: widening the role statement's actions is not the fix.
            main = repo / "infra/bootstrap/main.tf"
            original = main.read_text()
            main.write_text(original.replace('"iam:CreateRole",', '"iam:CreateRole",\n      "iam:CreateUser",'))
            self.assertIn("needs iam:CreateUser on user/…", self.gate(repo).stdout)

            main.write_text(original + USER_GRANT)
            granted = self.gate(repo)
            self.assertEqual(granted.returncode, 0, granted.stdout)

            # A policy document nobody attaches to the deploy role grants the deploy role nothing.
            main.write_text(original + USER_GRANT.replace("aws_iam_role.deploy.id", "aws_iam_role.other.id"))
            self.assertNotEqual(self.gate(repo).returncode, 0)

    def test_a_type_without_a_row_fails_and_a_commented_resource_is_not_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "shop", profile="standard", target="aws")
            (repo / "infra/service/old.tf").write_text("# " + USER.replace("\n", "\n# "))
            self.assertEqual(self.gate(repo).returncode, 0)
            (repo / "infra/service/mfa.tf").write_text('resource "aws_iam_virtual_mfa_device" "admin" {}\n')
            unknown = self.gate(repo)
            self.assertNotEqual(unknown.returncode, 0)
            self.assertIn("aws_iam_virtual_mfa_device.admin is an IAM type this gate has no row for", unknown.stdout)

    def test_a_target_with_no_such_gate_is_given_none(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "shop", profile="standard", target="azure")
            self.assertNotIn("check-deploy-role", (repo / "Makefile").read_text())
            self.assertFalse((repo / "scripts/check-deploy-role.py").exists())

    def test_an_apply_refused_on_an_iam_action_names_make_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "shop", profile="standard", target="aws")
            fake = Path(directory) / "bin"
            fake.mkdir()
            (fake / "tofu").write_text(FAKE_TOFU)
            (fake / "tofu").chmod(0o755)
            specification = importlib.util.spec_from_file_location("deploy_role_deploy", repo / "scripts/deploy.py")
            assert specification is not None and specification.loader is not None
            module: Any = importlib.util.module_from_spec(specification)
            specification.loader.exec_module(module)
            path = os.environ["PATH"]
            os.environ["PATH"] = f"{fake}{os.pathsep}{path}"
            try:
                with open(os.devnull, "w") as quiet, self.assertRaises(module.Failure) as raised:
                    module.sys.stderr = quiet
                    module.apply("staging", {})
            finally:
                os.environ["PATH"] = path
                module.sys.stderr = module.sys.__stderr__
            said = str(raised.exception)
            self.assertIn("refused iam:CreateUser, which the deploy role is not granted", said)
            self.assertIn("infra/bootstrap/main.tf", said)
            self.assertIn("run `make bootstrap`", said)
