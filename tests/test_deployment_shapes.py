"""Deployment choices preserve data-holding projects while new staff tools start small.

Real generated-project/provider proofs live here too, so the suite belongs to SLOW from its first commit.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.deployment_shapes import recorded, selected
from slipwai.errors import GenerationError


class ChoiceTest(unittest.TestCase):
    def test_an_old_slipway_manifest_never_silently_changes_its_deployed_shape(self) -> None:
        self.assertEqual(recorded({"target": "a-managed-target", "state": "slipway"}), "liner")
        self.assertEqual(recorded({"target": "a-managed-target", "shape": "skiff"}), "skiff")

    def test_new_staff_tools_start_small_and_real_products_keep_the_full_stack(self) -> None:
        self.assertEqual(selected(None, "slipway"), "skiff")
        self.assertEqual(selected(None, "in-service"), "liner")
        self.assertEqual(selected("liner", "slipway"), "liner")
        self.assertEqual(selected("skiff", "in-service"), "skiff")

    def test_an_unknown_recorded_shape_is_refused_with_a_repair(self) -> None:
        with self.assertRaisesRegex(GenerationError, "use --shape skiff or --shape liner"):
            recorded({"shape": "future-shape"})


class GeneratedShapeTest(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch

        from slipwai.project.deploy_workflow import TOOL_SETUPS
        # The local-only fixture names a fake image tool. Only its CI installer is omitted here; the
        # complete factory, package rows and manifest readers still execute. Real TS provider proof is separate.
        installer = patch.dict(TOOL_SETUPS, {"toy": ""})
        installer.start()
        self.addCleanup(installer.stop)

    def apps(self):
        from slipwai.selection import Selection
        from slipwai.services import App
        return [App(name="service", path="apps/service", kind="service", language="toy", framework="plain",
                    port=8080, selection=Selection({"write-model": "events", "persistence": "postgres",
                                                   "http": "toy-serve"}))]

    def test_new_managed_projects_default_small_but_an_explicit_liner_keeps_staging(self) -> None:
        import json

        from slipwai.scaffold import project_files
        for target in ("aws", "azure"):
            with self.subTest(target=target):
                skiff = project_files("a-staff-tool", "event-modelling", target, self.apps())
                self.assertEqual(json.loads(skiff["project.json"])["shape"], "skiff")
                workflow = skiff[".github/workflows/deploy.yml"]
                self.assertNotIn("\n  staging:", workflow)
                self.assertIn("\n  production:", workflow)
                self.assertNotIn(".github/workflows/production.yml", skiff)
                self.assertNotIn("infra/service/staging.tfvars", skiff)
                self.assertIn("ENV ?= production", skiff["Makefile"])
                liner = project_files("a-staff-tool", "event-modelling", target, self.apps(), shape="liner")
                self.assertIn("\n  staging:", liner[".github/workflows/deploy.yml"])
                self.assertIn("infra/service/staging.tfvars", liner)
                self.assertIn(".github/workflows/production.yml", liner)

    def test_a_shape_that_migrates_from_its_deploy_job_signs_that_job_in_to_the_registry(self) -> None:
        """`registry_at_deploy`, and the two halves of it that matter.

        A liner applies and lets a task the stack declares pull the migration image with the platform's own
        credentials, so the registry sign-in belongs to its build job and its deploy jobs never ask for it.
        AWS's skiff has no such task — Lightsail has no one-off job — so `scripts/skiff_migrations.py`
        builds a bounded wrapper over the immutable image and pushes it from inside `make deploy`; without
        the login in that job every deploy of a TypeScript+Postgres skiff ended in `no basic auth
        credentials`. Azure's skiff keeps the liner's Container App migrate job, so its deploy job must
        *not* be given a sign-in it never uses: a step that does nothing reads as configuration.
        """
        from slipwai.project.deploy_workflow import pipeline
        from slipwai.scaffold import project_files
        for target, at_deploy in (("aws", True), ("azure", False)):
            with self.subTest(target=target):
                login = pipeline(target)["registry_login"].strip()
                self.assertTrue(login)
                skiff = project_files("a-staff-tool", "event-modelling", target, self.apps())
                workflow = skiff[".github/workflows/deploy.yml"]
                self.assertIn(login, workflow.split("\n  build:", 1)[1].split("\n  production:", 1)[0])
                deploying = workflow.split("\n  production:", 1)[1]
                self.assertEqual(login in deploying, at_deploy)
                # And the liner is left exactly as it was: its deploy jobs apply and smoke, nothing else.
                liner = project_files("a-staff-tool", "event-modelling", target, self.apps(), shape="liner")
                self.assertNotIn(login, liner[".github/workflows/deploy.yml"].split("\n  staging:", 1)[1])

    def test_each_direction_warns_about_the_shape_it_is_being_asked_to_leave(self) -> None:
        """A package's `transition` is written as "how to leave this shape", so the direction decides whose.

        The decisive one is the skiff's: a private Lightsail database cannot be reached from ECS, so
        skiff → liner is an export/import and a verified cutover, not a DNS change. Printing the
        destination's row meant the one path this slice exists for never showed that warning at all, and
        the other direction told an operator leaving RDS to import *into* RDS.
        """
        import tempfile
        from pathlib import Path as _Path

        from slipwai.deployment_shapes import row
        from slipwai.scaffold import project_files
        from slipwai.shape_converge import check, prepare
        for current, requested in (("skiff", "liner"), ("liner", "skiff")):
            with self.subTest(leaving=current), tempfile.TemporaryDirectory() as directory:
                root = _Path(directory)
                generated = project_files("a-staff-tool", "event-modelling", "aws", self.apps(),
                                          shape=current)
                (root / "project.json").write_text(generated["project.json"], encoding="utf-8")
                leaving, arriving = row("aws", current) or {}, row("aws", requested) or {}
                self.assertTrue(leaving and arriving)
                self.assertNotEqual(leaving["transition"], arriving["transition"])
                said = check(root, requested)
                self.assertIn(f"{current} \u2192 {requested}", said)
                self.assertIn(leaving["transition"], said)
                self.assertNotIn(arriving["transition"], said)
                written = (prepare(root, requested) / "RUNBOOK.md").read_text(encoding="utf-8")
                self.assertIn(leaving["transition"], written)
                self.assertNotIn(arriving["transition"], written)

    def test_prepare_preserves_original_database_state_and_manifest_and_runs_no_cloud_commands(self) -> None:
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from slipwai.scaffold import project_files
        from slipwai.shape_converge import check, prepare
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generated = project_files("a-staff-tool", "event-modelling", "aws", self.apps())
            for name in ("project.json", "infra/service/versions.tf", "infra/service/database.tf", "Makefile"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(generated[name], encoding="utf-8")
            state = root / "infra/service/terraform.tfstate"
            state.write_bytes(b'{"serial":42,"resources":[{"name":"database","data":"preserve"}]}')
            before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
            with patch(
                "subprocess.run", side_effect=AssertionError("preparation must not execute cloud or git commands"),
            ):
                self.assertIn("No infrastructure is applied", check(root, "liner"))
                self.assertEqual({path: path.read_bytes() for path in root.rglob("*") if path.is_file()}, before)
                proposal = prepare(root, "liner")
            for path, content in before.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertEqual(json.loads((root / "project.json").read_text())["shape"], "skiff")
            self.assertEqual(json.loads((proposal / "project.json").read_text())["shape"], "liner")
            descriptor = json.loads((proposal / "transition.json").read_text())
            self.assertFalse(descriptor["applied"])
            self.assertFalse(descriptor["cutoverConfirmed"])
            self.assertNotIn("terraform.tfstate", " ".join(descriptor["files"]))
            self.assertIn("export/import", (proposal / "RUNBOOK.md").read_text())
            with self.assertRaisesRegex(GenerationError, "already holds a proposal"):
                prepare(root, "liner")
            self.assertEqual(state.read_bytes(), before[state])
