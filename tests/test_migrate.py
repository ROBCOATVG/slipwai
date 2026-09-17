"""`migrate`: the one command that brings a generated project up to this factory's version.

`replay` is gated in `test_replay.py`; this suite is about the merge around it — that a clean one is one
commit the project can undo, that a conflicted one is left in progress with the files named, that the
tree has to be clean first, that the projections a project derives from the factory's files are re-derived
afterwards, and that the registry is asked whether this slipwai is the newest and the answer is a warning
rather than a refusal either way.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from support import FactoryTestCase, commit_all
from test_replay import NEWER, SKILL, git, newer_factory, tree

from slipwai.assets import ROOT, VERSION

# A registry nothing listens on: the check for a newer slipwai fails fast and the migration goes ahead.
UNREACHABLE = "http://127.0.0.1:9/none"
PAGE = f'<html><body><a href="slipwai-{NEWER}-py3-none-any.whl">slipwai-{NEWER}-py3-none-any.whl</a></body></html>'


class Registry(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 — the handler's name is the protocol's
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PAGE.encode())

    def log_message(self, *_arguments: object) -> None:
        pass


def migrate(repo: Path, factory: Path = ROOT, index: str = UNREACHABLE) -> subprocess.CompletedProcess:
    env = os.environ | {"SLIPWAI_INDEX": index, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@local",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@local"}
    return subprocess.run([str(factory / "slipwai"), "migrate"], cwd=repo, env=env, text=True, capture_output=True)


class MigrateTest(FactoryTestCase):
    def test_a_clean_migration_is_one_commit_the_project_can_undo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "product", "event-modelling", "typescript")
            factory = newer_factory(Path(directory), "\n## A section a newer factory added\n")
            domain = next((repo / "apps/service/src").rglob("*.ts"))
            domain.write_text(domain.read_text() + "\n// the product's own line\n")
            commit_all(repo, "The product's own work")
            before = git(repo, "rev-parse", "HEAD").stdout.strip()

            result = migrate(repo, factory)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"migrated product from {VERSION} to slipwai {NEWER}", result.stdout)
            self.assertIn("Next: /catch-up", result.stdout)
            self.assertIn("could not ask the registry", result.stderr)
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")
            self.assertEqual(git(repo, "rev-parse", "HEAD^").stdout.strip(), before)
            subject = git(repo, "log", "-1", "--format=%s").stdout.strip()
            self.assertEqual(subject, f"Migrate product to slipwai {NEWER}")
            self.assertIn("A section a newer factory added", (repo / SKILL).read_text())
            self.assertIn("the product's own line", domain.read_text())
            self.assertEqual(json.loads((repo / "project.json").read_text())["generator"]["updatedWith"], NEWER)
            # The temporary replay is gone; the merge is the only thing left behind.
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ["factory", "product"])

            again = migrate(repo, factory)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertIn("nothing to migrate", again.stdout)

            git(repo, "reset", "--hard", "ORIG_HEAD")
            self.assertEqual(git(repo, "rev-parse", "HEAD").stdout.strip(), before)

    def test_a_project_with_nothing_of_its_own_fast_forwards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "fresh", "event-modelling", "python")
            factory = newer_factory(Path(directory), "\n## Added\n")
            result = migrate(repo, factory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("fast-forwarded", result.stdout)
            self.assertEqual(git(repo, "rev-list", "--count", "HEAD").stdout.strip(), "2")
            self.assertEqual(git(repo, "log", "-1", "--format=%ae").stdout.strip(), "factory@local")

    def project_the_harness(self, repo: Path) -> Path:
        """Put a project in the state `./init` leaves it in: a harness installed and its projections committed.

        The projections are the project's own files, derived from the factory's. Nothing in a generated tree
        has them until `./init` runs, which is why every test above this one migrates a project that cannot
        drift — and why the drift went unnoticed until a real project hit it.
        """
        (repo / ".specify").mkdir(exist_ok=True)
        (repo / ".specify/integration.json").write_text(
            json.dumps({"installed_integrations": ["claude"], "default_integration": "claude"}) + "\n"
        )
        subprocess.run(["python3", "scripts/agents/project.py"], cwd=repo, check=True, capture_output=True)
        projected = next(
            path for path in repo.rglob("tdd/SKILL.md") if path.relative_to(repo).parts[0] != "skills"
        )
        commit_all(repo, "init: install a harness and project into it")
        return projected

    def test_a_migration_re_derives_the_projections_the_merge_cannot_touch(self) -> None:
        """The failure this closes, and it was not subtle: the factory writes `skills/` and `commands/`, a
        project projects them into every installed harness and commits the result, and the factory has never
        written one of those copies — so neither side of the three-way merge carries them and every
        migration that moved a source file left `check-agents` red. Re-derived here — on disk, since the
        projections are ignored by Git — `make verify` is green on the other side of a migration again."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "projected", "event-modelling", "python")
            projected = self.project_the_harness(repo)
            self.assertNotIn("A newer factory's line", projected.read_text())
            factory = newer_factory(Path(directory), "\n## A newer factory's line\n")
            before = git(repo, "rev-parse", "HEAD").stdout.strip()

            result = migrate(repo, factory)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("extension and harness projections were re-derived", result.stdout)
            self.assertIn("ignored by Git or already current, so there is nothing to commit", result.stdout)
            self.assertIn("A newer factory's line", projected.read_text())
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")
            check = subprocess.run(
                ["python3", "scripts/agents/project.py", "--check"], cwd=repo, capture_output=True, text=True
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            # The projections are ignored by Git since 1.13.0, so the re-derivation is on disk and in no commit: HEAD
            # is the merge itself, and one `git reset --hard ORIG_HEAD` undoes the migration.
            self.assertNotEqual(git(repo, "log", "-1", "--format=%s").stdout.strip(),
                                f"Re-derive projected's agent projections for slipwai {NEWER}")
            git(repo, "reset", "--hard", "ORIG_HEAD")
            self.assertEqual(git(repo, "rev-parse", "HEAD").stdout.strip(), before)

    def test_a_migration_infers_a_legacy_extension_election_and_refreshes_its_block(self) -> None:
        """Projects adopted before extension elections were recorded carry only the marker. Migration uses
        that marker once, writes the durable election, and projects current guidance without rerunning the
        extension's installer or its interactive menu."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "legacy-extension", "event-modelling", "python")
            old = """
<!-- extension:codegraph:begin -->
## CodeGraph
Old guidance that incorrectly says a delegate cannot reach this index.
<!-- extension:codegraph:end -->
"""
            with (repo / "AGENTS.md").open("a") as handle:
                handle.write(old)
            commit_all(repo, "init: adopt CodeGraph before elections were recorded")
            self.assertFalse((repo / ".slipwai/extensions.json").exists())

            factory = newer_factory(Path(directory), "\n## Extension projection migration\n")
            init = factory / "assets/toolkit/scripts/extensions/codegraph/init.py"
            init.write_text(init.read_text().replace(
                "This project is indexed by CodeGraph",
                "This project has migration-refreshed CodeGraph guidance",
            ))

            result = migrate(repo, factory)

            self.assertEqual(result.returncode, 0, result.stderr)
            agents = (repo / "AGENTS.md").read_text()
            self.assertIn("migration-refreshed CodeGraph guidance", agents)
            self.assertNotIn("Old guidance that incorrectly", agents)
            self.assertEqual(agents.count("<!-- extension:codegraph:begin -->"), 1)
            self.assertEqual(
                json.loads((repo / ".slipwai/extensions.json").read_text()),
                {"schemaVersion": 1, "extensions": ["codegraph"]},
            )
            self.assertIn(
                ".slipwai/extensions.json",
                git(repo, "show", "--name-only", "--format=", "HEAD").stdout.splitlines(),
            )
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")

            # Projection is migration's job even when the generated tree is already on this factory.
            (repo / "AGENTS.md").write_text(agents.replace(
                "migration-refreshed CodeGraph guidance", "locally stale CodeGraph guidance"
            ))
            commit_all(repo, "Make the projected extension block stale")
            again = migrate(repo, factory)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertIn("nothing generated to migrate", again.stdout)
            self.assertIn(
                "migration-refreshed CodeGraph guidance", (repo / "AGENTS.md").read_text()
            )
            self.assertNotIn("locally stale CodeGraph guidance", (repo / "AGENTS.md").read_text())

    def test_the_re_derived_projections_stay_out_of_the_commit_the_factory_authored(self) -> None:
        """The reason the refresh is a separate commit rather than an amend. `replay` finds the base for the
        next migration by looking for the newest commit the factory authored; put files the factory does not
        generate into that commit's tree and the *next* replay — which genuinely has no such file — reads as
        the factory deleting them, so the next merge would take the projections away."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "unamended", "event-modelling", "go")
            projected = self.project_the_harness(repo).relative_to(repo).as_posix()
            factory = newer_factory(Path(directory), "\n## Another line\n")

            self.assertEqual(migrate(repo, factory).returncode, 0)

            replayed = git(repo, "rev-list", "-1", "--author=factory@local", "HEAD").stdout.strip()
            self.assertTrue(replayed, "no commit in the migrated history is the factory's")
            listed = git(repo, "ls-tree", "-r", "--name-only", replayed).stdout.splitlines()
            self.assertTrue(listed, "the factory's commit has no tree")
            # Narrowly the projection: `.claude/settings.json` beside it *is* the factory's, written by
            # `agent_settings.py`, and the difference between the two is exactly the point.
            self.assertNotIn(
                projected, listed, "the factory's commit carries a projection it does not generate"
            )
            # And the second migration keeps them, which is the whole point of the paragraph above.
            newer = newer_factory(Path(directory) / "second", "\n## A third line\n")
            self.assertEqual(migrate(repo, newer).returncode, 0)
            check = subprocess.run(
                ["python3", "scripts/agents/project.py", "--check"], cwd=repo, capture_output=True, text=True
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_the_catch_up_for_the_ignored_projections_leaves_a_clone_green(self) -> None:
        """The 1.13.0 catch-up tells a project that committed its projections to `git rm -r --cached` the harness
        directories. Native Spec Kit's own `speckit-*` skills live in the same directory, hashed in the committed
        `.specify/integrations/claude.manifest.json`, so that step also un-commits files the manifest names — and
        on the gate before this, following the documented upgrade turned a green project red on its next clone,
        exactly as fresh generation did. The upgrade order is migrate first, so the fixed gate is in the same
        push; this follows the note as written and clones the result."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "green", "event-modelling", "typescript")
            self.project_the_harness(repo)
            # What `specify init` leaves that the projection does not: its skills and the manifests hashing them.
            skills = [f".claude/skills/speckit-{name}/SKILL.md" for name in ("plan", "specify")]
            core = [".specify/templates/spec-template.md", ".specify/scripts/bash/common.sh"]
            for relative in skills + core:
                (repo / relative).parent.mkdir(parents=True, exist_ok=True)
                (repo / relative).write_text(f"# {relative}\n")
            for integration, files in (("claude", skills), ("speckit", core)):
                hashes = {relative: hashlib.sha256((repo / relative).read_bytes()).hexdigest() for relative in files}
                (repo / ".specify/integrations").mkdir(exist_ok=True)
                (repo / f".specify/integrations/{integration}.manifest.json").write_text(
                    json.dumps({"integration": integration, "files": hashes})
                )
            # A factory before 1.13.0 did not ignore the harness directories, so a plain `git add` committed all of
            # this; here the generated `.gitignore` already does, and the force stands in for that history.
            git(repo, "add", "-f", ".claude/skills", ".claude/commands")
            commit_all(repo, "init: Spec Kit installed, projections committed")
            self.assertIn(".claude/skills/speckit-plan/SKILL.md", git(repo, "ls-files").stdout)
            gate = ["python3", "scripts/check-speckit.py"]
            green = subprocess.run(gate, cwd=repo, text=True, capture_output=True)
            self.assertEqual(green.returncode, 0, green.stdout + green.stderr)

            factory = newer_factory(Path(directory), "\n## A line the upgrade brings\n")
            self.assertEqual(migrate(repo, factory).returncode, 0)
            # The catch-up note, as written: after `slipwai migrate`, once.
            git(repo, "rm", "-r", "-q", "--cached", ".claude/skills", ".claude/commands")
            commit_all(repo, "Stop committing the projections")
            self.assertNotIn(".claude/skills/", git(repo, "ls-files").stdout)

            # The maintainer's checkout still has every file on disk and stays green.
            after = subprocess.run(gate, cwd=repo, text=True, capture_output=True)
            self.assertEqual(after.returncode, 0, after.stdout + after.stderr)
            self.assertNotIn("not projected", after.stdout)
            # CI's clone has the manifest and no harness directory at all, and both gates read that as a clone
            # nobody has run `./init` in yet.
            clone = Path(directory) / "clone"
            git(Path(directory), "clone", "-q", str(repo), str(clone))
            self.assertFalse((clone / ".claude/skills").exists())
            speckit = subprocess.run(gate, cwd=clone, text=True, capture_output=True)
            self.assertEqual(speckit.returncode, 0, speckit.stdout + speckit.stderr)
            self.assertIn(
                "check-speckit: .claude/skills/: 2 file(s) managed by claude not projected here", speckit.stdout
            )
            self.assertIn("2 manifest(s) match", speckit.stdout)
            agents = subprocess.run(
                ["python3", "scripts/agents/project.py", "--check"], cwd=clone, text=True, capture_output=True
            )
            self.assertEqual(agents.returncode, 0, agents.stdout + agents.stderr)
            self.assertIn("not projected here", agents.stdout)

    def test_a_conflict_is_left_in_progress_with_the_files_named(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "product", "event-modelling", "typescript")
            factory = newer_factory(Path(directory), "\n## The factory's section\n")
            skill = repo / SKILL
            skill.write_text(skill.read_text() + "\n## The product's section, in the same place\n")
            commit_all(repo, "The product's own section")
            head = git(repo, "rev-parse", "HEAD").stdout.strip()

            result = migrate(repo, factory)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("stopped at 1 conflict(s)", result.stdout, result.stderr)
            self.assertIn(f"\n  {SKILL}\n", result.stdout)
            self.assertIn("git merge --abort", result.stdout)
            self.assertEqual(git(repo, "diff", "--name-only", "--diff-filter=U").stdout.split(), [SKILL])
            self.assertTrue((repo / ".git/MERGE_HEAD").is_file())
            git(repo, "merge", "--abort")
            self.assertEqual(git(repo, "rev-parse", "HEAD").stdout.strip(), head)
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")

    def test_migrate_refuses_a_dirty_tree_and_a_directory_that_is_not_a_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            elsewhere = Path(directory) / "elsewhere"
            elsewhere.mkdir()
            result = migrate(elsewhere)
            self.assertEqual(result.returncode, 2)
            self.assertIn("there is no project.json", result.stderr)
            self.assertIn("run migrate from that directory", result.stderr)

            repo = self.generate(directory, "dirty", "event-modelling", "go")
            (repo / "notes.md").write_text("uncommitted\n")
            result = migrate(repo)
            self.assertEqual(result.returncode, 2)
            self.assertIn("uncommitted changes", result.stderr)
            self.assertEqual((repo / "notes.md").read_text(), "uncommitted\n")
            self.assertEqual(git(repo, "rev-list", "--count", "HEAD").stdout.strip(), "1")
            self.assertEqual(tree(repo) | {"notes.md": b"uncommitted\n"}, tree(repo))

    def test_migrate_warns_when_a_newer_slipwai_is_published_and_goes_ahead(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), Registry)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                repo = self.generate(directory, "behind", "event-modelling", "typescript")
                result = migrate(repo, ROOT, f"http://127.0.0.1:{server.server_address[1]}/simple")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"warning: this is slipwai {VERSION} and {NEWER} is published", result.stderr)
                self.assertIn("`slipwai upgrade` first", result.stderr)
                self.assertIn("nothing to migrate", result.stdout)
        finally:
            server.shutdown()
            server.server_close()
