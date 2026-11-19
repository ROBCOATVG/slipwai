"""Built, unseen: a surface known only from a route is built, has no picture, and is drawn as a plain box.

The order of evidence stands — preview, implemented `ui` frame, photograph, route — and a route alone is still
enough to say a surface is built. What it is not enough for is a drawing: nothing shows how the screen looks.
So `existing.py` says *built, no picture*, the storyboard marks the box `data-surface="built"
data-picture="none"`, and the one part of that which is checkable without judgement is checked: a box that
frames a page, or holds something drawn, is refused.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import shlex
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401
from crossed_project import APP, FURTHER, crossed, storyboard, write

from slipwai.drawn import record_verdict, surface_pages
from slipwai.framed import surface_kinds, unseen
from slipwai.storyboard_card import mockups_card, verdict_form
from slipwai.voyage import mockups

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "assets/toolkit/scripts/agents"
ROUTED = APP.replace("</Routes>", '  <Route\n      path="/settings"\n      element={<Settings />}\n    />\n'
                                  '    <Route path="/audit" element={<AuditTrail />} />\n  </Routes>')
BOX = '<div class="unseen" data-surface="built" data-picture="none" data-route="/settings">{inside}</div>'
PLAIN = BOX.format(inside="/settings — built, no picture")


def loaded(name: str, alias: str) -> Any:
    spec = importlib.util.spec_from_file_location(alias, AGENTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # Python 3.11's dataclasses look a module up by name
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


def boxed(root: Path, box: str = PLAIN) -> Path:
    """The further feature's storyboard with one more thing on it: the box for a surface nothing shows."""
    home = storyboard(root)
    board = home / "storyboard.html"
    board.write_text(board.read_text(encoding="utf-8") + box, encoding="utf-8")
    return home


class EvidenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = crossed(Path(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.tree, True)
        write(self.tree, "apps/web/src/App.tsx", ROUTED)
        self.module = loaded("existing", "existing_unseen")

    def surfaces(self) -> dict[str, dict[str, Any]]:
        return {one["name"]: one for one in self.module.listing(FURTHER, self.tree)["surfaces"]}

    def test_a_surface_known_only_from_a_route_is_built_and_has_no_picture(self) -> None:
        found = self.surfaces()["/settings"]
        self.assertEqual((found["kind"], found["evidence"], found["picture"]), ("built", "route", ""))
        self.assertEqual(found["routes"], ["/settings (Settings)"], "the component is read across lines")
        self.assertEqual(self.module.listing(FURTHER, self.tree)["counts"],
                         {"built": 5, "unseen": 2, "planned": 0})

    def test_a_route_that_shows_a_previewed_surface_is_that_surface(self) -> None:
        found = self.surfaces()
        self.assertEqual(found["Deal console"]["routes"], ["/ (DealConsole)"])
        self.assertEqual(found["New workspace"]["routes"], ["/workspaces/new (NewWorkspace)"])
        self.assertTrue(found["New workspace"]["picture"].endswith("new-workspace-empty.html"))

    def test_any_earlier_evidence_gives_it_a_picture_and_the_order_stands(self) -> None:
        write(self.tree, "apps/web/screens/settings-shown.html", "<title>Settings — shown</title>")
        found = self.surfaces()
        self.assertNotIn("/settings", found)
        self.assertEqual((found["Settings"]["evidence"], found["Settings"]["routes"]),
                         ("preview", ["/settings (Settings)"]))

    def test_an_implemented_frame_nobody_drew_has_no_picture_either(self) -> None:
        model = self.tree / "docs/event-model/model.yaml"
        model.write_text(model.read_text(encoding="utf-8").replace(
            "  - id: S2", "  - id: S3\n    status: implemented\n    frames:\n"
                          "      - { type: ui, name: AuditTrailScreen }\n  - id: S2"), encoding="utf-8")
        found = self.surfaces()["AuditTrailScreen"]
        self.assertEqual((found["kind"], found["evidence"], found["picture"]), ("built", "frame", ""))
        self.assertEqual(found["routes"], ["/audit (AuditTrail)"], "the route and the frame are one surface")
        write(self.tree, "specs/001-deals/slices/S3/design/audit.png", "png")
        self.assertEqual(self.surfaces()["AuditTrailScreen"]["picture"], "specs/001-deals/slices/S3/design/audit.png")

    def test_the_page_says_no_picture_and_how_to_draw_it(self) -> None:
        said = self.module.said(self.module.listing(FURTHER, self.tree))
        self.assertIn("5 built, 2 of them with no picture; 0 planned.", said)
        self.assertIn("- built, no picture — /settings — a route alone, and nothing shows how it looks: draw a "
                      "plain labelled box; route /settings (Settings)", said)
        self.assertIn('`data-surface="built" data-picture="none"`', said)


class BoxTest(unittest.TestCase):
    """The mark on the storyboard, and the half of the rule a script can hold."""

    def setUp(self) -> None:
        self.root = crossed(Path(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.module = loaded("existing", "existing_boxes")

    def faults(self, box: str) -> list[str]:
        boxed(self.root, box)
        return self.module.held(FURTHER, self.root)[0]

    def test_a_plain_labelled_box_passes_and_is_no_page(self) -> None:
        home = boxed(self.root)
        self.assertEqual(self.module.held(FURTHER, self.root), ([], []))
        self.assertEqual(unseen(home), ["/settings"])
        self.assertEqual(len(surface_kinds(home)), 4, "a box frames no page, so it is no page's mark")
        self.assertEqual([page.name for page in surface_pages(home)], ["deal-console.html", "export-pack.html"])

    def test_a_box_that_holds_something_drawn_is_refused(self) -> None:
        for drawn in ("<form><input name='email'></form>", "<table><tr><td>Plan</td></tr></table>",
                      "<img src='guess.png'>", "<ul><li>Profile</li></ul>"):
            with self.subTest(drawn=drawn):
                found = self.faults(BOX.format(inside=f"Settings {drawn}"))
                self.assertEqual(len(found), 1, found)
                self.assertIn("a plain labelled box holds its label and nothing drawn", found[0])
                self.assertIn("/settings", found[0])

    def test_a_box_that_frames_a_page_is_refused(self) -> None:
        found = self.faults('<iframe data-surface="built" data-picture="none" data-route="/settings" '
                            'src="settings-guess.html"></iframe>')
        self.assertIn("frames settings-guess.html: a surface with no picture has no page to frame", found[0])
        found = self.faults('<img data-surface="built" data-picture="none" data-route="/settings" src="guess.png">')
        self.assertIn("is an <img>", found[-1])

    def test_a_box_says_what_it_is_known_by_and_only_a_built_surface_is_unseen(self) -> None:
        self.assertIn("does not say what it is known by",
                      self.faults('<div data-surface="built" data-picture="none">Settings</div>')[0])
        self.assertIn("only a built surface is unseen",
                      self.faults('<div data-surface="new" data-picture="none" data-route="/x">x</div>')[-1])

    def test_a_storyboard_from_before_the_mark_has_nothing_to_refuse(self) -> None:
        storyboard(self.root)
        self.assertEqual(self.module.held(FURTHER, self.root), ([], []))
        self.assertEqual(unseen(self.root / f"specs/{FURTHER}/mockups"), [])

    def test_the_command_says_what_the_storyboard_marks_and_refuses_with_the_way_out(self) -> None:
        boxed(self.root)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(self.module, "ROOT", self.root), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            self.assertEqual(self.module.main([FURTHER, "--check"]), 0, err.getvalue())
            boxed(self.root, BOX.format(inside="<table></table>"))
            self.assertEqual(self.module.main([FURTHER, "--check"]), 1)
        self.assertIn("marks 2 built, 0 planned, 1 changed, 1 new and 1 built with no picture", out.getvalue())
        self.assertIn("holds a <table>", err.getvalue())
        self.assertIn("Run: python3 scripts/agents/existing.py 002-export --check", err.getvalue())

    def test_the_card_counts_it_with_the_built_and_says_it_has_no_picture(self) -> None:
        boxed(self.root)
        card = mockups_card(mockups(self.root), self.root)
        self.assertIn('<span class="chip built">Built · 3</span> Sign in, Deal console — deals, '
                      "/settings (no picture)", card)
        self.assertIn("the 3 built surfaces are shown for the flow and are not asked about",
                      verdict_form(self.root, FURTHER))
        record_verdict(self.root, FURTHER, "approved")
        said = (self.root / f"specs/{FURTHER}/mockups/mock-states.md").read_text(encoding="utf-8")
        self.assertEqual(said.count("— approved"), 3, "a box is asked nothing and approved nothing")

    def run_stage(self, box: str) -> tuple[int, str, str]:
        """`make surfaces` with a stand-in session that draws the storyboard with this box on it."""
        sys.path.insert(0, str(AGENTS))
        self.addCleanup(sys.path.remove, str(AGENTS))
        module = loaded("surfaces", "surfaces_unseen")
        module.ROOT, module.SPECS = self.root, self.root / "specs"
        module.PID, module.HARBOUR = self.root / ".slipwai/surfaces.pid", self.root / "harbour.json"
        staged = boxed(Path(tempfile.mkdtemp()), box)
        self.addCleanup(shutil.rmtree, staged.parents[2], True)
        draw = ("import shutil, sys; shutil.copytree(sys.argv[1], sys.argv[2], dirs_exist_ok=True)")
        command = (f"{shlex.quote(sys.executable)} -c {shlex.quote(draw)} {shlex.quote(str(staged))} "
                   f"{shlex.quote(str(self.root / 'specs' / FURTHER / 'mockups'))} {{prompt}}")
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(module.harness, "choose", return_value=({}, "drawing with a stand-in")), \
                mock.patch.object(module.harness, "template", return_value=(command, "a test")), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main([FURTHER])
        return code, out.getvalue(), err.getvalue()

    def test_the_stage_ends_well_on_a_plain_box_and_counts_it(self) -> None:
        code, out, err = self.run_stage(PLAIN)
        self.assertEqual(code, 0, err)
        self.assertIn("drawn: 2 surface(s) under specs/002-export/mockups/, beside 2 built, 1 built with no "
                      "picture framed for the flow and not asked about", out)

    def test_the_stage_refuses_a_box_with_invented_content(self) -> None:
        code, _, err = self.run_stage(BOX.format(inside="<form><input></form>"))
        self.assertEqual(code, 1)
        self.assertIn("holds a <form>", err)
        self.assertIn("Run: python3 scripts/agents/existing.py 002-export --check", err)


if __name__ == "__main__":
    unittest.main()
