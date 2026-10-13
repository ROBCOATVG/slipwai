"""The keel reading a cloud it does not contain: every part that used to hold a row per target.

This is 10.3 and 10.4's acceptance, and it is here rather than in a generated project for a reason the suite
is honest about. The only language this checkout pins is the toy, which declares the `none` target and
nothing else, so `slipwai generate --target aws` cannot be run here: there is no backend offered under a
cloud. What *can* be proved, and is, is every reader the move touched — each one asked for a cloud it has
no row for, and each one answering with that cloud's own words.

Each test names the module whose per-target dict it replaced, because the thing being proved is that the
dict's absence did not take the behaviour with it.
"""
from __future__ import annotations

import unittest

import checkout_packages

from slipwai import deployment_shapes, loaded_targets, preflight
from slipwai.catalog import CATALOG
from slipwai.errors import GenerationError
from slipwai.project import add_commands, deploy_workflow, flag_route, infra, production, target_docs
from slipwai.selection import Selection
from slipwai.services import App
from slipwai.target_protocol import PROTOCOL, SCRIPTS, required

#: Both clouds, where this checkout has them. A package that is not checked out skips rather than passing on
#: nothing, which is the failure mode `checkout_packages` exists to prevent.
CLOUDS = [name for name in ("aws", "azure") if checkout_packages.installed(name)]
HERE = unittest.skipUnless(CLOUDS, "no target package is checked out")


def app() -> App:
    """One service of the only language this checkout pins, answering the axes a cloud provisions.

    The toy is local-only — it declares the `none` target and nothing else — so this is not a project that
    could be *generated* on a cloud. It is enough to ask each reader for one, which is what is being proved:
    the readers find the cloud's words, not whether the toy may be deployed there.
    """
    return App(name="service", path="apps/service", kind="service", language="toy", framework="plain",
               port=8080, selection=Selection({"write-model": "events", "persistence": "postgres",
                                               "http": "toy-serve"}))


@HERE
class ProtocolTest(unittest.TestCase):
    """Every member a managed target owes, answered by every cloud this checkout carries."""

    def test_each_installed_cloud_answers_every_required_member(self) -> None:
        for cloud in CLOUDS:
            for member in required():
                with self.subTest(target=cloud, member=member.name):
                    self.assertTrue(loaded_targets.answer(cloud, member))

    def test_each_installed_cloud_answers_nothing_the_protocol_does_not_declare(self) -> None:
        for cloud in CLOUDS:
            with self.subTest(target=cloud):
                self.assertLessEqual(set(loaded_targets.target_of(cloud).answers), set(PROTOCOL))

    def test_every_cloud_loaded_without_a_refusal(self) -> None:
        self.assertEqual(loaded_targets.refusals(), [])


@HERE
class RowTest(unittest.TestCase):
    """The catalogue, which holds no cloud of its own and every installed one."""

    def test_each_installed_cloud_is_a_target_a_project_can_be_generated_against(self) -> None:
        for cloud in CLOUDS:
            with self.subTest(target=cloud):
                self.assertIn(cloud, CATALOG["targets"])
                self.assertTrue(CATALOG["targets"][cloud]["managed"])

    def test_an_answer_a_cloud_brings_is_offered_only_there(self) -> None:
        """`cognito` exists because AWS is installed, and under no other target."""
        if "aws" not in CLOUDS:
            self.skipTest("aws is not checked out")
        self.assertEqual(CATALOG["axes"]["auth"]["options"]["cognito"]["targets"], ["aws"])

    def test_what_a_cloud_provisions_an_answer_as_is_recorded_against_it(self) -> None:
        for cloud, as_what in (("aws", "rds"), ("azure", "flexible-server")):
            if cloud not in CLOUDS:
                continue
            with self.subTest(target=cloud):
                self.assertEqual(CATALOG["axes"]["persistence"]["options"]["postgres"][cloud],
                                 {"provisions": as_what})


