"""The pointer at a project's code index: where it is, what it claims, and which skills may carry it.

`./init --extension codegraph` installs a local code-knowledge graph and, per `docs/extensions.md`, appends
a marker-fenced pointer to `AGENTS.md`. That obligation was met and the index still went unused, for a
reason worth gating rather than remembering: `./init` can only *append*, so the block landed below the
closing line of the file and was the only place in a generated project that named the index at all — while
the two skills asking for exactly the operation it performs said nothing about how to perform it, which
sends a reader to a text search by omission.

So the factory carries its own half now, and this suite is what stops the two halves from drifting apart.
The generated section names two skills; if either stops saying what it is quoted as saying, the section is
telling every project something false, and that is a failure here rather than a puzzle downstream.

The other half is a boundary. Ten skills under `assets/toolkit/skills/` are vendored third-party at pinned
upstream commits with their own `LICENSE`; an edit to one is a conflict on every refresh, for a pointer
`AGENTS.md` already carries. That the factory's own skills may name the index and licensed ones may not is
the rule, written here where it is enforced instead of only in prose.
"""
from __future__ import annotations

import hashlib
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import ROOT
from slipwai.project.rules import CODE_INDEX

SKILLS = ROOT / "assets/toolkit/skills"
HEADING = "## Finding your way around this codebase"
# What the generated section quotes each skill as saying. The quotes are the contract: the section tells
# every project these instructions exist and that the index is how to satisfy them.
QUOTED = {
    "debugging": "Search every caller before changing a shared function",
    "refactoring": "inspect every caller and\nreachability path",
}
# How the pointer is spelled wherever it appears, so a skill can be searched for it without matching prose
# about indexes in general.
NAMED = "code index"


def skills() -> list[Path]:
    return sorted(path for path in SKILLS.iterdir() if (path / "SKILL.md").is_file())


