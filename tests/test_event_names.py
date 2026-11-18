"""`check-model`'s two naming rules ask nothing of an event already in a log (issue 95).

The rules themselves are held in `test_rung_gate.NamingTest`; this is the one exemption from them, which is
a file and not a field: `.specify/event-names-from.json`, written once by `slipwai migrate` at the crossing
from version 1. `test_event_names_parity` holds the TypeScript reader to this one.
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_rung_gate import CHECK, findings, slice_of


class HeldNamesTest(unittest.TestCase):
    """An event already in a log keeps its name: a stored event cannot be renamed (issue 95).

    `slipwai migrate` writes the names a version 1 model's implemented slices hold, once, at the crossing;
    the two naming rules pass exactly those names and hold every other one as before. The pattern is the
    plain-sentence rule's (`.specify/decisions-in-short.json`): no file, no exemption.
    """

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        (self.root / ".specify").mkdir()
        was = CHECK.ROOT
        CHECK.ROOT = self.root
        self.addCleanup(setattr, CHECK, "ROOT", was)

    def hold(self, body: object) -> None:
        text = body if isinstance(body, str) else json.dumps(body)
        (self.root / CHECK.NAMES_FROM).write_text(text, encoding="utf-8")

    def named(self, *events: str, **frame: object) -> list[str]:
        """One slice per event, read through the file as `make check-model` reads it."""
        slices = [slice_of("orders", id=f"S{number}", frames=[
            {"type": "ui", "name": f"Screen{number}"}, {"type": "cmd", "name": f"DoIt{number}"},
            {"type": "evt", "name": event, **frame}]) for number, event in enumerate(events, start=1)]
        return findings(*slices)

    def test_a_project_with_no_file_is_held_on_every_name(self) -> None:
        self.assertEqual(CHECK.held_event_names(), frozenset())
        self.assertEqual(len(self.named("WorkspaceCreated", "DocumentNotReceived")), 2)

    def test_the_names_the_file_holds_pass_both_rules(self) -> None:
        self.hold({"events": ["WorkspaceCreated", "WorkspaceDeleted", "DocumentNotReceived"]})
        self.assertEqual(self.named("WorkspaceCreated", "WorkspaceDeleted", "DocumentNotReceived"), [])

    def test_a_name_the_file_does_not_hold_is_refused_beside_ones_that_pass(self) -> None:
        self.hold({"events": ["WorkspaceCreated", "DocumentNotReceived"]})
        found = self.named("WorkspaceCreated", "ModelVersionCreated", "DocumentNotReceived", "InviteNotSent")
        self.assertEqual(len(found), 2, found)
        self.assertIn("`ModelVersionCreated` names the write and not the fact", found[0])
        self.assertIn("`InviteNotSent` names something that did not happen", found[1])

    def test_a_held_name_is_exact_and_not_a_prefix_or_a_spelling(self) -> None:
        self.hold({"events": ["WorkspaceCreated"]})
        for near in ("WorkspaceCreatedUpdated", "workspaceCreated", "NewWorkspaceCreated"):
            with self.subTest(name=near):
                self.assertEqual(len(self.named(near)), 1)

    def test_no_other_rule_is_lifted_for_a_held_name(self) -> None:
        self.hold({"events": ["WorkspaceCreated"]})
        found = self.named("WorkspaceCreated", "WorkspaceCreated")
        self.assertEqual(len(found), 1, found)
        self.assertNotIn("names the write", found[0], "two slices raising one event is refused, held or not")

    def test_a_file_that_cannot_be_read_is_said_rather_than_forgiving_everything_or_nothing(self) -> None:
        for body in ("{", "[]", "{}", {"events": "WorkspaceCreated"}, {"events": ["WorkspaceCreated", 3]},
                     {"events": ["WorkspaceCreated", ""]}, {"events": None}, "null"):
            with self.subTest(body=body):
                self.hold(body)
                with self.assertRaises(OSError) as refused:
                    self.named("WorkspaceCreated")
                self.assertIn(CHECK.NAMES_FROM, str(refused.exception))
                self.assertIn('{"events": [', str(refused.exception), "it says what the file holds")

    def test_the_gate_as_a_project_runs_it_fails_on_an_unreadable_file(self) -> None:
        self.hold("{")
        with mock.patch.object(CHECK, "load_yaml", return_value={"version": 1, "slices": []}):
            self.assertEqual(self.run_main(), 1)
        self.hold({"events": []})
        with mock.patch.object(CHECK, "load_yaml", return_value={"version": 1, "slices": []}):
            self.assertEqual(self.run_main(), 0)

    def run_main(self) -> int:
        """`check.py`'s own last lines: an `OSError` is a failed gate with its reason, never a traceback."""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                return CHECK.main()
            except (OSError, ValueError):
                return 1


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
