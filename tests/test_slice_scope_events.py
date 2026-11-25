"""`check-slice-scope` on a real slice branch, judging its context's events module (issue 168).

The forms one by one, each a module before and after, are `test_events_widening`, which needs no git. This
is the gate itself reading them off a branch — what `git` holds as the base against the working tree, which
is what a slice's berth is judged on — and saying the rule in its own words.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from test_slice_scope import GATE, gate_module


class EventsModuleTest(unittest.TestCase):
    """manda's S115, on a `slice/S115` branch."""

    MODULE = "apps/app/src/domain/intake/events.ts"
    TRUNK = "const EmailKindShape = z.enum(['alert', 'reminder', 'digest']);\n"

    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(GATE, self.tree / "scripts/check-slice-scope.py")
        (self.tree / "project.json").write_text('{"deployables": {"app": {"kind": "service", "path": "apps/app"}}}',
                                                encoding="utf-8")
        self.module_file = self.tree / self.MODULE
        self.module_file.parent.mkdir(parents=True)
        self.module_file.write_text(self.TRUNK, encoding="utf-8")
        for argument in ("init -q -b main", "config user.email g@example.com", "config user.name g",
                         "add -A", "commit -qm base", "checkout -q -b slice/S115"):
            subprocess.run(["git", *argument.split()], cwd=self.tree, capture_output=True, check=True)
        self.module = gate_module(self.tree)

    def verdict(self, text: str, commit: bool) -> str | None:
        self.module_file.write_text(text, encoding="utf-8")
        if commit:
            subprocess.run(["git", "commit", "-qam", "S115"], cwd=self.tree, capture_output=True, check=True)
        return self.module.Scope("S115", "main").violation(self.MODULE, "M")

    def test_manda_s115_s_widened_enum_is_in_scope_committed_or_not(self) -> None:
        widened = self.TRUNK.replace("'digest']", "'digest', 'invite']")
        self.assertIsNone(self.verdict(widened, commit=False))
        self.assertIsNone(self.verdict(widened, commit=True))

    def test_a_member_removed_is_refused_in_the_rule_s_own_words(self) -> None:
        found = self.verdict(self.TRUNK.replace(", 'digest']", "]"), commit=True) or ""
        self.assertIn("the events module may only grow", found)
        self.assertIn("a member removed (`, 'digest'`)", found)
        self.assertIn("python3 scripts/check-slice-scope.py", found)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
