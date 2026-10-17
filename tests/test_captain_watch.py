"""The captain's watch on a stage that is working, and on one that has stopped itself.

What counts as progress, and whose reason a park carries. Beside `test_captain.py`, which holds the watch on a
stage that is not working, because that suite is at its budget.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from captain_fixture import Fixture


class WorkingTest(Fixture):
    def test_a_drive_committing_to_its_slice_branch_is_not_ended(self) -> None:
        """The implement rung commits an example at a time and writes no deck line until its mark: commits
        are evidence in git, not the agent's account of itself."""
        self.budget(minutes=0.05)
        commits = """import os, subprocess, sys, time
env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
parent = []
for n in range(6):
    made = subprocess.run(["git", "commit-tree", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", "-m", str(n),
                           *parent], capture_output=True, text=True, env=env, check=True).stdout.strip()
    subprocess.run(["git", "update-ref", "refs/heads/slice/" + sys.argv[1], made], check=True)
    parent = ["-p", made]
    time.sleep(1)
"""
        done = self.captain("ORD", self.sail(commits), timeout=120)
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertNotIn("the stage was ended", " ".join(parked), done.stdout)

    def test_a_drive_that_parked_itself_is_not_parked_again_over_its_reason(self) -> None:
        """The reason the session met is the one a person needs; what the gate then missed hides it."""
        parks_itself = """import sys, json, pathlib, datetime
fairway = sys.argv[2]
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
with path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps({"v": 1, "t": now, "kind": "parked", "fairway": fairway,
                             "why": "trunk is red at check-openapi"}) + "\\n")
"""
        done = self.captain("ORD", self.sail(parks_itself))
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(parked, ["trunk is red at check-openapi"], done.stdout)
        self.assertIn("trunk is red at check-openapi", done.stdout)


if __name__ == "__main__":
    unittest.main()
