"""The production target is a dimension of its own, and it filters every menu asked after it.

Four rows ship — `none`, `aws`, `azure` and `existing` — and the two managed ones are what prove the
mechanism against the real catalog: SQLite is off both their menus, Keycloak becomes that cloud's own
identity answer, and a service with no transport cannot be taken to either. The `cloud` fixture below is a
fifth, empty row — a target with nothing behind it, which is exactly why it is a fixture and not a catalog
entry — kept for the rules a real row cannot exercise, such as what the catalog refuses to declare.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from support import FactoryTestCase

from slipwai.assets import PRUNER, ROOT
from slipwai.catalog import (
    CATALOG,
    axis_applies,
    axis_options,
    axis_required,
    catalog_axis_default,
    validate_catalog,
)
from slipwai.errors import GenerationError
from slipwai.selection import resolve_selection
from slipwai.targets import managed, offered_backends, provisioned_as, required_axes


def with_cloud() -> dict:
    """The catalog with a third target that everything but SQLite is offered under, and nothing behind it.

    Provisioning declarations are dropped along with the row they would be checked against: the fixture is
    about where an option is offered, not what a target does with it."""
    catalog = json.loads(json.dumps(CATALOG))
    catalog["targets"]["cloud"] = {"label": "Cloud — a stand-in with nothing behind it, for these tests"}
    for spec in catalog["axes"].values():
        for option in spec["options"].values():
            option["targets"] = sorted(set(option["targets"]) | {"cloud"})
    catalog["axes"]["event-store"]["options"]["sqlite"]["targets"] = ["none", "existing"]
    for backend in catalog["backends"].values():
        backend["targets"] = ["none", "aws", "azure", "existing", "cloud"]
    return catalog


@contextlib.contextmanager
def pruner_matching(catalog: dict):
    """The shipped pruner's tables saying what this catalog says about targets.

    The factory refuses a catalog the pruner disagrees with, so a fixture with a third target has to be
    matched on the pruner's side too — which is also what a generated project's `./init` would read."""
    with contextlib.ExitStack() as stack:
        for axis, spec in catalog["axes"].items():
            options = PRUNER.AXES[axis]["options"]
            matched = {
                name: {**option, "targets": tuple(spec["options"][name]["targets"])}
                for name, option in options.items()
            }
            stack.enter_context(patch.dict(options, matched, clear=True))
        requires = {name: tuple(target.get("requires", [])) for name, target in catalog["targets"].items()}
        stack.enter_context(patch.dict(PRUNER.TARGET_REQUIRES, {k: v for k, v in requires.items() if v}, clear=True))
        yield


class TargetsTest(FactoryTestCase):
    def test_four_rows_ship_and_the_managed_ones_arrived_with_their_infrastructure(self) -> None:
        """A managed target with nothing behind it would generate projects claiming a destination they cannot
        reach — so `aws` and `azure` are in the catalog because `assets/targets/aws/` and
        `assets/targets/azure/` are, and the menus differ by them. `existing` manages nothing and offers
        what `none` offers: the project deploys somewhere it does not own."""
        self.assertEqual(list(CATALOG["targets"]), ["none", "aws", "azure", "existing"])
        self.assertEqual(CATALOG["default"]["target"], "none")
        for target in ("aws", "azure", "existing"):
            self.assertEqual(offered_backends(CATALOG, target), list(CATALOG["backends"]), target)
        self.assertEqual([name for name in CATALOG["targets"] if managed(CATALOG, name)], ["aws", "azure"])
        # What the design keeps off both clouds: the file store dies with the task, and Keycloak is the
        # local stand-in rather than something a project runs in production. Each cloud's own identity
        # answer is offered under that cloud alone.
        self.assertEqual(CATALOG["axes"]["event-store"]["options"]["sqlite"]["targets"], ["none", "existing"])
        self.assertEqual(CATALOG["axes"]["auth"]["options"]["keycloak"]["targets"], ["none", "existing"])
        self.assertEqual(CATALOG["axes"]["users"]["options"]["keycloak"]["targets"], ["none", "existing"])
        self.assertEqual(CATALOG["axes"]["auth"]["options"]["cognito"]["targets"], ["aws"])
        self.assertEqual(CATALOG["axes"]["auth"]["options"]["entra"]["targets"], ["azure"])
        for spec in CATALOG["axes"].values():
            for name, option in spec["options"].items():
                self.assertEqual(
                    "existing" in option["targets"], "none" in option["targets"],
                    f"{name}: existing provisions nothing, so it offers exactly what none offers",
                )
        # The same files, on purpose: what a Cognito project carries locally is the Keycloak stand-in.
        self.assertEqual(CATALOG["axes"]["auth"]["options"]["cognito"]["features"], ["keycloak"])
        self.assertEqual(CATALOG["axes"]["users"]["options"]["cognito"]["features"], ["users-keycloak"])
        # What the target provisions for an answer is declared on the option, under the target's key.
        self.assertEqual(provisioned_as(CATALOG, "event-store", "postgres", "aws"), "rds")
        self.assertEqual(provisioned_as(CATALOG, "auth", "cognito", "aws"), "cognito")
        self.assertIsNone(provisioned_as(CATALOG, "event-store", "postgres", "none"))
        self.assertIsNone(provisioned_as(CATALOG, "event-store", "postgres", "existing"))
        self.assertIsNone(provisioned_as(CATALOG, "event-store", "memory", "aws"))
        # The mechanism holds with a third row, and the pruner's copy is held to the catalog's.
        with pruner_matching(with_cloud()):
            validate_catalog(with_cloud())
        drifted = {**PRUNER.AXES["event-store"]["options"]["sqlite"], "targets": ("none", "existing", "azure")}
        with (
            patch.dict(PRUNER.AXES["event-store"]["options"], {"sqlite": drifted}),
            self.assertRaisesRegex(ValueError, "disagree about where event-store/sqlite is offered"),
        ):
            validate_catalog(CATALOG)
        with (
            patch.dict(PRUNER.TARGET_REQUIRES, {}, clear=True),
            self.assertRaisesRegex(ValueError, "disagree about which axes a target requires"),
        ):
            validate_catalog(CATALOG)

    def test_the_catalog_refuses_a_target_declaration_it_cannot_honour(self) -> None:
        for edit, message in (
            (lambda c: c["targets"].clear(), "at least one production target"),
            (lambda c: c["targets"].pop("none"), "must include none"),
            (lambda c: c["targets"]["cloud"].pop("label"), "target cloud must carry the label"),
            (lambda c: c["targets"]["cloud"].update(requires=["mars"]), "requires an axis the catalog does not define"),
            (lambda c: c["targets"]["none"].update(requires=["http"]), "none target deploys nothing"),
            (lambda c: c["default"].update(target="mars"), "default target 'mars' is not one"),
            (lambda c: c["backends"]["go"].pop("targets"), "backend go must declare the targets"),
            (
                lambda c: c["axes"]["http"]["options"]["fastify"].pop("targets"),
                "http/fastify must declare the targets",
            ),
            (
                lambda c: c["axes"]["http"]["options"]["fastify"].update(targets=["mars"]),
                "http/fastify declares a target the catalog does not offer",
            ),
            # "None" has to stay an answer everywhere, or a target could leave an axis unanswerable.
            (
                lambda c: c["axes"]["event-store"]["options"]["memory"].update(targets=["none"]),
                "event-store/memory means no infrastructure, so it must be offered under every target",
            ),
            # The same rule the default already meets per backend: where the axis offers something real, a
            # default that is not offered there is a recommendation that silently stopped being made.
            (
                lambda c: c["default"].update({"event-store": "sqlite"}),
                "event-store default 'sqlite' is not offered under the aws target, which can be given "
                "postgres",
            ),
            # Provisioning is a claim about a target the option is offered under, and says what it is.
            (
                lambda c: c["axes"]["event-store"]["options"]["sqlite"].update(aws={"provisions": "efs"}),
                "event-store/sqlite says how it is provisioned under aws, where it is not offered",
            ),
            (
                lambda c: c["axes"]["event-store"]["options"]["postgres"].update(aws={}),
                "event-store/postgres's aws entry must say what it provisions",
            ),
        ):
            catalog = with_cloud()
            edit(catalog)
            with (
                self.subTest(message=message),
                pruner_matching(with_cloud()),
                self.assertRaisesRegex(ValueError, message),
            ):
                validate_catalog(catalog)

    def test_an_option_is_offered_per_target_the_way_it_is_offered_per_backend(self) -> None:
        for backend in CATALOG["backends"]:
            self.assertEqual(axis_options("event-store", backend, "none"), ["memory", "sqlite", "postgres"])
            self.assertEqual(axis_options("event-store", backend, "aws"), ["memory", "postgres"], backend)
            self.assertEqual(axis_options("auth", backend, "none"), ["none", "keycloak"])
            self.assertEqual(axis_options("auth", backend, "aws"), ["none", "cognito", "auth0"], backend)
            self.assertEqual(axis_options("users", backend, "aws"), ["none", "cognito", "auth0"], backend)
            self.assertTrue(axis_applies("event-store", "event-modelling", backend, "aws"))
        # The backend filter still applies underneath the target one.
        self.assertEqual(axis_options("http", "go", "aws"), ["none", "net-http"])
        # A default the target does not offer falls back to the no-infrastructure answer, exactly as a
        # default the backend cannot be given does — `validate_axis_targets` is what refuses the catalog
        # that would rely on it.
        catalog = with_cloud()
        catalog["default"]["event-store"] = "sqlite"
        self.assertEqual(catalog_axis_default(catalog, "event-store", "go", "none"), "sqlite")
        self.assertEqual(catalog_axis_default(catalog, "event-store", "go", "cloud"), "memory")

    def test_an_option_the_target_does_not_offer_is_refused_with_the_flag_that_fixes_it(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            resolve_selection({"event-store": "sqlite"}, "event-modelling", "typescript", "aws")
        message = str(refused.exception)
        self.assertIn("--event-store sqlite is offered under the none/existing target only", message)
        self.assertIn("this project's target is aws", message)
        # Both ways out, in the same voice as the per-backend refusal.
        self.assertIn("--event-store postgres", message)
        self.assertIn("--target none", message)
        with self.assertRaisesRegex(GenerationError, "--auth cognito, or with --target none"):
            resolve_selection({"auth": "keycloak", "http": "fastify"}, "event-modelling", "typescript", "aws")
        # Asking for nothing, and for something the target does offer, both still work.
        resolve_selection({"event-store": "memory"}, "event-modelling", "typescript", "aws")
        selection = resolve_selection(
            {"event-store": "postgres", "http": "fastify", "auth": "cognito", "users": "cognito"},
            "event-modelling", "typescript", "aws",
        )
        # Cognito is answered with Keycloak's files, so every feature-keyed site emits the local stand-in.
        self.assertEqual(selection.feature_of("auth"), "keycloak")
        self.assertEqual(selection.feature_of("users"), "users-keycloak")
        self.assertEqual(selection.summary["auth"], "cognito")
        # The flag exists whatever the catalog offers, and refuses a target the catalog does not define.
        with tempfile.TemporaryDirectory() as directory:
            self.assertIn("invalid choice: 'cloud'", self.refuse(directory, "targeted", target="cloud"))

    def test_a_target_that_deploys_an_axis_refuses_its_no_infrastructure_answer(self) -> None:
        """`aws` deploys an HTTP service and proves a deploy by asking it /health, so `--http none` cannot go
        there — refused naming both ways out, and taken off the interactive menu rather than offered and then
        refused. The `none` target requires nothing, so a library or worker is still a valid project."""
        self.assertEqual(required_axes(CATALOG, "aws"), ["http"])
        self.assertEqual(required_axes(CATALOG, "none"), [])
        self.assertTrue(axis_required("http", "aws"))
        self.assertFalse(axis_required("event-store", "aws"))
        with self.assertRaises(GenerationError) as refused:
            resolve_selection({"http": "none"}, "standard", "python", "aws")
        message = str(refused.exception)
        self.assertIn("--http none cannot be taken to the aws target", message)
        self.assertIn("--http fastapi", message)
        self.assertIn("--target none", message)
        resolve_selection({"http": "none"}, "standard", "python", "none")
        # And the generated project's own pruner refuses the same prune, for the same reason.
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "deployed", "standard", "go", target="aws", http="net-http")
            result = subprocess.run(
                ["python3", "scripts/backing-services.py", "--http", "none"],
                cwd=repo, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("goes to the aws target", result.stderr)
            self.assertTrue((repo / "apps/service/cmd/serve/main.go").is_file())

    def test_project_json_records_the_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "local", target="none")
            metadata = json.loads((repo / "project.json").read_text())
            self.assertEqual(metadata["target"], "none")
            self.assertEqual(PRUNER.project_target(repo), "none")
            repo = self.generate(directory, "deployed", target="aws", http="fastify")
            self.assertEqual(json.loads((repo / "project.json").read_text())["target"], "aws")
            self.assertEqual(PRUNER.project_target(repo), "aws")

    def test_the_readme_says_what_init_needs_before_anyone_runs_it(self) -> None:
        """In a project going to production `./init` pushes and applies to an account, so the README lists
        every prerequisite — tools, identity, region, forge access, the repository's URL, the passphrase —
        above the command, and `infra/README.md` leads with the same list, above the bootstrap it is for."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "deployed", target="aws", http="fastify")
            readme = (repo / "README.md").read_text()
            self.assertLess(readme.index("## Before `./init`"), readme.index("## Start here"))
            for needed in (
                "OpenTofu 1.12", "signed in as an administrator", "aws sts get-caller-identity", "AWS_REGION",
                "gh auth login", "GITEA_TOKEN", "write:repository", "The repository's URL", "passphrase",
                "--skip-bootstrap", "0002-production-target.md",
            ):
                self.assertIn(needed, readme, needed)
            infra = (repo / "infra/README.md").read_text()
            self.assertLess(infra.index("## Before `./init`"), infra.index("## Bootstrap, once"))
            for needed in (
                "administrator", "GITEA_TOKEN", "write:repository", "TF_VAR_state_passphrase",
                "The repository's URL", "OpenTofu 1.12", "aws sts get-caller-identity", "AWS_REGION",
                "--skip-bootstrap", "0002-production-target.md",
            ):
                self.assertIn(needed, infra, needed)
            local = (self.generate(directory, "local", target="none") / "README.md").read_text()
            self.assertIn("## Before `./init`", local)
            for absent in ("tofu", "administrator", "GITEA_TOKEN"):
                self.assertNotIn(absent, local, absent)

    def test_the_pruner_offers_only_what_the_project_s_target_does(self) -> None:
        """`./init` re-answers the axes inside a generated project, so it applies the same filter — read
        from `project.json`'s `target`, because the pruner is the one copy shipped to every project."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "targeted", event_store="sqlite", http="fastify", auth="none"
            )
            manifest = json.loads((repo / "project.json").read_text())
            (repo / "project.json").write_text(json.dumps({**manifest, "target": "aws"}, indent=2) + "\n")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = PRUNER._main(["--event-store", "sqlite"], root=repo)
            self.assertEqual(code, 2)
            self.assertIn("not offered under the aws target", stderr.getvalue())
            # Refused before anything was touched, and the listing never offered it.
            self.assertTrue((repo / "apps/service/src/adapters/driven/event-store-sqlite.ts").is_file())
            listing = io.StringIO()
            with contextlib.redirect_stdout(listing):
                self.assertEqual(PRUNER._main(["--list"], root=repo), 0)
            self.assertNotIn("sqlite", listing.getvalue())
            self.assertIn("--http", listing.getvalue())

    def test_choosing_aws_checks_the_machine_before_anything_is_written(self) -> None:
        """The tools `./init` will use are asked for at the choice that creates the need — not at the end of
        `./init`, with Spec Kit installed and a repository half made. Simulated with a PATH that has the
        interpreter and git and nothing else, since the machine running this suite may well have them all."""
        with tempfile.TemporaryDirectory() as directory:
            bare = Path(directory) / "bin"
            bare.mkdir()
            for tool in ("python3", "git", "sh", "dirname"):
                found = shutil.which(tool)
                assert found is not None, tool
                (bare / tool).symlink_to(found)
            environment = {k: v for k, v in os.environ.items() if k not in ("GITEA_TOKEN", "AWS_REGION")}
            environment["PATH"] = str(bare)
            refused = subprocess.run(
                [str(ROOT / "slipwai"), "generate", "unready", "--target", "aws", "--output", directory],
                text=True, capture_output=True, env=environment,
            )
            self.assertNotEqual(refused.returncode, 0)
            for said in (
                "--target aws needs more than this machine has", "tofu", "aws", "AWS_REGION", "gh or GITEA_TOKEN",
                "--skip-checks",
            ):
                self.assertIn(said, refused.stderr)
            self.assertFalse((Path(directory) / "unready").exists())
            # The token alone satisfies the forge requirement; the two tools are still missing.
            with_token = subprocess.run(
                [str(ROOT / "slipwai"), "generate", "unready", "--target", "aws", "--output", directory],
                text=True, capture_output=True, env={**environment, "GITEA_TOKEN": "t"},
            )
            after = with_token.stderr.split("needs more than")[1]
            self.assertNotIn("GITEA_TOKEN", after)
            # And a region in the environment clears its line.
            with_region = subprocess.run(
                [str(ROOT / "slipwai"), "generate", "unready", "--target", "aws", "--output", directory],
                text=True, capture_output=True, env={**environment, "AWS_REGION": "eu-west-2"},
            )
            self.assertNotIn("AWS_REGION", with_region.stderr.split("needs more than")[1])
            # Skipping is explicit, and a local-only project asks for nothing.
            subprocess.run(
                [
                    str(ROOT / "slipwai"), "generate", "unready", "--target", "aws", "--skip-checks",
                    "--output", directory,
                ],
                check=True, capture_output=True, env=environment,
            )
            subprocess.run(
                [str(ROOT / "slipwai"), "generate", "local", "--output", directory],
                check=True, capture_output=True, env=environment,
            )
            # And the generated ./init checks the same three before asking where to push.
            init = (Path(directory) / "unready/init").read_text()
            self.assertIn("for tool in tofu aws", init)
            self.assertIn("gh-or-GITEA_TOKEN", init)
