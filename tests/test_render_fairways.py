"""Folding each fairway's own append-only files into the feature-level ones nobody edits.

Two fairways appending to one `decisions.md` is the shared-file problem from the other side: in the first
attempt it produced 54 renumbering commits in one night, and every merge of that file was a conflict in the
same three lines. So each fairway keeps its own and the feature-level file is rendered.

What is held here is the three properties that make that safe. The order is the instant each entry records,
so the folded file reads as one history rather than two lists stapled together. The ids are not touched, so
a citation written in a branch still resolves after the fold. And a rendered file that somebody edited is
refused, because a generated file edited by hand is a file that disagrees with its source and says nothing
about it.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "assets/toolkit/scripts/render-fairways.py"


def entry(id_: str, when: str, question: str) -> str:
    return (f"## {id_} — {question}\n"
            f"- **Stage:** plan · **Slice:** X · **When:** {when} · **Iteration:** 1\n"
            f"- **Decision:** something\n")


class Fixture(unittest.TestCase):
    """A project tree with two fairways. Both suites take it; neither runs the other's cases, because this
    one declares none of its own."""
    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(SCRIPT, self.tree / "scripts/render-fairways.py")
        (self.tree / "project.json").write_text("{}", encoding="utf-8")
        (self.tree / "specs/ordering/slices").mkdir(parents=True)
        for fairway in ("ordering", "billing"):
            (self.tree / f"fairways/{fairway}").mkdir(parents=True)
        spec = importlib.util.spec_from_file_location("render", self.tree / "scripts/render-fairways.py")
        assert spec is not None and spec.loader is not None
        self.module = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(self.module)

    def write(self, fairway: str, body: str) -> None:
        (self.tree / f"fairways/{fairway}/decisions.md").write_text(body, encoding="utf-8")

    def folded(self) -> str:
        self.assertEqual(self.module.main([]), 0)
        return (self.tree / "specs/ordering/decisions.md").read_text(encoding="utf-8")


class FoldTest(Fixture):
    def test_two_fairways_each_deciding_once_both_appear(self) -> None:
        """Slice 5.10b's done-when."""
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "which store"))
        self.write("billing", entry("D-BIL-01", "2026-10-07T10:00:00Z", "which gateway"))
        folded = self.folded()
        self.assertIn("D-ORD-01", folded)
        self.assertIn("D-BIL-01", folded)

    def test_the_order_is_the_instant_and_not_the_fairway(self) -> None:
        """Interleaving by time is what makes it one history rather than two lists stapled together."""
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "first")
                   + entry("D-ORD-02", "2026-10-07T11:00:00Z", "third"))
        self.write("billing", entry("D-BIL-01", "2026-10-07T10:00:00Z", "second"))
        folded = self.folded()
        self.assertLess(folded.index("D-ORD-01"), folded.index("D-BIL-01"))
        self.assertLess(folded.index("D-BIL-01"), folded.index("D-ORD-02"))

    def test_no_id_is_changed_by_the_fold(self) -> None:
        """Which is the point of an id carrying its fairway: a gap in the numbers is not a gap."""
        self.write("ordering", entry("D-ORD-07", "2026-10-07T09:00:00Z", "which store"))
        self.write("billing", entry("D-BIL-02", "2026-10-07T08:00:00Z", "which gateway"))
        folded = self.folded()
        self.assertIn("## D-ORD-07 —", folded)
        self.assertIn("## D-BIL-02 —", folded)

    def test_an_entry_with_no_instant_sorts_after_the_ones_that_have_one(self) -> None:
        """Visible at the end rather than silently first, which is where an unsorted key would put it."""
        self.write("ordering", "## D-ORD-01 — undated\n- **Decision:** something\n")
        self.write("billing", entry("D-BIL-01", "2026-10-07T10:00:00Z", "dated"))
        folded = self.folded()
        self.assertLess(folded.index("D-BIL-01"), folded.index("D-ORD-01"))

    def test_the_rendered_file_says_it_is_rendered(self) -> None:
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "which store"))
        self.assertIn("Never edit by hand", self.folded())


class CheckTest(Fixture):
    def test_a_file_that_matches_its_sources_passes(self) -> None:
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "which store"))
        self.folded()
        self.assertEqual(self.module.main(["--check"]), 0)

    def test_a_rendered_file_edited_by_hand_is_refused(self) -> None:
        """A generated file somebody edited disagrees with its source and says nothing about it."""
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "which store"))
        self.folded()
        path = self.tree / "specs/ordering/decisions.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n## D-ORD-02 — snuck in\n", encoding="utf-8")
        self.assertEqual(self.module.main(["--check"]), 1)

    def test_a_fairway_deciding_after_the_last_fold_is_refused(self) -> None:
        self.write("ordering", entry("D-ORD-01", "2026-10-07T09:00:00Z", "which store"))
        self.folded()
        self.write("billing", entry("D-BIL-01", "2026-10-07T10:00:00Z", "which gateway"))
        self.assertEqual(self.module.main(["--check"]), 1)

    def test_a_project_with_no_fairway_files_is_not_a_failure(self) -> None:
        self.assertEqual(self.module.main(["--check"]), 0)


