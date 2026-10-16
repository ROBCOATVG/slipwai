"""A further feature is handed to `/sail`. The directory is the record that session writes.

Nobody creates `docs/intake/` in order to start. The session writes the request there, assessment decides
whether it deserves a specification, and `specified.json` is how the next session knows the sources it
decided from have not changed.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.project import intake


def tree() -> Path:
    return Path(tempfile.mkdtemp())


class CaptureTest(unittest.TestCase):
    def test_a_request_becomes_a_slug_and_the_exact_words(self) -> None:
        root = tree()
        folder, missing = intake.capture(root, "this new fancy feature please")
        self.assertEqual(missing, ())
        self.assertEqual(folder.name, "this-new-fancy-feature-please")
        self.assertIn("this new fancy feature please", (folder / "brief.md").read_text(encoding="utf-8"))

    def test_a_second_request_with_the_same_words_does_not_overwrite_the_first(self) -> None:
        root = tree()
        first, _ = intake.capture(root, "Billing")
        second, _ = intake.capture(root, "Billing")
        self.assertNotEqual(first, second)
        self.assertTrue((first / "brief.md").is_file())

    def test_a_document_the_session_can_read_is_kept_beside_the_brief(self) -> None:
        root = tree()
        source = root / "notes.md"
        source.write_text("# Billing\n", encoding="utf-8")
        folder, missing = intake.capture(root, "Billing", (source,))
        self.assertEqual(missing, ())
        self.assertEqual((folder / "notes.md").read_text(encoding="utf-8"), "# Billing\n")

    def test_a_document_the_session_cannot_read_is_named_and_not_invented(self) -> None:
        root = tree()
        folder, missing = intake.capture(root, "Billing", (root / "gone.md",))
        self.assertEqual(missing, ("gone.md",))
        self.assertFalse((folder / "gone.md").exists())


class StateTest(unittest.TestCase):
    def test_a_captured_idea_is_waiting_for_a_yes_before_anything_else(self) -> None:
        root = tree()
        intake.capture(root, "Billing")
        found = intake.ideas(root)
        self.assertEqual(found[0].state, "confirm")
        self.assertEqual(intake.pending(root), ["billing"])

    def test_a_go_after_the_yes_is_ready_to_specify(self) -> None:
        root = tree()
        folder, _ = intake.capture(root, "Billing")
        (folder / "confirmed").write_text("yes\nperson\n", encoding="utf-8")
        decision = root / ".specify/assessments/billing"
        decision.mkdir(parents=True)
        (decision / "decision.md").write_text("Verdict: go\n", encoding="utf-8")
        self.assertEqual(intake.ideas(root)[0].state, "go")

    def test_a_kill_stops_short_of_a_specification(self) -> None:
        root = tree()
        folder, _ = intake.capture(root, "Billing")
        (folder / "confirmed").write_text("yes\nskipper\n", encoding="utf-8")
        decision = root / ".specify/assessments/billing"
        decision.mkdir(parents=True)
        (decision / "decision.md").write_text("**Verdict:** kill\n", encoding="utf-8")
        self.assertEqual(intake.ideas(root)[0].state, "kill")
        self.assertEqual(intake.ready(root), [])

    def test_a_matching_receipt_is_specified_and_a_changed_source_is_not(self) -> None:
        root = tree()
        folder, _ = intake.capture(root, "Billing")
        (folder / "confirmed").write_text("yes\nperson\n", encoding="utf-8")
        digest = intake.digest_of(folder)
        (folder / "specified.json").write_text(
            json.dumps({"feature": "specs/003-billing", "digest": digest}), encoding="utf-8")
        self.assertEqual(intake.ideas(root)[0].state, "specified")
        self.assertEqual(intake.ideas(root)[0].feature, "specs/003-billing")
        (folder / "brief.md").write_text("# Billing\n\nNow with refunds.\n", encoding="utf-8")
        self.assertEqual(intake.ideas(root)[0].state, "changed")


class ProfileStaysTest(unittest.TestCase):
    """A further feature is specified on the profile the project already has.

    Event-modelling stays event-modelling and standard stays standard. Spec Kit's preset is how a new
    feature would land on the other one, so the registry has to enable this profile and not the other.
    """

    KEPT = "Do not enable the other preset"

    def gate(self):
        import importlib.util
        path = Path(__file__).resolve().parents[1] / "assets/toolkit/scripts/check-speckit.py"
        spec = importlib.util.spec_from_file_location("check_speckit_profile", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def project(self, profile: str, enabled: list[str]) -> Path:
        home = tree()
        (home / "project.json").write_text(json.dumps({"profile": profile}), encoding="utf-8")
        presets = home / ".specify/presets"
        presets.mkdir(parents=True)
        (presets / ".registry").write_text(json.dumps({"presets": {
            name: {"enabled": True} for name in enabled}}), encoding="utf-8")
        return home

    def test_the_commands_and_the_ladder_keep_the_profile_the_project_has(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for name in ("assets/toolkit/commands/assess.md", "assets/toolkit/commands/draft.md",
                     "assets/toolkit/commands/sail.md"):
            self.assertIn(self.KEPT, (root / name).read_text(encoding="utf-8"), name)
        from slipwai.project.ladder import sail_ladder
        self.assertIn(self.KEPT, sail_ladder(True, []))
        self.assertIn(self.KEPT, sail_ladder(False, []))
        self.assertIn(self.KEPT, intake.readme())

    def test_the_enabled_preset_is_the_projects_profile_and_not_the_other(self) -> None:
        gate = self.gate()
        self.assertEqual(gate.profile_preset_findings(tree()), [])
        self.assertEqual(gate.profile_preset_findings(self.project("event-modelling", ["event-modelling"])), [])
        self.assertEqual(gate.profile_preset_findings(self.project("standard", ["standard"])), [])
        switched = gate.profile_preset_findings(self.project("event-modelling", ["standard"]))
        self.assertTrue(any("event-modelling" in line and "not enabled" in line for line in switched))
        self.assertTrue(any("standard" in line and "other profile" in line for line in switched))
        both = gate.profile_preset_findings(
            self.project("standard", ["standard", "event-modelling"]))
        self.assertTrue(any("event-modelling" in line and "other profile" in line for line in both))
        self.assertFalse(any("not enabled" in line for line in both))
