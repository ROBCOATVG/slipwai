"""The three workflows an `aws` project is given, read as text: `deploy.yml`, which runs when `verify` has
passed on `main` and takes the commit through staging to production; `production.yml`, which promotes what
staging is running when a project deploys production by hand; and `rollback.yml`, which a person starts."""
from __future__ import annotations

import tempfile

from support import FactoryTestCase

from slipwai.catalog import axis_default


class AwsWorkflowsTest(FactoryTestCase):
    def test_deploy_follows_verify_and_rollback_is_started_by_hand(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "shipped", "event-modelling", "typescript", "none", target="aws",
                event_store="postgres", http=axis_default("http", "typescript", "aws"),
            )
            workflow = (repo / ".github/workflows/deploy.yml").read_text()
            self.assertIn("setup-pack", workflow)
            self.assertNotIn("setup-ko", workflow)
            self.assertIn("make deploy ENV=staging", workflow)
            self.assertIn("make deploy ENV=production", workflow)
            self.assertLess(workflow.index("ENV=staging"), workflow.index("ENV=production"))
            # The deploy follows `verify`, it does not race it: it is a `workflow_run` of that workflow on
            # main, goes on only when it passed, and every job checks out the commit it passed — not the
            # head of main, which a later push may have moved.
            self.assertNotIn("on:\n  push", workflow)
            for expected in (
                "workflow_run:", "workflows:\n      - verify", "types:\n      - completed",
                "branches:\n      - main", "if: github.event.workflow_run.conclusion == 'success'",
            ):
                self.assertIn(expected, workflow)
            self.assertEqual(workflow.count("ref: ${{ github.event.workflow_run.head_sha }}"), 3)
            self.assertLess(workflow.index("workflow_run.conclusion"), workflow.index("make build push"))
            self.assertIn("id-token: write", workflow)
            # One workflow for both forges: the OIDC token on GitHub, the key `make bootstrap` stored on a
            # forge without one — and nothing handed between jobs, so no artifact store is needed.
            self.assertIn("aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}", workflow)
            self.assertIn("role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}", workflow)
            self.assertNotIn("artifact", workflow)
            # A local runner's image (act's ubuntu-latest) ships no `aws` CLI, so every job that shells out
            # to it installs its own copy — the two deploy jobs, and not the build job, whose `make build
            # push` is docker-only. `--update` keeps it a no-op on GitHub's runners, which already have one.
            self.assertEqual(workflow.count("sudo ./aws/install --update"), 2)
            self.assertLess(workflow.index("make build push"), workflow.index("./aws/install"))
            # Rolling back is a person's decision, so it is its own workflow, started by hand, and it builds
            # nothing — no toolchain, no image builder — because the images it promotes already ran there.
            rollback = (repo / ".github/workflows/rollback.yml").read_text()
            for expected in (
                "workflow_dispatch:", "type: choice", "- staging\n          - production", "group: deploy",
                "environment: ${{ inputs.environment }}", "make rollback ENV=${{ inputs.environment }}",
                "make smoke URL=$(make -s url ENV=${{ inputs.environment }})", "role-to-assume:",
                "sudo ./aws/install --update",
            ):
                self.assertIn(expected, rollback)
            for absent in ("setup-pack", "setup-ko", "setup-node", "make build", "on:\n  push", "workflow_run"):
                self.assertNotIn(absent, rollback)

    def test_production_is_conditional_and_promotion_deploys_what_staging_runs(self) -> None:
        """A project pays for production when it decides to, not on its first green push. The production job
        carries one condition and `production.yml` is the other way in — the way in, where that condition
        holds the job back."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "shipped", "event-modelling", "typescript", "react-vite", target="aws",
                event_store="postgres", http=axis_default("http", "typescript", "aws"),
            )
            workflow = (repo / ".github/workflows/deploy.yml").read_text()
            # `!=`, not `== 'on'`: a repository bootstrapped before this variable existed has none, and
            # absent has to keep deploying production the way it always did.
            self.assertIn("if: vars.AUTO_PROMOTE != 'false'", workflow)
            self.assertNotIn("vars.AUTO_PROMOTE ==", workflow)
            # On the production job and nowhere else — staging deploys on every green push in both modes.
            self.assertEqual(workflow.count("vars.AUTO_PROMOTE"), 1)
            self.assertLess(workflow.index("ENV=staging"), workflow.index("vars.AUTO_PROMOTE"))
            self.assertLess(workflow.index("vars.AUTO_PROMOTE"), workflow.index("ENV=production"))

            promote = (repo / ".github/workflows/production.yml").read_text()
            for expected in (
                "name: production", "workflow_dispatch:", "group: deploy",
                "environment: production", "make deploy ENV=production",
                "make smoke URL=$(make -s url ENV=production)", "role-to-assume:", "sudo ./aws/install --update",
            ):
                self.assertIn(expected, promote)
            # It resolves the commit staging is running, then checks that commit out and deploys it — so the
            # order of those two is the whole guarantee, and the ref comes from the resolution.
            self.assertIn("scripts/deploy.py promoting staging", promote)
            self.assertIn("ref: ${{ steps.promoting.outputs.sha }}", promote)
            self.assertLess(promote.index("promoting staging"), promote.index("steps.promoting.outputs.sha"))
            self.assertLess(
                promote.index("steps.promoting.outputs.sha"), promote.index("- run: make deploy ENV=production")
            )
            # The dispatch input is free text, so it reaches the shell as a quoted environment variable
            # rather than interpolated into the command line.
            self.assertIn('COMMIT: ${{ inputs.commit }}', promote)
            self.assertIn('promoting staging "$COMMIT"', promote)
            self.assertNotIn("promoting staging ${{", promote)
            # Nothing is built: the images are the ones staging ran. Node is here only for the bundle,
            # which is not an image.
            for absent in ("setup-pack", "setup-ko", "make build", "make push", "workflow_run", "on:\n  push"):
                self.assertNotIn(absent, promote)
            self.assertIn("setup-node", promote)

    def test_a_project_with_no_browser_app_builds_no_bundle_when_it_promotes(self) -> None:
        """The one thing `production.yml` rebuilds is the site, because a bundle is not an image; a project
        with no site sets up no Node."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "headless", "event-modelling", "go", "none", target="aws",
                event_store="memory", http=axis_default("http", "go", "aws"),
            )
            promote = (repo / ".github/workflows/production.yml").read_text()
            self.assertNotIn("setup-node", promote)
            self.assertIn("make deploy ENV=production", promote)
