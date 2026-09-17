"""The service stack an `aws` project is given, read as HCL and held to the real provider.

The apply itself ends in somebody's account and is unprovable here. What is proved instead: what the stack
says about how a release reaches production and how it is undone, the apply-time decisions `tofu validate`
cannot see, and that every variant this factory writes — maximal, minimal, and maximal pruned to minimal —
validates against the pinned AWS provider.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.catalog import axis_default


def tofu(*arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["tofu", *arguments], cwd=cwd, text=True, capture_output=True)


class AwsStackTest(FactoryTestCase):
    def generate_aws(
        self, directory: str, name: str, backend: str = "typescript", frontend: str = "react-vite", **axes
    ):
        return self.generate(
            directory, name, "event-modelling", backend, frontend, target="aws",
            event_store=axes.pop("event_store", "postgres"), http=axis_default("http", backend, "aws"),
            **axes,
        )

    def validate(self, stack: Path) -> None:
        init = tofu("init", "-backend=false", "-input=false", cwd=stack)
        self.assertEqual(init.returncode, 0, init.stderr)
        formatted = tofu("fmt", "-check", "-recursive", ".", cwd=stack)
        self.assertEqual(formatted.returncode, 0, f"not formatted: {formatted.stdout}")
        valid = tofu("validate", cwd=stack)
        self.assertEqual(valid.returncode, 0, valid.stderr)

    def test_the_stack_deploys_blue_green_and_decides_its_counts_from_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "shipped", auth="cognito", users="cognito")
            # `count` must be knowable at plan time, and `secret_arns` is not: its ARNs are created in the
            # same apply, so deciding the count from it fails every first apply into a fresh environment —
            # a failure `tofu validate` cannot see. The count reads `has_secrets`, decided from `var.services`.
            stack = (repo / "infra/service/main.tf").read_text()
            self.assertNotIn("count = length(local.secret_arns)", stack)
            self.assertEqual(stack.count("count = local.has_secrets ? 1 : 0"), 2)
            # Fargate rejects an awslogs configuration without a stream prefix — another apply-time failure
            # `tofu validate` cannot see, because the provider schema leaves the option optional.
            self.assertIn('"awslogs-stream-prefix" = each.key', stack)
            # A buildpack image's entrypoint starts the web process whatever `command` it is given, so the
            # migrate task points the entrypoint at the buildpack launcher wherever it gives a command — a
            # run-time failure, not an apply-time one: the task serves instead of migrating and never exits.
            migrate = (repo / "infra/service/rds.tf").read_text()
            self.assertIn(
                'entryPoint = ["/cnb/lifecycle/launcher"]\n        command    = each.value.migrate_command', migrate
            )
            # Blue/green, native to ECS: two target groups and the listener rule ECS repoints between them,
            # the previous revision kept for the bake time, and the provider's re-sent load-balancer block
            # (#45678) ignored so that successive deploys alternate. The site fronts the balancer over HTTP;
            # HTTPS is CloudFront's, per service and for the site.
            self.assertIn('strategy             = "BLUE_GREEN"', stack)
            self.assertIn("bake_time_in_minutes = var.bake_minutes", stack)
            self.assertIn("sigint_rollback       = true", stack)
            ingress = (repo / "infra/service/ingress.tf").read_text()
            for said in ('"aws_lb_target_group" "blue"', '"aws_lb_target_group" "green"', "ignore_changes = [action]",
                         '"aws_cloudfront_distribution" "service"', 'origin_protocol_policy = "http-only"'):
                self.assertIn(said, ingress)
            self.assertIn("bake_minutes = 5", (repo / "infra/service/production.tfvars").read_text())
            # The infrastructure role's managed policy lives at the policy root, not under `service-role/`
            # where ECS's other managed policies are; the wrong path is a 404 at apply, not a validate error.
            self.assertIn(
                'policy_arn = "arn:aws:iam::aws:policy/AmazonECSInfrastructureRolePolicyForLoadBalancers"', stack
            )
            # EC2 rejects a security group description outside its character set — an apostrophe in a
            # sentence is enough — and the provider schema does not know the set. Every group, every file.
            allowed = re.compile(r"^[a-zA-Z0-9. _\-:/()#,@\[\]+=&;{}!$*]{1,255}$")
            groups = re.compile(r'resource "aws_security_group" "[^"]+" \{.*?\n\}', re.DOTALL)
            described = re.compile(r'^\s*description\s*=\s*"([^"]*)"', re.MULTILINE)
            descriptions = [
                (path.name, text)
                for path in sorted((repo / "infra/service").glob("*.tf"))
                for group in groups.findall(path.read_text())
                for text in described.findall(group)
            ]
            self.assertEqual(len(descriptions), 3, descriptions)
            for file, text in descriptions:
                with self.subTest(file=file, description=text):
                    self.assertRegex(text, allowed)
            frontend = (repo / "infra/service/frontend.tf").read_text()
            self.assertIn("api_origin = local.service_origins[var.web.api]", frontend)
            # The app's routes are rewritten to index.html by a function on the site's behaviour alone.
            # `custom_error_response` is the whole distribution's, so it would answer the service's
            # `404 {"error":"notFound"}` on `/api/*` with this page and a `200` — `make smoke` asks for that
            # 404 precisely because it proves `/api` reaches the service, and a bundle would parse HTML.
            self.assertNotIn("custom_error_response {", frontend)
            self.assertIn('resource "aws_cloudfront_function" "spa"', frontend)
            self.assertEqual(frontend.count("function_association"), 1)
            behaviours = re.compile(r"(default_cache_behavior|ordered_cache_behavior) \{.*?\n  \}", re.DOTALL)
            attached = {
                kind for kind, block in
                ((match.group(1), match.group(0)) for match in behaviours.finditer(frontend))
                if "aws_cloudfront_function.spa.arn" in block
            }
            self.assertEqual(attached, {"default_cache_behavior"})
            self.assertNotIn("express", (stack + ingress).lower())

    def test_every_stack_validates_against_the_real_provider_before_and_after_a_prune(self) -> None:
        if shutil.which("tofu") is None:
            self.skipTest("tofu is not installed; the factory's CI installs it")
        with tempfile.TemporaryDirectory() as directory:
            maximal = self.generate_aws(directory, "maximal", auth="cognito", users="cognito")
            minimal = self.generate_aws(directory, "minimal", "go", "none", event_store="memory")
            for repo in (maximal, minimal):
                for stack in ("bootstrap", "service"):
                    with self.subTest(project=repo.name, stack=stack):
                        self.validate(repo / "infra" / stack)
            # `./init --event-store memory --auth none --users none`, then the stack is still one stack.
            subprocess.run(
                [
                    "python3", "scripts/backing-services.py", "--event-store", "memory", "--auth", "none",
                    "--users", "none",
                ],
                cwd=maximal, check=True, capture_output=True,
            )
            self.assertEqual((maximal / "infra/service/rds.tf").read_text(), "")
            self.assertNotIn("backing-service:postgres", (maximal / "infra/service/main.tf").read_text())
            self.validate(maximal / "infra/service")
