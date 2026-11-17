"""A project pushed to a forge for the first time starts with a green trunk.

The owner's first fleet run pushed a project generated for Azure, event-modelling profile, and its trunk
was red from the first commit for three separate reasons, any one of which holds every merge — the
harbourmaster refuses to land anything while a run on trunk's head is not `success`, `skipped` or `neutral`.

1. The sign-in asked `secrets` in an `if:`, which GitHub refuses whole (fixed in the Azure target).
2. `event model` named `actions/upload-artifact@v3` on a step whose `if:` meant it never ran on GitHub. GitHub
   resolves every action a job names before any step runs, and fails the job for naming a refused version.
3. `deploy` ran on every push to `main` and failed at the cloud sign-in, because the repository had no
   variables yet: `make bootstrap` had not run, and could not, until the owner's cloud was ready.

Each is a property of the generated YAML, so these read the YAML every target, shape and profile produces.
What GitHub then does with it — that a run whose every job is skipped by `if:` concludes `skipped` — is the
forge's, and is the one thing here no test on this machine can show.
"""
from __future__ import annotations

import re
import unittest
from typing import Any
from unittest.mock import patch

import checkout_packages  # noqa: F401
import yaml  # type: ignore[import-untyped]

from slipwai.project import deploy_workflow
from slipwai.target_protocol import PIPELINE, Target, faults

TARGETS = ("none", "aws", "azure")
SHAPES = ("skiff", "liner")
PROFILES = ("standard", "event-modelling")
MANAGED = ("aws", "azure")

#: Action refs GitHub refuses at *Set up job*, before any step runs and whatever the step's `if:` says.
REFUSED = re.compile(r"uses:\s*actions/(?:upload|download)-artifact@v[123]\b")

#: Which contexts GitHub offers where, from its context-availability table. A workflow that reads any other
#: one in these places is refused whole, with no log — which is what the Azure sign-in did with `secrets`.
OFFERED = {
    "job if": {"github", "needs", "vars", "inputs"},
    "job name": {"github", "needs", "strategy", "matrix", "vars", "inputs"},
    "step if": {"github", "needs", "strategy", "matrix", "job", "runner", "env", "vars", "steps", "inputs"},
}
CONTEXT = re.compile(r"\b(github|needs|vars|secrets|env|steps|job|jobs|runner|matrix|strategy|inputs)\s*\.")
#: The toy language's own command lines are `echo 'toy: …'` and `@echo …`, which are fine to a Makefile and
#: not to a YAML parser. They exist only in the in-tree fixture; a real language answers real commands.
TOY = re.compile(r"run: @?echo 'toy: [^']*'")


def toolchain_free() -> Any:
    """The fixture names a fake image tool; only its CI installer is left out, as `test_deployment_shapes`."""
    return patch.dict(deploy_workflow.TOOL_SETUPS, {"toy": ""})


def apps() -> list:
    from slipwai.selection import Selection
    from slipwai.services import App
    return [App(name="service", path="apps/service", kind="service", language="toy", framework="plain",
                port=8080, selection=Selection({"write-model": "events", "persistence": "postgres",
                                               "http": "toy-serve"}))]


def workflows(targets: tuple[str, ...] = TARGETS) -> dict[tuple[str, str, str, str], str]:
    """Every workflow every combination generates, keyed by (target, shape, profile, path)."""
    from slipwai.scaffold import project_files
    found: dict[tuple[str, str, str, str], str] = {}
    with toolchain_free():
        for target in targets:
            for shape in SHAPES:
                for profile in PROFILES:
                    files = project_files("a-staff-tool", profile, target, apps(), shape=shape)
                    found |= {(target, shape, profile, name): text for name, text in files.items()
                              if name.startswith(".github/workflows/") and isinstance(text, str)}
    return found


def parsed(text: str) -> dict:
    return yaml.safe_load(TOY.sub("run: echo toy", text))


def contexts(expression: object) -> set[str]:
    """The contexts an expression reads, with its string literals taken out first — `'https://github.com'`
    is a URL, not the `github` context."""
    return set(CONTEXT.findall(re.sub(r"'[^']*'", "''", str(expression))))


def asked_where_not_offered(workflow: dict) -> list[str]:
    """Every job and step condition, and job name, that reads a context GitHub does not offer there."""
    found = []
    for job_id, job in (workflow.get("jobs") or {}).items():
        for place, value in (("job if", job.get("if")), ("job name", job.get("name"))):
            if value is not None and (extra := contexts(value) - OFFERED[place]):
                found.append(f"{job_id} {place} reads {sorted(extra)}")
        for index, step in enumerate(job.get("steps") or []):
            if "if" in step and (extra := contexts(step["if"]) - OFFERED["step if"]):
                found.append(f"{job_id} step {index} if reads {sorted(extra)}")
    return found


