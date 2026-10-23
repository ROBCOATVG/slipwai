"""Where a browser app's material comes from: the family that ships it, as a record naming its own root.

The keel ships no frontend. A family declares each one in `language.json`'s `frontends` block and answers
`browser_apps` with a `BrowserApp` per name, and nothing in the pipeline reaches for a directory under the
keel's `assets/` (`docs/frontend-protocol.md`). That is what these tests hold — that a family can supply one,
that the pipeline writes it from the family's tree, and that nothing it supplies comes from outside its own
package. The tree they write from is the `toy-web` fixture's, the smallest frontend that loads.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from registry_fakes import fake_language, fake_registry, required_answers

from slipwai.errors import GenerationError
from slipwai.loaded import writes
from slipwai.npm_workspace import BrowserApp, frontend, frontends
from slipwai.project.frontend import TOKENS, api_client_files, web_files
from slipwai.registry import BROWSER_APPS
from slipwai.selection import Selection
from slipwai.services import App

FIXTURE = Path(__file__).resolve().parent / "fixtures/frontend-family/toy-web"
TOY_VITE = BrowserApp("toy-vite", FIXTURE / "assets/frontends/toy-vite", "toy-web")


def answers(apps: dict[str, BrowserApp]) -> dict:
    """A family's answers with `browser_apps` among them. `browser_apps` is read per family, so `split` puts
    it on the family the way a real package's loader does."""
    return required_answers(extra={BROWSER_APPS: apps})


class WhatTheKeelCarriesTest(unittest.TestCase):
    def test_the_keel_offers_no_browser_app_of_its_own(self) -> None:
        """The suite's packages are the toy and the targets, none of which ships one."""
        self.assertEqual(frontends(), {})

    def test_a_frontend_nothing_here_ships_is_refused_by_name_and_says_none_is_offered(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            frontend("svelte-kit")
        self.assertIn("svelte-kit", str(raised.exception))
        self.assertIn("install a language that ships one", str(raised.exception))

    def test_a_frontend_may_not_read_a_file_outside_its_own_directory(self) -> None:
        """The root is a package's directory, and a frontend that could climb out of it could carry any file
        on the machine into somebody's repository."""
        with self.assertRaises(GenerationError) as raised:
            TOY_VITE.at("../../language.json")
        self.assertIn("toy-vite", str(raised.exception))


class WhatIsWrittenTest(unittest.TestCase):
    """The browser app the pipeline writes from a family's tree, held file by file with no language installed.

    `tests/test_frontend_only.py` proves the same end to end through `slipwai generate`; this holds the part
    that needs no generation — which trees are copied whole, and that every token is resolved in every file.
    """

    def setUp(self) -> None:
        self.web = App("web", "apps/web", "web", "toy-web", "toy-vite", 5173, first=True)
        self.files = web_files("demo", self.web, [self.web], "none", TOY_VITE)

    def test_the_skeleton_and_the_local_flag_reader_are_copied_whole(self) -> None:
        """Each tree is laid out like the app, so the files land where the tree has them and nowhere the keel
        chose: the skeleton, and the flag reader a project with nowhere to deploy reads `.env` through."""
        self.assertEqual(sorted(self.files), [
            "apps/web/index.html", "apps/web/package.json", "apps/web/src/App.tsx", "apps/web/src/flags.ts",
            "apps/web/tests/App.test.tsx", "apps/web/tests/flags.test.ts", "apps/web/vite.config.ts",
        ])
        self.assertIn("app-flags-local", self.files["apps/web/src/flags.ts"])

    def test_a_service_to_call_brings_the_route_in_its_shape(self) -> None:
        """A transport to call is what puts the route in; the tree it comes from is the one the service's
        contract allows, and either lands at the path the tree has it."""
        service = App("service", "apps/service", "service", "toy", "plain", 3000, Selection({"http": "toy-serve"}),
                      first=True)
        web = App("web", "apps/web", "web", "toy-web", "toy-vite", 5173, api="service", first=True)
        written = web_files("demo", web, [service, web], "none", TOY_VITE)
        self.assertRegex(written["apps/web/src/routes/Home.tsx"], r"app-route-(plain|client)")

    def test_the_app_is_named_and_titled_for_the_project_that_asked_for_it(self) -> None:
        self.assertEqual(json.loads(self.files["apps/web/package.json"])["name"], "demo-web")
        self.assertIn("<title>demo</title>", self.files["apps/web/index.html"])

    def test_no_token_survives_into_the_project(self) -> None:
        for path, content in self.files.items():
            for token in TOKENS:
                with self.subTest(path=path, token=token):
                    self.assertNotIn(token, content)

    def test_the_dev_server_port_is_this_apps(self) -> None:
        second = App("admin", "apps/admin", "web", "toy-web", "toy-vite", 5174)
        written = web_files("demo", second, [second], "none", TOY_VITE)
        self.assertIn("5174", written["apps/admin/vite.config.ts"])

    def test_a_project_with_no_api_document_gets_no_typed_client(self) -> None:
        """A client whose build points at a file that was never written is worse than no client."""
        self.assertEqual(api_client_files("demo", [self.web], TOY_VITE), {})


class WhatAFamilyCanSupplyTest(unittest.TestCase):
    """A family that writes browser apps hands each one over as a record, and `frontends` reads it."""

    def test_a_family_that_writes_one_offers_it_with_its_own_name_on_it(self) -> None:
        mine = BrowserApp("mine-vite", Path("/packages/mine/assets/frontends/mine-vite"))
        held = fake_registry(fake_language("fake-a", answers=answers({"mine-vite": mine})))
        found = frontends(held)["mine-vite"]
        self.assertEqual((found.name, found.root), (mine.name, mine.root))
        self.assertEqual(found.family, "fake")

    def test_a_family_that_writes_none_offers_nothing(self) -> None:
        held = fake_registry(fake_language("fake-a"))
        self.assertEqual(frontends(held), {})


class WhatTheLoaderRefusesTest(unittest.TestCase):
    """Every fault is the publisher's and is named on the publisher's machine, not at somebody's generation."""

    def setUp(self) -> None:
        self.root = FIXTURE / "assets/frontends"

    def test_an_answer_that_is_not_a_mapping_of_records_says_what_was_wanted(self) -> None:
        found = writes("mine", self.root, ("react-vite",), workspace=True)
        self.assertEqual(len(found), 1)
        self.assertIn("BrowserApp", found[0])

    def test_a_record_listed_under_a_name_it_does_not_answer_to_is_refused(self) -> None:
        apps = {"mine-vite": BrowserApp("toy-vite", self.root / "toy-vite")}
        found = writes("mine", self.root, apps, workspace=True)
        self.assertEqual(len(found), 1)
        self.assertIn("--frontend", found[0])

    def test_material_outside_the_package_is_refused_rather_than_copied(self) -> None:
        apps = {"mine-vite": BrowserApp("mine-vite", self.root.parent / "biome")}
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
        apps = {"mine-vite": BrowserApp("mine-vite", self.root / "toy-vite")}
        found = writes("mine", self.root, apps, workspace=False)
        self.assertEqual(len(found), 1)
        self.assertIn("npm_workspace", found[0])

    def test_a_family_that_writes_none_is_asked_nothing(self) -> None:
        self.assertEqual(writes("mine", self.root, {}, workspace=False), [])


if __name__ == "__main__":
    unittest.main()
