"""CI's split of the suite: every test module in exactly one shard, the slow ones spread across them.

What is proved: the four shards together are the whole suite with nothing twice, so splitting the gate
drops no test; on each platform the shards' measured loads are within one module of each other; a module
the record has not measured yet still lands somewhere; and a bad index is a usage line, not a traceback.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("test_shard_script", ROOT / "scripts/test-shard.py")
assert _spec is not None and _spec.loader is not None
shard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shard)


class ShardTest(unittest.TestCase):
    def test_the_shards_are_the_whole_suite_once(self) -> None:
        held = shard.shards(4)
        everything = sorted(path.stem for path in (ROOT / "tests").glob("test_*.py"))
        self.assertEqual(sorted(name for one in held for name in one), everything)

    def test_each_platforms_shards_are_balanced_on_what_they_took(self) -> None:
        for platform in ("win32", "darwin", "linux"):
            names = sorted(path.stem for path in (ROOT / "tests").glob("test_*.py"))
            cost = shard.weights(names, platform)
            loads = [sum(cost[name] for name in one) for one in shard.shards(4, platform)]
            self.assertLessEqual(max(loads) - min(loads), max(cost.values()), platform)

    def test_a_module_not_measured_yet_still_has_a_weight(self) -> None:
        cost = shard.weights(["test_loop", "test_not_written_yet"], "linux")
        self.assertGreater(cost["test_not_written_yet"], 0)

    def test_a_bad_index_is_a_usage_line(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()) as said:
            self.assertEqual(shard.main(["4", "4"]), 2)
        self.assertIn("usage", said.getvalue())


if __name__ == "__main__":
    unittest.main()
