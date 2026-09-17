"""The architecture view: where anything starts, what it is made of, where change happens, what depends on what.

Everything on `survey/structure.md` is read and nothing inferred, so what this gates is the reading: an entry
point comes from a manifest or a file's own name, a hotspot from commits that touched the file, a dependency from
the edge CodeGraph's index holds — and a tree with no index, or too little history, says so instead of drawing an
empty section. Experimental, with the rest of adoption (experimental).
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from slipwai.convergence import detected
from slipwai.layout import AT_ROOT, Layout
from slipwai.origin import Adoption
from slipwai.project.structure_page import structure_page
from slipwai.services import App
from slipwai.structure import GRAPH_DB, structure

FILES = {
    "package.json": json.dumps({
        "name": "shop", "private": True, "scripts": {"start": "node src/server.js", "test": "node --test"},
        "bin": {"shop-admin": "bin/admin.js"}, "dependencies": {"express": "^4", "pg": "^8"},
        "devDependencies": {"eslint": "^9"},
    }),
    "src/server.js": "const app = require('./app');\n", "src/app.js": "module.exports = {};\n",
    "bin/admin.js": "#!/usr/bin/env node\n", "test/a.test.js": "test('a', () => {});\n",
    "Dockerfile": "FROM node:22\nCMD [\"node\", \"src/server.js\"]\n",
    "services/worker/go.mod": "module example.com/worker\n\ngo 1.22\n\nrequire (\n\tgithub.com/lib/pq v1.10.9\n"
                              "\tgolang.org/x/sys v0.1.0 // indirect\n)\n",
    "services/worker/cmd/worker/main.go": "package main\n\nfunc main() {}\n",
    "services/worker/internal/jobs/jobs.go": "package jobs\n",
    "tools/py/pyproject.toml": '[project]\nname = "tool"\ndependencies = [\n  "click>=8",\n  "rich",\n]\n\n'
                               '[project.scripts]\nshoptool = "tool.cli:main"\n',
    "tools/py/tool/cli.py": "def main():\n    pass\n",
}


def wrapped(name: str, path: str, ecosystem: str, kind: str = "service") -> App:
    return App(name, path, kind, "javascript", None, 0, generated=False, commands={},
               toolchain={"ecosystem": ecosystem})


APPS = [wrapped("shop", ".", "node"), wrapped("worker", "services/worker", "go"),
        wrapped("tool", "tools/py", "python", "tool")]


def git(repo: Path, *arguments: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *arguments], cwd=repo, check=True,
                   capture_output=True)


def repository(parent: Path, commits: int) -> Path:
    repo = parent / "shop"
    for relative, content in FILES.items():
        (repo / relative).parent.mkdir(parents=True, exist_ok=True)
        (repo / relative).write_text(content)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "theirs")
    for index in range(commits - 1):
        (repo / "src/server.js").write_text(f"// change {index}\n")
        if index % 2:
            (repo / "services/worker/internal/jobs/jobs.go").write_text(f"package jobs // {index}\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", f"change {index}")
    return repo


def fake_index(repo: Path, edges: list[tuple[str, str]]) -> None:
    """CodeGraph's tables as `codegraph init` writes them, holding the file-level edges given."""
    (repo / GRAPH_DB).parent.mkdir()
    connection = sqlite3.connect(repo / GRAPH_DB)
    connection.executescript(
        "create table files (path text primary key, language text, node_count integer);"
        "create table nodes (id text primary key, kind text, name text, file_path text);"
        "create table edges (id integer primary key, source text, target text, kind text);"
        "create table project_metadata (key text primary key, value text);"
        "insert into project_metadata values ('indexed_with_version', '1.6.0');"
    )
    for source, target in edges:
        for path in (source, target):
            connection.execute("insert or ignore into files values (?, 'javascript', 1)", (path,))
            connection.execute("insert or ignore into nodes values (?, 'file', ?, ?)", (f"file:{path}", path, path))
        connection.execute("insert into edges (source, target, kind) values (?, ?, 'imports')",
                           (f"file:{source}", f"file:{target}"))
    connection.commit()
    connection.close()


