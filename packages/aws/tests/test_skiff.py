"""The skiff's own service stack: its own files, closed over its own declarations, and its own scripts.

The liner's stack is held to the real provider by `test_stack.py`, and so, now, is the skiff's — but that
proof needs `tofu` and a language package, which is the package's CI and not every checkout. What is here
runs anywhere and catches the failure that got past everything: a skiff file referring to a declaration
that lives only in a liner file the skiff's set deliberately leaves out. `tofu validate` says
`Reference to undeclared resource`; this says which reference, in a second, with no provider downloaded.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]

#: Every `data.<type>.<name>` a file reads, and every `data "<type>" "<name>"` a file declares.
READS = re.compile(r"\bdata\.([a-z0-9_]+)\.([a-z0-9_]+)")
DECLARES = re.compile(r'^data\s+"([a-z0-9_]+)"\s+"([a-z0-9_]+)"\s*\{', re.M)


def rows() -> dict:
    from slipwai_target_aws import TARGET

    from slipwai.target_protocol import DEPLOYMENT_SHAPES
    return TARGET.answers[DEPLOYMENT_SHAPES]


class AwsSkiffStackTest(unittest.TestCase):
    def test_the_skiff_ships_its_own_service_files_and_leaves_the_liners_behind(self) -> None:
        skiff, liner = rows()["skiff"], rows()["liner"]
        self.assertEqual(skiff["environments"], ("production",))
        self.assertEqual(liner["environments"], ("staging", "production"))
        service = skiff["stacks"]["service"]
        # The files the skiff replaces come from its own directory, not the liner's.
        for name in ("main.tf", "database.tf", "frontend.tf", "variables.tf", "outputs.tf", "versions.tf",
                     "flags.tf", "production.tfvars"):
            self.assertEqual(service[f"service/{name}"], f"skiff/{name}")
        # And the liner's load balancer, its network, its RDS and its second environment are not in the set
        # at all: a skiff is one managed compute with a managed database beside it.
        for absent in ("service/ingress.tf", "service/network.tf", "service/rds.tf", "service/staging.tfvars"):
            self.assertNotIn(absent, service)
            self.assertIn(absent, liner["stacks"]["service"])
        for source in service.values():
            self.assertTrue((PACKAGE / source).is_file(), source)

    def test_every_data_source_the_skiff_reads_is_declared_in_the_skiff(self) -> None:
        """The failure this test exists for, and the one it would have caught.

        `skiff/frontend.tf` took the managed `CachingDisabled` and `AllViewerExceptHostHeader` policies
        from `service/ingress.tf`, which is the liner's load balancer file and is not in the skiff's set.
        Nothing noticed, because no test ever generated a skiff: every generated skiff with a browser app
        was an OpenTofu configuration that could not be applied. A stack is a closed set of files, so the
        set is what this reads — including the `no-frontend`/`no-auth0` alternatives the keel swaps in,
        each checked against the set it is actually part of.
        """
        service = rows()["skiff"]["stacks"]["service"]
        # The keel picks one of each pair by whether the project has a browser app and an Auth0 answer
        # (`project/infra.py`), so each real variant is its own closed set.
        for frontend in ("service/frontend.tf", "service/no-frontend.tf"):
            for auth in ("service/auth0.tf", "service/no-auth0.tf"):
                chosen = {path: source for path, source in service.items()
                          if path not in {"service/frontend.tf", "service/no-frontend.tf",
                                          "service/auth0.tf", "service/no-auth0.tf"}}
                chosen[frontend], chosen[auth] = service[frontend], service[auth]
                with self.subTest(frontend=frontend, auth=auth):
                    declared, read = set(), {}
                    for path, source in chosen.items():
                        text = (PACKAGE / source).read_text(encoding="utf-8")
                        declared |= set(DECLARES.findall(text))
                        for reference in READS.findall(text):
                            read.setdefault(reference, path)
                    missing = sorted(f"{path}: data.{kind}.{name}"
                                     for (kind, name), path in read.items() if (kind, name) not in declared)
                    self.assertEqual(missing, [], "the skiff reads a data source no file in its set declares")

    def test_the_skiff_deploys_through_its_own_scripts_and_says_so_on_the_row(self) -> None:
        """A skiff migrates from inside `make deploy`, which is why its deploy job needs the registry."""
        skiff = rows()["skiff"]
        scripts = skiff["scripts"]
        self.assertEqual(scripts["scripts/deploy.py"], "scripts/skiff_deploy.py")
        # The liner's deploy script is kept beside it rather than replaced: the skiff's borrows from it.
        self.assertEqual(scripts["scripts/_deploy_common.py"], "scripts/deploy.py")
        self.assertEqual(scripts["scripts/skiff_migrations.py"], "scripts/skiff_migrations.py")
        self.assertEqual(rows()["liner"]["scripts"]["scripts/deploy.py"], "scripts/deploy.py")
        self.assertNotIn("scripts/skiff_migrations.py", rows()["liner"]["scripts"])
        # The row claims the deploy job has to reach the registry; the controller is why. Both halves, so
        # neither can be removed quietly: a pushed wrapper with no sign-in is `no basic auth credentials`.
        self.assertTrue(skiff["registry_at_deploy"])
        self.assertFalse(rows()["liner"].get("registry_at_deploy"))
        controller = (PACKAGE / scripts["scripts/skiff_migrations.py"]).read_text(encoding="utf-8")
        self.assertIn('run(["docker", "push", tag])', controller)
