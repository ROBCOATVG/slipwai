"""Where a browser app's material comes from, now that a language family may be the one that carries it.

The keel still ships `react-vite`, and that is the last answer of any kind inside it — every language,
extension, target and quickstart is a package already. What changed is that nothing in the pipeline reaches
for a directory under `assets/` any more: a frontend is a record naming its own root, so moving the material
into the family that writes it is a change of who answers and of nothing else.

The family is the destination because the two halves are already one dependency set: a family that answers
`npm_workspace` commits the workspace lock that resolves the browser app's `package.json` and pins the Biome
that manifest has to agree with. That is what these tests hold — that a family can supply one, that it wins
the name when it does, and that nothing it supplies can come from outside its own package.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from registry_fakes import fake_language, fake_registry, required_answers

from slipwai.errors import GenerationError
from slipwai.loaded import writes
from slipwai.npm_workspace import KEEL_APPS, BrowserApp, frontend, frontends
from slipwai.project.frontend import WEB_FEATURE_FILES, api_client_files, frontend_files, web_files
from slipwai.project.shared_packages import WORKSPACE
from slipwai.registry import BROWSER_APPS
from slipwai.services import App


def answers(apps: dict[str, BrowserApp]) -> dict:
    """A family's answers with `browser_apps` among them. `browser_apps` is read per family, so `split` puts
    it on the family the way a real package's loader does."""
    return required_answers(extra={BROWSER_APPS: apps})