class StructureTest(unittest.TestCase):
    def test_entry_points_modules_and_dependencies_are_read_from_the_files_that_say_so(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), 1)
            found = structure(repo, APPS)
            shop, worker, tool = found.apps
            self.assertEqual([(p.what, p.path, p.runs) for p in shop.entry_points], [
                ("`npm start`", "package.json", "node src/server.js"),
                ("command `shop-admin`", "bin/admin.js", ""),
                ("container runs", "Dockerfile", 'CMD ["node", "src/server.js"]'),
            ])
            # `bin/` is what a .NET build writes, so the survey's skip list keeps it out of every reading.
            self.assertEqual([m.path for m in shop.modules], ["services/", "src/", "test/", "tools/"])
            self.assertEqual((shop.dependencies, shop.manifest), (("express", "pg"), "package.json"),
                             "runtime dependencies only; a linter is not a dependency of the running code")
            self.assertEqual([(p.what, p.path) for p in worker.entry_points],
                             [("main package", "services/worker/cmd/worker/main.go")])
            self.assertEqual(worker.dependencies, ("github.com/lib/pq",), "an indirect requirement is not declared")
            self.assertEqual([(p.what, p.runs) for p in tool.entry_points],
                             [("console script `shoptool`", "tool.cli:main")])
            self.assertEqual(tool.dependencies, ("click", "rich"))
            # One commit: hotspots would be noise, and the page says so instead of ranking every file at 1.
            self.assertEqual((found.commits, found.authors), (1, 1))
            page = structure_page(found, Adoption(convergence=detected(APPS, Adoption())), Layout("delivery"))
            self.assertIn("too little for a hotspot to mean anything", page)
            self.assertIn("Not read: not indexed: `./init --extension codegraph`", page)
            self.assertIn("- **`npm start`** — `package.json`: `node src/server.js`", page)
            self.assertIn("| `src/` | 2 | javascript |", page)

    def test_hotspots_come_from_commits_and_the_graph_from_codegraphs_own_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), 7)
            fake_index(repo, [("src/server.js", "src/app.js"), ("bin/admin.js", "src/app.js"),
                              ("test/a.test.js", "src/app.js"), ("src/app.js", "bin/admin.js"),
                              ("services/worker/cmd/worker/main.go", "services/worker/internal/jobs/jobs.go")])
            found = structure(repo, APPS)
            shop, worker, _ = found.apps
            self.assertEqual(found.commits, 7)
            self.assertEqual(shop.hotspots[0], ("src/server.js", 7))
            self.assertNotIn("services/worker/internal/jobs/jobs.go", [path for path, _ in shop.hotspots],
                             "the root application is everything the other wrapped applications are not")
            self.assertEqual(worker.hotspots, (("services/worker/internal/jobs/jobs.go", 4),
                                               ("services/worker/cmd/worker/main.go", 1),
                                               ("services/worker/go.mod", 1)))
            self.assertEqual(worker.commits, 4)
            self.assertTrue(found.graph.present)
            self.assertEqual((found.graph.files, found.graph.nodes, found.graph.edges, found.graph.version),
                             (6, 6, 5, "1.6.0"))
            self.assertEqual(shop.depended_on[0], ("src/app.js", 3))
            self.assertEqual(shop.depending[0], ("src/app.js", 1))
            self.assertEqual(worker.depended_on, (("services/worker/internal/jobs/jobs.go", 1),))
            adoption = Adoption(convergence=detected(APPS, Adoption()))
            page = structure_page(found, adoption, Layout("delivery"))
            self.assertIn("7 of the 7 commits before the method arrived (since ", page)
            self.assertIn("| `src/server.js` | 7 |", page)
            self.assertIn("Read from CodeGraph 1.6.0, `.codegraph/codegraph.db`: 6 files, 6 symbols, 5 edges", page)
            self.assertIn("| `src/app.js` | 3 |", page)
            # The map: the row's rung is marked and every rung says what it asks; the cut points at the ledger.
            self.assertIn("stands at `named`", page, "every application here has a recorded kind")
            self.assertIn("- **`named`** — here: to move on, move each application under `apps/<name>/`", page)
            self.assertIn("`delivery/docs/convergence.md`", page)
            self.assertIn("`delivery/survey/pinned.md`", page)
            self.assertIn("`survey/pinned.md`", structure_page(found, adoption, AT_ROOT).replace("delivery/", ""))

    def test_an_index_that_is_not_codegraphs_is_said_not_guessed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), 1)
            (repo / GRAPH_DB).parent.mkdir()
            (repo / GRAPH_DB).write_text("not a database")
            found = structure(repo, APPS)
            self.assertFalse(found.graph.present)
            self.assertIn("could not be read as CodeGraph's schema", found.graph.note)

    def test_the_factorys_own_files_are_not_hotspots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), 5)
            (repo / "delivery").mkdir()
            for index in range(3):
                (repo / "delivery/baseline.json").write_text(f"{index}")
                git(repo, "add", "-A")
                git(repo, "commit", "-q", "-m", "factory")
            # The loop's own bookkeeping is touched on every slice; counted, it was the first real adoption's top
            # hotspot, ahead of any of its code.
            for path in ("project.json", "specs/001-thing/spec.md", "AGENTS.md"):
                for index in range(4):
                    (repo / path).parent.mkdir(parents=True, exist_ok=True)
                    (repo / path).write_text(f"{path} {index}")
                    git(repo, "add", "-A")
                    git(repo, "commit", "-q", "-m", "loop")
            shop = structure(repo, APPS, "delivery").apps[0]
            hot = [path for path, _ in shop.hotspots]
            self.assertNotIn("delivery/baseline.json", hot)
            for path in ("project.json", "specs/001-thing/spec.md", "AGENTS.md"):
                self.assertNotIn(path, hot, "the method's bookkeeping is not where the code changes")
            # And the factory's own commits are not the repository's change: left out, the history is theirs alone.
            self.assertEqual(structure(repo, APPS, "delivery", "t@local").commits, 0)
            self.assertEqual(structure(repo, APPS, "delivery", "nobody@local").commits, 20)


if __name__ == "__main__":
    unittest.main()