@HERE
class ReaderTest(unittest.TestCase):
    """Each keel reader that held a row per cloud, asked for one it has no row for."""

    def test_the_stacks_are_the_packages_own_files_copied_as_committed(self) -> None:
        """`project/infra.py`, which read `assets/targets/<cloud>/`."""
        for cloud in CLOUDS:
            with self.subTest(target=cloud):
                files = infra.target_files("shopfront", "event-modelling", cloud, [app()])
                self.assertIn("infra/bootstrap/main.tf", files)
                self.assertIn("infra/service/main.tf", files)
                self.assertIn("scripts/deploy.py", files)
                self.assertIn("terraform", files["infra/bootstrap/main.tf"])

    def test_every_page_a_project_going_to_production_gets_is_written(self) -> None:
        """`project/target_docs.py`, which was a table naming one keel module per cloud.

        The drawing and the decision record are the cloud's own; `infra/README.md` is the operations page
        3.4b added, and it is written from the shape row rather than from a page the package brings, so it
        is the one of the three the keel composes and the one that can disagree with the stacks.
        """
        for cloud in CLOUDS:
            with self.subTest(target=cloud):
                pages = target_docs.pages("shopfront", [app()], cloud)
                self.assertEqual(sorted(pages), ["docs/adr/0002-production-target.md",
                                                 "docs/deployment.md", "infra/README.md"])
                self.assertIn("flowchart", pages["docs/deployment.md"])
                liner = deployment_shapes.row(cloud, "liner") or {}
                self.assertTrue(liner)
                operations = pages["infra/README.md"]
                self.assertTrue(operations.startswith("# Liner infrastructure"))
                self.assertIn(f"Compute: {liner['compute']}.", operations)
                self.assertIn(f"Database: {liner['database']}.", operations)
                self.assertIn(liner["transition"], operations)
                self.assertIn("make deploy ENV=production", operations)

    def test_a_skiff_gets_the_same_three_pages_written_round_its_own_row(self) -> None:
        """The shape `pages` is asked for decides the words, and a skiff's are not a liner's.

        The deployment drawing and the decision record are the keel's for a skiff — the package's pages
        describe a pipeline with a staging environment this shape has not got — so all three say one
        environment, and all three say the compute the shape row names.
        """
        for cloud in CLOUDS:
            with self.subTest(target=cloud):
                pages = target_docs.pages("shopfront", [app()], cloud, "skiff")
                self.assertEqual(sorted(pages), ["docs/adr/0002-production-target.md",
                                                 "docs/deployment.md", "infra/README.md"])
                skiff = deployment_shapes.row(cloud, "skiff") or {}
                self.assertTrue(skiff)
                for page in pages.values():
                    self.assertIn(f"Compute: {skiff['compute']}.", page)
                    self.assertIn(f"Database: {skiff['database']}.", page)
                self.assertTrue(pages["infra/README.md"].startswith("# Skiff infrastructure"))
                self.assertIn("deploys the one\nproduction environment", pages["docs/deployment.md"])

    def test_the_readme_borrows_the_clouds_own_nouns(self) -> None:
        """`project/target_docs.WORDS`."""
        for cloud in CLOUDS:
            with self.subTest(target=cloud):
                words = target_docs.words(cloud)
                self.assertEqual(sorted(words), ["credentials", "runtime", "site"])
                self.assertTrue(target_docs.prerequisites(cloud))

    def test_the_deploy_workflow_takes_its_sign_in_from_the_cloud(self) -> None:
        """`project/deploy_workflow.CLOUD_STEPS`."""
        for cloud in CLOUDS:
            with self.subTest(target=cloud):
                parts = deploy_workflow.pipeline(cloud)
                self.assertTrue(parts["credentials"].strip().startswith("- "))
                self.assertIn("IMAGE_REGISTRY", parts["environment"])

    def test_the_makefiles_registry_words_are_the_clouds(self) -> None:
        """`project/production.REGISTRY`."""
        for cloud in CLOUDS:
            with self.subTest(target=cloud):
                name, registry, example, platform = production.registry_words(cloud)
                self.assertTrue(all((name, registry, example, platform)))

    def test_the_flag_transports_are_the_clouds(self) -> None:
        """`project/flag_route.DEFAULT_TRANSPORT`."""
        for cloud in CLOUDS:
            with self.subTest(target=cloud):
                default, _opt_in = flag_route.transports_of(cloud)
                self.assertTrue(default)

    def test_what_add_service_says_afterwards_is_the_clouds(self) -> None:
        """`project/add_commands.PRODUCTION_AFTERWARDS`."""
        for cloud in CLOUDS:
            with self.subTest(target=cloud):
                self.assertIn("deploys to", add_commands.afterwards(cloud, "service"))
                self.assertIn("deploys to", add_commands.afterwards(cloud, "web"))

    def test_each_cloud_ships_the_setup_hook_init_runs_and_it_says_what_it_would_do(self) -> None:
        """The hook is the cloud's: carried in `scripts`, and asked `--check` it names each tool it would
        install with no manager found, which is what a machine with nothing on it is told."""
        import os
        import subprocess
        import sys
        for cloud in CLOUDS:
            with self.subTest(cloud=cloud):
                hook = loaded_targets.setup_for(cloud)
                self.assertEqual(hook, "scripts/setup.py")
                scripts = loaded_targets.answer(cloud, SCRIPTS)
                script = loaded_targets.root_of(cloud) / str(scripts[hook])
                self.assertTrue(script.is_file(), script)
                done = subprocess.run([sys.executable, str(script), "--check"], capture_output=True, text=True,
                                      env={**os.environ, "PATH": "/nonexistent"}, cwd=str(script.parents[1]))
                for tool in loaded_targets.tools_for(cloud):
                    self.assertIn(tool, done.stdout, done.stdout + done.stderr)
                self.assertNotIn("Installing", done.stdout)

    def test_the_tools_preflight_refuses_on_are_the_clouds(self) -> None:
        """`targets.TOOLS` and `preflight.REGION`."""
        for cloud in CLOUDS:
            with self.subTest(target=cloud):
                self.assertIn("tofu", loaded_targets.tools_for(cloud))
                self.assertGreater(len(loaded_targets.tools_for(cloud)), 1)


class WithoutACloudTest(unittest.TestCase):
    """What the keel does when it is asked about a place it has not got, which is now the ordinary case."""

    def test_a_target_that_is_not_installed_is_refused_with_the_command_that_installs_it(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            loaded_targets.answer("gcp", required()[0])
        said = str(raised.exception)
        self.assertIn("gcp", said)
        self.assertIn("target install gcp", said)

    def test_a_target_that_provisions_nothing_is_asked_for_nothing(self) -> None:
        """`none` has no CLI to sign in with and no region to be told, so `preflight` wants nothing."""
        for target in ("none", "existing"):
            with self.subTest(target=target):
                self.assertEqual(preflight.missing_for(target), [])
                self.assertEqual(infra.target_files("shopfront", "event-modelling", target, [app()]), {})

    def test_a_target_with_no_prose_name_is_called_what_it_is_called(self) -> None:
        self.assertEqual(loaded_targets.cloud_of("none"), "none")


if __name__ == "__main__":
    unittest.main()
