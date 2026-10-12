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

    def test_a_make_target_rename_does_not_rewrite_the_same_word_in_the_persons_own_files(self) -> None:
        files = {"Makefile": b"test:\n\tpytest\n", "apps/service/Makefile": b"\tmake test\n",
                 "docs/how-we-work.md": b"Write the test first, then the code.\n",
                 "apps/service/src/orders.py": b"def test(value):\n    return value\n"}
        moved = renamed(dict(files), [{"kind": "make-target", "from": "test", "to": "check"}])
        self.assertEqual(moved["Makefile"], b"check:\n\tpytest\n")
        self.assertEqual(moved["apps/service/Makefile"], b"\tmake check\n")
        self.assertEqual(moved["docs/how-we-work.md"], files["docs/how-we-work.md"])
        self.assertEqual(moved["apps/service/src/orders.py"], files["apps/service/src/orders.py"])

    def test_a_command_or_skill_rename_reaches_only_the_files_that_declare_it(self) -> None:
        rows = [{"kind": "command", "from": "commands/drive.md", "to": "commands/sail.md"},
                {"kind": "skill", "from": "skills/wtf", "to": "skills/debug"}]
        files = {"commands/plan.md": b"see commands/drive.md\n", "skills/house/SKILL.md": b"skills/wtf helps\n",
                 "docs/README.md": b"see commands/drive.md and skills/wtf\n"}
        moved = renamed(dict(files), rows)
        self.assertEqual(moved["commands/plan.md"], b"see commands/sail.md\n")
        self.assertEqual(moved["skills/house/SKILL.md"], b"skills/debug helps\n")
        self.assertEqual(moved["docs/README.md"], files["docs/README.md"])

    def test_a_projects_own_toolkit_shaped_path_is_not_relocated_by_the_tables_spelling(self) -> None:
        moved = renamed({"assets/toolkit/house-rules.md": b"ours", "x.md": b"theirs"}, table())
        self.assertEqual(moved, {"assets/toolkit/house-rules.md": b"ours", "x.md": b"theirs"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
