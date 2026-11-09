"""CI's split of the suite: every test module in exactly one shard, the slow ones spread across them.

What is proved: the four shards together are the whole suite with nothing twice, so splitting the gate
drops no test; no shard holds more than its share of the Makefile's `SLOW` modules; and a bad index is a
usage line, not a traceback.
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

    def test_the_slow_modules_are_spread(self) -> None:
        slow = shard.slow()
        self.assertIn("test_loop", slow)
        counts = [len(slow & set(one)) for one in shard.shards(4)]
        self.assertLessEqual(max(counts) - min(counts), 1)

    def test_a_bad_index_is_a_usage_line(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()) as said:
            self.assertEqual(shard.main(["4", "4"]), 2)
        self.assertIn("usage", said.getvalue())


if __name__ == "__main__":
    unittest.main()
