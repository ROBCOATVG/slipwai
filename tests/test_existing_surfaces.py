"""What a project has already drawn or built, listed for the mock-up stage before it draws a further feature.

`scripts/agents/existing.py` is what hands the stage its list — earlier features' mock-ups, the browser app's
committed previews, its routes and its own stylesheets, the event model's `ui` frames, `docs/design.md` — so a
further feature is drawn into the flow the project has, in the app's own look, rather than alone in a look made
up for it. The hard case is a project with a built app and no storyboard anywhere.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401
from crossed_project import FIRST, FURTHER, crossed, storyboard, write

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "assets/toolkit/scripts/agents"


def loaded(name: str = "existing") -> Any:
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", AGENTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # Python 3.11's dataclasses look a module up by name
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


class ListingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = crossed(Path(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.tree, True)
        self.module = loaded()

    def listing(self, feature: str = FURTHER) -> dict[str, Any]:
        return self.module.listing(feature, self.tree)

    def test_a_built_app_with_no_storyboard_is_listed_by_surface_with_its_previews(self) -> None:
        found = self.listing()
        self.assertEqual(found["storyboards"], [])
        app = found["apps"][0]
        self.assertEqual((app["name"], app["path"]), ("web", "apps/web"))
        self.assertEqual(app["styles"], ["apps/web/src/styles/base.css", "apps/web/src/styles/tokens.css"])
        surfaces = {one["name"]: one["states"] for one in app["previews"]}
        self.assertEqual(sorted(surfaces), ["Deal console", "New workspace", "Sign in"])
        self.assertEqual(surfaces["Deal console"], [
            {"state": "deals", "page": "apps/web/screens/deal-console-deals.html"},
            {"state": "empty", "page": "apps/web/screens/deal-console-empty.html"}])
        self.assertEqual(surfaces["Sign in"], [{"state": "shown", "page": "apps/web/screens/sign-in.html"}])

    def test_the_apps_routes_and_shell_are_read_from_its_source(self) -> None:
        app = self.listing()["apps"][0]
        self.assertEqual(app["routes"], [{"path": "/", "file": "apps/web/src/App.tsx"},
                                         {"path": "/workspaces/new", "file": "apps/web/src/App.tsx"}])
        self.assertEqual(app["shell"], ["apps/web/src/App.tsx"])

    def test_the_models_ui_frames_carry_their_slice_and_its_status(self) -> None:
        frames = self.listing()["frames"]
        self.assertEqual([(one["name"], one["slice"], one["status"]) for one in frames],
                         [("NewWorkspaceForm", "S1", "implemented"), ("ExportPanel", "S2", "planned")])
        self.assertEqual(frames[0]["mockups"],
                         [{"state": "empty", "at": "docs/event-model/mockups/new-workspace-empty.html"}])

    def test_the_look_is_the_apps_own_and_a_handed_direction_wins(self) -> None:
        self.assertEqual(self.listing()["look"], {
            "follow": "app", "files": ["apps/web/src/styles/base.css", "apps/web/src/styles/tokens.css"]})
        write(self.tree, "docs/design/brand.css", ":root{}")
        self.assertEqual(self.listing()["look"], {"follow": "handed", "files": ["docs/design/brand.css"]})

    def test_a_project_with_neither_proposes_a_look_and_a_later_feature_keeps_it(self) -> None:
        bare = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, bare, True)
        write(bare, "project.json", "{}")
        write(bare, f"specs/{FIRST}/spec.md", "# One\n")
        write(bare, f"specs/{FURTHER}/spec.md", "# Two\n")
        first = self.module.listing(FIRST, bare)
        self.assertEqual((first["look"]["follow"], first["storyboard"]), ("proposed", "first"))
        write(bare, f"specs/{FIRST}/mockups/mockups.css", "body{}")
        write(bare, f"specs/{FIRST}/mockups/basket.html", "<title>Basket</title>")
        self.assertEqual(self.module.listing(FURTHER, bare)["look"],
                         {"follow": "earlier", "files": [f"specs/{FIRST}/mockups/mockups.css"]})

    def test_what_the_storyboard_is_made_from_is_said(self) -> None:
        """Nothing drawn and something built: the first storyboard is made from what exists. An earlier
        feature's storyboard: this one frames it."""
        self.assertEqual(self.listing()["storyboard"], "from-what-exists")
        home = storyboard(self.tree, FIRST)
        write(self.tree, f"specs/{FIRST}/mockups/mock-states.md",
              "## Surface: Export pack\n- Ready — approved\n- Failed — parked: which failure?\n")
        found = self.listing()
        self.assertEqual(found["storyboard"], "extend")
        earlier = found["storyboards"][0]
        self.assertEqual((earlier["feature"], earlier["storyboard"]),
                         (FIRST, f"specs/{FIRST}/mockups/storyboard.html"))
        pack = next(one for one in earlier["surfaces"] if one["name"] == "Export pack")
        self.assertEqual(pack["page"], f"specs/{FIRST}/mockups/export-pack.html")
        self.assertEqual(pack["states"], [{"state": "Ready", "verdict": "approved"},
                                          {"state": "Failed", "verdict": "parked"}])
        self.assertTrue(home.is_dir())

    def test_the_feature_being_drawn_is_never_listed_as_existing(self) -> None:
        storyboard(self.tree, FURTHER)
        self.assertEqual(self.listing()["storyboards"], [])

    def test_the_page_it_writes_names_every_source_and_how_to_mark(self) -> None:
        path = self.module.write(FURTHER, self.tree)
        self.assertEqual(path, self.tree / f"specs/{FURTHER}/mockups/existing.md")
        said = path.read_text(encoding="utf-8")
        for expected in ("apps/web/screens/", "deal-console-deals.html", "apps/web/src/styles/tokens.css",
                         "/workspaces/new", "NewWorkspaceForm", "implemented", "docs/design.md",
                         "the app's own", "no storyboard", 'data-surface="built"'):
            self.assertIn(expected, said)
        self.assertEqual(said, self.module.write(FURTHER, self.tree).read_text(encoding="utf-8"),
                         "the same project says the same thing: the page is committed, and must not churn")

    def test_committed_previews_are_told_from_ones_only_on_disk(self) -> None:
        self.assertIsNone(self.listing()["apps"][0]["committed"], "not a git checkout: not known")
        git = ["git", "-C", str(self.tree), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "add", "apps/web/screens/sign-in.html"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "one preview"], check=True)
        self.assertEqual(self.listing()["apps"][0]["committed"], 1)

    def test_the_command_prints_the_list_and_json_on_request(self) -> None:
        shutil.copytree(AGENTS, self.tree / "scripts/agents")
        run = [sys.executable, "scripts/agents/existing.py", FURTHER]
        done = subprocess.run(run, cwd=self.tree, capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("Deal console", done.stdout)
        self.assertFalse((self.tree / f"specs/{FURTHER}/mockups/existing.md").exists(), "printing writes nothing")
        asked = subprocess.run([*run, "--json"], cwd=self.tree, capture_output=True, text=True, check=False)
        self.assertEqual(json.loads(asked.stdout)["feature"], FURTHER)
        missing = subprocess.run([*run[:2], "009-none"], cwd=self.tree, capture_output=True, text=True, check=False)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("has no specification here", missing.stderr)


class HandedToTheStageTest(unittest.TestCase):
    """`make surfaces` writes the list before the session starts and tells the session where it is."""

    def setUp(self) -> None:
        self.tree = crossed(Path(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.tree, True)
        sys.path.insert(0, str(AGENTS))
        self.addCleanup(sys.path.remove, str(AGENTS))
        self.module = loaded("surfaces")
        self.module.ROOT = self.tree
        self.module.SPECS = self.tree / "specs"

    def test_built_frames_are_not_surfaces_the_drawing_drew(self) -> None:
        storyboard(self.tree)
        self.assertEqual([page.name for page in self.module.drawn(FURTHER)],
                         ["deal-console.html", "export-pack.html"])
        for page in ("deal-console.html", "export-pack.html"):
            (self.tree / f"specs/{FURTHER}/mockups/{page}").unlink()
        self.assertEqual(self.module.drawn(FURTHER), [], "what is built is framed, never counted as drawn")

    def test_the_session_is_handed_the_list_and_told_where(self) -> None:
        handed = self.module.handed(FURTHER)
        self.assertEqual(handed["SLIPWAI_EXISTING"], f"specs/{FURTHER}/mockups/existing.md")
        self.assertIn("deal-console-deals.html",
                      (self.tree / handed["SLIPWAI_EXISTING"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