class EveryWorkflowStartsTest(unittest.TestCase):
    flows: dict[tuple[str, str, str, str], str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.flows = workflows()

    def test_every_generated_workflow_is_yaml(self) -> None:
        for key, text in self.flows.items():
            with self.subTest(workflow=key):
                self.assertIsInstance(parsed(text), dict)

    def test_no_generated_workflow_names_an_action_ref_github_refuses(self) -> None:
        """Fault 2. A refused ref fails its job at *Set up job*, so an `if:` that skips its step is no guard."""
        self.assertTrue(any(name.endswith("event-model.yml") for (_, _, _, name) in self.flows))
        for key, text in self.flows.items():
            with self.subTest(workflow=key):
                self.assertEqual(REFUSED.findall(text), [])

    def test_the_table_refuses_what_it_should(self) -> None:
        """Fault 1 is held by `test_deployment_shapes` with `asked_where_not_offered`, over every workflow
        here. That passing on nothing would prove nothing, so the check is shown the shapes that were red."""
        workflow = {"jobs": {"deploy": {"if": "vars.A != '' && secrets.B != ''", "steps": [
            {"if": "${{ secrets.AZURE_CLIENT_SECRET == '' }}"}, {"if": "github.server_url == 'https://x'"}]}}}
        self.assertEqual(asked_where_not_offered(workflow),
                         ["deploy job if reads ['secrets']", "deploy step 0 if reads ['secrets']"])


class DeployWaitsForTheCloudTest(unittest.TestCase):
    """Fault 3. Until `make bootstrap` writes the target's variables, every deploy pipeline is skipped whole."""

    flows: dict[tuple[str, str, str, str], str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.flows = workflows(MANAGED)

    def test_each_target_names_the_variable_its_pipeline_waits_for(self) -> None:
        for target, variable in (("aws", "AWS_DEPLOY_ROLE_ARN"), ("azure", "AZURE_CLIENT_ID")):
            with self.subTest(target=target):
                self.assertEqual(deploy_workflow.pipeline(target).get("configured"), variable)

    def test_every_job_of_every_deploy_pipeline_waits_for_that_variable(self) -> None:
        """The first job asks; every other job needs it, so a skipped first job skips the run."""
        for (target, shape, profile, name), text in self.flows.items():
            if name.rsplit("/", 1)[-1] not in ("deploy.yml", "production.yml", "rollback.yml"):
                continue
            ready = f"vars.{deploy_workflow.pipeline(target)['configured']} != ''"
            jobs = parsed(text)["jobs"]
            with self.subTest(target=target, shape=shape, profile=profile, workflow=name):
                waiting = {job_id for job_id, job in jobs.items() if ready in str(job.get("if", ""))}
                self.assertEqual(len(waiting), 1, jobs.keys())
                for job_id in jobs:
                    if job_id not in waiting:
                        self.assertTrue(self.depends(jobs, job_id, waiting), f"{job_id} would run anyway")
                for job_id in waiting:
                    self.assertIn("skipped until make bootstrap sets", jobs[job_id]["name"])
                    self.assertIn(ready, jobs[job_id]["name"])

    @staticmethod
    def depends(jobs: dict, job_id: str, on: set[str]) -> bool:
        needs = jobs[job_id].get("needs") or []
        needs = [needs] if isinstance(needs, str) else needs
        return any(need in on or DeployWaitsForTheCloudTest.depends(jobs, need, on) for need in needs)

    def test_the_deploy_still_waits_for_verify_too(self) -> None:
        for (target, _, _, name), text in self.flows.items():
            if name.endswith("/deploy.yml"):
                build = parsed(text)["jobs"]["build"]["if"]
                self.assertIn(deploy_workflow.pipeline(target)["configured"], build)
                self.assertTrue(build.startswith("github.event.workflow_run.conclusion == 'success' && "), build)

    def test_a_target_that_names_no_variable_gets_the_workflows_it_always_had(self) -> None:
        """The protocol addition is optional: without the key, not a byte of these workflows changes."""
        real = deploy_workflow.pipeline

        def without(target: str) -> dict[str, str]:
            return {key: value for key, value in real(target).items() if key != "configured"}

        with toolchain_free(), patch.object(deploy_workflow, "pipeline", without):
            deploy = deploy_workflow.deploy_workflow(apps(), "azure", False, "liner")
            rollback = deploy_workflow.rollback_workflow("azure", False, "liner")
            promotion = deploy_workflow.promotion_workflow(False, "azure", False)
        self.assertIn("jobs:\n  build:\n    if: github.event.workflow_run.conclusion == 'success'\n"
                      "    runs-on: ubuntu-latest\n", deploy)
        self.assertIn("jobs:\n  rollback:\n    runs-on: ubuntu-latest\n", rollback)
        self.assertIn("jobs:\n  promote:\n    runs-on: ubuntu-latest\n", promotion)
        for text in (deploy, rollback, promotion):
            self.assertNotIn("make bootstrap sets", text)

    def test_the_readme_says_deploys_are_skipped_until_the_bootstrap(self) -> None:
        from slipwai.project.target_docs import production_readme
        for target in MANAGED:
            for shape in SHAPES:
                with self.subTest(target=target, shape=shape):
                    readme = production_readme(target, apps(), [], shape)
                    self.assertIn("Until `make bootstrap` has run, every deploy is skipped rather than failed",
                                  readme)
                    self.assertIn(deploy_workflow.pipeline(target)["configured"], readme)


class ProtocolTest(unittest.TestCase):
    """`configured` is an optional key of `pipeline`: absent is fine, present is a variable's name."""

    PARTS = {"cli": "", "credentials": "", "build_cli": "", "registry_login": "", "environment": ""}

    def faults_of(self, pipeline: dict) -> list[str]:
        return faults(Target(name="somewhere", answers={PIPELINE: pipeline}), managed=False)

    def test_a_pipeline_without_it_is_whole(self) -> None:
        self.assertEqual(self.faults_of(dict(self.PARTS)), [])

    def test_a_pipeline_with_a_variable_name_is_whole(self) -> None:
        self.assertEqual(self.faults_of({**self.PARTS, "configured": "AZURE_CLIENT_ID"}), [])

    def test_anything_else_is_refused_with_what_it_should_be(self) -> None:
        for wrong in ("vars.AZURE_CLIENT_ID", "", "azure client", 3):
            with self.subTest(configured=wrong):
                found = self.faults_of({**self.PARTS, "configured": wrong})
                self.assertEqual(len(found), 1, found)
                self.assertIn("repository variable", found[0])


if __name__ == "__main__":
    unittest.main()