class WhatTheKeelStillCarriesTest(unittest.TestCase):
    def test_the_keel_offers_the_one_browser_app_it_still_ships(self) -> None:
        self.assertEqual(sorted(frontends()), ["react-vite"])
        self.assertEqual(frontend("react-vite"), KEEL_APPS["react-vite"])

    def test_its_material_is_a_directory_laid_out_the_way_the_pipeline_reads_it(self) -> None:
        """The pipeline asks for these five by name. A record pointing at a tree missing one of them would
        be a project half-written before anything refused."""
        found = frontend("react-vite")
        for relative in ("app", "api-client", "app-flags-local", "app-flags-target", "app-route-plain"):
            with self.subTest(relative=relative):
                self.assertTrue(found.at(relative).is_dir())
        self.assertTrue(found.at("locks/frontend-only.json").is_file())

    def test_every_feature_a_browser_app_can_gain_is_a_path_inside_the_frontend(self) -> None:
        """`WEB_FEATURE_FILES` is relative to the frontend and never to the keel, so that the same row reads
        whether the material ships in a package or, as this one still does, here."""
        found = frontend("react-vite")
        for feature, relative in WEB_FEATURE_FILES.items():
            with self.subTest(feature=feature):
                self.assertFalse(Path(relative).is_absolute())
                self.assertTrue(found.at(relative).is_dir())

    def test_a_frontend_nothing_here_writes_is_refused_by_name_and_says_what_is_offered(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            frontend("svelte-kit")
        self.assertIn("svelte-kit", str(raised.exception))
        self.assertIn("react-vite", str(raised.exception))

    def test_a_frontend_may_not_read_a_file_outside_its_own_directory(self) -> None:
        """The root becomes a package's directory, and a frontend that could climb out of it could carry any
        file on the machine into somebody's repository."""
        with self.assertRaises(GenerationError) as raised:
            frontend("react-vite").at("../../catalog.json")
        self.assertIn("react-vite", str(raised.exception))


class WhatIsStillWrittenTest(unittest.TestCase):
    """The browser app the pipeline writes, held file by file with no language installed.

    `tests/test_frontend.py` proves this end to end and skips wherever no real language package is pinned,
    which is every run of the keel's own gate. So the part that needs no language — which files the skeleton
    becomes and which variant each token comes from — is held here, where it runs. Without it, moving the
    material from a path to a record would have been a change nothing in this repository could notice.
    """

    def setUp(self) -> None:
        self.web = App("web", "apps/web", "web", "typescript", "react-vite", 5173, first=True)
        self.files = web_files("demo", self.web, [self.web], "none", frontend("react-vite"))

    def test_the_skeleton_becomes_the_browser_apps_own_files(self) -> None:
        self.assertEqual(sorted(self.files), [
            "apps/web/index.html", "apps/web/package.json", "apps/web/src/App.tsx", "apps/web/src/flags.ts",
            "apps/web/src/main.tsx", "apps/web/src/styles/base.css", "apps/web/src/styles/tokens.css",
            "apps/web/tests/App.test.tsx", "apps/web/tests/flags.test.ts", "apps/web/tests/setup.ts",
            "apps/web/tsconfig.json", "apps/web/vite.config.ts",
        ])

    def test_the_app_is_named_and_titled_for_the_project_that_asked_for_it(self) -> None:
        self.assertEqual(json.loads(self.files["apps/web/package.json"])["name"], "demo-web")
        self.assertIn("<title>demo</title>", self.files["apps/web/index.html"])

    def test_a_project_with_nowhere_to_deploy_reads_its_flags_through_the_bundle(self) -> None:
        """The two flag variants export the same things, so the only way to tell which was copied is what it
        reads from: `.env` through the bundle with nowhere to deploy, `GET /api/flags` with somewhere."""
        self.assertIn("import.meta.env", self.files["apps/web/src/flags.ts"])

    def test_no_token_the_skeleton_carries_survives_into_the_project(self) -> None:
        for path, content in self.files.items():
            with self.subTest(path=path):
                self.assertNotIn("__TRANSPORT__", content)
                self.assertNotIn("__PROJECT_NAME__", content)

    def test_a_project_with_no_api_document_gets_no_typed_client(self) -> None:
        """A client whose build points at a file that was never written is worse than no client."""
        self.assertEqual(api_client_files("demo", [self.web], frontend("react-vite")), {})

    def test_a_browser_app_with_no_member_service_beside_it_takes_the_frontends_own_lock(self) -> None:
        """The workspace lock is the first npm member service's language's; with no member service there is
        none to ask, and the lock is the frontend's own — which is why the frontend carries one at all."""
        whole = frontend_files("demo", [self.web], "none")
        lock = json.loads(whole["package-lock.json"])
        self.assertEqual(lock["name"], "demo")
        self.assertEqual(lock["packages"][""]["workspaces"], ["apps/web", WORKSPACE])
        self.assertIn("apps/web", lock["packages"])
        self.assertIn("node_modules/demo-web", lock["packages"])


class WhatAFamilyCanSupplyTest(unittest.TestCase):
    """A family that writes browser apps hands each one over as a record, and `frontends` reads it."""

    def test_a_family_that_writes_one_offers_it_beside_the_keels(self) -> None:
        mine = BrowserApp("mine-vite", Path("/packages/mine/frontends/mine-vite"))
        held = fake_registry(fake_language("fake-a", answers=answers({"mine-vite": mine})))
        self.assertEqual(frontends(held)["mine-vite"], mine)
        self.assertIn("react-vite", frontends(held))

    def test_a_family_wins_a_name_the_keel_also_carries(self) -> None:
        """The family ships the lock that resolves the app it ships. A project given the keel's files under
        a family's lock is a project whose `npm ci` refuses the tree it was handed."""
        theirs = BrowserApp("react-vite", Path("/packages/mine/frontends/react-vite"))
        held = fake_registry(fake_language("fake-a", answers=answers({"react-vite": theirs})))
        self.assertEqual(frontends(held)["react-vite"], theirs)

    def test_a_family_that_writes_none_changes_nothing(self) -> None:
        held = fake_registry(fake_language("fake-a"))
        self.assertEqual(sorted(frontends(held)), ["react-vite"])


class WhatTheLoaderRefusesTest(unittest.TestCase):
    """Every fault is the publisher's and is named on the publisher's machine, not at somebody's generation."""

    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1] / "assets/frontends"

    def test_an_answer_that_is_not_a_mapping_of_records_says_what_was_wanted(self) -> None:
        found = writes("mine", self.root, ("react-vite",), workspace=True)
        self.assertEqual(len(found), 1)
        self.assertIn("BrowserApp", found[0])

    def test_a_record_listed_under_a_name_it_does_not_answer_to_is_refused(self) -> None:
        apps = {"mine-vite": BrowserApp("react-vite", self.root / "react-vite")}
        found = writes("mine", self.root, apps, workspace=True)
        self.assertEqual(len(found), 1)
        self.assertIn("--frontend", found[0])

    def test_material_outside_the_package_is_refused_rather_than_copied(self) -> None:
        apps = {"mine-vite": BrowserApp("mine-vite", self.root.parent / "toolkit")}
        found = writes("mine", self.root, apps, workspace=True)
        self.assertEqual(found, ["family mine reaches outside its directory for browser app mine-vite"])

    def test_a_root_that_is_not_there_is_refused_before_a_project_is_written(self) -> None:
        apps = {"mine-vite": BrowserApp("mine-vite", self.root / "mine-vite")}
        found = writes("mine", self.root, apps, workspace=True)
        self.assertEqual(len(found), 1)
        self.assertIn("not a directory", found[0])

    def test_a_browser_app_without_an_npm_workspace_to_hold_it_is_refused(self) -> None:
        """A browser app is an npm package in the workspace `npm_workspace` declares. A family offering one
        without that answer has no lock to resolve it with, and the refusal belongs where the package is
        named rather than at `npm ci` in somebody's generated project."""
        apps = {"mine-vite": BrowserApp("mine-vite", self.root / "react-vite")}
        found = writes("mine", self.root, apps, workspace=False)
        self.assertEqual(len(found), 1)
        self.assertIn("npm_workspace", found[0])

    def test_a_family_that_writes_none_is_asked_nothing(self) -> None:
        self.assertEqual(writes("mine", self.root, {}, workspace=False), [])


if __name__ == "__main__":
    unittest.main()
