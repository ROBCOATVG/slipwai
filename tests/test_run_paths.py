"""Nothing names a place under `.slipwai/` that is neither the run's folder nor the committed record.

Phase 25.1: the run's own state was ignored a name at a time, and the list fell behind what a run writes three
times — each time an untracked file in every berth that `check-slice-scope` failed every slice on. Now it all
lives under `.slipwai/run/`, which one ignore line covers, and this holds the code and the prose to that: a
path under `.slipwai/` is `run/...` or one of `logs.COMMITTED`, and anything else is a name the ignore file
does not cover. The few places that name an old spelling on purpose — the fallback in `logs.run_dir`, the
migration that moves the old places in, the wire format of a log ref — are listed below with why.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from slipwai import berths, logs

REPOSITORY = Path(__file__).resolve().parents[1]
SCANNED = (REPOSITORY / "src", REPOSITORY / "assets/toolkit")
#: What is read: code and the prose a project receives. Binary assets and lock files say nothing about paths.
SUFFIXES = {".py", ".md", ".ts", ".js", ".json", ".sh", ".yml", ".yaml", ".toml", ".txt", ".mk", ""}
#: A project-relative path under `.slipwai/`: not inside another path, a home folder (`~/.slipwai`,
#: `$HOME/.slipwai`) or a git ref (`refs/slipwai/...` has no dot).
SPELLED = re.compile(r"(?<![\w~/$}])\.slipwai/([A-Za-z0-9_*.-]+)")
#: `".slipwai" / "name"` and `(root / ".slipwai") / "name"`, the two ways a Path join spells one.
JOINED = re.compile(r"""["']\.slipwai["']\s*\)?\s*/\s*(?:\w+\s*/\s*)?["']([^"'/]+)""")
#: A line about a person's home folder, which is the board's and never a project's.
HOME = re.compile(r"home\(\)|~/|\$HOME|\bHOME\b")
#: (file, name): the places that name an old spelling on purpose, each with its reason.
ALLOWED = {
    # The log ref's wire format: the path inside the ref's tree stays the pre-2.1 spelling so a peer still on
    # 2.0 lands every line where it reads them; `landed` maps either spelling into the logs folder.
    ("assets/toolkit/scripts/agents/travel.py", "logs"),
    # The board's own log, under the person's home folder (`at_login.LOG` is joined to `Path.home()`).
    ("src/slipwai/at_login.py", "board.log"),
}


def committed(name: str) -> bool:
    return name == "run" or name in logs.COMMITTED or f"{name}/" in logs.COMMITTED


def findings() -> list[str]:
    found: list[str] = []
    for top in SCANNED:
        for path in sorted(top.rglob("*")):
            if not path.is_file() or path.suffix not in SUFFIXES or "node_modules" in path.parts:
                continue
            relative = path.relative_to(REPOSITORY).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if ".slipwai" not in line or HOME.search(line):
                    continue
                names = [match.rstrip(".") for match in SPELLED.findall(line)] + JOINED.findall(line)
                for name in names:
                    if name and not committed(name) and (relative, name) not in ALLOWED:
                        found.append(f"{relative}:{number}: `.slipwai/{name}` is neither `.slipwai/run/` nor "
                                     f"committed — put it under `.slipwai/run/` through `logs.run_dir`")
    return found


class RunPathsTest(unittest.TestCase):
    def test_every_path_under_slipwai_is_the_run_folder_or_the_record(self) -> None:
        found = findings()
        self.assertEqual(found, [], "\n".join(found))

    def test_the_scan_catches_a_string_and_a_join(self) -> None:
        """The guard is only as good as its patterns: a name each way it is spelled, and a home folder not."""
        self.assertEqual(SPELLED.findall('x = ROOT / ".slipwai/acp/one"'), ["acp"])
        self.assertEqual(JOINED.findall('kept = root / ".slipwai" / "acp" / slice_id'), ["acp"])
        self.assertEqual(SPELLED.findall("kept in ~/.slipwai/tools"), [])
        self.assertTrue(committed("dispatch") and committed("hooks.json") and committed("run"))
        self.assertFalse(committed("acp"))

    def test_a_berth_record_is_under_the_run_folder(self) -> None:
        """`berths.py` is carried into projects and imports nothing of the keel, so it spells the folder out."""
        self.assertTrue(berths.BERTHS.startswith(f"{logs.RUN}/"))


if __name__ == "__main__":
    unittest.main()
