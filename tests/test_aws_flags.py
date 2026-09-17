"""Feature flags on the `aws` target: the one change to a running environment that costs no deploy.

The apply is unprovable here as everywhere else on this target. What is proved is the shape the apply would
have: that a flag reaches the container as an ordinary environment variable — so no image in any of the five
backends gains an AWS SDK — that the stack stops managing the value once it has seeded it, and that flipping
one is a verb needing no build and no apply.

The second half of the file is the browser's, and it exists because of a defect downstream: a flag turned on
in staging moved the service and left the browser app rendering its holding page for ever, because nothing in
the delivery path ever set a `VITE_FLAG_*`. A browser flag cannot be live — Vite inlines it while the bundle
is built — so what is proved is the honest contract instead: the bundle is built with what this environment's
parameters are *set to* at deploy time, one product flag is spelled the same way in the stack, the deploy and
the app, and everything says which half is a restart and which is a redeploy.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from support import FactoryTestCase

from slipwai.assets import ROOT
from slipwai.catalog import axis_default

# What the `flags` output looks like once an environment exists, with two flags on the service the site's
# `/api` goes to and one on a service beside it.
PARAMETERS = {
    "service/publish-table": "/flagged/staging/service/flags/publish-table",
    "service/checkout-v2": "/flagged/staging/service/flags/checkout-v2",
    "billing/dunning": "/flagged/staging/billing/flags/dunning",
}
LIVE = {
    PARAMETERS["service/publish-table"]: "on",
    PARAMETERS["service/checkout-v2"]: "off",
    PARAMETERS["billing/dunning"]: "on",
}


def deploy_script(repo: Path, values: dict[str, str]) -> tuple[Any, list[tuple[list[str], dict]]]:
    """A generated project's `scripts/deploy.py`, imported, with every command recorded rather than run and
    the parameter store answering out of `values`.

    Imported from the project so its own `ROOT` is that project: `web_app()` then reads that project's
    `project.json`, which is where the service behind the site is named.
    """
    specification = importlib.util.spec_from_file_location(f"flags_{repo.name}", repo / "scripts/deploy.py")
    assert specification is not None and specification.loader is not None
    module: Any = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    recorded: list[tuple[list[str], dict]] = []

    def record(command: list[str], **kwargs: object) -> str:
        recorded.append((command, dict(kwargs)))
        if command[:4] == ["aws", "ssm", "get-parameters", "--names"]:
            names = command[4:command.index("--output")]
            found = [{"Name": name, "Value": values[name]} for name in names if name in values]
            return json.dumps({"Parameters": found})
        return ""

    module.run = record
    # `npm` belongs to the deploy runner's PATH, not to this one's; what it is asked to do is the subject.
    module.which = lambda tool: None
    return module, recorded


def outputs(*, web_environment: dict[str, str] | None = None) -> dict:
    found: dict = {
        "web_bucket": "site-bucket",
        # What a flip smokes when it has waited for the deployment it forced: the environment's public
        # address, which is the site's where there is one — the same output a deploy smokes.
        "url": "https://flagged.example.invalid",
        "flags": {
            "cluster": "flagged-staging",
            "services": {"service": "flagged-staging-service", "billing": "flagged-staging-billing"},
            "parameters": dict(PARAMETERS),
        },
    }
    if web_environment is not None:
        found["web_environment"] = web_environment
    return found


def site_build(recorded: list[tuple[list[str], dict]]) -> dict[str, str]:
    """The environment the site's own build was given — the only place a `VITE_*` value can reach a bundle."""
    for command, kwargs in recorded:
        if command[:2] == ["npm", "--workspace"] and command[2].startswith("apps/") and command[-1] == "build":
            return dict(kwargs["env"])
    raise AssertionError(f"the site was never built: {[' '.join(c) for c, _ in recorded]}")