SPLIT = """# The split

## Fairways

| Fairway | Context | Slices, in split order | held_by | Notes |
|---|---|---|---|---|
| ordering | Ordering | ORD-01; ORD-02 | — | the first |
| billing | Billing | BIL-01 | whoever typed this | and nobody can tell when |

## Slice graph
| Slice | depends_on | parallel_ok_with | Notes |
|---|---|---|---|
| ORD-01 | — | — | — |
"""


class HeldByTest(unittest.TestCase):
    """`held_by` is rendered from the claim refs and written by nothing.

    There were two answers to *who holds this fairway* — a name somebody typed in this table, and a running
    process with a pid file — and the table's was the one the loop reads. A field only a hand edit reaches
    is exactly the state this method is built around not keeping, so the column is folded from the refs the
    way every other status here is folded from a log, and `make check-rendered` refuses one that is not.
    """

    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts/agents").mkdir(parents=True)
        shutil.copy(SCRIPT, self.tree / "scripts/render-fairways.py")
        for name in ("claims.py", "logs.py"):
            shutil.copy(ROOT / f"assets/toolkit/scripts/agents/{name}", self.tree / f"scripts/agents/{name}")
        (self.tree / "project.json").write_text("{}", encoding="utf-8")
        (self.tree / "specs/ordering/slices").mkdir(parents=True)
        self.split = self.tree / "specs/ordering/story-split.md"
        self.split.write_text(SPLIT, encoding="utf-8")
        self.git("init", "--quiet", "--initial-branch=main")
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "the split")
        spec = importlib.util.spec_from_file_location("render", self.tree / "scripts/render-fairways.py")
        assert spec is not None and spec.loader is not None
        self.module = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(self.module)

    def git(self, *argv: str, where: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                              cwd=where or self.tree, capture_output=True, text=True, check=False)

    def forge(self) -> None:
        """Somewhere to push a claim to, which is what makes a claim mean anything to a second machine."""
        bare = self.tree.parent / f"{self.tree.name}-forge.git"
        self.addCleanup(shutil.rmtree, bare, True)
        self.git("init", "--quiet", "--bare", "--initial-branch=main", str(bare), where=self.tree.parent)
        self.git("remote", "add", "origin", str(bare))
        self.git("push", "--quiet", "origin", "main")

    def hold(self, fairway: str, machine: str) -> None:
        done = subprocess.run([sys.executable, str(self.tree / "scripts/agents/claims.py"),
                               "--take", fairway], cwd=self.tree, capture_output=True, text=True,
                              env={**os.environ, "SLIPWAI_MACHINE": machine})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def rows(self) -> dict[str, str]:
        """Each fairway against what the split's `held_by` cell now says."""
        found = {}
        for line in self.split.read_text(encoding="utf-8").splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) == 5 and cells[0] not in ("Fairway", "---"):
                found[cells[0]] = cells[3]
        return found

    def test_the_cell_is_the_machine_the_ref_names(self) -> None:
        self.forge()
        self.hold("ordering", "harbour_one")
        self.assertEqual(self.module.main([]), 0)
        self.assertEqual(self.rows()["ordering"], "harbour_one")

    def test_a_name_somebody_typed_is_overwritten_by_what_the_refs_say(self) -> None:
        """The column is a rendering, so a hand edit is not an error to report — it is a thing that does
        not survive the next fold, which is what makes the refs the only answer."""
        self.forge()
        self.assertEqual(self.module.main([]), 0)
        self.assertEqual(self.rows()["billing"], "—")

    def test_a_hand_edit_is_refused_by_the_check(self) -> None:
        self.forge()
        self.hold("ordering", "harbour_one")
        self.module.main([])
        held = self.split.read_text(encoding="utf-8")
        self.split.write_text(held.replace("harbour_one", "me, actually"), encoding="utf-8")
        self.assertEqual(self.module.main(["--check"]), 1)

    def test_a_released_fairway_goes_back_to_a_dash(self) -> None:
        self.forge()
        self.hold("ordering", "harbour_one")
        self.module.main([])
        done = subprocess.run([sys.executable, str(self.tree / "scripts/agents/claims.py"),
                               "--release", "ordering"], cwd=self.tree, capture_output=True, text=True,
                              env={**os.environ, "SLIPWAI_MACHINE": "harbour_one"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.module.main([]), 0)
        self.assertEqual(self.rows()["ordering"], "—")

    def test_a_harbour_with_no_forge_renders_a_dash_and_says_the_claim_is_local(self) -> None:
        """A claim no other machine can see is not routing, whatever this machine's ref says. The column
        says nothing and the command says why, rather than naming a machine nobody else can reach."""
        self.hold("ordering", "harbour_one")
        done = io.StringIO()
        with contextlib.redirect_stdout(done):
            self.assertEqual(self.module.main([]), 0)
        self.assertEqual(self.rows()["ordering"], "—")
        self.assertIn("local to this machine", done.getvalue())

    def test_a_project_with_no_split_is_not_a_failure(self) -> None:
        self.split.unlink()
        self.assertEqual(self.module.main(["--check"]), 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