class CodeIndexTest(FactoryTestCase):
    def test_the_section_is_near_the_top_of_every_generated_agents_file(self) -> None:
        """Position is the whole point. The extension's own block can only be appended, which put it after
        the last generated section — a footnote below the line that says this file wins."""
        with tempfile.TemporaryDirectory() as directory:
            for profile, backend, target in (("event-modelling", "go", "aws"), ("standard", "python", "none")):
                repo = self.generate(directory, f"indexed-{backend}", profile, backend, "none", target=target)
                text = (repo / "AGENTS.md").read_text()

                self.assertIn(HEADING, text)
                headings = [line for line in text.splitlines() if line.startswith("## ")]
                self.assertEqual(headings[0], HEADING, f"the section is not the first in {headings}")

    def test_a_project_that_never_adopted_the_extension_is_not_told_it_has_an_index(self) -> None:
        """The section is generated unconditionally and phrased conditionally, because an extension is
        adopted at `./init` — after this file is written. Told flatly that it has an index, a project that
        has none sends its agent looking for a tool that is not installed."""
        with tempfile.TemporaryDirectory() as directory:
            text = (self.generate(directory, "unindexed", "standard", "go") / "AGENTS.md").read_text()

            self.assertIn("If this file carries an extension block for a code index", text)
            self.assertIn("With no such block this project has no index", text)
            # The extension's own wording, which is a claim only it may make.
            self.assertNotIn("This project is indexed by CodeGraph", text)

    def test_the_skills_the_section_names_still_say_what_it_quotes_them_as_saying(self) -> None:
        """The cross-reference is the bridge between standing advice and the moment it is needed, and it is
        only worth having while it is true."""
        for skill, quote in QUOTED.items():
            text = (SKILLS / skill / "SKILL.md").read_text()
            self.assertIn(quote, text, f"{skill} no longer says what CODE_INDEX quotes it as saying")
            self.assertIn(skill, CODE_INDEX, f"CODE_INDEX no longer names {skill}")
            self.assertIn(NAMED, text, f"{skill} asks for the operation and does not name the index")

    def test_only_the_factorys_own_skills_name_the_index(self) -> None:
        """A skill with a `LICENSE` is vendored at a pinned upstream commit; naming the index in one buys a
        conflict on every refresh for a pointer `AGENTS.md` already carries. `docs/extensions.md` says so;
        this is where it holds."""
        licensed = [path for path in skills() if (path / "LICENSE").is_file()]
        self.assertTrue(licensed, "no skill carries a LICENSE, so this boundary is testing nothing")
        for path in licensed:
            body = (path / "SKILL.md").read_text().lower()
            self.assertNotIn("codegraph", body, f"{path.name} is vendored and must not name the index")
            self.assertNotIn(NAMED, body, f"{path.name} is vendored and must not name the index")

    def test_the_block_tries_every_route_before_declaring_the_index_unreachable(self) -> None:
        """The block used to be unconditional: query the index, do not delegate the exploration. In a
        checkout opened where the tooling never was — no `codegraph_explore` offered, nothing on `PATH` —
        that instruction cannot be followed, and agents either ignored it silently or reported that the
        repository has no code index while a 25MB one sat on disk. Detection, fallback and restoration are
        what make it an instruction rather than an assumption; naming the tool that was actually used is
        the part that already worked, and is what made the failure diagnosable at all.

        Asserted against the source because this text is a literal in it: `./init` appends the block, and
        `tests/test_extensions.py` covers the appending."""
        source = (ROOT / "assets/toolkit/scripts/extensions/codegraph/init.py").read_text()
        block = source.split("MARKER_BEGIN}\n")[1].split("{MARKER_END")[0]

        self.assertIn("Check you can reach it before you trust it", block)
        mcp = block.index("use `codegraph_explore`")
        cli = block.index("`command -v codegraph` succeeds")
        npx = block.index("`npx -y @colbymchenry/codegraph explore <query>`")
        fallback = block.index("Only when all three routes are unavailable")
        self.assertLess(mcp, cli)
        self.assertLess(cli, npx)
        self.assertLess(npx, fallback)
        self.assertIn("work as a project with no index would", " ".join(block.lower().split()))
        self.assertIn("./init --extension codegraph", block)
        self.assertIn("Say which route you used", block)

    def test_the_block_says_the_index_is_only_maintained_while_a_client_is_attached(self) -> None:
        """It claimed the index was "kept fresh automatically as files change". It is — while a CodeGraph
        client is attached to the daemon that does the watching. Once the work moved into an environment
        with the database and none of the tooling, nothing indexed anything for four days, the slice under
        assessment was absent from the `files` table, and a query about it answered *no callers* in the
        same words it uses for a symbol nothing calls."""
        source = (ROOT / "assets/toolkit/scripts/extensions/codegraph/init.py").read_text()

        self.assertIn("It is only current while a client is attached", source)
        self.assertIn("shuts down on an idle timeout", source)
        self.assertIn("make check-codegraph", source)
        self.assertNotIn("kept fresh automatically", source)
        # A delegate gets the repository instruction, not the parent's live connection or conversation:
        # probe its own tools, use the index when reachable, and say when it is not.
        self.assertIn("A sub-agent does not inherit this session's connection", source)
        self.assertIn("checks its own tools", source)
        self.assertIn("follows the same MCP, installed-CLI, then `npx` order", source)
        self.assertIn("only when none of those routes exists", source)
        self.assertIn("Do not pass the parent", source)
        self.assertIn("keeps its focused stage brief", source)

    def test_a_deferred_mcp_tool_is_not_an_unavailable_one(self) -> None:
        """The availability order was followed and the index still went unused, for a reason neither half
        named. On Claude Code the server's tool reaches a sub-agent *deferred*: the delegate's context
        lists `codegraph_explore` as a bare name with no schema, and calling it fails until the delegate
        loads it by name through the harness's own tool-search step. So "probe your MCP route" reads as
        "you have no MCP route", and a measured `drive-tasks` delegate on an indexed repository spent 45
        Bash calls and a single CLI call. Both halves must say that a name with no schema means not loaded
        yet, or the first route silently drops on every harness that defers MCP tools."""
        source = (ROOT / "assets/toolkit/scripts/extensions/codegraph/init.py").read_text()
        self.assertIn("defers MCP tools", source)
        self.assertIn("not loaded yet", source)
        self.assertIn("tool-search step", source)

        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "deferred", "event-modelling", "go")
            briefs = sorted((repo / "agents").glob("drive-*.md"))
            self.assertTrue(briefs, "no agent briefs generated, so this boundary tests nothing")
            for brief in briefs:
                body = brief.read_text()
                self.assertIn("defers MCP tools", body, f"{brief.name} treats a deferred tool as absent")
                self.assertIn("not loaded yet", body, f"{brief.name} does not say a deferred tool loads")
                self.assertIn("tool-search", body, f"{brief.name} does not name the loading step")
                # The loophole the old wording left: "before a repository-wide text search" reads as
                # permission for a targeted grep, which is what the delegate used it for.
                self.assertNotIn("before a repository-wide text search", body)
                # And the line the index cannot answer, so a delegate stops apologising for `find`.
                self.assertIn("is a `find`, not a question", body)

    def test_the_extension_still_writes_a_marker_fenced_block_into_agents(self) -> None:
        """What the section's conditional wording depends on: the block is what a project checks for, and
        the markers are what carries it into a copy-mode harness's own context file."""
        source = (ROOT / "assets/toolkit/scripts/extensions/codegraph/init.py").read_text()
        self.assertIn("<!-- extension:codegraph:begin -->", source)
        self.assertIn("<!-- extension:codegraph:end -->", source)
        self.assertIn("AGENTS.md", source)


# The three columns `scripts/check-codegraph.py` reads, written the way CodeGraph writes them: a path
# relative to the root, the SHA-256 of the file's bytes, and epoch milliseconds. The rest of that table
# (language, size, modified_at, node_count, errors, generated) is CodeGraph's and no business of the gate.
SCHEMA = """CREATE TABLE files (
    path TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    language TEXT NOT NULL,
    size INTEGER NOT NULL,
    modified_at INTEGER NOT NULL,
    indexed_at INTEGER NOT NULL
)"""


