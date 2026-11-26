"""A slice's `demo` and `seeded` lines count at the branch's head, whichever run wrote them (issue 170).

manda's S114, at one commit: run 1 demoed and was told it had not seeded, run 2 seeded and was told it had not
demoed, run 3 demoed and was told it had not seeded, and it parked with its code fine. The captain counted
only the lines the turn had written and named one missing line at a time; the harbourmaster counted any line.
Both now read `evidence.py`, and the refusal names everything still owed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from captain_fixture import Fixture
from harbourmaster_fixture import MergeFixture

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"
sys.path.insert(0, str(AGENTS))

import evidence  # noqa: E402

STORY = "specs/ordering/slices/ORD-01/try-it.json"


def git(root: Path, *argv: str) -> str:
    done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv], cwd=root,
                          capture_output=True, text=True, check=True)
    return done.stdout.strip()


def commit(root: Path, files: dict[str, str], message: str) -> str:
    for path, body in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(body, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", message)
    return git(root, "rev-parse", "HEAD")


def demo(at: str = "", verdict: str = "accepted") -> logs.Entry:
    return logs.entry("demo", fairway="ORD", slice="ORD-01", verdict=verdict, **({"commit": at} if at else {}))


def seeded(at: str) -> logs.Entry:
    return logs.entry("seeded", fairway="ORD", slice="ORD-01", records=1, commit=at)


class RuleTest(unittest.TestCase):
    """The rule itself, over a real repository: what counts at a head."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        git(self.root, "init", "--quiet", "--initial-branch=main")
        self.first = commit(self.root, {"src/app.py": "one\n", STORY: "{}\n"}, "the slice")

    def read(self, lines: list[logs.Entry], head: str, turn: list[logs.Entry] | None = None) -> evidence.Standing:
        return evidence.standing(lines, "ORD-01", head, self.root, STORY, turn=turn)

    def test_the_s114_sequence_at_one_head_is_whole_on_the_third_run(self) -> None:
        lines = [demo(self.first), seeded(self.first), demo(self.first)]
        found = self.read(lines, self.first, turn=lines[2:])
        self.assertEqual((found.verdict, found.seeded), ("accepted", True))

    def test_a_seed_from_an_earlier_head_whose_code_has_changed_does_not_count(self) -> None:
        later = commit(self.root, {"src/app.py": "two\n"}, "a code change")
        found = self.read([seeded(self.first), demo(later)], later, turn=[demo(later)])
        self.assertFalse(found.seeded)
        self.assertEqual(found.stale, ("seeded",))
        self.assertEqual(found.verdict, "accepted")

    def test_a_changed_story_makes_its_seed_stale_and_records_under_specs_do_not(self) -> None:
        records = commit(self.root, {"specs/ordering/slices/ORD-01/demo-log.md": "walked\n"}, "a record")
        self.assertTrue(self.read([seeded(self.first)], records).seeded)
        story = commit(self.root, {STORY: '{"steps": [1]}\n'}, "the story changed")
        self.assertFalse(self.read([seeded(self.first)], story).seeded)
        self.assertTrue(self.read([demo(self.first)], story).verdict, "the demo is of the code, not the story")

    def test_a_line_with_no_commit_counts_only_where_this_turn_wrote_it_or_where_any_turn_does(self) -> None:
        old = demo()
        self.assertEqual(self.read([old], self.first, turn=[]).verdict, "")
        self.assertEqual(self.read([old], self.first, turn=[old]).verdict, "accepted")
        self.assertEqual(self.read([old], self.first, turn=None).verdict, "accepted")

    def test_the_newest_demo_that_counts_is_the_verdict(self) -> None:
        lines = [demo(self.first), demo(self.first, verdict="behaviour")]
        self.assertEqual(self.read(lines, self.first, turn=lines[1:]).verdict, "behaviour")


