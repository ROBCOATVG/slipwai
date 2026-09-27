"""The design rungs of `/drive`: a screen decided before it is built and reviewed rendered before the demo — and
the extension steps that reach those rungs only through the extension's own `AGENTS.md` block."""
from __future__ import annotations

import importlib.util
import sys
import tempfile

from support import FactoryTestCase

from slipwai.assets import TOOLKIT_ROOT
from slipwai.catalog import CATALOG


def guidance(key: str) -> str:
    """An extension's `AGENTS.md` block, as its installer writes it."""
    spec = importlib.util.spec_from_file_location(f"guidance_{key}", TOOLKIT_ROOT / f"scripts/extensions/{key}/init.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Loaded from the factory's own tree, which `test_toolkit` reads file by file: no `__pycache__` left in it.
    written, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = written
    return str(module.GUIDANCE)


class DesignStageTest(FactoryTestCase):
    def test_a_screen_is_designed_before_it_is_built_and_reviewed_rendered_before_the_demo(self) -> None:
        """Three new screens reached a demo with every `check-ux-gates` gate green and still showed
        default-blue links, labels crammed against their fields, a raw UUID and a diagram drawn as a bare
        rectangle. The design skills were installed and `AGENTS.md` named them, but no rung asked for them,
        so a delegate briefed from the plan styled from the tokens, ran the gates and stopped. So the design
        is two rungs with a record in `tasks.md`, which is what makes skipping them visible.

        The rungs name only what every browser app carries. An extension's steps — `uipro`'s search,
        `ux-gates`' gates and checklists — are written into its own `AGENTS.md` block when it is adopted, so a
        project that never adopted one never reads about it."""
        with tempfile.TemporaryDirectory() as directory:
            for profile in CATALOG["profiles"]:
                repo = self.generate(directory, f"designed-{profile}", profile, "typescript", "react-vite")
                drive = (repo / "commands/drive.md").read_text()
                order = [drive.index(f"**{rung}**") for rung in
                         ("Plan and tasks", "Screen design", "Implementation", "Design review", "Convergence", "Demo")]
                self.assertEqual(order, sorted(order))

                # Read as prose, whatever the wrapping: the rungs are reflowed as they grow.
                designed = " ".join(drive.split("**Screen design**")[1].split("**Implementation**")[0].split())
                self.assertIn("`## Design review` heading with a `Designed:` line for every screen", designed)
                self.assertIn("`No screen in this slice`", designed)
                self.assertIn("`skills/frontend-design`'s second pass", designed)
                reviewed = " ".join(drive.split("**Design review**")[1].split("**Convergence**")[0].split())
                self.assertIn("a `Reviewed:` line for every screen the slice", reviewed)
                self.assertIn("review what the actor will see, not the source", reviewed)
                self.assertIn("take a screenshot of each state it can be in", reviewed)
                self.assertIn("`skills/web-interface-guidelines`", reviewed)
                self.assertIn("A passing gate is evidence for this stage, never the stage", reviewed)
                self.assertIn("Fix each finding in this slice, or record it with a reason", reviewed)
                self.assertIn("doing what an extension block in `AGENTS.md` adds to this rung as well", designed)
                self.assertIn("doing what an extension block in `AGENTS.md` adds to this rung as well", reviewed)
                # Nothing an extension installs is named by the ladder: a project that did not adopt it
                # would be sent looking for a file it does not have.
                for extension_only in ("ui-ux-pro-max", "tools/ux-gates", "check-ux-gates", "design-review.md",
                                       "wcag-checklist.md"):
                    self.assertNotIn(extension_only, drive)

                brief = " ".join((repo / "agents/drive-tasks.md").read_text().split())
                self.assertIn("The styling task names the design steps inside it", brief)
                self.assertIn("Leave a `## Design review` heading", brief)
                self.assertNotIn("ui-ux-pro-max", brief)

            repo = self.generate(directory, "no-screen", "event-modelling", "typescript", "none")
            drive = (repo / "commands/drive.md").read_text()
            self.assertNotIn("**Screen design**", drive)
            self.assertNotIn("**Design review**", drive)

    def test_an_extension_puts_its_steps_into_the_rung_they_belong_to(self) -> None:
        """The ladder names nothing an extension installs, so each adopted extension says in its own block
        which rung it adds to and what it adds: the search before the build, the gates and checklists before
        the demo."""
        uipro = guidance("uipro")
        self.assertIn("at `/drive`'s *Screen design* rung", uipro)
        self.assertIn("`Designed:` line which search the decision came from", uipro)
        gates = guidance("ux-gates")
        self.assertIn("**What this adds to `/drive`'s *Design review* rung.**", gates)
        self.assertIn("Run `make check-ux-gates` first", gates)
        self.assertIn("tools/ux-gates/workflows/design-review.md", gates)
        self.assertIn("tools/ux-gates/accessibility/wcag-checklist.md", gates)
        self.assertIn("on the screen's `Reviewed:` line", gates)

    def test_the_hand_looks_at_every_screen_it_walks(self) -> None:
        """Under `/cruise` the demo has no person at it, so the actor's delegate notices what a person would
        have seen, and hands it back against the slice's design record."""
        with tempfile.TemporaryDirectory() as directory:
            hand = (self.generate(directory, "walked") / "agents/drive-hand.md").read_text()
            self.assertIn("**Look at every screen as well as using it**", hand)
            self.assertIn("Write each as `design:` in **Feedback** with its\nscreenshot", hand)
            self.assertIn("against the slice's `## Design review` record", hand)
