"""The Spec Kit phases slipwai composes around its own gap-finding and delivery stages."""
from __future__ import annotations

import re
import unittest

import checkout_packages  # noqa: F401

from slipwai.project import ladder


def rung_bodies(text: str) -> dict[str, str]:
    parts = re.split(r"^(?=\d+\. \*\*)", text, flags=re.MULTILINE)
    found: dict[str, str] = {}
    for part in parts:
        heading = re.search(r"^\d+\. \*\*(.+?)\*\*", part, re.MULTILINE)
        if heading:
            found[heading.group(1)] = " ".join(part.split())
    return found


class SpecKitFlowTest(unittest.TestCase):
    def test_clarify_precedes_the_parallel_checklist_and_find_gaps_survey(self) -> None:
        for event in (True, False):
            bodies = rung_bodies(ladder.sail_ladder(event=event, apps=[], target="aws"))
            specification = bodies["Product specification"]
            with self.subTest(event=event):
                self.assertIn("/speckit-clarify", specification)
                self.assertIn("/speckit-checklist", specification)
                self.assertIn("read-only survey phase of `skills/find-gaps/SKILL.md` in parallel",
                              specification)
                self.assertIn("Parallel workers do not edit `spec.md`", specification)
                self.assertLess(specification.index("/speckit-clarify"),
                                specification.index("/speckit-checklist"))

    def test_analyze_precedes_implementation_and_tasks_to_issues_stays_off_the_ladder(self) -> None:
        bodies = rung_bodies(ladder.sail_ladder(event=True, apps=[], target="aws"))
        implementation = bodies["Implementation"]
        self.assertLess(implementation.index("/speckit-analyze"),
                        implementation.index("Spec Kit implement command"))
        self.assertNotIn("/speckit-taskstoissues", " ".join(bodies.values()))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