class CaptainTest(Fixture):
    """The captain's gate, run: an earlier run's lines at this head are kept, and what is owed is named whole."""

    def setUp(self) -> None:
        super().setUp()
        self.head = commit(self.root, {"src/app.py": "one\n", STORY: '{"as": "ada", "steps": []}\n'}, "trunk")
        git(self.root, "branch", "slice/ORD-01")

    def writes(self, *kinds: str) -> str:
        """A fake `/sail` that writes the lines named, each at the slice branch's head."""
        return self.sail(f"""import sys, json, pathlib, datetime
slice_id, fairway = sys.argv[1], sys.argv[2]
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
bodies = {{"mark-set": {{"mark": "Placed"}}, "demo": {{"verdict": "accepted", "commit": {self.head!r}}},
          "seeded": {{"records": 1, "commit": {self.head!r}}}}}
with path.open("a", encoding="utf-8") as handle:
    for kind in {list(kinds)!r}:
        handle.write(json.dumps({{"v": 1, "t": now, "kind": kind, "fairway": fairway, "slice": slice_id,
                                  **bodies[kind]}}) + "\\n")
""")

    def test_a_run_that_writes_its_demo_beside_a_seed_an_earlier_run_wrote_at_this_head_is_through(self) -> None:
        self.deck("ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"),
                  demo(self.head), seeded(self.head))
        self.grant("ORD-01")
        done = self.captain("ORD", self.writes("demo"))
        self.assertEqual([e.kind for e in self.read("ORD") if e.kind in ("parked", "request", "merged")],
                         ["request", "merged"], done.stdout)

    def test_a_seed_from_an_older_head_does_not_close_the_gate(self) -> None:
        self.deck("ORD", seeded(self.head))
        self.head = commit(self.root, {"src/app.py": "two\n"}, "a code change")
        git(self.root, "branch", "--force", "slice/ORD-01", self.head)
        self.attempts(0)
        done = self.captain("ORD", self.writes("mark-set", "demo"))
        parks = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parks), 1, done.stdout)
        self.assertIn("`seeded` line was written before a commit that changed its code", parks[0])
        self.assertNotIn("no `demo` line", parks[0])

    def test_a_turn_missing_both_its_demo_and_its_seed_is_told_both_at_once(self) -> None:
        self.attempts(0)
        done = self.captain("ORD", self.writes("mark-set"))
        parks = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parks), 1, done.stdout)
        self.assertIn("owes 2 things at this head", parks[0])
        self.assertIn("no `demo` line for ORD-01", parks[0])
        self.assertIn("no `seeded` line", parks[0])
        self.assertIn("deck_line.py demo --slice ORD-01", parks[0])
        self.assertIn("try_it.py seed --slice ORD-01", parks[0])

    def attempts(self, many: int) -> None:
        import json
        held = json.loads((self.root / "harbour.json").read_text(encoding="utf-8"))
        (self.root / "harbour.json").write_text(json.dumps({**held, "attempts": many}), encoding="utf-8")


class HarbourTest(MergeFixture):
    """The harbourmaster's hold reads the same rule: a seed counts at the head, and not after its code moved."""

    def setUp(self) -> None:
        super().setUp()
        (self.root / "specs/ordering").mkdir(parents=True, exist_ok=True)
        (self.root / "specs/ordering/chart.yaml").write_text(
            "slices:\n  ORD-01: {fairway: ORD, sets: [], steers_by: []}\n", encoding="utf-8")
        self.commit("the chart")
        self.git("checkout", "--quiet", "-b", "slice/ORD-01", "main")
        (self.root / STORY).parent.mkdir(parents=True, exist_ok=True)
        (self.root / STORY).write_text('{"steps": []}\n', encoding="utf-8")
        (self.root / "service.txt").write_text("one\n", encoding="utf-8")
        self.commit("ORD-01")
        self.seeded_at = self.head("slice/ORD-01")

    def then(self, path: str, body: str) -> None:
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(body, encoding="utf-8")
        self.commit(f"then {path}")
        self.git("checkout", "--quiet", "-b", "parked-ORD-01", "slice/ORD-01")

    def test_a_seed_whose_code_moved_after_it_is_refused_saying_so(self) -> None:
        self.deck("ordering", "ORD", seeded(self.seeded_at))
        self.then("service.txt", "two\n")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused", answer.fields)
        self.assertIn("not evidence of the branch's head", str(answer.fields["why"]))

    def test_a_seed_followed_only_by_records_under_specs_still_merges(self) -> None:
        self.deck("ordering", "ORD", seeded(self.seeded_at))
        self.then("specs/ordering/slices/ORD-01/demo-log.md", "walked\n")
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted", self.answer().fields)


class DeckLineCommitTest(unittest.TestCase):
    """`deck_line.py demo` says which commit it was walked at, as `seeded` always has."""

    def test_the_demo_line_records_the_checkout_s_head(self) -> None:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / "scripts/agents").mkdir(parents=True)
        for name in ("deck_line.py", "clearance.py", "logs.py", "capabilities.py", "careen.py"):
            shutil.copy(AGENTS / name, root / "scripts/agents" / name)
        git(root, "init", "--quiet", "--initial-branch=main")
        at = commit(root, {"project.json": "{}", "specs/001-club/chart.yaml":
                           "slices:\n  TB1: {fairway: tables, sets: [], steers_by: []}\n"}, "chart")
        env = {key: value for key, value in os.environ.items() if key != "SLIPWAI_FAIRWAY"}
        done = subprocess.run([sys.executable, "-B", "scripts/agents/deck_line.py", "demo", "--slice", "TB1",
                               "--verdict", "accepted"], cwd=root, capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        path = logs.deck_path(root, "001-club", "tables")
        lines = logs.fold(path.read_text(encoding="utf-8").splitlines())
        self.assertEqual(lines[-1].fields.get("commit"), at)


if __name__ == "__main__":
    unittest.main()
