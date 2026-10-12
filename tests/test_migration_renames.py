"""Renames preserve edits, reject collisions, and never invent a version 1 generator."""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401

from slipwai.errors import GenerationError
from slipwai.migration_renames import renamed, table


class RenameTest(unittest.TestCase):
    def test_the_committed_axis_rename_preserves_the_persons_value(self) -> None:
        source = {"project.json": b'{"deployables":{"service":{"selection":{"event-store":"sqlite"}}}}'}
        moved = json.loads(renamed(source, table())["project.json"])
        self.assertEqual(moved["deployables"]["service"]["selection"], {"persistence": "sqlite"})
        self.assertIn(b"event-store", source["project.json"])

    def test_file_and_skill_edits_arrive_under_their_replacements(self) -> None:
        rows = [{"kind": "file", "from": "scripts/old.py", "to": "scripts/new.py"},
                {"kind": "skill", "from": "skills/old", "to": "skills/new"}]
        moved = renamed({"scripts/old.py": b"# person's edit\r\n", "skills/old/resource.md": b"# guidance"}, rows)
        self.assertEqual(moved["scripts/new.py"], b"# person's edit\r\n")
        self.assertEqual(moved["skills/new/resource.md"], b"# guidance")

    def test_two_paths_cannot_overwrite_each_other(self) -> None:
        with self.assertRaisesRegex(GenerationError, "collide"):
            renamed({"old": b"a", "new": b"b"}, [{"kind": "file", "from": "old", "to": "new"}])

    def test_two_fields_cannot_overwrite_each_other(self) -> None:
        with self.assertRaisesRegex(GenerationError, "intended value"):
            renamed({"project.json": b'{"event-store":"sqlite","persistence":"postgres"}'}, table())

    def test_a_path_cannot_move_out_of_the_project(self) -> None:
        with self.assertRaises(GenerationError):
            renamed({"old": b"a"}, [{"kind": "file", "from": "old", "to": "../outside"}])

    def test_make_target_renames_do_not_change_larger_names(self) -> None:
        moved = renamed({"Makefile": b"old: # old-target\r\n\tmake old\r\n"},
                        [{"kind": "make-target", "from": "old", "to": "new"}])
        self.assertEqual(moved["Makefile"], b"new: # old-target\r\n\tmake new\r\n")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