def index(repo: Path, paths: list[str], indexed_at: float | None = None) -> None:
    """Write a `.codegraph/codegraph.db` that says these files were read exactly as they now are."""
    (repo / ".codegraph").mkdir(exist_ok=True)
    at = indexed_at if indexed_at is not None else time.time() * 1000
    with sqlite3.connect(repo / ".codegraph/codegraph.db") as connection:
        connection.execute("DROP TABLE IF EXISTS files")
        connection.execute(SCHEMA)
        connection.executemany(
            "INSERT INTO files VALUES (?, ?, ?, ?, ?, ?)",
            [(path, hashlib.sha256((repo / path).read_bytes()).hexdigest(), "python",
              (repo / path).stat().st_size, at, at) for path in paths],
        )


def sources(repo: Path, suffix: str) -> list[str]:
    """Every tracked file with this suffix, as the gate itself asks the version control system for them."""
    listed = subprocess.run(["git", "ls-files"], cwd=repo, text=True, capture_output=True, check=True)
    return sorted(path for path in listed.stdout.split() if path.endswith(suffix))


def gate(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", "scripts/check-codegraph.py"], cwd=repo, text=True, capture_output=True)


class CodegraphGateTest(FactoryTestCase):
    """`make check-codegraph`: the gate that notices an index its own tooling has stopped writing to.

    The evidence it exists for: a repository whose `.codegraph/codegraph.db` was last written four days
    before the session, whose daemon had shut down on an idle timeout with no client left to hold it up,
    and whose entire slice under assessment was missing from the `files` table while 266 other files were
    in it. Nothing reported any of that. The index answered every question, and *no callers* meant *never
    read this file* — which is the failure the index is bought to prevent, wearing the index's confidence.
    """

    def test_a_project_with_no_index_says_so_and_passes(self) -> None:
        """The code index is an optional extension, so its gate is a no-op in every project that never
        adopted one — inside `verify` rather than beside it for the same reason `check-speckit` is: a
        check nothing runs until somebody remembers it is a check that reports nothing."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "ungated", "standard", "python")

            result = gate(repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("no .codegraph/", result.stdout)
            makefile = (repo / "Makefile").read_text()
            self.assertIn("check-codegraph: ## Fail when the adopted code index no longer describes", makefile)
            self.assertIn("check-extensions check-agents check-speckit check-codegraph", makefile)

    def test_an_index_that_matches_the_tracked_source_passes(self) -> None:
        """Content, not modification time: a checkout, a rebase or a `touch` moves an mtime without
        changing a line, and a gate that fails on those is a gate that gets ignored."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "indexed-current", "standard", "python")
            index(repo, sources(repo, ".py"))
            for path in sources(repo, ".py"):
                (repo / path).touch()

            result = gate(repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("check-codegraph: index current", result.stdout)

    def test_a_file_the_index_never_saw_and_a_file_it_read_before_it_changed_both_fail(self) -> None:
        """The two shapes of the same failure, and the message names the cause rather than a rebuild: the
        watcher runs in a daemon that only exists while a client is attached, so what went wrong is that
        nothing has been attached — and attaching one catches the backlog up by itself."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "indexed-stale", "standard", "python")
            tracked = sources(repo, ".py")
            unseen, edited = tracked[0], tracked[1]
            index(repo, tracked[1:], indexed_at=(time.time() - 4 * 86400) * 1000)
            (repo / edited).write_text((repo / edited).read_text() + "\n# changed after indexing\n")

            result = gate(repo)

            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("no longer describes this working tree", result.stderr)
            self.assertIn(f"- {unseen}", result.stderr)
            self.assertIn(f"- {edited}", result.stderr)
            self.assertIn("1 tracked file(s) the index has never seen", result.stderr)
            self.assertIn("1 tracked file(s) changed since they were indexed", result.stderr)
            self.assertIn("This is not a rebuild you forgot to run", result.stderr)
            self.assertIn("shuts down on its idle timeout", result.stderr)
            self.assertIn("codegraph sync", result.stderr)

    def test_an_index_holding_nothing_at_all_fails_too(self) -> None:
        """Which files an index should hold is read off the ones it has read, so an empty one has no
        opinion about its own gaps and would otherwise pass for want of anything to compare. In a
        checkout with tracked files, an index of nothing is the same failure as an index of a
        four-day-old tree."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "indexed-empty", "standard", "python")
            index(repo, [])

            result = gate(repo)

            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("holds no files at all", result.stderr)

    def test_a_schema_this_gate_cannot_read_is_reported_and_skipped(self) -> None:
        """CodeGraph owns that schema. A version of it that renamed the column this reads is CodeGraph's
        business, not a reason to fail the build of somebody who opted into the extension."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "indexed-moved-on", "standard", "python")
            (repo / ".codegraph").mkdir()
            with sqlite3.connect(repo / ".codegraph/codegraph.db") as connection:
                connection.execute("CREATE TABLE documents (path TEXT)")

            result = gate(repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("CodeGraph's schema may have moved on", result.stdout)
