"""A feature that adds and changes no surface ends the mock-up stage cleanly — on grounds, and only on grounds.

It ended "nothing to approve" with a non-zero exit, and a person wrote `surfaces: none` by hand. The stage now
records it itself and exits 0 where the drawing said so with its reason and nothing in the specification, the
split or the model says otherwise. The guard the stop was there for is kept: nothing drawn is not grounds, and
a drawing that says it has no surface is not taken on its word.
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
from crossed_project import FURTHER, crossed, write

from slipwai import no_surface
from slipwai.drawn import undrawn, unsurfaced
from slipwai.passage import surfaces
from slipwai.storyboard_card import verdict_form

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "assets/toolkit/scripts/agents"
HOME = f"specs/{FURTHER}/mockups"
SPEC = """\
# Move stored exports to the new bucket

### Functional Requirements

- **FR-001**: The system MUST copy every stored export to the new bucket before the old one is retired.
- **FR-002**: The system MUST keep each export's key unchanged, so that nothing that holds a key
  has to be told.
"""
WHY = "a storage migration: exports move bucket and keep their keys, so nobody meets anything new"
NOTE = f"Blockers open: 0\nQuestions open: 0\nSurfaces: none — {WHY}\n"


class GroundsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = crossed(Path(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.root, True)
        write(self.root, f"specs/{FURTHER}/spec.md", SPEC)
        write(self.root, f"{HOME}/research.md", NOTE)

    def states(self) -> str:
        return no_surface.read(self.root / HOME / "mock-states.md")

    def test_with_every_ground_it_is_recorded_with_the_reason_and_who_recorded_it(self) -> None:
        stands, said = no_surface.settle(self.root, FURTHER)
        self.assertTrue(stands, said)
        self.assertTrue(self.states().startswith(f"surfaces: none — {WHY}\n"))
        self.assertIn("recorded by the mock-up stage, not by a person, on these grounds: the drawing's research "
                      "note says so; none of the specification's 2 requirement(s) names anything a person or "
                      "another system meets; it has no slice yet, so none carries a `ui` frame", self.states())
        self.assertIn("there is nothing to approve, and the feature moves on", said)
        self.assertEqual(surfaces(self.root), (0, 0, 0), "it adds no state, and nothing waits on a person")
        self.assertEqual(no_surface.settle(self.root, FURTHER)[0], True, "and asked again, it stands as written")

    def test_nothing_drawn_and_nothing_said_is_not_grounds(self) -> None:
        write(self.root, f"{HOME}/research.md", "Blockers open: 0\nQuestions open: 0\n")
        self.assertEqual(no_surface.settle(self.root, FURTHER), (False, ""))
        self.assertEqual(self.states(), "")

    def test_a_reason_is_part_of_saying_so(self) -> None:
        write(self.root, f"{HOME}/research.md", "Surfaces: none\n")
        stands, said = no_surface.settle(self.root, FURTHER)
        self.assertFalse(stands)
        self.assertIn("gives no reason", said)

    def test_a_requirement_that_asks_for_something_a_person_meets_stops_it(self) -> None:
        write(self.root, f"specs/{FURTHER}/spec.md", SPEC + "- **FR-003**: The system MUST let a BD keep working\n"
              "  and show a banner while exports move.\n")
        stands, said = no_surface.settle(self.root, FURTHER)
        self.assertFalse(stands)
        self.assertIn(f"specs/{FURTHER}/spec.md:8 asks for something a person or another system meets (`show`)", said)
        self.assertIn(f"Nothing was written. Settle it in the agent: /mockups {FURTHER}", said)
        self.assertEqual(self.states(), "")

    def test_a_specification_with_no_requirement_to_read_cannot_be_told(self) -> None:
        write(self.root, f"specs/{FURTHER}/spec.md", "# Move the exports\n\nThey move.\n")
        self.assertIn("has no requirement line", no_surface.settle(self.root, FURTHER)[1])

    def test_a_slice_of_it_with_a_ui_frame_or_a_surface_in_the_split_stops_it(self) -> None:
        write(self.root, f"specs/{FURTHER}/story-split.md",
              "| Slice | Value | Surfaces and states |\n|---|---|---|\n| S2 | exports | |\n")
        stands, said = no_surface.settle(self.root, FURTHER)
        self.assertIn("docs/event-model/model.yaml gives slice S2 a `ui` frame", said)
        write(self.root, f"specs/{FURTHER}/story-split.md",
              "| Slice | Value | Surfaces and states |\n|---|---|---|\n| M1 | moves | Export pack · Moving |\n")
        self.assertIn("story-split.md has M1 deliver `Export pack · Moving`", no_surface.settle(self.root, FURTHER)[1])
        write(self.root, f"specs/{FURTHER}/story-split.md",
              "| Slice | Value | Surfaces and states |\n|---|---|---|\n| M1 | moves | |\n")
        self.assertTrue(no_surface.settle(self.root, FURTHER)[0])
        self.assertIn("none of its 1 slice(s) carries a `ui` frame or names a surface", self.states())

    def test_a_verdict_already_given_or_a_page_drawn_stops_it(self) -> None:
        write(self.root, f"{HOME}/mock-states.md", "## Surface: Export pack\n- Ready — parked: redraw it\n")
        self.assertIn("mock-states.md already holds a verdict", no_surface.settle(self.root, FURTHER)[1])
        (self.root / HOME / "mock-states.md").unlink()
        self.assertIn("1 surface page(s) of it are drawn", no_surface.settle(self.root, FURTHER, drawn=1)[1])

    def test_the_board_ends_a_drawing_it_ran_over_the_protocol_the_same_way(self) -> None:
        self.assertEqual(undrawn(self.root, FURTHER), "")
        self.assertTrue(self.states().startswith("surfaces: none — "))
        self.assertIn(f"{FURTHER} adds and changes no surface", unsurfaced(self.root, FURTHER))
        self.assertIn("adds and changes no surface", verdict_form(self.root, FURTHER))
        self.assertNotIn("data-verdict", verdict_form(self.root, FURTHER))

    def test_the_board_still_stops_where_the_grounds_are_not_there(self) -> None:
        write(self.root, f"specs/{FURTHER}/spec.md", SPEC + "- **FR-003**: Users MUST see a progress page.\n")
        self.assertIn("is not recorded on its word", undrawn(self.root, FURTHER))
        write(self.root, f"{HOME}/research.md", "Blockers open: 0\n")
        self.assertIn(f"The session ended with no surface page under {HOME}/", undrawn(self.root, FURTHER))
        self.assertEqual((self.states(), unsurfaced(self.root, FURTHER)), ("", ""))

    def test_the_toolkit_carries_the_same_reading(self) -> None:
        carried = (AGENTS / "no_surface.py").read_text(encoding="utf-8")
        self.assertTrue(carried.endswith((ROOT / "src/slipwai/no_surface.py").read_text(encoding="utf-8")))


class StageTest(unittest.TestCase):
    """`make surfaces` with a stand-in session that writes a research note and draws nothing."""

    def setUp(self) -> None:
        self.root = crossed(Path(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.root, True)
        write(self.root, f"specs/{FURTHER}/spec.md", SPEC)
        sys.path.insert(0, str(AGENTS))
        self.addCleanup(sys.path.remove, str(AGENTS))
        spec = importlib.util.spec_from_file_location("surfaces_no_surface", AGENTS / "surfaces.py")
        assert spec is not None and spec.loader is not None
        module: Any = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module  # Python 3.11's dataclasses look a module up by name
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
        module.ROOT, module.SPECS = self.root, self.root / "specs"
        module.PID, module.HARBOUR = self.root / ".slipwai/surfaces.pid", self.root / "harbour.json"
        self.module = module

    def run_stage(self, note: str) -> tuple[int, str, str]:
        noted = ("import pathlib, sys; p = pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True); "
                 "p.write_text(sys.argv[2], encoding='utf-8')")
        command = (f"{shlex.quote(sys.executable)} -c {shlex.quote(noted)} "
                   f"{shlex.quote(str(self.root / HOME / 'research.md'))} {shlex.quote(note)} {{prompt}}")
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(self.module.harness, "choose", return_value=({}, "drawing with a stand-in")), \
                mock.patch.object(self.module.harness, "template", return_value=(command, "a test")), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = self.module.main([FURTHER])
        return code, out.getvalue(), err.getvalue()

    def test_a_feature_with_no_surface_ends_cleanly_and_is_recorded(self) -> None:
        code, out, err = self.run_stage(NOTE)
        self.assertEqual(code, 0, err)
        self.assertIn(f"surfaces: {FURTHER} adds and changes no surface — {WHY}. Recorded as `surfaces: none`", out)
        self.assertTrue((self.root / HOME / "mock-states.md").read_text(encoding="utf-8").startswith(
            f"surfaces: none — {WHY}"))

    def test_nothing_drawn_and_nothing_said_still_stops(self) -> None:
        code, _, err = self.run_stage("Blockers open: 0\nQuestions open: 0\n")
        self.assertEqual(code, 1)
        self.assertIn(f"no surface pages under {HOME}/", err)
        self.assertFalse((self.root / HOME / "mock-states.md").exists())

    def test_said_and_contradicted_still_stops_and_says_why(self) -> None:
        write(self.root, f"specs/{FURTHER}/spec.md", SPEC + "- **FR-003**: The system MUST email the owner.\n")
        code, _, err = self.run_stage(NOTE)
        self.assertEqual(code, 1)
        self.assertIn("is not recorded on its word", err)
        self.assertIn("(`email`)", err)
        self.assertFalse((self.root / HOME / "mock-states.md").exists())

    def test_built_frames_alone_and_no_word_of_it_still_stops(self) -> None:
        """The stop #107 added: a storyboard that only frames what exists is not a feature with no surface."""
        write(self.root, f"{HOME}/storyboard.html",
              '<iframe data-surface="built" src="../../../apps/web/screens/sign-in.html"></iframe>')
        code, _, err = self.run_stage("Blockers open: 0\n")
        self.assertEqual(code, 1)
        self.assertIn("does not say `Surfaces: none — <why>`", err)


if __name__ == "__main__":
    unittest.main()