class AwsFlagsTest(FactoryTestCase):
    def generate_aws(self, directory: str, name: str, backend: str = "typescript"):
        return self.generate(
            directory, name, "event-modelling", backend, "react-vite", target="aws",
            event_store="postgres", http=axis_default("http", backend, "aws"),
        )

    def test_a_flag_is_declared_where_a_project_owns_it_and_reaches_the_container_as_a_variable(self) -> None:
        """The whole point of the shape: a flag costs the *application* nothing. It arrives as an ordinary
        environment variable resolved by ECS, so the adapter reading it is the one a project already has and
        no image gains an AWS SDK — which is what makes this affordable across five backends at once."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "flagged")

            seeds = (repo / "infra/service/flags.auto.tfvars").read_text()
            self.assertIn("flags = {", seeds)
            # Ships empty: a project declares its first flag in the change that adds the code reading it,
            # and until then `has_flags` is false and no parameter, policy or grant exists at all.
            self.assertNotRegex(seeds, r"(?m)^[ \t]+[a-z][a-z0-9-]* = \{")

            stack = (repo / "infra/service/flags.tf").read_text()
            self.assertIn("ignore_changes = [value]", stack)
            self.assertIn('"FLAG_${upper(replace(flag.key, "-", "_"))}"', stack)
            self.assertIn('actions   = ["ssm:GetParameters"]', stack)
            # Under `ssm` the execution role reads the parameters when it starts the task, and the task
            # role — the application's own — is untouched. Under `appconfig` the agent runs inside the task
            # and uses the task role, so choosing that transport is also choosing to give the application
            # its first AWS permission. Both are here; which one an environment gets is `flag_transport`.
            self.assertIn("role   = aws_iam_role.execution.id", stack)
            self.assertIn("count = local.has_flags && local.use_ssm ? 1 : 0", stack)
            self.assertIn("role   = aws_iam_role.task.id", stack)
            self.assertIn("count = local.has_flags && local.use_appconfig ? 1 : 0", stack)

            main = (repo / "infra/service/main.tf").read_text()
            self.assertIn("merge(local.service_secrets[each.key], local.service_flags[each.key])", main)
            self.assertIn("aws_iam_role_policy.execution_flags,", main)

    def test_flipping_a_flag_is_a_verb_that_needs_no_build_and_no_apply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "flippable")

            makefile = (repo / "Makefile").read_text()
            self.assertIn("\nSERVICE ?= service\n", makefile)
            self.assertIn("python3 scripts/deploy.py flag $(ENV) $(SERVICE) $(KEY) $(VALUE)", makefile)
            self.assertIn("python3 scripts/deploy.py flags $(ENV)", makefile)

            deploy = (repo / "scripts/deploy.py").read_text()
            self.assertIn('"flag": flag,', deploy)
            self.assertIn('"flags": lambda arguments: flags(*arguments),', deploy)
            # Write the parameter, then replace the tasks holding the old value: a flag reaches a running
            # environment through a restart, not a rebuild.
            self.assertIn('"aws", "ssm", "put-parameter"', deploy)
            self.assertIn('"--force-new-deployment"', deploy)
            self.assertNotIn("images_of", deploy.split("def flag(")[1].split("def flags(")[0])

    def test_a_project_with_two_services_names_the_one_a_flag_belongs_to(self) -> None:
        """A default `SERVICE` is only defensible when there is one; with two, the help text says so rather
        than the Makefile picking."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "two-flagged")
            subprocess.run(
                [str(ROOT / "slipwai"), "add-service", "billing", "--purpose", "Invoices."],
                cwd=repo, check=True, capture_output=True,
            )

            makefile = (repo / "Makefile").read_text()
            self.assertNotIn("\nSERVICE ?= ", makefile)
            self.assertIn("make flag ENV=production SERVICE=", makefile)

    def test_the_browser_bundle_is_built_with_no_flag_values_at_all(self) -> None:
        """The bundle used to be built with `VITE_FLAG_*` taken from this environment's parameters, which
        gave one product flag two clocks: the service's moved in a restart, the browser's only on the next
        deploy. The browser asks the service now, so nothing about a flag is baked into a build — and what
        an apply decided about the environment still is."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "flagged-web")
            module, recorded = deploy_script(repo, LIVE)
            found = outputs(web_environment={"VITE_USERS_ISSUER": "https://issuer", "VITE_USERS_CLIENT_ID": "cid"})

            module.upload_site(found, "abc123", module.site_environment(found))

            built = site_build(recorded)
            self.assertEqual(built["VITE_USERS_ISSUER"], "https://issuer")
            self.assertEqual([name for name in built if name.startswith("VITE_FLAG_")], [])
            # And the deploy no longer reads a parameter to build the site, so a parameter removed out of
            # band cannot turn a declared flag silently off at build time — there is nothing to inline.
            self.assertNotIn("site_flags", (repo / "scripts/deploy.py").read_text())

    def test_the_browser_asks_the_service_for_its_flags(self) -> None:
        """One product flag, one value, one source of truth: the service that enforces the flag is the one
        that answers for it, over the same `/api` the bundle already calls."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "flag-asked")

            helper = (repo / "apps/web/src/flags.ts").read_text()
            self.assertIn("'/api/flags'", helper)
            # No variable is derived on this side any more: there is no build-time value to name.
            self.assertNotIn("VITE_FLAG_", helper)
            # Only `on` is on, and a request that failed is off — the direction that hides a feature rather
            # than offering a customer something the endpoint will refuse.
            self.assertIn("=== 'on'", helper)
            self.assertIn("noFlags", helper)
            # The service's half: the route the bundle calls, and the snapshot it answers with.
            self.assertIn("/api/flags", (repo / "apps/service/src/adapters/driving/http/app.ts").read_text())

    def test_one_flag_is_spelled_the_same_way_in_the_stack_and_in_the_service(self) -> None:
        """Two files derive a variable name from one key, and a flag arrives only if both agree. The browser
        is no longer a third: it asks by key and never spells a variable."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "flag-spelling")

            self.assertIn(
                '"FLAG_${upper(replace(flag.key, "-", "_"))}"', (repo / "infra/service/flags.tf").read_text()
            )
            reader = (repo / "apps/service/src/flags.ts").read_text()
            self.assertIn("`${PREFIX}${key.toUpperCase().replace(/-/g, '_')}`", reader)
            self.assertIn("=== 'on'", reader)

    def test_flipping_a_flag_the_browser_reads_says_no_deploy_is_owed(self) -> None:
        """Both halves move on the one restart now, and that is worth saying at the moment of the flip:
        anybody who has flipped a flag on this stack before will expect to owe the browser a deploy."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "flagged-said")
            module, recorded = deploy_script(repo, LIVE)
            module.flag_state = lambda environment: outputs()
            # The environment's own address is asked the question a deploy asks it, and the answer comes
            # over the network — which this suite has no business reaching. What it is *given* is the
            # subject, so `smoke` is recorded rather than run.
            smoked: list[str] = []
            module.smoke = smoked.append

            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                module.flag(["staging", "service", "publish-table", "on"])
            said = printed.getvalue()

            self.assertIn("apps/web", said)
            self.assertIn("No deploy is owed", said)
            # The instruction that used to be here, and would now be wrong.
            self.assertNotIn("make deploy ENV=staging", said)
            # A flip forces a deployment either way, so it waits for it and then proves the environment
            # still answers: the one piece of evidence available for a change no pipeline saw.
            commands = [" ".join(command) for command, _ in recorded]
            self.assertIn(
                "aws ecs wait services-stable --cluster flagged-staging --services flagged-staging-service",
                commands,
            )
            self.assertEqual(smoked, ["https://flagged.example.invalid"])

            # And says nothing of the sort about a flag no bundle is built with.
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                module.flag(["staging", "billing", "dunning", "on"])
            self.assertNotIn("apps/web", printed.getvalue())

    def test_a_rollback_returns_the_bundle_that_ran_rather_than_rebuilding_it(self) -> None:
        """Which is the other direction the two halves diverge in, and it is worth being sure of: the
        browser's flags go back to the rolled-back release's, while the parameter — and so the service —
        keeps the value it has now. `flags.tf` says so; this is that it is true."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "flagged-back")
            module, recorded = deploy_script(repo, LIVE)

            module.restore_site(outputs(), "earlier")

            commands = [" ".join(command) for command, _ in recorded]
            self.assertEqual(len(commands), 1, commands)
            self.assertIn("s3://site-bucket/releases/earlier/index.html", commands[0])
            self.assertNotIn("npm", commands[0])

    def test_the_flag_policy_says_which_half_is_a_switch_and_which_is_a_build(self) -> None:
        """The rule an author needs before writing the first gate, in the file they are held to — and, for a
        project with no browser app, the browser half absent rather than there to be filtered out."""
        with tempfile.TemporaryDirectory() as directory:
            guidance = (self.generate_aws(directory, "flag-policy") / "AGENTS.md").read_text()
            self.assertIn("`FLAG_<KEY>`", guidance)
            self.assertIn("`VITE_FLAG_<KEY>`", guidance)
            self.assertIn("flagEnabled('checkout-v2')", guidance)
            self.assertIn("apps/web/src/flags.ts", guidance)
            self.assertIn("make flag ENV=… KEY=… VALUE=on", guidance)
            # The failure the contract admits, and which way round to move so it stays harmless.
            self.assertIn("an inviting UI whose every call", guidance)

            service_only = self.generate(
                directory, "flag-policy-headless", "event-modelling", "typescript", "none", target="aws",
                event_store="postgres", http=axis_default("http", "typescript", "aws"),
            )
            headless = (service_only / "AGENTS.md").read_text()
            self.assertIn("`FLAG_<KEY>`", headless)
            self.assertNotIn("VITE_FLAG", headless)

    def test_a_declared_flag_validates_against_the_real_provider(self) -> None:
        """The empty file every project ships means `aws_ssm_parameter.flag` has no instances, so the stack
        validating says nothing about the expressions that build one. This declares a flag and validates
        again: the flattening `merge(...)` does, the `for_each` over it, and the environment variable name
        derived from the key are all only exercised with something in the map."""
        if shutil.which("tofu") is None:
            self.skipTest("tofu is not installed; the factory's CI installs it")
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "flag-declared")
            # What a project does to the file it was shipped: fill in the map that is already there.
            seeds = repo / "infra/service/flags.auto.tfvars"
            declared = seeds.read_text().replace(
                '''flags = {
  # api = {
  #   checkout-v2 = "off"
  # }
}''',
                '''flags = {
  service = {
    checkout-v2 = "off"
  }
}''',
            )
            self.assertIn("service = {", declared)
            seeds.write_text(declared)
            stack = repo / "infra/service"

            for arguments in (
                ("init", "-backend=false", "-input=false"),
                ("fmt", "-check", "-recursive", "."),
                ("validate",),
            ):
                done = subprocess.run(["tofu", *arguments], cwd=stack, text=True, capture_output=True)
                self.assertEqual(done.returncode, 0, f"tofu {arguments[0]}: {done.stderr or done.stdout}")
